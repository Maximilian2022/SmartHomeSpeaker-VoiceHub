# Stage 1: go2rtc official binary
FROM alexxit/go2rtc:latest AS go2rtc-src

# Stage 2: Voice Hub Python 3.14 Runtime
FROM python:3.14-slim

WORKDIR /app

# go2rtc 単一バイナリを同梱
COPY --from=go2rtc-src /usr/local/bin/go2rtc /usr/local/bin/go2rtc

# IPv4 優先設定 (IPv6到達不能環境での接続タイムアウト防止)
RUN echo "precedence ::ffff:0:0/96 100" > /etc/gai.conf

# 必須システムパッケージのインストール (Python のみ)
RUN apt-get update && apt-get install -y --no-install-recommends \
    avahi-utils \
    jq \
    curl \
    tzdata \
    ca-certificates \
    ffmpeg \
    bash \
    zstd \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Tokyo
ENV PYTHONUNBUFFERED=1

# Python 依存関係
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh bin/alexa_remote_control.sh 2>/dev/null || true \
    && mkdir -p public/voice public/sound data

EXPOSE 8080 8081 1984 8554

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8080/api/status > /dev/null 2>&1 || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
