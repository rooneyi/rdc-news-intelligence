# AI Service - Architecture Refactorisée

## 📁 Structure du Projet

```
ai-service/
├── app/
│   ├── __init__.py
│   ├── main.py                      # Point d'entrée FastAPI (chargement .env + routes)
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py               # Configuration centralisée (DB, env vars)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── articles.py         # Endpoints des articles
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py               # Définitions des tables SQL
│   │   └── session.py              # Gestion des sessions DB
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── article.py              # Pydantic models (ArticleCreate, ArticleOut)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── article_service.py      # Logique métier articles
│   │   ├── embedding_service.py    # Génération d'embeddings
│   │   ├── retrieval_service.py    # Recherche vectorielle
│   │   ├── rag_service.py          # RAG (Retrieval-Augmented Generation)
│   │   ├── clustering_service.py   # Clustering d'articles
│   │   ├── summarizer_service.py   # Résumé d'articles
│   │   └── load_dataset.py         # Chargement du dataset au démarrage
│   └── utils/
│       ├── preprocessing.py        # Nettoyage de texte
│       └── text_chunker.py         # Découpe de texte en chunks
├── .env_file                        # Variables d'environnement
├── requirements.txt                 # Dépendances Python
└── README.md
```

## 🔄 Flux d'Exécution

### 1️⃣ Démarrage de l'Application
```
app/main.py
  ├── 1. Charge les variables d'env (.env_file)
  ├── 2. Initialise FastAPI
  ├── 3. Attache load_dataset.py au startup (background=True par défaut)
  └── 4. Inclut les routers (app/api/routes/articles.py)
```

### 2️⃣ Chargement des Données
```
load_dataset.py
  ├── Télécharge le dataset: bernard-ng/drc-news-corpus
  ├── Charge le modèle: sentence-transformers/all-MiniLM-L6-v2
  ├── Génère les embeddings pour chaque article
  └── Insère dans PostgreSQL (table: articles)
```

### 3️⃣ Endpoints Disponibles
- `POST /articles` - Créer un nouvel article
- `POST /query` - Rechercher des articles similaires
- `POST /admin/load` - Déclencher le chargement du dataset (admin)

## 🧹 Nettoyage Effectué

### ✅ Fichiers Supprimés (Vides ou Redondants)
- `main.py` (racine) - Point d'entrée dupliqué
- `app/config.py` - Vide (remplacé par `app/core/config.py`)
- `app/core/logger.py` - Vide
- `app/core/execption.py` - Vide
- `app/models/` - Dossier vide
- `app/api/route.py` - Obsolète (utiliser `routes/articles.py`)
- `app/api/schema.py` - Obsolète (utiliser `schemas/article.py`)

### ✅ Optimisations
- **Consolidation de la config** : Tout dans `app/core/config.py`
- **Point d'entrée unique** : `app/main.py` uniquement
- **Chargement .env centralisé** : Une seule place où charger les variables
- **Éviter le double chargement** : `load_dataset.py` détecte si les vars sont déjà chargées

## 🚀 Utilisation

### Lancer l'API
```bash
cd ai-service
python -m uvicorn app.main:app --reload
```

### Lancer le chargement du dataset seul
```bash
cd ai-service
python -m app.services.load_dataset
```

### Variables d'Environnement Requises
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rdc_news
DB_USER=postgres
DB_PASSWORD=postgres
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rdc_news
```

## 📊 Résumé des Changements

| Aspect | Avant | Après |
|--------|-------|-------|
| Points d'entrée | 2 (`main.py` + `app/main.py`) | 1 (`app/main.py`) |
| Fichiers vides | 6+ | 0 |
| Dossiers vides | 1 (`models/`) | 0 |
| Config .env | Chargée partout | Centralisée |
| Répétitions | Oui | Non |

## ✨ Avantages

✅ **Clarté** : Structure claire et facile à naviguer  
✅ **Maintenabilité** : Moins de doublons à maintenir  
✅ **Performance** : Pas de double chargement de .env  
✅ **Scalabilité** : Facile d'ajouter de nouveaux services  
✅ **Testabilité** : Dépendances bien organisées

