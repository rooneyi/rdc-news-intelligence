# Déploiement VPS + migration — guide pas à pas

Guide opérationnel pour **tout migrer** depuis ta machine locale vers **un seul VPS** (FastAPI + PostgreSQL + Chroma + Ollama + Redis).

Remplace les variables :

| Variable | Exemple |
|----------|---------|
| `VPS_USER` | `rooney` |
| `VPS_HOST` | `rooney-rdc.rooneykalumba.tech` ou IP |
| `DEPLOY_PATH` | `/home/rooney/web/rooney-rdc/ai-service` |
| `DOMAIN` | `rooney-rdc.rooneykalumba.tech` |

---

## Vue d’ensemble (ordre des étapes)

```
LOCAL                          VPS
─────                          ───
1. pg_dump + chroma_db    →    4. PostgreSQL + Chroma
2. .env (secrets)         →    5. .env production
3. code (git/scp)         →    6. venv + pip
                               7. Ollama + Redis
                               8. PM2 / systemd
                               9. Nginx HTTPS
                               10. Webhook Whapi
```

---

## Étape 0 — Prérequis VPS

**Matériel :** 8 Go RAM minimum (Ollama + embeddings + Postgres).

Sur le VPS (SSH) :

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-venv python3-pip \
  postgresql postgresql-contrib \
  tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng \
  redis-server nginx curl
```

**Ollama :**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral:7b-instruct-v0.3-q4_K_M
sudo systemctl enable ollama
sudo systemctl start ollama
curl http://127.0.0.1:11434/api/tags
```

**PostgreSQL — créer la base :**

```bash
sudo -u postgres psql <<'SQL'
CREATE USER rdc_user WITH PASSWORD 'CHANGER_MOT_DE_PASSE';
CREATE DATABASE rdc_news OWNER rdc_user;
GRANT ALL PRIVILEGES ON DATABASE rdc_news TO rdc_user;
SQL
```

**Redis :**

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
redis-cli ping   # doit répondre PONG
```

---

## Étape 1 — Préparer le dossier sur le VPS

```bash
ssh VPS_USER@VPS_HOST
mkdir -p DEPLOY_PATH
exit
```

**Option A — Git (recommandé pour le code) :**

```bash
ssh VPS_USER@VPS_HOST
cd DEPLOY_PATH/..
git clone https://github.com/TON_USER/rdc-news-intelligence.git .
cd ai-service
```

**Option B — Copie depuis ta machine (sans git sur VPS) :**

```bash
# Sur ta machine locale
cd /chemin/vers/rdc-news-intelligence/ai-service
tar --exclude='venv' --exclude='.venv' --exclude='models_cache' \
    --exclude='__pycache__' -czf /tmp/ai-service-code.tar.gz .
scp /tmp/ai-service-code.tar.gz VPS_USER@VPS_HOST:/tmp/
ssh VPS_USER@VPS_HOST "mkdir -p DEPLOY_PATH && tar -xzf /tmp/ai-service-code.tar.gz -C DEPLOY_PATH"
```

---

## Étape 2 — Exporter les données (machine locale)

### 2.1 Dump PostgreSQL

```bash
cd ai-service
source venv/bin/activate   # ou .venv

pg_dump -h localhost -U postgres -d rdc_news -Fc -f /tmp/rdc_news.dump
# Adapter -U et -d selon ton .env_file (DATABASE_URL)
```

### 2.2 Copier ChromaDB (rapide si déjà à 100 %)

```bash
# Depuis la racine ai-service
tar -czf /tmp/chroma_db.tar.gz -C data chroma_db
ls -lh /tmp/rdc_news.dump /tmp/chroma_db.tar.gz
```

**Alternative :** ne pas copier Chroma ; sur le VPS après import Postgres :

```bash
python scripts/sync_to_chroma.py --batch-size 50
```

*(Plus long mais évite les erreurs de version Chroma.)*

### 2.3 Sauvegarder les secrets

```bash
cp .env_file /tmp/rdc_env_backup.txt
# Ne jamais committer ce fichier
```

---

## Étape 3 — Transférer vers le VPS

```bash
scp /tmp/rdc_news.dump VPS_USER@VPS_HOST:/tmp/
scp /tmp/chroma_db.tar.gz VPS_USER@VPS_HOST:/tmp/
scp /tmp/rdc_env_backup.txt VPS_USER@VPS_HOST:/tmp/rdc_env_backup.txt
```

---

## Étape 4 — Python et dépendances sur le VPS

```bash
ssh VPS_USER@VPS_HOST
cd DEPLOY_PATH

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

---

## Étape 5 — Fichier `.env` production

```bash
cd DEPLOY_PATH
cp /tmp/rdc_env_backup.txt .env
nano .env
```

**Profil VPS tout-en-un (Whapi + polling local) — à adapter :**

