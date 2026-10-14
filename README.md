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

## 宅内デバイス設定 (デフォルト)
- **サーバーIP**: `192.168.11.244` (Port: `8080`)
- **デフォルトスピーカー**: 部屋 (`192.168.11.97`)

---

## 起動方法

### 1. ホストで直接起動
```bash
# 依存関係インストール
npm install

# サーバー起動 (ポート 8080)
npm start
```

ブラウザで `http://192.168.11.244:8080` または `http://localhost:8080` を開きます。

### 2. Docker Compose で起動
```bash
docker compose up -d
```

---

## Webhook API の使い方

### 1. テキストを発声させる (推奨)
```bash
curl -X POST http://192.168.11.244:8080/api/say \
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
| `device` または `deviceIp` | - | 送信先スピーカー名またはIP | `"部屋"`, `"192.168.11.97"` |
| `voice` | - | 話者名 | `"ja-JP-NanamiNeural"` (女性), `"ja-JP-KeitaNeural"` (男性) |
| `rate` | - | 話速 (パーセント) | `"+0%"`, `"+10%"` |
| `pitch` | - | 音高 (ヘルツ) | `"+0Hz"`, `"-5Hz"` |

### 2. 従来のエンドポイント互換 (google-home-voicetext)
```bash
curl -X POST -d "text=こんにちは、Googleです。" http://192.168.11.244:8080/google-home-voicetext
```

---

## Cloudflare Tunnel 経由での利用 (インターネット越しの発言)

1. `.my.env` に任意のセキュリティトークンを設定します：
   ```env
   WEBHOOK_TOKEN=your-super-secret-token
   ```
2. `docker-compose.yml` 内の `cloudflared` サービスのコメントアウトを解除し、Cloudflare Dashboard から取得したトンネルトークンを設定します。
3. インターネットから Webhook を叩く際は、ヘッダーにトークンを付与します：
   ```bash
   curl -X POST https://your-domain.example.com/api/say \
     -H "Authorization: Bearer your-super-secret-token" \
     -H "Content-Type: application/json" \
     -d '{"text": "外出先からの通知です。"}'
   ```
