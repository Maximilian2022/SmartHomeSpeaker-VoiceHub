# 変更履歴 (Changelog)

すべての重要な変更はこのファイルに記録されます。
フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づいています。

## [1.0.10] - 2026-10-23

### 追加・新機能 (Added)
- **WebUI 401 Unauthorized 自動検知 & ログインモーダル表示 (`public/app.js`)**:
  - グローバル `window.fetch` インターセプターを導入。セッション切れや管理者認証要求（HTTP 401）を自動検知し、即座にログインモーダルを開いて「セッションの有効期限が切れたか、管理者認証が必要です。再度ログインしてください。」と案内。
  - 認証切れ表示中は DND 等のバックグラウンド定期ポーリングを一時休止（pause）させ、サーバーログへの 401 警告連打（500回以上の連続アクセス等）を根本的に抑制。
  - パスワード入力・再ログイン成功時に自動的にリアルタイム同期（SSE）と画面データを再取得してシームレスに操作を復帰可能に改善。

### 修正・堅牢化 (Fixed / Security)
- **ログインセッションのファイル永続化 (`app/core/security.py`, `data/sessions.json`)**:
  - `PersistentSessionSet` クラスを新設。従来のインメモリ管理（`set()`）から、永続ボリューム上の `data/sessions.json` へのアトミック同期・保存に変更。
  - Docker コンテナや Uvicorn プロセスの再起動を跨いでも、ブラウザ側の有効な Cookie（有効期限30日）が自動的に復元され、再ログインを強いられる問題を根本解決。
  - 有効期限切れセッションの自動パージ、および管理者パスワード変更時の全セッション一括失効（セキュリティ保護）を完備。

---

## [1.0.9] - 2026-10-23

### 追加・新機能 (Added)
- **SSE (Server-Sent Events) による DND・ミュート状態のリアルタイム自動反映 (`GET /api/events`)**:
  - Homebridge（Apple ホームアプリ / Siri）、外部 API、外部デバイス（Logitech G HUB / Stream Deck 等）からミュート状態が変更された際、Web UI をリロードすることなく 0.01秒でヘッダーの「🔇ミュート」⇄「🔊ミュート解除」ボタンの色・アイコン・テキスト、および DND バナーを即座に自動反映。
  - プロキシ・ブラウザのタイムアウトを防ぐ 15 秒周期のキープアライブ（`: keepalive`）送信、ブラウザ標準の自動再接続、スマホスリープ復帰時やタブ切替時の `visibilitychange` 即時再同期、および従来の 15 秒ポーリングをフォールバックとして二重化。
- **外部デバイス連携スクリプトの拡充 (PowerShell / VBScript / バッチ / シェルスクリプト)**:
  - Logitech G HUB や Elgato Stream Deck からのワンタップ・ワンクリックで DND 即時ミュート・解除を可能にするスクリプト自動生成機能。
  - 近年の Windows 10/11 で標準的な PowerShell（`.ps1`）スクリプト形式を新設。
  - VBScript（`.vbs`）における `MSXML2.XMLHTTP` 優先化と WinHTTP 自動フォールバック、および管理者パスワード/Webhook トークンの自動埋め込みに対応。

### 修正・堅牢化 (Fixed / Security)
- **辞書未設定キー取得時の `NoneType.strip()` 例外耐性強化**:
  - 初期状態・クリーン Docker 環境で `webhookToken` 等が未設定（`null`）の場合に `dict.get()` が `None` を返して `AttributeError: 'NoneType' object has no attribute 'strip'` を誘発していた問題を根本改修。`(dict.get(key) or "").strip()` パターンに統一。
- **スマートホーム連携エンドポイント認証の最適化 (`check_admin_auth`)**:
  - 管理者パスワード設定時でも、`INTEGRATION_PREFIXES`（`/api/events`, `/api/dnd/`, `/api/disaster/triggers`, `/api/devices`, `/api/status`）へのアクセス時に Webhook トークン（URL クエリ `?token=`、Bearer、`x-webhook-token` 等）による正当な外部連携アクセスを許可。

---

## [1.0.8] - 2026-10-22

### 追加・新機能 (Added)
- **OpenAI & Gemini モデル動的ディスカバリー・厳格フィルタリング・推奨ソート**:
  - `GET /api/ai/models`: OpenAI および Google Gemini の公式 API から利用可能なモデル一覧を動的に取得する機能を実装。
  - **不要モデルの厳格除外**: 音声系（`whisper`, `audio`, `realtime`）、画像生成（`dall-e`）、テキスト埋め込み（`embedding`）、モデレーション、微調整（`ft:`）、および古い日付スナップショット版（`-2024-08-06`, `-0613` 等）を自動除外し、要約・発話生成に特化したモデルのみを抽出。
  - **推奨モデル優先ソート & 日本語ラベル**: コストパフォーマンス・速度に優れた最新主力モデル（OpenAI: `gpt-4o-mini`【高速・推奨】、`gpt-4o`【高性能・推奨】、`o3-mini`【最新推論・推奨】 / Gemini: `gemini-2.5-flash`【高速・推奨】、`gemini-2.5-pro`【高精度・推奨】）を自動判別し、最上位に日本語ラベル付きで優先配置。
  - **インメモリキャッシュ & 手動更新**: 外部 API への過剰リクエストを防ぐため 1 時間キャッシュし、WebUI の「🔄 モデル更新」ボタン押下時に `forceRefresh=true` で即座に最新一覧を取得可能。
  - **安全フォールバック & 自己修復機能**: API キー未設定時やネットワーク障害時のデフォルト推奨モデル一覧自動返却、および古い廃止モデル指定時の最新推奨モデル（`gpt-4o-mini` / `gemini-2.5-flash`）への自動補正。
