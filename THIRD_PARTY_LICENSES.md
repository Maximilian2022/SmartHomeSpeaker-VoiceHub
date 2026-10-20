# サードパーティライセンス一覧 (Third-Party Licenses)

本プロジェクト「Smart Home Speaker Voice Hub」は [MIT License](LICENSE) のもとで公開されていますが、以下のオープンソースソフトウェア、外部ライブラリ、およびツールを利用または参照しています。

それぞれの開発者およびコミュニティの皆様に心より感謝申し上げます。

---

## 1. Python 依存ライブラリ (`requirements.txt`)

| パッケージ名 | ライセンス | 著作権 / プロジェクト |
|---|---|---|
| **FastAPI** | MIT License | © Sebastián Ramírez ([tiangolo/fastapi](https://github.com/tiangolo/fastapi)) |
| **Uvicorn** | BSD 3-Clause | © Encode OSS Ltd. ([encode/uvicorn](https://github.com/encode/uvicorn)) |
| **Pydantic / Pydantic Settings** | MIT License | © Samuel Colvin / Pydantic Services Inc. ([pydantic/pydantic](https://github.com/pydantic/pydantic)) |
| **PyChromecast** | MIT License | © Paulus Schoutsen & Home Assistant Community ([home-assistant-libs/pychromecast](https://github.com/home-assistant-libs/pychromecast)) |
| **pyatv** | MIT License | © Pierre Ståhl ([postlund/pyatv](https://github.com/postlund/pyatv)) |
| **HTTPX** | BSD 3-Clause | © Encode OSS Ltd. ([encode/httpx](https://github.com/encode/httpx)) |
| **aiohttp** | Apache License 2.0 | © aiohttp contributors ([aio-libs/aiohttp](https://github.com/aio-libs/aiohttp)) |
| **python-multipart** | Apache License 2.0 | © Andrew Chen Wang & multipart contributors ([Kludex/python-multipart](https://github.com/Kludex/python-multipart)) |
| **icalendar** | BSD 2-Clause | © Max M / icalendar contributors ([collective/icalendar](https://github.com/collective/icalendar)) |
| **paho-mqtt** | EPL-2.0 / EDL-1.0 (BSD) | © Eclipse Foundation ([eclipse-paho/paho.mqtt.python](https://github.com/eclipse-paho/paho.mqtt.python)) |
| **aiomqtt** | BSD 3-Clause | © Felix Schwerter / SBT Instruments ([sbtinstruments/aiomqtt](https://github.com/sbtinstruments/aiomqtt)) |
| **edge-tts** | **GNU LGPL v3.0** | © rany2 ([rany2/edge-tts](https://github.com/rany2/edge-tts)) |
| **recurring-ical-events** | **GNU LGPL v3.0 or later** | © Nicco Kunzmann ([niccokunzmann/python-recurring-ical-events](https://github.com/niccokunzmann/python-recurring-ical-events)) |

> [!NOTE]
> ### LGPL v3.0 ライセンスのライブラリ（`edge-tts`, `recurring-ical-events`）について
> - 本プロジェクトは、これらのライブラリを改変することなく、Python の標準的なパッケージ管理（`requirements.txt` / `pip`）を通じて外部依存ライブラリとしてそのままインポート（動的利用）しています。
> - 本プロジェクト独自のソースコードは LGPL の派生物ではなく独立した著作物であるため、本プロジェクト全体は **MIT License** で提供されています。
> - 利用者は Python の実行環境において、同等または互換性のある改変版ライブラリへ自由に差し替えて実行することが可能です。

---

## 2. 同梱ツール・外部スクリプト

### `bin/alexa_remote_control.sh`
- **作成者**: Alexander Noack, Thorsten Gehrig, およびコミュニティコントリビューター
- **ライセンス**: Apache License 2.0
- **リポジトリ**: [thorsten-gehrig/alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control)
- **概要**: Amazon Echo へのリモートコマンド送信スクリプト。原著作者のクレジットおよびライセンスヘッダーをファイル内に保持しています。

### `go2rtc` (Docker 内同梱バイナリ)
- **作成者**: AlexxIT
- **ライセンス**: MIT License
- **リポジトリ**: [AlexxIT/go2rtc](https://github.com/AlexxIT/go2rtc)
- **概要**: ネットワークカメラへの双方向音声ストリーミングおよび WebRTC/RTSP 配信エンジン。

---

## 3. 同梱プラグイン

### `plugins/homebridge-voicehub`
- **作成者**: Maximilian2022
- **ライセンス**: Apache License 2.0
- **概要**: Homebridge 環境で Smart Home Speaker Voice Hub を Apple HomeKit と連携させるための専用プラグインです。プラグイン単体の詳細ライセンス条項は [plugins/homebridge-voicehub/LICENSE](plugins/homebridge-voicehub/LICENSE) をご参照ください。

---

## 4. 着想元プロジェクト (Inspiration)

### `sikkimtemi/google-home-voicetext-docker`
- **原案者**: Taro TAKAHASHI 様
- **リポジトリ**: [sikkimtemi/google-home-voicetext-docker](https://github.com/sikkimtemi/google-home-voicetext-docker)
- **概要**: スマートスピーカーへの音声通知という素晴らしい着想を与えてくださった元祖プロジェクトです。現在の Voice Hub は全機能を Python (FastAPI) で全面新規設計・スクラッチ実装した独立プロジェクトですが、アイデアの源流として深く感謝申し上げます。
