from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import json
import logging
import time
from pathlib import Path
from app.services.article_service import create_article, search_similar, save_crawled_article
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RAGService
from app.services.ocr_service import OCRService
from app.services.load_dataset import load_and_insert
from app.schemas.article import ArticleCreate, ArticleOut, RAGRequest, RAGResponse
from app.services.crawler.models import Article as CrawlerArticle
from app.db.session import get_db
from pydantic import BaseModel, Field
from typing import Optional, List

from app.services.crawler.admin_runner import (
    get_crawler_job_state,
    is_crawler_running,
    schedule_crawler_job,
)
import os

from app.services.vector_store_service import VectorStoreService

router = APIRouter()
logger = logging.getLogger(__name__)

vector_store_service = VectorStoreService()

_SOURCES_JSON = Path(__file__).resolve().parents[3] / "data" / "crawler" / "sources.json"


_LANG_LABELS = {
    "fr": "Français",
    "en": "Anglais",
    "sw": "Swahili",
    "unknown": "Non classé",
}


def _source_lang_map() -> dict[str, str]:
    """sourceId → fr | en | sw (défaut fr si absent du catalogue)."""
    if not _SOURCES_JSON.exists():
        return {}
    try:
        with _SOURCES_JSON.open(encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Impossible de lire %s: %s", _SOURCES_JSON, exc)
        return {}
    out: dict[str, str] = {}
    for section in ("html", "wordpress"):
        for item in data.get("sources", {}).get(section, []) or []:
            sid = item.get("sourceId")
            if not isinstance(sid, str) or not sid.strip():
                continue
            raw = (item.get("sourceLang") or "fr").strip().lower()
            out[sid.strip()] = raw if raw in ("en", "sw", "fr") else "fr"
    return out


def _crawler_catalog_source_ids() -> list[str]:
    """Identifiants déclarés dans data/crawler/sources.json (ordre du fichier, sans doublon)."""
    if not _SOURCES_JSON.exists():
        return []
    try:
        with _SOURCES_JSON.open(encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Impossible de lire %s: %s", _SOURCES_JSON, exc)
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for section in ("html", "wordpress"):
        for item in data.get("sources", {}).get(section, []) or []:
            sid = item.get("sourceId")
            if isinstance(sid, str) and sid.strip() and sid not in seen:
                seen.add(sid)
                ordered.append(sid.strip())
    return ordered


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
    logger.info(
        "[RAG] ← req channel=%s top_k=%s query=%r",
        channel,
        payload.top_k,
        (payload.query or "")[:500],
    )

    t0 = time.perf_counter()
    result = rag_service.generate_answer_stream(payload.query, payload.top_k, channel=channel)
    summary = ""
    sources = []
    pipeline_error = False
    async for chunk in result:
        if chunk.get("type") == "summary_chunk":
            summary += chunk.get("text", "")
        elif chunk.get("type") == "sources":
            sources = chunk.get("sources", [])
        elif chunk.get("type") == "error":
            summary = chunk.get("message") or summary
            pipeline_error = True

    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "[RAG] → res %.1fms chars=%s sources=%s erreur_pipeline=%s",
        elapsed_ms,
        len(summary),
        len(sources),
        pipeline_error,
    )
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
        elif chunk.get("type") == "error":
            summary = chunk.get("message") or summary

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
        channel = getattr(payload, "channel", "web")
        q_preview = (payload.query or "")[:500]
        t0 = time.perf_counter()
        ndjson_lines = 0
        last_event: str | None = None
        saw_error = False
        logger.info(
            "[RAG/stream] ← req channel=%s top_k=%s query=%r",
            channel,
            payload.top_k,
            q_preview,
        )
        try:
            first = True
            async for chunk in rag_service.generate_answer_stream(payload.query, payload.top_k, channel=channel):
                last_event = chunk.get("type")
                if last_event == "error":
                    saw_error = True
                ndjson_lines += 1
                yield json.dumps(chunk) + "\n"
                if first:
                    import sys

                    sys.stdout.flush()
                    first = False
        except Exception as e:
            logger.exception("[RAG/stream] exception dans le générateur: %s", e)
            saw_error = True
            last_event = "error"
            ndjson_lines += 1
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                "[RAG/stream] → fin %.1fms lignes_ndjson=%s dernier_event=%s erreur=%s",
                elapsed_ms,
                ndjson_lines,
                last_event,
                saw_error,
            )

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


