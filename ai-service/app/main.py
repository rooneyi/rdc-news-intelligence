# FastAPI entrypoint
# Variables d'environnement chargées automatiquement via app.core.config
from fastapi import FastAPI
from app.services.load_dataset import attach_to_app
from app.api.routes.articles import router as articles_router

app = FastAPI(title="RDC News Intelligence AI Service")

# Attach dataset loader to startup; run in background by default
attach_to_app(app, background=True, limit=None)

# Include routers
app.include_router(articles_router)
