from __future__ import annotations

from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.crawler.models import ArticleMetadata
from app.services.crawler.utils import pick, sanitize_text


class OpenGraphParser:
    def extract_meta(self, soup: BeautifulSoup, key: str) -> Optional[str]:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        return tag.get("content") if tag and tag.has_attr("content") else None

    def parse(self, url: str, html: str) -> ArticleMetadata:
        soup = BeautifulSoup(html, "lxml")

        title = pick(
            self.extract_meta(soup, "og:title"),
            soup.title.string if soup.title and soup.title.string else None,
        )

        description = pick(
            self.extract_meta(soup, "og:description"),
            self.extract_meta(soup, "description"),
        )

        image = self.extract_meta(soup, "og:image")

        og_url = self.extract_meta(soup, "og:url") or url
        canonical = soup.find("link", rel="canonical")
        canonical_url = canonical.get("href") if canonical else None

        final_url = og_url or canonical_url or url
        if final_url and final_url.startswith(("/", "#")):
            final_url = urljoin(url, final_url)

        author = self.extract_meta(soup, "article:author")
        published_at = self.extract_meta(soup, "article:published_time")
        updated_at = self.extract_meta(soup, "article:modified_time")

        return ArticleMetadata(
            title=sanitize_text(title),
            description=sanitize_text(description),
            image=image,
            url=final_url,
            author=sanitize_text(author),
            published_at=published_at,
            updated_at=updated_at,
        )

