# Article table definition for PostgreSQL with pgvector

"""
Dimensions des embeddings selon les modèles:
- sentence-transformers/all-MiniLM-L6-v2: 384 dimensions
- sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2: 384 dimensions

⚠️ IMPORTANT: Si vous changez le modèle, vérifiez la dimension!
"""

# Table creation SQL (for migration)
CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour recherche vectorielle (cosine similarity)
CREATE INDEX IF NOT EXISTS articles_embedding_idx 
ON articles USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
'''
