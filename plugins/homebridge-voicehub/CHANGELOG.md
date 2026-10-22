# 変更履歴 (Changelog)

## [1.0.6] - 2026-10-22
### 追加・国際化 (Added / Internationalization)
- `config.schema.json`: Homebridge Config UI X 設定画面のタイトル・説明文・プレースホルダー・フィールドセットを完全な日英併記（English / 日本語）に更新
- `README.md`: English および 日本語 の両セクションを網羅した包括的な日英併記ドキュメントにリニューアル
- `src/`: プラットフォームおよび各アクセサリ（DNDスイッチ、プリセットスイッチ、個別スピーカー）のログ出力、およびデフォルトのアクセサリ名称・プリセット例を日英併記に対応
- `public/`: WebUI 配信用のプラグイン解説書 Markdown を最新の日英併記版に同期

## [1.0.5] - 2026-10-22
### 追加 (Added)
- スピーカー自動検出・アクセサリ登録のカテゴリ別選択機能:
  - Google Home / Nest スピーカー (`discoverGoogleHome`)
  - Amazon Alexa / Echo スピーカー (`discoverAlexa`)
  - Apple HomePod スピーカー (`discoverHomepod`)
  - ONVIF カメラ・スピーカー (Tapo含む) (`discoverOnvif`)
  - DLNA / UPnP スピーカー (`discoverDlna`)
  それぞれのカテゴリごとに HomeKit アクセサリ登録の有効・無効を個別に選択可能に拡張。

### 修正 (Fixed)
- Homebridge Config UI X 設定画面で「設定の検証に失敗しましたが保存は可能です」という警告が表示される問題を解消:
  - `config.schema.json` の `layout` における `presets` 配列アイテム要素定義（`presets[].name`, `presets[].text` など）を Homebridge Config UI X の標準構文に正規化
  - JSON Schema における `required` 定義を親オブジェクトの配列形式（`"required": ["name", "host"]`）に標準化し、AJV スキーマコンパイル時の警告・不整合を根絶

## [1.0.4] - 2026-10-22
### セキュリティ (Security)
- `public/i18n.js`: GitHub Code Scanning (CodeQL) アラート（CWE-134 フォーマット文字列および CWE-79 / CWE-116 DOM XSS）を完全解消。DOMParser を活用したホワイトリスト型サニタイザー `setSafeHtml` の導入と静的フォーマット引数化。

## [1.0.3] - 2026-10-20
### 変更 (Changed)
- `package.json`: Homebridge v2.0 に対応するため `engines.homebridge` の指定を `"^1.6.0 || ^2.0.0"` に更新
- `package.json`: Homebridge 互換性メタデータキーワード `"supports-hap"` を追加

## [1.0.2] - 2026-10-19
### 修正 (Fixed)
- `voicehub-client.ts`: `getDevices()` において VoiceHub API の返却型（配列または `{devices: [...]}` オブジェクト）の両方を安全に正規化して取り出すよう修正
- `speaker.ts`: 個別スピーカー発話時の `targets` 引数の指定形式を修正し、意図しない全室一斉放送バグを解消
- デバイス音量制御時の連携処理を強化

## [1.0.1] - 2026-10-18
### 変更 (Changed)
- `config.schema.json` およびドキュメントのデフォルトホスト URL を汎用的な `http://127.0.0.1:8080`（プレースホルダー: `http://127.0.0.1:8080` または `http://192.168.1.100:8080`）に改善

## [1.0.0] - 2026-10-18
### 追加 (Added)
- 初回リリース
- VoiceHub REST API によるゼロコンフィグ自動検出 (`DynamicPlatformPlugin`)
- DND（会議・おやすみモード）切替スイッチアクセサリ（Gemini AI 要約連動）
- プリセット発話ステートレスプッシュスイッチ機能（Siri アナウンス連携）
- 各部屋スピーカーの音量スライダー操作（Lightbulb Brightness / Speaker 両対応）
- Homebridge Config UI X 設定スキーマ (`config.schema.json`) 対応
- ネイティブ fetch によるゼロ外部依存構成
- Node.js & Bun 両対応の高速ビルド構成
