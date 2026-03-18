#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

while true; do
    echo "[run_loop] Pulling latest..."
    git pull

    echo "[run_loop] Starting spotify-remote..."
    poetry run spotify-remote || true

    echo "[run_loop] Restarting in 3s..."
    sleep 3
done
