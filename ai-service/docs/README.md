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

## 🔁 Architecture proxy WhatsApp (prod -> local -> prod -> Meta)

Ce mode permet de garder le webhook Meta sur le backend heberge, tout en traitant la logique IA en local.

### 1) Variables sur le backend heberge (celui configure dans Meta)

```env
# Forward des payloads recus de Meta vers le local
WHATSAPP_FORWARD_URL=https://<ton-tunnel-local>/webhooks/whatsapp
WHATSAPP_FORWARD_TOKEN=secret-forward
WHATSAPP_FORWARD_TIMEOUT=10

# Ne pas traiter localement sur le serveur heberge (evite double reponse)
WHATSAPP_WEBHOOK_PROXY_ONLY=true

# Endpoint qui recoit les reponses remontees depuis le local
WHATSAPP_REPLY_RELAY_TOKEN=secret-relay
```

### 2) Variables sur le local

```env
# Accepter les payloads forwarded par le backend heberge
WHATSAPP_FORWARD_TOKEN=secret-forward

# Remonter les reponses vers le backend heberge (qui envoie ensuite a Meta)
WHATSAPP_REPLY_RELAY_URL=https://<ton-backend-heberge>/webhooks/whatsapp/reply-relay
WHATSAPP_REPLY_RELAY_TOKEN=secret-relay
WHATSAPP_REPLY_RELAY_TIMEOUT=15
```

Notes:
- Le header `X-RDC-Forwarded: true` est ajoute automatiquement pour eviter les boucles.
- Le backend heberge expose `POST /webhooks/whatsapp/reply-relay` pour envoyer a WhatsApp Cloud API.

## ✅ Mode sans tunnel (PULL) recommande

Si ton local n'est pas exposable publiquement, utilise ce mode:

1. Meta -> `https://rooney-rdc.rooneykalumba.tech/webhooks/whatsapp`
2. Le backend heberge met le payload en file memoire.
3. Le local fait du polling sur `POST /webhooks/whatsapp/queue/pop`.
4. Le local traite puis remonte les reponses vers `POST /webhooks/whatsapp/reply-relay`.

### Variables backend heberge

```env
WHATSAPP_WEBHOOK_PROXY_ONLY=true
WHATSAPP_QUEUE_TOKEN=secret-queue
WHATSAPP_REPLY_RELAY_TOKEN=secret-relay
```

### Variables local

```env
ENABLE_WHATSAPP_QUEUE_POLLING=true
WHATSAPP_QUEUE_POP_URL=https://rooney-rdc.rooneykalumba.tech/webhooks/whatsapp/queue/pop
WHATSAPP_QUEUE_TOKEN=secret-queue
WHATSAPP_QUEUE_POLL_INTERVAL=2
WHATSAPP_QUEUE_TIMEOUT=15

WHATSAPP_REPLY_RELAY_URL=https://rooney-rdc.rooneykalumba.tech/webhooks/whatsapp/reply-relay
WHATSAPP_REPLY_RELAY_TOKEN=secret-relay
WHATSAPP_REPLY_RELAY_TIMEOUT=15
```

### Worker sur le même VPS que FastAPI (PM2 / uvicorn)

Si le polling et l’API tournent **sur la même machine**, n’appelle pas le domaine public en HTTPS : OpenLiteSpeed / nginx peut renvoyer **502** ou une page HTML si `/webhooks/` n’est pas encore proxifié vers uvicorn. Utilise l’URL **locale** (même port que PM2, souvent `8000`) :

```env
WHATSAPP_QUEUE_POP_URL=http://127.0.0.1:8000/webhooks/whatsapp/queue/pop
WHATSAPP_REPLY_RELAY_URL=http://127.0.0.1:8000/webhooks/whatsapp/reply-relay
```

Pour **`https://…/health`** en JSON : configure le reverse proxy (vhost) avec une règle qui envoie `/health` et `/webhooks/` vers `http://127.0.0.1:8000`, ou teste en SSH avec `curl http://127.0.0.1:8000/health`.
