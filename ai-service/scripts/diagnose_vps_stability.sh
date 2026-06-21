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
SWAP_TOTAL_KB="$(awk '/SwapTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
SWAP_USED_KB="$(awk '/SwapFree/ {free=$2} /SwapTotal/ {total=$2} END {print total-free}' /proc/meminfo 2>/dev/null || echo 0)"
if [[ "${SWAP_TOTAL_KB}" -eq 0 ]]; then
  echo "ATTENTION : pas de SWAP — risque OOM élevé avec Ollama + FastAPI."
else
  SWAP_USED_MB=$((SWAP_USED_KB / 1024))
  echo "Swap actif : ${SWAP_USED_MB} Mo utilisés sur $((SWAP_TOTAL_KB / 1024)) Mo."
  if [[ "${SWAP_USED_MB}" -gt 512 ]]; then
    echo "→ Le VPS a déjà subi une forte pression mémoire (swap utilisé)."
    echo "  Préfère orca-mini / qwen2.5:3b et OLLAMA_KEEP_ALIVE=10m au lieu de -1."
  fi
fi
echo ""

echo "=== Top mémoire ==="
ps aux --sort=-%mem 2>/dev/null | head -12 || true
echo ""

echo "=== OOM killer (kernel a tué un processus ?) ==="
if command -v journalctl >/dev/null 2>&1; then
  journalctl -k --no-pager -n 50 2>/dev/null | grep -iE 'oom|killed process|out of memory' || echo "(aucun OOM boot courant)"
  echo ""
  echo "OOM boot précédent (si reboot récent) :"
  journalctl -k -b -1 --no-pager 2>/dev/null | grep -iE 'oom|killed process|out of memory' | tail -5 || echo "(aucun ou boot -1 indisponible)"
else
  dmesg 2>/dev/null | grep -iE 'oom|killed process' | tail -5 || echo "(dmesg indisponible)"
fi
echo ""

echo "=== Ollama (processus + modèle chargé) ==="
pgrep -af '[o]llama' 2>/dev/null || echo "(processus ollama non listé)"
curl -sS --max-time 3 http://127.0.0.1:11434/api/ps 2>/dev/null || echo "(api/ps indisponible)"
echo ""
OLLAMA_MODEL_EFF="$("${ROOT}/scripts/read_env_var.sh" OLLAMA_MODEL 2>/dev/null || true)"
echo "OLLAMA_MODEL effectif (.env_file + .env) : ${OLLAMA_MODEL_EFF:-(inconnu)}"
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
PM2_BOOT=""
for unit in "pm2-$(whoami)" "pm2-root" "pm2-rooney"; do
  if systemctl is-enabled "${unit}" &>/dev/null 2>&1; then
    PM2_BOOT="${unit} : $(systemctl is-enabled ${unit} 2>/dev/null)"
    break
  fi
done
if [[ -n "${PM2_BOOT}" ]]; then
  echo "OK — ${PM2_BOOT}"
else
  echo "PROBLÈME : PM2 pas activé au démarrage → après reboot, rien ne tourne jusqu'à relance manuelle."
  echo "  Lance : ./scripts/vps_enable_auto_start.sh"
fi
if command -v sudo >/dev/null 2>&1; then
  echo ""
  echo "Doublon PM2 root (doit être vide si tu utilises rooney) :"
  sudo pm2 list 2>/dev/null | head -8 || echo "(sudo pm2 indisponible)"
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
