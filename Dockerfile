FROM node:22-slim

WORKDIR /app

# avahi-utils (avahi-browseによるGoogle Cast探索用) と tzdata をインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    avahi-utils \
    tzdata \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Tokyo
ENV NODE_ENV=production

COPY package*.json ./
RUN npm ci --omit=dev

COPY . .

# 音声ファイル用・データ用ディレクトリの準備
RUN mkdir -p public/voice data

EXPOSE 8080

CMD ["node", "src/server.js"]
