import logging
from typing import Optional
from app.db.session import get_db_connection
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.schemas.article import ArticleCreate, ArticleOut

logger = logging.getLogger(__name__)
embedding_service = EmbeddingService()
retrieval_service = RetrievalService()


def create_article(title: str, content: str) -> ArticleOut:
    """Créer un article avec embedding et le sauvegarder en DB"""
    try:
        embedding = embedding_service.generate(content)
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO articles (title, content, embedding) VALUES (%s, %s, %s) RETURNING id, title, content, link, source_id, hash",
                (title, content, embedding)
            )
            article = cur.fetchone()
            conn.commit()
            logger.info(f"Article created with ID: {article[0]}")
            return ArticleOut(id=article[0], title=article[1], content=article[2], link=article[3], source_id=article[4], hash=article[5])
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error creating article: {e}")
        raise


def save_crawled_article(article) -> Optional[ArticleOut]:
    """
    Sauvegarder un article crawlé en DB avec embedding.
    Retourne None si l'article est un doublon (même link ou même hash).
    """
    try:
        link = str(article.link)
        hash_val = article.hash
        content = article.body
        title = article.title
        source_id = article.source_id

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Vérifier doublon par link ou hash
            cur.execute(
                "SELECT id FROM articles WHERE link = %s OR hash = %s LIMIT 1",
                (link, hash_val)
            )
            if cur.fetchone():
                logger.debug(f"Doublon ignoré: {link}")
                return None

            # Générer embedding sur le body
            embedding = embedding_service.generate(content)

            cur.execute(
                """INSERT INTO articles (title, content, source_id, link, hash, embedding)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id, title, content, link, source_id, hash""",
                (title, content, source_id, link, hash_val, embedding)
            )
            row = cur.fetchone()
            conn.commit()
            logger.info(f"Crawled article saved — id={row[0]} source={source_id}")
            return ArticleOut(id=row[0], title=row[1], content=row[2], link=row[3], source_id=row[4], hash=row[5])
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error saving crawled article: {e}")
        raise


def search_similar(query_embedding: list, limit: int = 5) -> list[ArticleOut]:
    """Rechercher des articles similaires par vecteur"""
    return retrieval_service.search(query_embedding, limit)
