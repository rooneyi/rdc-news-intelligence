# FastAPI entrypoint
# Charge l'environnement avant tout import lourd (sentence_transformers, routes, etc.).
import logging

import app.core.config  # noqa: F401 — charge `.env_file` / `.env`

import asyncio
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse


def _configure_logging() -> None:
    """Sans ça, les `logger.info` des routes / services ne sortent souvent pas (niveau WARNING par défaut)."""
    if os.getenv("RDC_SKIP_LOGGING_CONFIG", "").lower() in {"1", "true", "yes"}:
        return
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


_configure_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RDC News Intelligence AI Service",
    description="Service d'intelligence artificielle pour la détection de désinformation — RDC News",
    version="1.0.0",
)

app.state.bootstrap_ok = False
app.state.bootstrap_error = None


@app.get("/health", tags=["Health"], summary="Service health check")
async def health_check():
    """
    Toujours disponible si ce module se charge.
    `ready: false` indique que le bootstrap complet (RAG, webhooks) a échoué — voir `error`.
    """
    body: dict = {
        "status": "ok",
        "service": "rdc-ai-service",
        "ready": app.state.bootstrap_ok,
    }
    if app.state.bootstrap_error:
        body["error"] = app.state.bootstrap_error
    return JSONResponse(content=body)


def _bootstrap() -> None:
    from app.services.load_dataset import attach_to_app
    from app.api.routes.articles import router as articles_router
    from app.api.routes.webhooks import router as webhooks_router
    from app.services.telegram_polling import run_telegram_polling
    from app.api.routes.webhooks import run_whatsapp_queue_polling

    from app.scheduler import start_cron_jobs, stop_cron_jobs

    attach_to_app(app, background=True, limit=None)

    app.include_router(articles_router)
    app.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])

    @app.on_event("startup")
    async def startup_event():
        if os.getenv("ENABLE_CRON_JOBS", "").lower() in {"1", "true", "yes"}:
            asyncio.create_task(start_cron_jobs())

        if os.getenv("ENABLE_TELEGRAM_POLLING", "").lower() in {"1", "true", "yes"}:
            asyncio.create_task(run_telegram_polling())

        if os.getenv("ENABLE_WHATSAPP_QUEUE_POLLING", "").lower() in {"1", "true", "yes"}:
            asyncio.create_task(run_whatsapp_queue_polling())
            logger.info(
                "[Startup] Polling file WhatsApp actif → %s",
                os.getenv("WHATSAPP_QUEUE_POP_URL", "(WHATSAPP_QUEUE_POP_URL non défini)"),
            )

    @app.on_event("shutdown")
    def shutdown_event():
        stop_cron_jobs()


try:
    _bootstrap()
    app.state.bootstrap_ok = True
except Exception as e:
    app.state.bootstrap_error = f"{type(e).__name__}: {e}"
    logger.exception(
        "Bootstrap FastAPI incomplet — /rag et /webhooks indisponibles tant que la cause n'est pas corrigée."
    )
