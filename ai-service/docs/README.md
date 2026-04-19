# RDC News Intelligence - Service IA (FastAPI)

Ce service constitue le cerveau du projet. Il gère la vectorisation des articles, la recherche sémantique (RAG) et les interactions avec les bots de messagerie.

## 🛠 Fonctionnalités Clés

1. **Recherche Sémantique (RAG)** : 
   - Utilise une base de données **pgvector** pour trouver les articles les plus proches de vos questions.
   - Génère des réponses factuelles via **Mistral-7B** (Ollama).
2. **Traitement d'Images (OCR)** : 
   - Extrait le texte des images/affiches pour vérifier leur contenu.
3. **Multi-Canaux** : 
   - Intégration directe via **Webhooks** pour WhatsApp et Telegram.
4. **Collecte Continue (Crawler)** : 
   - Scripts automatisés pour récupérer les nouvelles actualités de Radio Okapi et d'autres sources.

## 🚀 Installation Rapide

```bash
# 1. Préparer l'environnement
python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt

# 2. Lancer le service
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📂 Organisation du Service

- `app/api/` : Points d'entrée (Endpoints) et Webhooks.
- `app/services/` : Logique métier (RAG, OCR, Crawler).
- `data/crawler/` : Sources et fichiers temporaires de collecte.

## 🤖 Commandes Utiles

- **Lancer un crawl manuel** :
  `python -m app.services.crawler.scripts.sync --source-id all --limit 20`
- **Tester une question (curl)** :
  `curl -X POST "http://localhost:8000/query" -H "Content-Type: application/json" -d '{"query": "élections RDC"}'`

## 📖 Documentation API
Une fois lancé, accédez à la documentation interactive sur : [http://localhost:8000/docs](http://localhost:8000/docs)
