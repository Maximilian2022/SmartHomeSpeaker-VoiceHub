#!/bin/bash
set -e

echo "[VoiceHub Entrypoint] Starting go2rtc background daemon..."
# go2rtc 設定ファイルがあれば使用、なければデフォルト起動
if [ -f "/app/data/go2rtc.yaml" ]; then
    /usr/local/bin/go2rtc -c /app/data/go2rtc.yaml &
else
    /usr/local/bin/go2rtc &
fi

# go2rtc の起動待ち (最大5秒)
for i in {1..10}; do
    if curl -s http://127.0.0.1:1984/api > /dev/null 2>&1; then
        echo "[VoiceHub Entrypoint] go2rtc started successfully on port 1984"
        break
    fi
    sleep 0.5
done

echo "[VoiceHub Entrypoint] Starting Python FastAPI Voice Hub Server on port ${PORT:-8080}..."
exec python3 -m uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8080}"
