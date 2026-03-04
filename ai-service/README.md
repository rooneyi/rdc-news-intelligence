# ai-service (FastAPI + pgvector)

## Description
Microservice d’intelligence artificielle pour le projet "rdc-news-intelligence". Ce service permet de stocker des articles, générer des embeddings avec Sentence Transformers, et effectuer des recherches sémantiques via PostgreSQL + pgvector.

## Structure du projet
```
ai-service/
│
├── app/
│   ├── main.py
│   ├── core/config.py
│   ├── db/session.py
│   ├── db/models.py
│   ├── schemas/article.py
│   ├── services/embedding_service.py
│   ├── services/article_service.py
│   └── api/routes/articles.py
│
├── requirements.txt
└── .env
```

## Fonctionnalités principales
- **Connexion à PostgreSQL** (avec psycopg2)
- **Utilisation de pgvector** pour stocker les embeddings
- **Génération d’embeddings** avec Sentence Transformers (all-MiniLM-L6-v2, 384 dimensions)
- **Stockage d’articles** avec embeddings
- **Recherche sémantique** (cosine similarity, top 5 résultats)

## Endpoints
- `POST /articles` : stocke un article et son embedding
- `POST /query` : recherche sémantique sur les articles

## Détail des fichiers
- `app/main.py` : Entrée FastAPI, inclut les routes
- `app/core/config.py` : Gestion des variables d’environnement (.env)
- `app/db/session.py` : Connexion PostgreSQL
- `app/db/models.py` : Définition SQL de la table articles
- `app/schemas/article.py` : Modèles Pydantic pour validation
- `app/services/embedding_service.py` : Génération d’embeddings
- `app/services/article_service.py` : Logique CRUD et recherche
- `app/api/routes/articles.py` : Routes API pour articles et recherche

## Installation
1. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
2. Configurer la base PostgreSQL avec pgvector et la table `articles` (voir db/models.py)
3. Lancer le serveur :
   ```bash
   uvicorn app.main:app --reload
   ```

## Test rapide
- Accéder à la doc interactive : http://localhost:8000/docs
- Utiliser Swagger pour tester les endpoints

## Variables d’environnement (.env)
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ai_db
DB_USER=postgres
DB_PASSWORD=password
```

## requirements.txt
```
fastapi
uvicorn
psycopg2-binary
sentence-transformers
python-dotenv
```

## Exemple SQL table articles
```sql
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    title TEXT,
    content TEXT,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Prochaine étape
- Générer un Dockerfile et docker-compose pour PostgreSQL + pgvector
- Intégration avec le backend Symfony
