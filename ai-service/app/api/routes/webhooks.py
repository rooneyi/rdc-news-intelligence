import json
import logging
import re
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Response
from app.services.rag_service import RAGService
from app.services.ocr_service import OCRService
from app.services.topic_gate_service import TopicGateService
import httpx
import os
import asyncio
from collections import deque

# WhatsApp / Meta: ~4096 chars per text body; long URLs must not be split mid-link.
_URL_IN_TEXT = re.compile(r"https?://[^\s]+", re.IGNORECASE)


def _pop_whatsapp_chunk(
    text: str,
    min_chars: int,
    hard_max: int,
    *,
    force: bool = False,
) -> tuple[str, str]:
    """
    Retire un préfixe à envoyer comme un message WhatsApp.
    Privilégie les fins de ligne / espaces; évite de couper au milieu d'une URL.
    """
    if not text:
        return "", ""
    if force and len(text) < min_chars:
        return text.strip(), ""

    if len(text) < min_chars:
        return "", text

    limit = min(len(text), hard_max)
    window = text[:limit]

    cut: int | None = None
    for sep in ("\n\n", "\n"):
        p = window.rfind(sep)
        if p >= 0:
            after = p + len(sep)
            if after >= min_chars:
                cut = after
                break

    if cut is None:
        p = window.rfind(" ")
        if p >= 0 and p + 1 >= min_chars:
            cut = p + 1

    if cut is None:
        for m in _URL_IN_TEXT.finditer(text):
            if m.start() < limit < m.end():
                cut = min(m.end(), len(text), hard_max)
                break

    if cut is None:
        cut = limit

    chunk = text[:cut].rstrip()
    rest = text[cut:].lstrip()
    if not chunk and rest:
        n = min(min_chars, len(rest))
        chunk = rest[:n]
        rest = rest[n:]
    return chunk, rest

router = APIRouter()
logger = logging.getLogger(__name__)


def _whatsapp_credentials() -> tuple[str, str]:
    """Token et phone id sans espaces / retours ligne (erreurs Meta fréquentes si .env mal collé)."""
    return (
        (os.getenv("WHATSAPP_TOKEN") or "").strip(),
        (os.getenv("WHATSAPP_PHONE_ID") or "").strip(),
    )
ocr_service = OCRService()
topic_gate_service = TopicGateService()
_whatsapp_queue: deque[dict] = deque()
_whatsapp_queue_lock = asyncio.Lock()


# Telegram limite les messages à 4096 caractères ; au-delà, editMessageText échoue sans mise à jour visible.
TELEGRAM_TEXT_MAX = 4096


def _clip_telegram_text(text: str, limit: int = TELEGRAM_TEXT_MAX) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: limit - 80] + "\n\n… (tronqué — limite Telegram)"


async def _send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": _clip_telegram_text(text)},
        )


async def _telegram_edit_message_text(
    client: httpx.AsyncClient,
    base_url: str,
    chat_id: str,
    message_id: int,
    text: str,
) -> bool:
    clipped = _clip_telegram_text(text)
    resp = await client.post(
        f"{base_url}/editMessageText",
        json={"chat_id": chat_id, "message_id": message_id, "text": clipped},
    )
    try:
        data = resp.json()
    except ValueError:
        logger.error("[Telegram] editMessageText réponse non-JSON (status=%s)", resp.status_code)
        return False
    if not data.get("ok"):
        logger.error("[Telegram] editMessageText refusé: %s", data)
        return False
    return True


