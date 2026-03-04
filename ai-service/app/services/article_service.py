from app.db.session import get_db
from app.services.embedding_service import EmbeddingService
from app.schemas.article import ArticleCreate, ArticleOut
import psycopg2

def create_article(title: str, content: str):
    embedding_service = EmbeddingService()
    embedding = embedding_service.generate(content)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO articles (title, content, embedding) VALUES (%s, %s, %s) RETURNING id, title, content",
        (title, content, embedding)
    )
    article = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return ArticleOut(id=article[0], title=article[1], content=article[2])

def search_similar(query_embedding):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, content FROM articles ORDER BY embedding <=> %s::vector LIMIT 5;",
        (query_embedding,)
    )
    results = cur.fetchall()
    cur.close()
    conn.close()
    return [ArticleOut(id=r[0], title=r[1], content=r[2]) for r in results]