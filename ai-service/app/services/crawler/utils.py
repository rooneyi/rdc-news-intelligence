from __future__ import annotations

import hashlib
import re
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# Slugs fréquents dans les médias RDC / francophones
_KNOWN_CATEGORY_SLUGS = frozenset(
    {
        "politique",
        "politics",
        "economie",
        "economy",
        "finance",
        "culture",
        "sport",
        "sports",
        "societe",
        "society",
        "sante",
        "health",
        "international",
        "afrique",
        "africa",
        "monde",
        "world",
        "justice",
        "securite",
        "security",
        "education",
        "environnement",
        "environment",
        "technologie",
        "tech",
        "actualite",
        "actualites",
        "news",
    }
)

_PATH_MARKERS = ("actualite", "actualites", "category", "categorie", "rubrique", "cat", "section")


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
    return urljoin(url, base)


def _normalize_category_label(raw: str) -> str | None:
    if not raw:
        return None
    label = sanitize_text(raw).lower()
    label = re.sub(r"\s+", " ", label)
    label = label.strip(".,;:/\\|")
    if not label or len(label) > 80:
        return None
    if label in {"accueil", "home", "news", "article", "articles", "lire plus"}:
        return None
    return label


def _dedupe_labels(labels: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for label in labels:
        norm = _normalize_category_label(label)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def infer_categories(url: str) -> list[str]:
    """Extrait une catégorie probable depuis le chemin de l'URL."""
    parts = [p.lower() for p in urlparse(url).path.split("/") if p]
    if not parts:
        return []

    for marker in _PATH_MARKERS:
        if marker in parts:
            idx = parts.index(marker)
            if idx + 1 < len(parts):
                candidate = parts[idx + 1]
                if candidate not in _PATH_MARKERS and not candidate.isdigit():
                    norm = _normalize_category_label(candidate)
                    if norm:
                        return [norm]

    for part in parts:
        if part in _KNOWN_CATEGORY_SLUGS and part not in _PATH_MARKERS:
            return [part]

    return []


def extract_categories_from_html(
    soup: BeautifulSoup,
    *,
    css_selector: str | None = None,
    listing_category: str | None = None,
) -> list[str]:
    """Lit les catégories sur la page article (sélecteur sources.json + balises meta)."""
    found: list[str] = []

    if listing_category:
        norm = _normalize_category_label(listing_category)
        if norm:
            found.append(norm)

    if css_selector:
        try:
            for node in soup.select(css_selector):
                text = node.get_text(" ", strip=True)
                norm = _normalize_category_label(text)
                if norm:
                    found.append(norm)
        except Exception:  # noqa: BLE001
            pass

    for prop in ("article:section", "og:article:section", "parsely-section"):
        tag = soup.find("meta", attrs={"property": prop}) or soup.find(
            "meta", attrs={"name": prop}
        )
        if tag and tag.get("content"):
            norm = _normalize_category_label(tag["content"])
            if norm:
                found.append(norm)

    for tag in soup.select('a[rel="category tag"], a[rel="tag"], .category a, .post-category a'):
        norm = _normalize_category_label(tag.get_text(" ", strip=True))
        if norm:
            found.append(norm)

    return _dedupe_labels(found)


def resolve_article_categories(
    url: str,
    soup: BeautifulSoup | None = None,
    *,
    css_selector: str | None = None,
    listing_category: str | None = None,
) -> list[str]:
    """Fusion URL + page HTML + catégorie de la page liste (crawler)."""
    merged: list[str] = []
    if listing_category:
        norm = _normalize_category_label(listing_category)
        if norm:
            merged.append(norm)
    merged.extend(infer_categories(url))
    if soup is not None:
        merged.extend(
            extract_categories_from_html(
                soup,
                css_selector=css_selector,
                listing_category=None,
            )
        )
    return _dedupe_labels(merged)
