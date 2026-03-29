#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

CHECK_INTERVAL=30

start_app() {
    echo "[run_loop] Starting spotify-remote..."
    poetry run spotify-remote &
    APP_PID=$!
}

stop_app() {
    if kill -0 "$APP_PID" 2>/dev/null; then
        echo "[run_loop] Stopping spotify-remote (pid $APP_PID)..."
        kill "$APP_PID"
        wait "$APP_PID" 2>/dev/null || true
    fi
}

has_remote_update() {
    git fetch origin --quiet 2>/dev/null
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main)
    [ "$LOCAL" != "$REMOTE" ]
}

trap 'stop_app; exit 0' INT TERM

echo "[run_loop] Pulling latest..."
git pull

start_app

while true; do
    sleep "$CHECK_INTERVAL"

    # Restart if the app crashed
    if ! kill -0 "$APP_PID" 2>/dev/null; then
        echo "[run_loop] App exited, restarting..."
        start_app
        continue
    fi

    # Check for remote updates
    if has_remote_update; then
        echo "[run_loop] Update detected, pulling and restarting..."
        stop_app
        git pull
        start_app
    fi
done
