# Implémenter le crawler en Python

Ce document décrit une implémentation Python qui reproduit le comportement du crawler actuel:

- HTTP robuste (timeout, retry, backoff, `Retry-After`, user-agent)
- extraction Open Graph
- persistance locale `.jsonl`
- forwarding vers le backend (`/articles`, `/sources/update-dates`)

## 1) Parité fonctionnelle avec le crawler TypeScript

Référence côté TS:

- `apps/crawler/src/http/http-client.ts`
- `apps/crawler/src/http/open-graph.ts`
- `apps/crawler/src/process/persistence.ts`
- `apps/crawler/src/process/crawler.ts`

Objectif Python: garder la même séparation des responsabilités.

## 2) Stack Python recommandée

- Python `>=3.11`
- `httpx` (client HTTP sync/async)
- `tenacity` (retry/backoff)
- `selectolax` ou `beautifulsoup4` (parse HTML)
- `pydantic` (validation/config)
- `orjson` (JSON rapide)
- `structlog` ou `logging` standard

Installation:

```bash
python -m venv .venv
source .venv/bin/activate
pip install httpx tenacity selectolax pydantic orjson
```

## 3) Structure de dossier proposée

```text
python-crawler/
  pyproject.toml
  src/
    crawler/
      __init__.py
      config.py
      constants.py
      logger.py
      models.py
      utils.py
      http/
        __init__.py
        user_agent.py
        http_client.py
        open_graph.py
      process/
        __init__.py
        crawler.py
        persistence.py
      scripts/
        sync.py
        async_worker.py
```

## 4) Modèles et config

### `models.py` (minimum)

```python
from pydantic import BaseModel, HttpUrl
from typing import Optional, List


class ArticleMetadata(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[HttpUrl] = None
    url: Optional[HttpUrl] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    updated_at: Optional[str] = None


class Article(BaseModel):
    source_id: str
    link: HttpUrl
    title: str
    body: str
    categories: List[str] = []
    hash: str
```

### `config.py`

Expose une config équivalente à `config.crawler.fetch.client` et `config.crawler.backend`:

- `timeout_seconds`
- `max_retries`
- `backoff_initial`, `backoff_multiplier`, `backoff_max`
- `respect_retry_after`
- `follow_redirects`
- `backend_endpoint`
- `backend_token`
- `data_dir`

## 5) Client HTTP robuste

### `http/http_client.py`

Points clés à reproduire:

- timeout par requête
- retry sur statuts transients (`429`, `500`, `502`, `503`, `504`)
- respect de `Retry-After` quand présent
- backoff exponentiel + jitter sinon
- exception dédiée type `HttpError`

Exemple simplifié:

```python
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx


TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


class HttpError(Exception):
    def __init__(self, message: str, response: httpx.Response):
        super().__init__(message)
        self.response = response
        self.status = response.status_code


@dataclass
class HttpSettings:
    timeout_seconds: float = 20
    max_retries: int = 3
    backoff_initial: float = 0.5
    backoff_multiplier: float = 2.0
    backoff_max: float = 10.0
    respect_retry_after: bool = True
    follow_redirects: bool = True
    user_agent: str = "BasangoCrawler/1.0"


class SyncHttpClient:
    def __init__(self, settings: HttpSettings):
        self.settings = settings
        self.client = httpx.Client(
            timeout=settings.timeout_seconds,
            follow_redirects=settings.follow_redirects,
            headers={"User-Agent": settings.user_agent},
        )

    def _compute_backoff(self, attempt: int) -> float:
        base = min(
            self.settings.backoff_initial * (self.settings.backoff_multiplier ** attempt),
            self.settings.backoff_max,
        )
        jitter = random.random() * base * 0.25
        return base + jitter

    def _retry_after_seconds(self, response: httpx.Response) -> Optional[float]:
        if not self.settings.respect_retry_after:
            return None
        value = response.headers.get("Retry-After")
        if not value:
            return None
        if value.isdigit():
            return float(value)
        return None

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self.client.request(method, url, **kwargs)
                if response.status_code in TRANSIENT_STATUSES and attempt < self.settings.max_retries:
                    sleep_s = self._retry_after_seconds(response) or self._compute_backoff(attempt)
                    time.sleep(sleep_s)
                    continue
                if response.is_error:
                    raise HttpError(f"HTTP {response.status_code}", response)
                return response
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt >= self.settings.max_retries:
                    raise
                time.sleep(self._compute_backoff(attempt))
        raise RuntimeError("HTTP request failed") from last_error

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)
```

