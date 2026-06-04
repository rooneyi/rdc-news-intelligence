import json
import logging
import re
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Response
from app.services.rag_service import RAGService
from app.services.ocr_service import OCRService
from app.services.topic_gate_service import TopicGateService
from app.services.embedding_service import EmbeddingService
from app.services.memory_service import (
    ConversationalMemoryService,
    conversational_memory_enabled,
    repeat_note_prefix,
    should_use_refined_local,
    should_use_viral_global,
)
from app.services.whapi_cloud import (
    parse_whapi_payload,
    whapi_config_ok,
    whapi_send_text,
    whapi_webhook_secret_expected,
)
from app.services.whatsapp_media import WhatsappImageLoadError, load_whatsapp_image_bytes
import httpx
import os
import asyncio
import redis.asyncio as redis
from collections import deque
from app.core.config import REDIS_URL

# Redis pour la file d'attente (Orchestrateur) et la mémoire
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
WHAPI_QUEUE_KEY = "whapi_payload_queue"

# Services
ocr_service = OCRService()
topic_gate_service = TopicGateService()
embedding_service = EmbeddingService()
memory_service = ConversationalMemoryService()
rag_service = RAGService()

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

_whapi_queue: deque[dict] = deque()
_whapi_queue_lock = asyncio.Lock()


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
async def process_telegram_message(
    chat_id: str,
    query: str,
    platform_message_id: str | None = None,
):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN manquant")
        return

    if not await memory_service.claim_inbound_message("telegram", platform_message_id):
        return

    base_url = f"https://api.telegram.org/bot{bot_token}"

    query_embedding = embedding_service.generate(query)
    local_context = None
    global_context = None
    if conversational_memory_enabled():
        local_context = await memory_service.search_similar(chat_id, query_embedding)
        global_context = await memory_service.search_global_similar(query_embedding)
    
    # 2. Topic Gate
    decision = await topic_gate_service.classify(query)
    if not decision.should_activate:
        logger.info(
            "[Telegram] Message ignoré (thème=%s, confiance=%.2f): %.80s",
            decision.theme,
            decision.confidence,
            query,
        )
        return

    # 3. Envoi du message d'attente
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

            # 4. Traitement RAG IA (Normal, Raffiné ou Viral)
            text_buffer = ""
            sources_header = ""

            # Analyse de la situation (Viralité transverse vs Local vs Nouveau)
            reply_to_id = None
            if should_use_viral_global(global_context):
                group_count = global_context.get("group_count")
                old_query = global_context.get("last_query", "Sujet transverse")
                old_verdict = local_context.get("verdict", "") if local_context else ""
                
                logger.info(f"[Telegram] Sujet VIRAL détecté dans {group_count} groupes.")
                text_buffer = f"🔥 *ALERTE VIRALITÉ* : Ce sujet circule actuellement dans {group_count} groupes en RDC. Voici une synthèse d'intelligence :\n\n"
                
                gen = rag_service.generate_viral_answer_stream(
                    query=query,
                    old_query=old_query,
                    old_verdict=old_verdict,
                    group_count=group_count,
                    channel="telegram",
                )
                reply_to_id = local_context.get("root_message_id") if local_context else None
            
            elif should_use_refined_local(local_context):
                old_query = local_context.get("query", "Inconnue")
                old_verdict = local_context.get("verdict", "")
                reply_to_id = local_context.get("root_message_id")
                
                logger.info("[Telegram] Génération d'une réponse raffinée locale.")
                text_buffer = repeat_note_prefix()
                
                gen = rag_service.generate_refined_answer_stream(
                    query=query,
                    old_query=old_query,
                    old_verdict=old_verdict,
                    channel="telegram",
                )
            else:
                gen = rag_service.generate_answer_stream(query, channel="telegram")
                reply_to_id = None

            # Si on a un message racine locale, on essaie de citer
            if reply_to_id:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            f"{base_url}/editMessageText",
                            json={
                                "chat_id": chat_id,
                                "message_id": message_id,
                                "text": text_buffer + "🕒 Analyse en cours...",
                                "reply_to_message_id": int(reply_to_id)
                            },
                        )
                except: pass

            async for event in gen:
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
            
            # Sauvegarder en mémoire à la fin du flux
            if text_buffer and conversational_memory_enabled():
                full_verdict = f"{sources_header}{text_buffer}"
                await memory_service.add_to_memory(
                    chat_id=chat_id,
                    query=query,
                    embedding=query_embedding,
                    verdict=full_verdict,
                    sources=[],
                    platform_message_id=str(message_id),
                )

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


