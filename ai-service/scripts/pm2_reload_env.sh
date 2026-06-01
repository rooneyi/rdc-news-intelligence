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

echo "=== Rechargement PM2 avec variables .env_file + .env ==="
node -e "
const c = require('./ecosystem.config.cjs');
const e = c.apps[0].env;
const keys = ['WHAPI_TOKEN','ENABLE_WHAPI_QUEUE_POLLING','WHAPI_WEBHOOK_PROXY_ONLY','WHAPI_QUEUE_POP_URL','REDIS_URL','OLLAMA_MODEL','DB_USER'];
for (const k of keys) {
  const v = e[k];
  if (v === undefined) console.log('  ' + k + ': (absent)');
  else if (k.includes('TOKEN') || k.includes('PASSWORD')) console.log('  ' + k + ': (défini)');
  else console.log('  ' + k + ': ' + v);
}
"

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
echo "Vérification API (attente démarrage 8s) :"
sleep 8
PORT="$(node -e "console.log(require('./ecosystem.config.cjs').apps[0].env.APP_PORT||8000)")"
curl -sf "http://127.0.0.1:${PORT}/health" && echo "" || echo "(health non joignable — voir: pm2 logs rdc-ai-service --lines 50)"
echo ""
echo "Logs Whapi au démarrage (dernier boot) :"
pm2 logs rdc-ai-service --lines 40 --nostream 2>/dev/null | grep -E 'Startup\]\[Whapi|Whapi Queue|Polling file Whapi' || true
