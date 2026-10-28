# 変更履歴 (Changelog)

すべての重要な変更はこのファイルに記録されます。
フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づいています。

## [1.0.14] - 2026-10-28

### 追加・新機能 (Added)
- **PC スピーカーのマルチオーディオ出力デバイス個別検出・ON/OFF・メイン出力指定 (`clients/speaker/voicehub_speaker.py`, `app/services/client_speaker_service.py`, `app/routers/client_speakers.py`, `app/services/speech_service.py`)**:
  - 1台の PC に複数の物理スピーカー（`Logicool G560`、モニター内蔵スピーカー等）や仮想オーディオデバイス（`SteelSeries Sonar` 等）が接続されている場合、全再生デバイスを自動列挙して VoiceHub に個別登録する機能を追加。
  - Web GUI の「💻 PC スピーカー連携」カード内に **「🔊 接続中 PC の出力スピーカー管理」** パネルを新設し、出力デバイスごとの **有効/無効 (ON/OFF)** トグル、**「⭐ メインに設定」** ラジオボタン、および単体テスト発声ボタン（`🔊 テスト`）を実装。
  - `ALL`（家中一斉）や `PC:ALL`、PC名単体指定時は、複数スピーカーが同時に鳴らないよう各 PC の「⭐ メイン出力」1台のみで再生し、個別指定時は有効な任意の出力デバイスをピンポイントで鳴らせるよう改善。
- **クライアントスクリプトの自動自己更新 (Auto Self-Update) (`clients/speaker/voicehub_speaker.py`, `app/routers/client_speakers.py`)**:
  - SSE 接続時（`connected` イベント）および Web GUI からの再スキャン指示時（`self_update` イベント）にサーバー上の `voicehub_speaker.py` の SHA-256 ハッシュ (`scriptHash`) を照合。更新があれば自動ダウンロードして `~/.voicehub/voicehub_speaker.py` をアトミック更新し、プロセスを自動再起動する機構を実装。
- **OS別ワンライナー3種への拡充とサーバー直接配信 (`public/index.html`, `public/app.js`, `app/main.py`)**:
  - Windows / macOS / Linux の各タブに **①一時起動（テスト実行）、②自動起動（常駐化・バックグラウンド起動）、③自動起動の解除（常駐停止）** の3種類のワンライナーを整備。
  - VoiceHub サーバー自身（`/clients/speaker/`）からクライアントスクリプトを直接配信し、Windows でも `--autostart enable` 実行と同時に `wscript.exe //B` で黒い画面を出さずに即時バックグラウンド常駐を開始するよう改善。

### 修正・堅牢化 (Fixed / Reliability)
- **PCスピーカー連携カードの i18n 翻訳キー補完とキャッシュバスター更新 (`public/locales/ja.json`, `public/locales/en.json`, `public/index.html`, `public/i18n.js`)**:
  - `settingsIntegrations.pcSpeakerHeader` / `pcSpeakerSub` をはじめとする全翻訳キーを日英辞書に追加し、`{SERVER_URL}` の3段階置換により未置換エラーを完全防止。
- **管理者ブラウザセッションのレート制限ロックアウト巻き込み防止 (`app/core/security.py`, `app/services/speech_service.py`)**:
  - 同一 PC 上の外部スクリプトが認証エラーを起こした際でも、静的 Web UI アセットや認証済みブラウザセッション（`auth_token` Cookie）が 429 ロックアウトに巻き込まれないよう認証評価順序を改善。
  - Web UI からの直接テスト発言（`web_ui` / `quick_test`）を30秒重複スキップ（Deduplication）の対象外とし、連続テスト発声が行えるよう改善。
- **Watchtower 稼働ヘルスチェック時の意図せぬコンテナ更新トリガー防止 (`app/services/update_service.py`, `tests/test_update_service.py`, `tests/test_sse_events.py`)**:
  - Watchtower の `/v1/update` エンドポイントは `GET` リクエストであっても有効な Bearer トークンを付与すると即座にコンテナ更新を開始する仕様であるため、`check_watchtower_health()` ではトークンを付与せずステータスコード（`401` 等）の応答のみで安全に生存確認を行うよう修正。
  - 単体テスト実行時間帯（DND 定時スケジュール時間内）に依存しないよう `test_sse_events.py` のテスト環境分離を強化。
