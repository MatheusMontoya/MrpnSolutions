#!/usr/bin/env bash
# PSA SAP — instala, builda o frontend e sobe o app em http://127.0.0.1:8000
set -e
cd "$(dirname "$0")"

echo "[1/3] Dependências do backend..."
python -m pip install -q -r backend/requirements.txt

echo "[2/3] Build do frontend..."
npm --prefix frontend install --no-fund --no-audit
npm --prefix frontend run build

echo "[3/3] Subindo PSA SAP em http://127.0.0.1:8000 (docs em /docs)"
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
