# Frontend Next.js sur Hestia (port 3000)

## Faut-il créer un nouveau domaine ?

**Non, ce n’est pas obligatoire.**

| Option | Nouveau domaine ? | Quand l’utiliser |
|--------|-------------------|------------------|
| **A — Même domaine que l’API** | **Non** | Un seul nom (`rooney-rdc.rooneykalumba.tech`) : nginx envoie `/webhooks` et `/health` vers FastAPI (8000), **tout le reste** vers Next (3000). |
| **B — Sous-domaine dédié** | **Oui** (ex. `app.…`) | Plus simple à comprendre ; site et API bien séparés. |

Vous pouvez rester sur **`rooney-rdc.rooneykalumba.tech`** avec l’option A (section ci-dessous).

---

## Option A — Même domaine que l’API (recommandé si un seul nom)

Pas de DNS supplémentaire. Vous complétez la config Hestia du domaine **déjà existant**.

| Chemin public | Service | Port |
|---------------|---------|------|
| `/health`, `/webhooks/` | FastAPI | 8000 |
| `/`, `/client`, `/admin` (interface Next) | Next.js | 3000 |

L’admin **web** est `/admin` (Next). L’API JSON `/admin/overview` est appelée **en interne** par Next (`/api/fastapi/…` → `127.0.0.1:8000`), pas besoin d’exposer `/admin/overview` au public.

### Fichier nginx (même domaine API)

```bash
DOMAIN=rooney-rdc.rooneykalumba.tech
CONF_DIR="/home/rooney/conf/web/${DOMAIN}"

cat > "${CONF_DIR}/nginx.ssl.conf_rdc-next" <<'EOF'
# --- FastAPI (priorité : chemins précis) ---
location = /health {
    proxy_pass http://127.0.0.1:8000/health;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /webhooks/ {
    proxy_pass http://127.0.0.1:8000/webhooks/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 600s;
    client_max_body_size 20m;
}

# --- Next.js : tout le reste (accueil, client, admin UI) ---
location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
EOF

export PATH="/usr/local/hestia/bin:$PATH"
v-rebuild-web-domain rooney "${DOMAIN}"
```

Gardez aussi `nginx.ssl.conf_rdc-api` si vous l’avez déjà (doublon partiel acceptable) ou **fusionnez** en un seul fichier `rdc-next` ci-dessus.

Vérification :

```bash
curl -s https://rooney-rdc.rooneykalumba.tech/health
curl -sI https://rooney-rdc.rooneykalumba.tech/
curl -sI https://rooney-rdc.rooneykalumba.tech/admin
```

Puis lancez Next (section « Build et PM2 » plus bas).

---

## Option B — Autre domaine / sous-domaine (optionnel)

Objectif : API sur `rooney-rdc…`, site sur `app.rooney-rdc…`.

| Domaine | Service | Port local |
|---------|---------|------------|
| `rooney-rdc.rooneykalumba.tech` | FastAPI (Whapi, `/health`) | 8000 |
| `app.rooney-rdc.rooneykalumba.tech` | Next.js | 3000 |

---

## 1. Créer le domaine dans Hestia (option B seulement)

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

## 2b. Proxy nginx (option B — sous-domaine dédié)

Voir bloc `APP_DOMAIN=app.rooney-rdc...` dans la section suivante du fichier (inchangé).

---

## 3. Build et lancer Next.js sur le VPS (options A et B)

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

## 5. Panneau Hestia 1.9 (domaine existant `rooney-rdc…`)

### Ce que vous voyez déjà (OK)

- **SSL** + **Let's Encrypt** cochés → certificat valide pour `rooney-rdc.rooneykalumba.tech`.
- **Modèle web Apache2 / PHP-FPM / proxy = `default`** → normal, mais **ce n’est pas encore Next.js**.

### Pourquoi `/admin` affiche la 404 Hestia (« Page Not Found »)

Avec **proxy = default**, nginx envoie le trafic vers **Apache / `public_html`**, pas vers **PM2 sur le port 3000**.  
`public_html` ne contient pas Next (le projet est dans `public_html/rdc-news-intelligence/`), d’où la page d’erreur Hestia.

### À faire dans le panneau + SSH

