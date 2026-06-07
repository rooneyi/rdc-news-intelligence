#!/usr/bin/env bash
# Recharge FastAPI via PM2 en injectant .env_file + .env (voir ecosystem.config.cjs).
#
# Usage sur le VPS :
#   cd ~/web/.../rdc-news-intelligence/ai-service
#   ./scripts/pm2_reload_env.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ ! -f "${ROOT}/.env" && ! -f "${ROOT}/.env_file" ]]; then
  echo "Erreur : ni .env ni .env_file dans ${ROOT}" >&2
  exit 1
fi

PORT="$("${ROOT}/scripts/read_app_port.sh")"

is_fastapi_up() {
  local body
  body="$(curl -sS --max-time 5 "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
  echo "${body}" | grep -q '"service"[[:space:]]*:[[:space:]]*"rdc-ai-service"'
}

echo "=== Rechargement PM2 avec variables .env_file + .env (port ${PORT}) ==="
node -e "
const c = require('./ecosystem.config.cjs');
const e = c.apps[0].env;
const keys = ['APP_PORT','WHAPI_TOKEN','ENABLE_WHAPI_QUEUE_POLLING','WHAPI_WEBHOOK_PROXY_ONLY','WHAPI_QUEUE_POP_URL','REDIS_URL','OLLAMA_MODEL','DB_USER'];
for (const k of keys) {
  const v = e[k];
  if (v === undefined) console.log('  ' + k + ': (absent)');
  else if (k.includes('TOKEN') || k.includes('PASSWORD')) console.log('  ' + k + ': (défini)');
  else console.log('  ' + k + ': ' + v);
}
" 2>/dev/null

if command -v ss >/dev/null 2>&1 && ss -tln 2>/dev/null | grep -q ":${PORT} "; then
  if ! is_fastapi_up; then
    echo ""
    echo "ERREUR : le port ${PORT} est pris par un AUTRE service (pas rdc-ai-service)."
    echo "  sudo fuser -v ${PORT}/tcp"
    echo "  sudo fuser -k ${PORT}/tcp && ./scripts/pm2_reload_env.sh"
    echo "  # ou bascule : ./scripts/switch_fastapi_port.sh 8001"
    exit 1
  fi
fi

if pm2 describe rdc-ai-service &>/dev/null; then
  pm2 restart ecosystem.config.cjs --update-env
else
  pm2 start ecosystem.config.cjs
fi

pm2 save
echo ""
echo "=== Contrôle Whapi (fusion .env_file + .env) ==="
"${ROOT}/scripts/check_env_whapi.sh" || true
echo ""
echo "Vérification API (attente démarrage 20s) :"
for i in 1 2 3 4; do
  sleep 5
  if is_fastapi_up; then
    curl -sS "http://127.0.0.1:${PORT}/health"
    echo ""
    break
  fi
  if [[ "${i}" -eq 4 ]]; then
    echo "(health non joignable après 20s)"
    echo "Dernières lignes PM2 :"
    pm2 logs rdc-ai-service --lines 25 --nostream 2>/dev/null | tail -25 || true
    echo ""
    echo "Si « address already in use » : ./scripts/switch_fastapi_port.sh 8001"
    exit 1
  fi
done

echo ""
echo "Test queue Whapi (JSON attendu) :"
QUEUE_TOKEN="$("${ROOT}/scripts/read_env_var.sh" WHAPI_QUEUE_TOKEN)"
if [[ -z "${QUEUE_TOKEN}" ]]; then
  QUEUE_TOKEN="$("${ROOT}/scripts/read_env_var.sh" WHATSAPP_QUEUE_TOKEN)"
fi
CURL_ARGS=(-sS -X POST "http://127.0.0.1:${PORT}/webhooks/whapi/queue/pop" -H "Content-Type: application/json" -d '{}')
if [[ -n "${QUEUE_TOKEN}" ]]; then
  CURL_ARGS+=(-H "X-RDC-Queue-Token: ${QUEUE_TOKEN}")
fi
if curl "${CURL_ARGS[@]}" | grep -q '"status"'; then
  curl "${CURL_ARGS[@]}"
  echo ""
else
  echo "(queue/pop échoue — mauvais service sur le port ${PORT} ?)"
  curl "${CURL_ARGS[@]}" | head -c 200 || true
  echo ""
fi

echo ""
echo "Logs Whapi au démarrage (dernier boot) :"
pm2 logs rdc-ai-service --lines 40 --nostream 2>/dev/null | grep -E 'Startup\]\[Whapi|Whapi Queue|Polling file Whapi|address already in use' || true
