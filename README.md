# Smart Home Speaker Voice Hub 🎙️

Google Home / Nest、Amazon Alexa (Echo)、Apple HomePod、ONVIF ネットワークカメラ、DLNA ネットワークオーディオなど、規格の異なる家庭内のスピーカー機器をまとめて、WebhookやAI、外部APIから自然な日本語音声（Edge-TTS）でお知らせを放送できる音声ハブです。

日常のちょっとしたお知らせやリマインダーを、手軽に心地よく届けることを目指して作成された主に自分用のツールです。

> [!NOTE]
> 本ソフトウェアは、個人の家庭内での利用を想定し、AIの支援を受けながら開発したオープンソースプロジェクトです。
> 細かい技術仕様、全 REST API リファレンス、ネットワークセキュリティ設計、高度な外部連携設定等については、**[詳細仕様書 (Manual.md)](Manual.md)** にすべて記載しておりますので、あわせてご参照ください。

---

## 🌿 主な特徴

- **いろいろなスピーカーへまとめて発声**:
  Google Home (Nest)、Amazon Alexa (Echo)、Apple HomePod、ONVIF 対応ネットワークカメラ、DLNA / UPnP 対応オーディオ機器へ、個別に、または家中で一斉にアナウンスを再生できます。
- **手軽な音声合成 & 多彩なエンジン拡張**:
  コミュニティ製ライブラリを活用した手軽な Edge-TTS に加え、公式の Azure Speech Service、Google Cloud TTS、ローカルで完結する VOICEVOX / SHAREVOX / COEIROINK などを自由に追加・多段フォールバック連携できます。
  *(※ Edge-TTS はコミュニティ製ライブラリを利用した試行的な機能であり、商用保証のある公式 Azure Speech Service とは異なり、将来的な仕様変更等を受ける可能性があります)*
- **直感的な Web 画面とリアルタイム操作**:
  スマートフォンやパソコンのブラウザからメッセージを入力するだけで、その場ですぐにアナウンスを送信できます。発言前の試聴プレビューや、過去の発言履歴からの再発話も可能です。
- **未来の発声予約（タイマー・リマインダー発声）**:
  「+10分後にリマインド」「19:30にお風呂のおしらせ」など、指定時刻（`at` / `time`）に合わせたタイマー予約発声に対応。Web 画面、Webhook、MQTT、MCP のいずれからでも柔軟に指定できます。
- **毎日の定期放送 & カレンダー連携**:
  「朝の挨拶」や「ゴミ出しリマインダー」などの定時スケジュール放送に加え、Google カレンダーと連携して予定の直前リマインドや朝の予定まとめアナウンスを自動で行えます。
- **おやすみ・会議モード (DND)**:
  就寝時や在宅勤務のオンライン会議中など、静かに過ごしたい時間帯には自動でアナウンスを控えたり、会議終了後にまとめてお知らせする（AIによる要約読み上げにも対応）といった配慮が可能です。
- **Apple HomeKit / Siri 連携**:
  同梱の専用プラグイン（`homebridge-voicehub`）を導入いただくことで、Apple の「ホーム」アプリや Siri から「『ご飯できたよ』をつけて」と話しかけるだけで、指定の部屋や家中のスピーカーから一言アナウンスを流すことができます。
- **手軽な外部連携 (Webhook / MQTT / MCP サーバー)**:
  IFTTT、Home Assistant (MQTT Discovery 対応)、Node-RED などの自動化ツールに加え、Claude Desktop や Cursor 等の AI アシスタントから直接スピーカーを操作できる MCP (Model Context Protocol) サーバーとしても機能します。

---

## 🚀 はじめかた

最も手軽でおすすめなのは、Docker Compose を利用した起動です。

### 1. 準備するもの
- Docker および Docker Compose が動作する環境（PC、Raspberry Pi、NAS、自宅サーバー等）
- スピーカー機器と同じ家庭内ネットワーク (LAN) への接続

### 2. 設定ファイルの作成
サンプル設定ファイルをコピーして、設定用のファイルを作成します。

```bash
cp .my.env.sample .my.env
```

※ 通常は初期設定のままでも起動いただけます。必要に応じてポート番号やスピーカーのIPアドレス等を編集してください。

### 3. 起動
Docker Compose コマンドでバックエンドサーバーを起動します。

```bash
docker compose up -d --build
```

起動が完了したら、ブラウザから以下の URL にアクセスしてください。

