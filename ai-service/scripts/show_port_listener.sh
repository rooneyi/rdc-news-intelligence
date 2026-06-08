#!/usr/bin/env bash
# Affiche qui écoute sur un port TCP (sans sudo quand possible).
set -euo pipefail
PORT="${1:-8000}"

echo "=== ss -tlnp :${PORT} ==="
ss -tlnp 2>/dev/null | grep ":${PORT} " || echo "(aucun listener)"

echo ""
echo "=== fuser :${PORT}/tcp ==="
if command -v fuser >/dev/null 2>&1; then
  fuser -v "${PORT}/tcp" 2>/dev/null || echo "(fuser : PID invisible sans sudo — essaie: sudo fuser -v ${PORT}/tcp)"
else
  echo "(fuser absent)"
fi

echo ""
echo "=== lsof :${PORT} ==="
if command -v lsof >/dev/null 2>&1; then
  lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null || echo "(lsof : rien ou droits insuffisants — essaie: sudo lsof -nP -iTCP:${PORT} -sTCP:LISTEN)"
else
  echo "(lsof absent)"
fi
