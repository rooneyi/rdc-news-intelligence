#!/usr/bin/env bash
# Bascule FastAPI + URLs internes Whapi/Meta vers un autre port (défaut 8001).
# À utiliser quand le port 8000 est occupé par un autre service (page HTML 400).
#
# Usage :
#   ./scripts/switch_fastapi_port.sh        # → 8001
#   ./scripts/switch_fastapi_port.sh 8002
#
# Après bascule : mets à jour nginx (Hestia) proxy_pass vers le nouveau port
# pour /health et /webhooks/ si le webhook Whapi passe par le domaine public.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

NEW_PORT="${1:-8001}"
ENV_FILE="${ROOT}/.env"
touch "${ENV_FILE}"

set_kv() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}"
  else
    echo "${key}=${val}" >> "${ENV_FILE}"
  fi
}

echo "=== Bascule FastAPI vers le port ${NEW_PORT} (.env) ==="

set_kv "APP_PORT" "${NEW_PORT}"
set_kv "WHAPI_QUEUE_POP_URL" "http://127.0.0.1:${NEW_PORT}/webhooks/whapi/queue/pop"
set_kv "WHAPI_REPLY_RELAY_URL" "http://127.0.0.1:${NEW_PORT}/webhooks/whapi/reply-relay"
set_kv "WHATSAPP_QUEUE_POP_URL" "http://127.0.0.1:${NEW_PORT}/webhooks/whatsapp/queue/pop"
set_kv "WHATSAPP_REPLY_RELAY_URL" "http://127.0.0.1:${NEW_PORT}/webhooks/whatsapp/reply-relay"
set_kv "CRAWLER_BACKEND_ENDPOINT" "http://127.0.0.1:${NEW_PORT}"
set_kv "BACKEND_ENDPOINT" "http://127.0.0.1:${NEW_PORT}"

echo "Variables mises à jour dans ${ENV_FILE}"
echo ""
echo "IMPORTANT nginx / Hestia : si Whapi webhook → domaine public, modifie le proxy :"
echo "  proxy_pass http://127.0.0.1:${NEW_PORT};   # pour /health et /webhooks/"
echo ""
echo "Puis : ./scripts/pm2_reload_env.sh"
echo ""

exec "${ROOT}/scripts/pm2_reload_env.sh"
