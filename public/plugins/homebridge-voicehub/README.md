# homebridge-voicehub

[![npm version](https://badge.fury.io/js/homebridge-voicehub.svg)](https://badge.fury.io/js/homebridge-voicehub)
[![verified-by-homebridge](https://badgen.net/badge/homebridge/verified/purple)](https://github.com/homebridge/homebridge/wiki/Verified-Plugins)

[English](#-english) | [日本語](#-japanese)

---

## 🌐 English

Official platform plugin for **Smart Speaker Voice Hub** to seamlessly integrate with Apple HomeKit and Siri.

Control your Google Cast, Amazon Alexa, Apple HomePod, and ONVIF / DLNA speakers directly from Apple Home and Siri. Supports meeting/sleep mode (DND) synchronization and preset speech automation switches.

### 🌿 Key Features

- **Auto-Discovery**: Automatically discovers all registered speakers (Google Cast, Echo, HomePod, ONVIF/DLNA) and speaker groups from VoiceHub and registers them as HomeKit accessories.
- **📢 Preset Speech Push Switches**: Create dedicated switches for frequent announcements (e.g., "Dinner is ready", "Bath is ready"). Triggering via Siri or scenes plays natural TTS voice announcements on target speakers (stateless push-button: automatically resets to OFF).
- **🌙 Do Not Disturb (DND) Switch**: Toggle DND mode via a HomeKit switch. Seamlessly integrate with Apple Home "Good Night" scenes and automations. When DND is turned off, VoiceHub's AI automatically summarizes and plays back queued notifications.
- **🚨 Disaster & Weather Automation Triggers**: Exposes virtual motion sensors for Earthquake Early Warning (EEW), JMA Weather Warnings, and Approaching Rain. You can use these sensors as triggers in Apple Home automations (e.g., turning on escape route lights, cutting heater power plugs, or closing electric shutters).
- **🔊 Speaker Volume Control**: Control individual speaker volume using HomeKit brightness sliders or Siri voice commands (e.g., *"Set Living Room volume to 50%"*).
- **Zero Dependencies**: Powered by native Node.js / Bun `fetch`, lightweight with zero external runtime dependencies.
- **Homebridge Config UI X Ready**: Intuitive graphical settings form with bilingual field descriptions.

### 📦 Installation

#### Method 1: Via Homebridge Config UI X (Recommended)
1. Open your Homebridge web interface.
2. Search for `homebridge-voicehub` in the **Plugins** tab.
3. Click **Install**.

#### Method 2: Via Command Line
```bash
npm install -g homebridge-voicehub
```
*(If using Bun, you can also install via `bun add -g homebridge-voicehub`)*

### ⚙️ Configuration

Add the following configuration to the `platforms` array in your Homebridge `config.json`, or configure via Homebridge Config UI X:

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
          "name": "Dinner is ready",
          "text": "Dinner is ready. Please come to the dining room.",
          "target": "ALL",
          "volume": 70
        },
        {
          "name": "Bath is ready",
          "text": "The bath is ready.",
          "target": "ALL",
          "volume": 60
        },
        {
          "name": "Lock Check",
          "text": "Please check all doors and windows before leaving.",
          "target": "Living Room",
          "volume": 65
        }
      ]
    }
  ]
}
```

#### Configuration Parameters

| Parameter | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `platform` | Yes | `VoiceHubPlatform` | Platform identifier (fixed). |
| `name` | Yes | `VoiceHub` | Display name in the Apple Home app. |
| `host` | Yes | `http://127.0.0.1:8080` | URL of your VoiceHub server. |
| `webhookToken` | No | `""` | Optional webhook authentication token if enabled in VoiceHub. |
| `enableDndSwitch` | No | `true` | Creates a toggle switch for Do Not Disturb (DND) / Meeting mode. |
| `enableDisasterSensors` | No | `true` | Exposes virtual motion sensors for EEW, Weather Warnings, and Rain alerts to trigger Apple Home automations. |
| `autoDiscoverSpeakers` | No | `true` | Automatically discovers and registers active speakers. |
| `discoverGoogleHome` | No | `true` | Enables discovery for Google Home / Nest speakers. |
| `discoverAlexa` | No | `true` | Enables discovery for Amazon Alexa / Echo speakers. |
| `discoverHomepod` | No | `true` | Enables discovery for Apple HomePod speakers. |
| `discoverOnvif` | No | `true` | Enables discovery for ONVIF cameras / Tapo speakers. |
| `discoverDlna` | No | `true` | Enables discovery for DLNA / UPnP speakers. |
| `volumeAsLightbulb` | No | `true` | Exposes volume control as a Lightbulb slider for intuitive HomeKit UI operation. |
| `pollInterval` | No | `30` | Polling interval in seconds to sync DND status with VoiceHub. |
| `presets` | No | `[...]` | Array of preset speech push-button switches. |

### 🗣️ Siri Voice Commands & Automation Examples

#### 1. Instant Siri Announcements
- *"Hey Siri, turn on Dinner is ready"*
  → Plays announcement across home speakers and automatically turns off the switch.
- *"Hey Siri, turn on Meeting Mode"*
  → Activates DND and holds incoming speaker notifications.

#### 2. Apple HomeKit Automations
- **Motion Sensor Trigger**: Trigger a welcome announcement when the entryway motion sensor detects presence.
- **Good Night Scene**: Turn ON the DND switch upon running the "Good Night" scene, and turn it OFF in the morning to hear the AI summary of queued notifications.
- **Disaster Trigger Automation**: When the EEW virtual motion sensor triggers, automatically turn on all lights to 100% white, unlock smart locks, and cut off smart plugs connected to high-heat appliances.

### 🛠️ Development & Build

