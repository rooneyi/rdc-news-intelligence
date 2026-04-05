import os
import asyncio
import logging

import httpx

from app.api.routes.webhooks import process_telegram_message
from app.services.ocr_service import OCRService

logger = logging.getLogger(__name__)

ocr_service = OCRService()


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
                    text = message.get("text")
                    photos = message.get("photo")

                    if chat_id is None:
                        continue

                    # 1. Message texte classique -> pipeline RAG texte
                    if text:
                        logger.info("[TelegramPolling] Message texte reçu (%s): %s", chat_id, text)
                        await process_telegram_message(str(chat_id), text)
                        continue

                    # 2. Message image -> OCR local puis RAG
                    if photos:
                        logger.info("[TelegramPolling] Photo reçue (%s), tentative d'OCR…", chat_id)
                        try:
                            # On prend la meilleure résolution (dernier élément)
                            best_photo = photos[-1]
                            file_id = best_photo.get("file_id")
                            if not file_id:
                                continue

                            # Récupérer le chemin du fichier via getFile
                            resp_file = await client.get(f"{api_url}/getFile", params={"file_id": file_id})
                            file_data = resp_file.json()
                            if not file_data.get("ok"):
                                logger.error("[TelegramPolling] Erreur getFile: %s", file_data)
                                continue

                            file_path = file_data["result"]["file_path"]
                            file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"

                            # Télécharger l'image
                            img_resp = await client.get(file_url)
                            image_bytes = img_resp.content

                            # OCR local
                            extracted_text = ocr_service.extract_text(image_bytes)
                            if not extracted_text:
                                logger.info("[TelegramPolling] Aucun texte extrait de l'image (%s)", chat_id)
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
                                extracted_text,
                            )

                            # Réutilise la logique RAG/streaming texte existante
                            await process_telegram_message(str(chat_id), extracted_text)
                        except Exception as e:  # noqa: BLE001
                            logger.error("[TelegramPolling] Erreur traitement image: %s", e)


            except Exception as e:  # noqa: BLE001
                logger.error("[TelegramPolling] Erreur dans la boucle: %s", e)
                await asyncio.sleep(5)
