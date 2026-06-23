#!/bin/sh
set -e
mkdir -p /app/data
# 没有真实库时，用合成样例库开箱演示
if [ ! -f /app/data/stock.db ]; then
  cp /app/data/sample.db /app/data/stock.db
fi
exec uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000
