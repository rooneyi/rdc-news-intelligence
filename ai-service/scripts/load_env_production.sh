#!/usr/bin/env bash
# Charge ai-service/.env dans le shell courant (export).
# Usage sur le VPS :
#   cd .../ai-service
#   source scripts/load_env_production.sh
#   python -m app.services.crawler.scripts.sync --source-id radiookapi.net --limit 5

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Fichier absent : ${ENV_FILE}" >&2
  echo "Copiez : cp .env.production.example .env puis éditez les secrets." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

echo "Variables chargées depuis ${ENV_FILE}"
echo "  CRAWLER_BACKEND_ENDPOINT=${CRAWLER_BACKEND_ENDPOINT:-non défini}"
echo "  WHAPI_WEBHOOK_PROXY_ONLY=${WHAPI_WEBHOOK_PROXY_ONLY:-non défini}"
echo "  ENABLE_WHAPI_QUEUE_POLLING=${ENABLE_WHAPI_QUEUE_POLLING:-non défini}"
echo "  OLLAMA_MODEL=${OLLAMA_MODEL:-non défini}"
