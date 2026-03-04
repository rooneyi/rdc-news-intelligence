# main.py
from fastapi import FastAPI
from app.api.routes.articles import router as articles_router

app = FastAPI(title="RDC RAG AI Service")

app.include_router(articles_router)