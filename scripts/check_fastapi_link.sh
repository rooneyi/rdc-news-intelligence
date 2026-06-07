#!/usr/bin/env bash
# Diagnostic : pourquoi Next.js ne joint pas FastAPI (ECONNREFUSED / HTML).
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AI="${REPO}/ai-service"
FE="${REPO}/frontend"

PORT="8000"
if [[ -x "${AI}/scripts/read_app_port.sh" ]]; then
  PORT="$("${AI}/scripts/read_app_port.sh")"
fi

echo "=============================================="
echo "  Diagnostic FastAPI ↔ Next.js"
echo "=============================================="
echo ""

echo "=== PM2 ==="
pm2 list 2>/dev/null || echo "(pm2 indisponible)"
echo ""

echo "=== Port FastAPI attendu : ${PORT} ==="
ss -tln 2>/dev/null | grep ":${PORT} " || echo "(rien n'écoute sur :${PORT})"
if command -v lsof >/dev/null 2>&1; then
  sudo lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null || lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null || true
fi
echo ""

echo "=== curl health ==="
HEALTH="$(curl -sS --max-time 5 "http://127.0.0.1:${PORT}/health" 2>&1 || true)"
if echo "${HEALTH}" | grep -q '"service"'; then
  echo "OK — ${HEALTH}" | head -c 400
  echo ""
else
  echo "KO — pas de JSON rdc-ai-service :"
  echo "${HEALTH}" | head -c 500
  echo ""
  echo ""
  echo "Dernières lignes pm2 error :"
  pm2 logs rdc-ai-service --err --lines 12 --nostream 2>/dev/null | tail -12 || true
fi
echo ""

echo "=== Starlette (incompatibilité FastAPI 0.115) ==="
if [[ -x "${AI}/venv/bin/pip" ]]; then
  "${AI}/venv/bin/pip" show starlette 2>/dev/null | grep -E '^Version' || echo "(starlette non installé)"
else
  echo "(venv absent dans ai-service)"
fi
echo ""

echo "=== Frontend .env.local (FASTAPI_URL) ==="
if [[ -f "${FE}/.env.local" ]]; then
  grep -E '^(FASTAPI_URL|NEXT_PUBLIC_FASTAPI_URL)=' "${FE}/.env.local" 2>/dev/null || echo "(clés absentes — ajoute FASTAPI_URL=http://127.0.0.1:${PORT})"
else
  echo "Fichier absent — crée ${FE}/.env.local avec :"
  echo "  FASTAPI_URL=http://127.0.0.1:${PORT}"
fi
echo ""

echo "=== Actions suggérées ==="
echo "  cd ${AI} && ./scripts/fix_starlette_pin.sh"
echo "  cd ${AI} && ./scripts/admin_clean_start.sh --with-frontend"
echo "  cd ${FE} && pm2 restart rdc-frontend --update-env"
