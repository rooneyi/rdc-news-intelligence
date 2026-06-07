"""Tests pour le filtrage de pertinence RAG — logique purement fonctionnelle, sans I/O."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schemas.article import ArticleOut
from app.services.rag_service import RAGService


def _make_article(similarity: float, article_id: int = 1) -> ArticleOut:
    return ArticleOut(
        id=article_id,
        title=f"Article {article_id}",
        content="Contenu test",
        link=f"http://example.com/{article_id}",
        source_id="test",
        hash=f"hash{article_id}",
        categories=[],
        image=None,
        similarity=similarity,
    )


def _make_rag() -> RAGService:
    svc = RAGService.__new__(RAGService)
    svc.min_similarity_default = 0.36
    svc.min_similarity_messaging = 0.40
    svc.enable_rerank = False
    return svc


def test_filter_keeps_articles_above_threshold():
    svc = _make_rag()
    articles = [_make_article(0.45, 1), _make_article(0.38, 2), _make_article(0.20, 3)]
    result = svc._filter_relevant_articles(articles, channel="whatsapp")
    ids = [a.id for a in result]
    assert 1 in ids
    assert 3 not in ids


def test_filter_messaging_threshold_higher_than_default():
    svc = _make_rag()
    # similarity=0.37 : passe le seuil par défaut (0.36) mais pas messagerie (0.40)
    articles = [_make_article(0.37, 1)]
    web_result = svc._filter_relevant_articles(articles, channel="api")
    msg_result = svc._filter_relevant_articles(articles, channel="whatsapp")
    assert len(web_result) == 1
    assert len(msg_result) == 0


def test_filter_web_uses_messaging_threshold():
    svc = _make_rag()
    articles = [_make_article(0.38, 1), _make_article(0.41, 2)]
    result = svc._filter_relevant_articles(articles, channel="web")
    assert len(result) == 1
    assert result[0].id == 2


def test_filter_none_similarity_excluded():
    svc = _make_rag()
    articles = [_make_article(None, 1), _make_article(0.50, 2)]
    result = svc._filter_relevant_articles(articles, channel="web")
    ids = [a.id for a in result]
    assert 1 not in ids
    assert 2 in ids


def test_filter_empty_list():
    svc = _make_rag()
    assert svc._filter_relevant_articles([], channel="web") == []