## 6) Open Graph

### `http/open_graph.py`

But:

- fetch HTML via `SyncHttpClient`
- parser le HTML
- extraire: `og:title`, `og:description`, `og:image`, `og:url`, `article:author`, `article:published_time`, `article:modified_time`
- fallback sur `<title>`, meta `description`, `link[rel=canonical]`
- convertir les URLs relatives en absolues

Implémentation pratique:

- utilitaire `pick(*values)` pour prendre la première valeur non vide
- utilitaire `extract_meta(tree, key)` pour `property` ou `name`

## 7) Persistance et forwarding

### `process/persistence.py`

Parité avec la version TS:

- `sanitize(text)`
  - retire NBSP/zero-width chars
  - normalise les retours ligne
  - `strip()`
- `hash = md5(link)`
- persistance locale JSONL (une ligne JSON par article)
- `forward(article)` vers le backend

Exemple minimal:

```python
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import orjson


def sanitize(text: str) -> str:
    if not text:
        return text
    text = text.replace("\u00A0", " ")
    text = text.replace("\u202F", " ")
    text = text.replace("\u200B", "").replace("\u200C", "").replace("\u200D", "")
    text = text.replace("\uFEFF", "")
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


class JsonlPersistor:
    def __init__(self, data_dir: str, source_id: str):
        self.path = Path(data_dir)
        self.path.mkdir(parents=True, exist_ok=True)
        self.file = self.path / f"{source_id}.jsonl"
        self.file.touch(exist_ok=True)

    def persist(self, article: dict) -> None:
        payload = orjson.dumps(article)
        with self.file.open("ab") as f:
            f.write(payload + b"\n")


def make_hash(link: str) -> str:
    return hashlib.md5(link.encode("utf-8")).hexdigest()
```

## 8) Orchestrateur de crawl

### `process/crawler.py`

Le flux recommandé:

1. Charger la source + options (`source_id`, `page_range`, `date_range`, `category`)
2. Résoudre la config de run (similaire `resolveCrawlerConfig`)
3. Construire la liste des URLs à crawler
4. Pour chaque URL:
   - fetch
   - parse article + OG metadata
   - enrichir/normaliser
   - `persist(article)`
   - `forward(article)`
5. Fermer les persistors

Version sync d’abord, async ensuite.

## 9) Scripts CLI

### `scripts/sync.py`

Minimum:

- parse des arguments (`--source-id`, `--page-range`, `--date-range`, `--category`)
- init config/client/persistor
- exécution de la boucle sync
- code de sortie non-zéro si erreur fatale

Tu peux ajouter un `scripts/async_worker.py` quand la version sync est stable.

## 10) Checklist d’implémentation

1. Créer le package Python + config environnement
2. Implémenter `HttpClient` avec retry/backoff
3. Implémenter Open Graph parser
4. Implémenter `JsonlPersistor` + `forward`
5. Implémenter l’orchestrateur sync
6. Ajouter logs structurés
7. Tester sur 1 source de bout en bout
8. Ajouter mode async/worker

## 11) Tests recommandés

- unitaires:
  - `sanitize`
  - extraction Open Graph
  - calcul backoff/retry
- intégration:
  - un run complet sur une source mockée
  - vérification JSONL + appel backend mock

## 12) Conseils de migration progressive

- Étape 1: reproduire le comportement TS en sync uniquement
- Étape 2: valider la parité de données (mêmes champs, même hash)
- Étape 3: activer async/worker
- Étape 4: brancher monitoring/alerting

Cette approche permet d’avoir rapidement une version Python fiable sans casser le pipeline existant.
## 13) Comment lancer le crawler Python