```bash
git clone https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub.git
cd SmartHomeSpeaker-VoiceHub/plugins/homebridge-voicehub
npm install
npm run build
npm link
```

---

## 🇯🇵 日本語

**Smart Speaker Voice Hub** を Apple HomeKit / Siri とスムーズに連携させるための Homebridge 公式準拠プラットフォームプラグインです。

Google Cast、Amazon Alexa、Apple HomePod、ONVIF / DLNA スピーカーを Apple ホームアプリや Siri から手軽に操作でき、会議・おやすみモード (DND) の連動や定型アナウンスのオートメーションなどにご活用いただけます。

### 🌿 主な特徴

- **自動検出**: VoiceHub に登録されているスピーカー（Google Cast, Echo, HomePod, ONVIF/DLNA）やグループを検出し、HomeKit アクセサリとして自動登録します。
- **📢 プリセット発話プッシュスイッチ**: 「ご飯できたよ」「お風呂が沸いたよ」などの定型メッセージをスイッチ化。Siri から話しかけるだけで、指定のスピーカーから自然な日本語音声でアナウンスされます（実行後、自動で OFF に戻るプッシュボタン仕様）。
- **🌙 会議・おやすみモード (DND) スイッチ**: DND の ON / OFF を HomeKit スイッチとして操作できます。Apple ホームの「おやすみ」シーンやオートメーションと連携でき、DND 解除時には保留されていた通知を AI が要約してお知らせします。
- **🚨 防災・気象連動トリガーセンサー**: 緊急地震速報（EEW）、気象警報、雨雲接近アラームを仮想モーションセンサーとして公開。Apple ホームのオートメーションの「トリガー」として利用でき、警報発令時に避難経路の照明を全点灯させたり、電気ストーブのスマートプラグ遮断、電動雨戸の閉扉などを自動発火できます。
- **🔊 個別スピーカー音量スライダー**: 各部屋のスピーカー音量を HomeKit のスライダーや Siri からパーセント指定（例:「リビングの音量を50%にして」）で調整できます。
- **ゼロ依存（Zero Dependencies）**: ネイティブ Fetch を採用しており、外部の追加パッケージに依存せず、軽量かつシンプルに動作します。
- **Homebridge Config UI X 対応**: ブラウザ上のグラフィカルな設定画面から手軽にセットアップしていただけます（日英併記対応）。

### 📦 インストール方法

#### 方法 1: Homebridge Config UI X から（推奨）
1. Homebridge の管理画面を開きます。
2. 「プラグイン」タブで `homebridge-voicehub` を検索します。
3. 「インストール」をクリックします。

#### 方法 2: コマンドラインから
```bash
npm install -g homebridge-voicehub
```
*(Bun をご利用の場合は `bun add -g homebridge-voicehub` でもインストール可能です)*

### ⚙️ 設定方法

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

#### 設定パラメータ一覧

| パラメータ | 必須 | デフォルト値 | 説明 |
| :--- | :---: | :--- | :--- |
| `platform` | ○ | `VoiceHubPlatform` | プラットフォーム名（固定） |
| `name` | ○ | `VoiceHub` | ホームアプリ上での表示名 |
| `host` | ○ | `http://127.0.0.1:8080` | VoiceHub サーバーの URL |
| `webhookToken` | - | `""` | VoiceHub でトークン認証を有効化している場合に設定 |
| `enableDndSwitch` | - | `true` | 会議・おやすみモード（DND）切替スイッチを作成 |
| `enableDisasterSensors` | - | `true` | 緊急地震速報・気象警報・雨雲接近をオートメーション用仮想モーションセンサーとして公開 |
| `autoDiscoverSpeakers` | - | `true` | VoiceHub に登録されたスピーカーの自動検出とアクセサリ登録 |
| `discoverGoogleHome` | - | `true` | Google Home / Nest スピーカーの登録有効化 |
| `discoverAlexa` | - | `true` | Amazon Alexa / Echo スピーカーの登録有効化 |
| `discoverHomepod` | - | `true` | Apple HomePod スピーカーの登録有効化 |
| `discoverOnvif` | - | `true` | ONVIF カメラ・スピーカー (Tapo含む) の登録有効化 |
| `discoverDlna` | - | `true` | DLNA / UPnP スピーカーの登録有効化 |
| `volumeAsLightbulb` | - | `true` | 音量を照明タイル（明度スライダー）として直感的に操作可能にする |
| `pollInterval` | - | `30` | DND および防災トリガー状態の同期インターバル（秒） |
| `presets` | - | `[...]` | プリセット発話スイッチの配列 |

### 🗣️ Siri 音声操作・オートメーション活用例

#### 1. Siri からの一言アナウンス
- *「Hey Siri, ご飯できたよ をつけて」*
  → 家中のスピーカーから「ご飯ができました。リビングに集まってください」とアナウンスされ、スイッチは自動で OFF に戻ります。
- *「Hey Siri, 会議モード をつけて」*
  → DND が有効になり、家族のスピーカー通知が自動で保留されます。

#### 2. Apple HomeKit オートメーション連動
- **人感センサー反応時**: 玄関の人感センサーが反応したら、VoiceHub の特定プリセット「おかえりなさい」をトリガー。
- **シーン連動**: 「おやすみ」シーン実行時に DND スイッチを ON にし、朝の「おはよう」シーンで OFF にして保留通知の AI 要約を再生。
- **防災連動オートメーション**: 緊急地震速報（EEW）センサーが反応した際に、廊下やリビングの照明を最大輝度で点灯させ、高熱家電のスマートプラグ電源を緊急遮断。


### 🛠️ 開発・ビルド

```bash
git clone https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub.git
cd SmartHomeSpeaker-VoiceHub/plugins/homebridge-voicehub
npm install
npm run build
npm link
```

---

## 📄 License / ライセンス

Apache License 2.0
