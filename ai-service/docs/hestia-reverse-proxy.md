# Reverse proxy FastAPI sur HestiaCP (sans sudo)

Quand `curl http://127.0.0.1:8000/health` répond OK mais  
`curl https://votre-domaine/health` renvoie **404 nginx**, le vhost ne proxifie pas vers uvicorn.

Sur Hestia, **ne modifiez pas** `nginx.ssl.conf` principal (écrasé au rebuild).  
Créez un fichier inclus automatiquement : `nginx.ssl.conf_*` dans le dossier domaine.

## 1. Fichier custom (HTTPS)

```bash
DOMAIN=rooney-rdc.rooneykalumba.tech
CONF_DIR="$HOME/conf/web/${DOMAIN}"
mkdir -p "${CONF_DIR}"

cat > "${CONF_DIR}/nginx.ssl.conf_rdc-api" <<'EOF'
# FastAPI (PM2 uvicorn) — chemins publics Whapi / santé / admin
location = /health {
    proxy_pass http://127.0.0.1:8000/health;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /webhooks/ {
    proxy_pass http://127.0.0.1:8000/webhooks/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 600s;
    client_max_body_size 20m;
}

location /admin/ {
    proxy_pass http://127.0.0.1:8000/admin/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /rag {
    proxy_pass http://127.0.0.1:8000/rag;
    proxy_set_header Host $host;
    proxy_read_timeout 600s;
}

location /docs {
    proxy_pass http://127.0.0.1:8000/docs;
    proxy_set_header Host $host;
}

location /openapi.json {
    proxy_pass http://127.0.0.1:8000/openapi.json;
    proxy_set_header Host $host;
}
EOF
```

Optionnel (redirections HTTP → HTTPS, si vous testez aussi en clair) :

```bash
cat > "${CONF_DIR}/nginx.conf_rdc-api" <<'EOF'
location = /health {
    proxy_pass http://127.0.0.1:8000/health;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
location /webhooks/ {
    proxy_pass http://127.0.0.1:8000/webhooks/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 600s;
}
EOF
```

## 2. Reconstruire le vhost (compte utilisateur)

```bash
v-rebuild-web-domain rooney rooney-rdc.rooneykalumba.tech
```

Si la commande `v-rebuild-web-domain` est introuvable :

```bash
export PATH="/usr/local/hestia/bin:$PATH"
v-rebuild-web-domain rooney rooney-rdc.rooneykalumba.tech
```

Sinon : panneau Hestia → **Web** → domaine → **Save** / **Rebuild** (selon version).

## 3. Vérifier

```bash
curl -s https://rooney-rdc.rooneykalumba.tech/health | jq .
curl -sI https://rooney-rdc.rooneykalumba.tech/webhooks/whapi
```

Attendu : JSON `{"status":"ok",...}` et plus de **404** sur `/health`.

Puis Whapi → webhook : `https://rooney-rdc.rooneykalumba.tech/webhooks/whapi`

## 4. Si ça ne change rien

1. Vérifier que l’include est bien généré :

   ```bash
   grep -n rdc-api /home/rooney/conf/web/rooney-rdc.rooneykalumba.tech/nginx.ssl.conf
   ```

2. Le site utilise peut‑être un **template proxy** différent — demander à l’admin d’activer le proxy ou d’exécuter le rebuild nginx.

3. **Ne pas** éditer à la main `/etc/nginx/` sans droits root.

## Alternative panneau Hestia

**Web** → `rooney-rdc.rooneykalumba.tech` → modifier le domaine :

- activer **Proxy** vers `127.0.0.1:8000` si vous voulez que **tout** le domaine pointe vers FastAPI (écrase le `public_html` à la racine) ;
- ou garder le snippet ci‑dessus pour ne proxifier que `/health` et `/webhooks/`.

Les URLs internes VPS restent en local :

```env
WHAPI_QUEUE_POP_URL=http://127.0.0.1:8000/webhooks/whapi/queue/pop
WHAPI_REPLY_RELAY_URL=http://127.0.0.1:8000/webhooks/whapi/reply-relay
```

## Frontend Next.js (autre domaine → port 3000)

Créez un **second domaine** Hestia (ex. `app.rooney-rdc.rooneykalumba.tech`) qui proxifie tout vers `127.0.0.1:3000`, sans toucher au domaine API.

Guide : [`frontend/docs/hestia-nextjs-domaine.md`](../../frontend/docs/hestia-nextjs-domaine.md).
