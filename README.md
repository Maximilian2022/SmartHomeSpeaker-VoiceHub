# Google Home Speaker (Edge TTS & Web GUI Edition)

Google Home / Nest に高品質な日本語音声を喋らせるシステムです。
従来の `google-home-voicetext` を大幅に刷新し、Microsoft Edge TTS、洗練された Web GUI、スケジュール管理機能、Cloudflare Tunnel 対応を備えています。

## 主な特徴
- **高品質・無料の音声合成 (Edge TTS)**: APIキー不要で、Microsoft Edge の自然な日本語音声（Nanami, Keita 等）を利用。
- **直感的な Web GUI**: ブラウザから即時発言、ブラウザ試聴プレビュー、送信先スピーカーの選択が可能。
- **スケジュール管理**: 定期アナウンス（毎朝の挨拶、ゴミ出しリマインダーなど）を GUI から登録・管理可能。
- **マルチデバイス対応**: 宅内にある複数の Google Home / Nest デバイス（部屋、書斎、リビング、寝室等）を自動検出し、個別または一括指定可能。
- **外部 Webhook & Cloudflare Tunnel 対応**: curl や Home Assistant、IFTTT 等から外部経由で呼び出し可能。トークン認証で外部公開時も安全。
- **1ポート統合アーキテクチャ**: ポート 8080 のみで Web GUI、Webhook、音声ホスティングの全てが動作。

---

## 起動方法

### 1. ホストで直接起動
```bash
# 依存関係インストール
npm install

# サーバー起動 (ポート 8080)
npm start
```

ブラウザで `http://localhost:8080` を開きます。

### 2. Docker Compose で起動
```bash
docker compose up -d
```

---

## Webhook API の使い方

### 1. テキストを発声させる (推奨)
```bash
curl -X POST http://[IP_ADDRESS]/api/say \
  -H "Content-Type: application/json" \
  -d '{
    "text": "こんにちは！テスト送信です。",
    "device": "部屋",
    "voice": "ja-JP-NanamiNeural"
  }'
```

#### パラメータ一覧 (JSON または Form-Data)
| パラメータ | 必須 | 説明 | 例 |
|---|---|---|---|
| `text` | ○ | 喋らせたい文言 | `"ご飯ができましたよ"` |
| `device` または `deviceIp` | - | 送信先スピーカー名またはIP (単一) | `"部屋"`, `"192.168.11.97"` |
| `devices` | - | 送信先スピーカーの配列 (複数一括) | `["部屋", "リビング"]` または `["all"]` |
| `voice` | - | 話者名 | `"ja-JP-NanamiNeural"` (女性), `"ja-JP-KeitaNeural"` (男性) |
| `rate` | - | 話速 (パーセント) | `"+0%"`, `"+10%"` |
| `pitch` | - | 音高 (ヘルツ) | `"+0Hz"`, `"-5Hz"` |

### 複数スピーカーへの送信例
```bash
curl -X POST http://[IP_ADDRESS]:8080/api/say \
  -H "Authorization: Bearer [WEBHOOK_TOKEN]" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "全員集合してください！",
    "devices": ["部屋", "書斎"]
  }'
```

### 2. 従来のエンドポイント互換 (google-home-voicetext)
```bash
curl -X POST -d "text=こんにちは、Googleです。" http://[IP_ADDRESS]:8080/google-home-voicetext
```

---

## 音声キャッシュ管理 (1GB LRU)
- 生成された MP3 音声は `public/voice/` にハッシュ名でキャッシュされます。
- 同一テキスト・同一話者の場合は再生成を行わずキャッシュから即座に再生されます。
- キャッシュ再利用時はアクセス日時（atime/mtime）を自動タッチ更新します。
- 合計容量が上限（デフォルト: 1024MB / 1GB）を超えると、最も古いアクセス日時のファイルから自動クリーンアップされます。
- 設定変更は `.my.env` の `MAX_CACHE_SIZE_MB` で調整可能です。

---

## Cloudflare Tunnel 経由での利用 (インターネット越しの発言)

Cloudflare Zero Trust (Dashboard) を使って外部から安全に Webhook を呼び出すことができます。

### 1. Cloudflare Dashboard の設定 (Public Hostname)
Cloudflare Zero Trust の **Networks > Tunnels** からトンネルを作成し、**Public Hostname** を次のように登録します：

| 設定項目 | 入力値 | 備考 |
|---|---|---|
| **Subdomain** | `webhook` | お好みのサブドメイン |
| **Domain** | `kit-a.net` | あなたの保有ドメイン |
| **Path** | 空欄 | ルート全体を対象 |
| **Type (Service Type)** | **`HTTP`** |  |
| **URL (サービスURL)** | **`localhost:8080`** または **`192.168.11.244:8080`** | 本サーバーのローカル待受アドレス |

> [!IMPORTANT]
> **サービスURL（Service URL）とは？**
> `cloudflared` が受信した通信を転送するローカルサーバーの宛先です。
> 本システムは Docker コンテナで `network_mode: "host"` としてホストマシンのポート `8080` を直接リッスンしているため、サービスURLには `localhost:8080`（または `192.168.11.244:8080`）を入力します。

### 2. Web GUI の 403 遮断プロテクション (セキュリティ)
Cloudflare Tunnel 経由（`Host: webhook.kit-a.net`）でのアクセスは、セキュリティのため**Web管理画面や内部API（`/`, `/index.html`, `/api/status`, `/api/devices`, `/api/schedules`）を `403 Forbidden` で自動遮断**します。
外部から許可されるのは **Webhook 発言エンドポイント（`/api/say`）のみ** です（認証トークン必須）。

### 3. 外部からの Webhook 呼び出し例
```bash
curl -X POST https://webhook.kit-a.net/api/say \
  -H "Authorization: Bearer your-super-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"text": "外出先からの通知です。", "devices": ["部屋"]}'
```

---

## Alexa (Amazon Echo) 連携 (オプション)
`thorsten-gehrig/alexa-remote-control` を内包しており、Amazon Echo デバイスへも同時に発言させることができます。
1. `.my.env` で `ALEXA_ENABLED=true` に設定。
2. 初回認証（Amazon OTP）を完了させると、Web GUI や Webhook で Echo デバイスも選択可能になります。

