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
    source_id TEXT,
    link TEXT UNIQUE,
    hash TEXT UNIQUE,
    categories TEXT[] DEFAULT '{}',
    image TEXT,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour recherche vectorielle (cosine similarity)
CREATE INDEX IF NOT EXISTS articles_embedding_idx 
ON articles USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
'''

# Migration SQL pour ajouter les colonnes si la table existe déjà
MIGRATE_TABLE_SQL = '''
ALTER TABLE articles ADD COLUMN IF NOT EXISTS source_id TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS link TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS hash TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS categories TEXT[] DEFAULT '{}';
ALTER TABLE articles ADD COLUMN IF NOT EXISTS image TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS articles_link_idx ON articles(link) WHERE link IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS articles_hash_idx ON articles(hash) WHERE hash IS NOT NULL;
'''
