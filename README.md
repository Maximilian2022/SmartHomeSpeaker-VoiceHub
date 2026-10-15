# Smart Home Speaker Voice Hub 🎙️

Google Home / Nest、Amazon Alexa (Echo)、Apple HomePod を統合し、自然な日本語音声（Microsoft Edge TTS）でアナウンスできるスマートスピーカー音声ハブです。

Webブラウザからの直感的な即時発言、定期スケジュール放送、Googleカレンダー予定の自動読み上げ、Webhook（外部API・IFTTT等）経由の発言に対応しています。

> [!NOTE]
> 本ソフトウェアは、AIコーディングアシスタント（Google Antigravity）の支援を活用して設計・実装されたオープンソースプロジェクトです。

---

## ✨ 主な機能

- **高品質な音声合成**: Edge TTSで自然な日本語音声（女性・男性の複数話者）を利用可能。
- **マルチスピーカー対応**: 宅内の Google Home / Nest、Amazon Echo、Apple HomePod を自動検出し、個別または一括で発言。
- **Web GUI**: 即時発言、ブラウザ試聴プレビュー、送信先スピーカーの選択、直近の発言履歴。
- **スケジュール管理**: 定期アナウンス（毎朝の挨拶、リマインダーなど）を GUI から登録・編集・管理。
- **Google カレンダー連携**: 予定開始前のリマインド放送や、毎朝の予定まとめアナウンスを自動実行。
- **Webhook & 外部連携**: cURL、Home Assistant、IFTTT 等から手軽に呼び出し可能。Cloudflare Tunnel による外部アクセス時の認証保護対応。

---

## 🚀 起動方法

### 1. 必要要件
- Node.js 18 以上 (または Docker / Docker Compose)
- スピーカー端末と同じローカルネットワーク (LAN)

### 2. 環境設定
サンプルファイルをコピーして設定ファイルを作成します。

```bash
cp .my.env.sample .my.env
```

必要に応じて `.my.env` を編集します（ポート番号変更、Webhookトークン設定など）。

### 3. 起動 (ホストで直接動かす場合)

```bash
# 依存ライブラリのインストール
npm install

# サーバー起動 (デフォルト: ポート 8080)
npm start
```

起動後、ブラウザで `http://localhost:8080` を開きます。

### 4. Docker Compose で起動する場合

```bash
docker compose up -d
```

---

## 📡 Webhook API の使い方

外部サービスやスクリプトからスピーカーへ発言させることができます。

### 基本的な呼び出し (JSON POST)

```bash
curl -X POST http://<サーバーIP>:8080/api/say \
  -H "Content-Type: application/json" \
  -d '{
    "text": "ご飯ができましたよ！",
    "devices": ["リビング", "部屋"]
  }'
```

### パラメータ一覧

| パラメータ | 必須 | 説明 | 例 |
|---|---|---|---|
| `text` | ○ | 喋らせたい文言 | `"お風呂が沸きました"` |
| `devices` | - | 送信先スピーカー名またはIP (配列) | `["リビング", "書斎"]` |
| `voice` | - | 話者名 | `"ja-JP-NanamiNeural"` (女性), `"ja-JP-KeitaNeural"` (男性) |
| `rate` | - | 話速 (パーセント) | `"+0%"`, `"+20%"` |
| `pitch` | - | 音高 (ヘルツ) | `"+0Hz"`, `"-5Hz"` |
| `volumeLevel`| - | Google Cast 音量 (0.0〜1.0) | `0.5` |

> [!TIP]
> Web GUI の「Webhook / Tunnel」タブにある **Webhook コマンドビルダー** を使うと、画面上でスピーカーやメッセージを選ぶだけで cURL や IFTTT 向けの設定が自動生成されます。

---

## 📅 Google カレンダー連携

1. Web GUI の「カレンダー連携」タブを開きます。
2. Google カレンダーの「設定」>「カレンダーの統合」にある **「iCal 形式の非公開 URL」** を貼り付けて保存します。
3. 開始前の直前リマインド（例: 10分前）や、毎朝の予定サマリー放送（例: 07:30）が自動でスピーカーからアナウンスされます。

※ サーバーは15分おきにカレンダー情報をバックグラウンド同期します。

---

## 📜 ライセンス & クレジット

本プロジェクトは **MIT License** の下で公開されています。

### 参考・利用ライブラリ
本ソフトウェアの開発にあたり、以下の素晴らしいオープンソースプロジェクトの知見・ライブラリを活用・参考にしています。各開発者・コミュニティの皆様に感謝いたします。

- **[google-home-voicetext](https://github.com/sikkimtemi/google-home-voicetext-docker)** (Taro TAKAHASHI) - オリジナルの Google Home 音声通知着想
- **[node-edge-tts](https://github.com/schroffl/node-edge-tts)** - Microsoft Edge 音声合成クライアント
- **[castv2-client](https://github.com/thibauts/node-castv2-client)** - Google Cast (Chromecast) 通信プロトコル実装
- **[alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control)** / **[alexa-cookie2](https://github.com/Apollon77/alexa-cookie)** - Amazon Echo 制御および認証連携
- **[pyatv](https://github.com/postlund/pyatv)** - Apple HomePod AirPlay2 ストリーミング
