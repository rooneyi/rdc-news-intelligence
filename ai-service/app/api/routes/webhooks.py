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
        
    # 1. Envoi du message d'attente (comme dans votre ancien script)
    url_send = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload_start = {"chat_id": chat_id, "text": "🔎 Recherche d'informations en cours..."}
    
    message_id = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url_send, json=payload_start)
            data = resp.json()
            if data.get("ok"):
                message_id = data["result"]["message_id"]
    except Exception as e:
        logger.error(f"Erreur envoi initial Telegram: {e}")
        return

    # 2. Traitement RAG IA
    rag_service = RAGService()
    response_text = await rag_service.generate_full_answer(query, channel="telegram")
    
    # 3. Édition du message d'attente avec la réponse finale
    if message_id:
        url_edit = f"https://api.telegram.org/bot{bot_token}/editMessageText"
        payload_edit = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": response_text
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(url_edit, json=payload_edit)
        except Exception as e:
            logger.error(f"Erreur édition message Telegram: {e}")

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
