# FastAPI entrypoint
import os
from dotenv import load_dotenv

# Load environment variables first, before any other imports
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env_file")
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=dotenv_path)

from fastapi import FastAPI
from app.services.load_dataset import attach_to_app
from app.api.routes.articles import router as articles_router

app = FastAPI(title="RDC News Intelligence AI Service")

# Attach dataset loader to startup; run in background by default
attach_to_app(app, background=True, limit=None)

# Include routers
app.include_router(articles_router)
