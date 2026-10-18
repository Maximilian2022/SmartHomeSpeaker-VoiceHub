# Smart Home Speaker Voice Hub 🎙️

Google Home / Nest、Amazon Alexa (Echo)、Apple HomePod に加え、**ONVIF ネットワークカメラ（双方向音声スピーカー）** および **DLNA / UPnP ネットワークオーディオ（MediaRenderer）** を統合し、自然な日本語音声（Microsoft Edge TTS）でアナウンスできるスマートスピーカー音声ハブです。

Webブラウザからの直感的な即時発言、定期スケジュール放送、Googleカレンダー予定の自動読み上げ、Webhook（外部API・IFTTT等）経由の発言に対応しています。

> [!NOTE]
> 本ソフトウェアは、AIコーディングアシスタント（Google Antigravity）の支援を活用して設計・実装されたオープンソースプロジェクトです。
> 主に自分用に作成したものなので、考慮不足の点が多々あると思われます。
> 
> 📖 **詳細なシステム内部仕様、全REST APIリファレンス、ネットワーク境界セキュリティ、同期エンジン仕様については [Manual.md](Manual.md) をご覧ください。**

---

## ✨ 主な機能

- **高品質な音声合成**: Edge TTSで自然な日本語音声（女性・男性の複数話者）を利用可能。
- **5大プラットフォーム対応マルチスピーカー**:
  - **Google Home / Nest**: Google Cast (castv2) によるキャスト再生。グループスピーカー対応。
  - **Amazon Alexa (Echo)**: 宅内 Echo デバイスへのアナウンス発話。
  - **Apple HomePod**: AirPlay 2 / RAOP 経由での高音質ストリーミング再生。
  - **ONVIF ネットワークカメラ**: Reolink や Tapo 等の防犯カメラのスピーカー（Two-Way Audio / Profile T）へのアナウンス発話。
  - **DLNA / UPnP スピーカー**: Bose SoundTouch、Sonos、Denon HEOS、Yamaha MusicCast、foobar2000 等の DLNA MediaRenderer へのストリーミング再生。
- **Web GUI**: 即時発言、ブラウザ試聴プレビュー、送信先スピーカーの選択、マクロ一括選択。
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
- Python 3.12 以上 (または Docker / Docker Compose)
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
pip install -r requirements.txt

# サーバー起動 (デフォルト: ポート 8080)
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080
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
7. **「Deploy the stack」** をクリックします。自動的に Python 3.14 環境がビルドされ、名前付きボリューム (`smart_speaker_data`, `smart_speaker_cache`) と共に起動します。

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

## 📷 ONVIF ネットワークカメラ連携 (Two-Way Audio / Profile T)

宅内の ONVIF Profile T 対応防犯カメラ（Reolink E1 Pro、TP-Link Tapo など）の内蔵スピーカーへ、アナウンス音声を送信できます。

1. Web GUI の「ONVIF / DLNA」タブを開きます。
2. カメラ共通の「デフォルト ONVIF ユーザー名」「パスワード」を入力して保存します。
3. **「＋ デバイスをスキャン」** をクリックすると、WS-Discovery（UDP 3702）により宅内のカメラが自動検出されます。
4. Profile T（双方向音声）対応のカメラを「＋ 連携登録」することで、即時発話や Webhook から `CAM:ALL` やカメラ名・IP を指定して発声できるようになります。
5. 音声は `go2rtc` 経由で RTSP バックチャンネル（PCMU コーデック）へプッシュされ、FFmpeg による動的音量ゲイン調整キャッシュファイルが自動適用されます。

---

## 🎵 DLNA / UPnP ネットワークオーディオ連携 (AVTransport)

Bose SoundTouch、Sonos、Denon HEOS、Yamaha MusicCast、あるいは PC 上の DLNA レンダラー（foobar2000 + UPnP等）と連携し、高音質なストリーミング再生が可能です。

1. Web GUI の「ONVIF / DLNA」タブで **「＋ デバイスをスキャン」** を実行します。
2. SSDP（UDP 1900, `MediaRenderer:1`）により、宅内の DLNA レンダラーが ONVIF カメラと一緒に一覧へ自動検出されます。
3. DLNA デバイスは認証情報（ID/パスワード）が不要なため、名前を確認してそのまま「＋ 連携登録」をクリックするだけで即座に利用可能になります。
4. 発話時は UPnP 標準プロトコル（SOAP `AVTransport:SetAVTransportURI` および `Play`）により、Voice Hub がホストする MP3 音声がダイレクトに再生されます。`RenderingControl:SetVolume` による音量制御にも対応しています。

---

## 📜 ライセンス & クレジット

本プロジェクトは **MIT License** の下で公開されています。

### 参考・利用ライブラリ
本ソフトウェアの開発にあたり、以下の素晴らしいオープンソースプロジェクトの知見・ライブラリを活用・参考にしています。各開発者・コミュニティの皆様に感謝いたします。

- **[google-home-voicetext](https://github.com/sikkimtemi/google-home-voicetext-docker)** (Taro TAKAHASHI) - オリジナルの Google Home 音声通知着想
- **[edge-tts](https://github.com/rany2/edge-tts)** - Python Microsoft Edge 音声合成クライアント
- **[PyChromecast](https://github.com/home-assistant-libs/pychromecast)** - Google Cast 通信プロトコル実装 (Home Assistant)
- **[alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control)** - Amazon Echo 制御シェルスクリプト
- **[pyatv](https://github.com/postlund/pyatv)** - Apple HomePod AirPlay2 ストリーミング
- **[go2rtc](https://github.com/AlexxIT/go2rtc)** - ONVIF Profile T 双方向音声バックチャンネルストリーミング
- **[aiomqtt](https://github.com/sbtinstruments/aiomqtt)** - 非同期 MQTT クライアント (Node-RED / n8n / Home Assistant 連携)
