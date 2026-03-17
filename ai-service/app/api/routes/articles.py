from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.services.article_service import create_article, search_similar, save_crawled_article
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RAGService
from app.services.load_dataset import load_and_insert
from app.schemas.article import ArticleCreate, ArticleOut, RAGRequest, RAGResponse
from app.services.crawler.models import Article as CrawlerArticle
from pydantic import BaseModel
from typing import Optional, List
import os

router = APIRouter()


# ── Articles manuels ────────────────────────────────────────────────────────

@router.post("/articles", response_model=ArticleOut, summary="Create Article", tags=["Articles"])
async def post_article(article: ArticleCreate):
    """Ajoute un nouvel article avec embedding."""
    result = create_article(article)
    if result is None:
        raise HTTPException(status_code=409, detail="Article déjà présent (link/hash)")
    return result


# ── Crawler → DB ─────────────────────────────────────────────────────────────

@router.post("/crawler/articles", summary="Ingest crawled article", tags=["Crawler"])
def ingest_crawled_article(article: CrawlerArticle):
    """
    Reçoit un article crawlé, génère son embedding et le sauvegarde en DB.
    Ignore les doublons (même link ou même hash).
    """
    result = save_crawled_article(article)
    if result is None:
        return {"status": "skipped", "reason": "doublon (link ou hash déjà présent)"}
    return {"status": "saved", "id": result.id, "title": result.title}


@router.post("/crawler/articles/batch", summary="Ingest batch of crawled articles", tags=["Crawler"])
def ingest_crawled_batch(articles: List[CrawlerArticle]):
    """
    Reçoit une liste d'articles crawlés et les insère en DB (ignore les doublons).
    """
    saved, skipped = 0, 0
    for article in articles:
        result = save_crawled_article(article)
        if result is None:
            skipped += 1
        else:
            saved += 1
    return {"status": "done", "saved": saved, "skipped": skipped}


# ── Recherche & RAG ──────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str

embedding_service = EmbeddingService()
rag_service = RAGService()


@router.post("/query", summary="Search Similar Articles", tags=["Articles"])
def query_articles(payload: QueryRequest):
    """Rechercher des articles similaires par requête texte"""
    query_embedding = embedding_service.generate(payload.query)
    results = search_similar(query_embedding)
    return {"results": [r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in results]}


@router.post("/rag", response_model=RAGResponse, summary="RAG - Generate Summary with Sources", tags=["RAG"])
def rag_query(payload: RAGRequest):
    """RAG : génère un résumé + sources pertinentes pour une requête."""
    result = rag_service.generate_answer(payload.query, payload.top_k)
    return RAGResponse(**result)


# ── Admin ────────────────────────────────────────────────────────────────────

class LoadRequest(BaseModel):
    limit: Optional[int] = None


@router.post("/admin/load", summary="Trigger dataset load (admin)", tags=["Admin"])
def admin_trigger_load(payload: LoadRequest, background_tasks: BackgroundTasks):
    """Déclenche le chargement du dataset HuggingFace en arrière-plan."""
    if not (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or os.getenv("DB_HOST")):
        raise HTTPException(status_code=400, detail="Database credentials not found in environment.")
    background_tasks.add_task(
        load_and_insert, None,
        "bernard-ng/drc-news-corpus",
        "sentence-transformers/all-MiniLM-L6-v2",
        payload.limit
    )
    return {"status": "scheduled"}
