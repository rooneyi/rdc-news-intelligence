import logging
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Response
from app.services.rag_service import RAGService
from app.services.ocr_service import OCRService
from app.services.topic_gate_service import TopicGateService
import httpx
import os

router = APIRouter()
logger = logging.getLogger(__name__)
ocr_service = OCRService()
topic_gate_service = TopicGateService()


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

            async for event in rag_service.generate_answer_stream(query, top_k=int(os.getenv("TELEGRAM_TOP_K", "3"))):
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
        
    rag_service = RAGService()
    # Utilisation du canal whatsapp pour avoir un prompt court et précis
    response_text = await rag_service.generate_full_answer(query, channel="whatsapp")
    
    # Envoi de la réponse à WhatsApp (Cloud API)
    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {whatsapp_token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": response_text}
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, headers=headers)
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

            # 4. RAG texte complet
            rag_service = RAGService()
            response_text = await rag_service.generate_full_answer(
                combined_query, channel="whatsapp"
            )

            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": response_text},
            }
            await client.post(
                f"https://graph.facebook.com/v17.0/{phone_id}/messages",
                json=payload,
                headers={**base_headers, "Content-Type": "application/json"},
            )

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
    
    try:
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        
        if "messages" in value:
            msg = value["messages"][0]
            phone_number = msg["from"]
            msg_type = msg.get("type")
            whatsapp_scope = topic_gate_service.detect_whatsapp_scope(value, msg)
            require_topic_gate = whatsapp_scope == "group"

            if msg_type == "text":
                text = msg["text"]["body"]
                logger.info(f"Message texte WhatsApp de {phone_number} : {text}")
                background_tasks.add_task(
                    process_whatsapp_message,
                    phone_number,
                    text,
                    require_topic_gate,
                )

            elif msg_type == "image":
                image = msg.get("image", {})
                media_id = image.get("id")
                caption = image.get("caption")
                logger.info(f"Image WhatsApp reçue de {phone_number} (media_id=%s)", media_id)
                if media_id:
                    background_tasks.add_task(
                        process_whatsapp_image,
                        phone_number,
                        media_id,
                        caption,
                        require_topic_gate,
                    )
    except Exception as e:
        logger.error(f"Erreur de parsing payload WhatsApp: {e}")
        
    return {"status": "ok"}

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
