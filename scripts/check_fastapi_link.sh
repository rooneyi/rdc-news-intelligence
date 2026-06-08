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

echo "=== PM2 ($(whoami)) ==="
pm2 list 2>/dev/null || echo "(pm2 indisponible)"
if command -v sudo >/dev/null 2>&1; then
  echo ""
  echo "=== PM2 (root — si les apps tournent en root) ==="
  sudo pm2 list 2>/dev/null | head -20 || echo "(sudo pm2 indisponible ou mot de passe requis)"
fi
echo ""

echo "=== Port FastAPI attendu : ${PORT} ==="
if [[ -x "${AI}/scripts/show_port_listener.sh" ]]; then
  "${AI}/scripts/show_port_listener.sh" "${PORT}"
else
  ss -tln 2>/dev/null | grep ":${PORT} " || echo "(rien n'écoute sur :${PORT})"
fi
echo ""

echo "=== curl health ==="
HEALTH="$(curl -sS --max-time 5 "http://127.0.0.1:${PORT}/health" 2>&1 || true)"
if echo "${HEALTH}" | grep -q '"service"'; then
  echo "OK — ${HEALTH}" | head -c 400
  echo ""
elif echo "${HEALTH}" | grep -qi '<!doctype html'; then
  echo "KO — AUTRE SERVICE sur :${PORT} (HTML, pas FastAPI). Souvent Django/Gunicorn."
  echo "${HEALTH}" | head -c 300
  echo ""
  echo ""
  echo "→ Lance : cd ai-service && ./scripts/recover_api.sh"
  echo "  (libère 8000 avec sudo, ou bascule auto vers 8001)"
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
echo "  cd ${AI} && ./scripts/recover_api.sh"
echo "  # si port 8000 bloqué par root/autre user :"
echo "  sudo fuser -v ${PORT}/tcp && sudo fuser -k ${PORT}/tcp"
echo "  cd ${AI} && ./scripts/recover_api.sh"
echo "  # ou PM2 root : sudo pm2 delete rdc-ai-service && cd ${AI} && ./scripts/recover_api.sh"
