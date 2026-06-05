import os
import time
import requests
import asyncio
import logging

from app.api.routes.webhooks import process_telegram_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN manquant dans l'environnement")

    api_url = f"https://api.telegram.org/bot{token}"
    last_update_id = None

    logger.info("Démarrage du polling Telegram (long polling getUpdates)…")

    while True:
        try:
            params = {"timeout": 50}
            if last_update_id is not None:
                params["offset"] = last_update_id

            resp = requests.get(f"{api_url}/getUpdates", params=params, timeout=60)
            data = resp.json()

            if not data.get("ok"):
                logger.error("Erreur Telegram getUpdates: %s", data)
                time.sleep(5)
                continue

            for update in data.get("result", []):
                last_update_id = update["update_id"] + 1

                message = update.get("message")
                if not message:
                    continue

                chat = message.get("chat", {})
                chat_id = chat.get("id")
                text = message.get("text")
                telegram_message_id = message.get("message_id")

                if chat_id is None or not text:
                    continue

                logger.info(
                    "Message Telegram reçu (%s, id=%s): %s",
                    chat_id,
                    telegram_message_id,
                    text,
                )

                tg_id_str = (
                    str(telegram_message_id) if telegram_message_id is not None else None
                )
                asyncio.run(process_telegram_message(str(chat_id), text, tg_id_str))

        except Exception as e:
            logger.error("Erreur dans la boucle de polling Telegram: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
