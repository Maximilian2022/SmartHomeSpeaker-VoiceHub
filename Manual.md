# Smart Home Speaker Voice Hub 徹底仕様書 (Manual.md) 📘

本ドキュメントは、[README.md](file:///root/google-home-voicetext-docker/README.md) に記載しきれていない **Smart Home Speaker Voice Hub** の全機能仕様、内部アーキテクチャ、アクセス制御・セキュリティ設計、および全 REST API の詳細仕様を網羅した包括的なテクニカルリファレンスです。

---

## 目次

1. [システムアーキテクチャ概要](#1-システムアーキテクチャ概要)
2. [ネットワーク＆アクセス制御・セキュリティ仕様](#2-ネットワークアクセス制御セキュリティ仕様)
   - 2.1 [デュアルレイヤー境界防御 (LAN vs Cloudflare Tunnel)](#21-デュアルレイヤー境界防御-lan-vs-cloudflare-tunnel)
   - 2.2 [Webhook トークン認証仕様 (WEBHOOK_TOKEN)](#22-webhook-トークン認証仕様-webhook_token)
   - 2.3 [Web GUI 管理者認証仕様 (ADMIN_PASSWORD)](#23-web-gui-管理者認証仕様-admin_password)
   - 2.4 [IPv6 直打ち露出防止仕様 (ループバックバインド)](#24-ipv6-直打ち露出防止仕様-ループバックバインド)
   - 2.5 [クライアント判定＆IPエイリアス・重複排除 (Deduplication)](#25-クライアント判定ipエイリアス重複排除-deduplication)
3. [宛先解決マクロ＆マルチプラットフォーム同期エンジン](#3-宛先解決マクロマルチプラットフォーム同期エンジン)
   - 3.1 [ターゲット指定記法＆マクロ一覧](#31-ターゲット指定記法マクロ一覧)
   - 3.2 [スピーカー種別の自動判別と解決アルゴリズム](#32-スピーカー種別の自動判別と解決アルゴリズム)
   - 3.3 [マルチプラットフォーム音ズレ補正エンジン (Sync Engine)](#33-マルチプラットフォーム音ズレ補正エンジン-sync-engine)
4. [音声合成 (TTS)＆オーディオ処理仕様](#4-音声合成-ttsオーディオ処理仕様)
   - 4.1 [Microsoft Edge Neural TTS パラメータ](#41-microsoft-edge-neural-tts-パラメータ)
   - 4.2 [チャイム音声結合 (FFmpeg / バイト連結フォールバック)](#42-チャイム音声結合-ffmpeg--バイト連結フォールバック)
   - 4.3 [音声キャッシュ管理 (MD5・LRU・目標容量)](#43-音声キャッシュ管理-md5lru目標容量)
   - 4.4 [時間帯別自動音量調整 (Auto Volume)](#44-時間帯別自動音量調整-auto-volume)
5. [おやすみ・会議モード (DND) アーキテクチャ](#5-おやすみ会議モード-dnd-アーキテクチャ)
   - 5.1 [DND 優先度判定パイプライン](#51-dnd-優先度判定パイプライン)
   - 5.2 [3つの抑制動作モード (Skip / Whisper / Queue)](#52-3つの抑制動作モード-skip--whisper--queue)
   - 5.3 [保留キューの永続化 (WAL) と起動時安全復元](#53-保留キューの永続化-wal-と起動時安全復元)
   - 5.4 [保留メッセージの AI 自動要約・キャッチアップ](#54-保留メッセージの-ai-自動要約キャッチアップ)
6. [緊急速報・防災＆天気予報システム (Disaster Manager)](#6-緊急速報防災天気予報システム-disaster-manager)
   - 6.1 [P2P地震情報 WebSocket 常時接続 (EEW / 震度速報)](#61-p2p地震情報-websocket-常時接続-eew--震度速報)
   - 6.2 [気象庁 防災気象情報 API 差分監視 (警報・特別警報)](#62-気象庁-防災気象情報-api-差分監視-警報特別警報)
   - 6.3 [気象庁 天気予報 API 連携 (毎朝のまとめへの自動注入)](#63-気象庁-天気予報-api-連携-毎朝のまとめへの自動注入)
   - 6.4 [通知先スピーカー制御と Urgent モード](#64-通知先スピーカー制御と-urgent-モード)
7. [AI 連携・要約エンジン (AI Manager)](#7-ai-連携要約エンジン-ai-manager)
   - 7.1 [マルチプロバイダー対応](#71-マルチプロバイダー対応)
   - 7.2 [利用可能モデルの自動ディスカバリー](#72-利用可能モデルの自動ディスカバリー)
   - 7.3 [朝の予定まとめ・コンテキスト注入](#73-朝の予定まとめコンテキスト注入)
8. [完全 REST API リファレンス](#8-完全-rest-api-リファレンス)
   - 8.1 [発声・Webhook エンドポイント](#81-発声webhook-エンドポイント)
   - 8.2 [認証・セッション エンドポイント](#82-認証セッション-エンドポイント)
   - 8.3 [発言履歴・キュー管理 エンドポイント](#83-発言履歴キュー管理-エンドポイント)
   - 8.4 [デバイス・スピーカー エンドポイント](#84-デバイススピーカー-エンドポイント)
   - 8.5 [スケジュール管理 エンドポイント](#85-スケジュール管理-エンドポイント)
   - 8.6 [Google カレンダー連携 エンドポイント](#86-google-カレンダー連携-エンドポイント)
   - 8.7 [おやすみ・会議モード (DND) エンドポイント](#87-おやすみ会議モード-dnd-エンドポイント)
   - 8.8 [防災・緊急速報＆天気 エンドポイント](#88-防災緊急速報天気-エンドポイント)
   - 8.9 [AI 連携 エンドポイント](#89-ai-連携-エンドポイント)
   - 8.10 [システム設定＆同期 エンドポイント](#810-システム設定同期-エンドポイント)
   - 8.11 [ハードウェア固有連携 (Alexa / HomePod) エンドポイント](#811-ハードウェア固有連携-alexa--homepod-エンドポイント)
9. [ファイル構成と永続化ディレクトリ](#9-ファイル構成と永続化ディレクトリ)

---

## 1. システムアーキテクチャ概要

Smart Home Speaker Voice Hub は、規格やプロトコルが全く異なる 3大スマートスピーカー（**Google Home / Cast**、**Amazon Echo / Alexa**、**Apple HomePod / AirPlay 2**）を統一抽象化し、高品質な日本語音声合成（Microsoft Edge TTS）を宅内のあらゆる部屋に遅延なくアナウンスするための音声プラットフォームです。

```
[外部 Webhook / IFTTT / Home Assistant]   [ブラウザ Web GUI]   [P2P地震速報 WS / 気象庁 API]
                      │                           │                        │
                      ▼                           ▼                        ▼
        ┌────────────────────────────────────────────────────────────────────────┐
        │                 Smart Home Speaker Voice Hub Core Engine               │
        │                                                                        │
        │  ┌───────────────────────┐  ┌───────────────────────────────────────┐  │
        │  │ Security Perimeter    │  │ Deduplication & Priority Filter       │  │
        │  │ (Tunnel / Auth / IPv6)│  │ (DND / Meeting Keywords / Urgent)     │  │
        │  └───────────────────────┘  └───────────────────────────────────────┘  │
        │                                                                        │
        │  ┌───────────────────────┐  ┌───────────────────────────────────────┐  │
        │  │ Edge TTS + Chime Mix  │  │ WAL Persistent Queue (Disk-backed)    │  │
        │  │ (LRU Caching & Probe) │  │ (Webhook Queue & DND Recovery)        │  │
        │  └───────────────────────┘  └───────────────────────────────────────┘  │
        │                                                                        │
        │  ┌──────────────────────────────────────────────────────────────────┐  │
        │  │       Cross-Platform Sync Engine (EMA Delay Compensation)        │  │
        │  └──────────────────────────────────────────────────────────────────┘  │
        └─────────────────┬───────────────────┬───────────────────┬──────────────┘
                          │                   │                   │
                          ▼                   ▼                   ▼
                  [ Google Cast ]      [ Amazon Alexa ]    [ Apple HomePod ]
                 (castv2 / Bonjour)   (Remote Control)     (pyatv / AirPlay)
```

---

## 2. ネットワーク＆アクセス制御・セキュリティ仕様

外部サービス（IFTTT、Slack、Home Assistant など）からの Webhook 受信と、家庭内 LAN からの安全な Web GUI 運用を両立するため、多重の防御境界（Perimeter Security）が設計されています。

### 2.1 デュアルレイヤー境界防御 (LAN vs Cloudflare Tunnel)

Cloudflare Tunnel（`cloudflared`）を利用して外部ドメイン（例: `webhook.example.com`）を公開している場合、サーバー内部でリクエストの進入経路を厳格に判定します。

* **進入経路の判定基準 (`isTunnelRequest`)**:
  - HTTP ヘッダーに `CF-Ray`、`CF-Connecting-IP`、`CF-IPCountry` のいずれかが含まれているか
  - HTTP `Host` ヘッダーが環境変数 `TUNNEL_DOMAIN` と一致するか
* **アクセスポリシー**:
  - **Tunnel 経由のリクエスト**: **`/api/say`** および **`/api/webhook`** のみアクセスを許可。
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

### 2.4 IPv6 直打ち露出防止仕様 (ループバックバインド)

一部の家庭用ルーター（IPv6 IPoE / NGN環境など）では、外部からの IPv6 パケットがルーターのポートフォワーディングを経由せずサーバーに直接到達するリスクがあります。
本システムではネットワークバインドを厳密に分離しています：

* **IPv4**: `0.0.0.0:8080` で待ち受け（宅内 LAN からの Web GUI や API アクセスを許可）。
* **IPv6**: **`[::1]:8080` (ループバック専用)** で待ち受け。
* これにより、外部のグローバル IPv6 アドレス直打ちによる不正アクセスを完全に遮断しつつ、ローカルPCからの `localhost`（::1）名前解決は正常に受け付けます。

### 2.5 クライアント判定＆IPエイリアス・重複排除 (Deduplication)

* **クライアント検出**: リクエストの `from`, `client`, `sender` パラメータ、IP エイリアス辞書（設定画面で IP ごとに「玄関インターホン」「Home Assistant」等の名前を付与可能）、および User-Agent（IFTTT, Slack, Discord 等）から送信元を自動同定し、履歴画面に色付きバッジで記録します。
* **重複排除エンジン (`deduplication`)**:
  - 人感センサーやスマートカメラの連続検知による連呼スパムを防止します。
  - 同一送信元から指定秒数（`cooldownSeconds`: デフォルト30秒）以内に完全に同一のテキストが送信された場合、発声をスキップして `200 OK`（`deduplicated: true`）を返却します。

---

## 3. 宛先解決マクロ＆マルチプラットフォーム同期エンジン

### 3.1 ターゲット指定記法＆マクロ一覧

発声 API（`/api/say`）の `devices` または `targets` には、単一のデバイス名や IP だけでなく、高度な短縮マクロやカスタムグループを指定できます。

| 指定文字列 | 対象スピーカー・動作 |
|---|---|
| `ALL` または `*` | **家中すべてのスピーカー**。Google Cast全体グループ、全室Echo、全室HomePod を同時に解決し、0msズレで一斉発声。 |
| `GH:ALL` / `GOOGLE:ALL` | 宅内のすべての Google Home / Nest デバイス（全体 Cast グループ優先）。 |
| `AL:ALL` / `ALEXA:ALL` | 宅内のすべての Amazon Echo デバイス（Echo全体グループ優先）。 |
| `HP:ALL` / `HOMEPOD:ALL` | 宅内のすべての Apple HomePod デバイス。 |
| `default` | システムで指定された標準スピーカー（`.my.env` の `GOOGLE_HOME_IP` または GUI 指定のデバイス）。 |
| カスタムグループ名 (例: `1F`, `LDK`) | 設定画面の「デバイスグループ」で定義したスピーカーの組み合わせを展開。 |
| デバイス表示名 (例: `リビング`, `書斎`) | デバイス名に部分一致する端末を自動検索して解決。 |
| `alexa:<デバイス名>` | 特定の Amazon Echo デバイスを直接指定。 |
| `homepod:<IPまたはMAC>` | 特定の Apple HomePod デバイスを直接指定。 |
| IPアドレス (例: `192.168.11.96`) | Google Cast デバイスの IP アドレス直打ち。 |

### 3.2 スピーカー種別の自動判別と解決アルゴリズム

`speakToMultipleDevices(text, targetList, options)` は以下の優先順序でデバイスを特定・集約します：

1. **マクロ・グループの展開**: `ALL` や `1F` を構成端末の配列へ展開。
2. **Google Cast グループ集約 (`preferNativeGroups`)**:
   - 複数の Google Home を個別指定して同時に鳴らすと、Wi-Fi の揺らぎによってエコー（輪唱）が発生します。
   - `ALL` や全体が指定された場合、個別の IP をすべて破棄し、Google Home アプリ等で作成された **Cast グループ（ポート 32xxx 等）** 1つに集約して送信します。これにより Google Cast プロトコルのネイティブ同期が働き、**ズレ 0ms の完全同期** が実現します。
3. **重複排除**: 同一の IP やストリーミング先が複数回解決された場合、自動的に単一の呼び出しにまとめます。

### 3.3 マルチプラットフォーム音ズレ補正エンジン (Sync Engine)

Google Home、Amazon Echo、Apple HomePod は、通信プロトコル（Castv2, Alexa クラウド経由, AirPlay 2）の構造上、発声開始までに要する内部レイテンシが異なります。

* **オフセット遅延制御 (`alexaDelayMs`, `homepodDelayMs`, `googleDelayMs`)**:
  - クラウド経由で最もレイテンシの大きい Alexa に合わせ、応答が速い Google Home や HomePod の再生開始を意図的にミリ秒単位でディレイ（待機）させます。
* **動的自動学習 (`dynamicAutoAdjust`)**:
  - 発声時の RTT（ラウンドトリップタイム）を各プラットフォームごとに計測。
  - **指数移動平均 (EMA / $\alpha = 0.25$)** を用いて直近のネットワークジッターを学習し、最適な遅延オフセットを自動計算・永続化します。

---

## 4. 音声合成 (TTS)＆オーディオ処理仕様

### 4.1 Microsoft Edge Neural TTS パラメータ

本システムは、Microsoft Edge の高品位な Neural 音声エンジン（SSML 対応）を内蔵しています。

* **標準ボイス (`voice`)**:
  - `ja-JP-NanamiNeural`: 七海（女性・標準アナウンス、透明感のある自然な声調）
  - `ja-JP-KeitaNeural`: 圭太（男性・標準、落ち着いたトーン）
  - `ja-JP-AoiNeural`: 碧（女性・穏やかで落ち着いた声調）
  - `ja-JP-DaichiNeural`: 大地（男性・低音で聞き取りやすい声調）
  - `ja-JP-MayuNeural`: 真夕（女性・明るく元気なトーン）
  - `ja-JP-NaokiNeural`: 直樹（男性・ニュース・案内放送調）
  - `ja-JP-ShioriNeural`: 詩織（女性・ニュース・案内放送調）
* **音響補正パラメータ**:
  - **話速 (`rate`)**: `+0%` (標準), `+20%` (高速), `-10%` (低速)
  - **音高 (`pitch`)**: `+0Hz` (標準), `+50Hz` (高め), `-30Hz` (低め)
  - **音量ゲイン (`volume`)**: `+0%` (標準), `+20%`, `-10%`

### 4.2 チャイム音声結合 (FFmpeg / バイト連結フォールバック)

アナウンスの冒頭にピンポン音を鳴らして注意を惹くため、音声合成時にチャイムの結合が行われます。

* **チャイム種別 (`chime`)**:
  - `dingdong`: 標準のピンポン音（`/public/sound/dingdong.mp3`）
  - `bell`: ベル音（`/public/sound/bell.mp3`）
  - `none`: チャイムなし（音声のみ即座に読み上げ）
* **結合アルゴリズム**:
  - システム内に `ffmpeg` が存在する場合、`concat` フィルターを用いてサンプリングレート・ビットレートを 128kbps MP3 として完全に再エンコード結合します（音割れやクリックノイズなし）。
  - `ffmpeg` が見つからない場合は、MP3 フレームの純粋バイナリバッファ連結に安全フォールバックします。
* **再生尺（Duration）の正確な計測**:
  - 後続処理や同期エンジンが完了を把握できるよう、`ffprobe` を用いてミリ秒精度の音声長を計測します（失敗時は文字数に基づく計算式 `text.length / 5.2 + chime` で推定）。

### 4.3 音声キャッシュ管理 (MD5・LRU・目標容量)

生成された音声ファイルは永続キャッシュディレクトリ（Docker ボリューム `smart_speaker_cache` / `/app/public/voice`）に保存されます。

* **キャッシュキー**:
  `MD5(text + "_" + voice + "_" + rate + "_" + pitch + "_" + volume + "_" + chimeType)`
* **LRU アクセス更新**:
  すでに生成済みの音声がリクエストされた場合、ディスクのファイル更新日時（`mtime`）を現在時刻に更新して再利用します。
* **自動クリーンアップ**:
  - 1時間ごとにキャッシュ総容量をチェック。
  - 上限容量（`MAX_CACHE_SIZE_MB` / デフォルト 1024MB）を超過した場合、最終アクセス日時の古いファイルから順に削除し、目標容量（上限の 90%）まで自動縮小します。

### 4.4 時間帯別自動音量調整 (Auto Volume)

朝の起床時間帯、昼間の活動時間帯、深夜の就寝時間帯など、時刻に応じてスピーカーの音量を自動追従させる機能です。

* **日跨ぎ対応ルール**:
  - 例: `23:00` 〜 `07:00` を音量 `25%`、`07:00` 〜 `09:00` を `60%`、`09:00` 〜 `18:00` を `70%` など。
* API 呼び出し時に個別の `volumeLevel` が明示されていない場合、このカーブに基づいた音量が Cast / Echo / HomePod へ自動適用されます。

---

## 5. おやすみ・会議モード (DND) アーキテクチャ

仕事中のオンライン会議や深夜の就寝中に突然スマートスピーカーが大声で喋り出すのを防ぐためのインテリジェント・サイレント制御機構です。

### 5.1 DND 優先度判定パイプライン

発声リクエストが届いた際、以下の優先度ツリーに沿ってミリ秒単位で発声可否が判定されます：

```
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

DND 発動時の振る舞いを設定画面で自由に選択できます：

1. **`skip` (完全スキップ)**:
   - 一切音を鳴らさず破棄します。発言履歴および DND 履歴に「スキップされた理由」が記録されます。
2. **`whisper` (囁き・極小音量モード)**:
   - 完全に無音にはせず、指定した極小音量（デフォルト `10%`）で控えめに発声します。
3. **`queue` (保留キューモード)**:
   - メッセージをメモリおよびディスク上の保留キューに格納。会議や DND が解除された瞬間にまとめて自動再生します。

### 5.3 保留キューの永続化 (WAL) と起動時安全復元

* **ディスク保存 (`/app/data/dnd_queue.json`)**:
  - 保留キューに追加されたメッセージは即座に JSON 永続化されます。
* **サーバー再起動時の誤再生防止**:
  - サーバーが再起動した際、Google カレンダーとの初回同期が完了するまでキューの消化を一時保留します。これにより、「会議中にサーバーが再起動して即座に大音量で保留が誤爆する」というトラブルを防止します。

### 5.4 保留メッセージの AI 自動要約・キャッチアップ

長時間の会議や深夜が明けた際、保留されていた大量のアナウンスが1件ずつ連続して再生されると煩わしくなります。

* **閾値判定 (`aiSummaryThreshold`)**:
  - 保留件数が設定値（デフォルト 2件以上）に達している場合、個別の音声を鳴らす代わりに AI（Gemini / OpenAI 等）を呼び出します。
* **自然な要約アナウンス**:
  - 例: *「お疲れ様です！不在の間に2件の通知がありました。15時に宅配便が届いたのと、お風呂が沸いたお知らせです。」*
  - このように1つの自然な音声メッセージに要約してスマートスピーカーから読み上げられます。

---

## 6. 緊急速報・防災＆天気予報システム (Disaster Manager)

### 6.1 P2P地震情報 WebSocket 常時接続 (EEW / 震度速報)

P2P地震情報 API（`wss://api.p2pquake.net/v2/ws`）の WebSocket に常時接続し、気象庁発表の防災速報をゼロ遅延で監視します。

* **緊急地震速報 (EEW / Code `556`)**:
  - 強い揺れが予想される際にミリ秒単位で発報。
  - **同一地震の続報連呼防止**: `issue.eventId` によるメモリ追跡を行い、第2報・第3報などの更新電文が届いても同じ地震の警報を連呼せず1回のみ発報。
  - **取消報（誤報・キャンセル）の自動検知とアナウンス**: 気象庁から取消報（`cancelled: true`）を受信した場合、発報済みイベントであれば「先ほどの緊急地震速報は取り消されました。誤報、または観測値の修正によるものです。」と自動アナウンスして安心を伝達。未発報地域の場合は不要な混乱を防ぐため自動スキップ。
  - 発報音量（50〜100%）および Urgent モード（DND貫通）の独立設定。
  - 対象地域が自地域に含まれるかを自動判定（全国通知も可能）。
* **地震情報・震度速報 (Code `551`)**:
  - 最低震度フィルター（震度1〜震度7）で小さな地震を無視可能。
  - 対象範囲（「自地域のみ」または「全国」）。
  - 重複発報防止ロジック（`time_hypocenter_maxScale` の一意キーで同一地震の複数回発話を防止）。

### 6.2 気象庁 防災気象情報 API 差分監視 (警報・特別警報)

気象庁の公式データエンドポイント（`https://www.jma.go.jp/bosai/warning/data/warning/{prefCode}.json`）を 5分間隔で定期ポーリング監視します。

* **市区町村単位の高精度判定**:
  - 設定された自治体コード（`class20` コード、例: 千代田区 `1310100`）の警報配列を監視。
  - 「大雨警報」「洪水警報」「暴風警報」「特別警報」などの発表を即時検知。
* **警報解除時の通知**:
  - 警報が解除された際にも「大雨警報は解除されました」とアナウンス可能（ON/OFF選択可）。
* **差分ステートマシン**:
  - 前回チェック時の警報セットを保持し、変化があった差分のみを抽出して発話（スパム防止）。

### 6.3 気象庁 天気予報 API 連携 (毎朝のまとめへの自動注入)

気象庁の週間予報データ（`https://www.jma.go.jp/bosai/forecast/data/forecast/{prefCode}.json`）から、設定地域の「今日の天気」「最高気温・最低気温」「降水確率」を抽出します。

* **毎朝の予定まとめ自動注入**:
  - カレンダー連携の「朝の予定まとめ放送」において、予定を読み上げる前に本日の天気を自然な文章で組み込みます。
* **傘・服装ワンポイントアドバイス**:
  - 降水確率 40% 以上: *「念のため折りたたみ傘をお持ちください。」*
  - 降水確率 70% 以上: *「本日は雨具を忘れずにお持ちください。」*
  - 最高気温 30℃ 以上: *「熱中症対策を万全にしてお過ごしください。」*
  - 最低気温 5℃ 以下: *「防寒対策をしっかりしてお出かけください。」*

### 6.4 通知先スピーカー制御と Urgent モード

緊急速報タブの **「📢 通知先スピーカー」** 設定により、アナウンス先を 3 つのスコープから選べます：

1. **`all` (家中すべてのスピーカー / 推奨)**:
   - 全室の Google Home、全室 Echo、全室 HomePod を一括起動し、家中のどこにいても聞こえるよう最大音量で全室一斉放送。
2. **`default` (標準スピーカーのみ)**:
   - メイン端末1台のみで放送。
3. **`specific` (個別選択)**:
   - チェックボックスで指定した部屋・端末（リビング、廊下など）のみで放送。

また、**Urgent モード** が有効な場合、会議中であっても DND を無視して強制的に割り込み再生されます。

---

## 7. AI 連携・要約エンジン (AI Manager)

### 7.1 マルチプロバイダー対応

設定画面から API Key または URL を入力するだけで、以下のプロバイダーを自由に切り替えて利用できます：

* **Google Gemini API**: `gemini-2.5-flash`, `gemini-1.5-flash`, `gemini-2.0-flash` など
* **OpenAI API**: `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo` など
* **ローカル LLM (Ollama)**: `http://localhost:11434` 等のローカル環境（Llama 3, Qwen 等）
* **DeepSeek API**: `deepseek-chat` など

### 7.2 利用可能モデルの自動ディスカバリー

API Key を入力して接続テストを実行すると、プロバイダーの利用可能モデル一覧 API を叩いて現在のアカウントで有効なモデル群を自動取得し、UI のドロップダウンに動的反映します。

### 7.3 朝の予定まとめ・コンテキスト注入

毎朝の予定放送時、AI に以下のコンテキストを自動提供してプロンプトを構築します：

1. 現在時刻・日付・曜日
2. カレンダーから取得した当日の予定一覧（時刻、タイトル、場所）
3. 気象庁から取得した本日の天気・最高/最低気温・降水確率
4. ユーザーが指定した追加プロンプト（例: 「明るく元気な敬語で」「子供向けの口調で」など）

---

## 8. 完全 REST API リファレンス

すべての API は JSON 形式をサポートしています。

### 8.1 発声・Webhook エンドポイント

#### `POST /api/say` または `GET /api/say`
#### `POST /api/webhook` または `GET /api/webhook`

スピーカーにメッセージを発話させます。

* **認証**: `WEBHOOK_TOKEN` が設定されている場合、必須（外部アクセス時）。
* **リクエストパラメータ (JSON Body または URL Query)**:

| パラメータ | 型 | 既定値 | 説明 |
|---|---|---|---|
| `text` | string | (必須) | 発話させる日本語テキスト。 |
| `devices` / `targets` | array \| string | `['default']` | 送信先スピーカー名、IP、マクロ（`ALL`, `GH:ALL`, `AL:ALL`, `HP:ALL`, グループ名等）。配列またはカンマ区切り文字列。 |
| `voice` | string | 設定値 | Edge TTS 音声モデル (`ja-JP-NanamiNeural`, `ja-JP-KeitaNeural` 等)。 |
| `rate` | string | `+0%` | 話速 (`+20%`, `-10%` 等)。 |
| `pitch` | string | `+0Hz` | 音高 (`+50Hz`, `-30Hz` 等)。 |
| `volume` | string | `+0%` | Edge TTS 内部ボリュームゲイン。 |
| `volumeLevel` | number | 自動音量 | Google Cast / Echo 音量 (Cast: 0.0〜1.0 または 0〜100)。 |
| `chime` | string | 設定値 | チャイム種別 (`dingdong`, `bell`, `none`)。 |
| `urgent` / `bypassDnd` | boolean | `false` | `true` の場合、DND や会議中ミュートを強制貫通して即時発声。 |
| `async` | boolean | Webhook時は `true` | `true` の場合、即座に受付完了を返却してバックグラウンドでキュー処理。 |
| `wait` / `sync` | boolean | `false` | `true` の場合、音声再生の完了まで HTTP レスポンスを待機。 |
| `from` / `client` | string | `null` | 呼び出し元サービス名（履歴画面で識別バッジ表示）。 |
| `token` | string | `null` | 認証用トークン（ヘッダーで送れない場合）。 |

* **非同期レスポンス例 (`200 OK`)**:
```json
{
  "success": true,
  "status": "accepted",
  "async": true,
  "jobId": "job_1729051234567_abc123",
  "message": "発声リクエストを受付け、永続化キューに安全に保存しました（順次処理中）",
  "text": "ご飯ができましたよ！",
  "targets": ["192.168.11.97"]
}
```

* **同期レスポンス例 (`wait=true`, `200 OK`)**:
```json
{
  "success": true,
  "count": 1,
  "results": [
    { "target": "192.168.11.97", "status": "played", "type": "google" }
  ],
  "audio": {
    "filename": "speech_e6d947...mp3",
    "duration": 3.8
  }
}
```

---

### 8.2 認証・セッション エンドポイント

#### `GET /api/auth/status`
現在の管理者パスワード設定状況およびログイン状態を返却します。
```json
{
  "required": true,
  "authenticated": false
}
```

#### `POST /api/auth/login`
管理者パスワードでログインし、セッション Cookie を発行します。
* Request: `{"password": "管理者パスワード"}`
* Response (`200 OK`): `{"success": true}`

#### `POST /api/auth/logout`
セッションを無効化してログアウトします。

---

### 8.3 発言履歴・キュー管理 エンドポイント

#### `GET /api/history`
直近 100 件の発言ログ一覧を取得します。
```json
[
  {
    "id": "hist_1729051234567",
    "text": "おはようございます",
    "targets": ["ALL"],
    "voice": "ja-JP-NanamiNeural",
    "source": "schedule",
    "sourceLabel": "定期スケジュール",
    "clientName": "朝の挨拶",
    "clientIp": "127.0.0.1",
    "status": "success",
    "timestamp": 1729051234567
  }
]
```

#### `DELETE /api/history`
発言履歴ログを全件クリアします。

#### `GET /api/queue`
現在処理待ちの永続化 Webhook キュー一覧を取得します。

---

### 8.4 デバイス・スピーカー エンドポイント

#### `GET /api/devices`
宅内ネットワークで検出されたすべてのスピーカー（Google Cast, Alexa, HomePod, 各グループ）の一覧を取得します。
```json
{
  "devices": [
    {
      "id": "group_32094_192_168_11_85",
      "name": "ALL",
      "ip": "192.168.11.85:32094",
      "type": "google",
      "isGroup": true
    },
    {
      "id": "alexa_ALL",
      "name": "全室 Echo",
      "ip": "alexa:ALL",
      "type": "alexa",
      "isGroup": true
    },
    {
      "id": "dev_192_168_11_97",
      "name": "部屋",
      "ip": "192.168.11.97",
      "type": "google",
      "isDefault": true
    }
  ],
  "defaultIp": "192.168.11.97"
}
```

#### `POST /api/devices/default`
標準（デフォルト）スピーカーの IP を変更します。
* Request: `{"ip": "192.168.11.96"}`

---

### 8.5 スケジュール管理 エンドポイント

* `GET /api/schedules` - スケジュール一覧の取得
* `POST /api/schedules` - スケジュールの新規登録
  * Body: `{"name": "朝の挨拶", "cron": "0 7 * * *", "text": "おはようございます", "targets": ["リビング"], "voice": "ja-JP-NanamiNeural", "enabled": true}`
* `PUT /api/schedules/:id` - スケジュールの更新
* `DELETE /api/schedules/:id` - スケジュールの削除
* `POST /api/schedules/:id/toggle` - 有効/無効のワンタップ切り替え
* `POST /api/schedules/:id/run` - スケジュールの即時テスト実行

---

### 8.6 Google カレンダー連携 エンドポイント

* `GET /api/calendar/events` - 同期済みの本日・直近の予定一覧を取得
* `POST /api/calendar/sync` - Google カレンダーからの即時再同期を実行
* `POST /api/calendar/summary` - 朝の予定まとめ発話をテスト実行

---

### 8.7 おやすみ・会議モード (DND) エンドポイント

* `GET /api/dnd/status` - 現在の DND 発動状態（理由、解除予定時刻、保留キュー件数）を取得
```json
{
  "isDnd": true,
  "reason": "オンライン会議中 (MTG)",
  "until": "2026-10-16T15:00:00.000Z",
  "queuedCount": 2,
  "action": "queue"
}
```
* `POST /api/dnd/quick` - ワンタップ即時ミュートのオン/オフ
  * Request: `{"action": "set", "duration": "60", "reason": "集中作業中"}` （duration: `'30'`, `'60'`, `'120'`, `'indefinite'` / 解除時は `{"action": "clear"}`）
* `GET /api/dnd/history` - DND による抑制・保留・囁きの記録ログを取得
* `DELETE /api/dnd/history` - DND 記録ログをクリア

---

### 8.8 防災・緊急速報＆天気 エンドポイント

* `GET /api/disaster/settings` - 防災・気象・天気設定の取得
* `PUT /api/disaster/settings` - 防災・気象設定の更新（地域、EEW音量、警報レベル、通知先スピーカー等）
* `GET /api/disaster/areas` - 都道府県マスター（47都道府県）または市区町村一覧（`?prefCode=130000`）を取得
* `GET /api/disaster/weather` - 現在設定されている地域の最新天気予報・気温・降水確率・アドバイスを取得
* `GET /api/disaster/status` - P2P地震情報 WebSocket の接続状態、現在の警報一覧を取得
* `POST /api/disaster/test` - 動作シミュレーションテスト発声
  * Request: `{"type": "eew"}` (緊急地震速報) | `{"type": "eew_cancel"}` (緊急地震速報の取消テスト) | `{"type": "quake"}` (震度速報) | `{"type": "warning"}` (気象警報) | `{"type": "weather"}` (朝の天気サマリー試聴)

---

### 8.9 AI 連携 エンドポイント

* `GET /api/ai/status` - AI 有効化状態および設定プロバイダーを取得
* `POST /api/ai/test` - API Key 接続テスト（有効性の検証）
* `GET /api/ai/models` - 設定された API Key で利用可能なモデル一覧を動的取得
* `POST /api/ai/summarize-test` - DND 保留メッセージの要約シミュレーション試聴
* `POST /api/ai/calendar-test` - カレンダー予定＋天気の朝サマリー要約テスト試聴

---

### 8.10 システム設定＆同期 エンドポイント

* `GET /api/settings` - システム全体設定（DND, カレンダー, AI, 防災, 同期エンジン, IPエイリアス, グループ）の取得
* `PUT /api/settings` - システム全体設定の更新
* `POST /api/settings/sync-test` - スピーカー間の音ズレ同期テスト（「ポン、ピン、パン」の同期トーンを発声し、各端末の RTT を再計測）

---

### 8.11 ハードウェア固有連携 (Alexa / HomePod) エンドポイント

* `GET /api/homepod/status` - 認識されている HomePod 一覧の取得
* `POST /api/homepod/scan` - LAN 内の HomePod デバイスを即時 mDNS 再スキャン
* `GET /api/alexa/status` - Amazon Echo 連携の認証状態を取得
* `POST /api/alexa/auth/start` - ブラウザプロキシログインの開始（認証用ポートオープン）
* `POST /api/alexa/auth/stop` - ブラウザプロキシログインの停止
* `POST /api/alexa/token` - 手動取得したリフレッシュトークン（`Atnr|...`）の直接登録
* `POST /api/alexa/logout` - Alexa 連携の解除

---

## 9. ファイル構成と永続化ディレクトリ

Docker コンテナ運用時、以下のディレクトリ構造でデータが永続化されます：

```text
/root/google-home-voicetext-docker/
├── .my.env                     # 環境設定ファイル (秘密情報・ポート等)
├── .my.env.sample              # 環境設定サンプル
├── docker-compose.yml          # Docker Compose 定義
├── Dockerfile                  # マルチステージビルド定義 (Node + Python + pyatv)
├── Manual.md                   # 本詳細仕様書
├── README.md                   # 簡易概要・導入ガイド
│
├── data/                       # [Named Volume: smart_speaker_data]
│   ├── settings.json           # システム設定 (DND, 防災, AI, デバイスグループ等)
│   ├── schedules.json          # 定期スケジュール定義
│   ├── dnd_queue.json          # DND 保留メッセージキュー (WAL)
│   ├── webhook_queue.json      # Webhook 非同期永続化キュー (WAL)
│   ├── homepod_devices.json    # HomePod スキャンキャッシュ
│   └── .alexa.cookie           # Alexa 認証クッキー・トークン
│
├── public/
│   ├── index.html              # Web GUI Single Page Application
│   ├── app.js                  # Web GUI フロントエンドロジック
│   ├── style.css               # グラスモーフィズムUI スタイル定義
│   ├── sound/                  # チャイム音源 (dingdong.mp3, bell.mp3)
│   └── voice/                  # [Named Volume: smart_speaker_cache]
│       └── speech_<MD5>.mp3    # 生成された Edge TTS 音声キャッシュファイル
│
├── src/                        # バックエンド実装 (Node.js)
│   ├── server.js               # Express サーバー、ルーティング、境界セキュリティ
│   ├── tts.js                  # Edge TTS、チャイム結合、LRU キャッシュ管理
│   ├── devices.js              # デバイス管理、Castv2、mDNS ディスカバリー
│   ├── settings.js             # 設定マネージャー、永続化
│   ├── dnd.js                  # おやすみ・会議モード (DND) 判定エンジン
│   ├── calendar.js             # Google カレンダー同期、直前リマインド、予定まとめ
│   ├── disaster.js             # P2P地震情報 WebSocket、気象庁API監視、天気予報
│   ├── ai.js                   # Gemini / OpenAI / Ollama 連携要約エンジン
│   ├── alexa.js                # Amazon Alexa 制御ブリッジ (alexa_remote_control)
│   ├── homepod.js              # Apple HomePod 制御ブリッジ (pyatv)
│   ├── scheduler.js            # 定期アナウンス実行スケジューラー
│   └── queue.js                # Webhook 永続化非同期キュー
│
└── bin/
    ├── alexa_remote_control.sh # Alexa 制御シェルスクリプト
    └── homepod_scan.py         # pyatv スキャン・AirPlay2 ストリーミング実行スクリプト
```
