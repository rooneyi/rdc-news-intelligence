"""Charge la configuration des sources depuis data/crawler/sources.json."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_SOURCES_JSON = Path(__file__).resolve().parents[3] / "data" / "crawler" / "sources.json"


@dataclass(frozen=True)
class SourceCrawlConfig:
    source_id: str
    base_url: str
    listing_url: str
    article_link_selector: str
    article_categories_selector: str | None
    listing_categories: tuple[str, ...]
    supports_listing_categories: bool


def load_all_source_configs(path: Path = _SOURCES_JSON) -> dict[str, SourceCrawlConfig]:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Impossible de lire %s: %s", path, exc)
        return {}

    out: dict[str, SourceCrawlConfig] = {}
    for section in ("html", "wordpress"):
        for item in data.get("sources", {}).get(section, []) or []:
            source_id = item.get("sourceId")
            if not isinstance(source_id, str) or not source_id.strip():
                continue
            base_url = (item.get("sourceUrl") or "").rstrip("/")
            pagination = (item.get("paginationTemplate") or "").lstrip("/")
            listing_url = f"{base_url}/{pagination}" if pagination else base_url
            selectors = item.get("sourceSelectors") or {}
            raw_cats = item.get("categories") or []
            listing_cats = tuple(
                str(c).strip().lower()
                for c in raw_cats
                if c and str(c).strip()
            )
            rss = (item.get("rssUrl") or "").strip()
            if section == "wordpress" and rss:
                listing_url = rss
            out[source_id.strip()] = SourceCrawlConfig(
                source_id=source_id.strip(),
                base_url=base_url,
                listing_url=listing_url,
                article_link_selector=selectors.get("articleLink") or "a",
                article_categories_selector=selectors.get("articleCategories"),
                listing_categories=listing_cats,
                supports_listing_categories=bool(item.get("supportsCategories")),
            )
    return out


def get_source_config(source_id: str) -> SourceCrawlConfig | None:
    return load_all_source_configs().get(source_id)
