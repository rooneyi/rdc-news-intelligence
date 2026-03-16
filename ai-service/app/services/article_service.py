import logging
from typing import Optional
from app.db.session import get_db
from app.services.embedding_service import EmbeddingService
from app.schemas.article import ArticleCreate, ArticleOut

logger = logging.getLogger(__name__)
embedding_service = EmbeddingService()


def create_article(title: str, content: str) -> ArticleOut:
    """Créer un article avec embedding et le sauvegarder en DB"""
    try:
        embedding = embedding_service.generate(content)
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO articles (title, content, embedding) VALUES (%s, %s, %s) RETURNING id, title, content",
                (title, content, embedding)
            )
            article = cur.fetchone()
            conn.commit()
            logger.info(f"Article created with ID: {article[0]}")
            return ArticleOut(id=article[0], title=article[1], content=article[2])
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

        conn = get_db()
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
                   RETURNING id, title, content""",
                (title, content, source_id, link, hash_val, embedding)
            )
            row = cur.fetchone()
            conn.commit()
            logger.info(f"Crawled article saved — id={row[0]} source={source_id}")
            return ArticleOut(id=row[0], title=row[1], content=row[2])
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error saving crawled article: {e}")
        raise


def search_similar(query_embedding: list, limit: int = 5) -> list[ArticleOut]:
    """Rechercher des articles similaires par vecteur"""
    try:
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT id, title, content FROM articles ORDER BY embedding <=> %s::vector LIMIT %s",
                (query_embedding, limit)
            )
            results = cur.fetchall()
            logger.debug(f"Found {len(results)} similar articles")
            return [ArticleOut(id=r[0], title=r[1], content=r[2]) for r in results]
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error searching similar articles: {e}")
        raise
