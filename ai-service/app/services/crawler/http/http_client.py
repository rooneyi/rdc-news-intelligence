from __future__ import annotations

import random
import time
from typing import Any, Optional

import httpx

from app.services.crawler.config import HttpSettings

TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


class HttpError(Exception):
    def __init__(self, message: str, response: httpx.Response):
        super().__init__(message)
        self.response = response
        self.status = response.status_code


class SyncHttpClient:
    def __init__(self, settings: HttpSettings):
        self.settings = settings
        self.client = httpx.Client(
            timeout=settings.timeout_seconds,
            follow_redirects=settings.follow_redirects,
            headers={"User-Agent": settings.user_agent},
        )

    def _compute_backoff(self, attempt: int) -> float:
        base = min(
            self.settings.backoff_initial * (self.settings.backoff_multiplier ** attempt),
            self.settings.backoff_max,
        )
        jitter = random.random() * base * 0.25
        return base + jitter

    def _retry_after_seconds(self, response: httpx.Response) -> Optional[float]:
        if not self.settings.respect_retry_after:
            return None
        value = response.headers.get("Retry-After")
        if not value:
            return None
        if value.isdigit():
            return float(value)
        return None

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self.client.request(method, url, **kwargs)
                if response.status_code in TRANSIENT_STATUSES and attempt < self.settings.max_retries:
                    sleep_s = self._retry_after_seconds(response) or self._compute_backoff(attempt)
                    time.sleep(sleep_s)
                    continue
                if response.is_error:
                    raise HttpError(f"HTTP {response.status_code}", response)
                return response
            except (httpx.TimeoutException, httpx.TransportError, HttpError) as exc:
                last_error = exc
                if attempt >= self.settings.max_retries:
                    raise
                time.sleep(self._compute_backoff(attempt))
        raise RuntimeError("HTTP request failed") from last_error

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

