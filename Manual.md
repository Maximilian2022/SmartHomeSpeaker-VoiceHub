# Smart Home Speaker Voice Hub 総合技術仕様書 (Manual.md) 📘

本ドキュメントは、[README.md](README.md) では割愛している **Smart Home Speaker Voice Hub** のシステムアーキテクチャ、各種スマートスピーカーとの接続仕様、Homebridge プラグイン、MCP (Model Context Protocol) サーバー、マルチ MQTT 連携、アクセス制御・セキュリティ設計、および全 REST API の詳細を網羅した技術仕様書です。

---

## 目次

1. [システムアーキテクチャ概要](#1-システムアーキテクチャ概要)
2. [ネットワーク・アクセス制御およびセキュリティ設計](#2-ネットワークアクセス制御およびセキュリティ設計)
   - 2.1 [デュアルレイヤー境界防御 (LAN vs Cloudflare Tunnel)](#21-デュアルレイヤー境界防御-lan-vs-cloudflare-tunnel)
   - 2.2 [Webhook トークン認証仕様 (WEBHOOK_TOKEN)](#22-webhook-トークン認証仕様-webhook_token)
   - 2.3 [Web GUI 管理者認証仕様 (ADMIN_PASSWORD)](#23-web-gui-管理者認証仕様-admin_password)
   - 2.4 [IPv6 ループバックバインド仕様](#24-ipv6-ループバックバインド仕様)
   - 2.5 [クライアント判定・IPエイリアス・重複排除 (Deduplication)](#25-クライアント判定ipエイリアス重複排除-deduplication)
3. [宛先解決マクロとスピーカー制御仕様](#3-宛先解決マクロとスピーカー制御仕様)
   - 3.1 [ターゲット指定記法＆マクロ一覧](#31-ターゲット指定記法マクロ一覧)
   - 3.2 [スピーカー種別の自動判別と解決アルゴリズム](#32-スピーカー種別の自動判別と解決アルゴリズム)
   - 3.3 [マルチプラットフォーム音ズレ補正エンジン (Sync Engine)](#33-マルチプラットフォーム音ズレ補正エンジン-sync-engine)
4. [音声合成 (TTS) とオーディオパイプライン仕様](#4-音声合成-tts-とオーディオパイプライン仕様)
   - 4.1 [Edge-TTS パラメータ](#41-edge-tts-パラメータ)
   - 4.2 [チャイム音声結合 (FFmpeg / バイト連結)](#42-チャイム音声結合-ffmpeg--バイト連結)
   - 4.3 [音声キャッシュ管理 (MD5・LRU・容量制限)](#43-音声キャッシュ管理-md5lru容量制限)
   - 4.4 [時間帯別自動音量調整 (Auto Volume)](#44-時間帯別自動音量調整-auto-volume)
   - 4.5 [外部音声エンジン自由追加アーキテクチャ (TTS Engine Extensibility)](#45-外部音声エンジン自由追加アーキテクチャ-tts-engine-extensibility)
   - 4.6 [発声時刻指定（タイマー予約発声）仕様](#46-発声時刻指定タイマー予約発声仕様)
5. [おやすみ・会議モード (DND) 仕様](#5-おやすみ会議モード-dnd-仕様)
   - 5.1 [DND 優先度判定パイプライン](#51-dnd-優先度判定パイプライン)
   - 5.2 [3つの抑制動作モード (Skip / Whisper / Queue)](#52-3つの抑制動作モード-skip--whisper--queue)
   - 5.3 [保留キューの永続化 (WAL) と起動時安全復元](#53-保留キューの永続化-wal-と起動時安全復元)
   - 5.4 [保留メッセージの AI 自動要約・キャッチアップ](#54-保留メッセージの-ai-自動要約キャッチアップ)
6. [緊急速報・防災情報および天気予報連携仕様](#6-緊急速報防災情報および天気予報連携仕様)
   - 6.1 [P2P地震情報 WebSocket 連携 (EEW / 震度速報)](#61-p2p地震情報-websocket-連携-eew--震度速報)
   - 6.2 [気象庁 防災気象情報 API 差分監視 (警報・特別警報)](#62-気象庁-防災気象情報-api-差分監視-警報特別警報)
   - 6.3 [気象庁 天気予報 API 連携 (朝のまとめへの自動注入)](#63-気象庁-天気予報-api-連携-朝のまとめへの自動注入)
   - 6.4 [通知先スピーカー制御と Urgent モード](#64-通知先スピーカー制御と-urgent-モード)
7. [AI 連携エンジン仕様 (AI Service)](#7-ai-連携エンジン仕様-ai-service)
   - 7.1 [対応プロバイダー (Google Gemini / OpenAI / ローカル LLM)](#71-対応プロバイダー-google-gemini--openai--ローカル-llm)
   - 7.2 [モデル自動ディスカバリーと耐障害フォールバック (503 / 429 耐性)](#72-モデル自動ディスカバリーと耐障害フォールバック-503--429-耐性)
   - 7.3 [朝の予定まとめ・コンテキスト注入](#73-朝の予定まとめコンテキスト注入)
8. [各種スマートスピーカー・音響機器の接続仕様](#8-各種スマートスピーカー音響機器の接続仕様)
   - 8.1 [Google Home / Nest (Google Cast)](#81-google-home--nest-google-cast)
   - 8.2 [Amazon Echo / Alexa (Remote Control & Atnrトークン)](#82-amazon-echo--alexa-remote-control--atnrトークン)
   - 8.3 [Apple HomePod (AirPlay 2 / pyatv)](#83-apple-homepod-airplay-2--pyatv)
   - 8.4 [ONVIF ネットワークカメラ (Two-Way Audio / Profile T)](#84-onvif-ネットワークカメラ-two-way-audio--profile-t)
   - 8.5 [DLNA / UPnP ネットワークオーディオ (MediaRenderer)](#85-dlna--upnp-ネットワークオーディオ-mediarenderer)
9. [Apple HomeKit / Homebridge プラグイン仕様 (`homebridge-voicehub`)](#9-apple-homekit--homebridge-プラグイン仕様-homebridge-voicehub)
   - 9.1 [プラグイン概要とアーキテクチャ](#91-プラグイン概要とアーキテクチャ)
   - 9.2 [提供アクセサリ仕様](#92-提供アクセサリ仕様)
   - 9.3 [設定スキーマ (`config.json`)](#93-設定スキーマ-configjson)
   - 9.4 [セットアップ手順](#94-セットアップ手順)
10. [MCP (Model Context Protocol) サーバー仕様](#10-mcp-model-context-protocol-サーバー仕様)
    - 10.1 [アーキテクチャとエンドポイント](#101-アーキテクチャとエンドポイント)
    - 10.2 [提供ツール一覧](#102-提供ツール一覧)
    - 10.3 [AI アシスタント設定例 (Claude Desktop / Cursor / Cline)](#103-ai-アシスタント設定例-claude-desktop--cursor--cline)
11. [マルチ MQTT ブローカー ＆ Home Assistant MQTT Discovery 仕様](#11-マルチ-mqtt-ブローカー--home-assistant-mqtt-discovery-仕様)
    - 11.1 [マルチブローカー接続アーキテクチャ](#111-マルチブローカー接続アーキテクチャ)
    - 11.2 [トピック設計とメッセージ仕様](#112-トピック設計とメッセージ仕様)
    - 11.3 [Home Assistant MQTT Discovery 自動エンティティ仕様](#113-home-assistant-mqtt-discovery-自動エンティティ仕様)
    - 11.4 [リアルタイム接続ステータスサマリーボード](#114-リアルタイム接続ステータスサマリーボード)
12. [Web GUI インターフェース仕様](#12-web-gui-インターフェース仕様)
    - 12.1 [macOS 風 2カラム縦型設定ナビゲーション](#121-macos-風-2カラム縦型設定ナビゲーション)
    - 12.2 [発言履歴 (リアルタイム記録・再発言・試聴)](#122-発言履歴-リアルタイム記録再発言試聴)
    - 12.3 [Webhook コマンドビルダー ＆ プラグイン解説書モーダル](#123-webhook-コマンドビルダー--プラグイン解説書モーダル)
    - 12.4 [視覚的フィードバックとモダンアニメーション](#124-視覚的フィードバックとモダンアニメーション)
13. [完全 REST API リファレンス](#13-完全-rest-api-リファレンス)
14. [ファイル構成と永続化ディレクトリ](#14-ファイル構成と永続化ディレクトリ)
15. [システム内部アーキテクチャ詳細 (FastAPI モジュール仕様)](#15-システム内部アーキテクチャ詳細-fastapi-モジュール仕様)
    - 15.1 [コアモジュール (`app/core/`)](#151-コアモジュール-appcore)
    - 15.2 [サービスモジュール (`app/services/`)](#152-サービスモジュール-appservices)
    - 15.3 [ロギング・運用保守基盤（シームレスログ ＆ 起動時バナー）](#153-ロギング運用保守基盤シームレスログ--起動時バナー)

---

## 1. システムアーキテクチャ概要

Smart Home Speaker Voice Hub は、規格の異なる 5 つのスマートスピーカー・音響機器（**Google Home / Cast**、**Amazon Echo / Alexa**、**Apple HomePod / AirPlay 2**、**ONVIF ネットワークカメラ**、**DLNA / UPnP MediaRenderer**）を単一の抽象レイヤーで統合し、日本語音声（Edge-TTS）を宅内のスピーカーへ配信する音声プラットフォームです。

バックエンドは **Python 3.14 + FastAPI** による完全非同期（`async/await`）アーキテクチャで構築されており、高速な応答性と高い並行処理性能を備えています。

```text
[外部 Webhook / IFTTT]    [ブラウザ Web GUI]    [HomeKit / Siri]    [MCP クライアント]    [MQTT ブローカー]
          │                       │                    │                    │                   │
          ▼                       ▼                    ▼                    ▼                   ▼
    ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
    │                        FastAPI Core Engine (Python 3.14 フル非同期)                         │
    │                                                                                             │
    │  ┌───────────────────────┐  ┌───────────────────────────────────────┐  ┌─────────────────┐  │
    │  │ Security Perimeter    │  │ Deduplication & Priority Filter       │  │ MCP Server      │  │
    │  │ (Tunnel / Auth / IPv6)│  │ (DND / Meeting Keywords / Urgent)     │  │ (SSE / Tools)   │  │
    │  └───────────────────────┘  └───────────────────────────────────────┘  └─────────────────┘  │
    │                                                                                             │
    │  ┌───────────────────────┐  ┌───────────────────────────────────────┐  ┌─────────────────┐  │
    │  │ Edge TTS + Chime Mix  │  │ WAL Persistent Queue (Disk-backed)    │  │ Multi MQTT Hub  │  │
    │  │ (LRU Caching & Probe) │  │ (Webhook Queue & DND Recovery)        │  │ (HA Discovery)  │  │
    │  └───────────────────────┘  └───────────────────────────────────────┘  └─────────────────┘  │
    │                                                                                             │
    │  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
    │  │                  Cross-Platform Sync Engine (EMA Delay Compensation)                  │  │
    │  └───────────────────────────────────────────────────────────────────────────────────────┘  │
    └───┬──────────────────┬──────────────────┬──────────────┬───────────────┬────────────────────┘
        │                  │                  │              │               │
        ▼                  ▼                  ▼              ▼               ▼
 [ Google Cast ]    [ Amazon Alexa ]   [ Apple HomePod ] [ ONVIF Camera ] [ DLNA / UPnP ]
(pychromecast)     (Remote Control)   (pyatv / AirPlay) (go2rtc / Profile T) (async_upnp_client)
```

---

## 2. ネットワーク・アクセス制御およびセキュリティ設計

外部サービス（IFTTT、Slack、Home Assistant 等）からの Webhook 受信と、家庭内 LAN からの安全な Web GUI 運用を両立するため、多重の防御境界（Perimeter Security）を設けています。

### 2.1 デュアルレイヤー境界防御 (LAN vs Cloudflare Tunnel)

Cloudflare Tunnel（`cloudflared`）を利用して外部ドメイン（例: `voicehub.example.com`）を公開している場合、サーバー内部でリクエストの進入経路を厳格に判定します。

* **進入経路の判定基準 (`is_tunnel_request`)**:
  - HTTP ヘッダーに `CF-Ray`、`CF-Connecting-IP`、`CF-IPCountry` のいずれかが含まれているか
  - HTTP `Host` ヘッダーが環境変数 `TUNNEL_DOMAIN` と一致するか
* **アクセスポリシー**:
  - **Tunnel 経由のリクエスト**: **`/api/say`**、**`/api/webhook`**、および **`/mcp/sse`, `/mcp/messages`** のみアクセスを許可。
  - Web GUI（`/`, `index.html`, `app.js`）および管理系 API（`/api/settings`, `/api/devices`, `/api/history` 等）は **`403 Forbidden`** で即座に遮断されます。
  - これにより、万が一 Tunnel URL が外部に知られた場合でも、設定変更・発言履歴閲覧・認証情報の漏洩が構造的に防止されます。

### 2.2 Webhook トークン認証仕様 (WEBHOOK_TOKEN)

環境変数 `WEBHOOK_TOKEN`（または Web GUI の設定画面で設定されたトークン）が存在する場合、Webhook 呼び出し元に対して認証が行われます。

* **認証トークンの受取方法（以下のいずれか1つを付与）**:
  1. `Authorization: Bearer <WEBHOOK_TOKEN>` ヘッダー
  2. `X-API-KEY: <WEBHOOK_TOKEN>` ヘッダー
  3. URL クエリパラメータ `?token=<WEBHOOK_TOKEN>`
  4. JSON リクエストボディの `"token": "<WEBHOOK_TOKEN>"` フィールド
* **ローカルアクセスの自動バイパス**:
  - 宅内プライベートネットワーク（`127.0.0.1`, `::1`, `192.168.x.x`）のブラウザ Web GUI からの同一起源リクエスト（`Referer` または `Sec-Fetch-Site: same-origin`）は、利便性のためトークン入力を自動免除します。

### 2.3 Web GUI 管理者認証仕様 (ADMIN_PASSWORD)

環境変数 `ADMIN_PASSWORD`（または `WEB_PASSWORD`）が設定されている場合、Web GUI の管理画面および全管理 API（`/api/*`）へのアクセスがパスワードで保護されます。

* **認証方式**:
  - **セッション Cookie 方式 (`auth_token`)**: `/api/auth/login` でパスワードを送信すると、暗号学的に安全なランダムトークン（SHA-256）が発行され、HttpOnly Cookie として保持されます（有効期限: 30日間）。
  - **ダイレクトヘッダー方式 (外部自動化用)**: `X-Admin-Password: <パスワード>` または `Authorization: Bearer <パスワード>` を送信することで、スクリプトからも全管理 API を呼び出し可能です。

### 2.4 IPv6 ループバックバインド仕様

一部の家庭用ルーター（IPv6 IPoE / NGN環境など）では、外部からの IPv6 パケットがルーターのポートフォワーディングを経由せずサーバーに直接到達するリスクがあります。
本システムではネットワークバインドを厳密に分離しています：

* **IPv4**: `0.0.0.0:8080` で待ち受け（宅内 LAN からの Web GUI や API アクセスを許可）。
* **IPv6**: **`[::1]:8080` (ループバック専用)** で待ち受け。
* これにより、外部のグローバル IPv6 アドレス直打ちによる不正アクセスを遮断しつつ、ローカルPCからの `localhost`（::1）名前解決は正常に受け付けます。

### 2.5 クライアント判定・IPエイリアス・重複排除 (Deduplication)

* **クライアント検出**: リクエストの `from`, `client`, `sender` パラメータ、IP エイリアス辞書（設定画面で IP ごとに「玄関インターホン」「Home Assistant」等の名前を付与可能）、および User-Agent（IFTTT, Slack, Discord 等）から送信元を自動同定し、履歴画面に色付きバッジで記録します。
* **重複排除エンジン (`deduplication`)**:
  - 人感センサーやスマートカメラの連続検知による連呼を防止します。
  - 同一送信元から指定秒数（`cooldownSeconds`: デフォルト30秒）以内に完全に同一のテキストが送信された場合、発声をスキップして `200 OK`（`deduplicated: true`）を返却します。

---

## 3. 宛先解決マクロとスピーカー制御仕様

### 3.1 ターゲット指定記法＆マクロ一覧

発声 API（`/api/say`）の `devices` または `targets` には、単一のデバイス名や IP だけでなく、短縮マクロやカスタムグループを指定できます。

| 指定文字列 | 対象スピーカー・動作 |
|---|---|
| `ALL` または `*` | **家中すべてのスピーカー**。Google Cast全体グループ、全室Echo、全室HomePod、登録済みONVIFカメラ、DLNAレンダラーを一斉に解決。 |
| `GH:ALL` / `GOOGLE:ALL` | 宅内のすべての Google Home / Nest デバイス（全体 Cast グループ優先）。 |
| `AL:ALL` / `ALEXA:ALL` | 宅内のすべての Amazon Echo デバイス（Echo全体グループ優先）。 |
| `HP:ALL` / `HOMEPOD:ALL` | 宅内のすべての Apple HomePod デバイス。 |
| `ONVIF:ALL` / `CAM:ALL` | 宅内のすべての登録済み ONVIF ネットワークカメラ。 |
| `DLNA:ALL` | 宅内のすべての登録済み DLNA / UPnP ネットワークスピーカー。 |
| `default` | システムで指定された標準スピーカー（`.my.env` の `GOOGLE_HOME_IP` または GUI 指定のデバイス）。 |
| カスタムグループ名 (例: `1F`, `LDK`) | 設定画面の「デバイスグループ」で定義したスピーカーの組み合わせを展開。 |
| デバイス表示名 (例: `リビング`, `書斎`) | デバイス名に部分一致する端末を自動検索して解決。 |
| `alexa:<デバイス名>` | 特定の Amazon Echo デバイスを直接指定。 |
| `homepod:<IPまたはMAC>` | 特定の Apple HomePod デバイスを直接指定。 |
| `onvif:<IP>` | 特定の ONVIF ネットワークカメラを直接指定。 |
| `dlna:<IP>` | 特定の DLNA / UPnP レンダラーを直接指定。 |
| IPアドレス (例: `192.168.11.96`) | Google Cast デバイスの IP アドレス直打ち。 |

### 3.2 スピーカー種別の自動判別と解決アルゴリズム

スピーカーの解決は以下の優先順序で行われます：

1. **マクロ・グループの展開**: `ALL`, `CAM:ALL`, `DLNA:ALL`, `1F` などを構成端末の配列へ展開。
2. **Google Cast グループ集約 (`preferNativeGroups`)**:
   - 複数の Google Home を個別指定して同時に鳴らすと、Wi-Fi の揺らぎによって輪唱（エコー）が発生します。
   - `ALL` や全体が指定された場合、個別の IP をまとめ、Google Home アプリ等で作成された **Cast グループ（ポート 32xxx 等）** 1つに集約して送信します。これにより Google Cast プロトコルのネイティブ同期が働き、エコーのない綺麗な同期再生が行われます。
3. **プロトコル別の仕分け**:
   - **Google Cast**: `type: google` (pychromecast)
   - **Amazon Alexa**: `type: alexa` (Alexa Remote Control)
   - **Apple HomePod**: `type: homepod` (pyatv AirPlay 2)
   - **ONVIF Camera**: `type: onvif` (go2rtc Two-Way Audio / Profile T)
   - **DLNA Renderer**: `type: dlna` (UPnP AVTransport / RenderingControl)
4. **重複排除**: 同一の IP やストリーミング先が複数回解決された場合、自動的に単一の呼び出しにまとめます。

### 3.3 マルチプラットフォーム音ズレ補正エンジン (Sync Engine)

Google Home、Amazon Echo、Apple HomePod は、通信プロトコル（Castv2、Alexa クラウド経由、AirPlay 2）の構造上、発声開始までに要する内部レイテンシが異なります。

* **オフセット遅延制御 (`alexaDelayMs`, `homepodDelayMs`, `googleDelayMs`)**:
  - クラウド経由でレイテンシが生じる Alexa に合わせ、応答の速い Google Home や HomePod の再生開始を意図的にミリ秒単位でディレイ（待機）させます。
* **動的自動学習 (`dynamicAutoAdjust`)**:
  - 発声時の RTT（ラウンドトリップタイム）を各プラットフォームごとに計測。
  - **指数移動平均 (EMA / $\alpha = 0.25$)** を用いて直近のネットワーク揺らぎを学習し、最適な遅延オフセットを自動計算・永続化します。

---

## 4. 音声合成 (TTS) とオーディオパイプライン仕様

### 4.1 Edge-TTS パラメータ

Edge-TTS の Neural 音声エンジン（SSML 対応）を採用しています。

* **標準ボイス (`voice`)**:
  - `ja-JP-NanamiNeural`: 七海（女性・標準アナウンス、透明感のある自然な声調）
  - `ja-JP-KeitaNeural`: 圭太（男性・標準、落ち着いたトーン）
  - `ja-JP-AoiNeural`: 碧（女性・穏やかで落ち着いた声調）
  - `ja-JP-DaichiNeural`: 大地（男性・低音で聞き取りやすい声調）
  - `ja-JP-MayuNeural`: 真夕（女性・明るく元気なトーン）
  - `ja-JP-NaokiNeural`: 直樹（男性・ニュース・案内放送調）
  - `ja-JP-ShioriNeural`: 詩織（女性・ニュース・案内放送調）
* **音響パラメータ**:
  - **話速 (`rate`)**: `+0%` (標準), `+20%` (高速), `-10%` (低速)
  - **音高 (`pitch`)**: `+0Hz` (標準), `+50Hz` (高め), `-30Hz` (低め)
  - **音量ゲイン (`volume`)**: `+0%` (標準), `+20%`, `-10%`

### 4.2 チャイム音声結合 (FFmpeg / バイト連結)

アナウンスの冒頭にチャイム音を鳴らして注意を惹くため、音声合成時にチャイムの結合が行われます。

* **チャイム種別 (`chime`)**:
  - `dingdong`: ピンポン音（`/public/sound/dingdong.mp3`）
  - `bell`: ベル音（`/public/sound/bell.mp3`）
  - `none`: チャイムなし（音声のみ即座に読み上げ）
* **結合処理**:
  - システム内の `ffmpeg` を用いて、サンプリングレート・ビットレートを 128kbps MP3 として再エンコード結合します（音割れやノイズを防止）。
  - `ffmpeg` が見つからない場合は、MP3 フレームのバイナリ連結にフォールバックします。
* **再生尺（Duration）の計測**:
  - 後続処理や同期エンジンが完了を把握できるよう、`ffprobe` を用いてミリ秒精度の音声長を計測します（失敗時は文字数に基づく計算式で推定）。

### 4.3 音声キャッシュ管理 (MD5・LRU・容量制限)

生成された音声ファイルは永続キャッシュディレクトリ（Docker ボリューム `smart_speaker_cache` / `/public/voice`）に保存されます。

* **キャッシュキー**:
  `MD5(text + "_" + voice + "_" + rate + "_" + pitch + "_" + volume + "_" + chimeType)`
* **LRU アクセス更新**:
  すでに生成済みの音声がリクエストされた場合、ディスクのファイル更新日時（`mtime`）を現在時刻に更新して再利用します。
* **自動クリーンアップ**:
  - 1時間ごとにキャッシュ総容量をチェック。
  - 上限容量（`MAX_CACHE_SIZE_MB` / デフォルト 1024MB）を超過した場合、最終アクセス日時の古いファイルから順に削除し、目標容量（上限の 90%）まで自動縮小します。

### 4.4 時間帯別自動音量調整 (Auto Volume)

朝の起床時間帯、昼間の活動時間帯、深夜の就寝時間帯など、時刻に応じてスピーカーの音量を自動調整する機能です。

* **日跨ぎ対応ルール**:
  - 例: `23:00` 〜 `07:00` を音量 `25%`、`07:00` 〜 `09:00` を `60%`、`09:00` 〜 `18:00` を `70%` など。
* API 呼び出し時に個別の `volumeLevel` が指定されていない場合、このカーブに基づいた音量が各スピーカーへ自動適用されます。

### 4.5 外部音声エンジン自由追加アーキテクチャ (TTS Engine Extensibility)

標準の Edge-TTS だけで完全自律稼働しますが、家庭内 LAN 内の別 PC や Docker で稼働しているローカル音声エンジン群（複数動的追加対応）、および公式クラウド音声 API（Azure / GCP）を自由に追加・併用できるプラグイン構造を備えています。

```text
                     ┌──────────────────────────────────────────────┐
                     │          発声リクエスト (say / urgent)         │
                     └──────────────────────┬───────────────────────┘
                                            │
               ┌────────────────────────────┴───────────────────────────┐
               ▼ (通常発話)                                              ▼ (緊急速報: urgent=True)
    [指定プロバイダー合成]                                       [最速並行生成: Fastest Wins]
    ├─► Azure Speech Service (公式SLAクラウド)                  ├─► Azure Speech
    ├─► Google Cloud TTS (Neural2/Standard)                     ├─► Google Cloud TTS
    ├─► ローカル音声エンジン群 (複数登録可)                     ├─► VOICEVOX / SHAREVOX / COEIROINK
    │   ├─► VOICEVOX (メインPC / GPUサーバー等)                 └─► 追加ローカル音声エンジン群
    │   ├─► SHAREVOX                                                        │
    │   └─► COEIROINK (192.168.11.245 等)                      asyncio.wait(FIRST_COMPLETED)
    └─► Edge-TTS (Azure未登録時)                                            │
               │                                                            ▼
       (タイムアウト/通信障害時)                                      最速完了音声を即採用
               │                                                 (残りの遅延タスクは即キャンセル)
               ▼
    【段階的フォールバック (Cascading Fallback)】
    Azure → GCP → ローカルエンジン群 → 🛡️ 最後の命綱: Edge-TTS
    (家庭内アナウンスを絶対に途切れさせない多重セーフティネット)
```

#### 4.5.1 対応音声合成プロバイダー一覧

| プロバイダー | 種別 | プロトコル・仕様 | 特徴・推奨ボイス |
|---|---|---|---|
| **Azure Speech Service** | クラウド (公式/無料枠あり) | 公式 Cognitive Services REST API | **公式推奨**。Microsoft 正規クラウド音声サービス。公式 SLA に基づき永続的・安定的に稼働。Azure 有効時は Edge-TTS が通常選択から待機化され、全障害時の最終セーフティネットとして安全に待機します。推奨: `azure:ja-JP-NanamiNeural`。 |
| **Google Cloud TTS (GCP)** | クラウド (従量課金/無料枠) | 公式 Cloud Text-to-Speech API | Neural2、Wavenet、Journey などの高品質クラウド音声。推奨: `gcp:ja-JP-Neural2-B`。 |
| **ローカル音声エンジン群 (VOICEVOX / SHAREVOX / COEIROINK / 互換)** | ローカル / LAN | REST API / 動的複数登録 | 家庭内 LAN 内の別 PC や Docker で稼働するエンジンを**何台でも追加・個別設定可能**。四国めたん、ずんだもん、らごぱすブラック、アメノちゃん等。モデル事前初期化 (`initialize_speaker`) 対応。 |
| **Edge-TTS (標準)** | クラウド (無料) | 非公式ブラウザ通信 | **標準搭載（Azure有効時は最終フォールバック待機）**。APIキー不要で即座に動作する7話者。手軽に利用できる一方、非公式手法のため将来の仕様変更リスクを伴います。 |

#### 4.5.2 耐障害・自動フォールバック設計
* 外部エンジンが起動していない、別 PC がスリープ中、あるいは指定秒数（`timeoutSeconds`: デフォルト 5.0秒）以内に合成が完了しなかった場合、エラーでアナウンスを落とすことなく、即座に **Edge TTS（七海）** へフォールバックして発声を継続します。
* 発言履歴ログにはフォールバックが発生した事実（`fallback: true`）が記録されます。

#### 4.5.3 緊急速報の最速並行生成 (Fastest Wins)
* 地震速報（EEW）や気象特別警報など、1秒を争う緊急アナウンス（`urgent: true`）を受信した際、有効化されているすべてのエンジン（Edge TTS、VOICEVOX、COEIROINK 等）へ同時に並行して音声合成リクエストを発行します。
* `asyncio.wait(..., return_when=FIRST_COMPLETED)` により、**0.1秒でも早く合成が完了した音声を即座にスピーカーへ送出**し、他の未完了タスクは直ちにキャンセルされます。これにより、エンジンの負荷やネットワーク揺らぎに左右されず、常に最短時間で警報を鳴らすことができます。

#### 4.5.4 クラウド無料枠月次使用量トラッカー
* Google Cloud TTS（Neural2: 月 100万文字、Standard: 月 400万文字）および Azure Speech（F0 プラン: 月 50万文字）の無料枠を超過して意図せぬ課金が発生することを防ぐため、文字数カウンターマネージャーを内蔵しています。
* 合成したテキストの文字数を `data/tts_usage.json` に永続記録し、毎月1日午前0時に自動リセットします。
* Web GUI の設定画面上で現在の当月消費文字数とパーセンテージ（プログレスバー）をリアルタイムに確認できます。

#### 4.5.5 クラウド音声エンジン（GCP / Azure）のキー取得手順

<details>
<summary><strong>💡 Google Cloud Text-to-Speech (GCP) API Key の取得手順</strong></summary>

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセスし、プロジェクトを選択（または新規作成）します。
2. 左メニューの「API とサービス」→「ライブラリ」を開き、**「Cloud Text-to-Speech API」** を検索して「有効にする」をクリックします。
3. 「API とサービス」→「認証情報」を開き、画面上部の「+ 認証情報を作成」→ **「API キー」** を選択します。
4. 生成された API キー（`AIzaSy...`）をコピーし、WebUI の「API Key」欄に入力します。
5. *(推奨設定)*: API キーの編集画面を開き、「API の制限」で「Cloud Text-to-Speech API」のみに限定しておくと安全です。

* **毎月の無料枠**: Neural2 / Journey 音声は **毎月 100万文字**、Standard 音声は **毎月 400万文字** まで無料枠が提供されています（Voice Hub 側で月次消費量を自動集計）。
</details>

<details>
<summary><strong>💡 Azure Speech Service キー・リージョンの取得手順・エラー対処</strong></summary>

> **【公式 Azure Speech をおすすめする理由】**
> * **標準の Edge TTS について**: 初期設定不要ですぐに動く反面、Edge ブラウザ用の非公式通信を利用しているため、Microsoft のサイレント仕様変更によって突然使えなくなるリスク（グレーな側面）があります。
> * **公式 Azure Speech のメリット**: Microsoft 公式の正規 API であるため仕様変更による停止リスクがなく、**「長期的に安定稼働させたい場合」** や **「Edge TTS が障害で不通になった際の堅牢なバックアップ」** として、公式無料枠（F0 プラン: 毎月 50万文字）の取得を推奨いたします。

1. [Azure ポータル](https://portal.azure.com/) にサインインします。
2. 上部検索バーで「音声サービス」(Speech Services) を検索し、「作成」をクリックします。
3. サブスクリプション、リソースグループを選択し、地域（例: **東日本 / `japaneast`**）を指定します。
4. 価格レベルで **「Free F0」**（無料プラン）を選択し、「確認および作成」をクリックしてデプロイします。
5. 作成完了後、リソースを開き、左メニューの「リソース管理」→ **「キーとエンドポイント」** を開きます。
6. **「キー 1」**（またはキー 2）をコピーして WebUI の「Speech Key」欄に、**「場所/地域」**（例: `japaneast`）を「リージョン」欄に入力します。

> **⚠️「テナント 'Microsoft Services' に存在しない」エラーが出る場合**
> 個人用 Microsoft アカウント（@outlook.jp, @gmail.com 等）で直接 Azure ポータルを開いた際や、ブラウザの古い認証情報が競合している際によく発生します。
> * **対処法**: ブラウザの**シークレットウィンドウ（InPrivate）**を開き、[Azure 無料アカウント作成ページ](https://azure.microsoft.com/ja-jp/free/) の**「無料で始める」**から初期登録を行ってからポータルにお進みください。

### 4.6 発声時刻指定（タイマー予約発声）仕様

「お風呂が沸いてから10分後にリマインド」「指定した時刻（19:30）に夕食のアナウンス」など、未来の特定日時にアナウンスを自動予約・発声させる機能です。

* **対応パラメータ名**:
  `at`, `time`, `scheduled_at`, `datetime`（すべて同等のエイリアスとして自動解釈されます）
* **指定可能な時刻フォーマット**:
  1. **相対時間指定**:
     - `+10m` (10分後), `+30m` (30分後), `+1h` (1時間後), `+45s` (45秒後) など、単位（`s`: 秒, `m`: 分, `h`: 時間, `d`: 日）を用いた直感的な指定。
  2. **時刻指定**:
     - `19:30`, `08:00:00` など（当日の指定時刻。すでに時刻が過ぎている場合は翌日の同時刻または即時判定）。
  3. **完全日時指定**:
     - `2026-10-19T15:00:00`, `2026-10-19 18:30:00` などの ISO 8601 / 日時文字列。
* **動作ライフサイクル**:
  1. **非同期即時応答**: 未来の日時が指定された場合、バックグラウンドのスケジューラーに予約タスクを登録し、即座に HTTP 200 OK（`{"status": "scheduled", "task_id": "...", "scheduled_at": "..."}`）を返却します。外部の呼び出し元（cURL、Home Assistant、Node-RED 等）を長時間待機させません。
  2. **定時自動実行**: 指定時刻の到来とともに、通常の音声合成・宛先解決・DND 優先度判定パイプラインが実行され、スピーカーからアナウンスが送出されます。
  3. **過去日時・空欄時の挙動**: 過去の日時や空欄が指定された場合は、遅延なく即時発声が行われます。
  4. **全連携機能との統合**: Web GUI（クイック選択チップ）、REST API (`/api/say`)、Webhook、MQTT (`voicehub/say`)、MCP サーバー (`speak(at=...)`, `list_scheduled_speeches`, `cancel_scheduled_speech`) のすべてでシームレスに機能します。

---

## 5. おやすみ・会議モード (DND) 仕様

在宅勤務のオンライン会議中や就寝中にスピーカーが突然大声で喋り出すのを防ぐための機構です。

### 5.1 DND 優先度判定パイプライン

発声リクエストが届いた際、以下の優先度ツリーに沿って判定されます：

```text
[発声リクエスト受信]
        │
        ├─► ① 緊急バイパス判定 (urgent === true または bypassDnd === true)
        │         └─► 【即時発声】 (すべての DND・会議・ミュート設定を強制貫通)
        │
        ├─► ② ワンタップ即時ミュート (Topバーミュート / manualUntil)
        │         └─► 【DND 発動】 (指定時間または手動解除まで抑制)
        │
        ├─► ③ カレンダー会議中判定 (Google カレンダー同期)
        │         └─► 現在時刻に会議キーワード (MTG, 会議, Zoom等) の予定があるか
        │                   └─► 【DND 発動】 (会議終了予定時刻まで抑制)
        │
        ├─► ④ 定時スケジュール判定 (平日日中・深夜帯など)
        │         └─► 該当曜日・時間帯に一致するか
        │                   └─► 【DND 発動】 (スケジュール終了まで抑制)
        │
        └─► ⑤ すべて非該当
                  └─► 【通常発声】
```

### 5.2 3つの抑制動作モード (Skip / Whisper / Queue)

1. **`skip` (スキップ)**:
   - 音を鳴らさずに破棄します。発言履歴に「スキップされた理由」が記録されます。
2. **`whisper` (囁き・極小音量モード)**:
   - 完全に無音にはせず、指定した極小音量（デフォルト `10%`）で控えめに発声します。
3. **`queue` (保留キューモード)**:
   - メッセージを保留キューに格納。会議や DND が解除されたタイミングでまとめて自動再生します。

### 5.3 保留キューの永続化 (WAL) と起動時安全復元

* **ディスク保存 (`/app/data/dnd_queue.json`)**:
  - 保留キューに追加されたメッセージは即座に JSON 永続化されます。
* **サーバー再起動時の誤再生防止**:
  - サーバーが再起動した際、Google カレンダーとの初回同期が完了するまでキューの消化を一時保留します。これにより、「会議中にサーバーが再起動して即座に大音量で保留が誤爆する」というトラブルを防止します。

### 5.4 保留メッセージの AI 自動要約・キャッチアップ

保留件数が設定値（デフォルト 2件以上）に達している場合、個別の音声を連続して鳴らす代わりに AI（Gemini / OpenAI 等）を呼び出し、1つの自然な音声メッセージに要約して読み上げます。

---

## 6. 緊急速報・防災情報および天気予報連携仕様

### 6.1 P2P地震情報 WebSocket 連携 (EEW / 震度速報)

P2P地震情報 API（`wss://api.p2pquake.net/v2/ws`）の WebSocket に常時接続し、気象庁発表の防災速報を低遅延で監視します。

* **緊急地震速報 (EEW / Code `556`)**:
  - 強い揺れが予想される際に即時発報。
  - **続報連呼防止**: `issue.eventId` によるメモリ追跡を行い、第2報・第3報が届いても同じ地震の警報を連呼せず1回のみ発報。
  - **取消報の自動検知**: 気象庁から取消報（`cancelled: true`）を受信した場合、発報済みイベントであれば「先ほどの緊急地震速報は取り消されました」と自動アナウンス。
* **地震情報・震度速報 (Code `551`)**:
  - 最低震度フィルター（震度1〜震度7）で小さな地震を無視可能。
  - 重複発報防止ロジック（`time_hypocenter_maxScale` の一意キー）で同一地震の複数回発話を防止。

### 6.2 気象庁 防災気象情報 API 差分監視 (警報・特別警報)

気象庁の公式データエンドポイント（`https://www.jma.go.jp/bosai/warning/data/warning/{prefCode}.json`）を 5分間隔で定期ポーリング監視します。

* **市区町村単位の高精度判定**:
  - 自治体コード（`class20` コード、例: 千代田区 `1310100`）の警報配列を監視。
  - 気象庁の種別コード（`03`: 大雨警報、`14`: 雷注意報 等）を内蔵マスター辞書で逆引きし、名称と危険度レベルを特定。
* **通知対象レベルの柔軟な設定**:
  - **特別警報のみ**: 生命に重大な危機が迫る特別警報時のみ発報。
  - **警報以上 (推奨・初期値)**: 大雨・洪水・暴風などの警報および特別警報を発表時に発報。
  - **注意報も含む**: 雷注意報、強風注意報、濃霧注意報なども含めて幅広くアナウンス。
* **警報解除時の通知**:
  - 警報が解除された際のアナウンスにも対応（ON/OFF選択可）。
* **差分ステートマシン**: 前回チェック時からの変化があった差分のみを抽出して発話します。

### 6.3 気象庁 天気予報 API 連携 (朝のまとめへの自動注入)

気象庁の週間予報データから、設定地域の「今日の天気」「最高気温・最低気温」「降水確率」を抽出します。
毎朝の予定まとめ放送において、カレンダー予定を読み上げる前に本日の天気とワンポイントアドバイス（傘や防寒の案内）を自然な文章で組み込みます。

### 6.4 通知先スピーカー制御と Urgent モード

緊急速報タブの **「📢 通知先スピーカー」** 設定により、アナウンス先を 3 つのスコープから選べます：
1. **`all` (家中すべてのスピーカー)**: 全室の Google Home、全室 Echo、全室 HomePod を一括起動し、全室一斉放送。
2. **`default` (標準スピーカーのみ)**: メイン端末1台のみで放送。
3. **`specific` (個別選択)**: チェックボックスで指定した部屋・端末のみで放送。

**Urgent モード** が有効な場合、会議中であっても DND を無視して強制的に割り込み再生されます。

---

## 7. AI 連携エンジン仕様 (AI Service)

### 7.1 対応プロバイダー (Google Gemini / OpenAI / ローカル LLM)

設定画面から API Key または URL を入力するだけで、以下のプロバイダーを自由に切り替えて利用できます：

* **Google Gemini API**: `gemini-2.5-flash`, `gemini-2.5-pro` 等の現行モデル
* **OpenAI API**: `gpt-4o`, `gpt-4o-mini`, `o3-mini` 等のモデル
* **ローカル LLM (Ollama)**: `http://localhost:11434` 等のローカル環境（Llama 3, Qwen 等）
* **DeepSeek API**: `deepseek-chat` など

### 7.2 モデル自動ディスカバリーと耐障害フォールバック (503 / 429 耐性)

* **モデル自動正規化**:
  設定ファイル内に過去の廃止モデルが残っていた場合、起動時および設定保存時に現行推奨モデル（`gemini-2.5-flash` 等）へ自動的に自己修復・正規化されます。
* **動的ディスカバリー**:
  設定画面の「モデル更新」ボタンを押すと、プロバイダーの有効モデル一覧 API を叩いて利用可能な最新モデルを動的取得します。
* **503 / 429 / 404 耐性フォールバック**:
  外部 AI API が一時的に利用できない場合（503 過負荷やレート制限等）でも、エラーで処理を止めず、ルールベースによる定型要約テキストを自動生成してアナウンスを継続します。

### 7.3 朝の予定まとめ・コンテキスト注入

毎朝の予定放送時、AI に以下のコンテキストを自動提供してプロンプトを構築します：
1. 現在時刻・日付・曜日
2. カレンダーから取得した当日の予定一覧（時刻、タイトル、場所）
3. 気象庁から取得した本日の天気・最高/最低気温・降水確率
4. ユーザーが指定した追加プロンプト（例: 「落ち着いた丁寧な敬語で」「簡潔に要点のみ」など）

---

## 8. 各種スマートスピーカー・音響機器の接続仕様

### 8.1 Google Home / Nest (Google Cast)
- **プロトコル**: Google Cast (castv2 / Avahi mDNS 探索)
- **ライブラリ**: `pychromecast` (Python ネイティブ実装)
- **特徴**: Google Home アプリで作成された「スピーカーグループ」への送信に対応しており、エコーのない同期再生が可能です。

### 8.2 Amazon Echo / Alexa (Remote Control & Atnrトークン)
- **プロトコル**: Amazon Alexa Remote Control (HTTPS / Cookie 認証)
- **連携方法**:
  1. **ブラウザプロキシ連携 (推奨)**: Web GUI の「Amazon ログインを開始」から、手元のブラウザで Amazon アカウントにログインするだけで連携完了。
  2. **リフレッシュトークン (`Atnr|...`) 手動登録**:
     ターミナルで `npx alexa-cookie2` を実行して取得した `Refresh Token: Atnr|...` を、Web GUI または `.my.env` (`REFRESH_TOKEN`) に登録して運用することも可能です。
- **全台発声時の公式 Everywhere グループ自動集約最適化**:
  アカウント内の全 Echo デバイスが発話対象となった場合（`devices: ["ALL"]` や `AL:ALL` 指定時）、個々の端末へ並行して個別 API を叩くのではなく、Amazon Alexa 公式の「Everywhere グループ（すべてのデバイス）」へ単一のブロードキャストコマンドとして自動集約します。これにより、Amazon 側の API レートリミット（429）を確実に回避し、複数台でのタイムラグやエコーのない同期同時鳴動を実現します。

### 8.3 Apple HomePod (AirPlay 2 / pyatv)
- **プロトコル**: Apple AirPlay 2 / RAOP (Bonjour / mDNS 探索)
- **ライブラリ**: `pyatv`
- **ネットワーク要件**:
  - 本サーバー（Docker）と Apple HomePod は、必ず**同一ローカルネットワーク（同じLAN / Wi-Fi、同一サブネット）**に接続されている必要があります。
  - Docker は `network_mode: host` を推奨します。ルーターのプライバシーセパレータや別VLANでセグメントが跨がっている場合、mDNS が届かず探索できません。

### 8.4 ONVIF ネットワークカメラ (Two-Way Audio / Profile T)
- **プロトコル**: ONVIF Profile T (WS-Discovery, UDP 3702, go2rtc 経由 RTSP バックチャンネル)
- **コーデック**: G.711 PCMU (8kHz 64kbps)
- **連携方法**:
  Web GUI の「ONVIF / DLNA」タブで「自動スキャン実行」を行うと、WS-Discovery により同一ネットワーク上のカメラ機器を自動検出します。Profile T（双方向音声）対応カメラをワンクリックで登録可能です。
- **go2rtc 通信堅牢化とタイムアウト・リトライ制御**:
  カメラ機器の起動遅延や Wi-Fi の一時的な電波揺らぎを考慮し、go2rtc バックチャンネルへの音声送出リクエストには `httpx.Timeout(30.0)` の適切なタイムアウトと非同期リトライハンドリングを実装。応答遅延による不用意な発声失敗を防止しています。

### 8.5 DLNA / UPnP ネットワークオーディオ (MediaRenderer)
- **プロトコル**: UPnP AVTransport / RenderingControl (SSDP, UDP 1900, SOAP)
- **対応機器**: Bose SoundTouch、Sonos、Denon HEOS、Yamaha MusicCast、foobar2000 (UPnP) 等
- **連携方法**:
  Web GUI の「ONVIF / DLNA」タブでスキャンすると自動検出されます。認証不要でそのまま登録・利用可能です。

---

## 9. Apple HomeKit / Homebridge プラグイン仕様 (`homebridge-voicehub`)

Homebridge をご利用のご家庭向けに、VoiceHub 専用の公式準拠プラグイン **`homebridge-voicehub`** を同梱しています。

### 9.1 プラグイン概要とアーキテクチャ
- **ディレクトリ**: `plugins/homebridge-voicehub/`
- **種別**: Dynamic Platform Plugin (`VoiceHubPlatform`)
- **設計**: 外部ライブラリへの依存が一切ない**ゼロ依存（Zero Dependencies）**構成。Node.js 18+ のネイティブ `fetch` を使用し、極めて軽量かつ堅牢に動作します。

### 9.2 提供アクセサリ仕様
1. **📢 プリセット発話プッシュスイッチ (`VoiceHubPresetSwitch`)**:
   - 「ご飯できたよ」「お風呂が沸いたよ」などの定型メッセージをスイッチ化。
   - Siri から「『ご飯できたよ』をつけて」と指示すると、VoiceHub API を呼び出して指定スピーカーから発声し、実行後自動で OFF に戻ります。
2. **🌙 会議・おやすみモード (DND) スイッチ (`VoiceHubDndSwitch`)**:
   - VoiceHub の DND 状態と完全連動。
   - Apple ホームの「おやすみ」シーンやオートメーションから DND を ON / OFF できます。
3. **🔊 スピーカー音量スライダー (`VoiceHubSpeakerAccessory`)**:
   - 各スピーカーを照明アクセサリ（明度スライダー方式）としてマッピング。
   - 「リビングの音量を 50% にして」といった Siri からの音量操作が可能です。

### 9.3 設定スキーマ (`config.json`)

```json
{
  "platforms": [
    {
      "platform": "VoiceHubPlatform",
      "name": "VoiceHub",
      "host": "http://127.0.0.1:8080",
      "webhookToken": "YOUR_OPTIONAL_TOKEN",
      "enableDndSwitch": true,
      "autoDiscoverSpeakers": true,
      "volumeAsLightbulb": true,
      "pollInterval": 30,
      "presets": [
        {
          "name": "ご飯できたよ",
          "text": "ご飯ができました。リビングに集まってください。",
          "target": "ALL",
          "volume": 70
        },
        {
          "name": "お風呂が沸いたよ",
          "text": "お風呂が沸き上がりました。",
          "target": "ALL",
          "volume": 60
        }
      ]
    }
  ]
}
```

### 9.4 セットアップ手順

```bash
cd plugins/homebridge-voicehub
npm install    # または bun install
npm run build  # または bun run build
npm link
```
または Homebridge Config UI X のプラグイン画面から `homebridge-voicehub` を検索してインストールします。

---

## 10. MCP (Model Context Protocol) サーバー仕様

Claude Desktop、Cursor、Cline などの AI アシスタントから直接スマートスピーカーを操作できる、FastAPI ネイティブの **MCP (Model Context Protocol) サーバー** を標準搭載しています。

### 10.1 アーキテクチャとエンドポイント
- **プロトコル**: MCP 2024-11-05 (JSON-RPC 2.0 over Server-Sent Events)
- **エンドポイント**:
  - `GET /mcp/sse`: クライアント接続用の SSE ストリーム。
  - `POST /mcp/messages`: JSON-RPC 2.0 リクエスト受付エンドポイント。
- **セキュリティ**:
  - `WEBHOOK_TOKEN` が設定されている場合、`Authorization: Bearer <WEBHOOK_TOKEN>` ヘッダーによる認証が行われます。
  - Cloudflare Tunnel 経由での外部接続時も、このエンドポイントへのアクセスが安全に許可されます。

### 10.2 提供ツール一覧

| ツール名 | 説明 | 主要引数 |
|---|---|---|
| `speak` | 指定したスピーカーへ音声を発話・予約 | `text` (必須), `target`, `volume`, `voice`, `urgent`, `at` (任意: `+10m`, `19:30` 等の予約時刻) |
| `list_speakers` | 利用可能な全スピーカー（Google, Alexa, HomePod, ONVIF, DLNA）の一覧を取得 | なし |
| `get_status` | システム状態（DND 状態、保留件数、デフォルト端末等）を取得 | なし |
| `set_dnd` | おやすみ・会議モード (DND) の有効化・解除 | `enabled` (必須), `durationMinutes`, `reason` |
| `get_history` | 直近の発言履歴ログ（直近 N 件）を取得 | `limit` (デフォルト 10) |
| `list_scheduled_speeches` | 現在スケジュールされている未来の発声予約タスク一覧を取得 | なし |
| `cancel_scheduled_speech` | スケジュールされた特定の発声予約タスクをキャンセル | `task_id` (必須) |

### 10.3 AI アシスタント設定例 (Claude Desktop / Cursor / Cline)

Web GUI の「MCP ツール連携」画面には、**「🏠 宅内 LAN (ローカル)」** と **「🌐 インターネット (Cloudflare Tunnel)」** をワンクリックで切り替えられるセグメントボタンが用意されており、環境に応じた設定 JSON スニペットが自動生成されます。

`claude_desktop_config.json` 等の設定例：

```json
{
  "mcpServers": {
    "voicehub": {
      "url": "http://127.0.0.1:8080/mcp/sse",
      "headers": {
        "Authorization": "Bearer YOUR_OPTIONAL_TOKEN"
      }
    }
  }
}
```
*(外出先やリモートの AI クライアントから接続する場合は、Web GUI のセグメントボタンで「インターネット」を選択し、表示される Tunnel 経由の URL をコピーしてご利用ください)*

---

## 11. マルチ MQTT ブローカー ＆ Home Assistant MQTT Discovery 仕様

Node-RED、Home Assistant、n8n などのホームオートメーションと連携するため、複数の MQTT ブローカーへ同時並行接続できるマルチ MQTT クライアントを内蔵しています。

### 11.1 マルチブローカー接続アーキテクチャ
- **ライブラリ**: `aiomqtt` (フル非同期 MQTT 3.1.1 / 5.0 クライアント)
- **機能**:
  - 複数のブローカー（例: 自宅 LAN の Mosquitto + クラウドブローカー）を同時に登録可能。
  - MQTTS (TLS 暗号化)、ユーザー名・パスワード認証対応。
  - 切断時の自動指数バックオフ再接続。

### 11.2 トピック設計とメッセージ仕様

| トピック | 種別 | 説明・ペイロード例 |
|---|---|---|
| `voicehub/say` | Subscribe (受信) | 発声コマンドの受付。JSON: `{"text": "こんにちは", "devices": ["ALL"], "at": "+10m"}` またはテキスト直打ち |
| `voicehub/dnd/set` | Subscribe (受信) | DND 切替コマンド。`ON`, `OFF`, `30`, `60`, `120` |
| `voicehub/status` | Publish (送信) | 定期ステータス発行。JSON: `{"status": "online", "dnd": false, "queued": 0}` |
| `voicehub/availability` | LWT (遺言) | 接続状態。`online` / `offline` |

※ `voicehub/say` で発声時刻（`"at": "+10m"` や `"at": "19:30"`）を指定すると、自動的にタイマー予約発声として登録され、指定時刻に実行されます。

### 11.3 Home Assistant MQTT Discovery 自動エンティティ仕様
設定画面で「Home Assistant Discovery」を有効にすると、`homeassistant/<component>/voicehub/.../config` トピックへ Discovery メッセージを自動発行し、Home Assistant 側に以下のエンティティが自動生成されます：
- **テキスト入力 (`text`)**: 発話テキスト送信フォーム
- **スイッチ (`switch`)**: 会議・おやすみモード (DND) 切替スイッチ
- **セレクト (`select`)**: 送信先スピーカー選択ボックス
- **ナンバー (`number`)**: スピーカー音量スライダー
- **センサー (`sensor`)**: 直近の発言内容、DND 状態センサー

### 11.4 リアルタイム接続ステータスサマリーボード
Web GUI の「MQTT ブローカー連携」画面上部には、登録されたすべてのブローカーの健全性を一目で把握できるサマリーボードが常時配置されています：
- **稼働台数バッジ**: 接続中 / 登録ブローカー数のリアルタイム集計（例: `1/1 稼働中`）
- **メインホスト情報**: 接続先 IP / ポートの明示
- **購読トピック・累計受信数**: リアルタイム送受信カウンタ
- **Home Assistant 連携ステータス**: HA Discovery の有効化状態および送出状況

---

## 12. Web GUI インターフェース仕様

### 12.1 macOS 風 2カラム縦型設定ナビゲーション
Web GUI の「拡張・システム設定」は、macOS や Home Assistant の設定画面に準拠した 2カラム構成を採用しています。
- **左カラム**: カテゴリ別（基本・音声、外部連携・API、システム・高度な設定）にグループ分けされたナビゲーションメニュー。
- **右カラム**: 選択されたカテゴリの設定カードがスムーズに切り替わります。

### 12.2 発言履歴 (リアルタイム記録・再発言・試聴)
直近 100 件の発言をリアルタイムで自動記録します。
- 送信元（Web UI、定期スケジュール、カレンダー連携、外部 API 等）を色付きバッジで視認可能。
- 履歴カードから「再発言」「ブラウザ試聴」「テキストコピー」をワンクリックで実行できます。

### 12.3 Webhook コマンドビルダー ＆ プラグイン解説書モーダル
- **Webhook コマンドビルダー**:
  画面上でスピーカーやメッセージを入力するだけで、cURL や IFTTT 向けの呼び出し設定が自動生成され、ワンクリックでコピーできます。
  - **⏰ 発声時刻指定 (at / time) 常時表示セクション**:
    アナウンス内容の直下に発声時刻指定枠が常時配置されており、「即時 (空欄)」「+5分後」「+10分後」「+15分後」「+30分後」「+1時間後」のクイック選択チップや「即時に戻す」ボタンからワンタップで設定可能。右側の cURL (GET/POST)、JSON、IFTTT スニペットにリアルタイム連動します。
- **プラグイン解説書モーダル**:
  Web 画面右上の「📖 プラグイン解説書を見る」ボタンから、いつでも Homebridge プラグインの導入手順や設定 JSON 例を確認・コピーできます。

### 12.4 視覚的フィードバックとモダンアニメーション
ユーザーが操作の進捗や状態を直感的に把握できるよう、以下のフィードバックデザインが適用されています：
- **保存ボタンの二段階遷移**:
  各種設定（全体設定、ONVIF認証、MQTT設定、Webhookトークン、TTSプロバイダー）の保存ボタン押下時、アイコンが「保存中（回転スピナー）」に変わり、完了時に「✓ 保存完了（エメラルドグリーンのバウンスアニメーション）」へと鮮やかに遷移し、数秒後に自然に戻ります。
- **アクティブボタンのグラデーショングロー**:
  MCP 接続環境選択（ローカル / インターネット）やフィルターボタンにおいて、選択中の要素に青紫グラデーションと発光グロー（`box-shadow`）が付与され、現在の状態が一目で判別できます。
- **ONVIF / DLNA スキャンプログレスバー**:
  探索処理実行中（約8秒間）、デバイス一覧の上部に滑らかな青色アニメーションバーが表示され、進行中であることが視覚的に明示されます。

---

## 13. 完全 REST API リファレンス

すべての API は JSON 形式をサポートしています。

### 13.1 発声・Webhook API
- **`POST /api/say`** / **`GET /api/say`**: スピーカーへの発話実行
  - **主要パラメータ**:
    - `text` (必須): 発話させたい日本語テキスト
    - `targets` / `devices` / `target`: 宛先スピーカー（配列または単数形文字列）
    - `volumeLevel` / `volume`: 音量 (0〜100)
    - `rate` / `speed`: 速度 (`+10%`, `-10%` 等)
    - `pitch`: 音高 (`+5Hz`, `-5Hz` 等)
    - `voice`: 音声モデル名 (Edge-TTS / Azure / ローカルエンジン等)
    - `chime`: 発話前チャイム種別 (`chime1`, `chime2`, `none` 等)
    - `urgent` / `bypassDnd`: DND (おやすみモード) を強制バイパスするかどうか
    - `at` / `time` / `scheduled_at`: 未来の予約発声日時 (`+10m`, `19:30` 等)
- **`POST /api/webhook`** / **`GET /api/webhook`**: 外部 Webhook 経由の発話実行
- **`POST /api/tts`**: 音声合成ファイル（MP3）の直接生成・ダウンロード

### 13.2 予約発声（スケジュールスピーチ）API
- **`GET /api/schedule/speeches`**: 現在スケジュールされている未来の発声予約タスク一覧を取得
- **`POST /api/schedule/speeches/{id}/cancel`**: 指定した発声予約タスクをキャンセル

### 13.3 認証 API
- **`GET /api/auth/status`**: 認証設定状態およびログイン状態の取得
- **`POST /api/auth/login`**: 管理者パスワードによるログイン (Cookie 発行)
- **`POST /api/auth/logout`**: ログアウト処理

### 13.4 履歴・キュー API
- **`GET /api/history`**: 直近 100 件の発言ログ取得
- **`DELETE /api/history`**: 発言履歴ログのクリア
- **`GET /api/queue`**: 処理待ち Webhook キュー一覧の取得

### 13.5 デバイス・スピーカー API
- **`GET /api/devices`**: 検出された全スピーカー・グループ一覧の取得
- **`POST /api/devices/default`**: デフォルトスピーカー IP の変更

### 13.6 スケジュール API
- **`GET /api/schedules`**: スケジュール一覧の取得
- **`POST /api/schedules`**: スケジュールの新規登録
- **`PUT /api/schedules/{id}`**: スケジュールの更新
- **`DELETE /api/schedules/{id}`**: スケジュールの削除
- **`POST /api/schedules/{id}/toggle`**: 有効/無効の切り替え
- **`POST /api/schedules/{id}/run`**: スケジュールのテスト実行

### 13.7 カレンダー連携 API
- **`GET /api/calendar/events`**: 同期済み予定一覧の取得
- **`POST /api/calendar/sync`**: Google カレンダー即時再同期
- **`POST /api/calendar/summary`**: 朝の予定まとめ発声テスト

### 13.8 おやすみ・会議モード (DND) API
- **`GET /api/dnd/status`**: 現在の DND 状態・保留件数の取得
- **`POST /api/dnd/quick`**: ワンタップ即時ミュートのオン/オフ
- **`GET /api/dnd/history`**: DND 抑制記録ログの取得
- **`DELETE /api/dnd/history`**: DND ログのクリア

### 13.9 防災・緊急速報 API
- **`GET /api/disaster/settings`**: 防災・気象設定の取得
- **`PUT /api/disaster/settings`**: 防災・気象設定の更新
- **`GET /api/disaster/areas`**: 地域マスター一覧の取得
- **`GET /api/disaster/weather`**: 設定地域の最新天気・アドバイスの取得
- **`GET /api/disaster/status`**: WebSocket 接続状態および現在の警報取得
- **`POST /api/disaster/test`**: シミュレーションテスト発報

### 13.10 AI 連携 API
- **`GET /api/ai/status`**: AI 連携状態の取得
- **`POST /api/ai/test`**: API Key の疎通検証
- **`GET /api/ai/models`**: 利用可能モデル一覧の動的取得
- **`POST /api/ai/summarize-test`**: 保留メッセージ要約テスト試聴
- **`POST /api/ai/calendar-test`**: カレンダー朝サマリー要約テスト試聴

### 13.11 システム設定 API
- **`GET /api/settings`**: システム全体設定の取得
- **`PUT /api/settings`**: システム全体設定の更新
- **`POST /api/settings/sync-test`**: スピーカー間音ズレ同期テスト

### 13.12 ハードウェア固有 API
- **`GET /api/alexa/status`**: Alexa 連携状態の取得
- **`POST /api/alexa/auth/start`**: Alexa プロキシログイン開始
- **`POST /api/alexa/auth/stop`**: Alexa プロキシログイン停止
- **`POST /api/alexa/token`**: リフレッシュトークン直接登録
- **`POST /api/alexa/logout`**: Alexa 連携解除
- **`GET /api/homepod/status`**: HomePod デバイス一覧取得
- **`POST /api/homepod/scan`**: HomePod 即時 mDNS 再スキャン
- **`POST /api/onvif/scan`**: ONVIF カメラ ＆ DLNA スピーカー自動探索
- **`POST /api/onvif/register`**: ONVIF / DLNA デバイスの登録・変更・解除
- **`POST /api/onvif/test`**: ONVIF / DLNA テスト発声
- **`POST /api/onvif/default-auth`**: カメラ共通デフォルト認証情報の保存

### 13.13 MQTT API
- **`GET /api/mqtt/status`**: 全 MQTT ブローカーの接続状態取得
- **`POST /api/mqtt/test`**: 指定ブローカーへの接続テスト
- **`POST /api/mqtt/reconnect`**: 全ブローカーの再接続

### 13.14 外部音声エンジン (TTS) API
- **`GET /api/tts/voices`**: 有効な全プロバイダー（Edge, VOICEVOX, SHAREVOX, COEIROINK, GCP, Azure）の統合話者一覧取得
- **`GET /api/tts/providers`**: 各プロバイダーの稼働・設定状態および当月文字数使用量（GCP/Azure無料枠）の取得
- **`POST /api/tts/providers/test`**: 指定プロバイダーの接続疎通検証、話者数検出、事前初期化テスト
- **`PUT /api/tts/providers/settings`**: 外部音声エンジン有効/無効、接続先URL、タイムアウト、最速並行生成設定の更新

### 13.15 システムログ API
- **`GET /api/logs`**: シームレスログ（メモリバッファと永続化ログファイルをマージした最新のシステムログ一覧）の取得（引数: `limit`, `level`）

---

## 14. ファイル構成と永続化ディレクトリ

```text
/root/google-home-voicetext-docker/
├── .my.env                     # 環境設定ファイル (秘密情報・ポート等)
├── .my.env.sample              # 環境設定サンプル
├── docker-compose.yml          # Docker Compose 定義
├── Dockerfile                  # Python 3.14 + go2rtc 同梱ビルド定義
├── Manual.md                   # 本総合技術仕様書
├── README.md                   # 一般向け概要・導入ガイド
│
├── data/                       # [Named Volume: smart_speaker_data]
│   ├── settings.json           # システム全体設定 (DND, 防災, AI, デバイス, MQTT, TTS等)
│   ├── tts_usage.json          # クラウドTTS (GCP/Azure) 月次消費文字数カウンター
│   ├── schedules.json          # 定期スケジュール定義
│   ├── dnd_queue.json          # DND 保留メッセージキュー (WAL)
│   ├── webhook_queue.json      # Webhook 非同期キュー (WAL)
│   ├── homepod_devices.json    # HomePod スキャンキャッシュ
│   └── .alexa.cookie           # Alexa 認証トークン
│
├── public/                     # Web フロントエンド静的配信
│   ├── index.html              # Web GUI Single Page Application
│   ├── app.js                  # フロントエンドロジック (optgroup動的グループ化・TTS連携)
│   ├── style.css               # グラスモーフィズム UI スタイル定義
│   ├── sound/                  # チャイム音源 (dingdong.mp3, bell.mp3)
│   ├── plugins/                # 配布用プラグイン静的公開ファイル
│   └── voice/                  # [Named Volume: smart_speaker_cache] 生成音声キャッシュ
│
├── app/                        # バックエンド実装 (Python 3.14 + FastAPI)
│   ├── main.py                 # FastAPI エントリーポイント、ライフスパン、ミドルウェア
│   ├── config.py               # Pydantic Settings による環境設定管理
│   ├── core/                   # 境界防御、認証、ロギング、重複排除基盤
│   ├── routers/                # REST API / SSE / MCP ルーター群
│   └── services/               # TTS、Cast、Alexa、HomePod、ONVIF/DLNA、DND、MQTT、MCP等の各サービス
│       └── tts/                # 外部音声エンジンプロバイダー基盤 (Edge, Voicevox, Sharevox, Coeiroink, GCP, Azure, Tracker)
│
├── plugins/
│   └── homebridge-voicehub/    # Homebridge 公式準拠プラットフォームプラグイン
│       ├── package.json
│       ├── tsconfig.json
│       ├── config.schema.json
│       ├── README.md
│       └── src/
│
└── bin/
    └── alexa_remote_control.sh # Alexa 制御補助スクリプト
```

---

## 15. システム内部アーキテクチャ詳細 (FastAPI モジュール仕様)

本システムは、すべての処理が非同期イベントループ（`asyncio`）上で効率的に動作するようモジュール設計されています。

### 15.1 コアモジュール (`app/core/`)
- **`security.py`**:
  Cloudflare Tunnel 判定、管理者セッション Cookie 検証、Webhook Bearer トークン認証を担当。
- **`deduplication.py`**:
  メモリ内キャッシュを用いた連呼防止エンジン。同一クライアントからの同一テキストをクールダウン秒数判定して重複排除。
- **`sync_engine.py`**:
  各スピーカーの RTT 計測結果に基づき、指数移動平均（EMA）で音ズレ補正オフセットを動的に計算。
- **`queue_manager.py`**:
  `asyncio.Queue` とディスク上の WAL（Write-Ahead Log）ファイルを同期させ、プロセス再起動時にも未処理メッセージを安全に復元。

### 15.2 サービスモジュール (`app/services/`)
- **`tts_service.py`**:
  プロバイダー別動的ルーティング、タイムアウト時の Edge TTS 自動フォールバック、緊急速報（`urgent: true`）時の最速並行生成（Fastest Wins）、FFmpeg チャイム結合、LRU ディスクキャッシュ管理。
- **`tts/` パッケージ**:
  - `base.py`: 抽象基底クラス `BaseTtsProvider`
  - `usage_tracker.py`: GCP/Azure の月次文字数カウントと無料枠管理（自動月次リセット）
  - `edge_provider.py`: Edge-TTS プロバイダー
  - `voicevox_provider.py`: VOICEVOX / SHAREVOX / COEIROINK (v2 API) クライアント
  - `gcp_provider.py`: Google Cloud Text-to-Speech クライアント
  - `azure_provider.py`: Azure Cognitive Services Speech クライアント
- **`cast_service.py`**:
  `pychromecast` による Google Cast デバイス・スピーカーグループの検出および再生制御。
- **`alexa_service.py`**:
  Amazon Echo デバイスへのアナウンス制御およびブラウザプロキシ認証管理。
- **`homepod_service.py`**:
  `pyatv` を用いた Apple HomePod の mDNS 探索および AirPlay 2 ストリーミング再生。
- **`onvif_service.py`**:
  WS-Discovery によるカメラ探索と、同梱 `go2rtc` 経由での Two-Way Audio バックチャンネルプッシュ。
- **`dlna_service.py`**:
  SSDP によるレンダラー探索と、UPnP AVTransport / RenderingControl SOAP 制御。
- **`dnd_service.py`**:
  カレンダー、スケジュール、手動タイマーの多層判定と、保留キュー・AI要約トリガーの管理。
- **`calendar_service.py`**:
  複数 Google カレンダー（iCal）の非同期取得・解析、直前リマインドおよび朝サマリー生成。
- **`disaster_service.py`**:
  P2P地震情報 WebSocket の常時接続管理、気象庁 API のポーリング監視と差分判定。
- **`ai_service.py`**:
  Gemini / OpenAI API との通信、モデル自動ディスカバリー、503 耐性フェイルオーバー。
- **`mqtt_service.py`**:
  `aiomqtt` による複数ブローカーへの同時接続、トピック購読・発行、および Home Assistant MQTT Discovery 自動管理。
- **`mcp_service.py`**:
  JSON-RPC 2.0 メッセージの解釈、SSE 接続管理、および各ツール（`speak`, `list_speakers`, `get_status`, `set_dnd`, `get_history`, `list_scheduled_speeches`, `cancel_scheduled_speech`）のディスパッチ処理。
- **`scheduler_service.py`**:
  発声予約（タイマー発声）タスクのメモリ管理、日時パーサー（相対 `+10m`、時刻 `19:30`、ISO8601対応）、バックグラウンド遅延実行ループ、および予約キャンセルハンドリング。

### 15.3 ロギング・運用保守基盤（シームレスログ ＆ 起動時バナー）
- **シームレスログ機構 (`core/logging.py`)**:
  - **メモリバッファ**: 直近 2,000 件のログレコードを `collections.deque` によるリングバッファでメモリ上に保持。超高速な WebUI リアルタイム閲覧を実現。
  - **永続化ログファイル (`logs/app.log`)**: ディスクへ常時書き出しを行い、再起動やコンテナ破棄に備えて永続保存。
  - **透過的自動マージ (`GET /api/logs`)**: WebUI がログを要求した際、直近のメモリバッファと再起動前の永続化ファイル内容を自動で時系列マージして返却。再起動直後でも過去のログが消えず、トラブルシューティングを極めて円滑に行えます。
- **システム起動時バナー (Startup Banner)**:
  - FastAPI の Lifespan 起動時に、システムバージョン、Python 実行環境、リッスン IP・ポート、有効化されたスピーカー連携（Cast, Alexa, HomePod, ONVIF, DLNA）、マルチ MQTT 接続構成、MCP サーバー待受状態等をアスキーアートバナーとともにログ先頭へ明刻。再起動の発生タイミングや稼働環境の変更が一目で把握できます。
