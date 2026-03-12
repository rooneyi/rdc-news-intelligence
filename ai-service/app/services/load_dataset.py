from datasets import load_dataset
from sentence_transformers import SentenceTransformer
import psycopg2
import os
from dotenv import load_dotenv
import asyncio
import logging
from typing import Optional

# Load environment variables (if not already loaded by app/main.py)
# This ensures the script works both standalone and within the app
if not os.getenv("DB_HOST"):
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env_file")
    if not os.path.exists(dotenv_path):
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    load_dotenv(dotenv_path=dotenv_path)

from app.core.config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DATABASE_URL

logger = logging.getLogger(__name__)

# Helper to get a DB connection; raises a clear error if credentials are missing
def get_db_connection():
    # Support a full database URL (e.g. DATABASE_URL or DB_URL) or individual params
    dsn = DATABASE_URL or os.getenv("DB_URL")
    if dsn:
        try:
            return psycopg2.connect(dsn)
        except Exception as e:
            raise RuntimeError(f"Failed to connect using DATABASE_URL/DB_URL: {e}")

    host = DB_HOST
    database = DB_NAME
    user = DB_USER
    password = DB_PASSWORD

    missing = [k for k, v in (("DB_HOST", host), ("DB_NAME", database), ("DB_USER", user), ("DB_PASSWORD", password)) if not v]
    if missing:
        raise RuntimeError(
            "Missing required database environment variables: " + ", ".join(missing) +
            ".\nSet DATABASE_URL or all of DB_HOST, DB_NAME, DB_USER, DB_PASSWORD in your environment or .env file."
        )

    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        return conn
    except Exception as e:
        raise RuntimeError(f"Failed to connect to Postgres: {e}")


def insert_article(cursor, title, content, embedding):
    cursor.execute(
        """
        INSERT INTO articles (title, content, embedding)
        VALUES (%s, %s, %s)
        """,
        (title, content, embedding)
    )


def load_and_insert(
    conn: Optional[psycopg2.extensions.connection] = None,
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
        logger.info("Starting dataset load: %s", dataset_name)
        dataset = load_dataset(dataset_name)

        logger.info("Loading embedding model: %s", model_name)
        model = SentenceTransformer(model_name)

        for i, item in enumerate(dataset["train"]):
            if limit is not None and i >= limit:
                break

            title = item.get("title", "")
            content = item.get("body") or item.get("text", "")

            if not content:
                continue

            embedding = model.encode(content).tolist()
            insert_article(cursor, title, content, embedding)
            inserted += 1

            if inserted % commit_every == 0:
                conn.commit()
                logger.info("Committed %d rows so far", inserted)

        conn.commit()
        logger.info("Completed dataset import. Total inserted: %d", inserted)
        return inserted

    except Exception as e:
        logger.exception("Error while loading dataset: %s", e)
        raise

    finally:
        cursor.close()
        if own_conn and conn is not None:
            conn.close()


def attach_to_app(app, *, background: bool = True, **load_kwargs):
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
