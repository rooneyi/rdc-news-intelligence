import psycopg2
import os
import logging
from app.core.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DATABASE_URL

logger = logging.getLogger(__name__)


def get_db():
    """Backward-compatible alias that uses the smarter connection helper."""
    return get_db_connection()


def get_db_connection():
    """Smart connection getter - tries DATABASE_URL first, then individual params"""
    # Support full database URL (DATABASE_URL or DB_URL) first
    dsn = DATABASE_URL or os.getenv("DB_URL")
    if dsn:
        try:
            logger.debug("Connecting via DATABASE_URL/DB_URL")
            return psycopg2.connect(dsn)
        except Exception as e:
            logger.warning("Failed to connect using DATABASE_URL/DB_URL: %s", e)
            # Fall through to individual params

    # Fall back to individual parameters
    missing = []
    if not DB_HOST:
        missing.append("DB_HOST")
    if not DB_NAME:
        missing.append("DB_NAME")
    if not DB_USER:
        missing.append("DB_USER")
    if not DB_PASSWORD:
        missing.append("DB_PASSWORD")

    if missing:
        raise RuntimeError(
            f"Missing required database environment variables: {', '.join(missing)}. "
            "Set DATABASE_URL or all of DB_HOST, DB_NAME, DB_USER, DB_PASSWORD in your environment or .env file."
        )

    try:
        logger.debug("Connecting via individual params (DB_HOST, DB_USER, DB_NAME)")
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    except Exception as e:
        logger.error("Failed to connect to Postgres: %s", e)
        raise RuntimeError(f"Database connection failed: {e}")
