import logging
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Response
from app.services.rag_service import RAGService
from app.services.ocr_service import OCRService
from app.services.topic_gate_service import TopicGateService
import httpx
import os
import asyncio
from collections import deque

router = APIRouter()
logger = logging.getLogger(__name__)
ocr_service = OCRService()
topic_gate_service = TopicGateService()
_whatsapp_queue: deque[dict] = deque()
_whatsapp_queue_lock = asyncio.Lock()


async def _send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )


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

                        await client.post(
                            f"{base_url}/editMessageText",
                            json={
                                "chat_id": chat_id,
                                "message_id": message_id,
                                "text": sources_header + (text_buffer or "🕒 Génération de la réponse…"),
                            },
                        )

                elif event_type == "summary_chunk":
                    chunk = event.get("text", "")
                    if not chunk:
                        continue
                    text_buffer += chunk

                    await client.post(
                        f"{base_url}/editMessageText",
                        json={
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "text": sources_header + text_buffer,
                        },
                    )

                elif event_type == "error":
                    error_message = event.get("message", "Erreur interne RAG")
                    await client.post(
                        f"{base_url}/editMessageText",
                        json={
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "text": error_message,
                        },
                    )
                    break

    except Exception as e:
        logger.error(f"Erreur streaming Telegram: {e}")


async def _send_whatsapp_text_direct(phone_number: str, body: str) -> None:
    whatsapp_token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
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

    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, headers=headers)


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
            logger.info(
                "[WhatsApp] Reponse relayee -> %s (status=%s)",
                reply_relay_url,
                resp.status_code,
            )
    except Exception as e:  # noqa: BLE001
        logger.error("[WhatsApp] Echec relay reponse vers %s: %s", reply_relay_url, e)


async def _stream_whatsapp_response(phone_number: str, query: str) -> None:
    rag_service = RAGService()
    text_buffer = ""
    sources: list[dict] = []

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
            if len(text_buffer) >= 350:
                await _send_whatsapp_text(phone_number, text_buffer)
                text_buffer = ""
            continue

        if event_type == "error":
            await _send_whatsapp_text(
                phone_number,
                event.get("message", "Erreur interne RAG"),
            )
            return

        if event_type == "done":
            break

    if text_buffer.strip():
        await _send_whatsapp_text(phone_number, text_buffer)

    if sources:
        lines = []
        for i, source in enumerate(sources, 1):
            title = source.get("title") or "Source locale"
            url = source.get("url") or "(lien indisponible)"
            lines.append(f"[{i}] {title} - {url}")
        await _send_whatsapp_text(phone_number, "🔗 SOURCES LOCALES :\n" + "\n".join(lines))


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
            return

        msg = value["messages"][0]
        phone_number = msg["from"]
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
                )
            else:
                asyncio.create_task(process_whatsapp_message(phone_number, text, require_topic_gate))

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
                    )
                else:
                    asyncio.create_task(
                        process_whatsapp_image(phone_number, media_id, caption, require_topic_gate)
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
                data = resp.json()
                item = data.get("item")
                if item:
                    await _dispatch_whatsapp_payload(item, background_tasks=None)
                    await asyncio.sleep(0.2)
                    continue
        except Exception as e:
            logger.error("[WhatsApp Queue] Erreur polling: %s", e)

        await asyncio.sleep(poll_interval)

async def process_whatsapp_message(phone_number: str, query: str, require_topic_gate: bool = False):
    whatsapp_token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
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
            return
        

    try:
        await _stream_whatsapp_response(phone_number, query)
    except Exception as e:
        logger.error(f"Erreur envoi WhatsApp: {e}")


async def process_whatsapp_image(
    phone_number: str,
    media_id: str,
    caption: str | None = None,
    require_topic_gate: bool = False,
):
    """Traite une image reçue sur WhatsApp : OCR local puis RAG texte."""
    whatsapp_token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
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
            media_url = meta_data.get("url")
            if not media_url:
                logger.error("[WhatsApp] Impossible de récupérer l'URL du média: %s", meta_data)
                return

            # 2. Télécharger l'image
            img_resp = await client.get(media_url, headers=base_headers)
            image_bytes = img_resp.content

            # 3. OCR local
            extracted_text = ocr_service.extract_text(image_bytes)
            combined_query = _build_combined_message(caption, extracted_text)
            if not combined_query:
                logger.info("[WhatsApp] Aucun texte exploitable extrait de l'image pour %s", phone_number)
                payload = {
                    "messaging_product": "whatsapp",
                    "to": phone_number,
                    "type": "text",
                    "text": {"body": "❌ Impossible d'extraire du texte de cette image."},
                }
                await client.post(
                    f"https://graph.facebook.com/v17.0/{phone_id}/messages",
                    json=payload,
                    headers={**base_headers, "Content-Type": "application/json"},
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
            await _stream_whatsapp_response(phone_number, combined_query)

    except Exception as e:  # noqa: BLE001
        logger.error(f"Erreur traitement image WhatsApp: {e}")

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
    payload = await request.json()
    logger.info(f"WhatsApp webhook reçu : {payload}")
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

    await _send_whatsapp_text_direct(phone_number, body)
    return {"status": "sent"}

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
