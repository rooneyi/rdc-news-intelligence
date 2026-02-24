# services/retrieval_service.py

import psycopg2
from psycopg2.extras import RealDictCursor

class RetrievalService:
    def __init__(self):
        self.conn = psycopg2.connect(
            host="localhost",
            database="rdc_news",
            user="postgres",
            password="password"
        )

    def search(self, embedding: list, limit: int = 5):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, title, content
                FROM articles
                ORDER BY embedding <-> %s
                LIMIT %s
                """,
                (embedding, limit)
            )
            return cur.fetchall()