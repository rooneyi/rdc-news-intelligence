from datasets import load_dataset
import os
import asyncio
import logging
from typing import Optional

# Variables d'environnement déjà chargées via app.core.config
from app.core.config import DATABASE_URL
from app.db.session import get_db_connection

logger = logging.getLogger(__name__)



def load_and_insert(
    conn: Optional[object] = None,
    dataset_name: str = "bernard-ng/drc-news-corpus",
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    limit: Optional[int] = None,
    commit_every: int = 500,
):
    """
    Blocking function that downloads the dataset and model and inserts rows into the database.
    - If conn is None, it will create a new connection using environment variables.
    - limit can be used to limit the number of rows (useful for testing).
    - commit_every batches commits for performance.
    """
    own_conn = False
    if conn is None:
        conn = get_db_connection()
        own_conn = True

    cursor = conn.cursor()
    inserted = 0

    try:
        logger.info(f"Starting dataset load: {dataset_name}")
        dataset = load_dataset(dataset_name)

        # Utiliser le service d'embedding pour cohérence
        from app.services.embedding_service import EmbeddingService
        embedding_service = EmbeddingService(model_name=model_name)

        logger.info(f"Using embedding model: {model_name}")

        for i, item in enumerate(dataset["train"]):
            if limit is not None and i >= limit:
                break

            title = item.get("title", "")
            content = item.get("body") or item.get("text", "")

            if not content:
                continue

            embedding = embedding_service.generate(content)
            cursor.execute(
                "INSERT INTO articles (title, content, embedding) VALUES (%s, %s, %s)",
                (title, content, embedding)
            )
            inserted += 1

            if inserted % commit_every == 0:
                conn.commit()
                logger.info(f"Committed {inserted} rows so far")

        conn.commit()
        logger.info(f"Completed dataset import. Total inserted: {inserted}")
        return inserted

    except Exception as e:
        logger.exception(f"Error while loading dataset: {e}")
        raise

    finally:
        cursor.close()
        if own_conn and conn is not None:
            conn.close()


def attach_to_app(app, *, background: bool = True, **load_kwargs):
    if os.getenv("DISABLE_DATASET_AUTOLOAD", "").lower() in {"1", "true", "yes"}:
        logger.info("Dataset autoload disabled by DISABLE_DATASET_AUTOLOAD")
        return
    if not (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or os.getenv("DB_HOST")):
        logger.warning("Database credentials not found in environment; dataset load will be skipped on startup.\nSet DATABASE_URL or DB_HOST/DB_USER/DB_PASSWORD to enable automatic loading.")
        return

    dataset_name = load_kwargs.get("dataset_name", "bernard-ng/drc-news-corpus")
    model_name = load_kwargs.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")
    limit = load_kwargs.get("limit", None)
    commit_every = load_kwargs.get("commit_every", 500)

    if background:
        @app.on_event("startup")
        async def _startup_load_background():
            # schedule blocking work in a threadpool
            loop = asyncio.get_running_loop()
            logger.info("Scheduling dataset load in background (startup)")
            # we intentionally don't await so the app can start
            loop.run_in_executor(None, load_and_insert, None, dataset_name, model_name, limit, commit_every)

    else:
        @app.on_event("startup")
        async def _startup_load_blocking():
            logger.info("Running dataset load during startup (blocking)")
            # run in threadpool and await so startup waits for completion
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, load_and_insert, None, dataset_name, model_name, limit, commit_every)

if __name__ == "__main__":
    # Limit for quick testing
    logging.basicConfig(level=logging.INFO)
    load_and_insert(limit=10)
