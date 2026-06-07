#!/usr/bin/env bash
# Corrige : TypeError Router.__init__() got an unexpected keyword argument 'on_startup'
# Cause : Starlette 1.0 incompatible avec FastAPI 0.115 (pip a installé starlette>=1.0).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ ! -x "${ROOT}/venv/bin/pip" ]]; then
  echo "Erreur : venv absent. Lance : python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

echo "=== Pin starlette < 1.0 ==="
"${ROOT}/venv/bin/pip" install 'starlette>=0.40.0,<1.0.0'
"${ROOT}/venv/bin/pip" show starlette | grep -E '^Version|^Name'

echo ""
echo "=== Redémarrage PM2 ==="
pm2 restart rdc-ai-service --update-env
sleep 5
curl -sf "http://127.0.0.1:$("${ROOT}/scripts/read_app_port.sh")/health" && echo "" || echo "(health KO — voir pm2 logs)"
