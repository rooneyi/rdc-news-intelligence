#!/usr/bin/env bash
# Diagnostic Telegram : la requête arrive-t-elle sur le VPS ?
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PORT="$("${ROOT}/scripts/read_app_port.sh")"
TOKEN="$("${ROOT}/scripts/read_env_var.sh" TELEGRAM_BOT_TOKEN)"
POLL="$("${ROOT}/scripts/read_env_var.sh" ENABLE_TELEGRAM_POLLING)"
[[ -z "${POLL}" ]] && POLL="$("${ROOT}/scripts/read_env_var.sh" TELEGRAM_POLLING)"
DOMAIN="${TELEGRAM_WEBHOOK_DOMAIN:-rooney-rdc.rooneykalumba.tech}"

echo "=============================================="
echo "  Diagnostic Telegram — réception VPS"
echo "=============================================="
echo ""
echo "APP_PORT=${PORT}"
echo "ENABLE_TELEGRAM_POLLING=${POLL:-(absent → polling OFF)}"
echo "TELEGRAM_BOT_TOKEN=$([[ -n "${TOKEN}" ]] && echo '(défini)' || echo 'ABSENT')"
echo ""

if [[ -z "${TOKEN}" ]]; then
  echo "ERREUR : TELEGRAM_BOT_TOKEN absent dans .env / .env_file" >&2
  exit 1
fi

echo "=== PM2 rdc-ai-service ==="
pm2 describe rdc-ai-service 2>/dev/null | grep -E 'status|restarts|uptime' || echo "(process absent)"
echo ""

echo "=== Variables PM2 (Telegram) ==="
pm2 env 0 2>/dev/null | grep -E 'TELEGRAM|ENABLE_TELEGRAM' || \
  pm2 show rdc-ai-service 2>/dev/null | grep -i telegram || \
  echo "(pm2 env indisponible — vérifie .env)"
echo ""

echo "=== API Telegram : getMe ==="
curl -sS --max-time 10 "https://api.telegram.org/bot${TOKEN}/getMe"
echo ""
echo ""

echo "=== API Telegram : getWebhookInfo ==="
WEBHOOK_JSON="$(curl -sS --max-time 10 "https://api.telegram.org/bot${TOKEN}/getWebhookInfo")"
echo "${WEBHOOK_JSON}"
echo ""

WEBHOOK_URL="$(echo "${WEBHOOK_JSON}" | node -e "
let s=''; process.stdin.on('data',d=>s+=d); process.stdin.on('end',()=>{
  try { const j=JSON.parse(s); process.stdout.write(j.result?.url||''); } catch { process.exit(0); }
});")"
PENDING="$(echo "${WEBHOOK_JSON}" | node -e "
let s=''; process.stdin.on('data',d=>s+=d); process.stdin.on('end',()=>{
  try { const j=JSON.parse(s); process.stdout.write(String(j.result?.pending_update_count??0)); } catch { process.exit(0); }
});")"

echo "=== Mode détecté ==="
if [[ "${POLL}" =~ ^(1|true|yes)$ ]]; then
  echo "Config : POLLING (getUpdates dans FastAPI)"
  if [[ -n "${WEBHOOK_URL}" ]]; then
    echo "PROBLÈME : webhook encore actif (${WEBHOOK_URL}) → getUpdates bloqué."
    echo "  ./scripts/fix_telegram.sh"
  else
    echo "Webhook : vide (OK pour polling)"
  fi
else
  echo "Config : WEBHOOK HTTPS (polling désactivé dans .env)"
  if [[ -z "${WEBHOOK_URL}" ]]; then
    echo "PROBLÈME : aucun webhook → Telegram n'envoie rien au VPS."
    echo "  ./scripts/fix_telegram.sh --webhook"
  else
    echo "Webhook URL : ${WEBHOOK_URL}"
    echo "Mises à jour en attente chez Telegram : ${PENDING}"
  fi
fi
echo ""

if [[ "${POLL}" =~ ^(1|true|yes)$ ]] && pm2 describe rdc-ai-service &>/dev/null; then
  echo "=== Test getUpdates ==="
  echo "SKIPPÉ — le polling PM2 tourne déjà ; un curl getUpdates ici provoque une erreur 409."
  echo "Envoie un vrai message au bot puis : pm2 logs rdc-ai-service | grep 'Message texte reçu'"
else
  echo "=== Test getUpdates (timeout 3s) ==="
  UPDATES="$(curl -sS --max-time 8 "https://api.telegram.org/bot${TOKEN}/getUpdates?timeout=3&limit=3")"
  echo "${UPDATES}" | head -c 600
  echo ""
  if echo "${UPDATES}" | grep -q '"ok":false'; then
    echo "→ getUpdates REFUSÉ"
  fi
fi
echo ""

echo "=== Doublons polling (409) ==="
if pm2 logs rdc-ai-service --lines 100 --nostream 2>/dev/null | grep -q 'other getUpdates'; then
  echo "PROBLÈME DÉTECTÉ : conflit 409 — deux instances pollent le même bot."
  echo "  ./scripts/telegram_stop_duplicates.sh --restart"
else
  echo "(pas de 409 récent dans les logs — OK ou polling arrêté)"
fi
echo ""

echo "=== Test route locale POST /webhooks/telegram ==="
curl -sS -o /dev/null -w "HTTP %{http_code}\n" \
  -X POST "http://127.0.0.1:${PORT}/webhooks/telegram" \
  -H "Content-Type: application/json" \
  -d '{"message":{"message_id":1,"chat":{"id":123,"type":"private"},"text":"ping-check"}}' || \
  echo "→ FastAPI injoignable sur :${PORT}"
echo ""

echo "=== Test webhook PUBLIC (si mode webhook) ==="
curl -sS -o /dev/null -w "HTTP %{http_code}\n" \
  -X POST "https://${DOMAIN}/webhooks/telegram" \
  -H "Content-Type: application/json" \
  -d '{"message":{"message_id":1,"chat":{"id":123,"type":"private"},"text":"ping-public"}}' || \
  echo "→ HTTPS webhook inaccessible"
echo ""

echo "=== Logs démarrage / réception Telegram ==="
pm2 logs rdc-ai-service --lines 300 --nostream 2>/dev/null \
  | grep -iE 'TelegramPolling|Startup\]\[Telegram|Telegram webhook|Message texte reçu' \
  | tail -25 || echo "(aucune trace Telegram — polling probablement OFF ou pas redémarré)"
echo ""

echo "=== Correction recommandée ==="
echo "  cd ${ROOT} && ./scripts/fix_telegram.sh"
echo "Puis envoie un message au bot et surveille :"
echo "  pm2 logs rdc-ai-service --lines 0 | grep -i telegram"
