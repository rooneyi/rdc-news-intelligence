import os
import asyncio
import logging

import httpx

from app.api.routes.webhooks import process_telegram_message, _build_combined_message, _extract_telegram_photo_text
from app.services.topic_gate_service import TopicGateService

logger = logging.getLogger(__name__)
topic_gate_service = TopicGateService()


async def run_telegram_polling() -> None:
    """Boucle de polling Telegram (getUpdates) lancée au démarrage FastAPI.

    - Ne nécessite PAS de webhook ni de HTTPS
    - Réutilise la même logique que le webhook: process_telegram_message
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN manquant, polling Telegram désactivé.")
        return

    api_url = f"https://api.telegram.org/bot{token}"
    last_update_id: int | None = None

    logger.info("[TelegramPolling] Démarrage du polling Telegram (getUpdates)…")

    async with httpx.AsyncClient(timeout=60) as client:
        while True:
            try:
                params: dict[str, object] = {"timeout": 50}
                if last_update_id is not None:
                    params["offset"] = last_update_id

                resp = await client.get(f"{api_url}/getUpdates", params=params)
                data = resp.json()

                if not data.get("ok"):
                    logger.error("[TelegramPolling] Erreur getUpdates: %s", data)
                    await asyncio.sleep(5)
                    continue

                for update in data.get("result", []):
                    last_update_id = update["update_id"] + 1

                    message = update.get("message")
                    if not message:
                        continue

                    chat = message.get("chat", {})
                    chat_id = chat.get("id")
                    chat_type = chat.get("type", "private")
                    text = message.get("text")
                    photos = message.get("photo")
                    caption = message.get("caption")

                    if chat_id is None:
                        continue

                    # 1. Message texte classique -> pipeline RAG texte
                    if text:
                        logger.info("[TelegramPolling] Message texte reçu (%s): %s", chat_id, text)
                        if topic_gate_service.is_group_chat(chat_type):
                            decision = await topic_gate_service.classify(text)
                            if not decision.should_activate:
                                logger.info(
                                    "[TelegramPolling] Message groupe ignoré (type=%s, thème=%s, confiance=%.2f): %.80s",
                                    chat_type,
                                    decision.theme,
                                    decision.confidence,
                                    text,
                                )
                                continue
                        await process_telegram_message(str(chat_id), text)
                        continue

                    # 2. Message image -> OCR local puis RAG
                    if photos:
                        logger.info("[TelegramPolling] Photo reçue (%s), tentative d'OCR…", chat_id)
                        try:
                            extracted_text = await _extract_telegram_photo_text(message, token)
                            combined_query = _build_combined_message(caption, extracted_text)

                            if not combined_query:
                                logger.info("[TelegramPolling] Aucun texte exploitable dans l'image (%s)", chat_id)
                                if not topic_gate_service.is_group_chat(chat_type):
                                    await client.post(
                                        f"{api_url}/sendMessage",
                                        json={
                                            "chat_id": chat_id,
                                            "text": "❌ Impossible d'extraire du texte de cette image.",
                                        },
                                    )
                                continue

                            logger.info(
                                "[TelegramPolling] Texte OCR extrait (%s): %.80s…",
                                chat_id,
                                combined_query,
                            )

                            if topic_gate_service.is_group_chat(chat_type):
                                decision = await topic_gate_service.classify(combined_query)
                                if not decision.should_activate:
                                    logger.info(
                                        "[TelegramPolling] Image groupe ignorée (type=%s, thème=%s, confiance=%.2f): %.80s",
                                        chat_type,
                                        decision.theme,
                                        decision.confidence,
                                        combined_query,
                                    )
                                    continue

                            # Réutilise la logique RAG/streaming texte existante
                            await process_telegram_message(str(chat_id), combined_query)
                        except Exception as e:  # noqa: BLE001
                            logger.error("[TelegramPolling] Erreur traitement image: %s", e)


            except Exception as e:  # noqa: BLE001
                logger.error("[TelegramPolling] Erreur dans la boucle: %s", e)
                await asyncio.sleep(5)
