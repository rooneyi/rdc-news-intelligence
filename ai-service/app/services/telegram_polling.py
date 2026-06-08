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

    webhook_cleared = False

    async with httpx.AsyncClient(timeout=60) as client:
        # Webhook actif = getUpdates ne reçoit jamais les messages.
        try:
            del_resp = await client.post(
                f"{api_url}/deleteWebhook",
                json={"drop_pending_updates": False},
            )
            del_data = del_resp.json()
            if del_data.get("ok"):
                logger.info("[TelegramPolling] Webhook supprimé au démarrage (mode polling).")
                webhook_cleared = True
            else:
                logger.warning("[TelegramPolling] deleteWebhook au démarrage: %s", del_data)
        except Exception as e:  # noqa: BLE001
            logger.error("[TelegramPolling] Impossible de supprimer le webhook: %s", e)

        while True:
            try:
                params: dict[str, object] = {"timeout": 50}
                if last_update_id is not None:
                    params["offset"] = last_update_id

                resp = await client.get(f"{api_url}/getUpdates", params=params)
                data = resp.json()

                if not data.get("ok"):
                    desc = str(data.get("description", data))
                    code = data.get("error_code", resp.status_code)
                    # Autre instance getUpdates (PC local, 2e PM2, script standalone).
                    if code == 409 and "other getupdates" in desc.lower():
                        logger.error(
                            "[TelegramPolling] Conflit 409 : une AUTRE instance poll ce bot "
                            "(PC local, PM2 rooney+root, ou scripts/telegram_polling.py). "
                            "Lance : ./scripts/telegram_stop_duplicates.sh --restart"
                        )
                        await asyncio.sleep(15)
                        continue
                    # Webhook actif → getUpdates bloqué.
                    if (
                        not webhook_cleared
                        and (
                            code == 409
                            or "webhook is active" in desc.lower()
                        )
                    ):
                        logger.warning(
                            "[TelegramPolling] Webhook Telegram actif — suppression pour le polling…"
                        )
                        del_resp = await client.post(
                            f"{api_url}/deleteWebhook",
                            json={"drop_pending_updates": True},
                        )
                        del_data = del_resp.json()
                        if del_data.get("ok"):
                            logger.info("[TelegramPolling] Webhook supprimé — polling repris.")
                            webhook_cleared = True
                            continue
                        logger.error(
                            "[TelegramPolling] deleteWebhook échoué: %s", del_data
                        )
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
                    telegram_message_id = message.get("message_id")

                    if chat_id is None:
                        continue

                    # 1. Message texte classique -> pipeline RAG texte
                    if text:
                        logger.info(
                            "[TelegramPolling] Message texte reçu (%s, id=%s): %s",
                            chat_id,
                            telegram_message_id,
                            text,
                        )
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
                        tg_id_str = (
                            str(telegram_message_id)
                            if telegram_message_id is not None
                            else None
                        )
                        asyncio.create_task(
                            process_telegram_message(str(chat_id), text, tg_id_str)
                        )
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

                            tg_id_str = (
                                str(telegram_message_id)
                                if telegram_message_id is not None
                                else None
                            )
                            asyncio.create_task(
                                process_telegram_message(
                                    str(chat_id), combined_query, tg_id_str
                                )
                            )
                        except Exception as e:  # noqa: BLE001
                            logger.error("[TelegramPolling] Erreur traitement image: %s", e)


            except Exception as e:  # noqa: BLE001
                logger.error("[TelegramPolling] Erreur dans la boucle: %s", e)
                await asyncio.sleep(5)
