from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, HttpUrl


class ArticleMetadata(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[HttpUrl] = None
    url: Optional[HttpUrl] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    updated_at: Optional[str] = None


class Article(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_id: str
    link: HttpUrl
    title: str
    body: str
    categories: List[str] = []
    hash: str
    metadata: Optional[ArticleMetadata] = None

    def to_backend_payload(self) -> dict:
        return {
            "source_id": self.source_id,
            "link": str(self.link),
            "title": self.title,
            "body": self.body,
            "categories": self.categories,
            "hash": self.hash,
            "metadata": {
                k: str(v) if hasattr(v, "__str__") and not isinstance(v, (str, type(None))) else v
                for k, v in (self.metadata.model_dump(exclude_none=True) if self.metadata else {}).items()
            } or None,
        }