async def _send_whatsapp_text(
    phone_number: str,
    body: str,
    *,
    transport: str = "meta",
    reply_to_id: str | None = None,
) -> str | None:
    """
    Envoie la réponse WhatsApp et retourne l'ID du message envoyé si possible.
    Supporte reply_to_id pour créer des bulles de discussion (Pivot Messages).
    """
    if transport == "whapi":
        # Whapi non supporté pour les bulles de discussion pour l'instant
        await whapi_send_text(phone_number, body)
        return None

    whatsapp_token, phone_id = _whatsapp_credentials()
    if not whatsapp_token or not phone_id:
        return None

    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": body},
    }
    
    if reply_to_id:
        payload["context"] = {"message_id": reply_to_id}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url, 
                json=payload, 
                headers={"Authorization": f"Bearer {whatsapp_token}"}
            )
            data = resp.json()
            if data.get("messages"):
                return data["messages"][0].get("id")
    except Exception as e:
        logger.error(f"Erreur _send_whatsapp_text: {e}")
    
    return None

async def _send_whatsapp_long_body(
    phone_number: str,
    body: str,
    *,
    transport: str = "meta",
    reply_to_id: str | None = None,
) -> str | None:
    """
    Envoie un texte complet et retourne l'ID du message.
    """
    body = (body or "").strip()
    if not body:
        return None
    
    chunk_max = int(os.getenv("WHATSAPP_CHUNK_MAX_CHARS", "3800"))
    if len(body) <= chunk_max:
        return await _send_whatsapp_text(phone_number, body, transport=transport, reply_to_id=reply_to_id)

    # Pour les messages longs, on répond au message racine avec le premier chunk
    first_chunk = body[:chunk_max] # Découpage simplifié pour l'exemple
    return await _send_whatsapp_text(phone_number, first_chunk, transport=transport, reply_to_id=reply_to_id)



