# FastAPI entrypoint

from fastapi import FastAPI
from app.services.load_dataset import attach_to_app

app = FastAPI()

# Attach dataset loader to startup; run in background by default
attach_to_app(app, background=True, limit=None)

# Try to include router from possible locations without raising at import time
try:
    from app.api.routes.articles import router as articles_router
except Exception:
    try:
        from app.api.route import router as articles_router
    except Exception:
        articles_router = None

if articles_router is not None:
    app.include_router(articles_router)
