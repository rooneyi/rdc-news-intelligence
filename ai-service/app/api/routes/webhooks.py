import logging
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Response
from app.services.rag_service import RAGService
import httpx
import os

router = APIRouter()
logger = logging.getLogger(__name__)

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

async def process_whatsapp_message(phone_number: str, query: str):
    whatsapp_token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    if not whatsapp_token or not phone_id:
        logger.error("Tokens WhatsApp manquants")
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

@router.post("/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook pour Telegram : Reçoit une question et y répond en asynchrone pointant au RAG.
    """
    payload = await request.json()
    logger.info(f"Telegram webhook reçu : {payload}")
    
    if "message" in payload and "text" in payload["message"]:
        chat_id = payload["message"]["chat"]["id"]
        text = payload["message"]["text"]
        
        # Filtre optionnel pour éviter le spam, activable si besoin (ex: text.startswith('/verifier'))
        background_tasks.add_task(process_telegram_message, str(chat_id), text)
        
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
            if msg.get("type") == "text":
                text = msg["text"]["body"]
                # Filtre anti-spam : on peut exiger que le message commence par "? " ou "!check "
                logger.info(f"Message de WhatsApp de {phone_number} : {text}")
                background_tasks.add_task(process_whatsapp_message, phone_number, text)
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
