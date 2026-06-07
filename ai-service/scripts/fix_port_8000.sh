#!/usr/bin/env bash
# Libère le port FastAPI (8000 par défaut) et redémarre un seul rdc-ai-service.
#
# Symptômes :
#   - address already in use ('0.0.0.0', 8000)
#   - [Whapi Queue] HTTP 400 + page HTML sur queue/pop
#
# Usage VPS :
#   cd ~/web/rooney-rdc.rooneykalumba.tech/public_html/rdc-news-intelligence/ai-service
#   ./scripts/fix_port_8000.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PORT="$(node -e "console.log(require('./ecosystem.config.cjs').apps[0].env.APP_PORT||8000)")"

echo "=== Port ${PORT} — processus en écoute ==="
if command -v ss >/dev/null 2>&1; then
  ss -tlnp 2>/dev/null | grep ":${PORT} " || echo "(aucun listener ss)"
elif command -v lsof >/dev/null 2>&1; then
  lsof -i ":${PORT}" -sTCP:LISTEN 2>/dev/null || echo "(aucun listener lsof)"
else
  echo "(installe ss ou lsof pour le diagnostic)"
fi

echo ""
echo "=== PM2 (avant nettoyage) ==="
pm2 list 2>/dev/null || true

echo ""
echo "=== Arrêt PM2 rdc-ai-service ==="
pm2 delete rdc-ai-service 2>/dev/null || pm2 stop rdc-ai-service 2>/dev/null || true
sleep 2

echo ""
echo "=== Libération port ${PORT} (uvicorn / python orphelins) ==="
if command -v fuser >/dev/null 2>&1; then
  fuser -k "${PORT}/tcp" 2>/dev/null || true
fi
pkill -f "uvicorn app.main:app.*--port ${PORT}" 2>/dev/null || true
sleep 2

if command -v ss >/dev/null 2>&1 && ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
  echo "ERREUR : le port ${PORT} est encore occupé. PID(s) :" >&2
  ss -tlnp 2>/dev/null | grep ":${PORT} " >&2 || true
  echo "Tue manuellement : kill <pid> puis relance ./scripts/pm2_reload_env.sh" >&2
  exit 1
fi

echo "Port ${PORT} libre."
echo ""
exec "${ROOT}/scripts/pm2_reload_env.sh"
