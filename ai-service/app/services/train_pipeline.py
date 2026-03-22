from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.db.session import get_db_connection
from app.services.embedding_service import EmbeddingService

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
    """Re-embed les articles nouveaux (ou tous si force_all) et rafraîchit l'index vectoriel."""
    conn = get_db_connection()
    cur = conn.cursor()
    model_to_use = model_name or EmbeddingService.DATASET_MODEL
    run_id = _start_run(cur, model_to_use, "re-embedding")
    conn.commit()

    processed = 0
    reembedded = 0
    try:
        cutoff = None if force_all else _get_last_success_timestamp(cur)
        if cutoff:
            cur.execute(
                "SELECT id, content FROM articles WHERE created_at > %s ORDER BY id",
                (cutoff,),
            )
        else:
            cur.execute("SELECT id, content FROM articles ORDER BY id")

        embedder = EmbeddingService(model_name=model_to_use)

        while True:
            rows = cur.fetchmany(batch_size)
            if not rows:
                break
            for article_id, content in rows:
                processed += 1
                embedding = embedder.generate(content)
                cur.execute(
                    "UPDATE articles SET embedding = %s WHERE id = %s",
                    (embedding, article_id),
                )
                reembedded += 1
            conn.commit()

        try:
            cur.execute("REINDEX INDEX IF EXISTS articles_embedding_idx;")
            conn.commit()
        except Exception as reindex_err:  # noqa: BLE001
            logger.warning("Reindex pgvector failed: %s", reindex_err)

        _finish_run(cur, run_id, processed, reembedded, "success", None)
        conn.commit()
        logger.info("Re-embedding terminé: processed=%s reembedded=%s", processed, reembedded)
        return {"processed": processed, "reembedded": reembedded, "run_id": run_id}
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        _finish_run(cur, run_id, processed, reembedded, "failed", str(exc))
        conn.commit()
        logger.error("Re-embedding failed: %s", exc)
        raise
    finally:
        cur.close()
        conn.close()


def run_finetune_stub(note: str | None = None) -> dict:
    """Placeholder pour du fine-tuning LLM. Loggue un run 'skipped'."""
    conn = get_db_connection()
    cur = conn.cursor()
    run_id = _start_run(cur, "fine-tune-placeholder", note or "fine-tune not implemented")
    _finish_run(cur, run_id, 0, 0, "skipped", note or "fine-tune not implemented")
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Fine-tuning placeholder enregistré (run_id=%s)", run_id)
    return {"run_id": run_id, "status": "skipped"}

