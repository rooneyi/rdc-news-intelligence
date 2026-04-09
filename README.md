# RDC RAG News Platform

An intelligent news aggregation and semantic recommendation platform designed to reduce information overload and mitigate misinformation in the Democratic Republic of Congo (RDC).

---

## Tech Stack

### Backend
- Symfony 7+
- Doctrine ORM
- PostgreSQL + pgvector

### Frontend
- Next.js 15
- React
- TailwindCSS

### AI Service
- Python
- HuggingFace Transformers
- Sentence Embeddings (1024-dim)
- Retrieval-Augmented Generation (RAG)

---

##  System Architecture

The platform is composed of three main layers:

1. Symfony API (Core Business Logic)
2. Next.js Frontend (User Interface)
3. Python AI Microservice (Semantic Processing)

---

##  Processing Pipeline

### Article Ingestion

1. Article stored via Symfony
2. Symfony triggers AI service
3. Article is chunked (500 chars)
4. Embeddings generated
5. Similarity computed
6. Story updated or created

---

### User Query

1. User submits search query
2. Symfony forwards query to AI service
3. AI generates embedding
4. Vector similarity search (pgvector)
5. Results grouped by story
6. RAG summary generated
7. Structured response returned to frontend

---

##  Repository Structure

- backend/ → Symfony API
- frontend/ → Next.js application
- ai-service/ → Python semantic engine

---

##  Development Setup

### AI Service (Python)
Le service d'IA gère la vectorisation des articles et la recherche sémantique.
- **Chemin** : `ai-service/`
- **Installation** : Voir le [README détaillé de ai-service](ai-service/README.md).
- **Statut** : Base de données initialisée avec ~2000 articles du corpus RDC.

### Backend (Symfony)
... (à compléter)

### Frontend (Next.js)
Le frontend fournit deux espaces principaux avec une direction visuelle premium inspirée de shadcn, en bleu foncé, bleu clair et blanc, avec une base Tailwind.
- **Espace client** : authentification, pose de questions, consultation de l'historique et affichage des réponses sourcées.
- **Espace admin** : supervision du système, gestion des sources, lancement du crawl et suivi de l'état du pipeline.
- **Objectif UI** : interface claire, moderne et stable pour l'usage quotidien sur desktop et mobile.

---

## Lancer tout en meme temps (front + back + FastAPI)

Depuis la racine du projet, lance:

```bash
bash scripts/dev-all.sh
```

Ce script demarre:
- Frontend Next.js: http://127.0.0.1:3000
- Backend Symfony: http://127.0.0.1:8000
- Service FastAPI: http://127.0.0.1:8001

Les logs sont ecrits dans `.logs/`.

Pour arreter tous les services: `Ctrl+C` dans le terminal du script.

### Connexion frontend vers FastAPI

Le frontend appelle FastAPI via un proxy Next (`/api/fastapi/rag`) pour eviter les problemes CORS.

Si besoin, configure l'URL FastAPI dans `frontend/.env.local`:

```bash
NEXT_PUBLIC_FASTAPI_URL=http://127.0.0.1:8001
```