# Smart Speaker Voice Hub 🎙️

**日本語** | [English](README-en.md) | [📖 取扱説明書・総合仕様書 (MANUAL.md)](MANUAL.md)

Google Home / Nest、Amazon Alexa (Echo)、Apple HomePod、ONVIF ネットワークカメラ、DLNA ネットワークオーディオなど、規格の異なる家庭内のスピーカー機器をまとめて、WebhookやAI、外部APIから自然な日本語音声（Edge-TTS）でお知らせを放送できる音声ハブです。

日常のちょっとしたお知らせやリマインダーを、手軽に心地よく届けることを目指して作成された主に自分用のツールです。

> [!TIP]
> 📖 **詳しい使い方・初期設定・接続手順をお探しですか？**  
> スピーカー別の登録手順（Google Cast / Alexa / HomePod / ONVIFカメラ / DLNA）、各種AI連携、HomeKit/Siri設定、MCPサーバー設定、および全 REST API リファレンスについては、**[総合取扱説明書・技術仕様書 (MANUAL.md)](MANUAL.md)** にすべて体系的にまとめています！あわせてご活用ください。

---

## 🌿 主な特徴

- **いろいろなスピーカーへまとめて発声**:
  Google Home (Nest)、Amazon Alexa (Echo)、Apple HomePod、ONVIF 対応ネットワークカメラ、DLNA / UPnP 対応オーディオ機器へ、個別に、または家中で一斉にアナウンスを再生できます。
- **手軽な音声合成 & 多彩なエンジン拡張**:
  コミュニティ製ライブラリを活用した手軽な Edge-TTS に加え、公式の Azure Speech Service、Google Cloud TTS、ローカルで完結する VOICEVOX / SHAREVOX / COEIROINK などを自由に追加・多段フォールバック連携できます。
  *(※ Edge-TTS はコミュニティ製ライブラリを利用した試行的な機能であり、商用保証のある公式 Azure Speech Service とは異なり、将来的な仕様変更等を受ける可能性があります)*
- **直感的な Web 画面とリアルタイム操作**:
  スマートフォンやパソコンのブラウザからメッセージを入力するだけで、その場ですぐにアナウンスを送信できます。発言前の試聴プレビュー、送信元別（雨アラーム・防災速報等）の発言履歴フィルターや再発話、気象庁公式配色凡例付きの雨雲レーダー重ね合わせマップも備えています。
- **未来の発声予約（タイマー・リマインダー発声）**:
  「+10分後にリマインド」「19:30にお風呂のおしらせ」など、指定時刻（`at` / `time`）に合わせたタイマー予約発声に対応。Web 画面、Webhook、MQTT、MCP のいずれからでも柔軟に指定できます。
- **毎日の定期放送 & カレンダー連携**:
  「朝の挨拶」や「ゴミ出しリマインダー」などの定時スケジュール放送に加え、Google カレンダーと連携して予定の直前リマインドや朝の予定まとめアナウンスを自動で行えます。
- **おやすみ・会議モード (DND) & リアルタイム自動連動**:
  就寝時や在宅勤務のオンライン会議中など、静かに過ごしたい時間帯には自動でアナウンスを控えたり、会議終了後にまとめてお知らせする（AIによる要約読み上げにも対応）といった配慮が可能です。SSE (Server-Sent Events) によるリアルタイム同期を搭載し、Apple HomeKit や外部スクリプト（Logitech G HUB / Stream Deck）からミュート操作を行った際も、Web UI 画面のリロード不要で即座にボタン表示が連動します。
- **Apple HomeKit / Siri 連携**:
  同梱の専用プラグイン（`homebridge-voicehub`）を導入いただくことで、Apple の「ホーム」アプリや Siri から「『ご飯できたよ』をつけて」と話しかけるだけで、指定の部屋や家中のスピーカーから一言アナウンスを流すことができます。