# ── Admin ────────────────────────────────────────────────────────────────────

class LoadRequest(BaseModel):
    limit: Optional[int] = None


class CrawlerRunRequest(BaseModel):
    source_id: str = Field(default="all", description="ID source ou « all »")
    limit: int = Field(default=30, ge=1, le=200)
    page_range: Optional[str] = Field(
        default=None,
        description="Plage de pages listing, ex. 1:3",
    )
    run_reembedding: bool = Field(
        default=True,
        description="Lancer le re-embedding Chroma après le crawl",
    )


@router.post("/admin/memory/flush", summary="Vider la mémoire conversationnelle Redis", tags=["Admin"])
async def admin_memory_flush():
    from app.services.memory_service import ConversationalMemoryService

    svc = ConversationalMemoryService()
    deleted = await svc.flush_all()
    return {"status": "ok", "keys_deleted": deleted}


@router.get("/admin/crawler/status", summary="État du dernier crawl admin", tags=["Admin"])
def admin_crawler_status():
    return {"status": "ok", "job": get_crawler_job_state()}


@router.post("/admin/crawler/run", summary="Lancer le crawler (admin)", tags=["Admin"])
def admin_crawler_run(payload: CrawlerRunRequest):
    if is_crawler_running():
        raise HTTPException(
            status_code=409,
            detail="Un crawl est déjà en cours. Consultez GET /admin/crawler/status.",
        )
    if not schedule_crawler_job(
        source_id=payload.source_id.strip() or "all",
        limit=payload.limit,
        page_range=(payload.page_range or "").strip() or None,
        run_reembedding_after=payload.run_reembedding,
        trigger="admin",
    ):
        raise HTTPException(status_code=409, detail="Impossible de démarrer le crawl.")
    return {
        "status": "started",
        "message": "Crawl démarré en arrière-plan.",
        "job": get_crawler_job_state(),
    }


@router.get("/admin/overview", summary="Admin overview stats", tags=["Admin"])
def admin_overview():
    """
    Retourne des stats réelles pour la console admin frontend.
    """
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM articles")
        total_articles = int(cur.fetchone()[0] or 0)

        # On compte les articles dans ChromaDB plutôt que Postgres
        embedded_articles = vector_store_service.collection.count()

        cur.execute("SELECT COUNT(DISTINCT COALESCE(source_id, 'unknown')) FROM articles")
        total_sources = int(cur.fetchone()[0] or 0)

        cur.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(source_id), ''), 'unknown') AS source, COUNT(*) AS n
            FROM articles
            GROUP BY source
            """
        )
        counts_map: dict[str, int] = {}
        for row in cur.fetchall():
            counts_map[row[0]] = int(row[1])

        sorted_by_volume = sorted(counts_map.items(), key=lambda x: -x[1])
        top_sources = [{"source": k, "count": v} for k, v in sorted_by_volume[:6]]

        catalog_ids = _crawler_catalog_source_ids()
        breakdown: list[dict] = []
        catalog_set = set(catalog_ids)
        for sid in catalog_ids:
            breakdown.append(
                {
                    "source": sid,
                    "count": counts_map.get(sid, 0),
                    "in_catalog": True,
                }
            )
        for sid, n in sorted_by_volume:
            if sid not in catalog_set:
                breakdown.append({"source": sid, "count": n, "in_catalog": False})
        breakdown.sort(key=lambda x: (-x["count"], x["source"]))

        cur.execute(
            """
            SELECT id, title, COALESCE(source_id, 'unknown') AS source, COALESCE(link, '') AS link
            FROM articles
            ORDER BY id DESC
            LIMIT 8
            """
        )
        latest_articles = [
            {
                "id": int(row[0]),
                "title": row[1],
                "source": row[2],
                "link": row[3],
            }
            for row in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT COUNT(*) FROM articles
            WHERE source_id IS NULL OR source_id = ''
            """
        )
        missing_source = int(cur.fetchone()[0] or 0)

        cur.execute(
            """
            SELECT COUNT(*) FROM articles
            WHERE link IS NULL OR link = ''
            """
        )
        missing_link = int(cur.fetchone()[0] or 0)

        return {
            "status": "ok",
            "stats": {
                "total_articles": total_articles,
                "embedded_articles": embedded_articles,
                "total_sources": total_sources,
                "catalog_sources_configured": len(catalog_ids),
                "embedding_coverage": round((embedded_articles / total_articles) * 100, 2)
                if total_articles
                else 0.0,
                "missing_source_articles": missing_source,
                "missing_link_articles": missing_link,
            },
            "top_sources": top_sources,
            "sources_breakdown": breakdown,
            "latest_articles": latest_articles,
        }
    finally:
        cur.close()
        conn.close()