async def _extract_telegram_photo_text(message: dict, bot_token: str) -> str:
    photos = message.get("photo") or []
    if not photos:
        return ""

    async with httpx.AsyncClient(timeout=60) as client:
        best_photo = photos[-1]
        file_id = best_photo.get("file_id")
        if not file_id:
            return ""

        resp_file = await client.get(
            f"https://api.telegram.org/bot{bot_token}/getFile",
            params={"file_id": file_id},
        )
        file_data = resp_file.json()
        if not file_data.get("ok"):
            logger.error("[Telegram] Erreur getFile: %s", file_data)
            return ""

        file_path = file_data["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        img_resp = await client.get(file_url)
        return ocr_service.extract_text(img_resp.content)


def _build_combined_message(*parts: str | None) -> str:
    return topic_gate_service.merge_text(*parts)

# Ce webhook traitera le message de l'utilisateur et enverra la réponse en arrière-plan
async def process_telegram_message(chat_id: str, query: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN manquant")
        return

    base_url = f"https://api.telegram.org/bot{bot_token}"

    # 1. Envoi du message d'attente
    message_id = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{base_url}/sendMessage",
                json={"chat_id": chat_id, "text": "🔎 Recherche d'informations en cours..."},
            )
            data = resp.json()
            if not data.get("ok"):
                logger.error(f"Erreur Telegram sendMessage: {data}")
                return
            message_id = data["result"]["message_id"]

            # 2. Traitement RAG IA en streaming
            rag_service = RAGService()
            text_buffer = ""
            sources_header = ""

            async for event in rag_service.generate_answer_stream(
                query,
                top_k=int(os.getenv("TELEGRAM_TOP_K", "3")),
                channel="telegram",
            ):
                event_type = event.get("type")

                if event_type == "sources":
                    sources = event.get("sources", [])
                    if sources:
                        lines = []
                        for i, s in enumerate(sources, 1):
                            url = s.get("url") or "(lien indisponible)"
                            title = s.get("title") or "Source locale"
                            lines.append(f"[{i}] {title} - {url}")
                        sources_header = "🔗 SOURCES LOCALES :\n" + "\n".join(lines) + "\n\n"

                        await _telegram_edit_message_text(
                            client,
                            base_url,
                            chat_id,
                            message_id,
                            sources_header + (text_buffer or "🕒 Génération de la réponse…"),
                        )

                elif event_type == "summary_chunk":
                    chunk = event.get("text", "")
                    if not chunk:
                        continue
                    text_buffer += chunk

                    await _telegram_edit_message_text(
                        client,
                        base_url,
                        chat_id,
                        message_id,
                        sources_header + text_buffer,
                    )

                elif event_type == "error":
                    error_message = event.get("message", "Erreur interne RAG")
                    await _telegram_edit_message_text(
                        client,
                        base_url,
                        chat_id,
                        message_id,
                        error_message,
                    )
                    break

    except Exception as e:
        logger.error(f"Erreur streaming Telegram: {e}")


async def _send_whatsapp_text_direct(phone_number: str, body: str) -> dict:
    whatsapp_token, phone_id = _whatsapp_credentials()
    if not whatsapp_token or not phone_id:
        logger.error("Tokens WhatsApp manquants")
        return

    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {whatsapp_token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": body},
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        raw_body = resp.text[:800]
        if resp.status_code >= 400:
            logger.error(
                "[WhatsApp] Echec envoi Meta (status=%s, to=%s, body=%s)",
                resp.status_code,
                phone_number,
                raw_body,
            )
            raise HTTPException(status_code=502, detail=f"Echec envoi WhatsApp Meta: {raw_body}")

        try:
            data = resp.json()
        except ValueError:
            logger.error("[WhatsApp] Reponse Meta non-JSON: %s", raw_body)
            raise HTTPException(status_code=502, detail="Réponse Meta invalide (non JSON)")

        if data.get("error"):
            logger.error("[WhatsApp] Erreur API Meta: %s", data["error"])
            raise HTTPException(status_code=502, detail=f"Erreur API Meta: {data['error']}")

        logger.info("[WhatsApp] Message envoye a Meta (to=%s)", phone_number)
        return data


async def _whatsapp_mark_read_and_show_typing(wa_message_id: str | None) -> None:
    """
    Marque le message utilisateur comme lu et affiche l’indicateur de frappe (Meta Cloud API).
    Nécessite l’id du message entrant (webhook messages[0].id). Passage direct Meta uniquement.
    """
    if not (wa_message_id and str(wa_message_id).strip()):
        return
    whatsapp_token, phone_id = _whatsapp_credentials()
    if not whatsapp_token or not phone_id:
        return
    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {whatsapp_token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": str(wa_message_id).strip(),
        "typing_indicator": {"type": "text"},
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                logger.warning(
                    "[WhatsApp] Indicateur frappe / lu — echec (status=%s): %s",
                    resp.status_code,
                    resp.text[:400],
                )
            else:
                logger.info("[WhatsApp] Message marque lu + indicateur de frappe")
    except Exception as e:  # noqa: BLE001
        logger.warning("[WhatsApp] Indicateur frappe: %s", e)


async def _send_whatsapp_text(phone_number: str, body: str) -> None:
    """
    Envoie la reponse WhatsApp:
    - direct vers Meta (mode standard)
    - ou via un backend relay (mode local -> prod -> Meta)
    """
    reply_relay_url = os.getenv("WHATSAPP_REPLY_RELAY_URL", "").strip()
    if not reply_relay_url:
        await _send_whatsapp_text_direct(phone_number, body)
        return

    relay_token = os.getenv("WHATSAPP_REPLY_RELAY_TOKEN", "").strip()
    timeout_seconds = float(os.getenv("WHATSAPP_REPLY_RELAY_TIMEOUT", "15"))
    headers = {"Content-Type": "application/json"}
    if relay_token:
        headers["X-RDC-Relay-Token"] = relay_token

    payload = {"to": phone_number, "body": body}
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(reply_relay_url, json=payload, headers=headers)
            if resp.status_code >= 400:
                logger.error(
                    "[WhatsApp] Relay reponse en echec (status=%s, body=%s)",
                    resp.status_code,
                    resp.text[:800],
                )
                return
            logger.info(
                "[WhatsApp] Reponse relayee -> %s (status=%s)",
                reply_relay_url,
                resp.status_code,
            )
    except Exception as e:  # noqa: BLE001
        logger.error("[WhatsApp] Echec relay reponse vers %s: %s", reply_relay_url, e)


async def _send_whatsapp_long_body(phone_number: str, body: str) -> None:
    """
    Envoie un texte complet. Une seule requête Meta si body <= WHATSAPP_CHUNK_MAX_CHARS.
    Au-delà, découpage propre (pas au milieu des URLs) pour respecter la limite ~4096.
    """
    body = (body or "").strip()
    if not body:
        return
    chunk_max = int(os.getenv("WHATSAPP_CHUNK_MAX_CHARS", "3800"))
    chunk_min = int(os.getenv("WHATSAPP_CHUNK_MIN_CHARS", "350"))
    if len(body) <= chunk_max:
        await _send_whatsapp_text(phone_number, body)
        return

    rest = body
    while rest.strip():
        if len(rest) <= chunk_max:
            await _send_whatsapp_text(phone_number, rest.strip())
            break
        to_send, rest = _pop_whatsapp_chunk(rest, chunk_min, chunk_max, force=True)
        if not to_send:
            await _send_whatsapp_text(phone_number, rest.strip())
            break
        await _send_whatsapp_text(phone_number, to_send)


async def _stream_whatsapp_response(
    phone_number: str,
    query: str,
    *,
    wa_message_id: str | None = None,
) -> None:
    rag_service = RAGService()
    text_buffer = ""
    sources: list[dict] = []
    # Premier envoi plus rapide pendant le stream (évite l’attente « vide » trop longue).
    chunk_min = int(os.getenv("WHATSAPP_CHUNK_MIN_CHARS", "220"))
    chunk_max = int(os.getenv("WHATSAPP_CHUNK_MAX_CHARS", "3800"))
    # Par défaut: envoi pendant la génération (streaming). false = tout à la fin (une ou peu de bulles).
    stream_while = os.getenv("WHATSAPP_STREAM_WHILE_GENERATING", "true").lower() not in {
        "0",
        "false",
        "no",
        "off",
    }

    await _whatsapp_mark_read_and_show_typing(wa_message_id)
    if not wa_message_id and os.getenv("WHATSAPP_ACK_IF_NO_TYPING", "true").lower() in {
        "1",
        "true",
        "yes",
    }:
        await _send_whatsapp_text(phone_number, "🔎 Analyse en cours…")

    async for event in rag_service.generate_answer_stream(
        query,
        top_k=int(os.getenv("WHATSAPP_TOP_K", "3")),
        channel="whatsapp",
    ):
        event_type = event.get("type")

        if event_type == "sources":
            sources = event.get("sources", [])
            continue

        if event_type == "summary_chunk":
            text_buffer += event.get("text", "")
            if stream_while:
                while len(text_buffer) >= chunk_min:
                    to_send, text_buffer = _pop_whatsapp_chunk(
                        text_buffer, chunk_min, chunk_max, force=False
                    )
                    if not to_send:
                        break
                    await _send_whatsapp_text(phone_number, to_send)
            continue

        if event_type == "error":
            await _send_whatsapp_text(
                phone_number,
                event.get("message", "Erreur interne RAG"),
            )
            return

        if event_type == "done":
            break

    if stream_while:
        while text_buffer.strip():
            if len(text_buffer) < chunk_min:
                await _send_whatsapp_text(phone_number, text_buffer.strip())
                break
            to_send, text_buffer = _pop_whatsapp_chunk(
                text_buffer, chunk_min, chunk_max, force=True
            )
            if not to_send:
                await _send_whatsapp_text(phone_number, text_buffer.strip())
                break
            await _send_whatsapp_text(phone_number, to_send)
    else:
        await _send_whatsapp_long_body(phone_number, text_buffer)

    if sources:
        lines = []
        for i, source in enumerate(sources, 1):
            title = source.get("title") or "Source locale"
            url = source.get("url") or "(lien indisponible)"
            lines.append(f"[{i}] {title} - {url}")
        await _send_whatsapp_long_body(
            phone_number,
            "🔗 SOURCES LOCALES :\n" + "\n".join(lines),
        )


async def _forward_whatsapp_payload(payload: dict) -> None:
    """
    Relaye le payload webhook vers une URL secondaire (ex: tunnel local).
    Désactivé si WHATSAPP_FORWARD_URL est vide.
    """
    forward_url = os.getenv("WHATSAPP_FORWARD_URL", "").strip()
    if not forward_url:
        return

    forward_token = os.getenv("WHATSAPP_FORWARD_TOKEN", "").strip()
    timeout_seconds = float(os.getenv("WHATSAPP_FORWARD_TIMEOUT", "10"))
    headers = {
        "Content-Type": "application/json",
        "X-RDC-Forwarded": "true",
    }
    if forward_token:
        headers["X-RDC-Forward-Token"] = forward_token

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(forward_url, json=payload, headers=headers)
            logger.info(
                "[WhatsApp] Forward webhook -> %s (status=%s)",
                forward_url,
                resp.status_code,
            )
    except Exception as e:  # noqa: BLE001
        logger.error("[WhatsApp] Echec du forward webhook vers %s: %s", forward_url, e)


def _queue_auth_ok(token_from_header: str) -> bool:
    expected = os.getenv("WHATSAPP_QUEUE_TOKEN", "").strip()
    if not expected:
        return True
    return token_from_header.strip() == expected


async def _enqueue_whatsapp_payload(payload: dict) -> int:
    async with _whatsapp_queue_lock:
        _whatsapp_queue.append(payload)
        return len(_whatsapp_queue)


async def _pop_whatsapp_payload() -> dict | None:
    async with _whatsapp_queue_lock:
        if not _whatsapp_queue:
            return None
        return _whatsapp_queue.popleft()


async def _get_whatsapp_queue_size() -> int:
    async with _whatsapp_queue_lock:
        return len(_whatsapp_queue)


async def _dispatch_whatsapp_payload(payload: dict, background_tasks: BackgroundTasks | None = None) -> None:
    try:
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})

        if "messages" not in value:
            logger.info(
                "[WhatsApp] Payload sans messages (accusé livraison / statut) — pas de RAG."
            )
            return

        msg = value["messages"][0]
        phone_number = msg["from"]
        wa_message_id = msg.get("id")
        msg_type = msg.get("type")
        whatsapp_scope = topic_gate_service.detect_whatsapp_scope(value, msg)
        require_topic_gate = whatsapp_scope == "group"

        if msg_type == "text":
            text = msg["text"]["body"]
            logger.info("[WhatsApp] Requete recue (%s): %.100s", phone_number, text)
            if background_tasks is not None:
                background_tasks.add_task(
                    process_whatsapp_message,
                    phone_number,
                    text,
                    require_topic_gate,
                    wa_message_id,
                )
            else:
                asyncio.create_task(
                    process_whatsapp_message(phone_number, text, require_topic_gate, wa_message_id)
                )

        elif msg_type == "image":
            image = msg.get("image", {})
            media_id = image.get("id")
            caption = image.get("caption")
            logger.info("Image WhatsApp reçue de %s (media_id=%s)", phone_number, media_id)
            if media_id:
                if background_tasks is not None:
                    background_tasks.add_task(
                        process_whatsapp_image,
                        phone_number,
                        media_id,
                        caption,
                        require_topic_gate,
                        wa_message_id,
                    )
                else:
                    asyncio.create_task(
                        process_whatsapp_image(
                            phone_number,
                            media_id,
                            caption,
                            require_topic_gate,
                            wa_message_id,
                        )
                    )
            else:
                logger.error("[WhatsApp] Message image sans media id — webhook Meta incomplet ou format inattendu.")
                asyncio.create_task(
                    _send_whatsapp_text(
                        phone_number,
                        "❌ Impossible de récupérer cette image (identifiant média manquant). Réessaie ou envoie une capture plus légère.",
                    )
                )
    except Exception as e:
        logger.error(f"Erreur de parsing payload WhatsApp: {e}")


async def run_whatsapp_queue_polling() -> None:
    """
    Worker local: lit la file sur le backend heberge puis traite les payloads.
    """
    queue_pop_url = os.getenv("WHATSAPP_QUEUE_POP_URL", "").strip()
    if not queue_pop_url:
        logger.warning("WHATSAPP_QUEUE_POP_URL absent, polling WhatsApp queue desactive.")
        return

    queue_token = os.getenv("WHATSAPP_QUEUE_TOKEN", "").strip()
    poll_interval = float(os.getenv("WHATSAPP_QUEUE_POLL_INTERVAL", "2"))
    timeout_seconds = float(os.getenv("WHATSAPP_QUEUE_TIMEOUT", "15"))
    headers = {}
    if queue_token:
        headers["X-RDC-Queue-Token"] = queue_token

    logger.info("[WhatsApp Queue] Polling actif sur %s", queue_pop_url)
    while True:
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.post(queue_pop_url, headers=headers)

            if resp.status_code >= 400:
                logger.warning(
                    "[WhatsApp Queue] HTTP %s sur queue pop — si FastAPI tourne sur ce même serveur, "
                    "utilise WHATSAPP_QUEUE_POP_URL=http://127.0.0.1:<port>/webhooks/whatsapp/queue/pop "
                    "(évite nginx / 502). Aperçu réponse: %.120s",
                    resp.status_code,
                    (resp.text or "").replace("\n", " "),
                )
                await asyncio.sleep(poll_interval)
                continue

            try:
                data = resp.json()
            except ValueError:
                logger.warning(
                    "[WhatsApp Queue] Réponse non-JSON (proxy mal configuré ?): %.120s",
                    (resp.text or "").replace("\n", " "),
                )
                await asyncio.sleep(poll_interval)
                continue

            item = data.get("item")
            if item:
                await _dispatch_whatsapp_payload(item, background_tasks=None)
                await asyncio.sleep(0.2)
                continue
        except Exception as e:
            logger.error("[WhatsApp Queue] Erreur polling (%s): %r", type(e).__name__, e)

        await asyncio.sleep(poll_interval)

async def process_whatsapp_message(
    phone_number: str,
    query: str,
    require_topic_gate: bool = False,
    wa_message_id: str | None = None,
):
    whatsapp_token, phone_id = _whatsapp_credentials()
    if not whatsapp_token or not phone_id:
        logger.error("Tokens WhatsApp manquants")
        return

    if require_topic_gate:
        decision = await topic_gate_service.classify(query)
        if not decision.should_activate:
            logger.info(
                "[WhatsApp] Message ignoré (thème=%s, confiance=%.2f): %.80s",
                decision.theme,
                decision.confidence,
                query,
            )
            if os.getenv("TOPIC_GATE_REPLY_WHEN_IGNORED", "").lower() in {"1", "true", "yes"}:
                await _send_whatsapp_text(
                    phone_number,
                    "ℹ️ Dans les groupes, ce bot ne répond qu’aux messages liés à l’actualité RDC "
                    "(politique, sport, santé, sécurité). Reformule avec des mots-clés du contexte RDC.",
                )
            return

    try:
        await _stream_whatsapp_response(phone_number, query, wa_message_id=wa_message_id)
    except Exception as e:
        logger.error(f"Erreur envoi WhatsApp: {e}")


async def process_whatsapp_image(
    phone_number: str,
    media_id: str,
    caption: str | None = None,
    require_topic_gate: bool = False,
    wa_message_id: str | None = None,
):
    """Traite une image reçue sur WhatsApp : OCR local puis RAG texte."""
    whatsapp_token, phone_id = _whatsapp_credentials()
    if not whatsapp_token or not phone_id:
        logger.error("Tokens WhatsApp manquants")
        return

    base_headers = {"Authorization": f"Bearer {whatsapp_token}"}

    try:
        async with httpx.AsyncClient() as client:
            # 1. Récupérer l'URL du média
            meta_resp = await client.get(
                f"https://graph.facebook.com/v17.0/{media_id}", headers=base_headers
            )
            meta_data = meta_resp.json()
            if meta_resp.status_code >= 400:
                logger.error(
                    "[WhatsApp] Meta média %s (status=%s): %s",
                    media_id,
                    meta_resp.status_code,
                    meta_data,
                )
                await _send_whatsapp_text(
                    phone_number,
                    "❌ Impossible de télécharger l'image depuis WhatsApp (vérifie le token / les permissions média).",
                )
                return
            media_url = meta_data.get("url")
            if not media_url:
                logger.error("[WhatsApp] Impossible de récupérer l'URL du média: %s", meta_data)
                await _send_whatsapp_text(
                    phone_number,
                    "❌ Impossible d'accéder au fichier image via l'API Meta.",
                )
                return

            # 2. Télécharger l'image
            img_resp = await client.get(media_url, headers=base_headers)
            image_bytes = img_resp.content

            # 3. OCR local
            extracted_text = ocr_service.extract_text(image_bytes)
            combined_query = _build_combined_message(caption, extracted_text)
            if not combined_query:
                logger.info("[WhatsApp] Aucun texte exploitable extrait de l'image pour %s", phone_number)
                await _send_whatsapp_text(
                    phone_number,
                    "❌ Impossible d'extraire du texte de cette image. Ajoute une légende avec ta question, ou envoie une image avec du texte lisible.",
                )
                return

            logger.info("[WhatsApp] Texte OCR extrait (%s): %.80s…", phone_number, extracted_text)

            if require_topic_gate:
                decision = await topic_gate_service.classify(combined_query)
                if not decision.should_activate:
                    logger.info(
                        "[WhatsApp] Image ignorée (thème=%s, confiance=%.2f): %.80s",
                        decision.theme,
                        decision.confidence,
                        combined_query,
                    )
                    return

            # 4. RAG texte en streaming par morceaux
            await _stream_whatsapp_response(phone_number, combined_query, wa_message_id=wa_message_id)

    except Exception as e:  # noqa: BLE001
        logger.exception("Erreur traitement image WhatsApp: %s", e)
        try:
            await _send_whatsapp_text(
                phone_number,
                "⚠️ Erreur technique lors du traitement de l'image. Réessaie dans un instant.",
            )
        except Exception as send_err:  # noqa: BLE001
            logger.error("[WhatsApp] Impossible d'envoyer le message d'erreur image: %s", send_err)

@router.post("/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook pour Telegram : Reçoit une question et y répond en asynchrone pointant au RAG.
    """
    payload = await request.json()
    logger.info(f"Telegram webhook reçu : {payload}")
    
    message = payload.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type", "private")

    if chat_id is None:
        return {"status": "ok"}

    text = message.get("text")
    if text:
        if topic_gate_service.is_group_chat(chat_type):
            decision = await topic_gate_service.classify(text)
            if not decision.should_activate:
                logger.info(
                    "[Telegram] Message groupe ignoré (type=%s, thème=%s, confiance=%.2f): %.80s",
                    chat_type,
                    decision.theme,
                    decision.confidence,
                    text,
                )
                if os.getenv("TOPIC_GATE_REPLY_WHEN_IGNORED", "").lower() in {"1", "true", "yes"}:
                    tok = os.getenv("TELEGRAM_BOT_TOKEN", "")
                    if tok:
                        await _send_telegram_message(
                            tok,
                            str(chat_id),
                            "ℹ️ Dans les groupes, le bot ne répond qu’aux messages jugés liés à l’actualité RDC "
                            "(politique, sport, santé, sécurité). Reformule avec des mots-clés du contexte RDC, "
                            "ou écris-moi en privé.",
                        )
                return {"status": "ok"}

        background_tasks.add_task(process_telegram_message, str(chat_id), text)
        return {"status": "ok"}

    if message.get("photo"):
        caption = message.get("caption")
        extracted_text = await _extract_telegram_photo_text(message, os.getenv("TELEGRAM_BOT_TOKEN", ""))
        combined_query = _build_combined_message(caption, extracted_text)

        if not combined_query:
            if not topic_gate_service.is_group_chat(chat_type):
                await _send_telegram_message(
                    os.getenv("TELEGRAM_BOT_TOKEN", ""),
                    str(chat_id),
                    "❌ Impossible d'extraire du texte de cette image.",
                )
            return {"status": "ok"}

        if topic_gate_service.is_group_chat(chat_type):
            decision = await topic_gate_service.classify(combined_query)
            if not decision.should_activate:
                logger.info(
                    "[Telegram] Image groupe ignorée (type=%s, thème=%s, confiance=%.2f): %.80s",
                    chat_type,
                    decision.theme,
                    decision.confidence,
                    combined_query,
                )
                return {"status": "ok"}

        background_tasks.add_task(process_telegram_message, str(chat_id), combined_query)
        
    return {"status": "ok"}

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook POST pour WhatsApp Cloud API : Reçoit les messages.
    """
    peer = request.client.host if request.client else "?"
    logger.info("[WhatsApp] ← POST /webhooks/whatsapp (client=%s)", peer)

    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        logger.exception("[WhatsApp] Corps JSON invalide ou vide : %s", exc)
        raise HTTPException(status_code=400, detail="JSON invalide") from exc

    try:
        preview = json.dumps(payload, ensure_ascii=False)
    except Exception:
        preview = str(payload)[:800]
    if len(preview) > 1200:
        preview = preview[:1200] + "…"
    logger.info("[WhatsApp] Payload reçu (aperçu): %s", preview)
    is_forwarded_payload = request.headers.get("X-RDC-Forwarded", "").lower() == "true"
    expected_forward_token = os.getenv("WHATSAPP_FORWARD_TOKEN", "").strip()
    received_forward_token = request.headers.get("X-RDC-Forward-Token", "").strip()

    if is_forwarded_payload and expected_forward_token and received_forward_token != expected_forward_token:
        logger.warning("[WhatsApp] Payload forward rejeté: token invalide")
        raise HTTPException(status_code=403, detail="Forward token invalide")

    # Forward optionnel vers un endpoint local (ngrok/cloudflared) sans boucle.
    if not is_forwarded_payload and os.getenv("WHATSAPP_FORWARD_URL", "").strip():
        background_tasks.add_task(_forward_whatsapp_payload, payload)

    # Mode proxy: la prod recoit Meta puis laisse uniquement le local traiter/repondre.
    proxy_only = os.getenv("WHATSAPP_WEBHOOK_PROXY_ONLY", "").lower() in {"1", "true", "yes"}
    if proxy_only and not is_forwarded_payload:
        queue_size = await _enqueue_whatsapp_payload(payload)
        logger.info("[WhatsApp] Mode proxy+queue actif: payload mis en file (taille=%s)", queue_size)
        return {"status": "queued", "queue_size": queue_size}

    await _dispatch_whatsapp_payload(payload, background_tasks=background_tasks)
        
    return {"status": "ok"}


@router.post("/whatsapp/queue/pop")
async def whatsapp_queue_pop(request: Request):
    """
    Endpoint lu par le worker local (mode pull, sans tunnel).
    """
    token = request.headers.get("X-RDC-Queue-Token", "")
    if not _queue_auth_ok(token):
        raise HTTPException(status_code=403, detail="Queue token invalide")

    item = await _pop_whatsapp_payload()
    remaining = await _get_whatsapp_queue_size()
    logger.info(
        "[WhatsApp Queue] → POST /webhooks/whatsapp/queue/pop item=%s remaining=%s",
        "oui" if item else "vide",
        remaining,
    )
    return {"status": "ok", "item": item, "remaining": remaining}


@router.post("/whatsapp/reply-relay")
async def whatsapp_reply_relay(request: Request):
    """
    Endpoint de remontee local -> backend heberge -> API WhatsApp.
    """
    expected_token = os.getenv("WHATSAPP_REPLY_RELAY_TOKEN", "").strip()
    received_token = request.headers.get("X-RDC-Relay-Token", "").strip()
    if expected_token and received_token != expected_token:
        raise HTTPException(status_code=403, detail="Relay token invalide")

    payload = await request.json()
    phone_number = str(payload.get("to", "")).strip()
    body = str(payload.get("body", "")).strip()
    if not phone_number or not body:
        raise HTTPException(status_code=422, detail="Champs 'to' et 'body' requis")

    meta_response = await _send_whatsapp_text_direct(phone_number, body)
    return {"status": "sent", "meta": meta_response}

@router.get("/whatsapp")
async def whatsapp_verify(request: Request):
    """
    Webhook GET pour Meta (WhatsApp) : Nécessaire pour valider le Webhook lors de la création de l'App.
    """
    hub_mode = request.query_params.get("hub.mode")
    hub_challenge = request.query_params.get("hub.challenge")
    hub_verify_token = request.query_params.get("hub.verify_token")
    
    # Token configuré dans le dashboard Meta
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "rdc_news_token")
    
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("Webhook WhatsApp vérifié avec succès!")
        return Response(content=hub_challenge, media_type="text/plain")
        
    raise HTTPException(status_code=403, detail="Token invalide")
