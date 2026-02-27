# FastAPI entrypoint

from fastapi import FastAPI
from app.api.routes.articles import router as articles_router

app = FastAPI()

app.include_router(articles_router)
