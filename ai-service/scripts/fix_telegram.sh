#!/usr/bin/env bash
# Répare Telegram après changement de port / conflit webhook+polling.
#
# Usage :
#   ./scripts/fix_telegram.sh              # polling (supprime webhook)
#   ./scripts/fix_telegram.sh --webhook    # webhook HTTPS (désactive le polling dans .env)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

MODE="polling"
DOMAIN="${TELEGRAM_WEBHOOK_DOMAIN:-rooney-rdc.rooneykalumba.tech}"
for arg in "$@"; do
  [[ "${arg}" == "--webhook" ]] && MODE="webhook"
done

TOKEN="$("${ROOT}/scripts/read_env_var.sh" TELEGRAM_BOT_TOKEN)"
if [[ -z "${TOKEN}" ]]; then
  echo "ERREUR : TELEGRAM_BOT_TOKEN absent" >&2
  exit 1
fi

PORT="$("${ROOT}/scripts/read_app_port.sh")"
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

echo "=== Mode : ${MODE} (APP_PORT=${PORT}) ==="

if [[ "${MODE}" == "polling" ]]; then
  set_kv "ENABLE_TELEGRAM_POLLING" "true"
  set_kv "TELEGRAM_POLLING" "true"
  echo "Suppression webhook Telegram…"
  curl -sS "https://api.telegram.org/bot${TOKEN}/deleteWebhook?drop_pending_updates=true"
  echo ""
else
  set_kv "ENABLE_TELEGRAM_POLLING" "false"
  set_kv "TELEGRAM_POLLING" "false"
  WEBHOOK_URL="https://${DOMAIN}/webhooks/telegram"
  echo "Configuration webhook → ${WEBHOOK_URL}"
  curl -sS -G "https://api.telegram.org/bot${TOKEN}/setWebhook" \
    --data-urlencode "url=${WEBHOOK_URL}" \
    --data-urlencode "drop_pending_updates=true"
  echo ""
fi

# TELEGRAM_BACKEND_ENDPOINT n'est pas lu par le code — harmoniser quand même
set_kv "TELEGRAM_BACKEND_ENDPOINT" "http://127.0.0.1:${PORT}"

echo ""
echo "=== Redémarrage rdc-ai-service ==="
"${ROOT}/scripts/pm2_reload_env.sh"

echo ""
echo "=== Vérification ==="
"${ROOT}/scripts/check_telegram.sh"