### Prérequis

- Python `>=3.11` avec venv activé
- Redis en local (ou distant) si tu veux le mode async
- Env variables: `BASANGO_BACKEND_ENDPOINT`, `BASANGO_BACKEND_TOKEN`, `BASANGO_CRAWLER_DATA_DIR`, etc.
- Source configurée (depuis `@basango/domain/config` ou un fichier JSON local)

### 3 modes de lancement

#### **Mode 1: Sync (synchrone) — lancement immédiat et bloquant**

```bash
cd python-crawler
python -m crawler.scripts.sync --source-id radiookapi.net
```

**Flux interne:**
1. Parse CLI args (`--source-id`, `--page-range`, `--date-range`, `--category`)
2. Charge la source depuis la config
3. Instancie `SyncHttpClient` + `OpenGraph` + `JsonlPersistor`
4. Pour chaque URL:
   - fetch HTML via `SyncHttpClient` (timeout, retry, backoff)
   - parse avec `OpenGraph.consumeHtml()`
   - normalise + sanitize + hash
   - écrit dans `data/<source_id>.jsonl`
   - forward asynchrone vers l'API backend
5. Ferme le persistor (flush + sortie)
6. Exit code `0` si OK, `1` si erreur fatale

**Variantes:**

```bash
# Crawler les pages 1 à 5 seulement
python -m crawler.scripts.sync --source-id radiookapi.net --page-range 1:5

# Date range (YYYY-MM-DD:YYYY-MM-DD)
python -m crawler.scripts.sync --source-id radiookapi.net --date-range 2024-01-01:2024-01-31

# Crawler une seule catégorie
python -m crawler.scripts.sync --source-id radiookapi.net --category tech

# Combinaison
python -m crawler.scripts.sync --source-id radiookapi.net --page-range 1:10 --category tech
```

#### **Mode 2: Async (non-bloquant avec Redis/RQ) — schedule un job**

```bash
cd python-crawler
python -m crawler.scripts.async_schedule --source-id radiookapi.net
```

**Flux:**
1. Parse CLI args
2. Instancie un client Redis
3. Crée un job dans la queue Redis (serialisé en JSON)
4. Retourne immédiatement avec l'ID du job
5. **Le vrai travail** est fait par les workers (voir Mode 3)

**Avec options:**

```bash
python -m crawler.scripts.async_schedule \
  --source-id radiookapi.net \
  --page-range 1:5 \
  --date-range 2024-01-01:2024-01-31
```

Avantage: tu peux déclencher N crawls en parallèle sans attendre.

#### **Mode 3: Worker (longue durée) — consomme les jobs Redis**

```bash
cd python-crawler
python -m crawler.scripts.worker
```

**Flux:**
1. Instancie un client Redis
2. Lance une boucle qui écoute les queues
3. Pour chaque job reçu:
   - désérialise les paramètres
   - exécute `runAsyncCrawl()` (similaire à sync mais avec logs enrichis)
   - sauvegarde le résultat/erreur dans Redis
4. Gère SIGINT/SIGTERM pour fermer proprement

**Avec queue spécifique:**

```bash
# Écoute seulement la queue "articles"
python -m crawler.scripts.worker --queue articles

# Écoute plusieurs queues
python -m crawler.scripts.worker --queue articles --queue metadata
```

**Lancer plusieurs workers en parallèle:**

```bash
# Terminal 1: articles
python -m crawler.scripts.worker --queue articles

# Terminal 2: metadata
python -m crawler.scripts.worker --queue metadata

# Terminal 3: toutes les queues (fallback)
python -m crawler.scripts.worker
```

Redis distribue les jobs entre les workers.

---

### Anatomie d'un lancement Sync complet (pas à pas)

Commande: `python -m crawler.scripts.sync --source-id radiookapi.net`