- **仕様書・取扱説明書の最新化 (`MANUAL.md`, `MANUAL-en.md`, `clients/speaker/README.md`)**:
  - マルチ出力管理、メイン出力解決アルゴリズム、クライアント自動自己更新、新規 API エンドポイント（`/api/client-speakers/config`, `/outputs`, `/rescan`）を日英マニュアルへ反映。

## [1.0.13] - 2026-10-28

### 追加・新機能 (Added)
- **PC スピーカークライアント連携 (Windows / Mac / Linux) (`clients/speaker/`, `app/services/client_speaker_service.py`, `app/routers/client_speakers.py`)**:
  - Windows / macOS / Linux PC を VoiceHub のアナウンス受話スピーカーとして利用できる常駐型超軽量クライアントを新設。
  - 常駐待機時メモリ約 15MB・CPU 0% の省フットプリント設計。OS ネイティブの最適再生エンジン（macOS は標準 `afplay`、Windows は `miniaudio` / PowerShell、Linux は `paplay` / `mpv` / `aplay` / `miniaudio`）を自動選択。
  - **Zero-Setup (Python 手動インストール不要)**: Astral `uv` の自動ブートストラップ機構を内蔵し、Python 未導入のクリーンな PC でも `run.bat` や `run.sh`、または Web GUI のワンライナーコマンドを実行するだけで自動セットアップ＆即時起動。
  - **完全画面非表示スタートアップ常駐**: Windows では黒いコマンドプロンプト画面を出さないバックグラウンド常駐用 VBScript を自動生成。macOS（LaunchAgents）や Linux（systemd --user）の自動起動にも対応。
  - **マクロ・ターゲット指定対応**: 全台発話マクロ `ALL` / `*` に自動統合されたほか、`PC:ALL` / `CLIENT:ALL` / `WIN:ALL` / `MAC:ALL` マクロおよび `client:<ID>` ターゲット指定に対応。
- **Web GUI スマートホーム連携タブへの PC スピーカー設定カード新設 (`public/index.html`, `public/app.js`, `public/locales/ja.json`, `public/locales/en.json`)**:
  - 「拡張・システム設定」>「スマートホーム連携」に「💻 PC スピーカー連携 (Windows / Mac / Linux)」セクションを新設。
  - 閲覧中の VoiceHub サーバー URL（`window.location.origin`）を動的に埋め込んだワンライナー実行コマンドを Windows (PowerShell) / Mac / Linux それぞれに自動生成し、ワンクリックでコピー可能。
  - 接続中の PC 台数リアルタイムステータスバッジ、スピーカー選択チップおよびデバイス一覧への PC アイコン（💻/🍎/🪟/🐧）表示。
- **PC スピーカー機能の単体テスト追加 (`tests/test_client_speaker.py`)**:
  - SSE ストリーム接続、クライアント登録・自動切断、キュー配信、宛先マクロ解決の検証を含む単体テストスイートを追加（全107件 PASS）。
- **仕様書・取扱説明書の最新化 (`MANUAL.md`, `MANUAL-en.md`)**:
  - PC スピーカークライアントの通信仕様（SSE）、常駐仕様、宛先マクロ、REST API（`GET /api/client-speakers/stream`, `GET /api/client-speakers`）を完全網羅。

## [1.0.12] - 2026-10-26

### 追加・新機能 (Added)
- **送信失敗時の自動フォールバック先オプション選択 (`public/index.html`, `public/app.js`, `app/services/speech_service.py`)**:
  - WebUI の防災・気象設定カード内に「🔄 送信失敗時の自動フォールバック先」セレクトボックスを新設。
  - 「自動 (推奨: Group > 単体, GH > Alexa > HP > DLNA > ONVIF)」「標準スピーカーのみ」「フォールバックしない (無効)」「個別スピーカー/グループ」からユーザーが柔軟に選択可能に。
  - 自動フォールバック時の厳格な優先順位階層（階層1: Group > 単体、階層2: GH > Alexa > HP > DLNA > ONVIF）を実装。屋外カメラ等の外部機器しかない環境でも確実に鳴らしつつ、屋内スピーカーがある環境では外部機器を巻き込まない安全設計。
- **GitHub Actions による完全日本語自動リリースパイプライン (`.github/workflows/docker-publish.yml`, `scripts/extract_release_notes.py`)**:
  - `main` ブランチ push 時に Docker イメージ作成と連動し、`logs/remediation_history.md` から詳細な変更履歴を自動抽出して完全日本語の GitHub Release を自動公開・更新するパイプラインを新設。
  - Docker Hub 上にも `latest` と `v1.0.12` / `1.0.12` タグを自動付与。

