from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import json
import logging
from app.services.article_service import create_article, search_similar, save_crawled_article
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RAGService
from app.services.ocr_service import OCRService
from app.services.load_dataset import load_and_insert
from app.schemas.article import ArticleCreate, ArticleOut, RAGRequest, RAGResponse
from app.services.crawler.models import Article as CrawlerArticle
from pydantic import BaseModel
from typing import Optional, List
import os

router = APIRouter()
logger = logging.getLogger(__name__)

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
    """
    result = save_crawled_article(article)
    if result is None:
        return {"status": "skipped", "reason": "doublon (link ou hash déjà présent)"}
    return {"status": "saved", "id": result.id, "title": result.title}


@router.post("/crawler/articles/batch", summary="Ingest batch of crawled articles", tags=["Crawler"])
def ingest_crawled_batch(articles: List[CrawlerArticle]):
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
ocr_service = OCRService()


@router.post("/query", summary="Search Similar Articles", tags=["Articles"])
def query_articles(payload: QueryRequest):
    """Rechercher des articles similaires par requête texte"""
    query_embedding = embedding_service.generate(payload.query)
    results = search_similar(query_embedding)
    return {"results": [r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in results]}


@router.post("/rag", response_model=RAGResponse, summary="RAG classique", tags=["RAG"])
async def rag_query(payload: RAGRequest):
    """Version non-streaming : réponse complète via le pipeline RAG
    
    Le paramètre channel indique la source: 'web', 'telegram', 'whatsapp', etc.
    Cette info permet de router la réponse au bon endroit si besoin.
    """
    channel = getattr(payload, "channel", "web")
    logger.info(f"[RAG] Requête depuis channel={channel}: {payload.query[:80]}")
    
    result = rag_service.generate_answer_stream(payload.query, payload.top_k, channel=channel)
    summary = ""
    sources = []
    async for chunk in result:
        if chunk.get("type") == "summary_chunk":
            summary += chunk.get("text", "")
        elif chunk.get("type") == "sources":
            sources = chunk.get("sources", [])
    
    logger.info(f"[RAG] Réponse complète ({len(summary)} chars, {len(sources)} sources)")
    return {"summary": summary or "Mistral n'a pas pu générer de réponse.", "sources": sources, "query": payload.query}


@router.post("/rag/image", response_model=RAGResponse, summary="RAG à partir d'une image (OCR local)", tags=["RAG"])
async def rag_from_image(file: UploadFile = File(...)):
    """Exécute le pipeline RAG à partir d'une image.

    - Utilise un OCR local (Tesseract via pytesseract) pour extraire le texte de l'image.
    - Passe le texte extrait au RAG existant (même logique que /rag).
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image.")

    image_bytes = await file.read()
    text = ocr_service.extract_text(image_bytes)

    if not text:
        raise HTTPException(status_code=400, detail="Impossible d'extraire du texte depuis cette image.")

    result = rag_service.generate_answer_stream(text, top_k=5)
    summary = ""
    sources: list = []
    async for chunk in result:
        if chunk.get("type") == "summary_chunk":
            summary += chunk.get("text", "")
        elif chunk.get("type") == "sources":
            sources = chunk.get("sources", [])

    return {
        "summary": summary or "Mistral n'a pas pu générer de réponse.",
        "sources": sources,
        "query": text,
    }

@router.post("/rag/stream", summary="RAG streaming réel", tags=["RAG"])
async def rag_query_stream(payload: RAGRequest):
    """
    RAG avec streaming mot-à-mot. 
    C'est ici que la magie de Mistral opère en temps réel.
    """
    async def event_generator():
        try:
            first = True
            channel = getattr(payload, "channel", "web")
            async for chunk in rag_service.generate_answer_stream(payload.query, payload.top_k, channel=channel):
                yield json.dumps(chunk) + "\n"
                if first:
                    import sys
                    sys.stdout.flush()
                    first = False
        except Exception as e:
            logger.error(f"Streaming route error: {e}")
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


# ── Admin ────────────────────────────────────────────────────────────────────

class LoadRequest(BaseModel):
    limit: Optional[int] = None


@router.post("/admin/load", summary="Trigger dataset load (admin)", tags=["Admin"])
def admin_trigger_load(payload: LoadRequest, background_tasks: BackgroundTasks):
    if not (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or os.getenv("DB_HOST")):
        raise HTTPException(status_code=400, detail="Database credentials not found in environment.")

    background_tasks.add_task(
        load_and_insert,
        None,
        "bernard-ng/drc-news-corpus",
        EmbeddingService.DEFAULT_MODEL,
        payload.limit
    )
    return {"status": "scheduled"}
