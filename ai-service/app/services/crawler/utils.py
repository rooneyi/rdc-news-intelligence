from __future__ import annotations

import hashlib
import re
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse


def sanitize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = text.replace("\u00A0", " ").replace("\u202F", " ")
    cleaned = cleaned.replace("\u200B", "").replace("\u200C", "").replace("\u200D", "")
    cleaned = cleaned.replace("\uFEFF", "").replace("\r\n", "\n")
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    return cleaned.strip()


def make_hash(link: str) -> str:
    return hashlib.md5(link.encode("utf-8")).hexdigest()


def pick(*values: Iterable[Optional[str]]) -> Optional[str]:
    for value in values:
        if value:
            return value
    return None


def absolutize(url: str, base: str) -> str:
    return urljoin(base, url)


def infer_categories(url: str) -> list[str]:
    """Best-effort category extraction from the URL path segments."""
    parts = [p for p in urlparse(url).path.split("/") if p]
    if "actualite" in parts:
        idx = parts.index("actualite")
        if idx + 1 < len(parts):
            return [parts[idx + 1]]
    return []
