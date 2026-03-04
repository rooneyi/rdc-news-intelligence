from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.schemas.article import ArticleCreate, ArticleOut
from app.services.article_service import create_article, search_similar
from app.services.embedding_service import EmbeddingService
from app.services.load_dataset import load_and_insert
from pydantic import BaseModel
import os

router = APIRouter()

@router.post("/articles", response_model=ArticleOut, summary="Create Article", tags=["Articles"])
async def post_article(article: ArticleCreate):
    """Ajoute un nouvel article avec embedding."""
    return create_article(article.title, article.content)


class QueryRequest(BaseModel):
    query: str

embedding_service = EmbeddingService()

@router.post("/query")
def query_articles(payload: QueryRequest):
    query_embedding = embedding_service.generate(payload.query)
    results = search_similar(query_embedding)
    return {"results": [r.dict() for r in results]}


# Admin endpoint to trigger dataset loading on demand
class LoadRequest(BaseModel):
    limit: int | None = None

@router.post("/admin/load", summary="Trigger dataset load (admin)", tags=["Admin"])
def admin_trigger_load(payload: LoadRequest, background_tasks: BackgroundTasks):
    """
    Trigger the dataset load in background. Requires DB credentials present in env (DATABASE_URL or DB_HOST...).
    Returns 202 Accepted if scheduled, 400 if DB creds are missing.
    """
    if not (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or os.getenv("DB_HOST")):
        raise HTTPException(status_code=400, detail="Database credentials not found in environment. Set DATABASE_URL or DB_HOST/DB_USER/DB_PASSWORD.")

    # schedule the blocking load in a threadpool (BackgroundTasks will run it)
    background_tasks.add_task(load_and_insert, None, "bernard-ng/drc-news-corpus", "sentence-transformers/all-MiniLM-L6-v2", payload.limit)
    return {"status": "scheduled"}
