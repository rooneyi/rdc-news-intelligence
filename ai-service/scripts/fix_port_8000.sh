#!/usr/bin/env bash
# Libère le port FastAPI et redémarre un seul rdc-ai-service.
#
# Symptômes :
#   - address already in use ('0.0.0.0', 8000)
#   - [Whapi Queue] HTTP 400 + page HTML sur queue/pop
#   - curl /health ne renvoie pas du JSON rdc-ai-service
#
# Usage VPS :
#   cd ~/web/.../rdc-news-intelligence/ai-service
#   ./scripts/fix_port_8000.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PORT="$("${ROOT}/scripts/read_app_port.sh")"

is_fastapi_health() {
  local body
  body="$(curl -sS --max-time 4 "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
  echo "${body}" | grep -q '"service"[[:space:]]*:[[:space:]]*"rdc-ai-service"'
}

echo "=== Port ${PORT} — écoute ==="
ss -tln 2>/dev/null | grep ":${PORT} " || echo "(aucun listener)"

if is_fastapi_health; then
  echo "FastAPI (rdc-ai-service) répond déjà correctement sur :${PORT}/health"
  echo "Relance propre PM2 seulement..."
  exec "${ROOT}/scripts/pm2_reload_env.sh"
fi

if curl -sS --max-time 4 "http://127.0.0.1:${PORT}/health" 2>/dev/null | grep -qi '<!doctype html'; then
  echo ""
  echo "ATTENTION : un AUTRE programme occupe le port ${PORT} (page HTML, pas FastAPI)."
  echo "Ce n'est pas rdc-ai-service — d'où les erreurs Whapi 400."
fi

echo ""
echo "=== PID sur le port ${PORT} ==="
if command -v fuser >/dev/null 2>&1; then
  fuser -v "${PORT}/tcp" 2>/dev/null || echo "(fuser : aucun PID visible — essaie: sudo fuser -v ${PORT}/tcp)"
fi
if command -v lsof >/dev/null 2>&1; then
  lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null || true
fi

echo ""
echo "=== PM2 (avant nettoyage) ==="
pm2 list 2>/dev/null || true

echo ""
echo "=== Arrêt PM2 rdc-ai-service ==="
pm2 delete rdc-ai-service 2>/dev/null || pm2 stop rdc-ai-service 2>/dev/null || true
sleep 2

echo ""
echo "=== Libération port ${PORT} ==="
if command -v fuser >/dev/null 2>&1; then
  fuser -k "${PORT}/tcp" 2>/dev/null || true
fi
pkill -f "uvicorn app.main:app.*--port ${PORT}" 2>/dev/null || true
sleep 2

if ss -tln 2>/dev/null | grep -q ":${PORT} "; then
  echo ""
  echo "ERREUR : le port ${PORT} est encore occupé (processus hors PM2 ou droits insuffisants)." >&2
  echo "Essaie :" >&2
  echo "  sudo fuser -v ${PORT}/tcp" >&2
  echo "  sudo fuser -k ${PORT}/tcp" >&2
  echo "  # ou change de port dans .env :" >&2
  echo "  ./scripts/switch_fastapi_port.sh 8001" >&2
  exit 1
fi

echo "Port ${PORT} libre."
echo ""
exec "${ROOT}/scripts/pm2_reload_env.sh"
