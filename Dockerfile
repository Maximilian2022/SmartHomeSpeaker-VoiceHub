FROM node:22-slim

WORKDIR /app

# avahi-utils, jq, curl, tzdata をインストール (Google Cast & Alexa Remote Control 用)
RUN apt-get update && apt-get install -y --no-install-recommends \
    avahi-utils \
    jq \
    curl \
    tzdata \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Tokyo
ENV NODE_ENV=production

COPY package*.json ./
RUN npm ci --omit=dev

COPY . .

# スクリプトの実行権限およびディレクトリの準備
RUN chmod +x bin/alexa_remote_control.sh 2>/dev/null || true \
    && mkdir -p public/voice data

EXPOSE 8080

CMD ["node", "src/server.js"]
