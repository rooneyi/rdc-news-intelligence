# Frontend Next.js sur un domaine Hestia (port 3000)

Objectif : garder **l’API** sur un domaine (ex. `rooney-rdc.rooneykalumba.tech` → port **8000**) et le **site Next.js** sur **un autre domaine** (ex. `app.rooney-rdc.rooneykalumba.tech` → port **3000**).

## Architecture recommandée

| Domaine | Service | Port local |
|---------|---------|------------|
| `rooney-rdc.rooneykalumba.tech` | FastAPI (Whapi, `/health`, API JSON) | 8000 |
| `app.rooney-rdc.rooneykalumba.tech` *(exemple)* | Next.js (accueil, `/client`, `/admin`) | 3000 |

Évite le conflit `/admin` (FastAPI vs Next).

---

## 1. Créer le domaine dans Hestia

1. Panneau Hestia → **Web** → **Add web domain** (ou **Add subdomain**).
2. Domaine exemple : `app.rooney-rdc.rooneykalumba.tech`.
3. Utilisateur : `rooney`.
4. Activer **SSL** (Let’s Encrypt).
5. Laisser `public_html` vide ou minimal — tout passera par le proxy vers 3000.

---

## 2. Proxy nginx vers Next.js (port 3000)

En SSH (utilisateur `rooney`) ou en **root** :

```bash
APP_DOMAIN=app.rooney-rdc.rooneykalumba.tech   # ← votre nouveau domaine
CONF_DIR="/home/rooney/conf/web/${APP_DOMAIN}"

cat > "${CONF_DIR}/nginx.ssl.conf_rdc-next" <<'EOF'
# Next.js (PM2 rdc-frontend) — tout le site
location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400s;
}
EOF

chown rooney:rooney "${CONF_DIR}/nginx.ssl.conf_rdc-next"
```

Rebuild :

```bash
export PATH="/usr/local/hestia/bin:$PATH"
v-rebuild-web-domain rooney "${APP_DOMAIN}"
```

En **root** si besoin : `nginx -t && systemctl reload nginx`

---

## 3. Build et lancer Next.js sur le VPS

```bash
cd ~/web/rooney-rdc.rooneykalumba.tech/public_html/rdc-news-intelligence/frontend

cp .env.production.example .env.local
nano .env.local   # ADMIN_*, NEXT_PUBLIC_FASTAPI_URL=http://127.0.0.1:8000

npm ci
npm run build

mkdir -p logs
pm2 start ecosystem.config.cjs
pm2 save
```

Vérifier en local sur le VPS :

```bash
curl -sI http://127.0.0.1:3000/
curl -sI https://app.rooney-rdc.rooneykalumba.tech/
```

---

## 4. Variables importantes

| Variable | Valeur VPS typique |
|----------|-------------------|
| `NEXT_PUBLIC_FASTAPI_URL` | `http://127.0.0.1:8000` (pas le domaine public API obligatoire) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_SESSION_SECRET` | pour `/admin` Next |

Après modification de `.env.local` : `npm run build` puis `pm2 restart rdc-frontend`.

---

## 5. Panneau Hestia (alternative)

**Web** → votre nouveau domaine → **Proxy** / **Proxy Template** :

- Cible : `http://127.0.0.1:3000`

Équivalent au fichier `nginx.ssl.conf_rdc-next` ci-dessus.

---

## 6. DNS

Chez votre registrar, ajoutez un enregistrement **A** (ou CNAME) :

- `app` → IP du VPS (même IP que le domaine principal).

---

## Dépannage

| Symptôme | Action |
|----------|--------|
| 502 Bad Gateway | `pm2 logs rdc-frontend` — Next pas démarré ou pas build |
| Page Hestia par défaut | Rebuild domaine ; vérifier `grep rdc-next .../nginx.ssl.conf` |
| Admin 401 | Vérifier `ADMIN_*` dans `.env.local` + rebuild |
| RAG ne répond pas | FastAPI PM2 + `NEXT_PUBLIC_FASTAPI_URL=http://127.0.0.1:8000` |

---

*API sur le même domaine : voir `ai-service/docs/hestia-reverse-proxy.md` (chemins `/health`, `/webhooks` seulement).*
