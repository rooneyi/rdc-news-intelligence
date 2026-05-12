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
import json
from pathlib import Path
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
        "categories": None,
    },
    "mediacongo.net": {
        "base_url": "https://mediacongo.net",
        "listing_url": "https://www.mediacongo.net/dpics/actualite.html",
        "article_selector": "article a[href], .titre a, h2 a",
        "categories": None,
    },
}

SOURCES_FILE = Path(__file__).resolve().parents[4] / "data" / "crawler" / "sources.json"


def _is_probable_syndication_feed(markup: str) -> bool:
    head = (markup or "")[:4000].lower()
    return any(
        x in head
        for x in (
            "<rss",
            "<feed",
            "rdf:rdf",
            "xmlns=\"http://purl.org/rss",
            "<!-- generator: wordpress",
        )
    )


def _urls_from_feed_markup(markup: str) -> list[str]:
    """
    Extrait les URLs d'articles depuis un flux RSS 2, Atom, ou RDF (ex. DW).
    """
    if not _is_probable_syndication_feed(markup):
        return []
    from bs4 import BeautifulSoup

    try:
        soup = BeautifulSoup(markup, "xml")
    except Exception:  # noqa: BLE001
        soup = BeautifulSoup(markup, "lxml")

    urls: list[str] = []
    for item in soup.find_all("item"):
        link_el = item.find("link")
        href = ""
        if link_el is not None:
            href = (link_el.string or link_el.get_text(strip=True) or link_el.get("href") or "").strip()
        if not href:
            guid = item.find("guid")
            if guid and guid.string:
                t = guid.string.strip()
                if t.startswith("http"):
                    href = t
        if href.startswith("http") and href not in urls:
            urls.append(href)

    if not urls:
        for entry in soup.find_all("entry"):
            for link_el in entry.find_all("link"):
                href = (link_el.get("href") or "").strip()
                if href.startswith("http"):
                    urls.append(href)
                    break
    return urls


def _load_sources_from_file(path: Path = SOURCES_FILE) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        sources = {}
        for item in data.get("sources", {}).get("html", []):
            source_id = item.get("sourceId")
            if not source_id:
                continue
            base_url = item.get("sourceUrl", "").rstrip("/")
            pagination = (item.get("paginationTemplate") or "").lstrip("/")
            listing_url = f"{base_url}/{pagination}" if pagination else base_url
            selector = item.get("sourceSelectors", {}).get("articleLink") or "a"
            sources[source_id] = {
                "base_url": base_url,
                "listing_url": listing_url,
                "article_selector": selector,
                "categories": item.get("categories"),
                "supports_categories": item.get("supportsCategories", False),
            }
        # WordPress entries have no selectors; still include so we can hit their feed endpoints later if needed
        for item in data.get("sources", {}).get("wordpress", []):
            source_id = item.get("sourceId")
            if not source_id:
                continue
            base_url = item.get("sourceUrl", "").rstrip("/")
            rss_url = (item.get("rssUrl") or "").strip()
            fp = item.get("feedPath")
            if fp is None or str(fp).strip() == "":
                feed_suffix = "/feed"
            else:
                fp_s = str(fp).strip()
                feed_suffix = fp_s if fp_s.startswith("/") else f"/{fp_s}"
            listing_url = rss_url if rss_url else f"{base_url}{feed_suffix}"
            sources[source_id] = {
                "base_url": base_url,
                "listing_url": listing_url,
                "article_selector": "a",
                "categories": None,
                "supports_categories": False,
            }
        return sources
    except Exception as exc:  # noqa: BLE001
        logger.warning("Impossible de charger %s: %s", path, exc)
        return {}


# Fusionne les sources du JSON avec les sources codées
KNOWN_SOURCES.update(_load_sources_from_file())


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

    start_page, end_page = 1, 3
    if page_range:
        parts = page_range.split(":")
        start_page = int(parts[0])
        end_page = int(parts[1]) if len(parts) > 1 else start_page

    urls = []
    base_url = source["base_url"]
    listing_url = source["listing_url"]
    selector = source.get("article_selector") or "a"
    categories = source.get("categories") if source.get("supports_categories") else [None]

    for category in categories or [None]:
        for page in range(start_page, end_page + 1):
            try:
                # Si paginationTemplate contient {category}, on l'a déjà injecté lors du build; sinon, on utilise query param
                page_url = listing_url
                if category:
                    page_url = listing_url.replace("{category}", category)
                page_url = page_url if page == 1 else f"{page_url}?page={page}"

                logger.info("Fetching listing page %d: %s", page, page_url)
                resp = client.get(page_url)
                text = resp.text
                soup = BeautifulSoup(text, "lxml")
                page_urls: list[str] = []
                for link in soup.select(selector):
                    href = link.get("href", "")
                    if not href:
                        continue
                    full_url = href if href.startswith("http") else f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                    if full_url not in page_urls:
                        page_urls.append(full_url)

                if not page_urls:
                    page_urls = _urls_from_feed_markup(text)

                for full_url in page_urls:
                    if full_url not in urls:
                        urls.append(full_url)

                if limit and len(urls) >= limit:
                    urls = urls[:limit]
                    break

            except Exception as exc:  # noqa: BLE001
                logger.warning("Erreur page %d: %s", page, exc)
                continue

    logger.info("Total URLs trouvées: %d", len(urls))
    return urls


def main() -> int:
    parser = argparse.ArgumentParser(description="RDC News Crawler - Mode Sync")
    parser.add_argument("--source-id", required=True, help="ID de la source (ex: radiookapi.net ou 'all' pour toutes)")
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

        source_ids = list(KNOWN_SOURCES.keys()) if args.source_id == "all" else [args.source_id]

        total_articles = 0
        for sid in source_ids:
            logger.info("--- Source: %s ---", sid)
            urls = get_article_urls(sid, args.page_range, args.limit)
            if not urls:
                logger.warning("Aucune URL trouvée pour la source %s", sid)
                continue
            crawler = SyncCrawler(settings=settings)
            articles = crawler.crawl_urls(urls, source_id=sid)
            logger.info("=== Terminé: %d articles crawlés pour %s ===", len(articles), sid)
            logger.info("Fichier JSONL: %s/%s.jsonl", settings.data_dir, sid)
            total_articles += len(articles)

        logger.info("=== Terminé: %d articles total ===", total_articles)
        return 0

    except KeyboardInterrupt:
        logger.info("Interrompu par l'utilisateur.")
        return 1
    except Exception as exc:
        logger.exception("Erreur fatale: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