async def _stream_whatsapp_response(
    phone_number: str,
    query: str,
    *,
    wa_message_id: str | None = None,
    transport: str = "meta",
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
        await _send_whatsapp_text(phone_number, "🔎 Analyse en cours…", transport=transport)

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
                    await _send_whatsapp_text(phone_number, to_send, transport=transport)
            continue

        if event_type == "error":
            await _send_whatsapp_text(
                phone_number,
                event.get("message", "Erreur interne RAG"),
                transport=transport,
            )
            return

        if event_type == "done":
            break

    if stream_while:
        while text_buffer.strip():
            if len(text_buffer) < chunk_min:
                await _send_whatsapp_text(phone_number, text_buffer.strip(), transport=transport)
                break
            to_send, text_buffer = _pop_whatsapp_chunk(
                text_buffer, chunk_min, chunk_max, force=True
            )
            if not to_send:
                await _send_whatsapp_text(phone_number, text_buffer.strip(), transport=transport)
                break
            await _send_whatsapp_text(phone_number, to_send, transport=transport)
    else:
        await _send_whatsapp_long_body(phone_number, text_buffer, transport=transport)

    if sources:
        lines = []
        for i, source in enumerate(sources, 1):
            title = source.get("title") or "Source locale"
            url = source.get("url") or "(lien indisponible)"
            lines.append(f"[{i}] {title} - {url}")
        await _send_whatsapp_long_body(
            phone_number,
            "🔗 SOURCES LOCALES :\n" + "\n".join(lines),
            transport=transport,
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


def _whapi_queue_auth_ok(token_from_header: str) -> bool:
    expected = (
        os.getenv("WHAPI_QUEUE_TOKEN") or os.getenv("WHATSAPP_QUEUE_TOKEN") or ""
    ).strip()
    if not expected:
        return True
    return token_from_header.strip() == expected


async def _enqueue_whapi_payload(payload: dict) -> int:
    try:
        return await redis_client.rpush(WHAPI_QUEUE_KEY, json.dumps(payload))
    except Exception as e:
        logger.error(f"[Whapi Queue] Erreur enqueue: {e}")
        # Fallback in-memory if Redis fails? (optional, but let's stick to Redis)
        return 0


async def _pop_whapi_payload() -> dict | None:
    try:
        raw = await redis_client.lpop(WHAPI_QUEUE_KEY)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.error(f"[Whapi Queue] Erreur pop: {e}")
    return None


async def _get_whapi_queue_size() -> int:
    try:
        return await redis_client.llen(WHAPI_QUEUE_KEY)
    except Exception:
        return 0


def _whapi_can_send_outbound() -> bool:
    """Local : relay VPS ou envoi direct avec WHAPI_TOKEN."""
    if (os.getenv("WHAPI_REPLY_RELAY_URL") or "").strip():
        return True
    return whapi_config_ok()


def _schedule_whapi_processing(
    payload: dict,
    background_tasks: BackgroundTasks | None,
) -> int:
    """Parse Whapi JSON et planifie texte / image (webhook HTTP ou worker file)."""
    inbound = parse_whapi_payload(payload)
    if not inbound:
        return 0

    for item in inbound:
        gate = item.is_group
        logger.info(
            "[Whapi] Dispatch kind=%s chat_id=%s topic_gate=%s",
            item.kind,
            item.chat_id if len(item.chat_id) < 80 else item.chat_id[:77] + "…",
            gate,
        )
        if item.kind == "text":
            if background_tasks is not None:
                background_tasks.add_task(
                    process_whatsapp_message,
                    item.chat_id,
                    item.text,
                    gate,
                    item.message_id,
                    transport="whapi",
                )
            else:
                asyncio.create_task(
                    process_whatsapp_message(
                        item.chat_id,
                        item.text,
                        gate,
                        item.message_id,
                        transport="whapi",
                    )
                )
        else:
            if background_tasks is not None:
                background_tasks.add_task(
                    process_whatsapp_image,
                    item.chat_id,
                    "",
                    item.caption,
                    gate,
                    item.message_id,
                    transport="whapi",
                    media_download_url=item.image_url,
                    media_inline_data_uri=item.image_data_uri,
                )
            else:
                asyncio.create_task(
                    process_whatsapp_image(
                        item.chat_id,
                        "",
                        item.caption,
                        gate,
                        item.message_id,
                        transport="whapi",
                        media_download_url=item.image_url,
                        media_inline_data_uri=item.image_data_uri,
                    )
                )
    return len(inbound)


async def _dispatch_whapi_payload(payload: dict) -> None:
    """Consommateur de file (polling local) : même traitement que POST /whapi."""
    n = _schedule_whapi_processing(payload, background_tasks=None)
    if n == 0:
        hint = ""
        raw = payload.get("messages")
        if isinstance(raw, list) and raw:
            m0 = raw[0]
            if isinstance(m0, dict):
                hint = f" premier_type={m0.get('type')!r} from_me={m0.get('from_me')}"
        logger.info(
            "[Whapi Queue] Payload sans message exploitable (statuts, from_me, parse vide, etc.)%s",
            hint,
        )


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
                        transport="meta",
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


async def run_whapi_queue_polling() -> None:
    """Worker local : lit la file Whapi sur le VPS (pull), même schéma que WhatsApp Meta."""
    queue_pop_url = os.getenv("WHAPI_QUEUE_POP_URL", "").strip()
    if not queue_pop_url:
        logger.warning("WHAPI_QUEUE_POP_URL absent, polling Whapi queue desactive.")
        return

    queue_token = (
        os.getenv("WHAPI_QUEUE_TOKEN") or os.getenv("WHATSAPP_QUEUE_TOKEN") or ""
    ).strip()
    poll_interval = float(os.getenv("WHAPI_QUEUE_POLL_INTERVAL", "2"))
    timeout_seconds = float(os.getenv("WHAPI_QUEUE_TIMEOUT", "15"))
    headers: dict[str, str] = {}
    if queue_token:
        headers["X-RDC-Queue-Token"] = queue_token

    logger.info("[Whapi Queue] Polling actif sur %s", queue_pop_url)
    while True:
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.post(queue_pop_url, headers=headers)

            if resp.status_code >= 400:
                logger.warning(
                    "[Whapi Queue] HTTP %s sur queue pop — utilise WHAPI_QUEUE_POP_URL="
                    "http://127.0.0.1:<port>/webhooks/whapi/queue/pop si FastAPI local. Aperçu: %.120s",
                    resp.status_code,
                    (resp.text or "").replace("\n", " "),
                )
                await asyncio.sleep(poll_interval)
                continue

            try:
                data = resp.json()
            except ValueError:
                logger.warning(
                    "[Whapi Queue] Réponse non-JSON : %.120s",
                    (resp.text or "").replace("\n", " "),
                )
                await asyncio.sleep(poll_interval)
                continue

            item = data.get("item")
            if item:
                await _dispatch_whapi_payload(item)
                await asyncio.sleep(0.2)
                continue
        except Exception as e:
            logger.error("[Whapi Queue] Erreur polling (%s): %r", type(e).__name__, e)

        await asyncio.sleep(poll_interval)


async def process_whatsapp_message(
    phone_number: str,
    query: str,
    require_topic_gate: bool = False,
    wa_message_id: str | None = None,
    *,
    transport: str = "meta",
):
    platform_key = f"whatsapp:{transport}"
    if not await memory_service.claim_inbound_message(platform_key, wa_message_id):
        return

    await _whatsapp_mark_read_and_show_typing(wa_message_id)

    query_embedding = embedding_service.generate(query)
    local_context = None
    global_context = None
    if conversational_memory_enabled():
        local_context = await memory_service.search_similar(phone_number, query_embedding)
        global_context = await memory_service.search_global_similar(query_embedding)
    
    # 2. Topic Gate (Thématisation)
    if require_topic_gate:
        decision = await topic_gate_service.classify(query)
        if not decision.should_activate:
            logger.info(
                "[Whapi] Message ignoré (topic gate) chat=%s raison=%s",
                phone_number[:40] if len(phone_number) > 40 else phone_number,
                getattr(decision, "reason", decision),
            )
            return

    # 3. Exécution RAG (Normal, Raffiné ou Viral)
    try:
        reply_to_id = None
        
        if should_use_viral_global(global_context):
            group_count = global_context.get("group_count")
            old_query = global_context.get("last_query", "Sujet transverse")
            old_verdict = local_context.get("verdict", "") if local_context else ""
            
            logger.info(f"[WhatsApp] Sujet VIRAL ({group_count} groupes).")
            
            rag_res = await rag_service.generate_viral_full_answer(
                query=query,
                old_query=old_query,
                old_verdict=old_verdict,
                group_count=group_count,
                channel="whatsapp"
            )
            verdict = rag_res.get("verdict", "")
            sources = rag_res.get("sources", [])
            body = f"🔥 *ALERTE VIRALITÉ* : Sujet détecté dans {group_count} groupes. Synthèse d'intelligence :\n\n{verdict}"
            reply_to_id = local_context.get("root_message_id") if local_context else None
            
        elif should_use_refined_local(local_context):
            old_query = local_context.get("query", "Inconnue")
            old_verdict = local_context.get("verdict", "")
            reply_to_id = local_context.get("root_message_id")
            logger.info(
                "[Whapi] RAG raffiné (mémoire locale) ancienne requête=%.60s",
                old_query,
            )
            rag_res = await rag_service.generate_refined_full_answer(
                query=query,
                old_query=old_query,
                old_verdict=old_verdict,
                channel="whatsapp"
            )
            verdict = rag_res.get("verdict", "")
            sources = rag_res.get("sources", [])
            body = f"{repeat_note_prefix()}{verdict}"
            
        else:
            logger.info("[Whapi] RAG standard (nouvelle question)")
            rag_res = await rag_service.generate_full_answer(query, channel="whatsapp")
            verdict = rag_res.get("verdict", "")
            sources = rag_res.get("sources", [])
            body = (verdict or "").strip()
        
        # Envoi WhatsApp
        if sources and "SOURCES" not in body.upper():
            # ... (formatage sources existant) ...
            pass # (déjà géré dans les prompt viraux/raffinés normalement)

        logger.info(
            "[Whapi] Réponse prête (%s car.) — envoi WhatsApp",
            len(body or ""),
        )
        sent_message_id = await _send_whatsapp_long_body(
            phone_number, body, transport=transport, reply_to_id=reply_to_id
        )
        logger.info("[Whapi] Message envoyé id=%s", sent_message_id or "(inconnu)")

        if conversational_memory_enabled():
            await memory_service.add_to_memory(
                chat_id=phone_number,
                query=query,
                embedding=query_embedding,
                verdict=verdict,
                sources=sources,
                platform_message_id=sent_message_id,
            )


    except Exception as e:
        logger.error(f"Erreur traitement WhatsApp: {e}")


async def process_whatsapp_image(
    phone_number: str,
    media_id: str,
    caption: str | None = None,
    require_topic_gate: bool = False,
    wa_message_id: str | None = None,
    *,
    transport: str = "meta",
    media_download_url: str | None = None,
    media_inline_data_uri: str | None = None,
):
    """Traite une image : Meta (média_id) ou Whapi (URL HTTP ou preview data:image du webhook)."""
    if transport == "whapi":
        if not _whapi_can_send_outbound():
            logger.error(
                "[Whapi] Ni WHAPI_REPLY_RELAY_URL ni WHAPI_TOKEN — impossible de répondre (image)."
            )
            return
        has_http = bool(
            media_download_url and str(media_download_url).strip().startswith("http")
        )
        has_data = bool(
            media_inline_data_uri
            and str(media_inline_data_uri).strip().startswith("data:image")
        )
        if not has_http and not has_data:
            logger.error(
                "[Whapi] Aucune image exploitable : pas de lien HTTP (Auto Download) "
                "ni preview data:image dans le webhook."
            )
            await _send_whatsapp_text(
                phone_number,
                "❌ Image reçue sans données téléchargeables. Active « Auto Download » sur Whapi "
                "ou renvoie la capture avec une légende.",
                transport=transport,
            )
            return
    else:
        whatsapp_token, phone_id = _whatsapp_credentials()
        if not whatsapp_token or not phone_id:
            logger.error("Tokens WhatsApp manquants")
            return

    platform_key = f"whatsapp:{transport}"
    if not await memory_service.claim_inbound_message(platform_key, wa_message_id):
        return

    await _whatsapp_mark_read_and_show_typing(wa_message_id)

    base_headers: dict[str, str] = {}
    if transport != "whapi":
        wt, _ = _whatsapp_credentials()
        base_headers = {"Authorization": f"Bearer {wt}"}

    media_timeout = float(os.getenv("WHATSAPP_MEDIA_TIMEOUT", "90"))
    ref = media_id or "whapi-url"

    try:
        async with httpx.AsyncClient(timeout=media_timeout) as client:
            try:
                image_bytes = await load_whatsapp_image_bytes(
                    transport=transport,
                    client=client,
                    media_id=media_id,
                    media_download_url=media_download_url,
                    media_inline_data_uri=media_inline_data_uri,
                    meta_auth_headers=base_headers,
                )
            except WhatsappImageLoadError as load_err:
                logger.warning("[WhatsApp] Chargement image (%s): %s", ref, load_err)
                await _send_whatsapp_text(
                    phone_number,
                    f"❌ {load_err.user_message}",
                    transport=transport,
                )
                return

            try:
                extracted_text = ocr_service.extract_text(image_bytes)
            except ValueError as val_exc:
                logger.warning("[WhatsApp] Image/OCR invalide (%s): %s", ref, val_exc)
                await _send_whatsapp_text(
                    phone_number,
                    f"❌ {val_exc}",
                    transport=transport,
                )
                return
            except RuntimeError as rt_exc:
                logger.error("[WhatsApp] Tesseract manquant (%s): %s", ref, rt_exc)
                await _send_whatsapp_text(
                    phone_number,
                    "❌ OCR indisponible sur le serveur. Installe Tesseract "
                    "(`sudo apt install tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng`) "
                    "puis redémarre le service IA.",
                    transport=transport,
                )
                return
            except Exception as ocr_exc:  # noqa: BLE001
                logger.exception("[WhatsApp] Échec OCR (image ref=%s): %s", ref, ocr_exc)
                await _send_whatsapp_text(
                    phone_number,
                    "❌ Lecture OCR impossible sur cette image. Ajoute une légende avec ta question "
                    "ou renvoie une capture plus nette.",
                    transport=transport,
                )
                return

            combined_query = _build_combined_message(caption, extracted_text)
            if not combined_query:
                logger.info(
                    "[WhatsApp] Aucun texte exploitable (OCR vide) pour %s — légende=%r",
                    phone_number,
                    (caption or "")[:80],
                )
                await _send_whatsapp_text(
                    phone_number,
                    "❌ Aucun texte lisible sur l’image. Écris ta question en légende sous la photo, "
                    "ou envoie une capture avec du texte plus grand.",
                    transport=transport,
                )
                return

            logger.info("[WhatsApp] Texte OCR extrait (%s): %.80s…", phone_number, extracted_text)

            query_embedding = None
            if conversational_memory_enabled():
                try:
                    query_embedding = embedding_service.generate(combined_query)
                except Exception as emb_exc:  # noqa: BLE001
                    logger.warning(
                        "[WhatsApp] Embedding mémoire ignoré pour image: %s",
                        emb_exc,
                    )
                if query_embedding is not None:
                    similar_context = await memory_service.search_similar(
                        phone_number, query_embedding
                    )
                    if should_use_refined_local(similar_context):
                        previous_verdict = similar_context.get("verdict")
                        previous_sources = similar_context.get("sources", [])
                        prefix = repeat_note_prefix() or ""
                        sources_text = ""
                        if previous_sources:
                            lines = []
                            for i, s in enumerate(previous_sources, 1):
                                url = s.get("url") or "(lien indisponible)"
                                title = s.get("title") or "Source locale"
                                lines.append(f"[{i}] {title} - {url}")
                            sources_text = "\n🔗 SOURCES LOCALES :\n" + "\n".join(lines) + "\n"
                        await _send_whatsapp_text(
                            phone_number,
                            f"{prefix}{previous_verdict}{sources_text}",
                            transport=transport,
                        )
                        return

            if require_topic_gate:
                decision = await topic_gate_service.classify(combined_query)
                if not decision.should_activate:
                    logger.info(
                        "[WhatsApp] Image ignoré (thème=%s, confiance=%.2f): %.80s",
                        decision.theme,
                        decision.confidence,
                        combined_query,
                    )
                    return

            try:
                rag_res = await rag_service.generate_full_answer(
                    combined_query, channel="whatsapp"
                )
                verdict = rag_res.get("verdict", "")
                sources = rag_res.get("sources", [])

                body = (verdict or "").strip()
                if not body:
                    await _send_whatsapp_text(
                        phone_number,
                        "❌ L’IA n’a pas pu formuler de réponse pour cette image. Réessaie avec une légende explicite.",
                        transport=transport,
                    )
                    return
                if sources and "SOURCES" not in body.upper():
                    lines = []
                    for i, source in enumerate(sources, 1):
                        title = source.get("title") or "Source locale"
                        url = source.get("url") or "(lien indisponible)"
                        lines.append(f"[{i}] {title} - {url}")
                    body = f"{body}\n\n🔗 SOURCES LOCALES :\n" + "\n".join(lines)
                await _send_whatsapp_long_body(phone_number, body, transport=transport)

                if conversational_memory_enabled() and query_embedding is not None:
                    await memory_service.add_to_memory(
                        chat_id=phone_number,
                        query=combined_query,
                        embedding=query_embedding,
                        verdict=verdict,
                        sources=sources,
                    )
            except Exception as rag_exc:  # noqa: BLE001
                logger.exception("[WhatsApp] Erreur RAG image (%s): %s", ref, rag_exc)
                await _send_whatsapp_text(
                    phone_number,
                    "❌ Erreur lors de l’analyse (IA surchargée ou indisponible). Réessaie dans 1–2 minutes.",
                    transport=transport,
                )

    except httpx.HTTPError as http_exc:
        logger.exception("[WhatsApp] Réseau image (%s): %s", ref, http_exc)
        await _send_whatsapp_text(
            phone_number,
            "❌ Délai dépassé ou réseau indisponible pour l’image. Réessaie.",
            transport=transport,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Erreur traitement image WhatsApp (%s): %s", ref, e)
        try:
            await _send_whatsapp_text(
                phone_number,
                "⚠️ Erreur inattendue sur l’image. Réessaie ou ajoute une légende avec ta question.",
                transport=transport,
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

        tg_msg_id = str(message.get("message_id")) if message.get("message_id") is not None else None
        background_tasks.add_task(
            process_telegram_message, str(chat_id), text, tg_msg_id
        )
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

        tg_msg_id = str(message.get("message_id")) if message.get("message_id") is not None else None
        background_tasks.add_task(
            process_telegram_message, str(chat_id), combined_query, tg_msg_id
        )
        
    return {"status": "ok"}


@router.post("/whapi")
async def whapi_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook Whapi.Cloud : format `messages[]` (text, link_preview, image + link, document image, etc.).

    Mode **proxy VPS** : ``WHAPI_WEBHOOK_PROXY_ONLY`` met le JSON brut en file ;
    la machine locale poll ``…/whapi/queue/pop`` puis répond via ``WHAPI_REPLY_RELAY_URL``
    (``…/whapi/reply-relay`` sur le VPS) ou envoi direct si ``WHAPI_TOKEN`` local.

    Sécurité optionnelle : header ``X-RDC-Whapi-Secret`` == ``WHAPI_WEBHOOK_SECRET`` (si défini).
    """
    peer = request.client.host if request.client else "?"
    logger.info("[Whapi] ← POST /webhooks/whapi (client=%s)", peer)

    expected_secret = whapi_webhook_secret_expected()
    if expected_secret:
        got = request.headers.get("X-RDC-Whapi-Secret", "").strip()
        if got != expected_secret:
            logger.warning("[Whapi] Secret webhook refusé")
            raise HTTPException(status_code=403, detail="Secret webhook invalide")

    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        logger.exception("[Whapi] Corps JSON invalide : %s", exc)
        raise HTTPException(status_code=400, detail="JSON invalide") from exc

    try:
        preview = json.dumps(payload, ensure_ascii=False)
    except Exception:
        preview = str(payload)[:800]
    if len(preview) > 1200:
        preview = preview[:1200] + "…"
    logger.info("[Whapi] Payload (aperçu): %s", preview)

    proxy_only = os.getenv("WHAPI_WEBHOOK_PROXY_ONLY", "").lower() in {"1", "true", "yes"}
    if proxy_only:
        queue_size = await _enqueue_whapi_payload(payload)
        logger.info(
            "[Whapi] Mode proxy+queue actif: payload mis en file (taille=%s)",
            queue_size,
        )
        return {"status": "queued", "queue_size": queue_size}

    handled = _schedule_whapi_processing(payload, background_tasks)
    if not handled:
        return {
            "status": "ok",
            "handled": 0,
            "note": "aucun message exploitable (statuts, from_me, etc.)",
        }
    return {"status": "ok", "handled": handled}


@router.post("/whapi/queue/pop")
async def whapi_queue_pop(request: Request):
    """Lu par le worker local (pull) : même rôle que ``/whatsapp/queue/pop`` pour Meta."""
    token = request.headers.get("X-RDC-Queue-Token", "")
    if not _whapi_queue_auth_ok(token):
        raise HTTPException(status_code=403, detail="Queue token invalide")

    item = await _pop_whapi_payload()
    remaining = await _get_whapi_queue_size()
    logger.info(
        "[Whapi Queue] → POST /webhooks/whapi/queue/pop item=%s remaining=%s",
        "oui" if item else "vide",
        remaining,
    )
    return {"status": "ok", "item": item, "remaining": remaining}


@router.post("/whapi/reply-relay")
async def whapi_reply_relay(request: Request):
    """Remontée local → VPS : envoi réel vers Whapi (WHAPI_TOKEN uniquement sur le VPS)."""
    expected_token = (
        os.getenv("WHAPI_REPLY_RELAY_TOKEN")
        or os.getenv("WHATSAPP_REPLY_RELAY_TOKEN")
        or ""
    ).strip()
    received_token = request.headers.get("X-RDC-Relay-Token", "").strip()
    if expected_token and received_token != expected_token:
        raise HTTPException(status_code=403, detail="Relay token invalide")

    body_json = await request.json()
    phone_number = str(body_json.get("to", "")).strip()
    body = str(body_json.get("body", "")).strip()
    if not phone_number or not body:
        raise HTTPException(status_code=422, detail="Champs 'to' et 'body' requis")

    if not whapi_config_ok():
        raise HTTPException(
            status_code=503,
            detail="WHAPI_TOKEN requis sur ce serveur pour relay Whapi",
        )

    await whapi_send_text(phone_number, body)
    return {"status": "sent"}


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
