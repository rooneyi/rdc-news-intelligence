from __future__ import annotations

import logging
from typing import Iterable, List

from bs4 import BeautifulSoup

from app.services.crawler.config import CrawlerSettings, load_crawler_settings
from app.services.crawler.http.http_client import HttpError, SyncHttpClient
from app.services.crawler.http.open_graph import OpenGraphParser
from app.services.crawler.models import Article
from app.services.crawler.process.persistence import BackendForwarder, JsonlPersistor
from app.services.crawler.utils import make_hash, sanitize_text, infer_categories

logger = logging.getLogger(__name__)


class SyncCrawler:
    """Synchronous crawler with persistence and optional backend forwarding."""

    def __init__(
        self,
        settings: CrawlerSettings | None = None,
        http_client: SyncHttpClient | None = None,
        og_parser: OpenGraphParser | None = None,
    ):
        self.settings = settings or load_crawler_settings()
        self.http_client = http_client or SyncHttpClient(self.settings.http)
        self.og_parser = og_parser or OpenGraphParser()

    def crawl_urls(self, urls: Iterable[str], source_id: str) -> List[Article]:
        persist = JsonlPersistor(self.settings.data_dir, source_id)
        forwarder = BackendForwarder(self.settings)
        collected: List[Article] = []

        for url in urls:
            try:
                article = self._process_single(url, source_id)
                if not article:
                    continue
                persist.persist(article)
                forwarder.forward(article)
                collected.append(article)
                logger.info("Crawled %s", url)
            except HttpError as http_err:
                logger.warning("HTTP error on %s: %s", url, http_err)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected error while crawling %s: %s", url, exc)

        forwarder.close()
        return collected

    def _process_single(self, url: str, source_id: str) -> Article | None:
        response = self.http_client.get(url)
        html = response.text
        soup = BeautifulSoup(html, "lxml")
        metadata = self.og_parser.parse(url, html)

        body = self._extract_body(soup)
        title = metadata.title or soup.title.string if soup.title else url

        if not body:
            logger.debug("Skipping %s because no body was extracted", url)
            return None

        article = Article(
            source_id=source_id,
            link=url,
            title=sanitize_text(title) or url,
            body=body,
            categories=infer_categories(url),
            hash=make_hash(url),
            metadata=metadata,
        )
        return article

    def _extract_body(self, soup: BeautifulSoup) -> str:
        # Prefer <article> then fall back to paragraphs
        article_tag = soup.find("article")
        if article_tag:
            text = "\n".join([p.get_text(" ", strip=True) for p in article_tag.find_all("p")])
            return sanitize_text(text)

        paragraphs = soup.find_all("p")
        text = "\n".join([p.get_text(" ", strip=True) for p in paragraphs])
        return sanitize_text(text)
