"""
Script CLI sync pour lancer le crawler de manière synchrone.

Usage:
    python -m app.services.crawler.scripts.sync --source-id radiookapi.net
    python -m app.services.crawler.scripts.sync --source-id radiookapi.net --page-range 1:3
    python -m app.services.crawler.scripts.sync --source-id mediacongo.net --limit 5
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from app.services.crawler.config import load_crawler_settings
from app.services.crawler.http.http_client import SyncHttpClient
from app.services.crawler.http.open_graph import OpenGraphParser
from app.services.crawler.process.crawler import SyncCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Sources connues avec leurs URLs de listing
KNOWN_SOURCES = {
    "radiookapi.net": {
        "base_url": "https://radiookapi.net",
        "listing_url": "https://radiookapi.net/actualite/",
        "article_selector": "article a[href], .post-title a, h2 a, h3 a",
    },
    "mediacongo.net": {
        "base_url": "https://mediacongo.net",
        "listing_url": "https://www.mediacongo.net/dpics/actualite.html",
        "article_selector": "article a[href], .titre a, h2 a",
    },
}


def get_article_urls(source_id: str, page_range: Optional[str], limit: Optional[int]) -> list[str]:
    """Récupère la liste d'URLs d'articles à crawler."""
    from bs4 import BeautifulSoup
    from app.services.crawler.config import load_crawler_settings
    from app.services.crawler.http.http_client import SyncHttpClient

    settings = load_crawler_settings()
    client = SyncHttpClient(settings.http)

    source = KNOWN_SOURCES.get(source_id)
    if not source:
        logger.error("Source inconnue: %s. Sources disponibles: %s", source_id, list(KNOWN_SOURCES.keys()))
        sys.exit(1)

    # Déterminer les pages à crawler
    start_page, end_page = 1, 3
    if page_range:
        parts = page_range.split(":")
        start_page = int(parts[0])
        end_page = int(parts[1]) if len(parts) > 1 else start_page

    urls = []
    base_url = source["base_url"]
    listing_url = source["listing_url"]
    selector = source["article_selector"]

    for page in range(start_page, end_page + 1):
        try:
            page_url = listing_url if page == 1 else f"{listing_url}?page={page}"
            logger.info("Fetching listing page %d: %s", page, page_url)
            resp = client.get(page_url)
            soup = BeautifulSoup(resp.text, "lxml")
            links = soup.select(selector)

            for link in links:
                href = link.get("href", "")
                if not href:
                    continue
                if href.startswith("http"):
                    full_url = href
                else:
                    full_url = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                if full_url not in urls:
                    urls.append(full_url)

            if limit and len(urls) >= limit:
                urls = urls[:limit]
                break

        except Exception as exc:
            logger.warning("Erreur page %d: %s", page, exc)
            continue

    logger.info("Total URLs trouvées: %d", len(urls))
    return urls


def main() -> int:
    parser = argparse.ArgumentParser(description="RDC News Crawler - Mode Sync")
    parser.add_argument("--source-id", required=True, help="ID de la source (ex: radiookapi.net)")
    parser.add_argument("--page-range", help="Pages à crawler (ex: 1:5)", default=None)
    parser.add_argument("--limit", type=int, help="Limite d'articles", default=None)
    parser.add_argument("--category", help="Catégorie à filtrer", default=None)
    args = parser.parse_args()

    logger.info("=== Démarrage du crawler sync ===")
    logger.info("Source: %s | Pages: %s | Limite: %s", args.source_id, args.page_range, args.limit)

    try:
        settings = load_crawler_settings()
        logger.info("Data dir: %s", settings.data_dir)
        logger.info("Backend: %s", settings.backend_endpoint or "non configuré (JSONL seulement)")

        # Récupérer les URLs
        urls = get_article_urls(args.source_id, args.page_range, args.limit)

        if not urls:
            logger.warning("Aucune URL trouvée pour la source %s", args.source_id)
            return 1

        # Lancer le crawl
        crawler = SyncCrawler(settings=settings)
        articles = crawler.crawl_urls(urls, source_id=args.source_id)

        logger.info("=== Terminé: %d articles crawlés ===", len(articles))
        logger.info("Fichier JSONL: %s/%s.jsonl", settings.data_dir, args.source_id)
        return 0

    except KeyboardInterrupt:
        logger.info("Interrompu par l'utilisateur.")
        return 1
    except Exception as exc:
        logger.exception("Erreur fatale: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