def _article_row_to_dict(row) -> dict:
    return {
        "id": int(row[0]),
        "title": row[1] or "",
        "source": row[2] or "unknown",
        "link": row[3] or "",
        "categories": row[4] if row[4] else [],
    }


@router.get("/admin/corpus", summary="Corpus: langues, catégories, échantillons", tags=["Admin"])
def admin_corpus():
    """
    Statistiques détaillées du corpus : langues (via source_id / sources.json),
    catégories PostgreSQL, sources, qualité et extraits d'articles.
    """
    lang_map = _source_lang_map()
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM articles")
        total = int(cur.fetchone()[0] or 0)
        embedded = vector_store_service.collection.count()

        cur.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(source_id), ''), 'unknown') AS source, COUNT(*) AS n
            FROM articles
            GROUP BY source
            """
        )
        source_counts = {row[0]: int(row[1]) for row in cur.fetchall()}

        lang_counts: dict[str, int] = {"fr": 0, "en": 0, "sw": 0, "unknown": 0}
        lang_sources: dict[str, list[dict]] = {k: [] for k in lang_counts}
        for sid, n in sorted(source_counts.items(), key=lambda x: -x[1]):
            if not sid or sid == "unknown":
                lang = "unknown"
            else:
                lang = lang_map.get(sid, "fr")
            lang_counts[lang] = lang_counts.get(lang, 0) + n
            lang_sources.setdefault(lang, []).append({"source": sid, "count": n})

        languages = []
        for code in ("fr", "en", "sw", "unknown"):
            n = lang_counts.get(code, 0)
            languages.append(
                {
                    "code": code,
                    "label": _LANG_LABELS[code],
                    "count": n,
                    "percent": round((n / total) * 100, 2) if total else 0.0,
                    "sources": lang_sources.get(code, [])[:12],
                }
            )

        cur.execute(
            """
            SELECT cat, COUNT(*)::int AS n
            FROM (
                SELECT unnest(categories) AS cat
                FROM articles
                WHERE categories IS NOT NULL AND cardinality(categories) > 0
            ) expanded
            GROUP BY cat
            ORDER BY n DESC
            """
        )
        category_rows = cur.fetchall()

        cur.execute(
            """
            SELECT COUNT(*)::int FROM articles
            WHERE categories IS NULL
               OR cardinality(categories) = 0
            """
        )
        without_category = int(cur.fetchone()[0] or 0)

        categories = [
            {
                "name": row[0],
                "count": int(row[1]),
                "percent": round((int(row[1]) / total) * 100, 2) if total else 0.0,
            }
            for row in category_rows
        ]
        if without_category:
            categories.append(
                {
                    "name": "(sans catégorie)",
                    "count": without_category,
                    "percent": round((without_category / total) * 100, 2) if total else 0.0,
                }
            )

        cur.execute(
            """
            SELECT COUNT(*)::int FROM articles
            WHERE source_id IS NULL OR TRIM(source_id) = ''
            """
        )
        missing_source = int(cur.fetchone()[0] or 0)
        cur.execute(
            """
            SELECT COUNT(*)::int FROM articles
            WHERE link IS NULL OR TRIM(link) = ''
            """
        )
        missing_link = int(cur.fetchone()[0] or 0)

        def _samples_for_lang(lang_code: str, limit: int = 5) -> list[dict]:
            if lang_code == "unknown":
                known = set(lang_map.keys())
                if not known:
                    cur.execute(
                        """
                        SELECT id, title, COALESCE(source_id, 'unknown'), COALESCE(link, ''),
                               COALESCE(categories, '{}')
                        FROM articles
                        ORDER BY id DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                else:
                    placeholders = ",".join(["%s"] * len(known))
                    cur.execute(
                        f"""
                        SELECT id, title, COALESCE(source_id, 'unknown'), COALESCE(link, ''),
                               COALESCE(categories, '{{}}')
                        FROM articles
                        WHERE source_id IS NULL
                           OR TRIM(source_id) = ''
                           OR source_id NOT IN ({placeholders})
                        ORDER BY id DESC
                        LIMIT %s
                        """,
                        (*known, limit),
                    )
            else:
                ids = [s for s, lg in lang_map.items() if lg == lang_code]
                if not ids:
                    return []
                placeholders = ",".join(["%s"] * len(ids))
                cur.execute(
                    f"""
                    SELECT id, title, COALESCE(source_id, 'unknown'), COALESCE(link, ''),
                           COALESCE(categories, '{{}}')
                    FROM articles
                    WHERE source_id IN ({placeholders})
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (*ids, limit),
                )
            return [_article_row_to_dict(r) for r in cur.fetchall()]

        def _samples_for_category(cat_name: str, limit: int = 5) -> list[dict]:
            if cat_name == "(sans catégorie)":
                cur.execute(
                    """
                    SELECT id, title, COALESCE(source_id, 'unknown'), COALESCE(link, ''),
                           COALESCE(categories, '{}')
                    FROM articles
                    WHERE categories IS NULL OR cardinality(categories) = 0
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            else:
                cur.execute(
                    """
                    SELECT id, title, COALESCE(source_id, 'unknown'), COALESCE(link, ''),
                           COALESCE(categories, '{}')
                    FROM articles
                    WHERE %s = ANY(categories)
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (cat_name, limit),
                )
            return [_article_row_to_dict(r) for r in cur.fetchall()]

        for lang in languages:
            if lang["count"] > 0:
                lang["samples"] = _samples_for_lang(lang["code"], 5)

        for cat in categories[:8]:
            cat["samples"] = _samples_for_category(cat["name"], 4)

        catalog_ids = _crawler_catalog_source_ids()
        catalog_set = set(catalog_ids)
        sources_breakdown = []
        for sid in catalog_ids:
            sources_breakdown.append(
                {"source": sid, "count": source_counts.get(sid, 0), "in_catalog": True}
            )
        for sid, n in sorted(source_counts.items(), key=lambda x: -x[1]):
            if sid not in catalog_set:
                sources_breakdown.append(
                    {"source": sid, "count": n, "in_catalog": False}
                )
        sources_breakdown.sort(key=lambda x: (-x["count"], x["source"]))

        return {
            "status": "ok",
            "stats": {
                "total_articles": total,
                "embedded_articles": embedded,
                "embedding_coverage": round((embedded / total) * 100, 2) if total else 0.0,
                "distinct_categories": len(category_rows),
                "catalog_sources": len(catalog_ids),
                "missing_source_articles": missing_source,
                "missing_link_articles": missing_link,
            },
            "languages": languages,
            "categories": categories,
            "sources_breakdown": sources_breakdown,
        }
    finally:
        cur.close()
        conn.close()


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
