# homebridge-voicehub

[![npm version](https://badge.fury.io/js/homebridge-voicehub.svg)](https://badge.fury.io/js/homebridge-voicehub)
[![verified-by-homebridge](https://badgen.net/badge/homebridge/verified/purple)](https://github.com/homebridge/homebridge/wiki/Verified-Plugins)

**Smart Speaker Voice Hub** を Apple HomeKit / Siri とスムーズに連携させるための Homebridge 公式準拠プラットフォームプラグインです。

Google Cast、Amazon Alexa、Apple HomePod、ONVIF / DLNA スピーカーを Apple ホームアプリや Siri から手軽に操作でき、会議・おやすみモード (DND) の連動や定型アナウンスのオートメーションなどにご活用いただけます。

---

## 🌿 主な特徴

- **自動検出**: VoiceHub に登録されているスピーカー（Google Cast, Echo, HomePod, ONVIF/DLNA）やグループを検出し、HomeKit アクセサリとして自動登録します。
- **📢 プリセット発話プッシュスイッチ**: 「ご飯できたよ」「お風呂が沸いたよ」などの定型メッセージをスイッチ化。Siri から話しかけるだけで、指定のスピーカーから自然な日本語音声でアナウンスされます（実行後、自動で OFF に戻るプッシュボタン仕様）。
- **🌙 会議・おやすみモード (DND) スイッチ**: DND の ON / OFF を HomeKit スイッチとして操作できます。Apple ホームの「おやすみ」シーンやオートメーションと連携でき、DND 解除時には保留されていた通知を AI が要約してお知らせします。
- **🔊 個別スピーカー音量スライダー**: 各部屋のスピーカー音量を HomeKit のスライダーや Siri からパーセント指定（例:「リビングの音量を50%にして」）で調整できます。
- **ゼロ依存（Zero Dependencies）**: ネイティブ Fetch を採用しており、外部の追加パッケージに依存せず、軽量かつシンプルに動作します。
- **Homebridge Config UI X 対応**: ブラウザ上のグラフィカルな設定画面から手軽にセットアップしていただけます。

---

## 📦 インストール方法

### 方法 1: Homebridge Config UI X から（推奨）
1. Homebridge の管理画面を開きます。
2. 「プラグイン」タブで `homebridge-voicehub` を検索します。
3. 「インストール」をクリックします。

### 方法 2: コマンドラインから
```bash
npm install -g homebridge-voicehub
```
*(Bun をご利用の場合は `bun add -g homebridge-voicehub` でもインストール可能です)*

---

## ⚙️ 設定方法

Homebridge Config UI X の設定画面、または `config.json` の `platforms` セクションに以下を追加します：

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
        },
        {
          "name": "戸締まり確認",
          "text": "外出前の戸締まりと消灯を確認してください。",
          "target": "部屋",
          "volume": 65
        }
      ]
    }
  ]
}
```

### 設定パラメータ一覧

| パラメータ | 必須 | デフォルト値 | 説明 |
| :--- | :---: | :--- | :--- |
| `platform` | ○ | `VoiceHubPlatform` | プラットフォーム名（固定） |
| `name` | ○ | `VoiceHub` | ホームアプリ上での表示名 |
| `host` | ○ | `http://127.0.0.1:8080` | VoiceHub サーバーの URL |
| `webhookToken` | - | `""` | VoiceHub でトークン認証を有効化している場合に設定 |
| `enableDndSwitch` | - | `true` | 会議・おやすみモード（DND）切替スイッチを作成 |
| `autoDiscoverSpeakers` | - | `true` | VoiceHub に登録されたスピーカーの自動検出とアクセサリ登録 |
| `discoverGoogleHome` | - | `true` | Google Home / Nest スピーカーの登録有効化 |
| `discoverAlexa` | - | `true` | Amazon Alexa / Echo スピーカーの登録有効化 |
| `discoverHomepod` | - | `true` | Apple HomePod スピーカーの登録有効化 |
| `discoverOnvif` | - | `true` | ONVIF カメラ・スピーカー (Tapo含む) の登録有効化 |
| `discoverDlna` | - | `true` | DLNA / UPnP スピーカーの登録有効化 |
| `volumeAsLightbulb` | - | `true` | 音量を照明タイル（明度スライダー）として直感的に操作可能にする |
| `pollInterval` | - | `30` | DND 状態の同期インターバル（秒） |
| `presets` | - | `[...]` | プリセット発話スイッチの配列 |

---

## 🗣️ Siri 音声操作・オートメーション活用例

### 1. Siri からの一言アナウンス
- *「Hey Siri, ご飯できたよ をつけて」*
  → 家中のスピーカーから「ご飯ができました。リビングに集まってください」とアナウンスされ、スイッチは自動で OFF に戻ります。
- *「Hey Siri, 会議モード をつけて」*
  → DND が有効になり、家族のスピーカー通知が自動で保留されます。

### 2. Apple HomeKit オートメーション連動
- **人感センサー反応時**: 玄関の人感センサーが反応したら、VoiceHub の特定プリセット「おかえりなさい」をトリガー。
- **シーン連動**: 「おやすみ」シーン実行時に DND スイッチを ON にし、朝の「おはよう」シーンで OFF にして保留通知の AI 要約を再生。

---

## 🛠️ 開発・ビルド

### Node.js (npm) でのビルド
```bash
git clone https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub.git
cd SmartHomeSpeaker-VoiceHub/plugins/homebridge-voicehub
npm install
npm run build
npm link
```

### Bun でのビルド
Bun をお使いの場合、以下のように迅速にビルドいただけます：
```bash
bun install
bun run build
```

---

## 📄 ライセンス

Apache License 2.0
