import logging
from typing import Optional
from app.db.session import get_db_connection
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.schemas.article import ArticleCreate, ArticleOut
from app.services.crawler.models import Article as CrawlerArticle
from typing import Optional

logger = logging.getLogger(__name__)
embedding_service = EmbeddingService()
retrieval_service = RetrievalService()


def create_article(article: ArticleCreate) -> Optional[ArticleOut]:
    """Créer un article avec embedding et le sauvegarder en DB (link/source/hash optionnels)."""
    try:
        embedding = embedding_service.generate(article.content)
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """INSERT INTO articles (title, content, link, source_id, hash, categories, image, embedding)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING
                   RETURNING id, title, content, link, source_id, hash, categories, image""",
                (
                    article.title,
                    article.content,
                    article.link,
                    article.source_id,
                    article.hash,
                    article.categories or [],
                    article.image,
                    embedding,
                )
            )
            row = cur.fetchone()
            conn.commit()
            if not row:
                logger.debug(f"Article ignoré (doublon link/hash): {article.link}")
                return None
            logger.info(f"Article created with ID: {row[0]}")
            return ArticleOut(
                id=row[0],
                title=row[1],
                content=row[2],
                link=row[3],
                source_id=row[4],
                hash=row[5],
                categories=row[6],
                image=row[7],
            )
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error creating article: {e}")
        raise


def save_crawled_article(article: CrawlerArticle) -> Optional[ArticleOut]:
    """
    Sauvegarder un article crawlé en DB avec embedding.
    Retourne None si l'article est un doublon (link ET/OU hash déjà présent).
    """
    try:
        link = str(article.link)
        hash_val = article.hash
        content = article.body
        title = article.title
        source_id = article.source_id
        categories = [str(c) for c in (article.categories or [])]
        image = str(article.metadata.image) if article.metadata and article.metadata.image else None

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Générer embedding sur le body
            embedding = embedding_service.generate(content)

            cur.execute(
                """INSERT INTO articles (title, content, source_id, link, hash, categories, image, embedding)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING
                   RETURNING id, title, content, link, source_id, hash, categories, image""",
                (title, content, source_id, link, hash_val, categories, image, embedding)
            )
            row = cur.fetchone()
            conn.commit()
            if not row:
                logger.debug(f"Doublon ignoré (link/hash): {link}")
                return None
            logger.info(f"Crawled article saved — id={row[0]} source={source_id}")
            return ArticleOut(id=row[0], title=row[1], content=row[2], link=row[3], source_id=row[4], hash=row[5], categories=row[6], image=row[7])
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error saving crawled article: {e}")
        raise


def search_similar(query_embedding: list, limit: int = 5) -> list[ArticleOut]:
    """Rechercher des articles similaires par vecteur"""
    return retrieval_service.search(query_embedding, limit)
