# Article table definition for PostgreSQL with pgvector

import psycopg2

# Table creation SQL (for migration)
CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    title TEXT,
    content TEXT,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''