| Étape | Code / Détail |
|-------|--------|
| **1. Parse CLI** | `argparse` extrait `source_id = "radiookapi.net"`, autres = None |
| **2. Load config** | Charge `HttpSettings`, `BackendConfig`, etc. depuis `.env` ou `config.py` |
| **3. Load source** | Récupère source depuis domaine (URL litiste, sélecteurs CSS, etc.) |
| **4. Init HTTP client** | `SyncHttpClient(HttpSettings(...))` → timeout 20s, max 3 retries, backoff exponentiel |
| **5. Init OpenGraph** | `OpenGraph(client)` → parser HTML avec user-agent OG spécialisé |
| **6. Init Persistor** | `JsonlPersistor(data_dir="data", source_id="radiookapi.net")` → fichier `data/radiookapi.net.jsonl` |
| **7. Build config** | Fusionne: config globale + source + CLI options → `CrawlerRunConfig` |
| **8. Scrape listing** | Utilise sélecteurs CSS pour extraire liste d'URLs d'articles |
| **9. Loop articles** | Pour chaque URL: |
| | a. `client.get(url)` → HTML, avec timeout + retry/backoff |
| | b. `OpenGraph.consumeHtml(html, url)` → `ArticleMetadata` |
| | c. Enrichir: ajouter source_id, categories, etc. |
| | d. Nettoyer: `sanitize(title)`, `sanitize(body)` → trim, pas de chars invisibles |
| | e. Hash: `make_hash(link)` → `md5(link)` |
| | f. `persistor.persist(article)` → écrit `{...}` en JSON, `\n` dans fichier |
| | g. `forward(article)` en thread → POST `/articles` au backend (non-bloquant) |
| **10. Close persistor** | Flush + attendre écritures finales |
| **11. Exit** | Code 0 si OK, 1 si erreur fatale |

Durée estimée: quelques secondes à plusieurs minutes selon le nombre d'articles.

---

### Fichiers générés après un run

```
data/
  radiookapi.net.jsonl  # articles crawlés, 1 JSON par ligne

# Exemple contenu (1 seule ligne):
{"source_id":"radiookapi.net","link":"https://radiookapi.net/article/123","title":"...","body":"...","categories":["tech"],"hash":"abc123..."}
```

---

### Intégration avec un scheduler (cron, systemd, PM2, etc.)

#### **Cron (toutes les heures)**

```bash
0 * * * * cd /path/to/python-crawler && /path/to/venv/bin/python -m crawler.scripts.sync --source-id radiookapi.net >> /var/log/crawler.log 2>&1
```

#### **Systemd timer**

```ini
# /etc/systemd/user/crawler.timer
[Unit]
Description=Run Python Crawler
After=network.target

[Timer]
OnBootSec=1min
OnUnitActiveSec=1h
AccuracySec=1min

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/user/crawler.service
[Unit]
Description=Python Crawler Sync

[Service]
Type=oneshot
ExecStart=/path/to/venv/bin/python -m crawler.scripts.sync --source-id radiookapi.net
WorkingDirectory=/path/to/python-crawler
```

#### **PM2 (avec workers)**

```javascript
// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: "crawler-worker-articles",
      script: "python",
      args: "-m crawler.scripts.worker --queue articles",
      instances: 1,
      autorestart: true,
      env: {
        PYTHONUNBUFFERED: 1,
      },
    },
    {
      name: "crawler-worker-metadata",
      script: "python",
      args: "-m crawler.scripts.worker --queue metadata",
      instances: 1,
      autorestart: true,
      env: {
        PYTHONUNBUFFERED: 1,
      },
    },
  ],
};
```

Lancer: `pm2 start ecosystem.config.js`

---

### Points clés à retenir

1. **Sync = bloquant**, idéal pour CLI manuel ou cron simple.
2. **Async + Worker = distribué**, idéal pour auto-scaling et plusieurs sources en parallèle.
3. **Chaque article**: HTTP (retry/backoff) → Parse OG → Normalize → JSONL + API.
4. **Erreurs réseau**: absorbées par backoff exponentiel jusqu'à `maxRetries`.
5. **Erreurs backend**: l'article reste dans `.jsonl`, retry possible plus tard.
6. **Parité TS-Python**: même pipeline, mêmes logs, mêmes fichiers `.jsonl`.