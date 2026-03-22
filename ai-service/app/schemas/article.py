from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class ArticleCreate(BaseModel):
    title: str
    content: str
    link: Optional[str] = None
    source_id: Optional[str] = None
    hash: Optional[str] = None
    categories: Optional[List[str]] = None
    image: Optional[str] = None


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    link: Optional[str] = None
    source_id: Optional[str] = None
    hash: Optional[str] = None
    categories: Optional[List[str]] = None
    image: Optional[str] = None
    similarity: Optional[float] = None  # score de similarité (cosine) pour RAG


class ArticleSource(BaseModel):
    """Source d'un article avec métadonnées pour RAG"""
    id: int
    rank: int
    title: str
    excerpt: str
    url: str
    relevance_score: str
    source_id: Optional[str] = None
    hash: Optional[str] = None
    similarity: Optional[float] = None


class Story(BaseModel):
    """Regroupement thématique des articles retournés par le RAG"""
    id: str
    title: str
    score: Optional[float] = None
    articles: List[ArticleSource]


class RAGRequest(BaseModel):
    """Requête pour le système RAG"""
    query: str
    top_k: Optional[int] = 5
    min_score: Optional[float] = 0.0  # seuil de similarité (0-1)


class RAGResponse(BaseModel):
    """Réponse du système RAG avec résumé et sources"""
    query: str
    summary: str = ""
    sources: List[ArticleSource] = []
    num_sources: int = 0
    stories: List[Story] = []
