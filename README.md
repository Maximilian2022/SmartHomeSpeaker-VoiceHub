# Smart Home Speaker Voice Hub 🎙️

Google Home / Nest、Amazon Alexa (Echo)、Apple HomePod を統合し、自然な日本語音声（Microsoft Edge TTS）でアナウンスできるスマートスピーカー音声ハブです。

Webブラウザからの直感的な即時発言、定期スケジュール放送、Googleカレンダー予定の自動読み上げ、Webhook（外部API・IFTTT等）経由の発言に対応しています。

> [!NOTE]
> 本ソフトウェアは、AIコーディングアシスタント（Google Antigravity）の支援を活用して設計・実装されたオープンソースプロジェクトです。
> 主に自分用に作成したものなので、考慮不足の点が多々あると思われます。

---

## ✨ 主な機能

- **高品質な音声合成**: Edge TTSで自然な日本語音声（女性・男性の複数話者）を利用可能。
- **マルチスピーカー対応**: 宅内の Google Home / Nest、Amazon Echo、Apple HomePod を自動検出し、個別または一括で発言。
- **Web GUI**: 即時発言、ブラウザ試聴プレビュー、送信先スピーカーの選択。
- **発言履歴ログ (過去100件)**: Web UI、定期スケジュール、カレンダー連携、外部API/Webhookからの全発話履歴をリアルタイム自動記録。送信元バッジ（色分け）、ステータス、再発言・試聴・テキストコピー機能。
- **スケジュール・カレンダー統合管理**:
  - 定期アナウンス（毎朝の挨拶、ゴミ出しリマインダーなど）の登録・編集・管理。
  - Google カレンダー（複数カレンダー対応）の同期、予定開始前リマインド放送や朝の予定まとめアナウンスを自動実行。
- **おやすみ・会議モード (DND)**:
  - 曜日・時間帯による定時ミュート（平日日中や深夜）。
  - カレンダー予定（MTG・会議等）進行中の自動サイレント化（終日予定自動除外）。
  - ワンタップ即時ミュート（30分/1時間/2時間/本日終了）。
  - 動作モード選択（完全スキップ、囁き極小音量、終了後まとめアナウンスの保留キュー）。
  - 書斎や仕事部屋のみミュートできる対象スピーカー選択。
  - 緊急警報用バイパスフラグ (`urgent: true`)。
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
docker compose up -d --build
```

- スケジュール・設定・認証情報は永続ボリューム `smart_speaker_data` に保存されます。
- 生成された音声キャッシュは `smart_speaker_cache` ボリュームに保持されます。

### 5. Portainer で起動する場合 (Stacks / Git Repository)

Portainer の Web GUI からリポジトリを指定してワンクリックでデプロイできます。

1. Portainer にログインし、**「Stacks」** → **「Add stack」** を開きます。
2. **Build method** で **「Repository」** を選択します。
3. **Repository URL**: `https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub.git` を入力します。
4. **Repository reference**: `refs/heads/main` (または `main`)
5. **Compose path**: `docker-compose.yml` (デフォルトのまま)
6. **Environment variables** (必要に応じて):
   - `DEFAULT_SPEAKER_IP`: メインの Google Home の IP アドレス
   - `WEBHOOK_TOKEN`: 外部アクセス時のセキュリティトークン
   - `TUNNEL_TOKEN`: Cloudflare Tunnel を利用する場合のトークン
7. **「Deploy the stack」** をクリックします。自動的に Node 26 環境がビルドされ、名前付きボリューム (`smart_speaker_data`, `smart_speaker_cache`) と共に起動します。

---

## 📡 Webhook API の使い方

外部サービス（Slack, LINE, IFTTT, Home Assistant, Zapier 等）やスクリプトからスピーカーへ発言させることができます。
**送信元の3秒タイムアウトを防ぐため、Webhook 呼び出し時は即座に `200 OK` を返却し、音声合成・再生はバックグラウンド（非同期）で高速実行されます。**

### 基本的な呼び出し (JSON POST)

```bash
curl -X POST http://<サーバーIP>:8080/api/say \
  -H "Content-Type: application/json" \
  -d '{
    "text": "ご飯ができましたよ！",
    "devices": ["リビング", "部屋"]
  }'
