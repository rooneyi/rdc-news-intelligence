#!/usr/bin/env bash
# Diagnostic Telegram : webhook vs polling, token, logs PM2.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PORT="$("${ROOT}/scripts/read_app_port.sh")"
TOKEN="$("${ROOT}/scripts/read_env_var.sh" TELEGRAM_BOT_TOKEN)"
POLL="$("${ROOT}/scripts/read_env_var.sh" ENABLE_TELEGRAM_POLLING)"
[[ -z "${POLL}" ]] && POLL="$("${ROOT}/scripts/read_env_var.sh" TELEGRAM_POLLING)"
DOMAIN="${TELEGRAM_WEBHOOK_DOMAIN:-rooney-rdc.rooneykalumba.tech}"

echo "=============================================="
echo "  Diagnostic Telegram"
echo "=============================================="
echo ""
echo "APP_PORT=${PORT}"
echo "ENABLE_TELEGRAM_POLLING=${POLL:-(absent)}"
echo "TELEGRAM_BOT_TOKEN=$([[ -n "${TOKEN}" ]] && echo '(défini)' || echo 'ABSENT')"
echo ""

if [[ -z "${TOKEN}" ]]; then
  echo "ERREUR : TELEGRAM_BOT_TOKEN absent dans .env / .env_file" >&2
  exit 1
fi

echo "=== getMe ==="
curl -sS "https://api.telegram.org/bot${TOKEN}/getMe" | head -c 300
echo ""
echo ""

echo "=== getWebhookInfo ==="
WEBHOOK_JSON="$(curl -sS "https://api.telegram.org/bot${TOKEN}/getWebhookInfo")"
echo "${WEBHOOK_JSON}" | head -c 500
echo ""
echo ""

WEBHOOK_URL="$(echo "${WEBHOOK_JSON}" | node -e "
let s=''; process.stdin.on('data',d=>s+=d); process.stdin.on('end',()=>{
  try { const j=JSON.parse(s); process.stdout.write(j.result?.url||''); } catch { process.exit(0); }
});")"

if [[ -n "${WEBHOOK_URL}" ]]; then
  echo "Webhook actif : ${WEBHOOK_URL}"
  if [[ "${POLL}" =~ ^(1|true|yes)$ ]]; then
    echo ""
    echo "PROBLÈME : polling ET webhook actifs en même temps → le bot ne répond pas."
    echo "  ./scripts/fix_telegram.sh"
  fi
else
  echo "Webhook : aucun (OK pour le polling)"
fi

echo ""
echo "=== Test webhook local (si mode webhook) ==="
curl -sS -o /dev/null -w "HTTP %{http_code}\n" \
  -X POST "http://127.0.0.1:${PORT}/webhooks/telegram" \
  -H "Content-Type: application/json" \
  -d '{"message":{"chat":{"id":0,"type":"private"},"text":"ping"}}' || true

echo ""
echo "=== Logs PM2 Telegram (30 dernières lignes) ==="
pm2 logs rdc-ai-service --lines 200 --nostream 2>/dev/null \
  | grep -iE 'Telegram|telegram' | tail -30 || echo "(aucune ligne Telegram)"

echo ""
echo "=== Actions ==="
if [[ "${POLL}" =~ ^(1|true|yes)$ ]]; then
  echo "  Mode polling : ./scripts/fix_telegram.sh"
else
  echo "  Mode webhook : ./scripts/fix_telegram.sh --webhook"
  echo "  URL attendue : https://${DOMAIN}/webhooks/telegram"
fi