### 修正・堅牢化 (Fixed / Reliability)
- **Google Cast グループ接続のフェイルファスト化と切断キャッシュ破棄 (`app/services/cast_service.py`)**:
  - キャストグループ接続タイムアウトを 3.0 秒に短縮し、不通時の遅延を大幅軽減。
  - 切断時・再生失敗時に `purge_cache(host, port)` で古いソケットキャッシュを確実に破棄し、次回の接続固着を解消。
- **リトライ＆2段階フォールバックの強化 (`app/services/speech_service.py`)**:
  - キャストグループ宛ては最大2回試行（mDNS再解決）。2回失敗時は紐付けられた個別 Google Cast スピーカー群（`_fallback_members`）へ自動フォールバック。
  - 個別スピーカー宛ては DHCP や一時的な瞬断を考慮し最大3回試行。失敗毎に IP/ポートを再解決。3回失敗した場合は全体フォールバック先へ。
  - 宛先重複排除（`resolve_targets`）で同一IPを持つ親端末とグループ（別ポート）が衝突して消えないようキーを改善。
- **防災スピーカー選択消失バグの修正 (`public/app.js`)**:
  - 画面再描画時に現在のチェック状態を引き継ぎ、空リストで初期化されて `targets: ["ALL"]` として保存される問題を完全防止。
- **震度速報(ScalePrompt)受信時の震源地脱字修正および空文字部分一致による他地域地震の誤発報防止 (`app/services/disaster_service.py`)**:
  - `hypocenter.name` が空文字の震度速報時、観測点配列 `points` から最大震度を観測した地域名を自動抽出し、フォールバック「各地」を徹底。
  - ローカル地域判定で `"" in target_pref` が常に True になるバグを修正し、他地域地震の誤発報を完全防止。
- **GitHub Actions ワークフローのバージョン取得構文エラー修正 (`.github/workflows/docker-publish.yml`)**:
  - bash内インラインPythonでの正規表現エスケープによる SyntaxError を解消し、標準インポート構文で安全にバージョンを取得できるように改善。

---

## [1.0.11] - 2026-10-24

### 追加・新機能 (Added)
- **気象庁高解像度降水ナウキャスト公式配色準拠の雨雲レーダー凡例 (`public/app.js`, `public/style.css`, `public/locales/ja.json`, `public/locales/en.json`)**:
  - 気象庁公式カラーテーブル（8段階: 0〜1, 1〜5, 5〜10, 10〜20, 20〜30, 30〜50, 50〜80, 80+ mm/h）に 100% 準拠した美しいフロート凡例コントロール（Leaflet `bottomleft`）を新設。
  - ダーク・グラスモーフィズムデザイン（半透明ぼかし背景、角丸、陰影）を採用し、地図上の視認性を確保。
  - 各色バーへのマウスホバーで「猛烈な雨」「非常に激しい雨」などの詳細な雨の強さ解説ツールチップを表示。
  - 「🌦️ 雨雲レーダー重ね合わせ」トグルスイッチの ON/OFF に完全連動し、レーダー非表示時は凡例も連動して非表示化。
  - WebUI の日英言語切り替え（`voicehub:language-changed`）にリアルタイム連動。
- **WebUI 発言履歴フィルターピルの拡充 (`public/index.html`, `public/app.js`, `public/style.css`)**:
  - 発言履歴画面のフィルターピルに「🌧️ 雨アラーム」と「🚨 防災速報」の専用フィルターボタンを追加。
  - 送信元バッジ（`source-rain_alarm`, `source-disaster`, `source-mcp`, `source-mqtt`, `source-scheduled_speech`）の専用カラーとバッジスタイルを定義。

### 修正・堅牢化 (Fixed / Reliability)
- **雨雲レーダーの尺度・ズーム表示不具合修正 (`public/app.js`)**:
  - 気象庁の高解像度降水ナウキャスト（`hrpns`）タイルの仕様（最大ズームレベルが 10 までで、ズーム 11 以上は空の透明画像が返却される）に起因し、デフォルト尺度（ズーム 12）で雨雲が表示されず、2段階縮小（マイナス）しないと表示されなかった問題を解消。
  - `rainRadarLayer`（Leaflet タイルレイヤー）に `maxNativeZoom: 10, maxZoom: 18, minZoom: 4` を設定。ズーム 11 以上のデフォルト尺度や拡大時でも、Leaflet がズーム 10 のタイルを自動的にオーバースケール（高解像度ストレッチ補間）して拡大描画するよう改善。
  - 地図初期化時の初期ズームを局地と周辺地域が見渡しやすい `zoom: 11` に最適化。