```

### URLクエリでの簡易呼び出し (GET 対応)

```bash
curl "http://<サーバーIP>:8080/api/say?text=お風呂が沸きました&devices=リビング"
```

### パラメータ一覧

| パラメータ | 必須 | 説明 | 例 |
|---|---|---|---|
| `text` | ○ | 喋らせたい文言 | `"お風呂が沸きました"` |
| `devices` | - | 送信先スピーカー名またはIP (配列またはカンマ区切り) | `["リビング", "書斎"]` または `"リビング,書斎"` |
| `voice` | - | 話者名 | `"ja-JP-NanamiNeural"` (女性), `"ja-JP-KeitaNeural"` (男性) |
| `rate` | - | 話速 (パーセント) | `"+0%"`, `"+20%"` |
| `pitch` | - | 音高 (ヘルツ) | `"+0Hz"`, `"-5Hz"` |
| `volumeLevel`| - | Google Cast 音量 (0.0〜1.0) | `0.5` |
| `async` | - | 非同期（即時応答）の明示指定 (デフォルト: Webhook時は true) | `true` |
| `wait` | - | 再生完了まで待機して詳細結果を受け取る (同期モード) | `true` |

> [!TIP]
> Web GUI の「Webhook / Tunnel」タブにある **Webhook コマンドビルダー** を使うと、画面上でスピーカーやメッセージを選ぶだけで cURL や IFTTT 向けの設定が自動生成されます。

---

## 📅 Google カレンダー連携 (複数カレンダー & 個別設定対応)

1. Web GUI の「カレンダー連携」タブを開きます。
2. **「＋ カレンダーを追加」** から、Google カレンダーの「設定」>「カレンダーの統合」にある **「iCal 形式の非公開 URL」** を登録します。
3. **カレンダーごとの個別カスタマイズ**:
   - カレンダーごとに独立した**直前リマインド時刻**（5分前、10分前、15分前、30分前、60分前、ON/OFF）
   - カレンダーごとに異なる**朝の予定まとめ時刻**（例: 仕事用は 08:30、プライベート用は 07:30、ON/OFF）
   - カレンダーごとの**通知先スピーカー**（仕事用は書斎のみ、家族用は全室スピーカー等）
   - カレンダーごとの**話者・話速・音高・音量**の個別設定
   を自在に設定・切り替えできます。

※ サーバーは15分おきに自動でバックグラウンド同期します（手動即時同期も可能）。

---

## 🍏 Apple HomePod 連携 (AirPlay 2)

宅内の Apple HomePod / HomePod mini を自動検出し、AirPlay 2 / RAOP 経由で高音質ストリーミング再生できます。

> [!IMPORTANT]
> **同一ローカルネットワーク (LAN) 接続の必須要件:**
> 本サーバー（Docker）と Apple HomePod は、必ず**同一ローカルネットワーク（同じLAN / Wi-Fi、同一サブネット）**に接続されている必要があります。
> - Docker コンテナを稼働させるホストは `network_mode: host` を推奨します。
> - ルーターの「ゲスト用Wi-Fi」や「端末間通信遮断（プライバシーセパレータ）」、「別VLAN」などでセグメントが跨がっている場合、Apple AirPlay の探索プロトコルであるマルチキャストDNS（Bonjour / mDNS）が届かず、HomePod の自動認識および音声ストリーミングができません。

---

## 🗣️ Amazon Alexa (Echo) 連携 & 手動リフレッシュトークン取得

宅内の Amazon Echo デバイスと連携し、Google Home や HomePod と同時にアナウンスできます。

### 1. ブラウザプロキシによる自動ログイン (推奨)
Web GUI の「デバイス一覧」タブにある「Amazon ログインを開始して Alexa と連携」をクリックし、画面に表示されるリンクから手元のブラウザで Amazon にログインするだけで自動連携されます。

### 2. 手動でリフレッシュトークン (`Atnr|...`) を取得・登録する場合
ブラウザプロキシログインが 2段階認証（OTP）や画像認証、CAPTCHA 等でブロックされる場合は、以下の手順で手動取得・登録が可能です。

1. ターミナルでコンテナ内に入り、`alexa-cookie2` を実行します:
   ```bash
   docker exec -it google-home-voicetext npx alexa-cookie2
   ```
   （またはローカルPCのターミナルで `npx alexa-cookie2` を実行）
2. ドメイン選択で **`amazon.co.jp`** を選択し、お使いの Amazon アカウントのメールアドレスとパスワードを入力します。
3. ログイン完了後、ターミナルのコンソール画面に以下のようなトークンが出力されます:
   ```text
   Refresh Token: Atnr|...（長い英数字文字列）
   ```
4. Web GUI の「手動でリフレッシュトークン（Atnr|...）を入力して直接登録する場合」に貼り付けて「トークンを保存」を押すか、環境設定ファイル `.my.env` に以下を追記してコンテナを再起動します:
   ```env
   REFRESH_TOKEN="Atnr|..."
   ```

---

## 📜 ライセンス & クレジット

本プロジェクトは **MIT License** の下で公開されています。

### 参考・利用ライブラリ
本ソフトウェアの開発にあたり、以下の素晴らしいオープンソースプロジェクトの知見・ライブラリを活用・参考にしています。各開発者・コミュニティの皆様に感謝いたします。

- **[google-home-voicetext](https://github.com/sikkimtemi/google-home-voicetext-docker)** (Taro TAKAHASHI) - オリジナルの Google Home 音声通知着想
- **[node-edge-tts](https://github.com/SchneeHertz/node-edge-tts)** - Microsoft Edge 音声合成クライアント
- **[castv2-client](https://github.com/thibauts/node-castv2-client)** - Google Cast (Chromecast) 通信プロトコル実装
- **[alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control)** / **[alexa-cookie2](https://github.com/Apollon77/alexa-cookie)** - Amazon Echo 制御および認証連携
- **[pyatv](https://github.com/postlund/pyatv)** - Apple HomePod AirPlay2 ストリーミング
