from __future__ import annotations

import asyncio
from typing import List

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from app.services.telegram.config import TelegramSettings
from app.services.telegram.keyword_classifier import classify
from app.services.telegram.backend import BackendResponder


def _format_sources(sources: List[dict]) -> str:
    lines = []
    for src in sources[:3]:
        title = src.get("title") or "(sans titre)"
        url = src.get("url") or src.get("link") or ""
        lines.append(f"- {title}\n{url}")
    return "\n".join(lines)


def _build_reply(data: dict) -> str:
    summary = data.get("summary") or ""
    sources = data.get("sources") or []
    if not sources:
        return summary or "Aucune source trouvée."
    return f"{summary}\n\nSources:\n{_format_sources(sources)}"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, settings: TelegramSettings, backend: BackendResponder) -> None:
    if not update.message or not update.message.text:
        return
    chat_id = update.message.chat_id
    if settings.allowed_chat_ids and chat_id not in settings.allowed_chat_ids:
        return

    text = update.message.text.strip()
    categories = classify(text)
    query = text if not categories else f"{text}\nCategories: {', '.join(categories)}"

    try:
        # Utilise le streaming pour limiter les timeouts
        data = await backend.answer_stream(query)
        reply = _build_reply(data)
    except Exception as exc:  # noqa: BLE001
        reply = "Erreur lors de la génération de la réponse."
        await update.message.reply_text(reply)
        raise exc

    await update.message.reply_text(reply)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Bot prêt. Envoyez une question.")


async def run_bot(settings: TelegramSettings) -> None:
    backend = BackendResponder(settings.backend_endpoint, top_k=settings.top_k, use_rag=settings.use_rag)
    application = Application.builder().token(settings.token).build()

    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: handle_message(u, c, settings, backend)))

    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        # Keep the bot alive until interrupted
        while True:
            await asyncio.sleep(3600)
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await backend.close()