1. **Cocher** (recommandé) : **Activer la redirection automatique en HTTPS** → Enregistrer.
2. **Proxy vers Next (port 3000)** : `v-add-web-domain-proxy … 127.0.0.1 3000` est **incorrect** (Hestia attend un **nom de modèle**). Sur beaucoup de VPS, `v-list-web-templates-proxy` ne liste rien : il faut **créer** `proxy3000.tpl` + `proxy3000.stpl` (voir section 5b ci-dessous), puis :

   ```bash
   export PATH="/usr/local/hestia/bin:$PATH"
   v-add-web-domain-proxy rooney rooney-rdc.rooneykalumba.tech proxy3000 yes
   v-rebuild-web-domain rooney rooney-rdc.rooneykalumba.tech
   ```

   Panneau : **Modèle proxy** → `proxy3000` → Enregistrer.

3. **Fichier custom API** (root) — **sans** `location /` dedans (évite le doublon avec le proxy Hestia) :

   `nginx.ssl.conf_rdc-next` → seulement `/health` et `/webhooks/` vers le port **8000** (voir section « Option A » plus haut, blocs FastAPI uniquement).

4. **PM2** (user `rooney`) : `npm run build` puis `pm2 restart rdc-frontend`.

### Vérification

```bash
curl -sI http://127.0.0.1:3000/admin | head -5
curl -sI https://rooney-rdc.rooneykalumba.tech/admin | head -5
grep proxy_pass /home/rooney/conf/web/rooney-rdc.rooneykalumba.tech/nginx.ssl.conf
```

Attendu : `proxy_pass` vers **3000** sur `location /`, et `/admin` répond comme Next (pas la 404 Hestia).

### 5b. Créer le modèle `proxy3000` (si absent du serveur)

```bash
export PATH="/usr/local/hestia/bin:$PATH"
v-list-web-templates-proxy plain   # souvent vide sauf après création

TPL=/usr/local/hestia/data/templates/web/nginx

cat > "${TPL}/proxy3000.tpl" <<'EOF'
server {
	listen      %ip%:%proxy_port%;
	server_name %domain_idn% %alias_idn%;
	error_log   /var/log/%web_system%/domains/%domain%.error.log error;

	include %home%/%user%/conf/web/%domain%/nginx.conf_*;

	location / {
		proxy_pass http://127.0.0.1:3000;
		proxy_http_version 1.1;
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_set_header Upgrade $http_upgrade;
		proxy_set_header Connection "upgrade";
	}

	location /error/ {
		alias %home%/%user%/web/%domain%/document_errors/;
	}

	location ~ /\.(?!well-known\/|file) {
		return 404;
	}
}
EOF

cat > "${TPL}/proxy3000.stpl" <<'EOF'
server {
	listen      %ip%:%proxy_ssl_port% ssl;
	http2 on;
	server_name %domain_idn% %alias_idn%;
	error_log   /var/log/%web_system%/domains/%domain%.error.log error;

	ssl_certificate     %ssl_pem%;
	ssl_certificate_key %ssl_key%;
	ssl_stapling on;
	ssl_stapling_verify on;

	include %home%/%user%/conf/web/%domain%/nginx.ssl.conf_*;

	location / {
		proxy_pass http://127.0.0.1:3000;
		proxy_http_version 1.1;
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_set_header Upgrade $http_upgrade;
		proxy_set_header Connection "upgrade";
	}

	location /error/ {
		alias %home%/%user%/web/%domain%/document_errors/;
	}

	location ~ /\.(?!well-known\/|file) {
		return 404;
	}
}
EOF

chmod 644 "${TPL}/proxy3000.tpl" "${TPL}/proxy3000.stpl"
chown root:root "${TPL}/proxy3000.tpl" "${TPL}/proxy3000.stpl"

v-list-web-templates-proxy plain
v-add-web-domain-proxy rooney rooney-rdc.rooneykalumba.tech proxy3000 yes
v-rebuild-web-domain rooney rooney-rdc.rooneykalumba.tech
```

Ensuite fichier **`nginx.ssl.conf_rdc-next`** (health + webhooks → 8000 uniquement).

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

*Détails API seule : `ai-service/docs/hestia-reverse-proxy.md`.*
