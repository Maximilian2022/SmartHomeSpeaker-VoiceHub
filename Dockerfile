FROM node:22-slim

WORKDIR /app

# avahi-utils, jq, curl, tzdata, python3 をインストール (Google Cast & Alexa & HomePod 用)
RUN apt-get update && apt-get install -y --no-install-recommends \
    avahi-utils \
    jq \
    curl \
    tzdata \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# pyatv 仮想環境の作成とインストール (Apple HomePod AirPlay2 制御用)
RUN python3 -m venv /opt/pyatv-env \
    && /opt/pyatv-env/bin/pip install --no-cache-dir pyatv

ENV TZ=Asia/Tokyo
ENV NODE_ENV=production
ENV PATH="/opt/pyatv-env/bin:$PATH"

COPY package*.json ./
RUN npm ci --omit=dev

COPY . .

# スクリプトの実行権限およびディレクトリの準備
RUN chmod +x bin/alexa_remote_control.sh bin/homepod_scan.py bin/homepod_stream.py 2>/dev/null || true \
    && mkdir -p public/voice data

EXPOSE 8080

CMD ["node", "src/server.js"]
