# Guide de Démarrage - RDC News Intelligence AI Service

## 📋 Prérequis

- Python 3.9+
- PostgreSQL 12+ avec extension pgvector
- pip ou conda

## 🔧 Installation

### 1. Activer l'environnement virtuel
```bash
cd ai-service
source .env/bin/activate  # Linux/Mac
# ou
.env\Scripts\activate  # Windows
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement
```bash
# Créer/vérifier .env_file
cat > .env_file << 'EOF'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rdc_news
DB_USER=postgres
DB_PASSWORD=postgres
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rdc_news
EOF
```

### 4. Créer la base de données et les tables
```bash
# Se connecter à PostgreSQL
psql -U postgres -h localhost

# Créer la base
CREATE DATABASE rdc_news;

# Installer pgvector
\c rdc_news
CREATE EXTENSION IF NOT EXISTS vector;

# Créer la table articles
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    title TEXT,
    content TEXT,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# Créer un index pour les recherches vectorielles
CREATE INDEX ON articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

## 🚀 Lancer l'Application

### Mode Développement
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

L'API sera disponible à : `http://localhost:8000`
Documentation Swagger : `http://localhost:8000/docs`

### Mode Production
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📡 Endpoints Disponibles

### 1. Créer un Article
```bash
curl -X POST "http://localhost:8000/articles" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Titre de l\''article",
    "content": "Contenu détaillé de l\''article..."
  }'
```

### 2. Rechercher des Articles Similaires
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Votre requête de recherche"
  }'
```

### 3. Déclencher le Chargement du Dataset (Admin)
```bash
curl -X POST "http://localhost:8000/admin/load" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": null
  }'
```

## 🧪 Tests

### Lancer le script de chargement seul
```bash
python -m app.services.load_dataset
```

## 📊 Architecture

Pour plus de détails sur l'architecture du projet, voir `ARCHITECTURE.md`

## 🐛 Dépannage

### Erreur: "no password supplied"
**Solution** : Vérifier que `.env_file` contient `DB_PASSWORD`

### Erreur: "connection refused"
**Solution** : Vérifier que PostgreSQL est en cours d'exécution sur `localhost:5432`

### Erreur: "pgvector extension not found"
**Solution** : Installer pgvector dans la base de données :
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 📚 Documents Connexes

- `README.md` - Vue d'ensemble du projet
- `ARCHITECTURE.md` - Architecture détaillée
- `requirements.txt` - Dépendances Python

