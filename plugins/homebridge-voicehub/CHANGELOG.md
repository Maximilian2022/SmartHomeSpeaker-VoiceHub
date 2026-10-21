# 変更履歴 (Changelog)

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
