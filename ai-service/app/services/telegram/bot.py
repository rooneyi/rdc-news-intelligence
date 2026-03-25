import asyncio
import logging
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app.services.telegram.config import TelegramSettings
from app.services.telegram.backend import BackendResponder

logger = logging.getLogger(__name__)

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Réponse à la commande /start"""
    await update.message.reply_text(
        "🇨🇩 *RDC News Intelligence AI*\n\n"
        "Posez-moi une question sur l'actualité en République Démocratique du Congo.\n"
        "Je vais rechercher les articles les plus pertinents et Mistral vous fera une synthèse.",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, settings: TelegramSettings, backend: BackendResponder) -> None:
    """Gère les messages textuels avec streaming en temps réel"""

    if not update.message or not update.message.text:
        return

    query = update.message.text.strip()

    # Toujours utiliser le pipeline RAG pour toute question
    placeholder = await update.message.reply_text("🔎 Recherche d'informations en cours...")

    try:
        url = f"{backend.base_url}/rag/stream"
        logger.info(f"[DEBUG] Appel backend URL: {url}")
        payload = {"query": query, "top_k": settings.top_k}
        full_response = ""
        last_sent_text = ""
        sources_text = ""
        async with backend._client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("type") == "sources":
                        sources = data.get("sources", [])
                        if sources:
                            sources_text = "\n\n🔗 *Sources :*\n" + "\n".join([f"- {s['title']}" for s in sources[:3]])
                    elif data.get("type") == "summary_chunk":
                        full_response += data.get("text", "")
                        if len(full_response) - len(last_sent_text) > 40:
                            await context.bot.edit_message_text(
                                chat_id=update.message.chat_id,
                                message_id=placeholder.message_id,
                                text=full_response + "..."
                            )
                            last_sent_text = full_response
                except Exception:
                    continue
        final_text = (full_response or "Mistral n'a pas pu générer de réponse.") + sources_text
        await context.bot.edit_message_text(
            chat_id=update.message.chat_id,
            message_id=placeholder.message_id,
            text=final_text
        )
    except Exception as e:
        import traceback
        err_type = type(e).__name__
        err_msg = str(e)
        tb = traceback.format_exc(limit=2)
        logger.error(f"[DEBUG] Connection Error: {err_type}: {err_msg}\nTraceback: {tb}")
        error_msg = (
            f"❌ Erreur de connexion\n\nLe Bot n'arrive pas à joindre le serveur AI sur :\n{backend.base_url}\n\n"
            f"Vérifie que le serveur FastAPI est bien lancé.\n\n[DEBUG] Erreur: {err_type}: {err_msg}"
        )
        try:
            await context.bot.edit_message_text(
                chat_id=update.message.chat_id,
                message_id=placeholder.message_id,
                text=error_msg
            )
        except Exception:
            await update.message.reply_text(error_msg)

async def run_bot(settings: TelegramSettings) -> None:
    """Initialise et lance le bot Telegram"""
    backend = BackendResponder(settings.backend_endpoint, top_k=settings.top_k, use_rag=settings.use_rag)
    application = Application.builder().token(settings.token).build()

    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        lambda u, c: handle_message(u, c, settings, backend)
    ))

    logger.info(f"Bot démarré. Cible backend : {settings.backend_endpoint}")
    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        while True:
            await asyncio.sleep(3600)
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await backend.close()
