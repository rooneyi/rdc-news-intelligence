# FastAPI entrypoint
# Variables d'environnement chargées automatiquement via app.core.config
from fastapi import FastAPI
from app.services.load_dataset import attach_to_app
from app.api.routes.articles import router as articles_router
from app.api.routes.webhooks import router as webhooks_router
from app.services.telegram_polling import run_telegram_polling

app = FastAPI(title="RDC News Intelligence AI Service")

# Attach dataset loader to startup; run in background by default
attach_to_app(app, background=True, limit=None)

# Include routers
app.include_router(articles_router)
app.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])

import asyncio
import os
from app.scheduler import start_cron_jobs, stop_cron_jobs

@app.on_event("startup")
async def startup_event():
    """Démarre les tâches de fond non bloquantes au démarrage du serveur."""

    # Cron (crawler + re-embedding) désactivé par défaut pour ne pas impacter
    # la réactivité de l'app. Active-le explicitement via l'env si tu le souhaites.
    if os.getenv("ENABLE_CRON_JOBS", "").lower() in {"1", "true", "yes"}:
        asyncio.create_task(start_cron_jobs())

    # Active le polling Telegram uniquement sur demande explicite.
    # Sinon, si un webhook est déjà branché, on peut rejouer d'anciens messages.
    if os.getenv("ENABLE_TELEGRAM_POLLING", "").lower() in {"1", "true", "yes"}:
        asyncio.create_task(run_telegram_polling())

@app.on_event("shutdown")
def shutdown_event():
    """Arrête proprement le CRON lors de la fermeture du serveur."""
    stop_cron_jobs()
