#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AI_DIR="$ROOT_DIR/ai-service"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

AI_PORT="${AI_PORT:-8001}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

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

mkdir -p "$ROOT_DIR/.logs"

if [[ ! -d "$AI_DIR" || ! -d "$BACKEND_DIR" || ! -d "$FRONTEND_DIR" ]]; then
  echo "Missing one of required folders: ai-service, backend, frontend" >&2
  exit 1
fi

if [[ -x "$AI_DIR/.env/bin/python" ]]; then
  AI_CMD="cd '$AI_DIR' && source .env/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port $AI_PORT --reload"
else
  AI_CMD="cd '$AI_DIR' && uvicorn app.main:app --host 127.0.0.1 --port $AI_PORT --reload"
fi

if command -v docker >/dev/null 2>&1; then
  log "Ensuring backend dependencies (docker compose) are up"
  (cd "$BACKEND_DIR" && docker compose up -d) || log "docker compose up failed, continuing"
fi

log "Installing frontend dependencies (npm install)"
(cd "$FRONTEND_DIR" && npm install >/dev/null 2>&1) || log "npm install failed, continuing"

run_bg "FastAPI" "$AI_CMD" "$ROOT_DIR/.logs/fastapi.log"
run_bg "Symfony backend" "cd '$BACKEND_DIR' && php -S 127.0.0.1:$BACKEND_PORT -t public" "$ROOT_DIR/.logs/backend.log"
run_bg "Next frontend" "cd '$FRONTEND_DIR' && npm run dev -- --port $FRONTEND_PORT" "$ROOT_DIR/.logs/frontend.log"

log "Services available:"
log "- Frontend: http://127.0.0.1:$FRONTEND_PORT"
log "- Backend:  http://127.0.0.1:$BACKEND_PORT"
log "- FastAPI:  http://127.0.0.1:$AI_PORT"
log "Logs in $ROOT_DIR/.logs"
log "Press Ctrl+C to stop all services"

while true; do
  sleep 2
  for pid in "${PIDS[@]}"; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      log "A service exited unexpectedly. Check logs in .logs/."
      exit 1
    fi
  done
done