```env
# Base
DATABASE_URL=postgresql://rdc_user:CHANGER_MOT_DE_PASSE@127.0.0.1:5432/rdc_news
REDIS_URL=redis://127.0.0.1:6379/0

# Ollama (sur le même VPS)
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=mistral:7b-instruct-v0.3-q4_K_M
RAG_ENABLE_RERANK=false

# Whapi
WHAPI_TOKEN=ton_token_whapi
WHAPI_WEBHOOK_PROXY_ONLY=true
ENABLE_WHAPI_QUEUE_POLLING=true
WHAPI_QUEUE_TOKEN=un_secret_long
WHAPI_REPLY_RELAY_TOKEN=un_autre_secret
WHAPI_QUEUE_POP_URL=http://127.0.0.1:8000/webhooks/whapi/queue/pop
WHAPI_REPLY_RELAY_URL=http://127.0.0.1:8000/webhooks/whapi/reply-relay

# Optionnel
ENABLE_CRON_JOBS=true
TELEGRAM_BOT_TOKEN=
ENABLE_TELEGRAM_POLLING=false
```

> Sur le **même VPS**, utilise toujours `127.0.0.1:8000` pour queue/relay (pas le domaine public) — évite les 502 du proxy.

---

## Étape 6 — Importer PostgreSQL

```bash
ssh VPS_USER@VPS_HOST
pg_restore -h 127.0.0.1 -U rdc_user -d rdc_news -Fc --clean --if-exists /tmp/rdc_news.dump
# --clean : remplace les tables existantes

psql -h 127.0.0.1 -U rdc_user -d rdc_news -c "SELECT COUNT(*) FROM articles;"
```

---

## Étape 7 — Importer ChromaDB

```bash
cd DEPLOY_PATH
mkdir -p data
tar -xzf /tmp/chroma_db.tar.gz -C data
ls data/chroma_db
```

**Ou reconstruction :**

```bash
cd DEPLOY_PATH
source venv/bin/activate
python scripts/sync_to_chroma.py --batch-size 50
```

Vérifier :

```bash
./venv/bin/python -c "from app.services.vector_store_service import VectorStoreService as V; print(V().collection.count())"
```

---

## Étape 8 — Démarrer l’API (PM2)

```bash
cd DEPLOY_PATH
pm2 start ecosystem.config.cjs
pm2 save
pm2 startup   # suivre les instructions une fois
pm2 logs rdc-ai-service
```

**Test local sur le VPS :**

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/admin/overview
```

---

## Étape 9 — Reverse proxy HTTPS (Nginx)

Exemple `/etc/nginx/sites-available/rdc-news` :

```nginx
server {
    listen 443 ssl;
    server_name DOMAIN;

  ssl_certificate     /chemin/fullchain.pem;
  ssl_certificate_key /chemin/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/rdc-news /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
curl https://DOMAIN/health
```

*(OpenLiteSpeed : même principe — proxy `/health` et `/webhooks/` vers port 8000.)*

---

## Étape 10 — Configurer Whapi

1. Dashboard Whapi → **Webhook URL** :  
   `https://DOMAIN/webhooks/whapi`
2. Vérifier que `WHAPI_TOKEN` est dans `.env`.
3. `WHAPI_WEBHOOK_PROXY_ONLY=true` + `ENABLE_WHAPI_QUEUE_POLLING=true`.
4. Envoyer un message **privé** test sur WhatsApp.

Logs :

```bash
pm2 logs rdc-ai-service
tail -f DEPLOY_PATH/../.logs/fastapi.log
```

---

## Étape 11 — Checklist finale

| Test | Commande / action |
|------|-------------------|
| Santé API | `curl https://DOMAIN/health` |
| Articles | `curl https://DOMAIN/admin/overview` |
| Postgres | `SELECT COUNT(*) FROM articles;` |
| Ollama | `curl http://127.0.0.1:11434/api/tags` |
| Redis | `redis-cli ping` |
| RAG (lent) | `curl -X POST http://127.0.0.1:8000/rag -H "Content-Type: application/json" -d '{"query":"Ebola RDC","top_k":3}'` |
| WhatsApp | Message test privé |

---

## Mises à jour ultérieures (sans tout refaire)

**Code seulement :**

```bash
git pull   # sur le VPS
./venv/bin/pip install -r requirements.txt
pm2 restart rdc-ai-service
```

**Nouveaux articles en local → VPS :**

```bash
# Local
pg_dump ... -f rdc_news.dump
scp rdc_news.dump VPS:/tmp/
# VPS
pg_restore ... /tmp/rdc_news.dump
python scripts/sync_to_chroma.py
pm2 restart rdc-ai-service
```

---

## Dépannage rapide

| Symptôme | Cause probable | Action |
|----------|----------------|--------|
| 502 sur `/webhooks/` | Proxy pas vers uvicorn | Nginx → `127.0.0.1:8000` |
| Pas de réponse WhatsApp | Polling off / Redis down | `ENABLE_WHAPI_QUEUE_POLLING`, `redis-cli ping` |
| Ollama 500 | RAM insuffisante | VPS 8 Go+, `RAG_ENABLE_RERANK=false` |
| NON VÉRIFIABLE partout | Chroma vide | `sync_to_chroma.py` |
| Timeout queue | URL publique au lieu de local | `WHAPI_*_URL=http://127.0.0.1:8000/...` |

---

*Voir aussi [`Chapitre_4_Deploiement.md`](Chapitre_4_Deploiement.md).*
