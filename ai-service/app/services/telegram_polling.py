import os
import asyncio
import logging

import httpx

from app.api.routes.webhooks import process_telegram_message

logger = logging.getLogger(__name__)


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

                    if chat_id is None or not text:
                        continue

                    logger.info("[TelegramPolling] Message reçu (%s): %s", chat_id, text)

                    # Réutilise exactement la même logique que le webhook
                    await process_telegram_message(str(chat_id), text)

            except Exception as e:  # noqa: BLE001
                logger.error("[TelegramPolling] Erreur dans la boucle: %s", e)
                await asyncio.sleep(5)