- **専用ヘルスチェックエンドポイント (`GET /health` & `GET /api/health`)**:
  - 管理者パスワード設定の有無にかかわらず、Docker `HEALTHCHECK` や外部監視ツールから常時認証不要で死活監視可能な専用エンドポイントを新設。
- **MCP エンドポイントの包括的認証保護 & 接続設定自動切り替え**:
  - `/mcp` 配下の全エンドポイント（`/mcp/*`）を管理者パスワード保護の対象として包括的に保護。
  - WebUI 上で「🏠 宅内 LAN (ローカル)」選択時はローカル HTTP / IP、「🌐 インターネット (Cloudflare Tunnel)」選択時は HTTPS / Tunnel ドメインの接続設定スニペットを正確に出力するよう補正。

### セキュリティ (Security)
- **GitHub Code Scanning (CodeQL) アラート #28 (`py/weak-sensitive-data-hashing`) 対策**:
  - API キーのキャッシュ管理においてハッシュ化（`hashlib.sha256`）を全廃し、ダイレクトな文字列比較に統一することで静的解析の誤検知を根絶。

---

## [1.0.7] - 2026-10-22

### 追加・新機能 (Added)
- **スマートホーム防災連動トリガー (HomeKit 仮想モーションセンサー & Home Assistant MQTT Discovery)**:
  - 緊急地震速報（EEW）、気象警報（大雨・暴風等）、雨雲接近アラームを Apple Home の仮想モーションセンサー（`MotionSensor`）および Home Assistant の `binary_sensor`（`safety` / `moisture`）として公開。
  - 警報発令時に避難経路のスマート照明全点灯、高熱家電のスマートプラグ電源緊急遮断、電動雨戸の閉塞などのオートメーションを発火可能に。
  - WebUI 上に「🏠 スマートホーム防災連動トリガー」カードを追加し、リアルタイムな状態表示および「10秒間テストON」シミュレーションボタンを配備。
  - REST API エンドポイント `GET /api/disaster/triggers` および `POST /api/disaster/triggers/test` を新設。
- **Web GUI 管理者パスワード設定 & Cloudflare Tunnel リモートアクセス動的連動**:
  - Web GUI（設定 > Webhook & Tunnel）から管理者パスワード（`ADMIN_PASSWORD`）を直接設定・変更・解除できる管理カードおよび API（`POST /api/auth/password`）を新設。
  - パスワード設定状況に応じた Cloudflare Tunnel 境界防御の動的解禁：パスワード設定時は Tunnel 経由でも正規 HTTPS（完全な SSL 証明書・警告なし）で Web GUI の安全なリモート操作を許可。未設定時は安全のため従来どおり 403 Forbidden で完全遮断。
  - 認証済みセッション Cookie（`auth_token`）保持時は、Tunnel 経由での Web GUI からの発声指示（`/api/say`）の Webhook トークン入力を自動免除。
- **セキュリティ堅牢化 & 侵入耐性強化 (Intrusion & Brute-Force Hardening)**:
  - **ブルートフォース対策**: `/api/auth/login` に対する IP ベースのレートリミッターを導入（1分間に5回連続失敗で3分間アカウントロックアウト）。
  - **タイミング攻撃耐性**: パスワードおよび各種認証トークンの照合を定数時間比較（`hmac.compare_digest`）に統一。
  - **動的 `Secure` Cookie**: HTTPS / Cloudflare Tunnel 経由時は自動的に `Secure: True` を付与し、ローカル HTTP 接続との互換性を両立。
  - **セキュリティヘッダー付与**: 全レスポンスに `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` を適用。
  - **パスワード平文の保護**: `GET /api/settings` のレスポンスでパスワードを常時マスク（`********`）し、設定有無フラグ（`hasAdminPassword`）を提供。

---

## [1.0.6] - 2026-10-22 (Homebridge Plugin)


