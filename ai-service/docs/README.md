# RDC News Intelligence - AI Service

Ce service est le moteur d'intelligence artificielle du projet **RDC News Intelligence**. Il utilise FastAPI, PostgreSQL avec l'extension `pgvector` et Sentence Transformers pour le traitement sémantique des actualités de la République Démocratique du Congo.

## 🚀 Fonctionnalités réalisées

### 1. Base de données Vectorielle
- **Configuration PostgreSQL + pgvector** : Mise en place de l'extension `vector` pour stocker et rechercher des vecteurs de haute dimension.
- **Modèle de données** : Création de la table `articles` incluant une colonne `embedding` de type `VECTOR(384)`.
- **Indexation** : Support de la recherche par similarité cosinus (`<=>`).

### 2. Chargement et Vectorisation du Dataset
- **Dataset utilisé** : `bernard-ng/drc-news-corpus` (Hugging Face).
- **Modèle d'Embedding** : `sentence-transformers/all-MiniLM-L6-v2` (dimension 384).
- **Pipeline de chargement** : Script automatique (`app/services/load_dataset.py`) qui télécharge, vectorise et insère les articles en base de données par lots.
- **État actuel** : Environ **1986 articles** ont été chargés et vectorisés avec succès.

### 3. API FastAPI & RAG
- **Recherche Sémantique** : Endpoint `POST /query` permettant de poser une question en langage naturel et d'obtenir les articles les plus pertinents.
- **RAG classique** : `POST /rag` renvoie un résumé complet + les sources.
- **RAG Streaming** : `POST /rag/stream` renvoie les chunks de réponse Mistral en flux (NDJSON) pour une UI temps réel.
- **RAG Image → Texte (OCR local)** : `POST /rag/image` prend une image, applique un OCR local (Tesseract) puis envoie le texte extrait dans le pipeline RAG.
- **Gestion des articles** : Endpoint `POST /articles` pour l'ajout manuel d'articles.
- **Administration** : Endpoint `POST /admin/load` pour déclencher ou limiter le chargement du dataset en arrière-plan.

## 🛠 Installation et Configuration

### Prérequis
- Python 3.10+
- PostgreSQL avec l'extension `pgvector` installée.

### Installation
1. Entrez dans le dossier du service :
   ```bash
   cd ai-service
   ```
2. Créez et activez l'environnement virtuel :
   ```bash
   python3 -m venv .env
   source .env/bin/activate
   ```
3. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

### Configuration (.env)
Créez un fichier `.env` ou `.env_file` à la racine de `ai-service` :
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rdc_news
DB_USER=votre_utilisateur
DB_PASSWORD=votre_mot_de_passe
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Désactive le chargement automatique du dataset HuggingFace au démarrage
DISABLE_DATASET_AUTOLOAD=true

# (Optionnel) Active le CRON automatique (crawler + re-embedding toutes les 2h)
# Par défaut il est désactivé pour ne pas impacter la réactivité.
# ENABLE_CRON_JOBS=true
```

## 📖 Utilisation

### Lancer l'application (API + Telegram)
```bash
export PYTHONPATH=$(pwd)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Le paramètre `DISABLE_DATASET_AUTOLOAD=true` fait que le loader de dataset **ne tourne pas automatiquement** au démarrage.
- Si `TELEGRAM_BOT_TOKEN` est défini, le polling Telegram est lancé automatiquement dans FastAPI (aucun script séparé à lancer).

Variables d'environnement importantes (exemple dans `.env_file`) :
- `TELEGRAM_BOT_TOKEN` : token du bot Telegram.
- `TELEGRAM_TOP_K` : nombre maximum d'articles utilisés par le RAG pour Telegram.
- `TELEGRAM_USE_RAG` : activer/désactiver l'utilisation du RAG côté bot.
- `OCR_LANG` : langues utilisées par Tesseract pour l'OCR (par défaut `fra+eng`).
- `ENABLE_CRON_JOBS` : si défini à `true`, active le cron crawler + re-embedding toutes les 2h.

### Tester la recherche sémantique
Utilisez `curl` pour poser une question :
```bash
curl -X POST "http://127.0.0.1:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "Quelle est la situation des élections en RDC ?"}'
```

