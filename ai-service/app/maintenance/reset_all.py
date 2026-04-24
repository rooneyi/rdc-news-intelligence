"""Maintenance script to wipe crawler data and reset the articles table.

Usage:
    python -m app.maintenance.reset_all

Requires DB env vars (.env/.env_file) and will drop + recreate the articles table.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.db.session import get_db_connection
from app.db.models import CREATE_TABLE_SQL, MIGRATE_TABLE_SQL
from app.services.crawler.config import load_crawler_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def reset_database() -> None:
    """Drop and recreate the articles table (clears all data)."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        logger.info("Dropping table training_runs (if exists)…")
        cur.execute("DROP TABLE IF EXISTS training_runs;")
        logger.info("Dropping table articles (if exists)…")
        cur.execute("DROP TABLE IF EXISTS articles;")

        logger.info("Recreating pgvector extension (idempotent)…")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        logger.info("Recreating articles table…")
        cur.execute(CREATE_TABLE_SQL)
        cur.execute(MIGRATE_TABLE_SQL)
        conn.commit()
        logger.info("Database reset completed: articles table is empty and schema recreated.")
    finally:
        cur.close()
        conn.close()


def clear_crawler_data() -> None:
    """Delete all local crawler JSONL files."""
    data_dir = Path(load_crawler_settings().data_dir)
    if data_dir.exists():
        logger.info("Removing crawler data directory: %s", data_dir)
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Crawler data directory recreated and empty: %s", data_dir)


if __name__ == "__main__":
    reset_database()
    clear_crawler_data()
    logger.info("Reset done. You can rerun the crawler from a clean state.")