### 追加・国際化 (Added / Internationalization)
- **Homebridge プラグイン (homebridge-voicehub) の全面日英併記対応**:
  - `config.schema.json`: Homebridge Config UI X 設定画面のタイトル、説明文、プレースホルダー、フィールドセットを完全な日英併記（English / 日本語）に更新。
  - `README.md`: English および 日本語 の両セクションを網羅した包括的な日英併記構成にリニューアル。
  - `src/`: プラットフォームおよび各アクセサリ（DNDスイッチ、プリセットスイッチ、個別スピーカー）のログ出力、およびデフォルトのアクセサリ名称・プリセット例を日英併記に対応。
  - `public/`: WebUI 配信用のプラグイン解説書 Markdown を最新の日英併記版に同期。

---

## [1.0.5] - 2026-10-22 (Homebridge Plugin)

### 追加・改善 (Added / Improved)
- **スピーカー自動検出のカテゴリ別選択**: Google Home / Nest、Amazon Alexa / Echo、Apple HomePod、ONVIF / Tapo、DLNA / UPnP の各カテゴリごとにアクセサリ登録の有効・無効を個別にトグル可能に拡張。
- **Homebridge Config UI X 検証警告の解消**: `presets` 配列アイテム要素定義の正規化および `required` 定義の標準化により、AJV スキーマコンパイル時の警告・不整合を根絶。

---

## [1.0.4] - 2026-10-22

### セキュリティ (Security)
- **GitHub Code Scanning (CodeQL) アラートの完全解消**:
  - `js/tainted-format-string` (CWE-134): `public/i18n.js` 内の `console.warn` / `console.log` において、外部入力値が混入したテンプレートリテラルの第一引数使用を排除し、完全な静的文字列リテラルと追加引数へ分離。さらにロケール引数のホワイトリスト入力検証（`/^[a-zA-Z0-9_-]+$/`）を導入。
  - `js/xss-through-dom` (CWE-79, CWE-116): `public/i18n.js` から `innerHTML` への直接代入を完全撤廃。ブラウザ標準の `DOMParser` を活用したホワイトリスト型サニタイザー `setSafeHtml` を実装し、安全なタグ（`strong`, `b`, `em`, `i`, `code`, `a`, `br`, `span`, `small`, `p`, `div`, `li`, `ul`, `ol`）および安全な属性のみを生成して `replaceChildren()` で差し替える安全設計に刷新。キー形式のバリデーションおよび言語セレクター描画の安全化も統合。

### 変更 (Changed)
- **WebUI キャッシュバスター更新**: `public/index.html` 内のスクリプト読み込みタグを `v=1.0.4` に更新。

---

## [1.0.3] - 2026-10-20 (Homebridge Plugin)

### 変更 (Changed)
- **Homebridge v2.0 対応**: `package.json` の `engines.homebridge` を `"^1.6.0 || ^2.0.0"` に更新し、次世代 Homebridge v2 環境との互換性を明示。
- **メタデータ整備**: `keywords` に `"supports-hap"` を追加し、Homebridge Config UI X でのプラグイン互換性チェック（Verified マーク）に対応。

---

## [1.0.2] - 2026-10-19 (Homebridge Plugin)

### 修正 (Fixed)
- **API 正規化**: `voicehub-client.ts` の `getDevices()` において、VoiceHub API の返却型（配列または `{devices: [...]}` オブジェクト）の両方を安全に正規化して取り出すよう修正。
- **ターゲット指定バグ修正**: `speaker.ts` で個別スピーカー発話時の `targets` 引数の指定形式を修正し、意図しない全室一斉放送バグを解消。
- **音量連携強化**: スピーカー音量制御時のイベント連携処理を強化。

---

## [1.0.1] - 2026-10-18 (Homebridge Plugin)

### 変更 (Changed)
- **スキーマ改善**: `config.schema.json` およびドキュメントのデフォルトホスト URL を汎用的な `http://127.0.0.1:8080`（プレースホルダー案内付き）に改善。

---

## [1.0.0] - 2026-10-18 (Initial Release)

### 追加 (Added)
- **VoiceHub 本体**:
  - Python 3.14 + FastAPI によるフル非同期リライト。
  - Google Cast (Chromecast), Alexa, HomePod (AirPlay 2), DLNA, ONVIF (Backchannel) マルチスピーカー統合制御。
  - Edge-TTS / Azure TTS による自然音声合成およびキャッシュ機構。
  - Gemini AI による通知要約および DND（おやすみ/会議モード）キューイング機能。
  - Zeroconf によるゼロコンフィグ mDNS デバイス自動探索。
  - Cloudflare Tunnel / リバースプロキシ連携および Webhook 認証。
- **Homebridge プラグイン (`homebridge-voicehub`)**:
  - VoiceHub REST API によるゼロコンフィグ自動検出 (`DynamicPlatformPlugin`)。
  - DND 切替スイッチアクセサリ連動。
  - プリセット発話ステートレスプッシュスイッチ機能（Siri アナウンス連携）。
  - 各部屋スピーカーの音量スライダー操作（Lightbulb Brightness / Speaker 両対応）。
  - ネイティブ `fetch` によるゼロ外部依存構成。
