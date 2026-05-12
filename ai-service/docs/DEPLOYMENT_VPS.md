# 🚀 Guide de Setup VPS — RDC AI Service (FastAPI)

## Prérequis VPS

- Ubuntu 22.04 LTS
- Python 3.11+
- PostgreSQL (avec pgvector)
- Nginx (reverse proxy)
- SSH configuré

---

## 1. Structure des répertoires à créer (UNE SEULE FOIS)

Connecte-toi au VPS et exécute :

```bash
# Créer toute la structure de déploiement
mkdir -p /home/rooney/web/rooney-rdc/ai-service/{releases,shared/models_cache,shared/data,logs}

# Vérifier
tree /home/rooney/web/rooney-rdc/ai-service/ -L 2
```

La structure finale sera :
```
/home/rooney/web/rooney-rdc/ai-service/
├── releases/
│   └── <version>/      ← chaque déploiement
├── shared/
│   ├── .env            ← ⚠ À CRÉER MANUELLEMENT (secrets)
│   ├── models_cache/   ← modèles IA (persistants, jamais supprimés)
│   └── data/           ← datasets (persistants)
├── current -> releases/<latest>   ← symlink (géré auto)
├── venv/               ← virtualenv Python (partagé entre releases)
└── logs/
    └── uvicorn.log
```

---

## 2. Fichier `.env` de production (CRITIQUE)

Créer le fichier de secrets **manuellement**, il ne sera jamais écrasé par le CI :

```bash
nano /home/rooney/web/rooney-rdc/ai-service/shared/.env
```

Contenu minimal (adapte les valeurs) :

```env
# Base de données
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rdc_news
DB_USER=postgres
DB_PASSWORD=TON_MOT_DE_PASSE_PROD
DATABASE_URL=postgresql://postgres:TON_MOT_DE_PASSE_PROD@localhost:5432/rdc_news

# LLM / Ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=mistral
USE_LLM_RAG=true

# Telegram
TELEGRAM_BOT_TOKEN=VOTRE_TOKEN
TELEGRAM_BACKEND_ENDPOINT=http://127.0.0.1:8000
TELEGRAM_ALLOWED_CHAT_IDS=
TELEGRAM_TOP_K=3
TELEGRAM_USE_RAG=true
TELEGRAM_POLLING=false   # true seulement si pas de webhook actif

# WhatsApp
WHATSAPP_TOKEN=VOTRE_TOKEN
WHATSAPP_PHONE_ID=VOTRE_PHONE_ID

# Cron Jobs (désactivé par défaut)
ENABLE_CRON_JOBS=false
ENABLE_TELEGRAM_POLLING=false

# Backend Laravel/Symfony
CRAWLER_BACKEND_ENDPOINT=http://127.0.0.1:8000
BACKEND_ENDPOINT=http://127.0.0.1:8000

# Dataset
DISABLE_DATASET_AUTOLOAD=true
```

---

## 3. Installation du service systemd (UNE SEULE FOIS)

```bash
# Copier le fichier de service
sudo cp /home/rooney/web/rooney-rdc/ai-service/current/scripts/rdc-ai-service.service \
        /etc/systemd/system/rdc-ai-service.service

# Recharger systemd
sudo systemctl daemon-reload

# Activer le démarrage automatique
sudo systemctl enable rdc-ai-service

# Démarrer le service
sudo systemctl start rdc-ai-service

# Vérifier le statut
sudo systemctl status rdc-ai-service
```

### Alternative — PM2 (si tu n’utilises pas systemd pour l’IA)

Le dépôt fournit [`ai-service/ecosystem.config.cjs`](../ecosystem.config.cjs). Sur le VPS :

```bash
cd /chemin/vers/ai-service   # ex. .../rdc-news-intelligence/ai-service
```

1. Crée un **venv** dans `ai-service` si besoin :  
   `python3 -m venv venv && ./venv/bin/pip install -r requirements.txt`  
   Le fichier `ecosystem.config.cjs` détecte automatiquement `venv/`, `.venv/` ou `.env/`.  
   Sinon : `export RDC_AI_PYTHON=/chemin/vers/bin/python`.

2. Le port par défaut est **8000** (aligné avec la section Nginx ci‑dessous). Pour changer :
   `export APP_PORT=8000`

3. Démarre et persiste :

```bash
pm2 start ecosystem.config.cjs
pm2 save
pm2 startup    # une fois : suivre la commande affichée pour l’auto-start au boot
```

Contrôle :

```bash
curl -sS http://127.0.0.1:8000/health
pm2 logs rdc-ai-service --lines 80
```

**À ne pas faire :** lancer en parallèle **systemd `rdc-ai-service`** et **PM2** sur le même port — un seul superviseur pour ce processus.

---

## 4. Configuration Nginx (reverse proxy)

```nginx
server {
    listen 80;
    server_name rooney-rdc.rooneykalumba.tech;  # adapte si nécessaire

    # Redirection vers le service FastAPI
    location /ai/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Pour le streaming (SSE / chunked responses)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # Webhooks Telegram / WhatsApp directement
    location /webhooks/ {
        proxy_pass http://127.0.0.1:8000/webhooks/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/rooney-rdc /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 5. Secrets GitHub à configurer

Dans **Settings > Secrets and variables > Actions** de ton repo :

| Secret | Valeur | Description |
|---|---|---|
| `SSH_PRIVATE_KEY` | Contenu de ta clé privée SSH | `cat ~/.ssh/id_rsa` |
| `SSH_HOST` | IP ou domaine du VPS | ex: `45.12.34.56` |
| `SSH_PORT` | Port SSH | ex: `22` ou `2222` |
| `SSH_USER` | Utilisateur SSH | `rooney` |
| `AI_DEPLOY_PATH` | Chemin de déploiement | `/home/rooney/web/rooney-rdc/ai-service` |

### Générer et configurer la clé SSH (si pas encore fait)

```bash
# Sur ta machine locale
ssh-keygen -t ed25519 -C "github-ci-rdc-news" -f ~/.ssh/github_ci_rdc

# Ajouter la clé publique sur le VPS
ssh-copy-id -i ~/.ssh/github_ci_rdc.pub rooney@TON_VPS_IP

# Copier la clé privée dans GitHub Secrets (SSH_PRIVATE_KEY)
cat ~/.ssh/github_ci_rdc
```

---

## 6. Commandes utiles sur le VPS

```bash
# Voir les logs en temps réel
journalctl -u rdc-ai-service -f

# Redémarrer après un changement de .env
sudo systemctl restart rdc-ai-service

# Voir la release active
ls -la /home/rooney/web/rooney-rdc/ai-service/current

# Tester l'API localement
curl http://localhost:8000/health
curl http://localhost:8000/docs   # Swagger UI

# Rollback vers une version précédente
ln -sfn /home/rooney/web/rooney-rdc/ai-service/releases/ANCIENNE_VERSION \
         /home/rooney/web/rooney-rdc/ai-service/current
sudo systemctl restart rdc-ai-service
```

---

## 7. Sudoers (pour que le CI puisse restart le service)

```bash
sudo visudo
```

Ajouter à la fin :

```
# GitHub CI — allow rooney to manage rdc-ai-service
rooney ALL=(ALL) NOPASSWD: /bin/systemctl restart rdc-ai-service, /bin/systemctl start rdc-ai-service, /bin/systemctl stop rdc-ai-service, /bin/systemctl status rdc-ai-service
```

---

## 8. Ajouter un endpoint `/health` à FastAPI (recommandé)

Dans `ai-service/app/main.py`, ajoute :

```python
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "rdc-ai-service"}
```
