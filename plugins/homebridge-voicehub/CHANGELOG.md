# 変更履歴 (Changelog)

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
