#!/usr/bin/env python3
"""
Remplit les catégories manquantes pour les articles déjà en base.

1. Inférence depuis l'URL (rapide)
2. Option --fetch-html : re-télécharge la page et utilise articleCategories (sources.json)

Usage:
  cd ai-service && source venv/bin/activate
  python scripts/backfill_article_categories.py --dry-run
  python scripts/backfill_article_categories.py --limit 500
  python scripts/backfill_article_categories.py --fetch-html --limit 100
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import psycopg2
from bs4 import BeautifulSoup
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
os.chdir(_ROOT)

from app.services.crawler.source_catalog import get_source_config  # noqa: E402
from app.services.crawler.http.http_client import SyncHttpClient  # noqa: E402
from app.services.crawler.config import load_crawler_settings  # noqa: E402
from app.services.crawler.utils import infer_categories, resolve_article_categories  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill categories[] sur articles")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="0 = tous")
    parser.add_argument("--fetch-html", action="store_true", help="Re-fetch page (lent)")
    args = parser.parse_args()

    load_dotenv(_ROOT / ".env_file")
    load_dotenv(_ROOT / ".env")
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL manquant")
        return 1

    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    sql = """
        SELECT id, link, COALESCE(source_id, '')
        FROM articles
        WHERE categories IS NULL OR cardinality(categories) = 0
        ORDER BY id DESC
    """
    if args.limit and args.limit > 0:
        sql += f" LIMIT {int(args.limit)}"
    cur.execute(sql)
    rows = cur.fetchall()
    logger.info("Articles sans catégorie à traiter : %s", len(rows))

    http = SyncHttpClient(load_crawler_settings().http) if args.fetch_html else None
    updated = 0

    for article_id, link, source_id in rows:
        cats: list[str] = []
        if args.fetch_html and http and link:
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
                logger.warning("id=%s fetch fail: %s", article_id, exc)
        if not cats and link:
            cats = infer_categories(link)

        if not cats:
            continue

        if args.dry_run:
            logger.info("id=%s → %s | %s", article_id, cats, link[:80])
            updated += 1
            continue

        cur.execute(
            "UPDATE articles SET categories = %s::text[] WHERE id = %s",
            (cats, article_id),
        )
        updated += 1

    if not args.dry_run:
        conn.commit()
    cur.close()
    conn.close()
    logger.info("Terminé : %s article(s) avec catégorie proposée/mise à jour", updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