```text
http://<サーバーのIPアドレス>:8080
```
*(サーバーを動かしている端末自身で開く場合は `http://localhost:8080`)*

---

## 💡 基本的な使い方

### 1. Web 画面からアナウンスする
ブラウザで Web 画面を開き、メッセージ入力欄にテキストを入力して「喋らせる」ボタンを押すだけで、登録されたスピーカーから音声が流れます。
画面上の「試聴」ボタンを押すと、スピーカーへ送信する前にブラウザ上だけで音声をテスト再生できます。

### 2. 外部から呼び出す (Webhook の例)
シェルスクリプトや自動化ツールから、以下のような簡単な cURL コマンドでアナウンスを実行できます。

```bash
curl -X POST http://<サーバーIP>:8080/api/say \
  -H "Content-Type: application/json" \
  -d '{
    "text": "ご飯ができましたよ",
    "devices": ["ALL"]
  }'
```

タイマー予約発声を行う場合は、`"at": "+10m"`（10分後）や `"at": "19:30"`（指定時刻）を追加するだけで自動的にスケジュールされます。

```bash
# 10分後にリマインドを発声する例
curl -X POST http://<サーバーIP>:8080/api/say \
  -H "Content-Type: application/json" \
  -d '{
    "text": "お風呂が沸いてから10分経過しました",
    "devices": ["ALL"],
    "at": "+10m"
  }'
```

※ Web 画面の「Webhook & Tunnel」メニュー内に、クリック操作だけで呼び出しコマンドを自動生成できる「Webhook コマンドビルダー」も用意されています。発声時刻のクイックチップ（+5分後、+10分後等）からも手軽に試せます。

### 3. Siri や Apple ホームアプリから使う (Homebridge プラグイン)
Homebridge をご利用のご家庭向けに、本システム専用のプラグイン **`homebridge-voicehub`** を同梱しています。
- 「ご飯できたよ」「お風呂が沸いたよ」といった定型メッセージを Apple ホームアプリのスイッチとして登録し、Siri から音声で呼び出せます。
- 家中のスピーカー音量を iPhone のスライダーで調整したり、おやすみモード（DND）を Apple の就寝シーンと連動させることができます。

プラグインの詳しい導入方法については、[プラグイン解説書 (plugins/homebridge-voicehub/README.md)](plugins/homebridge-voicehub/README.md) をご覧ください。

---

## 📖 より詳しい情報・技術仕様について

本システムは、ご家庭の環境に合わせて細かくカスタマイズできるよう、多様な設定項目や連携機能を備えています。

- **Amazon Echo / Apple HomePod / ネットワークカメラ / DLNA の詳しい連携設定**
- **MCP (Model Context Protocol) サーバーとして AI アシスタントから操作する設定**
- **マルチ MQTT ブローカー接続および Home Assistant MQTT Discovery 仕様**
- **すべての REST API エンドポイント一覧とパラメータ詳細**
- **内部アーキテクチャ、セキュリティ設計、およびデータ永続化仕様**

これらすべての詳細については、**[詳細技術仕様書 (Manual.md)](Manual.md)** に体系的にまとめております。必要に応じてご参照ください。

---

## 📜 ライセンスと謝辞

本プロジェクトは **MIT License** のもとで公開されています。

### 心より感謝申し上げます
本ソフトウェアの開発にあたり、スマートホームおよび音声合成の分野で貴重な知見やオープンソースライブラリを公開してくださっている開発者・コミュニティの皆様に深く敬意を表します。

- **[google-home-voicetext](https://github.com/sikkimtemi/google-home-voicetext-docker)** (Taro TAKAHASHI 様) - スマートスピーカー音声通知の素晴らしい着想
- **[edge-tts](https://github.com/rany2/edge-tts)** - 自然な日本語音声を届けてくれる音声合成ライブラリ
- **[PyChromecast](https://github.com/home-assistant-libs/pychromecast)** - Google Cast デバイスとの安定した通信基盤
- **[pyatv](https://github.com/postlund/pyatv)** - Apple HomePod への AirPlay ストリーミング基盤
- **[alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control)** - Amazon Echo コントロールの知見
- **[go2rtc](https://github.com/AlexxIT/go2rtc)** - ネットワークカメラへの双方向音声ストリーミング
- **[aiomqtt](https://github.com/sbtinstruments/aiomqtt)** - 非同期 MQTT 通信基盤
