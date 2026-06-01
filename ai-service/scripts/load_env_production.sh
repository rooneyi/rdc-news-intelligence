#!/usr/bin/env bash
# Exporte les variables dans le shell courant (set -a).
# Ordre : .env_file puis .env (comme app/core/config.py).
#
# Usage :
#   cd .../ai-service
#   source scripts/load_env_production.sh
#   python -m app.services.crawler.scripts.sync --source-id radiookapi.net

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT}/.env_file"
DOT_ENV="${ROOT}/.env"

_load_file() {
  local f="$1"
  if [[ ! -f "${f}" ]] || [[ -d "${f}" ]]; then
    return 0
  fi
  set -a
  # shellcheck disable=SC1090
  source "${f}"
  set +a
  echo "  chargé : ${f}"
}

if [[ "${RDC_ENV_FILE_ONLY:-}" =~ ^(1|true|yes|on)$ ]]; then
  echo "Mode RDC_ENV_FILE_ONLY : .env_file seulement"
  _load_file "${ENV_FILE}"
else
  echo "Chargement des variables (export shell) :"
  _load_file "${ENV_FILE}"
  _load_file "${DOT_ENV}"
fi

echo ""
echo "Aperçu (sans afficher les secrets complets) :"
echo "  DB_HOST=${DB_HOST:-?} DB_USER=${DB_USER:-?} DB_NAME=${DB_NAME:-?}"
echo "  REDIS_URL=${REDIS_URL:-non défini}"
echo "  CRAWLER_BACKEND_ENDPOINT=${CRAWLER_BACKEND_ENDPOINT:-non défini}"
echo "  WHAPI_WEBHOOK_PROXY_ONLY=${WHAPI_WEBHOOK_PROXY_ONLY:-non défini}"
echo "  ENABLE_WHAPI_QUEUE_POLLING=${ENABLE_WHAPI_QUEUE_POLLING:-non défini}"
echo "  WHAPI_QUEUE_POP_URL=${WHAPI_QUEUE_POP_URL:-non défini}"
echo "  OLLAMA_MODEL=${OLLAMA_MODEL:-non défini}"
echo "  WHAPI_TOKEN=${WHAPI_TOKEN:+défini}${WHAPI_TOKEN:-absent}"
