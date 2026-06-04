"""Remplissage des catégories manquantes sur les articles en base."""
from __future__ import annotations

import logging
from typing import Any

from bs4 import BeautifulSoup

from app.db.session import get_db_connection
from app.services.crawler.config import load_crawler_settings
from app.services.crawler.http.http_client import SyncHttpClient
from app.services.crawler.source_catalog import get_source_config
from app.services.crawler.utils import infer_categories, resolve_article_categories

logger = logging.getLogger(__name__)


def backfill_missing_categories(
    *,
    limit: int = 0,
    fetch_html: bool = False,
) -> dict[str, Any]:
    """
    Met à jour ``categories`` pour les articles où le tableau est vide ou NULL.

    Returns:
        dict avec scanned, updated, skipped
    """
    conn = get_db_connection()
    cur = conn.cursor()
    sql = """
        SELECT id, link, COALESCE(source_id, '')
        FROM articles
        WHERE categories IS NULL OR cardinality(categories) = 0
        ORDER BY id DESC
    """
    if limit and limit > 0:
        sql += f" LIMIT {int(limit)}"
    cur.execute(sql)
    rows = cur.fetchall()
    scanned = len(rows)
    updated = 0
    skipped = 0

    http = SyncHttpClient(load_crawler_settings().http) if fetch_html else None

    try:
        for article_id, link, source_id in rows:
            cats: list[str] = []
            if fetch_html and http and link:
                try:
                    cfg = get_source_config(source_id)
                    resp = http.get(link)
                    soup = BeautifulSoup(resp.text, "lxml")
                    cats = resolve_article_categories(
                        link,
                        soup,
                        css_selector=cfg.article_categories_selector if cfg else None,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("[Categories] id=%s fetch fail: %s", article_id, exc)
            if not cats and link:
                cats = infer_categories(link)

            if not cats:
                skipped += 1
                continue

            cur.execute(
                "UPDATE articles SET categories = %s::text[] WHERE id = %s",
                (cats, article_id),
            )
            updated += 1

        conn.commit()
        logger.info(
            "[Categories] Backfill terminé scanned=%s updated=%s skipped=%s",
            scanned,
            updated,
            skipped,
        )
        return {"scanned": scanned, "updated": updated, "skipped": skipped}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