- **防災速報コールバックの引数エラー解消 (`app/main.py`)**:
  - `disaster_service`（緊急地震速報・気象警報）から `source="disaster"` などのキーワード引数が渡された際、`app/main.py` 内の `on_disaster_speech` に `**kwargs` が欠落していたため `TypeError` が送出され、音声が再生されず履歴にも残らなかった不具合を完全解消。
- **全音声発話・履歴記録パイプラインの全面堅牢化 (`app/services/speech_service.py`, `app/services/rain_alarm_service.py`, `app/services/history_service.py`)**:
  - `rain_alarm_service._speak_alert`: DND 先回り return を撤廃して `speech_service.speak` に一本化し、DND 発動時でも履歴に「DND抑制」または保留キューとして確実に記録。
  - 重複排除（Deduplication）による同一メッセージ抑止時: `status: "skipped"`、抑止理由メッセージ付きで発言履歴に記録。
  - 対象スピーカー未解決（No valid target devices found）時: `status: "error"`、エラー理由付きで発言履歴に記録。
  - TTS 音声合成例外発生時: `try...except` で安全に捕捉し、`status: "error"`、エラー詳細付きで発言履歴に記録。
  - `history_service.derive_source_label` に `rain_alarm`, `disaster`, `mqtt`, `mcp`, `scheduled_speech`, `system` を追加し、あらゆる経路からの発言の送信元ラベルを正確に導出。
- **WebUI キャッシュバスター更新 (`public/index.html`)**:
  - `app.js?v=1.0.13` に更新。
- **単体・統合テストの追加 (`tests/test_speech_dispatch.py`)**:
  - 防災速報コールバック、雨アラーム連携、重複スキップ履歴、宛先未解決エラー履歴、TTS合成エラー履歴、送信元ラベル導出を検証する 6 件のテストを新設（テスト総数 77 件、100% PASS）。

---

## [1.0.10] - 2026-10-23

### 追加・新機能 (Added)
- **WebUI 401 Unauthorized 自動検知 & ログインモーダル表示 (`public/app.js`)**:
  - グローバル `window.fetch` インターセプターを導入。セッション切れや管理者認証要求（HTTP 401）を自動検知し、即座にログインモーダルを開いて「セッションの有効期限が切れたか、管理者認証が必要です。再度ログインしてください。」と案内。
  - 認証切れ表示中は DND 等のバックグラウンド定期ポーリングを一時休止（pause）させ、サーバーログへの 401 警告連打（500回以上の連続アクセス等）を根本的に抑制。
  - パスワード入力・再ログイン成功時に自動的にリアルタイム同期（SSE）と画面データを再取得してシームレスに操作を復帰可能に改善。

### 修正・堅牢化 (Fixed / Security)
- **ログインセッションのファイル永続化 (`app/core/security.py`, `data/sessions.json`)**:
  - `PersistentSessionSet` クラスを新設。従来のインメモリ管理（`set()`）から、永続ボリューム上の `data/sessions.json` へのアトミック同期・保存に変更。
  - Docker コンテナや Uvicorn プロセスの再起動を跨いでも、ブラウザ側の有効な Cookie（有効期限30日）が自動的に復元され、再ログインを強いられる問題を根本解決。
  - 有効期限切れセッションの自動パージ、および管理者パスワード変更時の全セッション一括失効（セキュリティ保護）を完備。

---

## [1.0.9] - 2026-10-23

### 追加・新機能 (Added)
- **SSE (Server-Sent Events) による DND・ミュート状態のリアルタイム自動反映 (`GET /api/events`)**:
  - Homebridge（Apple ホームアプリ / Siri）、外部 API、外部デバイス（Logitech G HUB / Stream Deck 等）からミュート状態が変更された際、Web UI をリロードすることなく 0.01秒でヘッダーの「🔇ミュート」⇄「🔊ミュート解除」ボタンの色・アイコン・テキスト、および DND バナーを即座に自動反映。
  - プロキシ・ブラウザのタイムアウトを防ぐ 15 秒周期のキープアライブ（`: keepalive`）送信、ブラウザ標準の自動再接続、スマホスリープ復帰時やタブ切替時の `visibilitychange` 即時再同期、および従来の 15 秒ポーリングをフォールバックとして二重化。
