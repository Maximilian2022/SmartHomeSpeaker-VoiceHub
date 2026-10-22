# 変更履歴 (Changelog)

すべての重要な変更はこのファイルに記録されます。
フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づいています。

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
