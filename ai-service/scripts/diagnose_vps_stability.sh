#!/usr/bin/env bash
# Pourquoi le VPS « se coupe » ? — diagnostic mémoire, PM2, OOM, reboot.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=============================================="
echo "  Diagnostic stabilité VPS — $(date -Iseconds)"
echo "=============================================="
echo ""

echo "=== Uptime / reboot récent ==="
uptime
who -b 2>/dev/null || true
echo ""

echo "=== RAM + swap ==="
free -h
echo ""
if ! swapon --show 2>/dev/null | grep -q .; then
  echo "ATTENTION : pas de SWAP — OOM killer très probable avec Ollama + FastAPI."
fi
echo ""

echo "=== Top mémoire ==="
ps aux --sort=-%mem 2>/dev/null | head -12 || true
echo ""

echo "=== OOM killer (kernel a tué un processus ?) ==="
if command -v journalctl >/dev/null 2>&1; then
  journalctl -k --no-pager -n 30 2>/dev/null | grep -iE 'oom|killed process|out of memory' || echo "(aucun OOM récent dans journalctl -k)"
else
  dmesg 2>/dev/null | grep -iE 'oom|killed process' | tail -5 || echo "(dmesg indisponible)"
fi
echo ""

echo "=== PM2 ($(whoami)) ==="
pm2 list 2>/dev/null || echo "(PM2 absent)"
echo ""
for app in rdc-ai-service rdc-frontend; do
  if pm2 describe "$app" &>/dev/null; then
    echo "--- $app ---"
    pm2 describe "$app" 2>/dev/null | grep -E 'status|restarts|uptime|memory|unstable' || true
    echo ""
  fi
done

echo "=== Services système ==="
for svc in ollama postgresql redis-server nginx; do
  if systemctl is-active "$svc" &>/dev/null; then
    echo "  $svc : $(systemctl is-active $svc)"
  fi
done
echo ""

echo "=== Ollama ==="
curl -sS --max-time 3 http://127.0.0.1:11434/api/tags 2>/dev/null | head -c 200 || echo "Ollama injoignable"
echo ""
echo ""

PORT="$("${ROOT}/scripts/read_app_port.sh" 2>/dev/null || echo 8001)"
echo "=== FastAPI :${PORT}/health ==="
curl -sS --max-time 5 "http://127.0.0.1:${PORT}/health" 2>/dev/null | head -c 250 || echo "API injoignable"
echo ""
echo ""

echo "=== PM2 au boot (persistant ?) ==="
if systemctl is-enabled pm2-root &>/dev/null 2>&1; then
  echo "pm2-root : $(systemctl is-enabled pm2-root 2>/dev/null)"
elif systemctl is-enabled pm2-rooney &>/dev/null 2>&1; then
  echo "pm2-rooney : $(systemctl is-enabled pm2-rooney 2>/dev/null)"
else
  echo "PROBLÈME probable : PM2 pas activé au démarrage → après reboot VPS, rien ne tourne."
  echo "  Lance : ./scripts/vps_enable_auto_start.sh"
fi
echo ""

echo "=== Dernières lignes PM2 error (rdc-ai-service) ==="
pm2 logs rdc-ai-service --err --lines 15 --nostream 2>/dev/null | tail -15 || true
echo ""

echo "=== Causes fréquentes ==="
echo "  1. RAM saturée → Linux tue Ollama ou Python (OOM)"
echo "  2. PM2 max_memory_restart 2G → redémarrage brutal pendant le RAG"
echo "  3. Reboot VPS sans pm2 startup → services arrêtés"
echo "  4. Ollama arrêté (systemctl) → API vivante mais RAG/Telegram mort"
echo ""
echo "Correctifs : ./scripts/vps_enable_auto_start.sh"
echo "             modèle plus léger (qwen2.5:7b), RAG_ENABLE_RERANK=false"
echo "             swap 2-4 Go si RAM ≤ 8 Go"
