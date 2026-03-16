from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import logging

import httpx

from app.services.crawler.config import CrawlerSettings
from app.services.crawler.models import Article

logger = logging.getLogger(__name__)


class JsonlPersistor:
    """Persist articles locally as JSONL, one per line."""

    def __init__(self, data_dir: str, source_id: str):
        self.path = Path(data_dir)
        self.path.mkdir(parents=True, exist_ok=True)
        self.file = self.path / f"{source_id}.jsonl"
        self.file.touch(exist_ok=True)

    def persist(self, article: Article) -> None:
        with self.file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(article.to_backend_payload(), ensure_ascii=False) + "\n")


class BackendForwarder:
    """Forward crawled articles to an HTTP backend if configured."""

    def __init__(self, settings: CrawlerSettings):
        self.endpoint = settings.backend_endpoint
        self.token = settings.backend_token
        self.enabled = bool(self.endpoint)
        self._client = httpx.Client(timeout=20) if self.enabled else None
        if not self.enabled:
            logger.info("Backend forwarding disabled: set CRAWLER_BACKEND_ENDPOINT to push to API")

    def forward(self, article: Article) -> Optional[httpx.Response]:
        if not self.enabled:
            return None
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return self._client.post(
            f"{self.endpoint.rstrip('/')}/crawler/articles",
            json=article.to_backend_payload(),
            headers=headers,
            timeout=20,
        )

    def close(self):
        if self._client:
            self._client.close()
