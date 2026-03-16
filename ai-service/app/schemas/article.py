from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class ArticleCreate(BaseModel):
    title: str
    content: str


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    link: Optional[str] = None
    source_id: Optional[str] = None
    hash: Optional[str] = None


class ArticleSource(BaseModel):
    """Source d'un article avec métadonnées pour RAG"""
    id: int
    rank: int
    title: str
    excerpt: str
    url: str
    relevance_score: str


class RAGRequest(BaseModel):
    """Requête pour le système RAG"""
    query: str
    top_k: Optional[int] = 5


class RAGResponse(BaseModel):
    """Réponse du système RAG avec résumé et sources"""
    query: str
    summary: str
    sources: List[ArticleSource]
    num_sources: int

