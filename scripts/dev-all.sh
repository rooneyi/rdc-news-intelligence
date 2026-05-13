#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AI_DIR="$ROOT_DIR/ai-service"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOGS_DIR="$ROOT_DIR/.logs"

AI_PORT="${AI_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
NEXT_DIST_DIR="${NEXT_DIST_DIR:-/tmp/rdc-next-dev-$$}"

PIDS=()

log() {
  printf "[%s] %s\n" "$(date +"%H:%M:%S")" "$1"
}

run_bg() {
  local name="$1"
  local command="$2"
  local logfile="$3"

  log "Start $name"
  bash -lc "$command" >"$logfile" 2>&1 &
  local pid=$!
  PIDS+=("$pid")
  log "$name started (PID=$pid, log=$logfile)"
}

free_port() {
  local port="$1"

  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
  fi

  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      kill -9 $pids >/dev/null 2>&1 || true
    fi
  fi
}

cleanup() {
  log "Stopping services..."
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
  wait || true
  log "All services stopped."
}

trap cleanup EXIT INT TERM

# Cleanup and recreate logs folder
if [[ -d "$LOGS_DIR" ]]; then
  # Try to remove old logs, if fails use temp folder
  rm -rf "$LOGS_DIR" 2>/dev/null || {
    log "Warning: Could not clean $LOGS_DIR, using /tmp for logs"
    LOGS_DIR="/tmp/rdc-logs-$$"
  }
fi
mkdir -p "$LOGS_DIR"
chmod 755 "$LOGS_DIR" 2>/dev/null || true
mkdir -p "$NEXT_DIST_DIR"

if [[ ! -d "$AI_DIR" || ! -d "$FRONTEND_DIR" ]]; then
  echo "Missing required folders: ai-service, frontend" >&2
  exit 1
fi

# RDC_ENV_FILE_ONLY : app/core/config.py ne lit cette variable qu’**avant** load_dotenv.
# La mettre seulement dans .env_file ne suffit pas — il faut l’exporter pour uvicorn.
# Ordre : variable d’environnement parente > détection dans .env_file (ligne RDC_ENV_FILE_ONLY=1).
AI_ENV_PREFIX=""
if [[ "${RDC_ENV_FILE_ONLY:-}" =~ ^(0|false|no|off)$ ]]; then
  AI_ENV_PREFIX=""
elif [[ "${RDC_ENV_FILE_ONLY:-}" =~ ^(1|true|yes|on)$ ]]; then
  AI_ENV_PREFIX="export RDC_ENV_FILE_ONLY=1 && "
elif [[ -f "$AI_DIR/.env_file" ]] && grep -qE '^[[:space:]]*RDC_ENV_FILE_ONLY[[:space:]]*=[[:space:]]*(1|true|yes|on)[[:space:]]*$' "$AI_DIR/.env_file" 2>/dev/null; then
  AI_ENV_PREFIX="export RDC_ENV_FILE_ONLY=1 && "
fi

if [[ -x "$AI_DIR/.env/bin/python" ]]; then
  AI_CMD="cd '$AI_DIR' && ${AI_ENV_PREFIX}export PYTHONUNBUFFERED=1 && source .env/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port $AI_PORT --reload"
else
  AI_CMD="cd '$AI_DIR' && ${AI_ENV_PREFIX}export PYTHONUNBUFFERED=1 && uvicorn app.main:app --host 127.0.0.1 --port $AI_PORT --reload"
fi

log "Installing frontend dependencies (npm install)"
(cd "$FRONTEND_DIR" && npm install >/dev/null 2>&1) || log "npm install failed, continuing"

free_port "$AI_PORT"
free_port "$FRONTEND_PORT"

run_bg "FastAPI" "$AI_CMD" "$LOGS_DIR/fastapi.log"
run_bg "Next frontend" "cd '$FRONTEND_DIR' && NEXT_DIST_DIR='$NEXT_DIST_DIR' npm run dev -- --port $FRONTEND_PORT" "$LOGS_DIR/frontend.log"

log "Services available:"
log "- Frontend: http://127.0.0.1:$FRONTEND_PORT"
log "- FastAPI:  http://127.0.0.1:$AI_PORT"
log "- Next dist: $NEXT_DIST_DIR"
log "Logs in $LOGS_DIR"
log "Press Ctrl+C to stop all services"

while true; do
  sleep 2
  for pid in "${PIDS[@]}"; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      log "A service exited unexpectedly. Check logs in $LOGS_DIR/."
      exit 1
    fi
  done
done
