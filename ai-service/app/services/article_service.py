import logging
from app.db.session import get_db
from app.services.embedding_service import EmbeddingService
from app.schemas.article import ArticleCreate, ArticleOut

logger = logging.getLogger(__name__)
embedding_service = EmbeddingService()  # Singleton instance


def create_article(title: str, content: str) -> ArticleOut:
    """Créer un article avec embedding et le sauvegarder en DB"""
    try:
        # Générer l'embedding
        logger.debug(f"Generating embedding for article: {title[:50]}")
        embedding = embedding_service.generate(content)

        # Insérer en DB
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