### Accéder à la documentation
Une fois l'application lancée, la documentation Swagger est disponible sur :
`http://127.0.0.1:8000/docs`

## 🏁 Démarrage rapide (ordre conseillé)
1. Activer le venv et installer les dépendances (si besoin) :
   ```bash
   cd ai-service
   source .env/bin/activate
   pip install -r requirements.txt
   ```
2. Vérifier/éditer les variables dans `.env_file` (chargé automatiquement par l'API **et** les scripts crawler) : DB_*, BACKEND_ENDPOINT, CRAWLER_BACKEND_ENDPOINT, OLLAMA_HOST/OLLAMA_MODEL, USE_LLM_RAG, TELEGRAM_*.
3. (Optionnel) Réinitialiser la base et vider les données crawler :
   ```bash
   python -m app.maintenance.reset_all
   ```
4. Lancer l’API FastAPI :
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
5. Lancer un crawl direct (exemple radiookapi) ou toutes les sources (crawler HTML) :
   ```bash
   python -m app.services.crawler.scripts.sync --source-id radiookapi.net --limit 20
   # ou tout le catalogue depuis data/crawler/sources.json (env auto-chargé depuis .env_file/.env)
   python -m app.services.crawler.scripts.sync --source-id all --limit 20
   ```
   Les définitions de sources sont dans `data/crawler/sources.json` (HTML + WordPress).
6. Rejouer un JSONL vers le backend si besoin :
   ```bash
   python -m app.services.crawler.scripts.replay_jsonl \
     --file data/crawler/radiookapi.net.jsonl \
     --endpoint http://127.0.0.1:8000 \
     --batch-size 50
   ```
7. Vérifier Ollama / modèles locaux (pour le résumé RAG) :
   ```bash
   curl -s http://127.0.0.1:11434/api/tags | jq .
   ```
   Ajuster `OLLAMA_MODEL` dans `.env_file` (défaut: mistral).
8. Démarrer le bot Telegram :
    - Renseigner `TELEGRAM_BOT_TOKEN` (et éventuellement `TELEGRAM_ALLOWED_CHAT_IDS`, `TELEGRAM_TOP_K`, `TELEGRAM_USE_RAG`).
    - Le polling Telegram est maintenant **intégré dans FastAPI** : il démarre automatiquement avec la commande :
       ```bash
       uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
       ```
    - Aucun script `run_bot` séparé n'est nécessaire.
    - **Flux supportés côté bot Telegram :**
      - Message texte → RAG texte (streaming Mistral) avec affichage immédiat des SOURCES LOCALES puis de la réponse.
      - Photo contenant du texte → téléchargement de l'image, OCR local (Tesseract), puis même pipeline RAG texte.

## 🧭 Guide opérationnel (étapes)
1. **Activer l'env & deps**
   ```bash
   cd ai-service
   source .env/bin/activate
   pip install -r requirements.txt
   ```
2. **Configurer `.env_file`** (chargé automatiquement par l'API, le crawler et les scripts) : DB_*, BACKEND_ENDPOINT/CRAWLER_BACKEND_ENDPOINT, OLLAMA_HOST/OLLAMA_MODEL, USE_LLM_RAG, TELEGRAM_*.
3. **(Optionnel) Réinitialiser DB + données crawler**
   ```bash
   python -m app.maintenance.reset_all
   ```
4. **Démarrer l'API FastAPI (sans CRON automatique)**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
5. **Crawler (HTML / WordPress) — manuel**
   - Une source :
     ```bash
     python -m app.services.crawler.scripts.sync --source-id radiookapi.net --limit 20
     ```
   - Toutes les sources déclarées (`data/crawler/sources.json`) :
     ```bash
     python -m app.services.crawler.scripts.sync --source-id all --limit 20
     ```
   Les articles sont sauvés en JSONL (`data/crawler/{source}.jsonl`) et envoyés au backend si `CRAWLER_BACKEND_ENDPOINT` est défini.

### Mise à jour continue du corpus et du moteur de recommandation

Le système ne se contente pas de répondre à une question ponctuelle : il s'appuie sur un moteur de recommandation d'articles basé sur des embeddings sémantiques et une base vectorielle.

- **Alimentation par le crawler**  
   À chaque exécution du crawler (scripts `sync` et `replay_jsonl`), les nouveaux articles sont envoyés à l'API. Le service d'articles calcule automatiquement un vecteur d'« embedding » pour chaque texte et l'enregistre dans la colonne `embedding` de la table `articles`. L'index `articles_embedding_idx` (pgvector) est mis à jour de manière transparente par PostgreSQL.

- **Recommandation lors des requêtes RAG**  
   Lors d'un appel à `/query`, `/rag`, `/rag/stream` ou `/rag/image`, le service `RetrievalService` interroge cette base vectorielle pour sélectionner les `top_k` articles les plus proches sémantiquement de la question. Ces articles jouent le rôle de **recommandations contextuelles** que le modèle Mistral utilise comme preuves avant de générer une réponse.

- **Ré-embedding et évolution du modèle**  
   En cas de changement de modèle d'embedding ou pour améliorer la qualité globale du moteur de recommandation, il est possible de relancer un ré-embedding complet ou partiel :
   ```bash
   python - <<'PY'
   from app.services.train_pipeline import run_reembedding
   print(run_reembedding(batch_size=50, force_all=False))
   PY
   ```
   Cette opération recalcule les vecteurs, réindexe `articles_embedding_idx` et permet au système de bénéficier d'un espace sémantique plus performant sans ré-entraîner le LLM Mistral lui-même.
6. **Rejouer un JSONL vers le backend** (si besoin) :
   ```bash
   python -m app.services.crawler.scripts.replay_jsonl \
     --file data/crawler/radiookapi.net.jsonl \
     --endpoint http://127.0.0.1:8000 \
     --batch-size 50
   ```
7. **Ré-embedding / rafraîchir l'index pgvector — manuel**
   ```bash
   python - <<'PY'
   from app.services.train_pipeline import run_reembedding
   print(run_reembedding(batch_size=50, force_all=False))
   PY
   ```
   - `force_all=True` pour tout recalculer.
   - Les runs sont tracés dans `training_runs` et l'index `articles_embedding_idx` est réindexé en fin de job.
8. **RAG / requêtes**
   - Via API: POST `/query` avec `{ "query": "..." }`.
   - Modèle utilisé côté embeddings: `EmbeddingService` (Sentence Transformers). Génération (résumé/synthèse) : `OLLAMA_MODEL` si activé.
9. **Bot Telegram**
   - Utilise `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BACKEND_ENDPOINT`, `TELEGRAM_ALLOWED_CHAT_IDS`, `TELEGRAM_USE_RAG`, `TELEGRAM_TOP_K`.
   - Est démarré automatiquement avec FastAPI via le polling (`getUpdates`).
   - Gère :
     - Texte → RAG texte (streaming)
     - Image → OCR local puis RAG texte

10. **WhatsApp (Cloud API)**
   - Webhook `/webhooks/whatsapp` pour recevoir les messages Meta.
   - Variables : `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_VERIFY_TOKEN`.
   - Gère :
     - Texte → RAG texte (réponse complète).
     - Image → téléchargement via l'API Graph, OCR local (Tesseract), puis RAG texte.

## 📦 Ce que fait le projet
- **FastAPI backend** : ingestion d’articles, recherche RAG, endpoints crawler.
- **Crawler HTML/WordPress** : sources définies dans `data/crawler/sources.json`, export JSONL, push API optionnel.
- **Stockage vectoriel** : PostgreSQL + pgvector (`articles.embedding`, index `articles_embedding_idx`).
- **Embeddings** : Sentence Transformers (défaut paraphrase-multilingual-MiniLM-L12-v2, dataset all-MiniLM-L6-v2), normalisation cosinus.
- **Re-embedding pipeline** : `app/services/train_pipeline.py` pour recalculer embeddings et rafraîchir l’index; journalisation dans `training_runs`.
- **RAG/Ollama** : `OLLAMA_HOST`/`OLLAMA_MODEL` pour la génération locale; top-K configurable.
- **Telegram bot** : capture des requêtes, relaye vers le backend/RAG, paramètres via env.
