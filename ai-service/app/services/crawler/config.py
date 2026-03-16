from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class HttpSettings:
    timeout_seconds: float = float(os.getenv("CRAWLER_TIMEOUT_SECONDS", 20))
    max_retries: int = int(os.getenv("CRAWLER_MAX_RETRIES", 3))
    backoff_initial: float = float(os.getenv("CRAWLER_BACKOFF_INITIAL", 0.5))
    backoff_multiplier: float = float(os.getenv("CRAWLER_BACKOFF_MULTIPLIER", 2.0))
    backoff_max: float = float(os.getenv("CRAWLER_BACKOFF_MAX", 10.0))
    respect_retry_after: bool = os.getenv("CRAWLER_RESPECT_RETRY_AFTER", "true").lower() == "true"
    follow_redirects: bool = os.getenv("CRAWLER_FOLLOW_REDIRECTS", "true").lower() == "true"
    user_agent: str = os.getenv("CRAWLER_USER_AGENT", "RDCNewsCrawler/1.0")


@dataclass
class CrawlerSettings:
    data_dir: str = os.getenv("CRAWLER_DATA_DIR", "data/crawler")
    backend_endpoint: str | None = os.getenv("CRAWLER_BACKEND_ENDPOINT") or os.getenv("BACKEND_ENDPOINT") or None
    backend_token: str | None = os.getenv("CRAWLER_BACKEND_TOKEN") or os.getenv("BACKEND_TOKEN") or None
    http: HttpSettings = field(default_factory=HttpSettings)


def load_crawler_settings() -> CrawlerSettings:
    """Build crawler settings from environment variables."""
    return CrawlerSettings()

