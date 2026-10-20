# 変更履歴 (Changelog)

すべての重要な変更はこのファイルに記録されます。
フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づいています。

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