- **外部デバイス連携スクリプトの拡充 (PowerShell / VBScript / バッチ / シェルスクリプト)**:
  - Logitech G HUB や Elgato Stream Deck からのワンタップ・ワンクリックで DND 即時ミュート・解除を可能にするスクリプト自動生成機能。
  - 近年の Windows 10/11 で標準的な PowerShell（`.ps1`）スクリプト形式を新設。
  - VBScript（`.vbs`）における `MSXML2.XMLHTTP` 優先化と WinHTTP 自動フォールバック、および管理者パスワード/Webhook トークンの自動埋め込みに対応。

### 修正・堅牢化 (Fixed / Security)
- **辞書未設定キー取得時の `NoneType.strip()` 例外耐性強化**:
  - 初期状態・クリーン Docker 環境で `webhookToken` 等が未設定（`null`）の場合に `dict.get()` が `None` を返して `AttributeError: 'NoneType' object has no attribute 'strip'` を誘発していた問題を根本改修。`(dict.get(key) or "").strip()` パターンに統一。
- **スマートホーム連携エンドポイント認証の最適化 (`check_admin_auth`)**:
  - 管理者パスワード設定時でも、`INTEGRATION_PREFIXES`（`/api/events`, `/api/dnd/`, `/api/disaster/triggers`, `/api/devices`, `/api/status`）へのアクセス時に Webhook トークン（URL クエリ `?token=`、Bearer、`x-webhook-token` 等）による正当な外部連携アクセスを許可。

---

## [1.0.8] - 2026-10-22

### 追加・新機能 (Added)
- **OpenAI & Gemini モデル動的ディスカバリー・厳格フィルタリング・推奨ソート**:
  - `GET /api/ai/models`: OpenAI および Google Gemini の公式 API から利用可能なモデル一覧を動的に取得する機能を実装。
  - **不要モデルの厳格除外**: 音声系（`whisper`, `audio`, `realtime`）、画像生成（`dall-e`）、テキスト埋め込み（`embedding`）、モデレーション、微調整（`ft:`）、および古い日付スナップショット版（`-2024-08-06`, `-0613` 等）を自動除外し、要約・発話生成に特化したモデルのみを抽出。
  - **推奨モデル優先ソート & 日本語ラベル**: コストパフォーマンス・速度に優れた最新主力モデル（OpenAI: `gpt-4o-mini`【高速・推奨】、`gpt-4o`【高性能・推奨】、`o3-mini`【最新推論・推奨】 / Gemini: `gemini-2.5-flash`【高速・推奨】、`gemini-2.5-pro`【高精度・推奨】）を自動判別し、最上位に日本語ラベル付きで優先配置。
  - **インメモリキャッシュ & 手動更新**: 外部 API への過剰リクエストを防ぐため 1 時間キャッシュし、WebUI の「🔄 モデル更新」ボタン押下時に `forceRefresh=true` で即座に最新一覧を取得可能。
  - **安全フォールバック & 自己修復機能**: API キー未設定時やネットワーク障害時のデフォルト推奨モデル一覧自動返却、および古い廃止モデル指定時の最新推奨モデル（`gpt-4o-mini` / `gemini-2.5-flash`）への自動補正。
- **専用ヘルスチェックエンドポイント (`GET /health` & `GET /api/health`)**:
  - 管理者パスワード設定の有無にかかわらず、Docker `HEALTHCHECK` や外部監視ツールから常時認証不要で死活監視可能な専用エンドポイントを新設。
- **MCP エンドポイントの包括的認証保護 & 接続設定自動切り替え**:
  - `/mcp` 配下の全エンドポイント（`/mcp/*`）を管理者パスワード保護の対象として包括的に保護。
  - WebUI 上で「🏠 宅内 LAN (ローカル)」選択時はローカル HTTP / IP、「🌐 インターネット (Cloudflare Tunnel)」選択時は HTTPS / Tunnel ドメインの接続設定スニペットを正確に出力するよう補正。

### セキュリティ (Security)
- **GitHub Code Scanning (CodeQL) アラート #28 (`py/weak-sensitive-data-hashing`) 対策**:
  - API キーのキャッシュ管理においてハッシュ化（`hashlib.sha256`）を全廃し、ダイレクトな文字列比較に統一することで静的解析の誤検知を根絶。

---

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
