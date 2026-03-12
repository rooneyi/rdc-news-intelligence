# 🔗 Dépendances et Flux de Données - AI Service

## 📌 Diagramme du Flux d'Exécution

```
┌─────────────────────────────────────────────────────────────┐
│                    app/main.py                              │
│  (Point d'entrée - Charge .env + crée FastAPI app)          │
└────────┬──────────────────────────────────────┬──────────────┘
         │                                      │
         ├─ charge .env_file                   ├─ attach_to_app()
         │  (DB credentials)                   │
         │                                      ▼
         ▼                          ┌──────────────────────────┐
    app/core/config.py              │ load_dataset.py          │
    (Lit DB_HOST, DB_USER, etc)     │ (Dataset loader)        │
         │                           │                         │
         │                           ├─ Télécharge dataset     │
         │                           ├─ Charge embedding model │
         │                           └─ Insert into DB         │
         │                                      │
         │                                      ▼
         └─────────────────┬────────────────────────────────┐
                           │                                │
                      app/db/session.py                     │
                   (DB connection pool)                     │
                           │                                │
                      app/db/models.py                      │
                   (Table: articles)                        │
         ┌──────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      app/api/routes/articles.py     │
│  (HTTP Endpoints)                   │
├─────────────────────────────────────┤
│ POST /articles                      │
│ POST /query                         │
│ POST /admin/load                    │
└──────────────┬──────────────────────┘
               │
      ┌────────┴────────┐
      │                 │
      ▼                 ▼
┌─────────────┐ ┌──────────────────┐
│ article_    │ │embedding_        │
│service.py   │ │service.py        │
│(Create)     │ │(Generate vectors)│
└──────┬──────┘ └──────┬───────────┘
       │                │
       └────────┬───────┘
                │
       ┌────────▼─────────┐
       │retrieval_service │
       │(Search similar)  │
       └───────────────────┘
```

## 📂 Dépendances des Imports

### app/main.py
```python
imports: os, dotenv, FastAPI, attach_to_app, router
depends_on:
  - app/core/config.py (pour les variables)
  - app/services/load_dataset.py (attach_to_app)
  - app/api/routes/articles.py (router)
```

### app/core/config.py
```python
imports: os, dotenv
depends_on: .env_file (fichier de config)
used_by:
  - app/services/load_dataset.py
  - app/services/article_service.py
  - app/db/session.py
```

### app/services/load_dataset.py
```python
imports: datasets, SentenceTransformer, psycopg2, asyncio
depends_on:
  - app/core/config.py (DB credentials)
  - .env_file (environnement)
used_by:
  - app/main.py (attach_to_app)
  - app/api/routes/articles.py (POST /admin/load)
```

### app/api/routes/articles.py
```python
imports: APIRouter, BaseModel, os
depends_on:
  - app/schemas/article.py (ArticleCreate, ArticleOut)
  - app/services/article_service.py (create_article, search_similar)
  - app/services/embedding_service.py (EmbeddingService)
  - app/services/load_dataset.py (load_and_insert)
used_by:
  - app/main.py (include_router)
```

### app/schemas/article.py
```python
imports: BaseModel (pydantic)
depends_on: rien
used_by:
  - app/api/routes/articles.py
  - app/services/article_service.py
```

### app/services/article_service.py
```python
imports: FastAPI, services
depends_on:
  - app/schemas/article.py
  - app/db/session.py
  - app/services/embedding_service.py
used_by:
  - app/api/routes/articles.py
```

### app/services/embedding_service.py
```python
imports: SentenceTransformer
depends_on:
  - Modèle pré-entraîné (auto-téléchargé)
used_by:
  - app/api/routes/articles.py
  - app/services/article_service.py
```

### app/db/session.py
```python
imports: psycopg2
depends_on:
  - app/core/config.py (DATABASE_URL)
used_by:
  - app/services/article_service.py
  - app/services/retrieval_service.py
```

### app/db/models.py
```python
imports: SQL (pas de dépendance Python)
depends_on: PostgreSQL + pgvector
used_by: Documentation (CREATE TABLE script)
```

## 🔄 Flux de Chargement des Variables d'Environnement

```
1. app/main.py démarre
   ├─ load_dotenv(".env_file") ✓
   └─ Toutes les variables disponibles

2. app/core/config.py importé
   ├─ Lit les variables d'env
   ├─ Crée DB_HOST, DB_USER, DATABASE_URL, etc
   └─ Prêt pour utilisation

3. app/services/load_dataset.py importé
   ├─ Vérifie si os.getenv("DB_HOST") existe
   ├─ Si oui → Skip load_dotenv (déjà chargé)
   └─ Si non → load_dotenv(".env_file")

4. Autres services importés
   └─ Utilisent la config via import
```

## 🎯 Cycle de Vie d'une Requête

### POST /articles (Créer un article)
```
1. Client envoie requête JSON
   └─ {"title": "...", "content": "..."}

2. articles.py::post_article() reçoit
   └─ Valide avec ArticleCreate schema

3. article_service.create_article()
   ├─ Génère embedding (embedding_service)
   ├─ Sauvegarde en DB (db/session.py)
   └─ Retourne ArticleOut

4. Client reçoit réponse
   └─ {"id": 1, "title": "...", "content": "..."}
```

### POST /query (Recherche)
```
1. Client envoie requête
   └─ {"query": "mon texte"}

2. articles.py::query_articles()
   ├─ Génère embedding de requête
   ├─ Appelle retrieval_service
   ├─ Recherche vectorielle en DB
   └─ Retourne résultats similaires

4. Client reçoit résultats
```

### POST /admin/load (Chargement dataset)
```
1. Client demande chargement
   ├─ load_dataset.py::load_and_insert()
   ├─ Télécharge dataset Hugging Face
   ├─ Génère embeddings
   └─ Insère 298k articles en DB

2. API reste responsive (background task)

3. Client peut interroger progressivement
   ├─ Articles insérés apparaissent
   └─ Recherche fonctionne en direct
```

## 🚨 Points Critiques

| Point | Dépendance | Impact |
|-------|-----------|--------|
| `.env_file` | Doit exister | Sinon DB credentials perdus |
| `app/core/config.py` | Importé par tous | Doit être correct |
| PostgreSQL | Doit tourner | Sinon insertion échoue |
| pgvector | Extension required | Sinon VECTOR(384) erreur |
| Modèles ML | Auto-téléchargés | Premier lancement slow |

## ✅ Vérification de l'Intégrité

```bash
# Vérifier que les imports fonctionnent
python -c "from app.main import app; print('✓ main.py ok')"

# Vérifier que les config sont chargées
python -c "from app.core.config import DB_HOST; print(f'✓ DB_HOST={DB_HOST}')"

# Vérifier que les services sont disponibles
python -c "from app.services.embedding_service import EmbeddingService; print('✓ services ok')"

# Lancer l'API
python -m uvicorn app.main:app --reload
```

