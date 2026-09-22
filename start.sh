#!/usr/bin/env bash
# Runs the FastAPI backend (background, port 8000) and the Streamlit UI
# (foreground, port 8501) in a single container
set -euo pipefail

echo "Starting FastAPI backend..."
uvicorn data_analyst_agent.api.app:create_app --factory --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "Waiting for backend health check..."
for _ in $(seq 1 60); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "Backend is up."
        break
    fi
    sleep 1
done

echo "Starting Streamlit UI..."
streamlit run src/data_analyst_agent/ui/app.py \
    --server.address 0.0.0.0 \
    --server.port 8501 \
    --server.headless true &
UI_PID=$!

trap 'kill $API_PID $UI_PID 2>/dev/null' TERM INT
wait -n $API_PID $UI_PID