- **スマート防災連動（緊急地震速報・気象警報・雨雲接近）**:
  日本の気象庁（JMA）および P2P 地震速報のオープンな防災情報と連動し、緊急地震速報や大雨警報、雨雲の接近・雨上がりをスピーカーから自動アナウンスします。さらに、これらの警報状態を Apple HomeKit（仮想人感センサー）や Home Assistant（MQTT Binary Sensor）のオートメーション「トリガー」として公開できるため、警報発令時に避難経路のスマート照明を全点灯させたり、暖房器具のスマートプラグを自動遮断するなどのスマートホーム防災連動を柔軟に構築できます。*(※ 本機能は日本国内の気象・地震情報APIを利用するため、日本国内専用となります)*
- **手軽な外部連携 (Webhook / MQTT / MCP サーバー)**:
  IFTTT、Home Assistant (MQTT Discovery 対応)、Node-RED などの自動化ツールに加え、Claude Desktop や Cursor 等の AI アシスタントから直接スピーカーを操作できる MCP (Model Context Protocol) サーバーとしても機能します。


---

## 🚀 はじめかた

最も手軽でおすすめなのは、Docker Compose を利用した起動です。[Docker Hub (madpiero/smarthomespeaker-voicehub)](https://hub.docker.com/r/madpiero/smarthomespeaker-voicehub) に公開されている公式マルチアーキテクチャイメージ（amd64 / arm64 対応）により、Raspberry Pi や NAS、PC でもコンパイル待ちなしで即座に起動できます。

### 方法 A: 一般ユーザー向け（最も簡単・リポジトリの clone 不要）

適当な作業ディレクトリを作成し、`docker-compose.yml` をダウンロードして起動するだけです。

```bash
# 1. 作業ディレクトリの作成
mkdir -p voicehub && cd voicehub

# 2. docker-compose.yml のダウンロード
curl -O https://raw.githubusercontent.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/main/docker-compose.yml

# 3. コンテナの起動（Docker Hub から自動 pull して即起動）
docker compose up -d
```

### 方法 B: 開発者向け（ソースコードを変更・開発したい場合）

リポジトリをクローンして起動すると、自動的にローカルビルドとソースコードのバインドマウントが適用され、コードのホットリロード開発が行えます。

```bash
git clone https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub.git
cd SmartHomeSpeaker-VoiceHub
docker compose up -d --build
```

---

起動が完了したら、ブラウザから以下の URL にアクセスしてください。

```text
http://<サーバーのIPアドレス>:8080
```
*(サーバーを動かしている端末自身で開く場合は `http://localhost:8080`)*

> 💡 **起動後の初期設定・スピーカー登録について**  
> 初回アクセス後は、画面の案内に従ってスピーカーの自動検出や登録を行います。  
> Google Home / Nest 以外の機器（Amazon Echo、Apple HomePod、Tapo等の防犯カメラ、DLNAスピーカー）の詳しい接続手順や設定例は、**[取扱説明書 (MANUAL.md) - 各種スマートスピーカーの接続仕様](MANUAL.md#8-各種スマートスピーカー音響機器の接続仕様)** をご覧ください。

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

## 📖 取扱説明書・総合技術仕様 (MANUAL.md)

本システムは、ご家庭のスマートホーム環境に合わせて細かくカスタマイズできるよう、多様な設定項目や連携機能を備えています。  
より詳しい設定手順や仕様については、**[総合技術仕様書・取扱説明書 (MANUAL.md)](MANUAL.md)** をご覧ください。

- **[各種スピーカーの接続仕様 (MANUAL.md 第8章)](MANUAL.md#8-各種スマートスピーカー音響機器の接続仕様)**:
  Amazon Echo（Atnr/トークン取得手順）、Apple HomePod（AirPlay2/認証）、ONVIF防犯カメラ（Tapo等の双方向音声）、DLNAネットワークオーディオ
- **[外部音声合成エンジンの自由追加 (MANUAL.md 第4.5節)](MANUAL.md#45-外部音声エンジン自由追加アーキテクチャ-tts-engine-extensibility)**:
  Azure Speech Service、Google Cloud TTS、VOICEVOX、SHAREVOX、COEIROINK の追加・多段フォールバック設定
- **[Apple HomeKit / Homebridge プラグイン (MANUAL.md 第9章)](MANUAL.md#9-apple-homekit--homebridge-プラグイン仕様-homebridge-voicehub)**:
  Siri 音声アナウンス、ホームアプリスイッチ設定、音量スライダー、DND連動
- **[スマート防災・気象連動トリガー (MANUAL.md 第6章)](MANUAL.md#6-緊急速報防災情報および天気予報連携仕様)**:
  緊急地震速報 (EEW)・気象警報・雨雲接近の自動アナウンスおよび HomeKit / MQTT 自動化トリガー
- **[MCP (Model Context Protocol) サーバー設定 (MANUAL.md 第10章)](MANUAL.md#10-mcp-model-context-protocol-サーバー仕様)**:
  Claude Desktop、Cursor、Cline 等の AI アシスタントからの直接音声発話・スピーカー操作設定
- **[マルチ MQTT ブローカー連携 (MANUAL.md 第11章)](MANUAL.md#11-マルチ-mqtt-ブローカー連携仕様)**:
  複数ブローカー同時接続、Home Assistant MQTT Discovery 自動登録、トピック購読発話
- **[全 REST API リファレンス (MANUAL.md 第12章)](MANUAL.md#12-全-rest-api-仕様リファレンス)**:
  `/api/say`、`/api/devices`、`/api/dnd`、`/api/disaster` 等の全エンドポイント一覧とパラメータ詳細
- **[セキュリティ・アクセス制御設計 (MANUAL.md 第2章)](MANUAL.md#2-ネットワークアクセス制御およびセキュリティ設計)**:
  LAN内 vs Cloudflare Tunnel の境界防御、Webhook トークン認証、管理者パスワード保護

---

## 🤝 コミュニティと開発への参加

バグ報告、新機能の提案、ドキュメントの改善、プルリクエストを心よりお待ちしております！

- **質問・アイデアの相談**: お気軽に **[GitHub Discussions](https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/discussions)** へお寄せください。
- **コントリビューション方針**: 開発環境のセットアップやコーディング規約については、**[コントリビューションガイド (CONTRIBUTING.md)](CONTRIBUTING.md)** をご覧ください。
- **行動規範**: コミュニティ内での対話や貢献にあたっては、**[行動規範 (CODE_OF_CONDUCT.md)](CODE_OF_CONDUCT.md)** の遵守をお願いいたします。
- **セキュリティの報告**: 脆弱性のご報告は公開 Issue ではなく、**[セキュリティポリシー (SECURITY.md)](SECURITY.md)** の案内に沿って非公開でご連絡をお願いいたします。

---

## 📜 ライセンスと謝辞

本プロジェクトは **[MIT License](LICENSE)** のもとで公開されています。
本ソフトウェアが利用・参照しているオープンソースソフトウェアのライセンスおよび詳細な著作権表記については、**[サードパーティライセンス一覧 (THIRD_PARTY_LICENSES.md)](THIRD_PARTY_LICENSES.md)** をご覧ください。

### 心より感謝申し上げます
本ソフトウェアの開発にあたり、スマートホームおよび音声合成の分野で貴重な知見やオープンソースライブラリを公開してくださっている開発者・コミュニティの皆様に深く敬意を表します。

- **[google-home-voicetext](https://github.com/sikkimtemi/google-home-voicetext-docker)** (Taro TAKAHASHI 様) - スマートスピーカー音声通知の素晴らしい着想
- **[edge-tts](https://github.com/rany2/edge-tts)** - 自然な日本語音声を届けてくれる音声合成ライブラリ
- **[PyChromecast](https://github.com/home-assistant-libs/pychromecast)** - Google Cast デバイスとの安定した通信基盤
- **[pyatv](https://github.com/postlund/pyatv)** - Apple HomePod への AirPlay ストリーミング基盤
- **[alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control)** - Amazon Echo コントロールの知見
- **[go2rtc](https://github.com/AlexxIT/go2rtc)** - ネットワークカメラへの双方向音声ストリーミング
- **[aiomqtt](https://github.com/sbtinstruments/aiomqtt)** - 非同期 MQTT 通信基盤


