from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.db.session import get_db_connection
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.schemas.article import ArticleOut

logger = logging.getLogger(__name__)


def _get_last_success_timestamp(cur) -> Optional[datetime]:
    cur.execute("SELECT MAX(ended_at) FROM training_runs WHERE status = 'success'")
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def _start_run(cur, model_name: str, note: str | None) -> int:
    cur.execute(
        "INSERT INTO training_runs (status, model_name, note) VALUES ('running', %s, %s) RETURNING id",
        (model_name, note),
    )
    run_id = cur.fetchone()[0]
    return run_id


def _finish_run(cur, run_id: int, processed: int, reembedded: int, status: str, note: str | None) -> None:
    cur.execute(
        """
        UPDATE training_runs
        SET ended_at = CURRENT_TIMESTAMP,
            status = %s,
            processed_count = %s,
            reembedded_count = %s,
            note = %s
        WHERE id = %s
        """,
        (status, processed, reembedded, note, run_id),
    )


def run_reembedding(batch_size: int = 50, force_all: bool = False, model_name: Optional[str] = None) -> dict:
    """Re-embed les articles nouveaux (ou tous si force_all) et synchronise ChromaDB."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    model_to_use = model_name or EmbeddingService.DATASET_MODEL
    run_id = _start_run(cur, model_to_use, "re-embedding (ChromaDB)")
    conn.commit()

    processed = 0
    reembedded = 0
    try:
        # 1. On récupère les articles avec leurs metadata pour ChromaDB
        cutoff = None if force_all else _get_last_success_timestamp(cur)
        query = "SELECT id, title, content, link, source_id, hash, categories, image FROM articles"
        if cutoff:
            cur.execute(query + " WHERE created_at > %s", (cutoff,))
        else:
            cur.execute(query)
        
        all_articles_rows = cur.fetchall()
        total_to_process = len(all_articles_rows)
        logger.info(f"Found {total_to_process} articles to re-embed and sync to ChromaDB")

        embedder = EmbeddingService(model_name=model_to_use)
        vector_store = VectorStoreService()

        articles_batch = []
        embeddings_batch = []

        # 2. On traite les articles
        for row in all_articles_rows:
            processed += 1
            article_id, title, content, link, source_id, hash_val, categories, image = row
            
            try:
                embedding = embedder.generate(content)
                
                article_out = ArticleOut(
                    id=article_id,
                    title=title,
                    content=content,
                    link=link,
                    source_id=source_id,
                    hash=hash_val,
                    categories=categories or [],
                    image=image
                )
                
                articles_batch.append(article_out)
                embeddings_batch.append(embedding)
                reembedded += 1
            except Exception as e:
                logger.error(f"Failed to embed article {article_id}: {e}")
            
            if len(articles_batch) >= batch_size:
                vector_store.add_articles(articles_batch, embeddings_batch)
                articles_batch = []
                embeddings_batch = []
                logger.info(f"Progress: {processed}/{total_to_process} articles processed and synced...")

        # Final sync pour le dernier batch
        if articles_batch:
            vector_store.add_articles(articles_batch, embeddings_batch)

        _finish_run(cur, run_id, processed, reembedded, "success", None)
        conn.commit()
        logger.info("Re-embedding et sync ChromaDB terminé: processed=%s reembedded=%s", processed, reembedded)
        return {"processed": processed, "reembedded": reembedded, "run_id": run_id}
    except Exception as exc:
        conn.rollback()
        _finish_run(cur, run_id, processed, reembedded, "failed", str(exc))
        conn.commit()
        logger.error("Re-embedding/Sync failed: %s", exc)
        raise
    finally:
        cur.close()
        conn.close()


def run_finetune_stub(note: str | None = None) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    run_id = _start_run(cur, "fine-tune-placeholder", note or "fine-tune not implemented")
    _finish_run(cur, run_id, 0, 0, "skipped", note or "fine-tune not implemented")
    conn.commit()
    cur.close()
    conn.close()
    return {"run_id": run_id, "status": "skipped"}
