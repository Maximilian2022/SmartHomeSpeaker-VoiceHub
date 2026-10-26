# 修正履歴 (Remediation History)

## 2026-10-26 23:45 - 震度速報(ScalePrompt)受信時の震源地脱字修正および空文字部分一致による他地域地震の誤発報防止
- **背景と課題**:
  - 発言履歴にて、2026/10/26 23:35:55 に「地震情報です。で最大震度3の地震が発生しました。」と、場所が脱字したアナウンスが実行され、ユーザーから「どこで？ｗ」と報告された。
  - 調査の結果、2026/10/26 23:34発生の「熊本県天草・芦北」（最大震度3）の地震情報を受信した際、気象庁の第一報が震度速報（`ScalePrompt`）であったため、震源地名（`hypocenter.name`）が空文字 `""` だったことが原因。
  - さらに、ユーザーは「東京都・対象地域のみ（`targetScope == 'local'`）」に設定していたにもかかわらず、熊本県の地震が誤って発報されていた。これは地域判定のフォールバック条件 `hypocenter in target_pref` が、`hypocenter == ""` のために `"" in "東京都"` と評価され、Pythonの仕様により常に `True` となっていたため。
- **改修内容**:
  1. **震度速報時の観測地点名抽出とフォールバック徹底 ([app/services/disaster_service.py](file:///root/google-home-voicetext-docker/app/services/disaster_service.py))**:
     - `hypocenter.name` が空文字の震度速報（`ScalePrompt`）受信時、観測点配列 `points` から最大震度を観測した地域名（`addr` または `pref`）を自動抽出（例：「熊本県天草・芦北」）。
     - 震度速報時は「地震情報です。{location}で最大{scale_text}の揺れを観測しました。」、震源確定時は「地震情報です。{location}で最大{scale_text}の地震が発生しました。」と適切な日本語を生成。
     - 観測地点データが得られない場合でも確実に `"各地"` にフォールバックさせ、「。で最大」の脱字を完全防止。
  2. **ローカル地域判定における空文字すり抜けバグの修正 ([app/services/disaster_service.py](file:///root/google-home-voicetext-docker/app/services/disaster_service.py))**:
     - `hypocenter_raw` が非空の場合のみ震源地名による地域判定を実行するように修正し、空文字列による `"" in target_pref`（常にTrue）の誤判定を完全に排除。
     - EEW地域判定（`_handle_eew`）側でも同様に `aname` の非空チェックを追加して堅牢化。
  3. **同一地震の重複抑止キー改善 ([app/services/disaster_service.py](file:///root/google-home-voicetext-docker/app/services/disaster_service.py))**:
     - `event_key` を `f"{event_time}_{display_scale}"` に改善し、震度速報の後に震源情報（Destination）等が届いた場合でも同一震度であれば多重アナウンスされないよう最適化。
  4. **単体テストの追加と全件検証 ([tests/test_disaster_quake_report.py](file:///root/google-home-voicetext-docker/tests/test_disaster_quake_report.py))**:
     - 震度速報時の他地域スキップ、自地域合致時の地点名発話、全国モードでの地点名抽出、フォールバック「各地」の動作を網羅するテスト5件を追加。全102件のテストが100% PASSすることを確認。

## 2026-10-26 17:35 - README への取扱説明書・詳細マニュアル (MANUAL.md) 総合案内とチャプターリンクの最適配置
- **背景と課題**:
  - リポジトリを訪れたユーザーが、1,000行を超える充実した仕様・設定書である [MANUAL.md](file:///root/google-home-voicetext-docker/MANUAL.md) の存在に気づきやすく、迷わず目的の情報（各種スピーカー接続、初期設定、HomeKit、REST API 等）にアクセスできるよう、README 内に最適な案内を配置したいという要望。
- **改修内容**:
  1. **日英トップナビゲーション・バナーの強化 ([README.md](file:///root/google-home-voicetext-docker/README.md), [README-en.md](file:///root/google-home-voicetext-docker/README-en.md))**:
     - タイトル直下の言語リンクに `[📖 取扱説明書・総合仕様書 (MANUAL.md)](MANUAL.md)` を設置。
     - 冒頭に `> [!TIP]` コールアウトを設け、「詳しい使い方・初期設定・接続手順をお探しですか？」として [MANUAL.md](file:///root/google-home-voicetext-docker/MANUAL.md) への直通リンクを目立たせて配置。
  2. **起動直後の初期設定・スピーカー登録ガイダンス ([README.md](file:///root/google-home-voicetext-docker/README.md), [README-en.md](file:///root/google-home-voicetext-docker/README-en.md))**:
     - 「🚀 はじめかた」のブラウザアクセス（`http://<IP>:8080`）直後に `> 💡 起動後の初期設定・スピーカー登録について` コールアウトを追加し、Echo、HomePod、Tapoカメラ、DLNA等の機器登録が必要なユーザーを [MANUAL.md 第8章](file:///root/google-home-voicetext-docker/MANUAL.md#8-各種スマートスピーカー音響機器の接続仕様) へスムーズに誘導。
  3. **詳細セクションの体系的チャプターリンク化 ([README.md](file:///root/google-home-voicetext-docker/README.md), [README-en.md](file:///root/google-home-voicetext-docker/README-en.md))**:
     - 「📖 取扱説明書・総合技術仕様」セクションを新設し、各種スピーカー接続、TTSエンジン拡張、HomeKit/Siri、防災トリガー、MCPサーバー、MQTT、全REST API、セキュリティの各章への直接アンカーリンクを一覧化。

## 2026-10-26 17:28 - GitHub Actions 自動化パイプラインの完全日本語リリースノート生成と都度リリース連動の実装
- **背景と課題**:
  - ユーザーから「Docker Image作成と連動して都度リリースを発行したい」「変更履歴の文章を完全な日本語でリリースページに自動反映させたい」という要望。
  - 従来の GitHub Actions ワークフローでは `v*.*.*` タグを明示 push した場合のみリリースが作成され、本文も GitHub の自動生成（英語見出し・コミット一覧）のみで、詳細な改修背景や内容が伝わらない状態だった。
- **改修内容**:
  1. **完全日本語リリースノート自動生成スクリプトの新設 ([scripts/extract_release_notes.py](file:///root/google-home-voicetext-docker/scripts/extract_release_notes.py))**:
     - `logs/remediation_history.md`（または `CHANGELOG.md`）の最新セクションを自動抽出し、背景・課題・改修内容を整形。
     - ローカル絶対パスリンク（`file:///root/...`）を GitHub リポジトリ上の blob URL に自動置換。
     - 直前タグからのコミット一覧（日本語コミットメッセージ）を整形して末尾に併記。
     - Docker pull コマンド（`latest` とバージョンタグ）を自動挿入。
  2. **GitHub Actions ワークフローの強化 ([.github/workflows/docker-publish.yml](file:///root/google-home-voicetext-docker/.github/workflows/docker-publish.yml))**:
     - `main` ブランチ push 時に、`app/version.py` からバージョン番号を取得し、Docker Hub へ `latest`、`v${version}`、`${version}` のマルチタグを自動ビルド＆プッシュ。
     - `release` ジョブを `main` push 時にも自動起動させ、該当バージョンの GitHub Release が未作成であれば自動で Git タグを作成して完全日本語の GitHub Release を公開。
  3. **バージョンバンプとドキュメント追跡 ([app/version.py](file:///root/google-home-voicetext-docker/app/version.py), [CHANGELOG.md](file:///root/google-home-voicetext-docker/CHANGELOG.md), [.gitignore](file:///root/google-home-voicetext-docker/.gitignore))**:
     - バージョンを `1.0.12` にバンプ。`CHANGELOG.md` を更新。
     - `.gitignore` で `logs/*.md` を追跡対象とし、リポジトリ上で改修履歴が正しく GitHub Actions ランナーに渡るよう整備。
     - `tests/test_update_service.py` のモックバージョンを `v9.9.9` に更新し、全97件の単体テストが 100% PASS することを確認。

## 2026-10-26 17:15 - Google Cast グループ/個別スピーカーのフェイルファストリトライ・安全な階層型フォールバックおよび防災スピーカー選択消失防止の完全実装
- **背景と課題**:
  - 発言履歴で雨アラームが「送信失敗 (Playback failed)」となっていた原因の調査。Google Cast キャストグループ（`192.168.11.176:32094`）への接続タイムアウト（4秒）により発声が途絶していた。
  - DND中だったため保留が期待されていたが、設定 `dnd.scheduleEnabled: false` で平日スケジュールが無効化されており、かつ手動ミュート（15:12〜16:26）前の時間帯（13:39〜14:14）であったため即時発信され失敗が記録された。
  - 防災設定で特定のスピーカーを選択していたにもかかわらず、画面表示の更新タイミングで選択状態が空にリセットされ、未選択（`targets: ["ALL"]`）として保存されてしまっていた。
  - 屋外カメラ（Tapo/ONVIF）や別室機器を不用意に巻き込まず、環境に応じた柔軟かつ確実なフォールバックを可能にするため、フォールバック先の優先順位設定（Group > 単体、GH > Alexa > HP > DLNA > ONVIF）と、オプション選択（`fallbackSpeaker`: auto / default / 個別指定 / none）を実装。
- **改修内容**:
  1. **Google Cast グループ接続のフェイルファスト化と切断キャッシュ破棄 ([app/services/cast_service.py](file:///root/google-home-voicetext-docker/app/services/cast_service.py))**:
     - グループ接続（port != 8009）時のタイムアウトを 3.0 秒に短縮。
     - ソケット切断時や再生失敗時に確実にキャッシュから pop して古いソケットを破棄する `purge_cache(host, port)` を新設。
  2. **送信失敗時のリトライ＆2段階フォールバックの強化 ([app/services/speech_service.py](file:///root/google-home-voicetext-docker/app/services/speech_service.py))**:
     - グループ宛て: 最大2回試行。1回目失敗時に最新の mDNS ポート/IP を再解決してリトライ。2回とも失敗した場合は紐づけられた個別 Google Cast スピーカー群（`_fallback_members`）へ自動フォールバック。
     - 個別スピーカー宛て: DHCP や一時的な瞬断を考慮し最大3回試行。失敗毎に IP/ポートを再解決。3回失敗した場合は全体フォールバック先へ。
     - フォールバック先の厳格な優先順位ロジック（`resolve_fallback_targets`）:
       - 階層1: グループ（Group） > 単体スピーカー（Single）
       - 階層2: Google Cast (GH) > Alexa > HomePod (HP) > DLNA > ONVIF/Tapo
       - 屋外カメラや外部機器しかない環境でも機能し、かつグループやGoogle Castがある環境ではそちらを最優先。
     - 宛先重複排除（`resolve_targets`）で同一IPを持つ親端末とグループ（別ポート）が衝突して消えないようキーを改善（`id` または `ip:port`）。
  3. **防災設定のスピーカー選択消失防止とフォールバック先設定 ([public/app.js](file:///root/google-home-voicetext-docker/public/app.js), [public/index.html](file:///root/google-home-voicetext-docker/public/index.html), [public/locales/ja.json](file:///root/google-home-voicetext-docker/public/locales/ja.json), [public/locales/en.json](file:///root/google-home-voicetext-docker/public/locales/en.json))**:
     - `renderAllSpeakerSelectors`: `renderDisasterSpeakers` 呼び出し前に現在のチェック状態を取得・引き継ぎ、空リセットを完全防止。
     - `renderDisasterSpeakers`: 引数が空でも画面チェック状態 ➔ `state.disasterSettings.targetDevices` の順でフォールバックして選択を保持。
     - 防災設定カード内に「🔄 送信失敗時の自動フォールバック先 (`settingDisasterFallbackSpeaker`)」を追加。
     - 日英多言語対応（`ja.json`, `en.json`）のキーを追加。
     - キャッシュバスター（`app.js?v=1.0.22`）を更新。
  4. **雨アラームの安全な初期値 ([app/services/rain_alarm_service.py](file:///root/google-home-voicetext-docker/app/services/rain_alarm_service.py))**:
     - 未指定・空リスト時のフォールバック先を外カメラを含む `ALL` から `GH:ALL`（屋内Google Cast）へ安全化。
  5. **ユニットテストの網羅とコンテナ反映 ([tests/test_speech_dispatch.py](file:///root/google-home-voicetext-docker/tests/test_speech_dispatch.py))**:
     - グループのリトライ＆個別フォールバック、個別の3回リトライ、階層型フォールバック（Group > 単体, GH > Alexa > HP > DLNA > ONVIF）のテストケースを追加。
     - 全97件の単体テストがすべて PASS。
     - 実機コンテナ `SmartSpeaker-VoiceHub` を再起動し healthy 稼働を確認。

## 2026-10-26 16:05 - ヘッダーの2段構造化による動的幅要素（DND・デバイス・Cache）の分離と完全美観保護
- **背景と課題**:
  - 先の修正で `.header-status` に `flex-wrap: nowrap;` を適用した結果、画面幅に対して右側のチップ群の合計幅が超過し、左側のブランドロゴ・タイトル（`Smart Speaker Voice Hub`）の上にステータスチップが重なって文字が潰れる重篤なレイアウト破壊が発生した。
  - ユーザーからの「動的に幅が変わるやつだけ、2段目にもってくとかどう？」という的確な提案に基づき、ヘッダーを「静的ブランド＆常駐操作行（1段目）」と「動的ステータス＆DND操作バー（2段目）」の美しい2段構成へ完全分離。
- **改修内容**:
  1. **HTML構造の階層分離 ([public/index.html](file:///root/google-home-voicetext-docker/public/index.html))**:
     - **1段目 (`header-main-row`)**: ブランドロゴ・タイトル（`Smart Speaker Voice Hub`）と、幅が固定された常駐ユーティリティ（サーバー稼働中、ログアウト、バージョン、言語切替）を配置。要素数を絞ったことで、どんな画面幅でもタイトルに他要素が被る事故を100%防止。
     - **2段目 (`header-sub-row`)**: 動的に幅が変化する要素（デフォルトスピーカー名、音声Cache容量、DND状態バッジ、ミュートトグルボタン）を専用のステータスバーとして配置。
  2. **スタイリングとグラスモーフィズムデザイン ([public/style.css](file:///root/google-home-voicetext-docker/public/style.css))**:
     - `.app-header`: `display: flex; flex-direction: column; gap: 10px;` で2段を整然と縦並び配置。
     - `.header-sub-row`: 薄い透過背景（`background: rgba(255, 255, 255, 0.025); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: var(--radius-md);`）とグラスモーフィズム（`backdrop-filter: blur(10px);`）を適用し、独立したダッシュボードコントロールバーとして高級感を向上。
     - 2段目内で `justify-content: space-between;` を使用し、左側にデバイス/Cache情報、右側にDND情報/ミュートボタンを余裕を持って左右分離配置。DNDの理由がどれだけ長く変化しても、中央に広い余白があるためレイアウトが一切崩れず1行を完璧にキープ。
     - キャッシュバスター（`style.css?v=3.5`, `app.js?v=1.0.21`）を更新。
  3. **検証とテスト**:
     - 単体テスト全94件 PASS。実機コンテナにて最新のHTML/CSS配信および正常稼働（healthy）を確認。
  4. **ミス記録と教訓 ([logs/past-mistake.md](file:///root/google-home-voicetext-docker/logs/past-mistake.md), [logs/past-mistake-title.md](file:///root/google-home-voicetext-docker/logs/past-mistake-title.md))**:
     - `[2026-10-26 01]` として、`flex-wrap: nowrap` の不用意な適用によるオーバーラップ破壊の事象・原因・防止策を記録済み。

## 2026-10-26 15:55 - DND有効化・動的項目選択時のヘッダー横幅崩れ・折り返し防止と美観保護改修
- **背景と課題**:
  - DND（おやすみ・会議モード）をミュートに切り替えたり、選んだ項目（30分ミュート、手動ミュート、カレンダー予定連動など）によって、ヘッダーのDNDチップテキスト（`DND: 🔇手動ミュート` 等）やミュートボタン（`🔇 ミュート` ➔ `🔊 ミュート解除`）の横幅が動的に増加していた。
  - ヘッダー右側のステータスエリア（`.header-status`）に `flex-wrap: wrap;` が指定されていたため、わずかなテキスト長の増加で横幅上限を超えてしまい、中途半端に2段に折り返されてヘッダーの縦幅が急激に広がり、デザインの美観が著しく損なわれる問題が発生していた。
- **改修内容**:
  1. **ヘッダーCSSの折り返し防止と幅安定化 ([public/style.css](file:///root/google-home-voicetext-docker/public/style.css))**:
     - `.app-header`: `min-height: 52px;` を設定し、状態遷移時にもヘッダー全体の高さが 1px たりとも動かないよう固定。
     - `.header-status`: `flex-wrap: nowrap;`、`gap: 8px;`、`justify-content: flex-end;` に変更し、状態変化による意図しない2段折り返しを根本防止。
     - 各チップ（`.status-chip`, `.status-chip-sub`）: パディングを `5px 11px`、フォントサイズを `0.82rem` に引き締め、全体で約60〜80pxの横幅余白を創出。
     - `#headerDndChip` & `#headerDndText`: `max-width: 125px;`、`overflow: hidden; text-overflow: ellipsis; white-space: nowrap;` を設定。どれだけ長いカレンダー予定名や定時スケジュール名が来てもヘッダーを突き破らないよう防御。
     - `.header-dnd-btn`: `min-width: 98px; justify-content: center;` を設定し、「ミュート」と「ミュート解除」でボタン幅が変わらないよう固定してレイアウトシフト（横揺れ）を防止。
     - `#defaultDeviceText`: `max-width: 95px;` と `text-overflow: ellipsis;` を設定し、長い端末名での圧迫を防止。
     - `.header-logout-btn`: パディングを `5px 11px`、`border-radius: 999px;` に変更して他チップとピル型で美観を統一。
  2. **レスポンシブな適応ブレークポイントの整備 ([public/style.css](file:///root/google-home-voicetext-docker/public/style.css))**:
     - 1340px以下: サーバーIPアドレス（`server-ip-text`）を非表示にして「● 稼働中」にスリム化。
     - 1160px以下: 優先度の低い `cacheStatusChip` と `headerVersionChip` を非表示にして主要な操作と状態を1行にキープ。
     - 920px以下（モバイル・タブレット）: ヘッダーを意図的な2段構成に切り替え、チップ群を横スクロール（スクロールバー非表示）でスマートに表示。
  3. **JavaScript 側でのスマートな DND ラベル生成と詳細ツールチップ ([public/app.js](file:///root/google-home-voicetext-docker/public/app.js))**:
     - `renderDndStatus`: 手動30分（`⏱️30分`）、1時間（`⏱️1時間`）、2時間（`⏱️2時間`）、本日中（`🌙本日中`）、手動解除まで（`🔇手動`）、カレンダー予定（`📅予定名`）、定時（`⏰予定名`）など、選択された項目に応じたスマートでコンパクトなラベルを生成。
     - チップの `title` 属性に完全な理由と解除予定時刻（例: `DND発動中: 手動ミュート (16:30まで) - クリックで設定へ`）を付与し、省略時もホバーで全文確認可能。
     - `serverStatusText`: IPアドレス部分を `<span class="server-ip-text">` で囲い、レスポンシブ制御に対応。
  4. **DND設定カード内のバナー美観保護 ([public/index.html](file:///root/google-home-voicetext-docker/public/index.html), [public/style.css](file:///root/google-home-voicetext-docker/public/style.css))**:
     - `#dndStatusBanner` の左側テキストブロックに `.dnd-status-banner-content`（`min-width: 0;`）と `word-break: break-word;` を適用。
     - 右側の保留キューバッジ（`#dndQueueBadge`）に `flex-shrink: 0;` を付与し、長い会議名でもバッジが潰れたり押し出されたりしないよう防御。
     - `.btn-quick-dnd` に `min-width: 105px; justify-content: center;` を付与し、ボタンの幅と整列を美しく均等化。
     - キャッシュバスター（`style.css?v=3.4`, `app.js?v=1.0.20`）を更新。
  5. **テスト検証**:
     - 全94件の単体テストがすべて PASS することを確認。実機コンテナが healthy 状態で正常稼働中であることを確認。

## 2026-10-26 15:10 - 外部デバイス連携 (Logitech G HUB / Stream Deck 等) の Windows 用スクリプト bat 一本化
- **背景と課題**:
  - これまで Windows 向けに `.vbs`、`.ps1`、`.bat` を提供していたが、`.ps1` は PowerShell 実行ポリシーや特殊な引数（`-ExecutionPolicy Bypass -WindowStyle Hidden` 等）が必要で動作しなかったり設定が煩雑であり、`.vbs` も `wscript.exe` の指定が必要など設定の敷居が高かった。
  - Logitech G HUB の「アプリケーションの起動」や Elgato Stream Deck の「システム: 開く」アクションでは、Windows 標準の `curl.exe` を呼び出す `.bat`（バッチファイル）をそのまま指定するだけで追加引数なしで確実・高速に動作するため、Windows 用は `.bat` に一本化したいという要望に対応。
- **改修内容**:
  1. **バックエンド API デフォルトの bat 化 ([app/routers/dnd.py](file:///root/google-home-voicetext-docker/app/routers/dnd.py))**:
     - `build_dnd_script` のデフォルトおよびフォールバック形式を `"bat"` に変更。
     - `/api/dnd/script/preview` および `/api/dnd/script/download` のクエリパラメータ `format` デフォルト値を `"bat"` に変更。
     - 生成される `.bat` ファイルのヘッダーコメントを `Suitable for Logitech G HUB, Elgato Stream Deck, Windows` に整理。
  2. **WebUI のスクリプト選択肢とガイドの刷新 ([public/index.html](file:///root/google-home-voicetext-docker/public/index.html), [public/app.js](file:///root/google-home-voicetext-docker/public/app.js))**:
     - スクリプト形式選択の選択肢を「`.bat` (Windows / Logitech G HUB & Stream Deck 推奨)」(デフォルト選択) と「`.sh` (Bash シェルスクリプト / macOS・Linux)」の2択に一本化・集約。
     - Logitech G HUB および Stream Deck の割り当て手順（Instruction）を、ダウンロードした `.bat` ファイルを直接指定するだけの簡単手順に刷新（特殊な引数や実行ファイルの複雑な説明を撤廃）。
     - `getSelectedFormat()` のデフォルトを `'bat'` に変更。
     - `app.js?v=1.0.19` キャッシュバスティングを更新。
  3. **多言語辞書・ドキュメントの更新 ([public/locales/ja.json](file:///root/google-home-voicetext-docker/public/locales/ja.json), [public/locales/en.json](file:///root/google-home-voicetext-docker/public/locales/en.json), [MANUAL.md](file:///root/google-home-voicetext-docker/MANUAL.md), [MANUAL-en.md](file:///root/google-home-voicetext-docker/MANUAL-en.md))**:
     - 日英の辞書で `.bat` 推奨文言と直接指定の案内文に更新（キー対称性を維持）。
     - マニュアルの外部デバイス連携解説を Windows `.bat` 一本化の仕様に更新。
  4. **単体テストの追加と動作検証 ([tests/test_dnd_scripts.py](file:///root/google-home-voicetext-docker/tests/test_dnd_scripts.py))**:
     - `test_api_script_preview_default_bat` および `test_api_script_download_default_bat` を追加。
     - 全94件の単体テストがすべて PASS することを確認。実機コンテナ `SmartSpeaker-VoiceHub` を再起動し healthy 状態を確認。

## 2026-10-26 12:20 - 発言履歴「再発言」スピーカー復元バグ修正 & スピーカー接続遅延・応答停止のインテリジェント通知 (案1+3)
- **背景と課題**:
  1. 発言履歴一覧で「再発言」ボタンを押した際、本来の発話対象スピーカーではなくすべてのスピーカーが全選択されてしまう不具合が発生していた。
  2. Google Home / Nest 等のスピーカーへの送信がタイムアウトした際、「0台成功でした。システムログを確認してください」とだけ表示され、一時的なWi-Fi混雑なのか端末ハングアップなのか一般ユーザーに判断がつかない課題があった。
- **改修内容**:
  1. **再発言スピーカー選択の正確な復元 ([public/app.js](file:///root/google-home-voicetext-docker/public/app.js))**:
     - `renderSpeakersCheckboxes` 内で `<input type="checkbox">` に `data-name`, `data-raw-name`, `data-id` 属性を付与。
     - `btn-repeat` クリックハンドラーで、履歴の `targets`（IP、デバイス名、rawName、id、表示名、ALL、default）との厳密照合を実装。
     - 照合不一致時に全選択してしまう不適切なフォールバックを撤廃（一致した端末のみ選択、未一致時はデフォルト1台を選択）。
  2. **スピーカー接続遅延・応答停止のインテリジェント通知 (案1+3)**:
     - `state.deviceFailureCounts` による端末ごとの連続失敗回数トラッキングを導入。成功時は自動リセット。
     - エラー種別（接続タイムアウト、オフライン/到達不能、再生エラー）を解析。
     - **1回目の失敗**: 「⚠️ {端末名} への送信に失敗しました。Wi-Fiの一時的な混雑・遅延の可能性があります。もう一度お試しください」と通知。
     - **2回以上の連続失敗**: 「⚠️ {端末名} が応答していません（{N}回連続）。端末がフリーズしている可能性が高いため、電源プラグの抜き差し（再起動）をお試しください」と具体的・段階的アドバイスを表示（表示時間も8秒に延長）。
     - 一部成功時も、どの端末が応答しなかったかを明記。
     - `public/index.html` の `app.js?v=1.0.18` キャッシュバスティングを更新。

## 2026-10-26 12:05 - Homebridge / 外部連携の Bearer Webhook トークン誤認によるレート制限ロックアウト (HTTP 429) バグの修正
- **背景と課題**:
  - Homebridge 等の外部クライアント (`192.168.11.248`) が `/api/dnd/status` や `/api/disaster/triggers` を定期ポーリングする際、`Authorization: Bearer <Webhookトークン>` ヘッダーを送信していた。
  - `app/core/security.py` の `check_admin_auth` において、Bearer ヘッダーが管理者パスワードまたは管理者セッションと一致しない場合に、即座に `login_rate_limiter.record_failure(client_ip)`（ログイン失敗）を記録していた。
  - 後続のスマートホーム連携判定で Webhook トークンとして認証成功（200 OK）するものの、内部の失敗カウンターが毎アクセス加算され、5回達した時点で 180秒間 HTTP 429 (Too Many Requests: 「認証試行回数が上限を超えました」) で誤認ロックアウトされる無限ループが発生していた。
- **改修内容**:
  1. **`app/core/security.py` の認証順序と失敗記録タイミングの是正**:
     - `auth_header.startswith("Bearer ")` で管理者パスワードと不一致の場合でも、即時 `record_failure` を呼ばずに後続の MCP / スマートホーム連携判定へフォールスルーするよう修正。
     - MCP エンドポイントおよびスマートホーム連携エンドポイント (`/api/dnd/`, `/api/disaster/triggers`, `/api/devices` 等) で Webhook トークン認証に成功した場合は `login_rate_limiter.record_success(client_ip)` を呼び出し、失敗カウントを確実にリセット。
     - 全ての認証チェック（Cookie, X-Admin-Password, Bearer, Webhookトークン等）を通過できなかった場合にのみ、認証情報が存在していれば最終段で `record_failure` を記録。
     - `record_failure` がロックアウトに達した場合は、即座に HTTP 429 を返却して挙動の一貫性を確保。
  2. **テストの追加と動作検証**:
     - `tests/test_auth_security.py` に `test_bearer_webhook_token_integration_rate_limit` を追加。有効な Webhook トークンを Bearer ヘッダーで連続送信しても 200 OK で通過しロックされないこと、および不正トークン時には正常に 429 ロックされることを検証。
     - 全92件の単体テストがすべて PASS することを確認。
     - コンテナ `SmartSpeaker-VoiceHub` を再起動し、実機環境で `192.168.11.248` からの定期アクセスが 429 にならず正常に 200 OK で処理され続けることを確認。

## 2026-10-26 10:35 - GitHub main ブランチ保護ルールの適用および依存関係更新 PR #18 のマージ・検証
- **背景と課題**:
  - GitHub リポジトリ上で「Your main branch isn't protected / Protect this branch from force pushing or deletion, or require status checks before merging」の警告が表示されていたため対処。
  - Dependabot より提出されていた PR #18 (`build(deps): bump the python-dependencies group with 3 updates`) の確認と取り込み。
- **対応内容**:
  1. **Dependabot PR #18 の検証およびマージ**:
     - 対象パッケージ: `fastapi` (0.143.3 -> 0.161.1), `pydantic-settings` (2.16.0 -> 2.16.1), `pytapo` (3.3.43 -> 3.4.28)。
     - CI チェック（Dockerビルド、ユニットテスト実行）全通過を確認。
     - コード互換性確認（`pytapo` の呼び出し箇所、`fastapi` のルーティング・ライフサイクル定義等）およびローカル環境での全91テスト PASS を確認。
     - `gh pr merge 18 --squash --delete-branch` でSquashマージ完了。ローカルの main ブランチに `git pull` で同期。
  2. **GitHub main ブランチ保護ルールの適用**:
     - GitHub REST API (`PUT /repos/Maximilian2022/SmartHomeSpeaker-VoiceHub/branches/main/protection`) を実行。
     - `allow_force_pushes: false`（強制プッシュ禁止）および `allow_deletions: false`（ブランチ誤削除禁止）を設定。
     - 個人開発時の快適な直接push運用を維持しつつ、事故によるブランチ消失や履歴破壊を防止し、GitHubの警告バナーを解消。

## 2026-10-25 21:00 - システム全般監査・安定性向上・セキュリティ強化・データ保護・機能バグ全面改修
- **背景と課題**:
  - `scratch/report.md` による包括的監査に基づき、実機障害、データ汚染、セキュリティ脆弱性、設定破壊バグ、機能バグ、最適化などシステム全体の指摘事項を網羅的に改修。
- **改修内容**:
  1. **実機障害の解消**:
     - `docker-compose.yml`: `watchtower` の `network_mode: "host"` を削除し `ports: ["127.0.0.1:8082:8080"]` に変更。VoiceHub 本体 (:8080) とのポート衝突による無限再起動ループを完全解消。実機上で `Up (healthy)` で安定稼働を確認。
  2. **テスト実行環境のデータ分離と本番履歴保護**:
     - `app/config.py`: テスト実行環境（`unittest` / `pytest`）を自動検出し、一時ディレクトリ（`/tmp/voicehub_test_env`）に `DATA_DIR` と `LOG_DIR` を自動隔離。
     - `tests/__init__.py` & `tests/conftest.py`: 自動一時ディレクトリ割当と終了時クリーンアップを実装。
     - `data/history.json`: 過去のテストデータ（`TestClient` や `TTSエラーテスト` 等）を全消去し本番履歴のみにクリーンアップ完了。
  3. **セキュリティ強化・IPスプーフィング対策**:
     - `app/core/security.py`: `LoginRateLimiter` に TTL 自動パージを追加しメモリリークを防止。`cf-*` ヘッダー信頼判定において接続元ソケットがローカルループバック (`is_loopback_or_local`) の場合のみ信頼するよう厳格化し、IP Spoofing を防止。
     - `app/routers/auth.py`: `POST /api/auth/password` にもレート制限と失敗カウント記録を適用。
     - `app/routers/dnd.py`: PowerShell スクリプト生成時に `$token = '{ps_pwd}'`（シングルクォート＋エスケープ）を採用しコマンドインジェクションを完全防止。
  4. **設定保護・マスク破壊バグの修正**:
     - `app/services/settings_service.py` & `app/routers/settings.py`: `mqtt.brokers[].password`, `tts_providers.apiKey`, `onvif` (`tapoPassword`, `registeredDevices[].password`), `rainAlarm.yahooAppId` のマスク (`********`) および保存時の既存パスワード自動復元処理を実装。
     - `app/routers/speech.py` & `app/services/tts_service.py`: TTS プロバイダー設定の API キーマスク＆復元処理を追加。
     - `app/services/devices_service.py` & `app/routers/onvif_dlna.py`: カメラの `passwordHash` を API レスポンスから除外。
  5. **機能バグ・UI不具合の解消**:
     - `app/services/tts/voicevox_provider.py`: SHAREVOX 話者IDが `sharevox:XX` となるよう修正。COEIROINK の `pitchScale` 計算を修正。
     - `app/routers/homepod_alexa.py`: 未定義メソッド `scan_devices()` を `list_devices(force_refresh=True)` に修正。
     - `app/services/history_service.py` & `app/core/log_rotator.py`: `SpeakLogRotator.clear()` を実装し、履歴クリア時に `/logs/speak.log` もトランケート。
     - `app/routers/system.py`: `POST /api/system/update` の管理者認証を `check_admin_auth` に統一。
     - `public/app.js`: 言語切替リスナーを `DOMContentLoaded` 内に配置し動的コンポーネントの再描画を確実に動作させ、`escapeHtml` による DOM XSS 多層防護を徹底。
     - `app/services/ai_service.py`: OpenAI 推論モデルの `max_completion_tokens` を 2000 に拡大。
     - `plugins/homebridge-voicehub/package.json`: 架空の依存バージョンを実在バージョン（Node 20, TS 5.4, Homebridge 1.8）へ修正。
  6. **最適化・構造改善**:
     - `app/services/tts_service.py`: WAV 再生時間計測に標準 `wave` モジュールを用いた高速パスを新設。TTS フォールバック時のキャッシュキー分離、`_cleanup_lru_cache` の `os.scandir` 化。
     - `app/services/mcp_service.py` & `app/services/mqtt_service.py`: バージョン表記を `__version__` に統一。
     - `README.md`: `MANUAL.md` へのリンク修正。
     - `public/index.html`: 静的資産のキャッシュバスティング更新。
     - 単体テスト全 91 件が完全合格（PASS）。

## 2026-10-25 16:30 - 標準チャイム音の初期化不具合解消（即時自動保存・差分更新化）およびAPI・インフラメニューのi18n表示不具合（settings.navUpdate）修正
- **背景と課題**:
  - ユーザーより「標準チャイム音を変更しても、何等かのタイミングで初期化される。設定保存に問題ないか？チェックしてほしい」「API・インフラのメニューがsettings.navUpdateになってる」との報告。
  - 原因調査：
    1. **チャイム音初期化の要因**:
       - `public/app.js` の ONVIF 認証情報保存処理 (`setupOnvifHandlers`) で、`...state.settings` を丸ごと `/api/settings` へ PUT 送信していた。そのため、`state.settings` が初期値（"dingdong"）や古いキャッシュを保持している状態で ONVIF 設定を保存すると、サーバー側の `chime` 設定が上書き・巻き戻されていた。
       - 「音声・機能拡張」サブタブの「標準チャイム音」セレクトボックス (`#settingDefaultChime`) に `change` イベント時の自動保存がなく、カード内にも個別の保存ボタンが存在しなかった（保存ボタンは画面右下最下部の「システム設定を保存」のみ）。ユーザーがチャイムを選択・試聴後に別タブ（即時発言タブや履歴タブなど）へ移動して設定タブに戻ると、タブ切り替えハンドラの `loadSettings()` によりサーバー上の値に巻き戻されていた。
       - `saveAllSettings` 内で DOM 要素から値が取得できない場合に無条件に `'dingdong'` にフォールバックしていた。
    2. **settings.navUpdate 表示異常の要因**:
       - `public/index.html` では `data-i18n="settings.navUpdate"` が指定されていたが、`public/locales/ja.json` および `en.json` の `settings` セクション内に `navUpdate` キーが定義されていなかったため、言語キー名がそのまま画面に露出していた。
- **改修内容**:
  1. **i18n 多言語辞書 (`public/locales/ja.json`, `public/locales/en.json`)**:
     - `settings.navUpdate` を追加（日本語: `"システム更新・自動更新"`、英語: `"System Update & Auto-Update"`）。
     - チャイムカード用キー `settingsFeatures.btnSaveChime`（"💾 保存" / "💾 Save"）および `settingsFeatures.chimeAutoSaveNotice`（"⚡ 選択と同時に自動保存されます" / "⚡ Auto-saved on change"）を追加。
  2. **フロントエンド保存ロジック (`public/app.js`)**:
     - ONVIF 認証保存処理を改修し、全設定オブジェクト（`...state.settings`）の送信を撤廃、`{ onvif: onvifPayload }` の差分のみを送信するように修正。
     - `saveChimeSetting(showNotification = true)` を新設。チャイムセレクトボックス変更時に即時自動保存を実行し、トースト通知で保存完了を明示。
     - `saveAllSettings` 内のフォールバック値を `state.settings?.chime || 'dingdong'` に改善し、DOM 要素が取得できない場合でも既存の設定値を維持。
  3. **UI の改善 (`public/index.html`)**:
     - 「前置きチャイム音」カード内に「💾 保存」ボタン（`#btnSaveChimeOnly`）を追加。
     - 「⚡ 選択と同時に自動保存されます」の案内テキストを追加し、ユーザーの心理的不安を解消。
  4. **単体テスト & 実機検証 (`tests/test_audit_fixes.py`)**:
     - `test_settings_chime_persistence_and_i18n` を追加し、チャイム設定の保存・他設定（ONVIF）差分保存時のチャイム設定維持、および `/locales/ja.json`, `/locales/en.json` の `settings.navUpdate` 定義を自動検証（全 91 件 PASS）。
     - 実機コンテナ `SmartSpeaker-VoiceHub` に改修ファイルを反映し、HTTP 経由での i18n 取得および API 経由でのチャイム設定保存・復元動作を確認。


## 2026-10-25 13:00 - マスク済みAPIキー(********)誤送信による外部AI(Gemini/OpenAI) 400エラー解消と多層防護
- **背景と課題**:
  - ユーザーより「AI Key not validってエラーがログに記録されてるんだけど・・」との報告。
  - 実機ログを調査したところ、定期的に以下の警告が記録されていた：
    `[WARNING] [VoiceHub.AI] [AiService] Geminiモデル動的取得エラー (HTTP 400): {"error": {"code": 400, "message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT"}}`
  - 原因調査：
    1. `/api/settings` の GET 応答時に、セキュリティ保護として `geminiApiKey` や `openaiApiKey` が `********`（8文字のアスタリスク）にマスクされてクライアントへ返却されていた。
    2. WebUI フロントエンド（`app.js` の `fetchAiModels`）が画面表示時に入力欄の `value`（`********`）を取得し、`/api/ai/models?provider=gemini&apiKey=********` としてそのままクエリパラメータで送信していた。
    3. バックエンド（`app/routers/ai.py` の `get_ai_models`）は `apiKey` パラメータが渡されるとそれを最優先で利用する仕様だったため、マスク文字列 `********` をそのまま Google Gemini API に渡し、Google から `400: API key not valid` が返されていた。
- **改修内容**:
  1. **バックエンド API ルーター (`app/routers/ai.py`)**:
     - `_resolve_key(given_key, saved_key)` ヘルパーを新設。
     - `get_ai_models` および `test_ai_connection` において、`apiKey` が渡された場合でもそれが空またはマスク値 `********` である場合は保存済みの本物のAPIキー（設定ファイルまたは環境変数）へ自動フォールバックするよう改修。
  2. **AI サービス層 (`app/services/ai_service.py`)**:
     - 多層防護として、`get_gemini_models`, `get_openai_models`, `_call_gemini_with_err`, `_call_openai_with_err` において `api_key == "********"` の場合は外部APIへリクエストを送信せず、即座に安全なデフォルトモデル一覧やエラーメッセージを返却するガードを追加。
  3. **フロントエンド (`public/app.js`)**:
     - `fetchAiModels` および `btnTestAiConnection` において、入力値が `********` の場合はクエリパラメータやリクエストボディに `apiKey` を含めないよう除外処理を追加。
  4. **単体テスト (`tests/test_audit_fixes.py`)**:
     - `test_ai_models_mask_key_protection` を追加。クエリパラメータに `apiKey=********` が渡された場合でも、外部APIへのリクエストにマスク文字列が含まれず、保存済みキーで正常に応答することを検証（テスト全16件 PASS）。
  5. **実機動作検証**:
     - 実機コンテナ `SmartSpeaker-VoiceHub` を再起動し、`apiKey=********` でのモデル取得リクエスト時に保存済み本物キー（Gemini API）で動的モデル取得が 200 OK で成功し、400 エラーログが一切発生しなくなったことを実機ログレベルで確認。

## 2026-10-25 00:15 - バージョンアップ通知 & Watchtower 自動/手動アップデート機能（暴発防止GUIトグル・ラベル方式）完全実装
- **背景と課題**:
  - ユーザーより「ユーザーへのバージョンアップ通知と、自動バージョンアップについて検討したい」「Watchtowerはcloudflaredも更新してほしい。安パイをとってラベル方式で。開発環境で暴発して手戻りするのを避けるためGUIでオンオフ切り替えたい」「ヘッダーはバージョン情報と更新通知、設定に今すぐ更新と自動更新のオンオフですすめてほしい」との指示。
  - 課題と要件の整理：
    1. **開発環境での意図せぬ上書き（暴発）防止**: Watchtower の勝手な定期更新（ポーリング）を完全無効化（`WATCHTOWER_HTTP_API_PERIODIC_POLLS=false`）し、VoiceHub から指示された時だけ動作する「API待機モード」を採用。
    2. **対象コンテナの厳密な限定**: `voice-hub` と `cloudflared` のみに `com.centurylinklabs.watchtower.enable=true` ラベルを付与し、ホスト上の他のコンテナに一切影響を与えない設計を徹底。
    3. **通知の軽量・低負荷化**: 外部 GitHub Releases API への問い合わせを 24 時間（1日1回）キャッシュし、API レート制限や外部依存リスクを極小化。
- **改修内容**:
  1. **バージョン定義と設定管理 (`app/version.py`, `app/config.py`, `app/services/settings_service.py`, `app/routers/settings.py`)**:
     - `app/version.py` を新設し、現在バージョン（`v1.0.11`）および GitHub リポジトリ情報を一元定義。
     - `DEFAULT_SETTINGS` に `systemUpdate` オブジェクト（`autoUpdate: False`（既定オフ）、`autoUpdateTime: "04:00"`、`watchtowerUrl`、`watchtowerToken`、`checkIntervalHours: 24`）を追加。
     - 設定 API で `watchtowerToken` がマスク（`********`）され、保存時に誤って消去されない安全機構を実装。
  2. **アップデート監視 & Watchtower 実行サービス (`app/services/update_service.py`)**:
     - `parse_semver` および `is_newer_version` による堅牢なセマンティックバージョン比較を実装。
     - GitHub Releases API から最新バージョン情報・リリースノートを取得し、24 時間インメモリキャッシュ。手動チェック時は即時リフレッシュ。
     - Watchtower の HTTP API（`/v1/update`）を呼び出し、コンテナの即時再作成を安全にトリガーするクライアントを実装。
     - 毎分起動するバックグラウンドスケジューラーにより、自動更新が ON の場合のみ指定時刻（04:00）に更新を自動トリガー。
  3. **システム API ルーター (`app/routers/system.py`, `app/routers/status.py`, `app/core/security.py`)**:
     - `GET /api/system/version`: バージョン情報、更新有無、リリースノート、Watchtower 稼働状態を取得（未認証アクセス許可）。
     - `POST /api/system/check-update`: GitHub Releases API を強制リフレッシュして再取得。
     - `POST /api/system/update`: Watchtower への即時更新トリガー（管理者パスワード設定時は管理者セッション認証必須）。
     - `/api/status` レスポンスにも `version`, `latestVersion`, `hasUpdate` を含め、画面初期ロード時の負荷を最小化。
     - `app/core/security.py` に `is_admin_session` ヘルパーを追加。
  4. **WebUI の改修 (`public/index.html`, `public/style.css`, `public/app.js`, `public/locales/ja.json`, `public/locales/en.json`)**:
     - **ヘッダー**: バージョン表示チップ（`#headerVersionChip`）および新バージョン利用可能時に脈動アニメーションする更新通知バッジ（`#headerUpdateBtn`）を追加。
     - **更新詳細モーダル (`#modalUpdateDetails`)**: バッジクリック時に開き、リリース名・公開日・リリースノート（Markdown/テキスト）を表示し、「今すぐアップデート」ボタンを提供。
     - **設定画面「システム更新」サブタブ (`#subtab-settings-update`)**:
       - 左カラム: バージョン情報、更新確認ボタン、今すぐアップデートボタン、ターミナル手動更新コマンドのワンクリックコピー。
       - 右カラム: Watchtower 待機状態バッジ（待機中/未実行）、深夜自動バージョンアップトグル（既定: OFF）、実行時刻設定、内部パラメータ設定。
     - 日英多言語対応辞書（`ja.json`, `en.json`）に翻訳キーを追加。キャッシュバスターを `app.js?v=1.0.16` に更新。
  5. **Docker Compose & ラベル定義 (`docker-compose.yml`)**:
     - `voice-hub` および `cloudflared` サービスに `com.centurylinklabs.watchtower.enable=true` ラベルを付与。
     - `watchtower` サービス定義を追記（API待機モード: `WATCHTOWER_HTTP_API_PERIODIC_POLLS=false`、ポート 8082）。
  6. **単体テスト & 実機検証**:
     - `tests/test_update_service.py` を作成（バージョン比較、GitHub API キャッシュ、Watchtower 接続確認、更新 API 認証保護）。
     - 全 89 件の単体テストが 100% PASS（OK）することを確認。
     - 実機コンテナ `SmartSpeaker-VoiceHub` へのデプロイ・再起動を実施し、稼働確認を完了。

## 2026-10-24 23:05 - 全体再点検に伴う全13項目包括改修（トークン必須化不整合完全解消・DND特権昇格脆弱性撲滅・高速化・UI整備）
- **背景と課題**:
  - ユーザーより「全体を再確認し、不具合・不整合、効率化・高速化、あるべきものの欠落、セキュリティ上の問題（特にToken必須化に伴う影響）を精査・報告後、全部対応してほしい」との指示。
  - 精査の結果、以下の重大な課題・不整合を発見：
    1. **RFC 8414 プローブの 403 遮断**: 管理者パスワード未設定環境において、Cloudflare Tunnel 経由の `/.well-known/oauth-protected-resource` アクセスが `check_tunnel_access` で 403 遮断されていた。
    2. **【重大セキュリティ脆弱性】DND スクリプト生成時の管理者パスワード平文漏洩（特権昇格）**: `preview_dnd_script` / `download_dnd_script` が低特権の Webhook トークン等でアクセスされた際、サーバーに管理者パスワードが設定されていると、その平文管理者パスワードを生成スクリプト（VBScript / PowerShell）内に埋め込んで返却していた。
    3. **連携 API (`/api/groups`, `GET /api/history`) の認証境界不整合**: 管理者パスワード設定時、Home Assistant 等の外部システムが Webhook トークン連携ヘッダー（`x-webhook-token`）を付与していても 401 で弾かれていた。
    4. **MCP 認証ヘッダー不整合**: `x-webhook-token` や `x-api-key`、`?token=` 等のトークン認証が MCP エンドポイントの一部で一元検証されていなかった。
    5. **環境変数トークンの空文字上書きリスク**: `settings.json` にキーがない環境変数トークン（`.my.env`）運用時、`GET /api/settings` で空文字として返却され、WebUI 設定保存時にトークンが消去される危険性があった。
    6. **外部気象 API 重複呼び出しによる遅延**: `rain_alarm_service.fetch_forecast` にキャッシュがなく、複数クライアントや画面リロード時に外部 API への過剰リクエストが発生していた。
    7. **TTS ディレクトリ容量集計の負荷**: `get_cache_stats` が短スパンで全ファイルを再帰走査し、イベントループに負荷を与えていた。
    8. **Google Cast グループフォールバック時の成功判定不整合**: 個別スピーカーへの自動フォールバックが全員成功しても、グループ親の失敗により全体ステータスが一部エラー扱いになっていた。
    9. **WebUI Homebridge 設定案内カードの表示崩れ**: トークン伏字化に伴い、カード内のスライス処理で「設定済み」文字列が欠落して表示されていた。
- **改修内容**:
  1. **トークン必須化 & 認証境界の不整合解消 (`app/core/security.py`)**:
     - `check_tunnel_access` に `or path.startswith("/.well-known/")` を追加し、管理者パスワード未設定時でも RFC 8414 プローブが Tunnel 経由で正常に 200 OK を返却するよう修正。
     - `check_admin_auth` において、`/.well-known/` パスを明示的に認証バイパス対象へ追加。
     - `check_admin_auth` の MCP 認証ロジックをリファクタリングし、`x-webhook-token`, `x-api-key`, `Authorization: Bearer`, クエリパラメータ `?token=` を一元検証。
     - `INTEGRATION_PREFIXES` に `"/api/groups"` を追加し、さらに `GET /api/history` に対しても Webhook トークンによる連携読み取りを許可（`DELETE /api/history` は管理者セッション専用を維持）。
  2. **DND スクリプト特権昇格脆弱性の完全撲滅 (`app/routers/dnd.py`)**:
     - `_resolve_script_password` を実装し、有効な管理者セッション Cookie（`is_admin_session`）を保持している場合のみ管理者パスワードの埋め込みを許可。Webhook トークン等による低特権アクセス時は管理者パスワードを一切漏洩させず、低特権の Webhook トークンのみを埋め込む安全な分離を徹底。
     - `build_dnd_script` で生成されるスクリプト URL に `?token=...` クエリパラメータを標準付与し、ヘッダー遮断プロキシ環境でも確実に動作するよう改善。
  3. **トークン保護・マスクおよび設定管理の堅牢化 (`app/routers/settings.py`, `app/routers/status.py`)**:
     - `mask_sensitive_settings` において、環境変数トークンを含めた実効トークンが存在する場合、確実に `webhookToken = "********"` でマスクし、未設定時のみ空文字を返却するよう修正（誤った空文字上書きを防止）。
     - `GET /api/settings` および `GET /api/status` に `webhookTokenSource` ("settings" | "env" | "none") を追加。
     - `GET /api/status` において、管理者パスワード設定時は LAN アクセス時でも管理者セッション認証がない限り生トークンを非公開化。
  4. **位置情報取得の HTTPS 化 (`app/routers/rain_alarm.py`)**:
     - 平文 HTTP だった `ip-api.com` を `https://ipapi.co/json/` に更新し、安全なフォールバック（東京都千代田区）を維持。
  5. **効率化 & 高速化 (`app/services/rain_alarm_service.py`, `app/services/tts_service.py`, `app/services/speech_service.py`)**:
     - `rain_alarm_service.py`: 60 秒のインメモリキャッシュ (`_forecast_cache`) を導入し、同一座標に対する外部気象 API の重複呼び出しを削減。
     - `tts_service.py`: `get_cache_stats` を `os.scandir` に最適化し、120 秒 TTL キャッシュを導入してイベントループブロッキングを低減。
     - `speech_service.py`: Google Cast ネイティブグループ失敗後に個別フォールバックが全員成功した場合、元グループを `fallback_recovered` とマークし、全体ステータスを `success` と正しく判定。
  6. **WebUI 表示改善 (`public/index.html`, `public/app.js`)**:
     - 設定画面で Webhook トークンが環境変数（`.my.env`）由来の場合に「⚙️ 環境変数 (.my.env) より読み込み中」の注記を表示。
     - Homebridge 設定案内カードの伏字トークンスライス処理を修正し、「🔒 設定済み (認証保護 有効)」とスマート表示。
     - キャッシュバスターを `app.js?v=1.0.15` に更新。
  7. **単体テスト拡充 & 実機コンテナ検証**:
     - `tests/test_audit_fixes.py` に DND スクリプト特権昇格防止、Tunnel 経由の `.well-known` アクセス、MCP `x-webhook-token` 認証、`/api/groups` および `GET /api/history` 連携認証、降雨予測キャッシュのテストを追加。
     - `tests/test_dnd_scripts.py` のテストケースを新仕様に合わせて更新。全85件のテストが 100% PASS することを確認。
     - 実機コンテナ `SmartSpeaker-VoiceHub` へのファイル反映・コンテナ再起動を実施し、バックグラウンドワーカー正常起動・ヘルスチェック（HTTP 200）を確認。

## 2026-10-24 18:20 - Webhook Token 未設定化原因究明 & ログエラー4項目（降雨500・Google Cast集約全滅・OAuth404・トークン重複定義）完全対処
- **背景と課題**:
  - ユーザーより「ログ見てエラーに対処してほしい」「あと、WebhookのTokenがいきなり未設定になったっぽいんだけど、それも調査して」との依頼。
  - **原因調査の結論**:
    1. **Webhook Token がいきなり未設定になった原因**:
       - `app/routers/status.py` の `get_system_status()` において、トークン取得に `settings_manager.get_webhook_token()` ではなく `settings.webhook_token`（環境変数のみ）を参照していた。
       - さらに `token_str = None if is_tunnel else ...` の処理により、Cloudflare Tunnel 経由（外部URL `webhook.kit-a.net`）からアクセスした際、管理者セッション認証済みであっても強制的に生トークンが `None` で返されていた。
       - フロントエンド `app.js` では `/api/status` の `webhookToken` を入力欄 `txtWebhookTokenVal` に反映していたため、外部からアクセスしたりリロードした際にトークン欄が空になり、プレースホルダー「トークン未設定」が表示されていた。
       - WebUIで設定保存した際に空文字で上書き保存される危険があった。
       - 加えて `app/core/security.py` 内で `def validate_webhook_token` が途中で重複定義されていた。
    2. **ログエラー**:
       - `GET /api/rain-alarm/forecast`: 外部気象API（Yahoo!/Open-Meteo）の一時的タイムアウトや障害時に `raise HTTPException(status_code=500)` を投げていたため HTTP 500 が発生していた。
       - `Google Cast ALL failed (192.168.11.176:32094)`: 宛先「ALL」指定時、Google Cast ネイティブグループ（`cast_group`）集約が走り、グループリーダー1台に集約された結果、そのソケット接続タイムアウトで個別スピーカーにも送られず家中への発話が全滅していた。
       - `/.well-known/oauth-protected-resource`: Claude Desktop / Cursor 等の MCP クライアントが RFC 8414 / RFC 9728 に基づき認可メタデータをプローブした際、エンドポイント未定義により 404 WARNING が多発していた。
- **改修内容**:
  1. **Webhook トークン取得の一元化 & 認証連動 (`app/routers/status.py`, `app/core/security.py`, `app/services/mcp_service.py`, `app/routers/dnd.py`)**:
     - すべてのエンドポイント・ミドルウェアで `settings_manager.get_webhook_token()` を使用して一元取得するように統一。
     - `/api/status` において、管理者セッション認証済み（Cookie `auth_token`）の場合は Cloudflare Tunnel 経由でも正常にトークン文字列を返却し、未認証外部アクセス時のみ安全に隠蔽（`None`）するよう改善。
     - `hasWebhookToken` は常に実効トークンの有無（`bool(effective_token)`）を正確に返却。
     - `app/core/security.py` の重複した `validate_webhook_token` コードを削除・クリーンアップ。
  2. **WebUI フロントエンドのトークン保護 & バッジ動的連動 (`public/app.js`, `public/index.html`)**:
     - `/api/status` のレスポンスに基づき、`webhookTokenBadge` を「認証保護 有効 (緑)」または「認証 未設定 (灰色)」へリアルタイム連動。
     - 外部未認証アクセス等でトークン文字列が非公開の場合でも、設定済みの場合は「🔒 トークン設定済み (管理者ログインで表示・変更可能)」を表示して未設定との誤認を防止。
     - トークン設定済みの状態で空文字保存しようとした場合、誤消去防止の確認ダイアログを表示する安全ガードを追加。
     - キャッシュバスターを `app.js?v=1.0.14` に更新。
  3. **降雨予測 API のグレースフルハンドリング (`app/routers/rain_alarm.py`)**:
     - 外部API一時障害時は 500 を投げず、WARNING ログを出力した上で安全なフォールバックレスポンス（空タイムライン、エラー詳細付き 200 OK）を返却するように強化。
  4. **Google Cast ネイティブグループ失敗時の自動個別フォールバック (`app/services/speech_service.py`)**:
     - `resolve_targets` で Google Cast グループに集約する際、集約前の個別 Google スピーカー一覧を `_fallback_members` として保持。
     - ディスパッチ時にグループへの送信が失敗（タイムアウト等）した場合、自動的に個別スピーカー群へフォールバックして即座に並列再送する二重安全機構を実装。全室発話の全滅を完全防止。
  5. **MCP OAuth Protected Resource Metadata エンドポイント実装 (`app/routers/mcp.py`)**:
     - `/.well-known/oauth-protected-resource` および `/mcp/sse` エンドポイントを定義し、Claude Desktop や Cursor 等の MCP クライアントからのプローブに RFC 8414 / RFC 9728 準拠のメタデータを返却。404 WARNING を完全解消。
  6. **テスト拡充 & コンテナ再起動**:
     - `tests/test_audit_fixes.py` に新規4件のテストケースを追加。
     - クリーンな一時コンテナ内で全80件のテストを実行し、100% PASS（OK）を確認。
     - 実機コンテナ `SmartSpeaker-VoiceHub` を再起動し、正常稼働を確認。

## 2026-10-24 13:55 - GitHub Actions CI 単体テスト実機依存不具合修正 & v1.0.11 再リリース
- **背景と課題**:
  - ユーザーより「githubでビルドアクションが失敗してるようなので確認して、リリースしてほしい」との依頼。
  - GitHub Actions の実行ログ（ID: 40062148516 / 40062147431）を確認したところ、`Run Unit Tests (Docker)` ジョブにおいて `tests/test_speech_dispatch.py` の `test_deduplication_skip_recorded_in_history` が `AssertionError: False is not true (res1.get("success") == False)` で失敗していた。
  - **原因**:
    - `test_deduplication_skip_recorded_in_history` 内で `speech_service.speak` を実行して重複排除と履歴記録をテストしていたが、TTSおよびデバイス取得のみモックし、スピーカーへの実際の送信処理（`cast_service.play_audio`）のモックが抜けていた。
    - ローカル環境では LAN 内に実機 Google Cast スピーカー（192.168.11.97）が存在していたため偶然接続が成功してテストを通過していたが、外部ネットワークから完全に隔離された Docker CI コンテナ環境では実機へのソケット通信がタイムアウト/失敗し、`res1.get("success")` が `False` となって CI が中断していた。
- **改修内容**:
  1. **単体テストの外部ネットワーク完全遮断 & モック適用 (`tests/test_speech_dispatch.py`)**:
     - `patch("app.services.speech_service.cast_service.play_audio", new_callable=AsyncMock, return_value=True)` を追加。
     - 宛先スピーカーを `targets=["192.168.1.50"]` で明示固定し、ローカル実機設定ファイル（`settings.json` の `defaultSpeaker` 等）に依存せず確実にモックされた `cast_service.play_audio` が呼ばれるよう変更。
     - テスト実行時間が実機接続待ち（約5秒）から **0.045秒** に劇的に高速化。
  2. **テスト & 記録**:
     - 全77件の単体・結合テストを実行し 100% PASS を確認。
     - `logs/past-mistake-title.md` および `logs/past-mistake.md` に再発防止策を追記。
  3. **コミット & タグ更新・再プッシュ**:
     - 修正をコミットし、Git タグ `v1.0.11` を更新してリモートへ push。CI/CD パイプラインを再起動してリリース。

## 2026-10-24 13:23 - v1.0.11 正式リリース & ドキュメント総合整備
- **背景と課題**:
  - ユーザーより「必要に応じてDoc類を整備して、リリースして」との依頼。
  - 雨雲レーダー凡例追加、尺度ズーム不具合修正、防災速報コールバック例外修正、音声発言履歴パイプラインの全面堅牢化、および履歴フィルターピル追加に伴うドキュメント整備と正式タグリリースを実施。
- **改修内容**:
  1. **CHANGELOG.md**:
     - `## [1.0.11] - 2026-10-24` を新設。追加・新機能（雨雲レーダー凡例、発言履歴フィルターピル）および修正・堅牢化（尺度不具合解消、防災速報例外解消、全音声発話パイプライン履歴記録の網羅）を詳細に記録。
  2. **詳細仕様書 (MANUAL.md & MANUAL-en.md)**:
     - 第6章に「6.6 雨アラーム・雨雲接近通知および雨雲レーダー (Japan Only)」を新設。雨雲自動監視、気象庁高解像度降水ナウキャスト重畳、`maxNativeZoom: 10` による自動拡大描画、公式配色8段階グラスモーフィズム凡例、スマートホーム防災トリガー連動仕様を明記。
     - 第12章「12.2 発言履歴」を拡充。送信元フィルターピル機能、および実行ステータス（成功、DND抑制、重複排除スキップ、宛先未解決・TTSエラー）の記録仕様を追記。
  3. **README.md & README-en.md**:
     - 「直感的な Web 画面とリアルタイム操作」セクションに、送信元別履歴フィルターおよび気象庁公式配色凡例付き雨雲レーダー重ね合わせマップの機能概要を反映。
  4. **テスト & リリース**:
     - 単体・統合テスト全77件を実行し 100% PASS を確認。
     - Git コミット作成 (`feat: add rain radar legend, fix zoom scale, fix disaster speech, and harden speech history pipeline (v1.0.11)`)。
     - Git タグ `v1.0.11` を作成し、リモート（`origin/main`, `origin/v1.0.11`）へ push。
     - GitHub Actions による CI/CD パイプライン（Unit Tests、Docker Hub マルチアーキテクチャイメージビルド＆プッシュ、GitHub Releases 作成）の起動を確認。

## 2026-10-24 13:16 - 雨雲レーダーの尺度・ズーム表示不具合修正 (v1.0.13)
- **背景と課題**:
  - ユーザーより「雨雲レーダーがデフォルトの尺度だと表示されない。2個分くらいマイナスで引くと表示される」との報告。
  - **原因調査**:
    - 気象庁公式の「高解像度降水ナウキャスト（`hrpns`）」タイル画像は、配信仕様上の最大ズームレベルが `10`（約 1:500,000）となっている。
    - ズームレベル 11 や 12 の URL リクエストに対しては、気象庁サーバーから雨雲データを含まない透明な空画像（334 bytes）が返却される仕様であった。
    - 地図の初期ズームレベルが 12 のままで、かつ Leaflet の `tileLayer` にネイティブズーム制限が設定されていなかったため、初期表示時および拡大時にズーム 11/12 の空タイルを読み込んで雨雲が表示されず、地図を2段階マイナス（12 -> 10）に縮小した時だけ生画像が存在して表示されていた。
- **改修内容**:
  1. **Leaflet タイルレイヤーの `maxNativeZoom: 10` 設定 (`public/app.js`)**:
     - `rainRadarLayer`（気象庁タイル）のオプションに `maxNativeZoom: 10, maxZoom: 18, minZoom: 4` を設定。
     - これにより、ユーザーがズームレベル 11 以上（デフォルトの尺度や拡大時）にズームしても、Leaflet がレベル 10 のタイルを自動的にオーバースケール（高解像度ストレッチ補間）して拡大描画するようになり、どの尺度でも雨雲が鮮明に重畳表示される。
  2. **初期ズームの最適化 (`public/app.js`)**:
     - 地図初期化時のデフォルトズームを広域と局地が見渡しやすい `zoom: 11` に最適化。
  3. **キャッシュバスター更新 (`public/index.html`)**:
     - ブラウザキャッシュを即座に更新するため、`app.js?v=1.0.13` に更新。
  4. **テスト & 実機検証**:
     - 全77件の単体・統合テスト（`tests/`）を実行し 100% PASS を確認。
     - 実機コンテナ `SmartSpeaker-VoiceHub` を再起動し、起動時エラー皆無、WebUI の `maxNativeZoom: 10` 反映および実際の雨雲接近音声配信の正常動作を確認。

## 2026-10-24 13:05 - 雨雲レーダー凡例追加 & 防災・雨アラーム・全音声発話の履歴記録総点検と堅牢化 (v1.0.12)
- **背景と課題**:
  - ユーザーより「雨アラーム・雨雲接近通知 (Japan Only)の雨雲レーダー重ね合わせに凡例を追加したい」との要望。
  - 同時に「雨アラーム等で発言した内容が履歴に残っていない原因の調査（発言エラーなのか、発言自体されていないのか）」および「前回更新後のログエラー調査」「他にも履歴に残らないケースがないかの総チェック」の依頼。
  - **ログ調査で判明した重大不具合**:
    1. `[ERROR] [VoiceHub.Disaster] Speech dispatch error in disaster: lifespan.<locals>.on_disaster_speech() got an unexpected keyword argument 'source'` (TypeError):
       `disaster_service`（気象警報・地震情報等）から `source="disaster"`, `source_label="防災速報"` 等のキーワード引数を渡された際、`app/main.py` の `on_disaster_speech` が `**kwargs` を受け取っていなかったため例外で落ち、音声が再生されず履歴にも残っていなかった。
    2. 雨アラームの自動監視について、設定ファイル（`settings.json`）の `rainAlarm.enabled` が `false`（無効）となっていたため、定期監視による自動検知・発言自体が行われていなかった。
    3. `rain_alarm_service._speak_alert` 内で `dnd_service.is_in_dnd()` による直接 return が行われていたため、DND おやすみモード発動時に `speech_service.speak` をバイパスし、DND 抑制履歴（`status: "suppressed"`）にすら残らない状態だった。
    4. 全体精査により、重複排除（Deduplication）によるスキップ時、対象スピーカー未解決（No valid target devices found）時、および TTS 音声合成エラー時にも `record_history` が呼ばれずに return され、ユーザー視点で「通知が消えた」ように見える履歴漏れが存在していた。
- **改修内容**:
  1. **雨雲レーダー重ね合わせの凡例追加 (`public/app.js`, `public/style.css`, `public/locales/ja.json`, `public/locales/en.json`)**:
     - 気象庁「高解像度降水ナウキャスト（hrpns）」公式カラーテーブル（8段階: 0〜1, 1〜5, 5〜10, 10〜20, 20〜30, 30〜50, 50〜80, 80+ mm/h）に 100% 準拠した凡例コンポーネントを新設。
     - Leaflet コントロール（`bottomleft`）として地図上に美しくフロート表示（ダーク・グラスモーフィズムデザイン、`backdrop-filter: blur(8px)`、角丸、陰影）。
     - 各カラーバーにマウスホバーで「猛烈な雨」「非常に激しい雨」等の説明ツールチップを表示。
     - 「🌦️ 雨雲レーダー重ね合わせ」トグルボタンの ON/OFF に完全連動し、レーダー非表示時は凡例も非表示化。
     - 言語切り替えイベント（`voicehub:language-changed`）と連動し、日英切り替えにリアルタイム対応。
  2. **防災速報コールバックの引数エラー解消 (`app/main.py`)**:
     - `on_disaster_speech` の引数に `**kwargs` を追加し、`speech_service.speak` へ安全に転送。地震速報や気象警報で例外が起きず確実に発話・履歴記録されるよう修正。
  3. **音声発声・履歴記録パイプラインの全面堅牢化 (`app/services/speech_service.py`, `app/services/rain_alarm_service.py`, `app/services/history_service.py`)**:
     - `rain_alarm_service._speak_alert`: DND 先回り return を撤廃し、`speech_service.speak` に委任。DND 中でも履歴に「DND 抑制（おやすみモード）」または保留キューとして確実に記録。
     - 重複排除スキップ時: `status: "skipped"`, `statusMessage: "直前の同一通知から XX 秒以内のため重複スキップしました"` で履歴記録。
     - 宛先スピーカー未解決時: `status: "error"`, `statusMessage: "対象スピーカーが見つかりませんでした (No valid target devices found)"` で履歴記録。
     - TTS 合成例外時: `try...except` で安全に捕捉し、`status: "error"`, `statusMessage: "音声合成に失敗しました (エラー内容)"` で履歴記録。
     - `history_service.py`: `derive_source_label` に `rain_alarm`, `disaster`, `mcp`, `mqtt`, `scheduled_speech`, `system` を追加。
  4. **WebUI 発言履歴フィルターの拡充 (`public/index.html`, `public/app.js`, `public/style.css`, `public/locales/ja.json`, `public/locales/en.json`)**:
     - 履歴画面のフィルターピルに「🌧️ 雨アラーム」と「🚨 防災速報」の専用ボタンを追加。
     - 送信元バッジ（`source-rain_alarm`, `source-disaster`, `source-mcp`, `source-mqtt`, `source-scheduled_speech`）のカラー・スタイルを新規定義。
     - キャッシュバスターを `app.js?v=1.0.12`, `style.css?v=3.3` に更新。
  5. **テスト & 実機検証**:
     - `tests/test_speech_dispatch.py` を新設し、防災速報・雨アラーム・重複スキップ・宛先エラー・TTSエラー・ラベル導出の単体テストを網羅。
     - 全77件のテストを実行し、100% PASS を達成。
     - 実機コンテナ `SmartSpeaker-VoiceHub` を再起動し、起動時エラー皆無および最新静的アセットの正常配信を確認。

## 2026-10-23 12:25 - ログインセッション永続化 & WebUI 401 自動検知・モーダル再ログイン対応 (v1.0.10)
- **背景と課題**:
  - コンテナやプロセスの再起動後、ブラウザ側に有効期限30日の Cookie（`auth_token`）が残っているにもかかわらず、サーバー側セッションがインメモリ（`ACTIVE_SESSIONS = set()`）であったためセッション情報がクリアされ、未認証（401）状態となる問題。
  - WebUI 画面を開いたまま再起動を跨いだ際、フロントエンドが 401 エラーを検知できず、バックグラウンドの DND ポーリングが 538 回連続で 401 警告をサーバーログに出力し続けるとともに、ユーザーが「音声・機能拡張」で「システム設定を保存」ボタンを押した際に「設定保存エラー: 設定保存失敗」とだけ表示され原因が分からない不親切な状態が発生していた。
- **改修内容**:
  1. **ログインセッションのファイル永続化 (`app/core/security.py`, `data/sessions.json`)**:
     - `PersistentSessionSet` クラスを新設。従来の `ACTIVE_SESSIONS`（set インターフェース）と 100% の後方互換性を保ちながら、セッション情報（トークン、作成日時、有効期限 30日）を永続ボリューム配下の `data/sessions.json` へアトミック保存・同期。
     - サーバー再起動時でも `data/sessions.json` から有効期限内のセッションを自動ロードし、再起動を跨いでも再ログイン不要で作業を継続可能に改善。
     - 期限切れセッションの自動パージおよびパスワード変更時の一括クリア（`clear()`）に対応。
  2. **フロントエンドでの 401 Unauthorized 自動検知 & ログインモーダル表示 (`public/app.js`)**:
     - グローバル `window.fetch` インターセプターを導入。API レスポンスで 401 が返却された際、自動的にログインモーダルを開き「セッションの有効期限が切れたか、管理者認証が必要です。再度ログインしてください。」と提示。
     - 認証切れ表示中は DND ポーリングなどバックグラウンド通信を一時休止（pause）させ、サーバーログへの 401 警告連打を根絶。
     - パスワード入力・再ログイン成功時にモーダルを閉じ、リアルタイム同期（`initEventSource`）と画面データを自動再同期。
     - 「システム設定を保存」処理で 401 を明示的にハンドリングし、具体的な案内トーストを表示。
  3. **キャッシュバスター更新 (`public/index.html`)**:
     - `app.js?v=1.0.10` に更新。
  4. **テスト & 実機検証**:
     - `tests/test_session_persistence.py`（4件）を新規作成し全件合格。
     - 既存全単体テスト（71件）が 100% PASS することを確認。
     - 実機コンテナ `SmartSpeaker-VoiceHub` 上でログイン、セッションファイル保存、コンテナ再起動後も同じ Cookie で `PUT /api/settings` が 200 OK で成功することを実証確認。

## 2026-10-23 03:55 - CI テスト自動化・NoneType 例外修正 & SSE リアルタイム同期正式リリース (v1.0.9)
- **背景と課題**:
  - GitHub Actions CI（`Run unit & smoke tests inside container`）にて、初期状態（クリーンな Docker 環境）でテストを実行した際、`check_admin_auth` 内の `settings_manager.get().get("webhookToken", "").strip()` で `AttributeError: 'NoneType' object has no attribute 'strip'` が発生しパイプラインが停止していた。
  - Web UI 上のヘッダーにあるミュートボタンおよび DND バナーを、Homebridge や外部 API、外部スクリプト（G HUB / Stream Deck）から切り替えた際にリロード不要で 0.01 秒自動反映する SSE（Server-Sent Events）機能の正式統合。
- **改修内容**:
  1. **未設定キー取得時の `NoneType.strip()` 例外耐性強化 (`app/core/security.py`, `app/services/mcp_service.py`, `app/services/rain_alarm_service.py`, `app/routers/onvif_dlna.py`, `app/services/ai_service.py`)**:
     - `dict.get(key, "")` で値が `None`（`null`）の場合にデフォルト値が効かず `None` が返る仕様に対応し、`(dict.get(key) or "").strip()` に統一して例外を完全撲滅。
  2. **SSE イベント配信サービス新設 (`app/services/event_service.py`)**:
     - `asyncio.Queue` を用いたパブリッシュ/サブスクライブ（Pub/Sub）モデルのイベント配信基盤を新規実装。
     - 接続中クライアントへのリアルタイムプッシュ通知（`broadcast`）と、プロキシ/ブラウザ切断を防ぐ 15 秒周期のキープアライブコメント（`: keepalive\n\n`）送信、切断時の自動キュー破棄を完備。
  3. **SSE エンドポイント新設 (`app/routers/events.py`, `app/main.py`, `app/core/security.py`)**:
     - `GET /api/events`（および `/api/events/stream`）を新設。
     - `text/event-stream` レスポンス（`Cache-Control: no-cache`, `X-Accel-Buffering: no`）。
     - 初回接続時に現在の最新 DND ステータスを即時プッシュ返却。
     - 管理者パスワード設定時および Webhook トークン（URL クエリ `?token=`、Cookie `auth_token`）双方のセキュアな認証を担保（`INTEGRATION_PREFIXES` に追加）。
  4. **バックエンド状態変更時の即時ブロードキャスト連携 (`app/routers/dnd.py`, `app/routers/settings.py`, `app/services/dnd_service.py`)**:
     - `mute_dnd`、`unmute_dnd`、`quick_dnd` 実行時に `event_service.broadcast("dnd_status", ...)` を即時呼び出し。
     - `dnd_service.tick()` での定期監視（定時スケジュールやカレンダー連動による発動・終了）時にも状態変化を検知して自動ブロードキャスト。
     - `update_settings` での DND 設定更新時にも最新ステータスを即座にプッシュ。
  5. **フロントエンド連携 & 画面復帰検知 (`public/app.js`, `public/index.html`)**:
     - ブラウザ標準の `EventSource` を用いた `initEventSource()` を実装。`dnd_status` イベント受信時に `renderDndStatus()` を即時トリガー。
     - バックグラウンド切断や未対応環境を考慮し、従来の 15 秒ポーリングをフォールバックとして温存。
     - スマホスリープ復帰時や別タブから戻った際にも `document.addEventListener('visibilitychange')` で最新ステータスへ即時再同期。
     - キャッシュバスターを `app.js?v=1.0.9` に更新。
  6. **テスト & 実機検証**:
     - `tests/test_sse_events.py` を新規作成、および `tests/test_audit_fixes.py` のクリーン実行を強化。
     - クリーンコンテナ環境で全 67 件の単体テストが 100% PASS することを確認。
     - 実機コンテナ `SmartSpeaker-VoiceHub` 上でバックグラウンド接続および API ミュート/解除の 0.01 秒プッシュ受信を実証確認。

## 2026-10-22 23:35 - 外部デバイス連携 (Logitech G HUB / Stream Deck 等) VBScript/PowerShell 改善 & スマートホーム認証連動 (v1.0.10)
- **背景と課題**:
  1. **Logitech G HUB での VBScript 起動不全**:
     - Logitech G HUB の「アプリケーションの起動」機能で生成された `.vbs` スクリプトを指定しても動作しない問題。
     - **原因の特定**:
       - 動作ログ（`/logs/container.log`）を調査した結果、G HUB 側からのリクエストがサーバーに一切到達していなかった。
       - G HUB は Windows API（`CreateProcess`）で実行可能ファイル（`.exe`）を起動する仕様となっており、スクリプトファイル（`.vbs` や `.ps1`）を直接指定しても OS 側でインタープリタが自動起動されず無視される。
       - また、従来の VBScript 内でサーバー用途の `MSXML2.ServerXMLHTTP` が使用されていたため、クライアント Windows 環境で WinHTTP のプロキシ名前解決やソケット制限に引っかかるリスクがあった。
  2. **スマートホーム連携機器 (Homebridge 等) の 401 Unauthorized エラー**:
     - ログ調査により、Homebridge（`192.168.11.248`）から 30 秒ごとに送られていた防災トリガー監視リクエスト（`GET /api/disaster/triggers`）が `401 Unauthorized (Admin password required)` で拒絶されていたことを検知。
     - Web GUI から管理者パスワード（`ADMIN_PASSWORD`）が設定された場合、`/api/` 以下のエンドポイント全体に管理者パスワード認証が要求され、Homebridge が送付していた Webhook トークン（`?token=...`）が連携エンドポイントで受け付けられていなかった。
- **改修内容**:
  1. **スマートホーム・外部デバイス連携エンドポイント認証の緩和 (`app/core/security.py`)**:
     - `check_admin_auth` に `INTEGRATION_PREFIXES`（`/api/dnd/`, `/api/disaster/triggers`, `/api/devices`, `/api/status`）を追加。
     - 管理者パスワードが有効化されている場合でも、設定済みの Webhook トークン（Bearer ヘッダー、`x-webhook-token`、`x-api-key`、または URL クエリ `?token=`）が合致していれば正規の外部連携として安全にアクセスを許可するよう改善。
     - 実機ログにて Homebridge からの `GET /api/disaster/triggers?token=***` が即座に `HTTP 200 OK` に転換したことを確認。
  2. **DND 外部デバイス連携スクリプト生成の堅牢化 & PowerShell オプション新設 (`app/routers/dnd.py`)**:
     - **VBScript (`.vbs`)**: クライアント環境で最も安定して動作する `MSXML2.XMLHTTP` を最優先にし、利用不可環境向けに `WinHttp.WinHttpRequest.5.1` への自動フォールバックを実装。ボディなし POST で不要だった `Content-Type` ヘッダー付与を撤廃。
     - **PowerShell (`.ps1`)**: 近年の Windows 10/11 で標準かつ信頼性の高い PowerShell スクリプト生成オプションを新設（`Invoke-RestMethod` によるサイレント実行）。
     - スクリプト内に現在の管理者パスワード（`x-admin-password` ヘッダー）または Webhook トークン（`?token=` クエリ）が自動的に埋め込まれるよう強化。
  3. **WebUI ＆ 多言語対応の更新 (`public/index.html`, `public/locales/ja.json`, `public/locales/en.json`)**:
     - 外部デバイス連携セクションのスクリプト形式選択に「⚡ PowerShell (.ps1)」を追加。
     - Logitech G HUB の折りたたみ設定手順（Instruction）に、確実に動作させるための「アプリケーション: `C:\Windows\System32\wscript.exe`（または `powershell.exe`）」と「引数: `"C:\Path\To\voicehub_dnd_toggle.vbs"`」の指定方法を日英完全対称で明記（`data-i18n-html="true"` 準拠）。
  4. **単体テスト & 実機検証**:
     - `tests/test_dnd_scripts.py` を更新し、全64件の単体テスト合格を確認。
     - 稼働中コンテナ `SmartSpeaker-VoiceHub` を再起動し、実機疎通（ヘルスチェック HTTP 200、Homebridge 連携 HTTP 200）を確認。

## 2026-10-22 23:10 - Webhook 認証トークンおよび全コピーボタンのクリップボードフォールバック対応 (v1.0.9)
- **背景と課題**:
  - Web GUI の「Webhook & Tunnel」画面において、「Webhook 認証シークレットトークン (WEBHOOK_TOKEN)」のコピーボタン（`btnCopyWebhookToken`）をクリックしても動作しないという報告。
  - **原因の特定**:
    1. 最新ブラウザの仕様により、LAN IP アドレス（例: `http://192.168.11.244:8080`）などの HTTP 環境（非 Secure Context）では `navigator.clipboard` が `undefined` となり、`navigator.clipboard.writeText` 呼び出し時に `TypeError` が発生して処理が停止していた。
    2. トークンが未設定（空文字）の場合のガード判定で何のフィードバック（トースト）も出ず、無反応に見えていた。
    3. 同様に、履歴コピー、ビルダーコードコピー、Homebridge 設定コピー、MCP 設定コピー等でも同様の問題が発生していた。
- **改修内容**:
  1. `public/app.js`:
     - 安全なクリップボードコピー関数 `copyTextToClipboard(text)` を実装：
       - Secure Context（HTTPS / localhost）では標準の `navigator.clipboard.writeText` を優先実行。
       - 非セキュアな HTTP（LAN IP）環境や API 非対応環境では、画面外に不可視の `<textarea>` を生成して `document.execCommand('copy')` を行うフォールバックを完備。
     - `btnCopyWebhookToken` のイベントリスナーを改修：
       - トークンが未設定の場合は「Webhook 認証トークンが未設定です」と警告トーストを表示。
       - コピー成功時にはボタン表示を 2 秒間「✓ コピー完了」に切り替え、成功トーストを表示。
     - アプリ全体の他のコピーボタン（発言履歴コピー、コードビルダーコピー、Homebridge コマンド/JSON コピー、MCP 設定コピー）もすべて `copyTextToClipboard` 経由に統一・堅牢化。
     - `TOAST_STATIC_EN` に `"Webhook 認証トークンが未設定です"` の多言語対応キーを追加。
  2. `public/index.html`:
     - ブラウザキャッシュ対策として `app.js` のクエリパラメータを `app.js?v=1.0.8` に更新。

- **背景と課題**:
  - Gemini の動的取得と同様に、OpenAI も公式 API から利用可能なモデル一覧を動的に取得したいという要望に対応。
  - テキスト生成・要約に無関係なモデル（音声系、画像生成、テキスト埋め込み、モデレーション、リアルタイム、微調整モデル、古い日付スナップショット版）が混入しないよう厳格に除外する必要があった。
  - 主力モデル（`gpt-4o-mini`, `gpt-4o`, `o3-mini`, `o1` 等）を日本語ラベル付きで優先ソートし、1時間のインメモリキャッシュ保持、通信失敗時の安全フォールバック、および古い廃止モデル指定時の自動補正を完備。
- **改修内容**:
  1. `app/services/ai_service.py`:
     - `DEFAULT_OPENAI_MODELS` を定義（`gpt-4o-mini`【高速・推奨】, `gpt-4o`【高性能・推奨】, `o3-mini`【最新推論・推奨】, `o1`, `gpt-4-turbo` 等）。
     - `get_openai_models(api_key, force_refresh)` を新規実装。
       - `https://api.openai.com/v1/models` を非同期呼び出し。
       - 正規表現およびキーワードによる厳格フィルタリング（`realtime`, `audio`, `whisper`, `dall-e`, `embedding`, `moderation`, `ft:`, 日付スナップショット版を除外）。
       - 推奨順ソートおよび日本語推奨ラベルの付与。
       - 1時間インメモリキャッシュ（`_openai_models_cache`）の実装（CodeQL #28 対策としてハッシュ化を避け直接比較）。
       - APIキー未設定や401エラー等の障害時には `DEFAULT_OPENAI_MODELS` へ自動フォールバック。
     - `_call_openai_with_err`:
       - 動的モデル一覧を用いて指定モデル名を検証し、非推奨・存在しないモデルの場合は自動的に最新推奨モデル（`gpt-4o-mini`）へ自己修復・動的補正して呼び出すロジックを統合。
  2. `app/routers/ai.py`:
     - `GET /api/ai/models` で `provider == "openai"` の場合に `ai_service.get_openai_models` を呼び出すよう拡張。
     - `forceRefresh` および `apiKey` パラメータに対応。
  3. 単体テスト (`tests/test_audit_fixes.py`):
     - `test_dynamic_openai_models` を追加し、正常取得、不要モデル除外、ソート順、キャッシュ動作、APIキー無効時フォールバック、エンドポイント疎通を網羅（全63件テスト合格）。
  4. ドキュメント最新化:
     - `MANUAL.md` / `MANUAL-en.md`（第2章ヘルスチェック、第7章AI連携、第10章MCP包括保護）
     - `CHANGELOG.md`（1.0.8 新設）
  5. 稼働中コンテナ `SmartSpeaker-VoiceHub` へのファイルコピーおよび再起動・疎通確認完了。

## 2026-10-22 22:38 - GitHub Code scanning (CodeQL) Alert #28 解消 (v2.0.4)
- **対象アラート**:
  - Alert #28: `py/weak-sensitive-data-hashing` (`app/services/ai_service.py:205`)
  - 内容: `get_gemini_models` 内で `api_key` に対して `hashlib.sha256()` を呼んでいたため、「パスワード・秘密情報の保存/照合に低コストなハッシュアルゴリズムが使われている」と誤検知されていた。
- **対応内容 (`app/services/ai_service.py`)**:
  - `_gemini_models_cache` の照合ロジックから `hashlib.sha256` によるハッシュ計算を全廃。
  - プロセス内インメモリキャッシュとして `api_key` の直接文字列比較に移行し、不要となった `import hashlib` を削除。
  - CodeQL の誤検知を根本解消し、単体テスト全62件合格およびコンテナへの反映を完了。

## 2026-10-22 22:30 - WebUI Webhookビルダー & Gemini連携ガイドの動的URL・トークン解決 (v2.0.3)
- **背景と課題**:
  1. **1枚目 (Webhook ビルダー)**: 送信先エンドポイントの「🏠 宅内 LAN」ラジオボタンに `http://<SERVER_IP>:8080/api/say` とプレースホルダーが残ったままになっていた。また、Tunnel 経由で開いている場合でも宅内LANが初期選択されていた。
  2. **2枚目 (Gemini / AI 連携ガイド)**: プロンプト例が `POST http://<サーバーIP>:8080/api/say` の固定プレースホルダーになっており、外部クラウド（Gemini Web/Gems）から呼ぶために必須となる公開 URL や認証トークンヘッダーが欠落していた。
  3. **3枚目 (cURL コマンド生成)**: IP は動的解決されていたものの、Tunnel 経由時やパスワード設定時に必要なトークンヘッダー（`Authorization: Bearer <token>`）が、トークン未取得・マスキング時に出力されず、コピーしたコマンドが 401 Unauthorized で失敗する潜在課題があった。
- **修正内容 (`public/index.html`, `public/app.js`)**:
  - `fetchServerStatus`:
    - `builderLanUrlLabel` をサーバー実 IP（`http://${data.serverIp}:${data.port}/api/say`）で動的置換。
    - Cloudflare Tunnel 経由で WebUI を開いている場合は、Webhook ビルダーのラジオボタン初期選択を自動的に「Cloudflare Tunnel」に切り替え。
  - `updateBuilderCode`:
    - `baseUrl` 生成時のローカル IP 解決において、ドメインアクセス時に引きずられないよう `state.serverInfo.serverIp` を最優先。
    - Tunnel 接続時またはパスワード設定時、トークンが未取得または伏字（`********`）の場合は `YOUR_WEBHOOK_TOKEN` プレースホルダーで認証ヘッダーを明示出力。
    - コピーボタン押下時、`YOUR_WEBHOOK_TOKEN` が含まれていればトークン置き換えを促す案内トーストを表示。
  - `updateGeminiGuidePrompt` を新設:
    - サーバー環境（Tunnel ドメインの有無、実際の登録スピーカー名、Webhook トークン）に連動して、Gemini Gems/カスタム指示向けのプロンプト例を完全に動的生成。
    - Webhook トークン入力欄（`txtWebhookTokenVal`）のリアルタイム入力イベントにも連動。
  - 実機コンテナ `SmartSpeaker-VoiceHub` 内の `/app/public/index.html` および `/app/public/app.js` に変更を即時反映完了。

## 2026-10-22 22:20 - WebUI MCP設定スニペットの宅内LAN/インターネットURL生成不具合の解消 (v2.0.2)
- **背景と課題**:
  - Cloudflare Tunnel 経由で WebUI（`https://webhook.kit-a.net`）を開いている状態で、MCP設定画面（Claude Desktop / Cursor）の接続環境を「宅内 LAN (ローカル)」にした際、生成される URL が `location.host` に引きずられて `https://webhook.kit-a.net/mcp/sse`（Tunnelドメイン）になってしまい、かつ認証トークンが付与されず接続エラー（401 Unauthorized）になる不具合が発生していた。
  - また、インターネットモード時にもトークンが伏字（`********`）になっている場合、そのまま無効な伏字トークンがスニペットに出力されてしまう課題があった。
- **修正内容 (`public/app.js`)**:
  1. `updateMcpConfigSnippets`:
     - アクセス元がローカル IP 以外（Cloudflare Tunnel 等の外部ドメイン）の場合、「宅内 LAN」選択時にはサーバーの実内部 IP（`state.serverInfo.serverIp` / `192.168.11.244`）とポート（`8080`）を使用して正しく `http://<serverIp>:8080/mcp/sse` を生成するように改修。
     - 管理者パスワード設定時などの認証保護に対応するため、トークンが存在する場合は宅内 LAN URL にも `?token=...` を付与。
     - インターネットモード選択時、トークンがマスキング（`********`）等で未取得の場合は `YOUR_WEBHOOK_TOKEN` プレースホルダーを明示。
  2. `setupMcpSettings`:
     - 外部ドメイン（Cloudflare Tunnel）経由で WebUI を開いている場合は、初期アクティブタブを自動的に「インターネット」側に設定。
     - コピーボタン押下時、`YOUR_WEBHOOK_TOKEN` が含まれている場合は「実際のトークンに置き換えて設定してください」と親切に案内するトースト通知を表示。
     - Webhook トークン入力欄（`txtWebhookTokenVal`）のリアルタイム変更イベントと連動。
  3. 実機コンテナ `SmartSpeaker-VoiceHub` 内の `/app/public/app.js` に変更を即時反映完了。

## 2026-10-22 20:45 - プロジェクト包括的セキュリティ監査指摘事項の改修・コンテナ健全化 (v2.0.1)
- **背景と課題**:
  - `scratch/report.md` の監査精査に基づき、実機コンテナが恒常的に `unhealthy` になっていた問題、OpenAI 呼び出し時のランタイムエラー、Gemini モデル指定不整合、MCP エンドポイント認証漏れ、設定ファイル破損リスク、各種セキュリティ脆弱性（トークン免除偽装、秘密情報平文返却、IP Spoofing、セッション失効漏れ）を包括的に改修。
- **修正内容**:
  1. **コンテナヘルスチェック健全化 (`app/routers/status.py`, `app/core/security.py`, `docker-compose.yml`, `Dockerfile`)**:
     - 無認証・超軽量なヘルスチェック専用エンドポイント `/health` および `/api/health` を新設。
     - `docker-compose.yml` および `Dockerfile` のヘルスチェック先を `/health` に変更。
     - 実機コンテナ `SmartSpeaker-VoiceHub` が連続 281 回失敗状態から即座に `healthy` に完全復帰。
     - システム情報を含む `/api/status` は管理者パスワード設定時に 401 保護を維持。
  2. **OpenAI 呼び出し NameError 修正 (`app/services/ai_service.py`)**:
     - `_call_openai_with_err` で未定義だった `url` および `headers` を定義し、100% クラッシュしていた致命的バグを解消。
  3. **Gemini モデル動的取得・厳格フィルタリング (`app/services/ai_service.py`, `app/routers/ai.py`)**:
     - 架空モデル `gemini-3.5-flash` のハードコードを撤廃。
     - Google Generative AI API から利用可能モデルを動的取得する `get_gemini_models` を実装（TTL 1時間のキャッシュ付き）。
     - テキスト生成（要約・発話）に関係のない埋め込み（embedding）、AQA、画像生成（imagen）、日付ピン留め版などのノイズを厳格に除外し、チャット・要約用主力モデル（`gemini-2.5-flash` 等）のみを抽出・優先ソート。
  4. **MCP (`/mcp*`) エンドポイントの包括的認証保護 (`app/core/security.py`, `app/services/mcp_service.py`)**:
     - `check_admin_auth` および `mcp_service.verify_auth` を改修し、管理者パスワード設定時は管理者認証（Cookie / Bearer / X-Admin-Password）または有効な Webhook トークンを必須化（無認証乗っ取り・情報閲覧を完全防止）。
  5. **`settings.json` のアトミック書き込み・バックアップ復元・既定値汚染防止 (`app/services/settings_service.py`)**:
     - 一時ファイル (`.tmp`) への書き込み ＋ `os.fsync()` ＋ `os.replace()` によるアトミック保存を実装。
     - 保存時に直前の正常設定を `settings.json.bak` として自動バックアップ。
     - 読み込み失敗時はバックアップからの自動復元を試行し、破損時の上書き保存を防止する安全フラグを導入。
     - `copy.deepcopy` を徹底し、グローバル `DEFAULT_SETTINGS` の参照共有汚染を解消。
  6. **設定画面の秘密情報マスキング返却 & パスワード直接変更禁止 (`app/routers/settings.py`)**:
     - `GET /api/settings` で `webhookToken`, `geminiApiKey`, `openaiApiKey`, `mqtt.password`, `onvif.defaultPassword` 等を `********` にマスクして返却。
     - `PUT /api/settings` でマスク値が送られてきた場合は既存値を安全に維持。
     - `PUT /api/settings` での `adminPassword` 直接変更を禁止し、`currentPassword` 必須の `/api/auth/password` に統一。
  7. **認証セキュリティ & レートリミット堅牢化 (`app/core/security.py`, `app/routers/auth.py`, `app/routers/speech.py`)**:
     - クライアント IP 取得処理 `extract_client_ip` を共通化し、直接アクセス時は未信頼ヘッダーを無視して IP Spoofing によるレート制限回避を防止。
     - Webhook トークン免除において、ヘッダー偽装（`Sec-Fetch-Site`）単体による無条件免除を撤廃（管理者Cookieまたはトークンを必須化）。
     - パスワード変更・解除時に既存の全セッションを一括失効（`ACTIVE_SESSIONS.clear()`）。
     - `SayRequest.text` に最大 10,000 文字の入力長バリデーションを導入（DoS防止）。
  8. **不具合・コード品質改善 (`app/services/scheduler_service.py`, `app/routers/dnd.py`, `app/main.py`, Git追跡)**:
     - `scheduler_service.py`: `now.second < 10` 条件による定期発声スキップバグを解消（毎分確実に1回発火）。
     - `dnd.py`: スクリプト生成時の改行・特殊文字サニタイズを実装し、パスワード参照を `get_effective_admin_password()` に統一。
     - `settings_service.py`: GUI で空文字設定時にパスワードが正しく解除されるようフォールバック不整合を解消。
     - `main.py`: `Response` のインポート追加、重複 `import re` の削除、`global_exception_handler` の内部例外メッセージ隠蔽、`/health` の頻出ポーリングログ抑制。
     - Git: 大文字小文字のファイル名衝突リスクがあったシンボリックリンク `Manual-en.md` の git 追跡を解除し、`MANUAL-en.md` に一本化。
- **検証結果**:
  - 新規テスト `tests/test_audit_fixes.py`（6件）を含む全 62 件の単体テストがすべて合格。
  - 実機 Docker コンテナ `SmartSpeaker-VoiceHub` が再作成後に即座に `Up (healthy)` に復帰し、`curl http://127.0.0.1:8080/health` で HTTP 200 OK（uptime確認）完了。

## 2026-10-22 18:00 - Web GUI 管理者パスワード設定・Cloudflare Tunnel リモートアクセス動的連動 & セキュリティ堅牢化
- **背景と課題**:
  - 自宅に常時稼働サーバーがない環境や外出先からでも安全に Web GUI を利用したいという要望に対し、スマートスピーカー（Google Home 等）のローカル HTTP キャスト互換性を一切損なうことなく、Cloudflare Tunnel（正規 SSL 証明書による警告なしの完全な HTTPS）経由での安全なリモート GUI アクセスを実現。
  - AI によるイントラネット探索や自動ブルートフォース攻撃から保護するため、ログイン試行のレートリミット、定数時間比較によるタイミング攻撃対策、動的 `Secure` Cookie、およびセキュリティヘッダー付与による包括的なセキュリティ強化を実施。
  - `.my.env` を直接編集できない一般ユーザーでも、Web GUI（設定 > Webhook & Tunnel）から直接パスワードを設定・変更・解除できるように連動。
- **修正内容**:
  1. **動的境界防御 & Cloudflare Tunnel 制御 (`app/core/security.py`)**:
     - `check_tunnel_access`: 管理者パスワード（`ADMIN_PASSWORD` / `adminPassword`）が設定されている場合は、Tunnel 経由での Web GUI および全 API の通過を動的許可。未認証時は `check_admin_auth` が 401 Unauthorized で遮断し、ログイン画面を表示。パスワード未設定時は従来どおり 403 Forbidden で即座に遮断（事故防止）。
     - `validate_webhook_token`: 認証済み管理者セッション Cookie（`auth_token`）を保持している場合、進入経路（LAN / Tunnel）を問わず Webhook (`/api/say`) のトークン入力を自動免除（外部から GUI で手軽に発声可能）。
     - `is_https_request`: リクエストが HTTPS / Cloudflare Tunnel 経由であるかを判定し、Cookie の `Secure: True` を動的付与（ローカル HTTP 接続時は `Secure: False` で互換維持）。
  2. **アタック・侵入耐性強化 (`app/core/security.py`, `app/main.py`)**:
     - **ブルートフォース対策**: `LoginRateLimiter` を実装。同一 IP から 1 分間に 5 回連続で失敗した場合、3 分間（180秒）すべてのログイン試行を `429 Too Many Requests` でロックアウト。
     - **タイミング攻撃耐性**: パスワード照合およびヘッダー検証に `hmac.compare_digest` を採用。
     - **セキュリティヘッダー**: `app/main.py` のミドルウェアですべてのレスポンスに `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` を自動付与。
  3. **パスワード管理 API & 設定サービス (`app/routers/auth.py`, `app/services/settings_service.py`, `app/routers/settings.py`)**:
     - `POST /api/auth/password`: Web GUI からのパスワード設定・変更・解除エンドポイントを新設。既存パスワード設定時は現在のパスワード検証を必須化し、設定・解除後は Cookie を自動再発行/削除。
     - `GET /api/auth/status`: レートリミットロック状態（`isLocked`, `remainingSeconds`）を返却。
     - `GET /api/settings`: パスワード平文の露出を防止するため、常にマスク値（`********`）を返し、設定有無フラグ（`hasAdminPassword`）を提供。
     - `settings_manager`: `get_admin_password()` および `set_admin_password()` を追加し、GUI 設定値（`settings.json`）を最優先しつつ `.my.env` と透過的に連動。
  4. **Web GUI 画面・多言語辞書 (`public/index.html`, `public/app.js`, `public/locales/ja.json`, `public/locales/en.json`)**:
     - 「設定 > Webhook & Tunnel」サブペインに「🛡️ Web GUI 管理者パスワード & Cloudflare Tunnel リモートアクセス」カードを新設。
     - 現在の保護状態（🔒 認証保護有効 / Tunnel リモート許可 ⇄ ⚠️ 未設定 / Tunnel GUI 遮断中）バッジ、現在のパスワード確認欄、新しいパスワード入力欄、表示/非表示トグル、保存・解除ボタンを配備。
     - 日英辞書に対称に 10 キーを追加。
  5. **テスト & 実機検証 (`tests/test_auth_security.py`)**:
     - レートリミッターロックアウト、動的 Tunnel ゲーティング、パスワード変更 API、動的 `Secure` Cookie、セキュリティヘッダー、設定マスキングを網羅する 6 件の単体テストを追加。全 56 テスト合格確認。
     - 実機コンテナ（`SmartSpeaker-VoiceHub`）再起動後の疎通確認、およびセキュリティヘッダー付与（HTTP 200）を確認。
  6. **ドキュメント更新 (`Manual.md`, `MANUAL-en.md`, `CHANGELOG.md`)**:
     - 第2章（境界防御・認証・セキュリティ設計）および第13章（認証 REST API リファレンス）を完全更新。

- **背景と課題**:
  - 緊急地震速報（EEW）、気象警報（大雨警報・特別警報等）、雨雲接近アラームを、単なるスピーカーからの音声アナウンスだけでなく、スマートホーム（Apple Home / Homebridge, Home Assistant / MQTT, Alexa, Google Home）のオートメーションの「トリガー（発火条件）」として活用したいという要望に対応。
  - 警報発令時に避難経路のスマート照明を最大光量で自動点灯させたり、高熱暖房器具に接続したスマートプラグの電源を緊急遮断したり、豪雨・強風時に電動シャッター・雨戸を自動閉塞するなどの高度なスマートホーム防災連動を実現。
- **修正内容**:
  1. **MQTT サービス拡張 (`app/services/mqtt_service.py`)**:
     - Home Assistant MQTT Auto-Discovery に 3 つの `binary_sensor`（`eew_alert` [safety], `weather_warning` [safety], `rain_alarm` [moisture]）を追加。
     - `publish_disaster_state(category, is_active, extra_info)` メソッドを実装し、警報状態（ON/OFF）および詳細メタデータを即時ブロードキャスト。
  2. **防災サービス・雨アラームサービス拡張 (`app/services/disaster_service.py`, `app/services/rain_alarm_service.py`)**:
     - EEW、気象警報差分検知、雨雲接近検知、および各テスト発報時にトリガー状態と MQTT を自動同期。
     - `get_trigger_status()` および `trigger_test_state(target, duration_sec)` を実装し、有効期限経過時の自動 OFF タイマーを配備。
  3. **REST API ルーティング追加 (`app/routers/disaster.py`)**:
     - `GET /api/disaster/triggers`: 現在の各防災トリガー状態を返却。
     - `POST /api/disaster/triggers/test`: 指定した防災トリガー（`eew`, `warning`, `rain`）を一定時間（10秒間等）強制ONにするシミュレーション用エンドポイントを追加。
  4. **Homebridge プラグイン拡張 (`plugins/homebridge-voicehub`)**:
     - `src/accessories/disaster-sensor.ts`: Apple Home 側でオートメーションのトリガーとして最も自然かつ確実に動作する `Service.MotionSensor`（仮想人感センサー / `Characteristic.MotionDetected`）アクセサリクラスを新設。
     - `src/voicehub-client.ts`: `getDisasterTriggers()` を追加。
     - `src/platform.ts`: `enableDisasterSensors !== false` 時に 3 つのセンサー（`EEW Alert`, `Weather Warning`, `Rain Approaching`）を自動登録し、定期ポーリングでリアルタイムに状態同期。
     - `config.schema.json` & `README.md`: 日英併記で設定項目・パラメータ説明・オートメーション活用例を追記。
  5. **WebUI 画面・フロントエンド制御 (`public/index.html`, `public/app.js`)**:
     - 「緊急速報・防災・天気」タブに「🏠 スマートホーム防災連動トリガー」カードを追加。
     - EEW、気象警報、雨雲接近の各リアルタイム状態（ON/OFF）バッジと、「⚡ 10秒間テストON」シミュレーションボタン群を配置。
  6. **多言語辞書更新 (`public/locales/ja.json` & `public/locales/en.json`)**:
     - `settingsDisaster` にトリガー名、説明文、ボタンラベルなど 10 キーを日英完全対称に追加。
  7. **ドキュメント更新 (`README.md`, `README-en.md`, `Manual.md`, `MANUAL-en.md`)**:
     - README の「主な特徴 (Key Features)」に、過大・誇張のない上品かつ事実ベースで「スマート防災連動（Smart Disaster Trigger Integration）」セクションを追記。
     - MANUAL の第6章（6.5節）および第13章（13.9節 APIリファレンス）を追記・更新。
  8. **単体テスト作成 (`tests/test_disaster_triggers.py`)**:
     - トリガー状態取得、テスト発動（EEW/気象警報/雨アラーム）、MQTT 安全送出、i18n キー対称性の全6テストを追加。全50テスト合格。
- **検証結果**:
  - `python3 -m unittest discover tests`: 全50テスト合格（リグレッションなし）。
  - `docker restart SmartSpeaker-VoiceHub` 後の実機疎通確認: `GET /api/disaster/triggers` および `POST /api/disaster/triggers/test` ともに HTTP 200 OK、状態遷移および自動 OFF 復帰を確認。
  - プラグイン TypeScript ビルド: `npm run build` 正常終了（エラー0件）。

## 2026-10-22 16:15 - 外部デバイス連携 (Logitech G HUB / Elgato Stream Deck) スクリプト自動生成・WebUI機能追加
- **背景と課題**:
  - Logitech マウス/キーボードの G キーや Elgato Stream Deck 等のハードウェアデバイスから、ワンタップで DND（会議・おやすみモード）を直接トグル・操作したいという要望に対応。
  - 通常のバッチファイル（`.bat`）実行時に発生する「一瞬黒いコマンドプロンプト画面が出る」チラつきを嫌うユーザーのために、完全サイレントでバックグラウンド実行される VBScript（`.vbs` / Windows標準COM `MSXML2.ServerXMLHTTP`）と、シンプルなバッチ（`.bat`）、macOS/Linux用のシェルスクリプト（`.sh`）の複数形式に対応したスクリプト自動生成＆ダウンロード機能を実装した。
  - 宅内LAN想定で、WebUIから現在のアクセスURLやパスワードが自動埋め込まれたスクリプトをワンクリックでダウンロードできる仕組みを新設。
- **修正内容**:
  1. **バックエンド API 実装 (`app/routers/dnd.py`)**:
     - `build_dnd_script(action, fmt, host, password)` ヘルパー関数を新設。
     - 各アクション（`toggle`: トグル反転, `30m`: 30分会議ミュート, `60m`: 60分会議ミュート, `unmute`: ミュート解除）および各フォーマット（`.vbs`, `.bat`, `.sh`）に応じたスクリプトを安全に生成。
     - `GET /api/dnd/script/preview`: WebUIプレビューおよびコピー用 JSON API を追加。
     - `GET /api/dnd/script/download`: ブラウザ直接ダウンロード用 API (`Content-Disposition: attachment; filename=...`) を追加。
  2. **WebUI 画面追加 (`public/index.html`)**:
     - 「拡張・システム設定」内のおやすみ・会議 (DND) サブペイン末尾に新カード「🎮 外部デバイス連携 (Logitech G HUB / Stream Deck 等)」を追加。
     - 接続先URL入力欄（現在のホストを自動補完・リセット可能）、スクリプト形式選択（.vbs / .bat / .sh）、ワンクリックダウンロードボタン群（トグル / 30分 / 60分 / 解除）を配置。
     - Logitech G HUB および Elgato Stream Deck への設定手順ガイドを折りたたみアコーディオン（`<details>` / `<summary>`）として掲載。
     - スクリプト内容のリアルタイムプレビュー枠およびワンクリック「📋 スクリプトをコピー」ボタンを装備。
  3. **フロントエンド制御 (`public/app.js`)**:
     - `setupDndDeviceIntegration()` を新設。
     - 形式・接続先URLの変更に応じたプレビューのリアルタイム更新、ワンクリックダウンロード、クリップボードコピー処理を実装。
  4. **多言語辞書更新 (`public/locales/ja.json` & `public/locales/en.json`)**:
     - `settingsDnd` 配下に全22キーの外部デバイス連携テキストを日英完全対称に追加。
  5. **ドキュメント更新 (`Manual.md`, `MANUAL-en.md`)**:
     - 5.5節「外部デバイス・ショートカット連携 (Logitech G HUB / Stream Deck)」および 13.8節 API リファレンスを追加・更新。
  6. **単体テスト作成 (`tests/test_dnd_scripts.py`)**:
     - 各形式（.vbs, .bat, .sh）のスクリプト生成内容、APIレスポンス、Content-Disposition、i18n キー対称性の全8テストを追加。
- **検証結果**:
  - `python3 -m unittest tests/test_dnd_scripts.py`: 全8テスト合格。
  - `python3 -m unittest discover tests`: 全44テスト合格（リグレッションなし）。
  - `node -c public/app.js`: JavaScript 構文検証クリア。
  - JSON 辞書構文およびキー完全対称性クリア。

## 2026-10-22 14:50 - Homebridge プラグイン (homebridge-voicehub) 全面日英併記対応 & v1.0.6 リリース
- **背景と課題**:
  - VoiceHub 本体の WebUI および総合技術仕様書（MANUAL）等の多言語化が完了していたが、Apple HomeKit 連携用プラグイン（`plugins/homebridge-voicehub`）は日本語のみで記述されていた。
  - Homebridge Config UI X（ブラウザ設定画面）の標準仕様上、動的な言語切り替え辞書ではなく静的 JSON Schema が用いられるため、グローバルユーザーおよび国内ユーザー双方が違和感なく扱えるよう、全体を「日英併記（Bilingual）」構成へ刷新した。
  - また、リモート最新の `v1.0.5`（スピーカーカテゴリ別検出機能＆Config UI X 検証警告解消）を統合・取り込み、新設されたカテゴリ検出フィールド（GoogleHome, Alexa, HomePod, ONVIF/Tapo, DLNA）を含めて完全な日英併記に対応した `v1.0.6` としてリリース。
- **修正内容**:
  1. **設定スキーマ (`plugins/homebridge-voicehub/config.schema.json`) の日英併記化**:
     - `headerDisplay` を英語および日本語の2行併記に更新。
     - 全プロパティの `title`、`description`、`placeholder` を `English / 日本語`（または `English (日本語)`）形式で分かりやすく併記。
     - スピーカーカテゴリ検出オプション（`discoverGoogleHome`, `discoverAlexa`, `discoverHomepod`, `discoverOnvif`, `discoverDlna`）も日英併記化。
     - 設定フォームの `fieldset`（接続設定、スピーカー自動検出と登録カテゴリ、検出対象カテゴリ、その他の機能オプション、プリセット発話スイッチ）タイトル・ボタンを日英併記化。
  2. **ドキュメント (`plugins/homebridge-voicehub/README.md`) の日英併記化**:
     - 冒頭に言語切り替えアンカー（`[English](#-english) | [日本語](#-japanese)`）を設置。
     - 概要、特徴、インストール方法、設定例、パラメータ表（カテゴリ検出設定含む）、Siri操作例、ビルド手順を英語（English）および日本語の完全な2大セクションとして構成。
     - WebUI から「📄 Raw Markdown」として参照される `public/plugins/homebridge-voicehub/README.md` にも完全同期。
  3. **TypeScript ソースコード (`src/`) のログ・デフォルト値の日英併記化**:
     - `src/platform.ts`: プラットフォーム初期化、デバイス検出開始、アクセサリ復元、カテゴリ無効スキップ、登録解除等の全ログ出力を日英併記（`[VoiceHubPlatform] ... / ...`）化。DNDアクセサリのデフォルト名称を `DND Mode / 会議・おやすみモード` に変更。プリセットのデフォルトサンプル配列を英語・日本語併記に更新。
     - `src/accessories/dnd-switch.ts`: スイッチ操作ログ、エラーログ、DND理由文字列を日英併記化。
     - `src/accessories/preset-switch.ts`: プリセット発話開始、成功、エラー、ビジー通知の全ログを日英併記化。
     - `src/accessories/speaker.ts`: 音量変更、ミュート切り替え、エラー等のログを日英併記化。
     - `npm run build` を実行し、TypeScript ビルドおよび `dist/` の再生成を確認。
  4. **バージョン管理 & CHANGELOG 更新**:
     - `plugins/homebridge-voicehub/package.json` および `package-lock.json` のバージョンを `1.0.6` に更新。
     - `plugins/homebridge-voicehub/CHANGELOG.md` および リポジトリルート `CHANGELOG.md` に `[1.0.6] - 2026-10-22` を追記。
- **検証結果**:
  - `python3 -m json.tool plugins/homebridge-voicehub/config.schema.json`: JSON 構文正常。
  - `npm run build`: TypeScript コンパイル正常終了（エラー 0 件）。
  - `diff plugins/homebridge-voicehub/README.md public/plugins/homebridge-voicehub/README.md`: 同期完全一致。
  - `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/plugins/homebridge-voicehub/README.md`: HTTP 200 応答確認。
  - `python3 -m unittest discover tests`: 全36単体テスト合格（リグレッションなし）。

## 2026-10-22 07:45 - GitHub Code Scanning アラート完全解消（js/tainted-format-string & js/xss-through-dom）および v1.0.4 リリース
- **背景と課題**:
  - GitHub Code Scanning（CodeQL）において、WebUI多言語化エンジン（`public/i18n.js`）に起因する 2 件のアラートが検出されていた：
    1. Alert #27 (`js/tainted-format-string` / CWE-134): `loadDictionary` 内の `console.warn` において、第一引数にユーザー制御可能な `lang`（URLパラメータ `?lang=` 起因）が含まれるテンプレートリテラルが渡され、第二引数に `err` が渡されていたため、フォーマット文字列インジェクション脆弱性として検出。
    2. Alert #26 (`js/xss-through-dom` / CWE-79, CWE-116): `applyTranslations` 内で `el.getAttribute('data-i18n')` から取得したDOMテキストが `t(key)` を経由して `innerHTML` に代入されていた。未定義キーのフォールバックにより属性値がそのままHTMLシンクへ流れる可能性があり、かつサニタイズなしに `innerHTML` へ代入されていたため DOM XSS として検出。
- **修正内容**:
  1. **フォーマット文字列脆弱性の解消 (`public/i18n.js`)**:
     - `console.warn` / `console.log` の第一引数を完全な固定文字列リテラルに変更し、変数はカンマ区切りの追加引数として渡すよう改修（`console.warn('[i18n] Failed to load locale:', lang, err)`）。
     - `loadDictionary(lang)` の先頭にホワイトリスト形式の形式チェック（`/^[a-zA-Z0-9_-]+$/`）を追加。
  2. **DOM XSS 脆弱性の根本解消 (`public/i18n.js`)**:
     - `public/i18n.js` から `innerHTML` への直接代入コードを完全撤廃（使用ゼロ件）。
     - ブラウザ標準の `DOMParser` を活用したホワイトリスト型サニタイザー `setSafeHtml(el, rawHtml)` を新設。
     - 許可タグ（`STRONG`, `B`, `EM`, `I`, `CODE`, `A`, `BR`, `SPAN`, `SMALL`, `DIV`, `P`, `LI`, `UL`, `OL`）および許可属性（`class`, `style`, `title`）のみをホワイトリストで生成。
     - `A` タグの `href` は安全なスキーム（`http:`, `https:`, `/`, `mailto:`）のみ許可し、自動で `target="_blank" rel="noopener noreferrer"` を付与。危険なスキーム（`javascript:`）やイベントハンドラ（`on*`）を完全遮断。
     - 生成されたクリーンなDOMノードツリーを `replaceChildren()` で安全に適用。
     - `renderLanguageSelector` も `replaceChildren` と `document.createElement('option')` による安全なDOM構築に統一。
     - `key` のホワイトリストバリデーション（`/^[a-zA-Z0-9_.-]+$/`）を適用。
  3. **リグレッション防止テストの強化 (`tests/test_smoke.py`)**:
     - `test_i18n_static_files_and_locales` に `setSafeHtml` の実装存在、ホワイトリスト定義、およびコード行での `.innerHTML =` 代入が 0 件であることを自動検証するアサーションを追加。全36単体テスト合格。
  4. **バージョン更新 & リリース準備**:
     - `public/index.html` のキャッシュバスターを `v=1.0.4` に更新。
     - `plugins/homebridge-voicehub/package.json` および `package-lock.json` を `1.0.4` に引き上げ。TypeScript ビルド正常終了。
     - `CHANGELOG.md` および `plugins/homebridge-voicehub/CHANGELOG.md` に `[1.0.4] - 2026-10-22` を追記。
- **検証結果**:
  - `node -c public/i18n.js`: 構文エラー 0 件。
  - `python3 -m unittest discover -s tests -p "test_*.py"`: 全36テスト合格（3.347s）。
  - `npm run build` (homebridge plugin): 正常終了。

## 2026-10-21 20:45 - 主要ドキュメント（README, Contributing, Security, MANUAL）の完全英語化と相互言語リンク整備
- **背景と課題**:
  - ユーザーより「README、Contributing、Security、MANUAL これらを英語化してほしい。それぞれ-enを付けて別ファイルでよろしく」との要望。
  - 多言語ユーザーおよび国際的なオープンソースコミュニティからのアクセス・利用を円滑にするため、主要ドキュメント4点の包括的な英語版作成と、言語切り替え導線の整備が求められた。
- **修正内容**:
  1. **README (`README-en.md`) の作成**:
     - プロジェクト概要、主要機能（マルチスピーカー、多段TTSフォールバック、WebUI、タイマー発声予約、DND、HomeKit/Siri、Webhook/MQTT/MCP）、導入手順（一般ユーザー向け Docker Compose / 開発者向けホットリロード）、基本操作、API/ドキュメント導線、ライセンス・謝辞を完全英語化。
  2. **Contributing (`CONTRIBUTING-en.md`) の作成**:
     - コントリビューション方針、GitHub Discussions/Issues、開発アーキテクチャ規約（Pythonファースト、Vanilla JS/CSS、TypeScriptプラグイン、pydantic-settings）、Docker/ローカル開発環境セットアップ、単体テスト実行手順、プルリクエスト作法、MITライセンス同意事項を完全英語化。
  3. **Security (`SECURITY-en.md`) の作成**:
     - セキュリティポリシー、サポートバージョン対象（`main`）、脆弱性非公開報告手順（GitHub Private Vulnerability Reporting / Discussions）、報告時推奨記載事項、対応プロセス、スコープ外事項（サードパーティ仕様変更、設定不備、DoS）を完全英語化。
  4. **MANUAL (`MANUAL-en.md` / `Manual-en.md`) の作成**:
     - 全15セクション・約930行の総合技術仕様書を完全英語化（アーキテクチャ図、デュアルレイヤー境界防御・Tunnel・認証、ターゲット宛先解決マクロ、TTSエンジン多段フォールバック＆Fastest-Wins並行生成、DND判定パイプライン＆保留WAL、防災気象API、AI連携、各ハードウェア接続仕様、Homebridgeプラグイン、MCPサーバー仕様、マルチMQTT＆HA Discovery、WebUI仕様、全REST APIリファレンス、内部FastAPIモジュール設計）。
     - Linux環境での大文字小文字参照互換性のため `Manual-en.md` -> `MANUAL-en.md` のシンボリックリンクも整備。
  5. **言語切り替えナビゲーションの追加**:
     - 各日本語版（`README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `Manual.md`）および英語版の先頭に、相互に行き来できる `**日本語** | [English](...)` ナビゲーションリンクを配置。
- **検証結果**:
  - `git status` により全ファイル配置・シンボリックリンク作成を確認。
  - `docker exec SmartSpeaker-VoiceHub python3 -m unittest discover -s tests -p "test_*.py"` で全36テスト合格。

## 2026-10-21 20:30 - 雨アラーム音声再生バグ修正（targets引数名整合 & 防災スピーカー連動）、テスト発話ボタンの統合、Yahoo! Client ID取得ガイド折りたたみ追加 & `<br>` 表示崩れ修正
- **背景と課題**:
  1. ユーザーより「雨雲接近テストとかを押してみても音声ならないな？ 緊急地震速報・震度速報・気象警報をアナウンスするスピーカーを指定します、のところと一緒だよね？」との報告。コンテナログに `SpeechService.speak() got an unexpected keyword argument 'target'` が記録され、音声発話が失敗していた。
  2. 「雨雲接近テストとか、その下のテスト発話・シミュレーションのところにまとめてよ」との配置改善要望。
  3. 「Yahoo! JAPAN Client ID (アプリケーションID) 折りたたみで、これの取得方法のアナウンスもお願い」とのガイド追加要望。
  4. 説明文に `<br>` 文字列がそのままレンダリングされてしまっていた表示バグの修正要望。
- **修正内容**:
  1. **雨アラーム音声発話バグ修正 (`app/services/rain_alarm_service.py`)**:
     - `_speak_alert` 内で `speech_service.speak(target=target)` となっていた引数名を正しい `targets=targets` に修正。
     - スピーカー選択に関して、雨アラーム個別設定が未指定または全室の場合でも、ユーザーの直感通り「緊急速報・防災タブ全体の通知先スピーカー設定（`disaster.targetScope` / `disaster.targetDevices`）」に自動フォールバック・完全連動するよう処理を強化。
  2. **テスト発話・シミュレーションカードへの統合 (`public/index.html`)**:
     - 雨アラームカード内にあったテストボタン群（雨雲接近・大雨警戒・雨上がり）を削除し、下部の「🧪 テスト発話・シミュレーション」カード内に「⚡ 地震速報・気象警報テスト」と「🌧️ 雨雲接近・雨アラームテスト」の2大グループとして集約・統一。
  3. **Yahoo! Client ID 取得ガイド折りたたみ追加 & `<br>` 表示崩れの解消 (`public/index.html`, `public/locales/ja.json`, `public/locales/en.json`)**:
     - `<br>` タグを排除し、`yahooAppIdHelpMain` と `yahooAppIdHelpSub` の2つのクリーンなブロックに分割。
     - `<details>` / `<summary>` によるスタイリッシュな折りたたみアコーディオン「📖 Yahoo! JAPAN Client ID の無料取得手順（約2分）」を追加（Yahoo! JAPAN IDログイン → デベロッパーネットワークアクセス → Web APIアプリ無料登録 → Client ID貼り付け手順を明記）。
     - 日英両言語で対称に15キーを追加・更新。
- **検証結果**:
  - `curl -X POST http://localhost:8080/api/rain-alarm/test -d '{"alertType":"approaching"}'` で即座に TTS 合成が行われ、指定スピーカー（Google Home: `192.168.11.85:32094`）へ Cast 再生（HTTP 200 / 206）されることをログで確認。
  - ブラウザサブエージェントにより WebUI 上で全テストボタン（EEW、気象警報、雨雲接近等）がクリック可能かつトースト表示されることを実機確認。
  - 折りたたみガイドの表示、`<br>` の消失、統一されたテストセクションの描画を完了。

## 2026-10-21 20:20 - 雨アラーム・雨雲接近通知 (降雨ナウキャスト & Leaflet地図 & レーダー重ね合わせ) 実装 & ブラウザタブタイトルHTML混入バグ修正
- **背景と課題**:
  1. ユーザーより「雨アラーム的な機能を作りたい。地図で実際にいる場所を登録して、雨雲レーダーとかから何分後に雨が降ります、みたいなアナウンスしたい」との要望。
  2. ブラウザのタブ名（document.title）に `<span data-i18n="devices.de...` と生HTMLタグが混入して表示されてしまう不具合の報告。
  3. LAN内HTTPアクセス時（非セキュアオリジン環境）に `navigator.geolocation` が `Only secure origins are allowed` エラーになる問題。
- **修正内容**:
  1. **ブラウザタブタイトルHTML混入バグの修正**:
     - `public/index.html`: `<title>` 内に記述されていた `<span>` タグを撤廃し、純粋なプレーンテキスト `<title>Google Home, Alexa &amp; HomePod | Voice Hub</title>` に修正。
     - `public/locales/ja.json` & `en.json`: `app.pageTitle` を新設。
     - `public/i18n.js`: `applyTranslations` 内で `document.title = t('app.pageTitle')` により安全にプレーンテキストで更新するよう統一。
  2. **雨アラーム サービス・API設計 (`app/services/rain_alarm_service.py`, `app/routers/rain_alarm.py`)**:
     - **ハイブリッド降雨予測**:
       - Yahoo! JAPAN Client ID（YOLP 気象情報API）が設定されている場合は10分刻み・60分後までの高精度雨雲レーダーデータを取得。
       - 空欄の場合はAPIキー不要の標準モード（Open-Meteo minutely_15）へ自動フォールバック。
     - **3段階の音声アナウンス判定ステートマシン**:
       - 雨雲接近・降り始め: 「まもなく約{X}分後に雨が降り始める見込みです（予想降水量: 毎時約{Y}mm）。洗濯物の取り込み等にご注意ください。」
       - 大雨警戒: 時間雨量10mm以上の激しい雨が接近した場合に「大雨警戒」を通知。
       - 雨上がり: 雨が止んだ際に「雨が止んだ見込みです。傘のお忘れ物にご注意ください」を通知。
     - **DND（おやすみモード）連動**: DND判定中は音声発話を抑制（ログ記録）。
     - **気象庁雨雲レーダー時刻同期**: `https://www.jma.go.jp/bosai/jmatile/data/nowc/targetTimes_N1.json` から最新の basetime / validtime を取得し、キャッシュ（TTL 60秒）して返却。
     - **IP Geolocation フォールバック**: `GET /api/rain-alarm/ip-location` を新設。HTTP環境でGPSがブロックされた場合でもIPアドレスから大まかな地域を逆引きして地図をジャンプ可能に。
  3. **WebUI（Leaflet 地図 & 雨雲レーダー重ね合わせ）の実装**:
     - `public/vendor/leaflet/`: Leaflet.js / CSS / マーカー画像をローカル配備。
     - 「緊急速報・防災・天気」タブ内に「🌧️ 雨アラーム・雨雲接近通知 (Japan Only)」カードを新設。
     - ドラッグ可能なピン（Marker）と地図クリックによる位置指定・緯度経度即時反映。
     - 気象庁高解像度降水ナウキャストのタイルを半透明（opacity: 0.65）で地図上に重ね合わせ表示（ON/OFFトグル、最新時刻リロード）。
     - 国土地理院ジオコーディングAPIによる住所・駅名検索バー（Enterキー対応）。
     - 現在地取得ボタン（GPS失敗時は自動でIPジオロケーションにフォールバック案内）。
     - 直近〜60分後までの10分刻み雨雲状況タイムラインバー（色分け・降水強度mm/h・アイコン表示）。
     - テスト発声ボタン（接近テスト・大雨テスト・雨上がりテスト）。
  4. **多言語化（i18n）**:
     - `public/locales/ja.json` & `en.json` に全32キーを完全対称で追加（全1,402キー）。
- **検証結果**:
  - `python3 -m unittest discover tests`: 新設した `tests/test_rain_alarm.py` を含む全36テスト合格。
  - `node -c public/app.js`: 構文エラー 0 件。
  - 実機ブラウザ検証: タブタイトルが正常表示され、雨アラームカード・Leaflet地図・雨雲レーダー重ね合わせ・タイムラインの描画を確認。

- **背景と課題**:
  - WebUIの初期多言語化後、「結構日本語のまま残っちゃってるところがあるので、再度総チェックをかけてほしい」との要望を受け、リポジトリ全体を対象とした徹底的な総点検を実施。
  - **残存箇所の調査結果**:
    1. `public/index.html`: 親タグの `data-i18n` 漏れや、インラインタグ（`<br>`, `・`, `<code>`）で文節が細切れになっていた未翻訳テキストが61箇所残存。
    2. `public/app.js`: JavaScript による動的レンダリング（トースト通知 196件、確認ダイアログ 16件、DOMテキスト・バナー・ボタン更新 222件、動的テンプレート生成 319件）が日本語ハードコードのまま動作していた。
- **修正内容**:
  1. **`public/locales/ja.json` & `public/locales/en.json` の大幅拡充**:
     - 辞書キーを初期の237キーから **全1,369キー** に大幅拡充（約6倍）。
     - 単語単位の不自然な細切れ置換を廃止し、文全体を包括する自然な日英対訳フレーズに再構成。
     - Python スクリプト（`scratch/check_symmetry.py`）により、全キーが 100% 完全に対称であることを検証。
  2. **`public/index.html` の 100% 完全多言語化（残存0件達成）**:
     - カレンダー設定の非公開 iCal 取得ガイド、Azure / Edge-TTS 推奨理由・無料枠・ポータル登録注意、外部音声エンジン（VOICEVOX/AivisSpeech/OpenJTalk）登録・テーブル、HomePod ネットワーク注意、Tapo事前設定案内、Webhook / Gemini / MQTT / Homebridge の各種ガイド・JSONサンプルなど全残存箇所を `data-i18n` 化。
     - HTML パーサーによる精密スキャン（`scratch/quick_audit.py`）にて、**未翻訳テキストノード・属性残存 0件（100% クリーン）** を達成。
  3. **`public/app.js` の動的レンダリング・トースト・ダイアログ多言語化**:
     - **トースト自動翻訳エンジン**: `translateToast(msg)` を実装。184件のユニークメッセージの静的対訳辞書および正規表現パターン（動的名前・件数・エラープレフィックス等）を統合し、既存の全196箇所の `showToast` 呼び出しが自動で高品質な英語表示になるハイブリッド設計を配備。
     - **確認ダイアログ (confirm)**: 予約キャンセル、ログアウト、スケジュール削除、履歴クリア、Alexa解除、カレンダー削除、DNDルール削除、グループ削除、IPエイリアス削除、ONVIF連携解除、MQTTブローカー削除、HA連携解除、音声エンジン削除、ログアーカイブ等の全16件を日英対応化。
     - **動的DOM・ステータスバナー**:
       - ヘッダーステータス（稼働中、接続エラー、標準スピーカー、HomePod認識台数）
       - DNDステータスバナー（🟢 Currently Normal Mode (DND Inactive) / サブタイトル / 進行中カレンダー予定 / 曜日の英語表示: Every Mon, Tue...）
       - 即時発言スライダー表示値（Follow global setting, Standard (0%), Keep device volume）および送信中・音声生成中ボタン
       - デバイス一覧カード（お気に入り追加/解除、デフォルト設定、テスト発声ボタン）
       - カレンダー・スケジュールモーダルタイトル、定時ルール追加/編集モーダル
       - MQTT / ONVIF / AI連携の稼働ステータス・バッジ
     - **言語切替イベント (`voicehub:language-changed`)**: 言語セレクターの変更を検知し、デバイスグリッド・発言履歴・スケジュール一覧・DNDステータス・ヘッダーを即座に再レンダリングするリスナーを接続。
  4. **キャッシュバスター更新**:
     - `public/index.html` 内の `app.js?v=3.7`, `i18n.js?v=3.7` に更新。
- **検証結果**:
  - `python3 -m unittest discover tests`: 全31テスト合格（3.091s）。
  - `node -c public/app.js`: 構文エラー 0 件。
  - 実機ブラウザ検証（`browser_subagent`）:
    - 英語モード（`?lang=en`）で全タブ・全設定サブペインを巡回・スクリーンショット撮影。
    - DND画面のバナー、サブタイトル、スケジュール定時ルールの英語表記（`Every Mon, Tue, Wed, Thu, Fri | 09:00 - 18:00`）、カレンダー予定空表示がすべて英語になることを確認。
    - 即時発言タブでのトースト通知が英語で出力されることを確認。
    - 「緊急速報・防災・天気」の全見出し・サイドバー・ボタン・注記に「(Japan Only)」が100%付与・維持されていることを確認。
    - ヘッダーの言語ドロップダウンから「日本語」への切り替えがリロードなしで即座に動作し、破綻なく日本語へ復帰することを確認。

## 2026-10-21 18:20 - WebUI 多言語対応（i18n）フェーズ2 & 3: 全画面日英完全対応 & 防災・気象の「Japan Only」明記
- **背景と課題**:
  - フェーズ1（基盤構築・ヘッダー・タブ・即時発言パネル）に続き、WebUI の残り全画面（定期スケジュール・カレンダー、発言履歴、接続デバイス、各種拡張・システム設定、リアルタイムシステムログ、モーダル）を一気に多言語対応（日本語・英語）させた。
  - **重要要件**: 緊急速報・防災・天気（緊急地震速報、震度速報、気象警報、天気予報）は日本の気象庁（JMA）および国内 P2P 地震速報 API に依存しており日本国外では動作しないため、英語表記ではサイドバーナビゲーションおよび画面内各カード見出しに「**Japan Only (日本専用)**」であることを明確に明記することが求められた。
- **修正内容**:
  1. `public/locales/ja.json` & `public/locales/en.json`:
     - 定期スケジュール、カレンダー連携、発言履歴、接続デバイス、各種設定（TTS、拡張機能、DND、防災・気象、AI/Alexa/HomePod、ONVIF/DLNA、MQTT、Webhook、MCP）、リアルタイムシステムログ、モーダル、共通語句を網羅。
     - 全237キーが完全に対称・一致することを Python スクリプトで構文検証。
     - 防災・天気機能の英語テキストに「(Japan Only)」を統一適用：
       - `settings.navDisaster`: `"Disaster & Weather (Japan Only)"`
       - `settings.disasterTitle`: `"🚨 Disaster & Weather Alerts (Japan Only)"`
       - `settings.disasterSub`: `"Automated integration with Japan P2P Earthquake Info and Japan Meteorological Agency (JMA) alerts & forecasts. (Available only for regions in Japan)"`
       - `settings.disasterJapanOnlyNotice`: `"※ This feature is designed exclusively for regions in Japan using JMA (Japan Meteorological Agency) and P2P Earthquake APIs."`
       - `settings.disasterRegionTitle`: `"📍 Target Region (Japan Only)"`
       - `settings.disasterEewTitle`: `"⚡ Earthquake Early Warning (EEW) (Japan Only)"`
       - `settings.disasterQuakeTitle`: `"🌊 Earthquake Intensity Reports (Japan Only)"`
       - `settings.disasterWeatherTitle`: `"⛈️ Weather Warnings & Advisories (Japan Only)"`
       - `settings.disasterMorningTitle`: `"☀️ Morning Briefing & Weather Integration (Japan Only)"`
  2. `public/i18n.js`:
     - URL クエリパラメータ（`?lang=ja` / `?lng=en`）による初期言語強制指定をサポート（テストや共有リンクでの再現性向上、`localStorage` とも自動同期）。
     - キャッシュバスターを `v=3.3` に更新。
  3. `public/index.html`:
     - スケジュール・カレンダー、発言履歴、接続デバイス、設定サイドバー、防災・天気カード（左右カラム全カード見出し・説明・選択肢）、システムログに `data-i18n` 属性を完全配備。
     - Python の HTMLParser による構文解析を実施し、タグのネスト整合性を完全確認。
     - スクリプトタグを `<script src="i18n.js?v=3.3"></script>` および `<script src="app.js?v=3.3"></script>` に更新。
  4. `public/app.js`:
     - `renderFullHistory()`: 発言履歴カード内の動的テキストを多言語化：
       - 相対時間表示（`4h ago` / `4時間前`）
       - ステータスバッジ（`✓ Success` / `✓ 送信成功`、`❌ Failed` / `❌ 送信失敗`、`🕒 DND Queued` / `🕒 DND保留中`、`🌙 DND Silent` / `🌙 DNDサイレント`、`🕒 DND Replay` / `🕒 DND保留再生`）
       - 送信先（`Target:` / `送信先:`）
       - 操作ボタン（`Copy` / `コピー`、`Preview` / `試聴`、`Repeat` / `再発言`）
       - 空履歴メッセージ（`No speech history records matching the criteria`）
     - `voicehub:language-changed` イベントリスナーでデバイス一覧、スケジュールテーブル、予約タスク、発言履歴の再描画を完全連動。
- **検証結果**:
  - `python3 -m unittest discover tests`: 全31テスト合格（3.299s）。
  - 実機ブラウザ（`http://localhost:8080/`）検証:
    - 即時発言（Direct Speech）、定期スケジュール（Schedule & Calendar）、発言履歴（Speech History）、接続デバイス（Connected Devices）、各種設定（System & Settings）、システムログ（System Logs）の全画面で英語が美しく適用されることを確認。
    - 発言履歴カード内の「Target:」「Copy」「Preview」「Repeat」「✓ Success」「4h ago」がすべて英語表示されることをスクリーンショットで確認。
    - 各種設定のサイドバー「🚨 Disaster & Weather (Japan Only)」および防災設定画面内の全見出し・注記に「(Japan Only)」が明記されていることをスクリーンショットで確認。
    - 日本語に戻した際にすべての画面が破綻なく日本語へ復帰することを確認。

## 2026-10-21 17:46 - WebUI 多言語対応（i18n）フェーズ1: 基盤構築・ヘッダー・タブ・即時発言パネルの日英完全対応
- **背景と課題**:
  - WebUIの国際化（多言語対応）にあたり、まずは日本語・英語の2言語対応を導入する方針となった。
  - 将来的な他言語追加（中国語、韓国語、ドイツ語等）がJSONファイルの追加と配列1行の追加のみで完結する拡張性の高い設計が求められた。
  - ブラウザの優先言語（`navigator.languages`）から自動検出し、手動切替時は `localStorage` で次回以降も記憶・永続化すること、最終フォールバック言語は英語（`en`）とすることが合意された。
- **修正内容**:
  1. `public/locales/ja.json` & `public/locales/en.json`:
     - アプリ基本情報、ヘッダー、ナビゲーションタブ、即時発言パネル（クイックプリセット、スライダー、マクロボタン、予約発声、緊急通知等）、共通アクション、トースト通知メッセージを辞書化。
  2. `public/i18n.js`:
     - 軽量Vanilla i18nエンジンを新設。
     - `SUPPORTED_LANGUAGES` 配列による動的言語セレクター生成機能。
     - `detectInitialLanguage()`: `localStorage` -> `navigator.languages` -> `en` の動的ロケール判定。
     - キャッシュ付き非同期辞書ローダー `loadDictionary` と `t(key, params, defaultValue)`。
     - `applyTranslations()`: `data-i18n`, `data-i18n-placeholder`, `data-i18n-title`, `data-i18n-aria-label` のDOM一括適用（SVGアイコン保護）。
     - 言語変更時の `voicehub:language-changed` カスタムイベント発火。
  3. `public/index.html`:
     - `<script src="i18n.js?v=1.0"></script>` を `app.js` の直前にインクルード。
     - ヘッダー右上にモダンなピル型言語セレクターチップ（`<div class="status-chip-sub lang-select-chip">` & `<select id="headerLanguageSelect">`）を新設。
     - ヘッダーチップ、メインタブナビゲーション（6タブ）、即時発言パネルの全要素に `data-i18n` 属性を付与。
  4. `public/style.css`:
     - `.lang-select-chip`, `.lang-icon`, `.header-lang-select` のスタイリングを追加。
  5. `public/app.js`:
     - `renderMacroButtonsFor`: マクロボタン（ALL、クリア等）を `window.t` で多言語化。
     - クイックプリセット: クリック時に入力される発言テキストも選択言語に合わせて日英動的切り替え。
     - スライダー（話速、音高、音量）: 標準値表示の多言語化。
     - `updateSpeakButtonLabel`: 発言ボタンおよび予約発声ボタンのラベル多言語化。
     - `voicehub:language-changed` イベントリスナーにより、言語変更時にスライダーや動的ボタンを即時再描画。
  6. `tests/test_smoke.py`:
     - `test_i18n_static_files_and_locales` を新設。ファイル存在、JSON構文およびキー整合性、FastAPI静的ファイル配信、HTML組み込みを検証。
- **検証結果**:
  - `python3 -m unittest tests/test_smoke.py`: 全16テスト合格 (2.73s)。
  - `python3 -m unittest discover tests`: 全31テスト合格。
  - 実機ブラウザ検証: `http://localhost:8080/` にてヘッダーの言語ドロップダウンから日本語/Englishの切り替え、タブおよび即時発言パネルのリアルタイム翻訳、プリセット入力（"Dinner" -> "Dinner is ready!"）、日本語復帰が正常動作することを確認。

## 2026-10-21 09:05 - mDNS (.local) 動的名前解決 (Zeroconf Resolver) 機能の内蔵と MQTT 連携
- **背景と課題**:
  - MQTT ブローカーや各種連携先で `MasterProDesk400G5.local` などの `.local` ホスト名を使用する際、Docker コンテナ（`python:3.14-slim`）環境内の標準 libc リゾルバが mDNS に非対応であるため名前解決に失敗していた。
  - `extra_hosts` や `/etc/hosts` による静的 IP ハードコードは、DHCP 環境による相手先 IP の変動や、ポータビリティ・運用保守の観点で採用できない制約があった。
- **修正内容**:
  1. `app/core/resolver.py`:
     - Pure Python の mDNS 動的名前解決マネージャー `MDNSResolver`（共通ヘルパー `resolve_host` / `resolve_host_sync`）を新設。
     - `zeroconf.AddressResolver` を活用し、末尾が `.local` のホスト名に対して同一 L2 ネットワーク内のマルチキャスト問い合わせを行い最新の IPv4 アドレスを動的に取得。
     - TTL（60秒）によるインメモリキャッシュを実装し、不要なマルチキャストパケットを抑制しつつ相手マシンの DHCP アドレス変動に自動追従。
     - 通常の IP アドレスや通常ドメイン名の場合は名前解決処理をバイパスし、mDNS 失敗時は元のホスト名に安全にフォールバック。
     - `DeviceManager` の既存 Zeroconf インスタンスを優先再利用し、ポートやソケットの二重生成・競合を防止。
  2. `app/services/mqtt_service.py`:
     - `MQTTBrokerWorker._run_loop()` にて、ブローカー接続前に `await resolve_host(broker)` を呼び出し、動的に解決された IP アドレスへ接続するよう統合。
     - `MQTTBrokerWorker.get_status()` およびトップレベルステータスに `resolvedBroker` プロパティを追加。
  3. `public/app.js`:
     - MQTT 接続ステータスサマリーボードおよび各ブローカーカードの統計情報にて、mDNS 解決が行われた場合に解決先 IP（`resolvedBroker`）を表示するよう UI を改善。
  4. `Manual.md`:
     - 第11章「マルチ MQTT ブローカー仕様」に mDNS (.local) 動的名前解決の仕様を追加。
  5. `tests/test_resolver.py`:
     - 単体テストを新規作成し、IPアドレス判定、mDNS判定、キャッシュ動作、解決失敗時のフォールバック、実環境での `MasterProDesk400G5.local` 解決（`192.168.11.115`）、MQTT 連携ステータスを網羅検証（全8テスト合格）。
- **検証結果**:
  - `python3 -m unittest tests/test_resolver.py`: 全8テストすべて合格 (0.006s)。
  - `python3 -m unittest discover tests`: 全30テストすべて合格 (4.61s)。
  - `MasterProDesk400G5.local` が `192.168.11.115` に動的解決されることを実機確認。

## 2026-10-20 18:35 - 各テーマ10個ずつ（計60種＋none）へのチャイム音拡充と、WebUI試聴ボード撤去・ドロップダウン集約
- **背景と課題**:
  1. 試聴ボード表示（グリッドカード一覧）はWebUIの縦幅を取りすぎるため撤去し、通常のセレクトボックス（ドロップダウン）でテーマ別にスッキリ選べるUIにしたいという要望があった。
  2. チャイム音のラインナップを各テーマ10個ずつ均等に揃え、十分なバリエーションを確保したいという要望があった。
- **修正内容**:
  1. `public/sound/` (新規47種を追加合成・配備し、6テーマ×各10種 計60種を完全配備):
     - 【標準・日常】: `dingdong`, `chime_simple`, `classic_doorbell`, `classic_triangle`, `classic_cuckoo`, `classic_step`, `classic_warm`, `classic_bright`, `classic_soft`, `classic_clarity` (10種)
     - 【ホテル・高級ラウンジ】: `chime_hotel`, `chime_marimba`, `hotel_glockenspiel`, `hotel_vibes`, `hotel_concierge`, `hotel_celesta`, `hotel_harp`, `hotel_rhodes`, `hotel_acoustic`, `hotel_suite` (10種)
     - 【和風・伝統・癒やし】: `chime_zen`, `chime_koto`, `zen_rin`, `zen_hyoshigi`, `zen_suikinkutsu`, `zen_windchime`, `zen_bamboo`, `zen_miyabi`, `zen_shakuhachi`, `zen_taiko` (10種)
     - 【スマートホーム・近未来】: `chime_cyber`, `chime_digital`, `cyber_assist`, `cyber_pulse`, `cyber_warp`, `cyber_synapse`, `cyber_hologram`, `cyber_quantum`, `cyber_laser`, `cyber_blip` (10種)
     - 【オルゴール・リラックス】: `chime_musicbox`, `relax_kalimba`, `relax_crystal`, `relax_lullaby`, `relax_starlight`, `relax_chime`, `relax_dream`, `relax_meadow`, `relax_twinkle`, `relax_calm` (10種)
     - 【案内・注意喚起】: `chime_airport`, `announce`, `bell`, `alert`, `notice_broadcast`, `notice_train`, `notice_school`, `notice_info`, `notice_chime3`, `notice_urgent` (10種)
     - 【その他】: `none` (前置きチャイムなし)
  2. `app/services/tts_service.py`:
     - `ALLOWED_CHIMES` ホワイトリストに全60個のチャイムIDおよびMP3ファイル名マッピングを登録。
  3. `app/routers/settings.py`:
     - `CHIME_CATALOG` に全60個（＋none）の定義を登録。
  4. `public/index.html`:
     - 「テーマ別チャイム試聴ボード (`chimeCatalogContainer`)」カードを削除し、UIをコンパクトに集約。
     - 「標準チャイム音 (`settingDefaultChime`)」およびWebhookビルダーの「前置きチャイム音 (`builderChime`)」の各 `<optgroup>` に全60種（各テーマ10種ずつ）を完備。
     - セレクトボックス横の「▶ 試聴 / ⏹ 停止」ボタンを残し、選択したチャイム音の確認を可能にした。
     - キャッシュバスターを `v=3.1` に更新。
  5. `public/app.js`:
     - 試聴ボードDOM構築コード（`renderChimeCatalog`）およびカードクリックイベントを削除し、コードを軽量化。
     - セレクトボックス横の試聴ボタン制御（`updateChimePreviewButton`）およびセレクト変更時の停止制御を最適化。
     - `node -c` による構文検証をパス。
  6. `public/style.css`:
     - 試聴ボード専用のCSS（`.chime-catalog-container`, `.chime-card` 等）を削除。
  7. `tests/test_smoke.py`:
     - `test_chimes_catalog_and_files` を強化し、各テーマが正確に10個ずつ定義されていること、および `ALLOWED_CHIMES` 全60個の実ファイルが存在することを自動検証。
- **検証結果**:
  - `docker exec -e PYTHONPATH=/app SmartSpeaker-VoiceHub pytest`: 全22テストすべて合格 (4.21s)。
  - `python3 -m unittest tests/test_smoke.py`: 全15テストすべて合格 (2.86s)。
  - `GET /api/chimes` で 6テーマ×各10種＋none が返却されることを実機確認。

## 2026-10-20 18:25 - 前置きチャイム音のテーマ別バリエーション拡充と試聴ボード（聞き比べ・即時設定）の実装
- **背景と課題**:
  1. 発話前の前置きチャイム音のバリエーションを増やし、シーンやインテリア・用途に合わせたテーマ別の音源から好みのものを選択したいという要望があった。
  2. WebUI上で実際に各チャイム音を試聴・聞き比べしながら、ワンクリックでデフォルトチャイムに設定できる方式（試聴ボード）が求められていた。
- **修正内容**:
  1. `public/sound/` (新規9種を合成・配備、既存と合わせ全13種):
     - 【標準・日常】: `dingdong.mp3` (既存 1.8s), `chime_simple.mp3` (爽やか2音 1.1s)
     - 【ホテル・高級ラウンジ】: `chime_hotel.mp3` (優雅な4音ロビーベル 2.2s), `chime_marimba.mp3` (あたたかい木琴3音 1.5s)
     - 【和風・癒やし】: `chime_zen.mp3` (水琴窟・おりんの澄んだ響き 2.3s), `chime_koto.mp3` (雅な都節2音 1.6s)
     - 【スマートホーム・近未来】: `chime_cyber.mp3` (近未来ガジェット風ピロリン 1.1s), `chime_digital.mp3` (クリア高音短音 0.9s)
     - 【オルゴール・リラックス】: `chime_musicbox.mp3` (やさしいキラキラ3音 1.9s)
     - 【案内・注意喚起】: `chime_airport.mp3` (空港・駅3点 1.9s), `announce.mp3` (既存 1.7s), `bell.mp3` (既存 1.4s), `alert.mp3` (既存 0.8s)
     - 【その他】: `none` (前置きチャイムなし)
  2. `app/services/tts_service.py`:
     - トップレベル定数 `ALLOWED_CHIMES: Dict[str, str]` を定義し、全13種類のチャイムファイル名マッピングを一元管理。
     - `_synthesize_with_chime` 内でホワイトリスト照合を行い、Path Injectionを構造的に防止しつつ FFmpeg concat で結合。
  3. `app/routers/settings.py`:
     - `CHIME_CATALOG` 定義および `GET /api/chimes` エンドポイントを新設。現在設定中のチャイムIDと、テーマ別に分類された全チャイムのメタデータ（ID、名称、説明、アイコン）を返却。
  4. `public/index.html`:
     - 設定画面の「デフォルト前置きチャイム (`settingDefaultChime`)」およびWebhookビルダーの「前置きチャイム (`builderChime`)」をテーマ別 `<optgroup>` で整理。
     - チャイム設定欄の直下に「🎵 チャイム音聞き比べ・試聴ボード (`chimeCatalogContainer`)」カードを新設。
     - キャッシュバスターを `v=3.0` に更新。
  5. `public/style.css`:
     - チャイム試聴ボード用のスタイル（グリッドカード、試聴ボタン、再生中イコライザーパルスアニメーション、デフォルト設定済みバッジ）を追加。
  6. `public/app.js`:
     - `CHIME_CATALOG` 定義、`loadChimes()`、`renderChimeCatalog()`、`playChimePreview()`、`stopChimePreview()` を実装。
     - 試聴カードから「▶ 試聴」と「✓ これにする」をワンクリック操作可能にし、選択時は設定を即時保存＆全セレクトボックスへ同期。
  7. `tests/test_smoke.py`:
     - `test_chimes_catalog_and_files` を追加。APIレスポンス、ホワイトリスト整合性、および `public/sound/*.mp3` の実体存在を網羅的に自動検証。
- **検証結果**:
  - `docker exec -e PYTHONPATH=/app SmartSpeaker-VoiceHub pytest`: 全22テスト合格 (4.15s)。
  - `GET /api/chimes` および各 `/sound/*.mp3` の HTTP 200 OK を確認済み。

## 2026-10-20 18:08 - お気に入り機能の実装（接続デバイス一覧でのグレー☆/★表示、即時発言・送信先スピーカー一覧での最優先配置）
- **背景と課題**:
  1. 接続デバイス数が増えた環境において、よく利用する特定のスピーカー（例: リビング、自室、Tapo等）を素早く選択したいという要望があった。
  2. 接続デバイス一覧カード上で、名前の横にグレーの「☆」（未選択）と選択時の「★」（お気に入り）を表示し、ワンクリックで登録・解除できるUIが必要とされていた。
  3. お気に入り登録されたデバイスは、即時発言や各種送信先スピーカー一覧（スケジュール、カレンダー、DND、防災、Webhookビルダー等）が並ぶ際に一番最初（最優先）に並ぶことが求められていた。
- **修正内容**:
  1. `app/services/settings_service.py`:
     - `DEFAULT_SETTINGS` および `OVERWRITE_COLLECTIONS` に `favoriteDevices: []` を追加。
     - `SettingsManager` に `get_favorite_devices()`、`set_favorite_devices()`、`toggle_favorite_device()` を実装し、`settings.json` へ永続化。
  2. `app/services/devices_service.py`:
     - `get_devices()` で永続化されたお気に入りデバイスリストを取得し、各デバイス辞書に `isFavorite: bool` フラグを付与。
     - ソート順序をお気に入り最優先（`0 if d.get("isFavorite") else 1`）に更新し、バックエンドから返却される段階で先頭に来るよう制御。
  3. `app/routers/devices.py`:
     - `GET /api/devices` および `POST /api/devices/rescan-all` のレスポンスに `favorites` 配列を含めるよう拡張。
     - `GET /api/devices/favorites`、`POST /api/devices/favorites`、`POST /api/devices/favorite/toggle` エンドポイントを新設。
  4. `public/app.js`:
     - `state.favoriteDevices = []` を追加し、`loadDevices` でサーバー値および localStorage から初期化。
     - `isDeviceFavorite(dev)` ヘルパー関数を新設。
     - `sortDevicesList(devices)` にお気に入り最優先ソート（お気に入り -> カテゴリ順 -> デフォルト優先 -> 名前順）を組み込み。
     - `renderDevicesGrid()` の各デバイスカードヘッダーで、デバイス名の横に `.btn-fav-star`（未選択: グレーの☆、選択時: ゴールドの★）を配置。
     - `toggleDeviceFavorite(ip, name)` を新設。クリック時にローカル状態とお気に入りフラグを即時更新し、`sortDevicesList` で並び替えて接続デバイス一覧・即時発言・全セレクターを即時再描画し、トースト通知を表示しつつバックエンドへ非同期保存。
     - `renderSpeakersCheckboxes()`（即時発言含む全スピーカーセレクター）および `renderBuilderSpeakers()` で、お気に入りデバイスのチップに `is-favorite` クラスおよびゴールドの「★」バッジを付与。
  5. `public/style.css`:
     - `.btn-fav-star` のスタイリングを追加（グレーの☆、ホバー拡大アニメーション、選択時のゴールド★とグロー効果）。
     - `.device-card.favorite-dev`、`.device-tag.fav`、`.speaker-chip-badge.fav-badge`、`.speaker-chip.favorite-chip` のスタイルを追加。
  6. `public/index.html`:
     - `app.js?v=2.9` および `style.css?v=2.9` にキャッシュバスターを更新。
  7. `tests/test_smoke.py`:
     - `test_favorite_devices_settings_and_api` を追加。CRUD、トグルAPI、お気に入り最優先ソート順序を網羅的に検証。
- **検証結果**:
  - `docker exec -e PYTHONPATH=/app SmartSpeaker-VoiceHub pytest tests/`: 全21テスト合格 (4.24s)。
  - 実機APIテスト（`POST /api/devices/favorite/toggle`、`GET /api/devices`）: お気に入り登録されたデバイスが最前列（1番目）に配置され、解除後に元の順序に戻ることを実機コンテナで確認済み。

## 2026-10-20 16:48 - DND保留解除時の発言履歴ステータス自動更新（保留中解除・送信成功化）
- **背景と課題**:
  1. DND（おやすみ・会議モード）発動中に受け付けた通知は「DND保留中 (`status: queued`)」として発言履歴（`speak.log` およびメモリ履歴）に記録される。
  2. DNDが解除されて保留キューから発話再生された後も、元の発言履歴レコードのステータスが `queued` のまま残留し、WebUIの「DND保留中」バッジが外れず、「⏳ DND保留中」フィルターにも抽出され続けてしまう課題があった。
- **修正内容**:
  1. `app/core/log_rotator.py`:
     - `SpeakLogRotator` に `update_entry(entry_id, updates)` および `update_entries(updates_map)` を追加。`speak.log`（アクティブファイル）内の既存エントリをアトミックに更新可能にした。
  2. `app/services/history_service.py`:
     - `HistoryManager` に `update_entry`、`update_entries`、`mark_queued_as_released` を実装。メモリ上の履歴、`speak.log`、`history.json` を同期更新。
  3. `app/services/speech_service.py`:
     - DND保留時に生成された履歴ID（`hist_...`）をキューデータに `history_id` として紐付け。
     - `speak` メソッドに `existing_history_id` 引数を追加。保留キューからの再生時は新規履歴を追加せず、既存の保留レコードを「送信成功（DND保留再生）」へとステータス更新するよう改善。
  4. `app/services/dnd_service.py`:
     - `check_and_flush_queue` での個別再生時に `existing_history_id` を渡して再生。
     - AI要約再生時には、要約発話を新規記録しつつ、保留されていた各元エントリ群のステータスを `mark_queued_as_released` で「送信成功（DND保留再生）」へ一括更新。
     - `_call_speaker` を新設し、カスタムのスピーカー関数に対しても kwargs を安全に渡せるよう引数フィルタリングを実装。
  5. `tests/test_speak_log.py` & `tests/test_smoke.py`:
     - 保留解除時のステータス更新・永続化検証テストを追加。
- **検証結果**:
  - `python3 -m unittest discover -s tests -p "test_*.py"`: 全20テストすべて合格 (2.31s)。
  - `pytest`: 全20テストすべて合格 (3.55s)。

## 2026-10-20 15:37 - CI環境テスト互換性向上（pytest依存排除・unittest.TestCase標準化）
- **背景と課題**:
  1. GitHub Actions の Docker ビルド・公開ワークフロー（`docker-publish.yml`）内の単体テストステップにおいて、`python3 -m unittest discover -s tests -p "test_*.py"` が実行されていた。
  2. 新設した `tests/test_speak_log.py` および `tests/test_tapo.py` が `import pytest` に依存していたため、本番コンテナ（pytest未同梱）内で `ModuleNotFoundError: No module named 'pytest'` が発生しCIが失敗していた。
- **修正内容**:
  1. `tests/test_speak_log.py`:
     - 標準ライブラリの `unittest.TestCase` ベースにリファクタリング。`tmp_path` fixture を `tempfile.TemporaryDirectory()` に移行。
  2. `tests/test_tapo.py`:
     - `unittest.TestCase` ベースにリファクタリング。`setUp` / `tearDown` による設定退避・復元を実装し、テスト内でも `derive_tapo_auth_token` を活用。
- **検証結果**:
  - `python3 -m unittest discover -s tests -p "test_*.py"`: 全18テスト合格 (1.75s)。
  - `pytest`: 全18テスト合格 (3.03s)。

## 2026-10-20 15:30 - GitHub Code Scanning アラート対処（mktemp廃止、Tapoトークン導出関数の集約）
- **背景と課題**:
  1. GitHub Code Scanning（CodeQL）において、オープンなアラートが 5 件検出されていた：
     - #20, #21: `tests/test_smoke.py` で非推奨かつ安全でない `tempfile.mktemp()` が使用されている (`py/insecure-temporary-file`)。
     - #22, #23, #24: `app/routers/onvif_dlna.py` および `app/services/onvif_service.py` で `hashlib.sha256()` がセンシティブデータに対して直接使用されている (`py/weak-sensitive-data-hashing`)。
  2. #22〜#24 は一般的なパスワード保管ではなく、TP-Link Tapo の双方向音声通話プロトコル（ポート8800）の規格仕様が要求する認証トークン生成（`SHA256(password).upper()`）であるため、アルゴリズムの変更はハードウェア通信上不可能。
- **修正内容**:
  1. `tests/test_smoke.py`:
     - 非推奨な `tempfile.mktemp()` を完全排除し、標準的な `tempfile.TemporaryDirectory()` コンテキストマネージャによる安全な一時ディレクトリ・ファイル作成へ移行（アラート #20, #21 を解消）。
  2. `app/core/security.py`:
     - `derive_tapo_auth_token(token_or_secret: str) -> str` を新設。外部機器プロトコル規格に準拠したトークン導出処理であることを明記し集約。
  3. `app/routers/onvif_dlna.py` & `app/services/onvif_service.py`:
     - 散在していた `hashlib.sha256` 直接呼び出しコードを排除し、`derive_tapo_auth_token` の呼び出しに一元化。
- **検証結果**:
  - 全 18 件のユニットテストすべてパス。

- **背景と課題**:
  1. `pytapo` によるカメラ別名（`device_alias`: ウッドスロープ、ウッドデッキ、リビングTapo等）の取得には、カメラ本体のローカル認証ではなくユーザーの TP-Link ID（メールアドレス）とクラウドパスワードが必要であった。
  2. 従来の WebUI にはパスワード入力欄しかなくメールアドレス欄が存在しなかったため、WebUI から TP-Link ID（メールアドレス）とパスワードの双方を入力・保存できるように拡張。
  3. これにより、スキャン探索時にも未登録カメラの日本語カスタム名を自動取得して表示・登録できるように改修。
- **修正内容**:
  1. `public/index.html`:
     - `#tapoAuthAccordion` の認証入力フォームに「TP-Link ID (メールアドレス)」入力欄（`#tapoCloudEmail`）を追加。
     - キャッシュバスターを `app.js?v=2.8` に更新。
  2. `public/app.js`:
     - `refreshTapoAuthStatus` で保存済み `tapoEmail` を自動ロード・バッジ表示（`🔒 クラウド認証設定済み (user@example.com)`）。
     - `btnSaveTapoAuth` で `email` と `password` を `/api/onvif/tapo-auth` に送信・保存。
  3. `app/routers/onvif_dlna.py`:
     - `TapoAuthRequest` に `email` フィールドを追加。
     - `POST /api/onvif/tapo-auth` で `tapoEmail` と `tapoPassword`（および音声通話用 `tapoPasswordHash`）を保存。
     - `GET /api/onvif/config` で `tapoEmail` を返却。
  4. `app/services/onvif_service.py`:
     - `_fetch_tapo_alias_sync` を正しく改修し、メールアドレスとクラウドパスワードで `pytapo` から `device_alias` を取得。
     - スキャン時に `custom_name` として自動反映。
  5. `tests/test_tapo.py`:
     - `email` を含めた保存・取得のユニットテストを更新。
- **検証結果**:
  - 全 18 件のユニットテストすべてパス。
  - 実機（211: ウッドスロープ、212: ウッドデッキ、235: リビングTapo）が接続デバイス一覧で完璧に表示されることを確認。

- **背景と課題**:
  1. 接続デバイス一覧（`#tab-devices`）において、Tapo や ONVIF が `Google Home` タグ扱いになってしまう不具合が発生していた。また、Reolink カメラは ONVIF スコープから名前が引けるのに対し、Tapo はメーカー仕様上 ONVIF 応答に機種名（C320WS等）しか返さず、ポート 443 経由の取得はカメラの一時ロック（30分間停止）を招くため、名前解決と安全な識別表示の改善が求められた。
  2. 設定画面の「サイレント履歴ログ」は機能しておらず不要なため完全撤去。
  3. 発言履歴ログのフィルターバーに、DND保留中キューのみを絞り込める選択肢ピル「⏳ DND保留中 (`queued`)」を常設追加（A案採択）。
  4. 発言履歴の永続化先として `/logs/speak.log` を新設し、1行1JSON（JSON Lines形式）で記録。既存の `container.log` と同一のローテーション仕様（1,000行または日次で `speak-archive.log` へ退避追記、100MB超で `.zst` 圧縮世代管理）を統合し、WebUI および API が最新100件を取得できるように改修。
- **修正内容**:
  1. `app/services/onvif_service.py`:
     - `_fetch_tapo_alias_sync` でのポート443アクセスを完全停止（不可逆ハッシュでの認証失敗によるカメラ30分ロックを防止）。
     - スキャン時（`scan_devices`）、登録済み機器（`registeredDevices`）があればその名前（例:「リビングTapo」）を最優先。未登録の Tapo は機種名とIP末尾を組み合わせた `Tapo {model} (.{ip末尾})`（例: `Tapo C320WS (.211)`）を付与し、探索結果やモーダルで即座に識別可能にした。
  2. `public/index.html` & `public/app.js`:
     - 接続デバイス一覧（`renderDevicesGrid`）のタグ判定を整理し、`isTapo`（`📹 Tapo`）、`isOnvif`（`📷 ONVIF`）、`isDlna`（`🎵 DLNA`）を適用。Google Home への誤判定を徹底防止。
     - キャッシュバスターを `app.js?v=2.7` に更新し、ブラウザキャッシュによる旧表示をクリア。
     - 設定タブ（DND設定サブタブ）から「サイレント履歴ログ」カードHTML、および関連JS関数（`loadDndHistory`, `renderDndHistory`, `btnClearDndHistory`）を完全撤去。
     - 発言履歴ログのフィルターボタングループ（`#historyFilterGroup`）に `<button type="button" class="history-filter-pill" data-filter="queued">⏳ DND保留中</button>` を新設。`renderFullHistory` に `state.historyFilter === 'queued'`（`item.status === 'queued'`）絞り込み処理を追加。
  3. `app/core/log_rotator.py`:
     - `SpeakLogRotator` クラスおよびシングルトンゲッター `get_speak_log_rotator()` を新設。
     - `/logs/speak.log` への 1行1JSON 追記、1,000行または日次での `speak-archive.log` への退避追記、100MB 超過時の `.zst` 圧縮世代管理（最大10世代）、末尾からの最新エントリ高速読み出し（`read_latest_entries(limit=100)`）を実装。
  4. `app/services/history_service.py`:
     - `HistoryManager` を `SpeakLogRotator` と連携するように改修。
     - 初回起動時、既存の `data/history.json` があれば自動で `speak.log` にインポートして過去履歴をシームレスに継承。
     - `add_entry` 時に `speak.log` へのリアルタイム JSONL 追記を実行。
  5. `tests/test_speak_log.py`:
     - `SpeakLogRotator` の JSONL 書き込み、ローテーション、最新件数逆順読み出し、および `HistoryManager` 連携を検証するユニットテストを新設。
- **検証結果**:
  1. ユニットテスト全 18 件（`test_speak_log.py`, `test_tapo.py`, `test_smoke.py`）が全て正常パス。
  2. コンテナ再起動（`docker restart SmartSpeaker-VoiceHub`）後、旧 `history.json` から `/logs/speak.log` への自動移行（約82KB）が瞬時に完了することを確認。
  3. 実機発声テストを実行し、`/logs/speak.log` の末尾に最新発言レコードが即座に追記され、`/api/history?limit=3` でも最新エントリとして正常に返却されることを確認。
  4. 接続デバイス一覧（`/api/devices`）で Tapo 3台（`リビングTapo`, `C320WS (.211)`, `C320WS (.212)`）が `type: tapo` として正常認識されていることを確認。

- **背景と課題**:
  1. TP-Link Tapo カメラ（C212 等）は公式規格上 ONVIF Profile S 準拠のため規格上の RTSP バックチャネル（Profile T）を持たず、VoiceHub からスピーカー出力（TTS・効果音）を行えなかった。
  2. Tapo 独自通話プロトコル（ポート8800 / `tapo://`）を活用することで Profile S 機種でもスピーカー音声再生が可能であることが実証された。
  3. 認証情報のセキュリティ確保のため、平文パスワードはファイルに一切保存せず、不可逆な SHA256 大文字ハッシュのみで通信・永続化する方針を採用。
  4. ONVIF WS-Discovery では固定機種名（C212）しか取得できない課題に対し、管理ポート（443 / `pytapo`）からユーザー命名の `device_alias`（例:「リビングTapo」）を自動取得して補完する仕組みを実装。
- **修正内容**:
  1. `requirements.txt`:
     - `pytapo>=3.3.43` を追加。
  2. `app/services/onvif_service.py`:
     - `_fetch_tapo_alias_sync`: `pytapo` 経由でポート 443 から `device_alias` を取得。
     - `scan_devices`: ポート 2020 / モデル / スコープ等から Tapo を判定し、`type: "tapo"`、`model: "C212 (Tapo)"`、`friendlyName: "リビングTapo"` を自動付与。
     - `_play_tapo_audio`: go2rtc へ `tapo://admin:{password_hash}@{ip}` を動的登録し、PCMA（8000Hz mono G.711 A-law）ストリームをプッシュ、再生完了後に自動クリーンアップ。
  3. `app/routers/onvif_dlna.py`:
     - `POST /api/onvif/tapo-auth`: クラウドパスワードを即時 SHA256 大文字ハッシュ化して保存（平文は完全破棄）。
     - `GET /api/onvif/config`: `tapoAuthConfigured` 判定の返却。
     - `POST /api/onvif/register`: `type == "tapo"` の場合、パスワードをハッシュ化して平文は破棄。
  4. `app/services/devices_service.py` & `app/services/speech_service.py`:
     - `tapo:` プレフィックスの認識、カテゴリソート順への追加、`CAM:ALL` / `TAPO:ALL` マクロ展開とディスパッチへの統合。
     - `speech_service.resolve_targets` の独立メソッド化。
  5. `public/index.html` & `public/style.css` & `public/app.js`:
     - デフォルトONVIF設定枠直下に Tapo クラウド認証アコーディオン（`#tapoAuthAccordion`）を配置。Tapoアプリの「わたし ＞ Tapo Lab ＞ サードパーティ互換性」を ON にする事前設定の注意喚起ボックスを設置。
     - 手動登録セレクトへの Tapo カメラ追加、登録モーダルでの Tapo 用UI切り替え（ユーザー名admin固定、パスワード空欄時共通ハッシュ使用ヒント）。
     - ターコイズ/シアン系の `.speaker-chip-badge.tapo-badge` および `.speaker-chip.tapo-chip.checked` を新設し、トップ画面スピーカーチップや検出一覧、登録一覧へ統合。
  6. `tests/test_tapo.py`:
     - SHA256ハッシュ保存（平文不保持）、設定取得、デバイス認識、マクロ展開を検証するユニットテストを新設（fixture による設定保護対応）。
- **検証結果**:
  1. 実機 Tapo（192.168.11.235 / C212 2.0 / `device_alias: "リビングTapo"`）へのテスト発声および `/api/say` からのルーティング発声が HTTP 200 で正常終了、クリアな音声出力を確認。
  2. ユニットテスト全 15 件（`test_smoke.py`, `test_tapo.py`）が全て正常パス。
  3. WebUI 上で Tapo 認証ハッシュ保存、登録、スピーカーチップ描画が正常に機能することを確認。

## 2026-10-20 11:45 - Homebridge プラグイン 1.0.3 へのバージョン引き上げと、Homebridge UI 向けルート CHANGELOG.md の新規整備
- **背景と課題**:
  1. Homebridge Config UI X 上でプラグイン更新時にリリースノートや変更履歴が空になっていた問題について調査を実施。
  2. Homebridge UI のソースコード解析により、UI はリポジトリルート直下の `/CHANGELOG.md` を取得する仕様であることが判明。モノレポ構成のためルートにファイルが存在しなかったことが原因であった。
  3. また、先ほど Homebridge v2.0 対応メタデータ（`engines.homebridge`, `keywords`）を更新したため、npm レジストリへの反映にはバージョンを `1.0.3` に引き上げる必要があった。
- **修正内容**:
  1. `CHANGELOG.md`:
     - リポジトリのルート直下に新規作成。Homebridge Config UI X がどのバージョンからでも確実にパース・表示できるよう、全バージョン（1.0.0〜1.0.3）の変更履歴を標準フォーマットで集約。
  2. `plugins/homebridge-voicehub/package.json` & `package-lock.json`:
     - バージョンを `1.0.2` から `1.0.3` へインクリメント。
  3. `plugins/homebridge-voicehub/CHANGELOG.md`:
     - `1.0.3`（Homebridge v2.0 対応メタデータ追加）のエントリを追記。
  5. Git コミットおよび GitHub リモート（`origin/main`）へのプッシュ完了。
  6. GitHub CLI（`gh release create`）により、`v1.0.2` および `v1.0.3`（Latest）の GitHub Releases を正式発行。
  7. npm レジストリへ `homebridge-voicehub@1.0.3` を正式公開（`npm publish` 成功）。
- **検証結果**:
  1. プラグインの TypeScript コンパイル正常終了。
  2. 単体テスト全 13 件が正常パスすることを確認。
  3. GitHub Releases ページおよび raw URL（`https://raw.githubusercontent.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/HEAD/CHANGELOG.md`）が正常疎通することを確認。
  4. npm レジストリへの `1.0.3` パッケージアップロード成功確認。

## 2026-10-20 11:35 - Python 3.14 標準ライブラリ compression.zstd 移行に伴う不要外部パッケージ削除と Homebridge v2.0 互換性メタデータ対応
- **背景と課題**:
  1. OSS 依存関係の健全性調査（`scratch/oss.md`）により、サードパーティ製 `zstandard` パッケージについて、ベースイメージ（Python 3.14）で標準ライブラリ `compression.zstd` (PEP 784) に正式統合されたため外部パッケージが不要であることが確認された。
  2. 実装精査の結果、単なる未使用ではなく `app/core/log_rotator.py` で `zstandard` の固有 API（`cctx.copy_stream`）が利用されていたため、外部パッケージ削除前に標準ライブラリ `compression.zstd`（`zstd.open` + `shutil.copyfileobj`）へ安全に移行させる必要があった。
  3. Homebridge プラグイン（`plugins/homebridge-voicehub`）において、Homebridge v2.0 環境の公式 UI で「Verified / 互換性あり」判定を受けるためのメタデータ（`engines.homebridge`, `keywords`）が未対応だった。
- **修正内容**:
  1. `app/core/log_rotator.py`:
     - `compress_file_zstd()` を改修し、Python 3.14 標準ライブラリ `compression.zstd` を最優先で利用するストリーム圧縮へ更新。
     - サードパーティ製 `zstandard`、OS コマンド（`/usr/bin/zstd`）、`gzip` へのフォールバックチェーンを維持。
  2. `requirements.txt`:
     - 外部パッケージ `zstandard>=0.25.0` を削除。
  3. `THIRD_PARTY_LICENSES.md`:
     - 外部 pip 依存ライブラリ一覧から `zstandard` を整理。
  4. `plugins/homebridge-voicehub/package.json`:
     - `engines.homebridge` を `"^1.6.0 || ^2.0.0"` に更新。
     - `keywords` に `"supports-hap"` を追加。
  5. `tests/test_smoke.py`:
     - `test_compress_file_zstd` を新規追加し、標準ライブラリによる zstd 圧縮・伸長が正確に動作することを自動テスト化。
- **検証結果**:
  1. `tests/test_smoke.py`: 全 13 件のユニットテストがすべて正常パス。
  2. `plugins/homebridge-voicehub`: `npm run build` による TypeScript コンパイルが正常完了。

## 2026-10-20 07:52 - Dependabot PR（#15, #16, #17）の一括マージと、PR 実行時 Docker イメージタグ構文エラーの完全解消
- **背景と課題**:
  1. Dependabot より届いた 3 件のまとめ PR（#16: GitHub Actions、#15: Homebridge npm、#17: Python pip 依存関係）について、全テストおよび TypeScript ビルドの合格を確認した上で一括マージを実施。
  2. PR 実行時の CI において、GitHub のセキュリティ制限により Secrets（`DOCKERHUB_USERNAME`）が空文字となり、イメージタグ名が `/smarthomespeaker-voicehub:sha-xxx` となって Docker buildx が構文エラーで失敗する問題が発覚した。
- **修正内容**:
  1. GitHub CLI（`gh pr merge --squash --delete-branch`）により PR #16, #15, #17 をすべてスカッシュマージし、リモートブランチを自動削除。
  2. `.github/workflows/docker-publish.yml`:
     - `DOCKER_USER=${DOCKER_USER:-madpiero}` を追加し、PR 実行時など Secrets が注入されない環境でも既定ユーザー名（`madpiero`）へ安全にフォールバックするよう修正。
- **検証結果**:
  1. Python `yaml.safe_load` によるワークフロー構文検証合格。
  2. ローカルでの単体テスト全12件が正常パスすることを確認。

## 2026-10-20 07:40 - Dependabot の全グループ化集約と PR 上限引き上げ、および不足ラベルの完全整備
- **背景と課題**:
  1. Dependabot 初回実行時、`update-types: ["minor", "patch"]` 指定によってメジャーアップデートや 0.x 系ライブラリ（FastAPI、HTTPX、Edge-TTS 等）がグループ外判定となり、pip だけで 10 件の個別 PR が生成され上限エラー（`open pull request limit has been exceeded: 10`）が発生した。
  2. また、リポジトリに `dependencies`, `python`, `docker`, `github-actions`, `homebridge` ラベルが存在せず、Dependabot からラベル未検出の警告コメントが投稿されていた。
- **修正内容**:
  1. `gh label create` により不足していた各ラベル（`dependencies`, `python`, `github-actions`, `docker`, `homebridge`）を完全作成。
  2. `.github/dependabot.yml`:
     - `pip` および `npm` のグループ設定から `update-types` を撤廃し、`patterns: ["*"]` に統一。
     - 各エコシステム（GitHub Actions, Python pip, Docker, Homebridge npm）ごとにすべての更新がそれぞれ 1 つのまとめ PR（Grouped PR）に完全集約されるよう設定。
     - `open-pull-requests-limit` を 10 から 20 に引き上げ、制限による中断を防止。
- **検証結果**:
  1. Python `yaml.safe_load` による構文チェック合格。
  2. GitHub Labels 一覧に全ラベルが登録されたことを確認。

## 2026-10-20 02:21 - 最適な Dependabot 設定（.github/dependabot.yml）の新規作成
- **背景と課題**:
  1. プロジェクト内の依存パッケージ（GitHub Actions、Python pip、Dockerfile ベースイメージ、Homebridge npm）の自動セキュリティ更新およびバージョン追従を安全かつ効率的に行うための Dependabot 設定が未整備だった。
  2. 単発 PR が大量に作成されて運用負荷（PR 爆発）とならないよう、グループ化（Grouped Updates）および週次スケジュールを適切に設計する必要があった。
- **修正内容**:
  1. `.github/dependabot.yml` を新規作成：
     - **GitHub Actions**: ワークフロー内アクションの週次更新（全アクションを 1 PR に集約）。
     - **pip (Python)**: `requirements.txt` の週次更新（マイナー・パッチをグループ化、メジャーは単独 PR）。
     - **Docker**: `Dockerfile` ベースイメージの週次更新。
     - **npm (Homebridge)**: `plugins/homebridge-voicehub` の週次更新（マイナー・パッチをグループ化）。
     - タイムゾーン `Asia/Tokyo`、毎週月曜 09:00 実行。
     - Conventional Commits（`ci(deps):`, `build(deps):`）およびラベル自動付与。
- **検証結果**:
  1. Python `yaml.safe_load` による YAML 構文検証をパス。

## 2026-10-20 02:15 - 公開 Docker イメージ名を実環境（madpiero/smarthomespeaker-voicehub）に統一
- **背景と課題**:
  1. Docker Hub 上の公式公開リポジトリが `madpiero/smarthomespeaker-voicehub` として作成・公開（Public）されていたが、リポジトリ内の `docker-compose.yml` および `README.md` では `maximilian2022/smarthomespeaker-voicehub` と記述されていた。
  2. 一般ユーザーが `docker-compose.yml` をダウンロードして `docker compose up -d` を実行した際にイメージが見つからない不整合を防ぐため、実在する公式イメージ名に完全統一する必要があった。
- **修正内容**:
  1. `docker-compose.yml`:
     - `image: maximilian2022/smarthomespeaker-voicehub:latest` を `image: madpiero/smarthomespeaker-voicehub:latest` に修正。
  2. `README.md`:
     - はじめかたセクションの記載に Docker Hub（`madpiero/smarthomespeaker-voicehub`）への直接リンクを追加。
- **検証結果**:
  1. Docker Hub API（`https://hub.docker.com/v2/repositories/madpiero/smarthomespeaker-voicehub/`）にてイメージが実在し、`latest`, `1.0.0` のタグが存在することを確認。
  2. ユニットテスト全12件が正常パスすることを確認。

## 2026-10-20 01:47 - GitHub Actions による GitHub Release 自動発行ジョブの追加
- **背景と課題**:
  1. Docker Hub へのマルチアーキテクチャイメージ自動ビルド・Push（`.github/workflows/docker-publish.yml`）は整備されていたが、Git タグ（`v*.*.*`）をプッシュした際に GitHub の Releases ページに自動でリリースノートやバージョンを発行する仕組みがなかった。
  2. 手動で Releases ページから変更履歴を書いて公開する手間を省き、タグのプッシュをトリガーとしてテスト、Docker Hub Push、GitHub Release 作成を一連のパイプラインとして完全自動化することが求められた。
- **修正内容**:
  1. `.github/workflows/docker-publish.yml`:
     - ワークフロー名を `Build, Push Docker Image & Release` に更新。
     - `release` ジョブを新規追加：
       - `needs: [test, docker]` により、ユニットテストおよび Docker Hub へのビルド・Push が完全に成功した場合のみ実行。
       - `if: startsWith(github.ref, 'refs/tags/v')` により、タグプッシュ時のみ実行。
       - `permissions: contents: write` を付与し、安全な最小権限でリリース作成を許可。
       - `softprops/action-gh-release@v2` を採用し、`generate_release_notes: true` を指定することで、前回のリリース以降のマージされた PR やコミット履歴から GitHub 公式の変更履歴（Changelog）を自動生成して公開。
- **検証結果**:
  1. Python `yaml.safe_load` による YAML 構文検証をパス。
  2. 既存のユニットテスト（全12件）が正常に合格することを確認。

## 2026-10-20 01:32 - Azure 有効時のデフォルト話者（Azure Nanami）自動選択と未選択ブランク不具合の完全解消
- **背景と課題**:
  1. Azure Speech が有効化されている環境において、Edge-TTS は通常選択肢から除外され最終フォールバック待機となる設計となっていたが、WebUI の話者選択ドロップダウン（`sayVoiceSelect` 等）を開いた際に話者が未選択（ブランク・空）になってしまう現象が発生していた。
  2. 原因調査の結果：
     - バックエンドの `/api/voices` が Azure 有効時にも関わらず、固定の `settings.default_voice`（`ja-JP-NanamiNeural`、Edge-TTS 形式）を返していた。
     - フロントエンド `public/app.js` の `renderVoiceSelects` において、`state.ttsProvidersStatus` がセットされておらず `isAzureActive = false` と誤認し、Azure 話者（`azure:ja-JP-NanamiNeural`）に `selected` 属性が付与されなかった。
     - さらに、セレクトボックス値の復元処理で、既存値（古い `ja-JP-NanamiNeural`）が新しい選択肢一覧に存在しない場合に代入に失敗し、ブラウザによって未選択状態にクリアされていた。
     - `speech_service.py` でも、`voice` 未指定時に固定値 `"ja-JP-NanamiNeural"` を使っていた。
- **修正内容**:
  1. `app/services/tts_service.py`:
     - `get_default_voice_id()` メソッドを追加。Azure 有効時は `self.azure_provider.default_voice_id`（`azure:ja-JP-NanamiNeural`）、GCP 有効時は `self.gcp_provider.default_voice_id`、それ以外は `self.edge_provider.default_voice_id` を動的に返却。
  2. `app/routers/status.py`:
     - `/api/voices` で動的な `defaultVoice: tts_service.get_default_voice_id()` および `isAzureActive: tts_service.is_azure_active()` を返却するように修正。
  3. `app/services/speech_service.py`:
     - `voice` 未指定時のデフォルト音声フォールバックを、固定値から `tts_service.get_default_voice_id()` に統一。
  4. `public/app.js`:
     - `loadVoices()` で `defaultVoice` および `isAzureActive` を `state` に確実に保持。
     - `loadTtsProvidersSettings()` で `state.ttsProvidersStatus` および `state.isAzureActive` をセット。
     - `renderVoiceSelects()` で、Azure 有効時は `azure:ja-JP-NanamiNeural` をデフォルト選択。
     - `setSelectValueSafely` ヘルパーを導入し、既存値が選択肢に存在しない場合は自動的にアクティブなデフォルト話者（`azure:ja-JP-NanamiNeural`）へ安全にフォールバック設定し、未選択ブランクを 100% 防止。
  5. `tests/test_smoke.py`:
     - `test_azure_active_default_voice` ユニットテストを追加。
- **検証結果**:
  - `/api/voices` が `defaultVoice: "azure:ja-JP-NanamiNeural"`, `isAzureActive: true` を返却することを確認。
  - WebUI 上で Azure 話者が確実にデフォルト選択され、全12件のユニットテストがパスすることを確認。

## 2026-10-20 01:25 - Pure Python Zeroconf による Google Cast 探索統合と、公開・開発両立型 Docker Compose 構成への刷新
- **背景と課題**:
  1. 従来はコンテナからホストの `/run/dbus/system_bus_socket` および `/var/run/avahi-daemon/socket` をバインドマウントし、`avahi-browse` コマンド（`subprocess`）を実行して Google Cast を探索していた。
  2. これにより、Synology NAS、QNAP、WSL2、Alpine Linux、最小構成サーバーなど、ホスト側に Avahi デーモンが存在しない環境では Docker が空ディレクトリを作成してしまいエラーになる問題や、コンテナ内での外部プロセス呼び出しオーバーヘッドがあった。
  3. また、自動ビルドした Docker Hub イメージを一般ユーザーが手軽に使う際、リポジトリを `git clone` していない環境で `build: .` や `./app:/app/app` のマウントがあると起動失敗（空ディレクトリ作成）するため、一般ユーザー向けと開発者向けの構成を両立する必要があった。
- **修正内容**:
  1. `app/services/devices_service.py`:
     - 外部コマンド `avahi-browse` および `subprocess` を完全撤廃。
     - Pure Python の `zeroconf`（`ServiceBrowser` / `ServiceListener`）によるバックグラウンド常駐 mDNS 探索へ移行。
     - `_googlecast._tcp.local.` サービスを全インターフェース（`InterfaceChoice.All`）でリッスンし、IPv4 アドレス、ポート、モデル名、スピーカーグループ（ポート32094等）をメモリ上でリアルタイム自動更新。
     - `decode_avahi_string` 等のレガシーエスケープ処理を撤廃。
  2. `app/main.py`:
     - FastAPI の lifespan シャットダウン処理に `device_manager.close()` を追加し、Zeroconf のソケット・スレッドリソースを安全解放。
  3. `docker-compose.yml`（一般ユーザー・公開用）:
     - `image: maximilian2022/smarthomespeaker-voicehub:latest` を指定。
     - ソースコードバインドマウント（`./entrypoint.sh`, `./app`, `./public`）およびホストの Avahi/D-Bus ソケットマウントを完全撤廃。
     - 一般ユーザーは `docker-compose.yml` 1枚だけで、Raspberry Pi でも NAS でも即座に `docker compose up -d` 可能に。
  4. `docker-compose.override.yml`（リポジトリ内・開発者用）:
     - リポジトリ内に配置し、開発者が `docker compose up` を実行した際に自動でマージされるホットリロードマウント（`build: .`、`./app:/app/app`、`./public:/app/public`、`./tests:/app/tests`）を定義。
  5. `Dockerfile`:
     - Zeroconf 化に伴い、不要となった `avahi-utils` システムパッケージを apt-get から削除し、イメージサイズを削減。
  6. `README.md` & `CONTRIBUTING.md`:
     - 一般ユーザー向けのかんたん起動手順（`docker-compose.yml` 1枚での起動）と、開発者向けのローカル開発手順を更新。
  7. `tests/test_smoke.py`:
     - Zeroconf によるデバイス・グループ登録および `find_device` 照合のスモークテストを追加。
- **検証結果**:
  - 実機環境（15台の Google Cast デバイスおよびグループ）が Avahi ソケットなしで瞬時に検出されることを確認。
  - `docker exec SmartSpeaker-VoiceHub python3 -m unittest` で全11件のテストが合格することを確認。
  - `/api/status`, `/api/devices` の正常稼働（67台認識）を確認。

## 2026-10-20 00:35 - GitHub Actions ワークフローの各種 Action 最新化（Node.js 24 ランナー移行対応）
- **背景と課題**:
  1. GitHub Actions のランナー実行ログにおいて、「Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, docker/build-push-action@v6, docker/setup-buildx-action@v3」という非推奨警告（Annotation）が発生していた。
  2. GitHub は 2025年秋〜2026年にかけてランナー環境を Node 20 から Node 24 へ移行しており、古いバージョンの Action を使い続けると強制フォールバックや将来的な実行失敗の原因となるため、公式推奨の最新メジャーバージョンへ更新する。
  3. 併せてアナウンスされていた `ubuntu-latest` の Ubuntu 26 への移行アナウンスについては、本リポジトリのテスト・ビルドが Docker コンテナ内で完全に自己完結（抽象化）されているため、`ubuntu-latest` を固定せずそのまま追従・許容する方針とした。
- **修正内容**:
  1. `.github/workflows/docker-publish.yml`:
     - `actions/checkout@v4` → `@v7` (Node 24 完全対応版)
     - `docker/setup-buildx-action@v3` → `@v4`
     - `docker/build-push-action@v6` → `@v7`
     - `docker/setup-qemu-action@v3` → `@v4`
     - `docker/login-action@v3` → `@v4`
     - `docker/metadata-action@v5` → `@v6`
- **検証結果**:
  - GitHub 公式 API（`gh api`）により各 Action のリリース最新タグ（checkout v7.0.1, buildx v4.4.1, build-push v7.4.0, qemu v4.4.0, login v4.6.0, metadata v6.2.0）を確認し、メジャーバージョン指定が整合していることを確認。

## 2026-10-20 00:20 - ONVIF 認証の Profile T 規格準拠 HTTP DigestAuth 化による SHA-1 脆弱性アラート完全解消
- **背景と課題**:
  1. 本システムはカメラからの音声出力（Audio Backchannel）を前提としており、Profile S（音声受信のみ対応）ではなく Profile T（双方向音声・スピーカー出力対応）対応カメラが必須要件である。
  2. Profile T では従来の SOAP ヘッダー内 WS-UsernameToken（PasswordDigest = SHA-1）が非推奨となり、HTTP Digest 認証（RFC 7616 / RFC 2617、SHA-256 対応）が必須要件（Mandatory）と規定されている。
  3. 自前で計算していた `hashlib.sha1` によるパスワードダイジェストを撤廃し、Profile T 正式仕様に移行することで、CodeQL の脆弱性アラート（#12）を構造的に解消する。
- **修正内容**:
  1. `app/services/onvif_service.py`:
     - 自前の `_build_ws_security_header` 関数、および `import hashlib`, `import base64` を完全に撤廃。
     - `send_soap` メソッドにおいて、Profile T 規格準拠の `httpx.DigestAuth(username, password)` を用いた HTTP Digest 認証へ移行。
- **検証結果**:
  - 実機カメラ（Reolink E1 Pro / E1 Outdoor: `192.168.11.202`, `192.168.11.203`, `192.168.11.208`）すべてにおいて、`HTTP 200 OK` で正常に認証・応答できることを実機検証。
  - `docker compose run --rm voice-hub python3 -m unittest` で全テストが合格することを確認。

## 2026-10-20 00:09 - CodeQL 公式推奨パターンによる /voice/{filename} の Path Injection 完全解消
- **背景と課題**:
  1. `app/main.py` の `/voice/{filename}` において、`pathlib.Path.is_relative_to` による検証を行っていたが、CodeQL のクエリパーサーがこれをサニタイザとして完全認識せず `py/path-injection` アラート（#16, #17）が残存していた。
- **修正内容**:
  1. `app/main.py`:
     - CodeQL 公式推奨の `os.path.realpath`, `os.path.normpath`, `startswith` パターンに厳格準拠。
     - `clean_name = os.path.basename(filename)` と `fullpath = os.path.normpath(os.path.join(base_path, clean_name))` を用い、`fullpath.startswith(base_path)` による検証へ刷新。
- **検証結果**:
  - `docker compose run --rm voice-hub python3 -m unittest` で全テストが合格することを確認。

## 2026-10-20 00:02 - CodeQL 残余アラートの構造的排除（定数ホワイトリスト化・正規表現バリデーション・URL完全再構築）
- **背景と課題**:
  1. 初回修正により元々の 14 件中 11 件が `fixed`（解消）となったが、行番号変更に伴い CodeQL が `app/services/tts_service.py`、`app/main.py`、`app/services/dlna_service.py` を再検知し新規番号（#15〜#19）を付与していた。
  2. 動的文字列操作やパス解決演算が残っていたため、CodeQL のデータフロー解析（Taint Analysis）を完全に切断する構造的サニタイズが必要だった。
- **修正内容**:
  1. `app/services/tts_service.py`:
     - チャイム指定を動的パス生成から静的定数辞書（`ALLOWED_CHIMES = {"alert": ..., "announce": ..., ...}`）のキー照合方式に刷新。ユーザー入力からのパス演算を完全排除。
  2. `app/main.py`:
     - `/voice/{filename}` の冒頭に正規表現チェック `re.match(r"^[a-zA-Z0-9_\-]+\.mp3$", filename)` を追加し、英数字以外の文字を即座に 400 Bad Request で拒絶。
  3. `app/services/dlna_service.py`:
     - `_fetch_device_info` において、`localhost`, `127.0.0.1`, `0.0.0.0`, `::1`, `169.254.169.254`（メタデータ）を明示的にブロック。
     - 検証済みコンポーネントから `clean_url = f"{scheme}://{hostname}:{port}{path}{query}"` を完全再構築してリクエスト。
- **検証結果**:
  - `docker compose run --rm voice-hub python3 -m unittest` で全テストが合格することを確認。

## 2026-10-19 23:55 - GitHub Code Scanning (CodeQL) アラートの一括是正（SSRF・Path Injection・情報露出の解消）
- **背景と課題**:
  1. GitHub Code scanning (CodeQL) により、合計 14 件のアラートが検出されていた。
  2. SSRF（Critical 3件: Azure TTS リージョン指定、DLNA探索先URL）、Path Injection（High 4件: 音声キャッシュ配信、効果音チャイムパス）、Stack Trace Exposure（Medium 4件: 500エラーハンドラ、TTSテスト例外、Alexaプロキシ例外）、規格準拠によるSHA1検知（High 1件: ONVIF WS-Security）、Actions権限（Medium 2件）の対処が必要だった。
- **修正内容**:
  1. SSRF 対策 (`app/services/tts/azure_provider.py`, `app/services/dlna_service.py`):
     - Azure TTS: リージョン指定を `^[a-z0-9\-]+$`（英数字・ハイフンのみ）に厳格バリデーションし、URL 組み立て時の不正ホスト注入を完全に防御。
     - DLNA: `_fetch_device_info` 実行前に `urlparse` を行い、スキームが `http`/`https` かつホストが存在することを検証。
  2. Path Injection 対策 (`app/main.py`, `app/services/tts_service.py`):
     - `/voice/{filename}`: `Path(filename).name` に加え、`resolve().is_relative_to(VOICE_DIR.resolve())` でディレクトリ外参照を完全に遮断。
     - チャイム結合: `chime` 名から記号を除去し、`self.sound_dir` 配下に実在するファイルであることを検証。
  3. Stack Trace Exposure 対策 (`app/main.py`, `app/routers/speech.py`, `app/services/alexa_proxy_service.py`):
     - グローバル 500 ハンドラ、TTS テスト、Alexa プロキシにおいて、サーバーログには例外詳細を記録しつつ、クライアントへのレスポンスは安全なメッセージにサニタイズ。
  4. ONVIF WS-Security の SHA-1 規格注記 (`app/services/onvif_service.py`):
     - OASIS WS-Security UsernameToken Profile 1.0 国際規格仕様に準拠した認証ダイジェストであることを明記し、`usedforsecurity=False` を付与。
- **検証結果**:
  - `docker compose run --rm voice-hub python3 -m unittest discover -s tests -p "test_*.py"` およびホスト上でのテストが全件合格することを確認。

## 2026-10-19 23:40 - ARM64 マルチアーキテクチャビルド用 C/C++ コンパイラ追加および GHA permissions 明示
- **背景と課題**:
  1. GitHub Actions の Docker Hub マルチアーキテクチャ（amd64 / arm64）ビルドにおいて、arm64 環境で `miniaudio` の wheel ビルド時に C++ コンパイラ（`c++`）が存在せずビルドが失敗した。
  2. GitHub Actions ワークフローにおいて明示的な permissions 設定がなく、CodeQL のセキュリティスキャンでアラート（`actions/missing-workflow-permissions`）として検出されていた。
- **修正内容**:
  1. `Dockerfile`: `apt-get` のインストール対象に `gcc` と `g++` を追加し、ARM64 向け Python C++ 拡張モジュールのビルドに対応。
  2. `.github/workflows/docker-publish.yml`: トップレベルに `permissions: contents: read` を明示し、セキュリティ権限を最小化。
- **検証結果**:
  - `Dockerfile` の構文およびローカル Docker テストが問題なく動作することを確認。

## 2026-10-19 23:31 - クリーン環境における StaticFiles マウント用 sound ディレクトリ自動作成および Git 追跡対応
- **背景と課題**:
  1. GitHub Actions の Docker コンテナ内テスト実行において、新規クローンされた環境では `public/sound/` ディレクトリが存在せず、`app.main` の StaticFiles マウント時に `RuntimeError: Directory '/app/public/sound' does not exist` でテストが失敗していた。
  2. `.gitignore` で `*.mp3` が除外されていたため同梱の効果音 MP3 およびディレクトリ自体が Git から漏れており、かつ `app/config.py` でも `SOUND_DIR` の `mkdir` 漏れがあった。
- **修正内容**:
  1. `app/config.py`: `SOUND_DIR.mkdir(parents=True, exist_ok=True)` を追加し、起動時・インポート時にディレクトリが存在しない場合でも自動作成されるよう堅牢化。
  2. `Dockerfile`: `mkdir -p public/voice public/sound data` に更新。
  3. `.gitignore`: `!public/sound/*.mp3` および `!public/sound/.gitkeep` を追加して同梱の効果音ファイルを保護。
  4. `public/sound/.gitkeep` を配置し、ディレクトリが Git に確実に保持されるように対応。
- **検証結果**:
  - ホストおよび一時 Docker コンテナ（`docker compose run --rm`）の両方で `python3 -m unittest` を実行し、全件合格（OK）を確認。

## 2026-10-19 23:18 - Docker 完結型テスト・CI/CD への刷新および entrypoint.sh の任意コマンド実行対応
- **背景と課題**:
  1. ホスト環境に依存せず、Docker コンテナ内でテストやコマンド実行を完結（代替）させたいという方針への転換。
  2. 既存の `entrypoint.sh` は渡されたコマンド引数を無視して常に uvicorn を起動していたため、`docker compose run --rm voice-hub <cmd>` 実行時にポート競合エラーが発生して一時コンテナでのテスト実行ができなかった。
  3. GitHub Actions のテストジョブもホスト側 Python（setup-python）を使用していたため、コンテナ環境と乖離していた。
- **修正内容**:
  1. `entrypoint.sh`:
     - 引数が指定された場合（`"$#"` > 0）に `exec "$@"` で任意のコマンドを実行できるように改善。
     - 引数なしの通常起動時は従来通り go2rtc と uvicorn を起動。
  2. `.github/workflows/docker-publish.yml`:
     - `setup-python` によるホスト依存を撤廃。
     - Docker Buildx でローカルテスト用イメージをビルドし、`docker run --rm` によりコンテナ内で `unittest` を実行する Docker 完結型 CI に刷新。
  3. `CONTRIBUTING.md`:
     - テストの実行手順を Docker コンテナ内での実行（`docker compose run --rm` または `docker exec`）を第一推奨としてドキュメントを改訂。
- **検証結果**:
  - `docker compose run --rm voice-hub python3 -m unittest discover -s tests -p "test_*.py"` を実行し、全 9 テストが成功（OK）し一時コンテナが自動破棄されることを確認。
  - 稼働中コンテナ `SmartSpeaker-VoiceHub` 上での `docker exec` テスト実行も成功することを確認。

## 2026-10-19 23:15 - GitHub Actions による Docker Hub 自動ビルド・プッシュ構築およびホスト環境 Python 3.14 更新
- **背景と課題**:
  1. GitHub にコードを push / タグ付けした際に、自動でテストを実行し Docker Hub へマルチアーキテクチャ（amd64 / arm64）イメージをビルド＆プッシュする CI/CD パイプラインが未整備だった。
  2. ホスト OS（CentOS Stream 10）上の Python が 3.12 であり、プロジェクト標準（Dockerfile 等）の Python 3.14 と乖離していた。
- **修正内容**:
  1. `.github/workflows/docker-publish.yml`:
     - `main` への push、リリースタグ（`v*.*.*`）、PR、手動実行（`workflow_dispatch`）に対応した GitHub Actions ワークフローを新規作成。
     - 単体テストジョブ（Python 3.14 上での `unittest`）を先行させ、テスト通過時のみ Docker ビルドを実施する安全設計。
     - QEMU + Docker Buildx によるマルチプラットフォーム（`linux/amd64`, `linux/arm64`）対応。
     - Docker Hub アカウント名の大文字小文字差異によるビルドエラーを防止する自動小文字化（Normalize）ステップを導入。
     - PR 時は Docker Hub へのプッシュを抑止しビルド検証のみ実行。
  2. ホスト環境の Python 3.14 更新:
     - `dnf install python3.14 python3.14-pip python3.14-devel` を実行。
     - システム管理ツール `dnf` が Python 3.12（`/usr/bin/python3`）に直接依存しているためシステム Python を破壊せず、優先順位の高い `/usr/local/bin` 配下に `python`, `python3`, `pip`, `pip3` のシンボリックリンクを配置。
     - Python 3.14 環境に `requirements.txt` の全パッケージを導入。
- **検証結果**:
  - `python --version` / `python3 --version` が `Python 3.14.8`、`pip3 --version` が `pip 25.2 (python 3.14)` を指していることを確認。
  - `dnf --version` が正常に動作し、システム管理コマンドに一切影響がないことを確認。
  - ホスト Python 3.14 上で `python3 -m unittest discover -s tests -p "test_*.py"` を実行し、全 10 テストが成功（OK）することを確認。

## 2026-10-19 22:58 - セキュリティポリシー (SECURITY.md) およびコントリビューションガイド (CONTRIBUTING.md) の整備
- **背景と課題**:
  1. オープンソースコミュニティからの貢献や質問を受け付ける導線（CONTRIBUTING.md、Discussions）、および脆弱性の安全な非公開報告ポリシー（SECURITY.md）が未整備だった。
  2. 連絡窓口を GitHub Discussions に集約しつつ、セキュリティ上の機密情報は非公開で受け取れる体制が必要だった。
- **修正内容**:
  1. `SECURITY.md`:
     - サポート対象ブランチ（`main`）を定義。
     - 公開 Issue での脆弱性投稿を抑止し、GitHub の Private Vulnerability Reporting または GitHub Discussions での安全な連絡方法・報告テンプレート・対応フローを策定。
     - 非公式 API（Edge-TTS, Alexa スクリプト）やユーザー側環境設定等のスコープ外事項を明記。
  2. `CONTRIBUTING.md`:
     - GitHub Discussions での質問・アイデア交換を推奨。
     - 本プロジェクト固有の開発規約（Python ファースト、フロントエンド Vanilla JS/CSS、Homebridge プラグイン TypeScript、Conventional Commits）を明文化。
     - ローカル開発環境のセットアップ（Docker / venv）およびテスト実行コマンド（`tests/test_smoke.py`）を網羅。
     - PR 提出手順および MIT License への同意条項を整備。
  3. `README.md`:
     - 「🤝 コミュニティと開発への参加」セクションを新設し、`GitHub Discussions`, `CONTRIBUTING.md`, `SECURITY.md` へのリンクを配置。
- **検証結果**:
  - 各ドキュメント間の相対リンクおよび GitHub Discussions リンクの整合性を確認。

## 2026-10-19 22:52 - GitHub オープンソースライセンス (MIT License) およびサードパーティライセンス一覧の整備
- **背景と課題**:
  1. リポジトリ直下に `LICENSE` ファイルが存在せず、GitHub 上でライセンスが明示されていなかった。
  2. 依存している外部 OSS（特に LGPL-3.0 である `edge-tts` や `recurring-ical-events`、および同梱スクリプト `alexa_remote_control.sh` 等）とのライセンス互換性および著作権・クレジット表記の整理が必要だった。
- **修正内容**:
  1. `LICENSE`: MIT License（Copyright (c) 2026 Maximilian2022）をルート直下に新規作成。
  2. `THIRD_PARTY_LICENSES.md`:
     - 利用している Python ライブラリ（FastAPI, Uvicorn, Pydantic, edge-tts 等）のライセンス一覧を明記。
     - LGPL-3.0（`edge-tts`, `recurring-ical-events`）について、本プロジェクトが外部依存として動的利用している独立著作物であること、およびライブラリ差し替え可能性を満たしている旨の注記を明記。
     - 同梱の `bin/alexa_remote_control.sh` (Apache-2.0 / Alexander Noack, Thorsten Gehrig)、`go2rtc` (MIT / AlexxIT)、同梱プラグイン `plugins/homebridge-voicehub` (Apache-2.0 / Maximilian2022)、および着想元の `google-home-voicetext-docker` への謝辞を体系的に整理。
  3. `README.md`: 「ライセンスと謝辞」セクションに `[MIT License](LICENSE)` および `[サードパーティライセンス一覧 (THIRD_PARTY_LICENSES.md)](THIRD_PARTY_LICENSES.md)` へのリンクを反映。
- **検証結果**:
  - ファイル配置・マークダウンリンクの整合性を確認。

## 2026-10-19 19:55 - DND保留解除時の宛先別スピーカー再生＆同一宛先グルーピングAI要約、Gemini APIタイムアウト・複数フォールバック強化
- **背景と課題**:
  1. **DND保留解除時の一斉再生問題**: 保留（queue）モードで蓄積された通知をDND解除時に再生する際、AI要約（2件以上）が発動すると無条件に `targets="ALL"`（家中すべてのスピーカー）から流れてしまい、本来の宛先（リビングや寝室など）が無視されていた。
  2. **異なる宛先の混ざったAI要約**: 送信先が異なる複数メッセージ（例: リビング宛て通知と寝室宛て通知）が丸ごと1つにまとめられて家中へ放送されていた。
  3. **未指定宛先の全スピーカー強制化**: `app/main.py` で DND のエグゼキュータに `on_disaster_speech`（`targets or "ALL"`）が渡されており、宛先未指定（None）の通知もデフォルトスピーカーではなく全スピーカーへ化けていた。
  4. **Gemini API のタイムアウトおよびフォールバック不全**: ログで `httpcore.ReadTimeout`（15秒）が発生していた。メッセージ数が多い場合や外部LLMの高負荷時に15秒でタイムアウトし、例外発生時にフォールバックモデルが試行されずに単なるテキスト連結（「保留されていた通知が10件あります...」）へ落ちていた。
- **修正内容**:
  1. `app/services/dnd_service.py`:
     - ターゲット正規化ヘルパー `_normalize_target_key(targets)` を導入し、保留メッセージを宛先（`targets`）ごとに正規化してグルーピング。
     - 各宛先グループごとに、蓄積件数が閾値（`aiSummaryThreshold`、デフォルト2件）以上の場合は**同一宛先のメッセージ群のみをAI要約**し、**その本来の宛先スピーカー（`targets`）宛てに発話**。
     - 閾値未満（1件など）またはAI無効/失敗時は、本来の宛先スピーカーへ個別に順次発話。宛先未指定（None）は `targets=None` のまま渡し、システムのデフォルトスピーカーから再生。
     - 発話時に `source="dnd_queue"`, `source_label="DND保留再生"` を付与し履歴表示を整備。
  2. `app/main.py`:
     - `dnd_service.set_speaker_executor(speech_service.speak)` に変更し、防災速報用の `targets or "ALL"` 強制変換を排除。
  3. `app/routers/dnd.py`:
     - `POST /api/dnd/queue/release` で重複していた古い一斉再生ロジックを全廃し、`dnd_service.check_and_flush_queue()` を直接呼び出す形に一元化。
  4. `app/services/ai_service.py`:
     - Gemini API 呼び出しのタイムアウトを 15 秒から 25 秒に延長。
     - タイムアウト例外（`httpx.TimeoutException`）や HTTP エラー（503/404 等）発生時に、複数のフォールバックモデル（`gemini-3.5-flash`, `gemini-2.5-flash`, `gemini-flash-latest`）へ順次自動再試行する多重フォールバックを実装。
  5. `tests/test_smoke.py`:
     - `test_dnd_flush_grouped_by_target` を追加し、宛先正規化、同一宛先のみの要約、宛先別発話、未指定時のデフォルト宛先発話を自動検証。
- **検証結果**:
  - `docker exec SmartSpeaker-VoiceHub python3 -m unittest tests/test_smoke.py`: 全 9 テストが 0.372 秒で全件合格。
  - 実機 API (`POST /api/ai/summarize-test`, `POST /api/dnd/queue/release`) の正常疎通および要約生成（所要時間4〜6秒）を確認。
  - コンテナ `SmartSpeaker-VoiceHub` は正常稼働中（healthy）。

## 2026-10-19 11:20 - 第3回調査レポート (report3.md) に基づく不整合解消・UI改善・Homebridge 1.0.2 公開準備の完了
- **背景と課題**:
  1. **AI 要約テストのスタブ残存**: `POST /api/ai/calendar-test` が `ai_service` を呼ばず固定文字列を即返却していたため、APIキーやカスタムプロンプトの動作確認ができなかった。
  2. **履歴フィルターの機能不全**: `scheduler_service.py` で `source="scheduler"` が使われていたため、WebUI（`data-filter="schedule"`）の「スケジュール」履歴フィルターで 1 件もヒットせず空になっていた。
  3. **Homebridge プラグインの未ビルド**: `plugins/homebridge-voicehub/` の TypeScript 修正（全室指定バグ解消、音量連携）が `dist/` にコンパイルされておらず古い JS のままだった。
  4. **ONVIF カメラパスワードの上書き消去**: 設定編集時にパスワード欄が空だと保存済みパスワードが空文字で上書きされ RTSP 認証エラーになる問題、および WebUI 一覧での平文パスワード表示。
  5. **Alexa 手動トークン登録の即時スキャン漏れ**: `POST /api/alexa/token` 後にデバイススキャンが走らず、再起動まで Echo 一覧が反映されなかった。
  6. **ログエンドポイントのメモリ負荷**: `ACTIVE_LOG_FILE` 読み込みで `f.readlines()` による全行メモリ展開が行われていた。
- **修正内容**:
  1. `app/routers/ai.py`: `test_calendar` を修正し、固定サンプル予定 3 件と `promptHint` を `ai_service.summarize_calendar_events()` に渡して実際に AI 疎通・プロンプト確認を行うよう改修。
  2. `app/services/scheduler_service.py` & `public/app.js`: `scheduler_service.py` の発声時 `source="schedule"` に統一。`public/app.js` の履歴フィルターで `schedule`/`scheduler`/`scheduled_speech` および `api`/`tunnel_webhook`/`webhook` の揺れを網羅的に吸収。
  3. `plugins/homebridge-voicehub/`: バージョンを `1.0.2` にバンプし `CHANGELOG.md` を更新。`npm run build` を実行して `dist/` のコンパイル成果物を最新化。
  4. `app/routers/onvif_dlna.py` & `public/app.js`: カメラ更新時にパスワードやユーザー名が未指定・空文字の場合、既存の設定値を維持するフォールバックを追加。WebUI の接続 URL 表示でパスワードを `rtsp://admin:****@...` にマスク表示。
  5. `app/routers/homepod_alexa.py`: `set_alexa_token` 完了直後に `await alexa_service.scan_devices(force_login=True)` を実行し、即時に Echo デバイスを検出・反映。
  6. `app/routers/logs.py`: `ACTIVE_LOG_FILE` の読み込みを `f.readlines()` から `read_tail_lines()` に統一し、大容量時のメモリ負荷を削減。
- **検証結果**:
  - `python3 -m unittest tests/test_smoke.py`: 全 9 テストが 0.277 秒で全件合格。
  - 実機 API (`GET /api/logs`, `POST /api/ai/calendar-test`) の正常疎通およびエラーハンドリングの動作を確認。
  - コンテナ `SmartSpeaker-VoiceHub` は正常に再起動し `healthy` を維持。

## 2026-10-19 10:45 - 第2回再監査レポート (report2.md) に基づくリグレッション解消・セキュリティ実効化・OSS不整合解消・OSS公開クリーンアップの完遂
- **背景と課題**:
  1. **新規リグレッション (致命的クラッシュ & 一斉放送不全)**:
     - `app/services/speech_service.py`: Alexa 単独発声時の TTS スキップ最適化の余波で `opt_voice`, `opt_rate`, `opt_pitch` が `else:` 内でのみ定義されるようになり、発声直後の履歴記録処理で 100% `UnboundLocalError` が発生してクラッシュしていた。
     - `app/services/devices_service.py` & `app/services/onvif_service.py`: パスワード平文漏洩対策の余波で、`ALL` / `CAM:ALL` 一斉放送時に `device_manager.get_devices()` が渡されたカメラの個別パスワードが空になり、RTSP 401 認証エラーで鳴動しなくなっていた。
  2. **実稼働コンテナでのセキュリティ設定未反映**:
     - `docker-compose.yml` で Named Volume (`smart_speaker_data`) をマウントしているため、`entrypoint.sh` の `if [ ! -f ... ]` がスキップされ、稼働中の `go2rtc` が依然として `*:8554` / `*:8555` で全インターフェースに露出していた。
  3. **コンテナ内 OSS (`bin/alexa_remote_control.sh`) との不整合・デッドロックリスク**:
     - `alexa_service.py`: `Semaphore(2)` 内での再帰呼び出しによる永久デッドロックリスク、および単一ファイル `/tmp/.alexa.cmd` のファイル競合。
     - スクリプト内部の `$TMP`、`$TTS_LOCALE`（デフォルトドイツ語 `de-DE`）との不整合、および標準音量制御変数 `$SPEAKVOL`（一時変更・自動復元）の未活用。
     - Alexa 認証プロキシ (`:8081`) の 10 分自動停止タイマー未実装。
  4. **周辺機能・代替措置・ドキュメントの乖離**:
     - `settings.json` の `syncOffsets`（静的ディレイ）が `speech_service.py` で未参照、および `Manual.md` の EMA / WAL 残存。
     - `pychromecast` 再接続時の古い `SocketClient` ワーカースレッドリーク。
     - `uvicorn.access` による 30 秒ごとのヘルスチェックログ肥大化および `token=` 生トークン平文記録。
     - ローカル音声エンジン（VOICEVOX / COEIROINK 等）オフライン時の 66 秒に及ぶ直列タイムアウトブロック。
     - OpenAI `o1`/`o3-mini` 指定時の `max_tokens` HTTP 400 エラー、および存在しない `gemini-3.5-flash` 定義。
     - Homebridge プラグイン音量連携の通信未接続、HomePod 音量制御 (`pyatv.audio.set_volume`) の未実装。
     - テストスイートにおける動的 import 検査および AST 未束縛変数自動検知の欠落。
  5. **OSS 公開（GitHub）における環境依存データの露出**:
     - 開発環境の特定 IP アドレス (`192.168.11.x`) のハードコード補正ロジックおよびプレースホルダーの残存。
- **修正内容**:
  1. **フェーズ 1 (致命的バグ・デッドロック・実環境セキュリティの修正)**:
     - `app/services/speech_service.py`: `opt_voice`, `opt_rate`, `opt_pitch`, `opt_chime` を `if only_alexa:` の前に移動し `UnboundLocalError` を完全解消。`audioUrl` を空文字 `""` に適正化。
     - `app/services/onvif_service.py`: `play_audio()` 内で `camera.get("password")` が無い場合、`registeredDevices` から `raw_ip` に一致する個別パスワードを自動補完するよう改修。
     - `entrypoint.sh`: Named Volume 内の既存 `go2rtc.yaml` に対しても `sed` 置換を強制実行し、`127.0.0.1:8554` / `127.0.0.1:8555` / `127.0.0.1:1984` に確実にバインド（ホスト `ss -tulpn` で確認完了）。
     - `app/services/alexa_service.py`: `Semaphore(1)` 完全直列化、再帰呼び出しをループ `for attempt in range(2):` に変更してデッドロックと競合を排除。`env["TMP"] = str(DATA_DIR)`、`env["TTS_LOCALE"] = "ja-JP"` を設定。`speak()` で `SPEAKVOL` を渡し、Alexa でも自動音量・ささやき音量を実現。10分自動停止タイマーを追加。
  2. **フェーズ 2 (代替措置の完遂・パフォーマンス改善・ログ適正化)**:
     - `app/services/speech_service.py`: `syncOffsets` (`googleDelayMs`, `homepodDelayMs`, `alexaDelayMs`) を読み取り、各プラットフォームへの発声タスク前に `asyncio.sleep` を挟む静的オフセット制御を実装。
     - `app/services/cast_service.py`: 再接続時に切断状態の古いインスタンスの `c.disconnect(timeout=1.0)` を呼び出し、ワーカースレッドのリークを防止。
     - `app/core/logger.py`: `UvicornAccessFilter` を新設し、`/api/status`, `/api/dnd/status`, `/api/logs` のアクセスログ除外と `?token=...` のマスク処理を実装。
     - `app/services/tts_service.py`: `warmup_enabled_speakers()` を `asyncio.gather()` で並列化しタイムアウトを 3 秒に短縮（起動時待機時間を 66 秒から 4 秒に短縮）。`get_cache_stats()` に 60 秒インメモリキャッシュを導入しヘルスチェック時の過剰ディスク I/O を排除。キャッシュクリーンアップ時の `_duration_cache` 解放を追加。
     - `app/routers/ai.py` & `app/services/ai_service.py`: 非実在モデル (`gemini-3.5-flash`, `3.8-flash`) を削除。OpenAI `o1`/`o3` 指定時に `max_completion_tokens` を使用するよう分岐を追加。
  3. **フェーズ 3 (周辺機能・Homebridge連携・仕様書整合・OSS公開クリーンアップ)**:
     - `plugins/homebridge-voicehub/`: `voicehub-client.ts` の `target !== 'ALL'` 条件バグを解消、`setDeviceVolume` メソッドを新設。`speaker.ts` で HomeKit 音量スライダー操作時にバックエンド API を叩くよう接続。
     - `app/services/homepod_service.py` & `app/routers/devices.py`: `pyatv.audio.set_volume` を用いた HomePod 音量変更処理を実装。
     - `app/services/calendar_service.py` & `dnd_service.py`: 同時刻の全予定タイトルを検査し `calendarIncludeAllDay` 設定を反映。デイリーサマリーに `dailyCalendarPrompt` を引き渡し。発声呼び出し時に `source="calendar"` を明示。
     - `app/services/disaster_service.py` & `scheduler_service.py`: 発声呼び出し時に `source="disaster"`, `source="scheduler"` を明示。
     - `app/services/mqtt_service.py`: `base_topic/say` と `base_topic/say/#` の重複購読を排除（重複発声防止）。
     - `app/core/log_rotator.py`: gzip フォールバック時に拡張子を `.gz` として正しく保存するよう修正。
     - **OSS 公開クリーンアップ**: `settings_service.py`, `public/app.js`, `Manual.md`, `devices_service.py` から環境依存の IP アドレス（`192.168.11.x`）のハードコード補正・プレースホルダーを一掃し、一般的な例示 (`192.168.1.x`, `127.0.0.1`, `localhost`) に標準化。
     - `Manual.md`: 第3章、第4章、第14章、第15章に残存していた EMA / WAL / queue_manager 記述を実態（インメモリキュー・静的ディレイ）に完全一致。
  4. **フェーズ 4 (テスト強化・自己チェック・実機検証)**:
     - `tests/test_smoke.py`: `app/` 配下の全モジュール動的 import 検査、AST 構文解析、Alexa 単独発声回帰テスト、ONVIF パスワード補完テストを追加（全 9 テストが 0.29 秒で全件パス）。
     - 実機 API 検証: Alexa 単独発声 (`curl /api/say`) にて `UnboundLocalError` が解消され、HTTP 200 で発声・履歴保存されることを実証。
     - コンテナ再ビルド・再起動完了 (`SmartSpeaker-VoiceHub`, `cloudflared-SmartSpeaker-VoiceHub` ともに `healthy`)。

---

## 2026-10-19 10:00 - プロジェクト総合監査 (Report.md) に基づく全フェーズ改修・最適化の完遂
- **背景と課題**:
  1. **致命的クラッシュ & 外部侵入・認証バイパス**:
     - `tts_service.py` における `import time` 欠落により、キャッシュMISS時の新規音声合成が `NameError` で例外終了していた。
     - Docker `network_mode: "host"` 環境下で Cloudflare Tunnel (`cloudflared`) からのリクエスト元IPが `127.0.0.1` になるため、「宅内プライベートIPならWebUIトークン免除」という判定が外部トンネル経由のリクエストにも誤適用され、外部から無認証で音声発声や MCP ツール実行が可能となっていた重大なセキュリティ脆弱性。
     - FastAPI の `BaseHTTPMiddleware` 内で `raise HTTPException` すると例外ハンドラが捕捉できずに HTTP 500 (Internal Server Error) に化けていた問題。
  2. **高優先機能不具合 & 情報漏洩対策**:
     - `settings_service.py` の辞書マージ `{**old, **new}` により、WebUIからデバイスグループやIPエイリアスを削除しても古いキーが残り続け、削除が反映されなかった。
     - DND（おやすみモード）で時間省略時に `manualUntil` が即時期限切れ（1秒後）となり機能しなかった問題、および `speech_service.py` での発声抑制時に `dnd_service.record_history()` が呼ばれていなかった問題。
     - Alexa デバイス名の二重ラップ (`Alexa (Alexa (...))`)、カスタムグループ内の Echo 端末検索不全、`/api/devices` レスポンスでの ONVIF カメラパスワード平文露出。
     - 防災速報において地震情報の地域フィルタ (`local`) が未適用で全国の地震で鳴動していた問題、コンテナ起動時に既存警報をすべて新規発表と誤認して誤発報していた問題、WebUI の P2P 地震速報バッジが常に「再接続待機中」と表示されていたプロパティ不一致。
     - 外部トンネル経由で `/api/status` を叩いた際の生トークン露出、CORS のワイルドカードと認証情報併用による仕様違反、`.dockerignore` への `data/`, `logs/` 欠落。
     - `go2rtc` の RTSP ポート (`:8554`) が全インターフェースに無認証バインドされ、再生完了後にストリーム定義が残存してカメラ映像・音声が同一LANから盗聴可能だった問題。
  3. **パフォーマンス最適化 & リソース負荷削減**:
     - Alexa デバイス一覧取得時の毎回 bash サブプロセス (`alexa_remote_control.sh -a`) 起動による Amazon API レートリミット懸念と発声遅延。
     - Alexa 単独発声時にも MP3 合成・ffmpeg チャイム結合がフル実行され破棄されていた無駄な CPU/API 負荷。
     - 話者一覧取得 (`get_voices`) ごとの不要な `sync_settings()`、音声再生時間 (`ffprobe`) の毎回実行、キャッシュHIT時の LRU タイムスタンプ更新漏れ。
     - WebUI 初回ロード時における `/api/settings` の複数同時重複 fetch。
  4. **品質・保守性向上**:
     - 音量空文字指定時の `float("")` による `ValueError` クラッシュ。
     - カレンダー終日予定・複数日予定が当日の予定サマリーから漏れる判定バグ。
     - Homebridge / Home Assistant 個別スピーカー音量連携 API の欠落、MQTT 分数指定タイマーミュート未対応。
     - 自動テストスイートの不在、Docker `HEALTHCHECK` および `go2rtc` プロセス死活監視の欠落、デッドコードの残存、`Manual.md` の実態乖離。
- **修正内容**:
  1. **フェーズ 1 (最優先バグ & 認証バイパス遮断)**:
     - `app/services/tts_service.py`: 先頭に `import time` を追加し、音声合成時の `NameError` を解消。
     - `app/main.py` & `app/services/tts/azure_provider.py` & `gcp_provider.py`: 未インポート・未定義変数 (`HTTPException`, `logger` -> `log`) を修正。
     - `app/core/security.py`: `validate_webhook_token` において `is_tunnel_request(request)` 時のトークン検証免除を絶対禁止に改修。
     - `app/routers/mcp.py` & `app/services/mcp_service.py`: 外部トンネル経由時のトークン認証強制、`GET /mcp`, `DELETE /mcp` に認証適用。
     - `app/main.py`: ミドルウェア内で `HTTPException` を捕捉し、適切な 401/403 `JSONResponse` を直接返却して 500 化を防止。
  2. **フェーズ 2 (機能不具合 & 情報漏洩対策)**:
     - `app/services/settings_service.py`: `OVERWRITE_COLLECTIONS = {"deviceGroups", "ipAliases"}` を定義し、設定更新時に上書き置換してWebUIからの削除機能を完全復旧。
     - `app/routers/dnd.py` & `app/services/mcp_service.py`: 時間未指定時の `manualUntil` を実質無期限（365日後）に修正。`app/services/speech_service.py` から DND抑制時に `dnd_service.record_history()` を呼び出すよう修正。
     - `app/services/devices_service.py`: 正規表現 `re.sub(r"^Alexa \((.+)\)$", r"\1", ...)` による二重ラップ防止、カスタムグループ内の Echo 端末検索対応、`isDefault` 付与、`/api/devices` レスポンスから ONVIF カメラパスワード（平文）を完全除外。
     - `app/services/disaster_service.py`: `_handle_quake_report` に地域フィルタ (`targetScope == 'local'`) を実装し設定地域外の揺れをスキップ。初回起動時の `_is_first_warning_check` ベースライン記録による誤発報防止、ポーリング間隔の動的適用、`includeAdvice` 設定連動。
     - `app/routers/disaster.py` & `public/app.js`: ステータスレスポンスに `wsConnected` を追加し、フロントエンドの接続判定を `isWsConnected ?? connected ?? wsConnected` に修正。
     - `app/routers/status.py`: トンネル経由アクセス時に `webhookToken` を非公開（`None`）に制限。
     - `app/main.py`: CORS を RFC 1918 プライベートIP・localhost・トンネルドメインに限定する正規表現 (`allow_origin_regex`) に更新。
     - `.dockerignore`: `data/`, `logs/` を追記しイメージビルド時の秘密情報混入を防止。
     - `data/go2rtc.yaml` & `entrypoint.sh`: RTSP/WebRTC を `127.0.0.1` にバインド制限。`app/services/onvif_service.py` のセッション終了時に `DELETE /api/streams?src={stream_name}` を発行してストリーム定義自体を削除。
  3. **フェーズ 3 (パフォーマンス・リソース最適化)**:
     - `app/services/alexa_service.py`: `list_devices()` に TTL（300秒）インメモリキャッシュを導入し、発声ごとの無駄な bash サブプロセス起動を排除。
     - `app/services/speech_service.py`: 宛先がすべて Alexa の場合、MP3 音声は一切不要なため TTS 合成処理・ffmpeg チャイム結合をスキップして即時ディスパッチ。
     - `app/services/tts_service.py`: `get_voices()` に TTL（60秒）キャッシュを導入し、重複 `sync_settings()` を排除。
     - `app/services/tts_service.py`: `get_audio_duration()` にインメモリキャッシュを導入して `ffprobe` 起動を最小化。音声キャッシュHIT時に `os.utime()` でタイムスタンプを更新し LRU 削除から保護。
     - `public/app.js`: シングルトン Promise ヘルパー `fetchSettings()` を導入し、初期画面ロード時の複数コンポーネントからの `/api/settings` 重複 fetch を 1 回に統合。
  4. **フェーズ 4 (品質向上・保守性・スモークテスト)**:
     - `scheduled_speech_service.py`, `scheduler_service.py`, `cast_service.py`: 音量パラメータの空文字 `""` 時に `ValueError` でクラッシュしないよう安全なパース処理を適用。
     - `calendar_service.py`: `get_today_events()` で終日予定（`start <= today < end`）および複数日にまたがる時間指定予定（`start <= today <= end`）を正確に抽出するよう修正。
     - `mqtt_service.py`: `voicehub/dnd/set` への数値送信（例: `30`, `60`）によるタイマー付きDNDミュートに対応。
     - `app/routers/devices.py`: 個別スピーカー音量制御エンドポイント (`POST /api/devices/{id}/volume`) を新設し、Google Cast / Alexa / WebUI / Homebridge からの個別音量変更と永続化に対応。
     - `tests/test_smoke.py`: トンネル境界認証、トークン強制、TTS キャッシュキー、カレンダー複数日予定、DND 緊急バイパスを網羅する高速スモークテストスイート（5 件全パス、0.005 秒）を新設。
     - `Dockerfile` & `docker-compose.yml`: `voice-hub` コンテナに `HEALTHCHECK`（`/api/status` 監視）を追加。さらに `cloudflared` サービスにも `--metrics 127.0.0.1:20245` を指定した `cloudflared tunnel ready` による公式準拠の `healthcheck` を追加。
     - `entrypoint.sh`: `go2rtc` プロセスの常時監視・自動再起動ループを実装。
     - `bin/`: 不要な旧スクリプト残骸（`homepod_scan.py`, `homepod_stream.py`）を削除。
     - `Manual.md`: 存在しない動的 EMA 補正や WAL ファイルの記述を実態に合わせて適正化。
- **検証結果**:
  - スモークテスト (`tests/test_smoke.py`): 5 テスト全件成功 (OK, 0.005s)。
  - 構文検証: 全 Python ファイル（`app/`, `tests/`）の `py_compile` エラーゼロ。
  - セキュリティ検証: 外部トンネル経由（`CF-Connecting-IP` 模倣）での `/api/status` は 403 Forbidden、未認証 `/api/say` は 401 Unauthorized で完全に遮断。
  - 実機稼働検証: コンテナ再起動後、`SmartSpeaker-VoiceHub` および `cloudflared-SmartSpeaker-VoiceHub` の双方が `(healthy)` ステータスで安定稼働中。P2P地震速報 WebSocket、MQTT ブローカー（Home Assistant / Node-RED）、Google カレンダー、MCP SSE すべて正常稼働。

## 2026-10-19 08:50 - プロジェクト全体監査に伴う品質・セキュリティ・API互換性・コア不具合の包括的改善
- **背景と課題**:
  1. **セキュリティリスク**:
     - `go2rtc` API がホストネットワークモードにより全LAN（`0.0.0.0:1984`）へ無認証露出しており、同一LAN内の他機器から登録防犯カメラの平文RTSPパスワードが漏洩する危険があった。
     - 管理画面セッショントークン生成が固定ソルト＋パスワードハッシュであり、同一パスワードで常に同一トークンが生成され予測可能だった。
  2. **コア不具合の解消**:
     - `calendar_service.py` から毎朝呼び出される `ai_service.is_available()` および `ai_service.summarize_calendar_events()` が存在せず、`AttributeError` が発生して毎朝のデイリーサマリーが失敗していた。
     - `disaster_service.py` の気象警報ポーリングにおいて、気象庁APIが `name` を含まず `code` のみを返却する仕様のため、警報名が空文字（`""`）となり「○○市にが発表されました」という破綻発話が発生し、レベル判定（特別警報・警報・注意報）も機能していなかった。
  3. **外部連携・API互換性**:
     - Homebridge プラグインや各種外部スクリプト・curl が送るパラメータ `target`（単数形）、`volume`（`volumeLevel` の別名）、`speed`（`rate` の別名）が FastAPI の `SayRequest`（POST）および `api_say_get`（GET）で定義されておらず、パラメータが無視されてデフォルト端末・デフォルト音量で再生されていた。
  4. **WebUI の整合性**:
     - 設定タブの Webhook サブタブ表示時に呼ばれる関数名が `updateWebhookSnippets` となっており、実際の実装 `updateBuilderCode` と不一致だったためコードスニペットの自動再生成がスキップされていた。
     - DND設定画面の「AI要約設定」クイックリンクが非実在の `btnSubtabSettingsAi` をクリックしており、外部連携サブタブに遷移しなかった。
  5. **最適化・耐障害性**:
     - 重複排除コードが `app/core/deduplication.py` と `app/services/speech_service.py` の2箇所に重複定義されていた。
     - `tts_service.py` で音声合成ごとに全MP3ファイルの `stat()` とソートを伴うLRU走査が行われており、キャッシュ蓄積時にディスクI/Oボトルネックとなる懸念があった。
     - `history_service.py` のJSON書き込みが直接上書きであり、電源断や強制再起動時にJSON破損を起こす危険があった。
- **修正内容**:
  1. **セキュリティ修正 (`data/go2rtc.yaml`, `entrypoint.sh`, `docker-compose.yml`, `app/core/security.py`)**:
     - `data/go2rtc.yaml` を新設し `api.listen: "127.0.0.1:1984"` を設定。`entrypoint.sh` を改修して未存在時にもローカル限定設定を自動生成して起動するよう保護。`docker-compose.yml` に `entrypoint.sh` のバインドマウントを追加。
     - `security.py` の `generate_session_token()` を `secrets.token_hex(32)` による暗号論的ランダムトークン生成に変更。
  2. **コア不具合解消 (`app/services/ai_service.py`, `app/services/disaster_service.py`)**:
     - `ai_service.py` に `is_available()` および `summarize_calendar_events()` を実装。予定（辞書/文字列問わず）と天気・降水確率・気温を親しみやすい日本語で要約するロジックを構築。Geminiモデルガードを同期し、最新の `3.5-flash` / `3.8-flash` を不当に降格しないよう修正。
     - `disaster_service.py` に気象庁警報コードマスタ辞書 `JMA_WARNING_CODES`（大雨・洪水・暴風雪・雷等）を導入。`check_weather_warnings` でコードを逆引きして名称と区分を取得し、ユーザー設定レベル（特別警報/警報/注意報）に応じた正確なフィルタリングと自然なアナウンスを生成するよう改修。
  3. **API互換性拡張 (`app/routers/speech.py`)**:
     - `SayRequest`（POST）に `target`, `volume`, `speed` を追加し、`targets = req.targets or req.devices or req.target`、`volume_level = req.volumeLevel if req.volumeLevel is not None else req.volume`、`rate = req.rate or req.speed` で正規化。
     - `api_say_get`（GET）にも `target`, `volume`, `speed` クエリパラメータを追加し、同様に正規化して `speech_service` および `scheduled_speech_service` に渡すよう改修。
  4. **WebUI 整合性修正 (`public/app.js`)**:
     - Webhook サブタブ表示時に `updateBuilderCode()` を呼び出すよう修正。
     - DND 画面からの AI 設定リンク先を `btnSubtabSettingsIntegrations` に修正し、AI設定カードへのスムーズスクロールアニメーションを追加。
  5. **最適化・堅牢化 (`app/core/deduplication.py`, `app/services/speech_service.py`, `app/services/tts_service.py`, `app/services/history_service.py`)**:
     - `deduplication.py` を共通モジュールとして一本化し、1000件超過時のみクリーンアップするO(1)軽量設計に統一。`speech_service.py` の重複クラスを排除。
     - `tts_service._cleanup_lru_cache()` に 10 分間のインターバル制御と単一 `stat()` タプル化を導入し、発話ごとの無駄なディスク走査を大幅削減。
     - `history_service.save_history()` を一時ファイル書き込み＋アトミック `replace` に改修し、耐障害性を強化。
- **検証結果**:
  - `ss -tlpn`: go2rtc が `127.0.0.1:1984` にのみバインドされ、外部露出が完全に遮断されていることを確認。
  - 単体・結合テスト: セッショントークンの一意性・ランダム性、AIカレンダーサマリー（Gemini API 連携・フォールバック）、気象庁コード逆引き、重複排除判定、アトミック履歴保存の全パスを確認。
  - API パラメータテスト: `target`, `volume`, `speed` パラメータが正常にパース・正規化されることを確認。
  - 構文検証: 全Pythonファイルの `py_compile` および `node -c public/app.js` のエラーゼロを確認。
  - コンテナ稼働: `SmartSpeaker-VoiceHub` がエラーなく安定稼働中であることを確認。

## 2026-10-19 01:50 - /goal 完遂: WebUI美観・ボタン状態遷移の徹底強化、指摘4機能（ONVIFプログレス・MQTTサマリー・MCPセグメント・Webhook時間指定）の完全解消、およびドキュメント（README / Manual）の最新化
- **背景と課題**:
  1. **WebUI の美観・動作の一貫性向上**:
     - デザインにおかしい点や見苦しい点がなく、ダークグラスモーフィズムと滑らかなマイクロアニメーションを完備すること。
     - 保存ボタンの保存中スピナーとエメラルドグリーンチェックマーク、ボタンのアクティブ状態などの視覚的フィードバックの徹底。
  2. **ユーザー指摘の4大課題の完全解消**:
     - **ONVIF/DLNA 自動スキャン**: ボタンを押しても約8秒間静止して見え、動作しているかわかりにくかった。
     - **MQTT ブローカー接続設定**: 接続中のブローカーの詳細情報や送受信統計が表示されていなかった。
     - **MCP サーバー連携**: 接続環境選択ボタン（ローカル/インターネット）をクリックしても見た目が変化せず動かないように見えていた。
     - **発声時刻指定の各種連携安心化**: Webhook ビルダーで時間指定が隠れており、Home Assistant、Node-RED、MCP 等で活用できるか不安があった。
  3. **ドキュメントの最新化**:
     - `README.md` と `Manual.md` を前回の要綱（過大表現を排した上品・謙遜・控えめなトーン、Edge-TTS の正確な位置づけ、全機能完全網羅）に沿って最新化すること。
- **修正内容**:
  1. **CSS スタイルシート全面強化 (`public/style.css`)**:
     - `.btn-secondary.active`, `.btn.active`, `.btn-segment.active`（青紫グラデーション＆発光グロー）新設。
     - モダンセグメントボタングループ `.btn-group-segmented`, `.btn-segment` 新設。
     - 保存ボタン共通アニメーション `.btn-saving`（回転スピナー）、`.btn-saved`（チェックマークバウンスアニメーション `@keyframes pulse-saved`）新設。
     - ONVIF スキャン進行インジケーター `.scan-progress-box`, `.scan-progress-bar-indeterminate` 新設。
     - MQTT サマリーボード `.mqtt-summary-board`, `.mqtt-summary-item` 新設。
     - Webhook 時刻指定クイック選択チップ `.time-quick-chip` 新設。
  2. **WebUI マークアップ改修 (`public/index.html`)**:
     - ONVIF: スキャン進行ボックス `#onvifScanProgressBox` を一覧上部に配置。
     - MQTT: 接続ステータスサマリーボード `#mqttSummaryBoard` を新設、各ブローカーカード内に統計エリアを配置。Node-RED / HA ガイドに発声時刻指定の具体例と JSON 例を追記。
     - MCP: 接続環境選択をセグメントボタングループ化。ツール仕様に予約発声関連ツールを追記。
     - Webhook ビルダー: アナウンス内容直下に「⏰ 発声時刻指定 (at / time)」常時表示セクションを新設。クイック選択チップ（`即時`, `+5分後`, `+10分後`, `+15分後`, `+30分後`, `+1時間後`）およびクリアボタンを配置。
  3. **フロントエンドロジック改修 (`public/app.js`)**:
     - サブタブ切り替え時に各設定画面（ONVIF, MQTT, MCP, Webhook）の描画・更新関数を漏れなく実行するリスナーを強化。
     - 共通保存ボタンヘルパー `setButtonSaving(btn, text)` を実装し、主要な全保存ボタンに適用。
     - ONVIF: スキャン中のプログレスバー連動と完了トースト内訳（検出台数・連携中台数）の明示。
     - MQTT: `updateMqttStatus()` によるサマリーボードおよび各カード内統計情報のリアルタイム描画。
     - Webhook ビルダー: クイックチップクリック時の `#builderAt` 自動入力、および cURL (GET/POST)、JSON、IFTTT の全スニペットへのリアルタイム連動。
  4. **ドキュメント全面改訂 (`README.md`, `Manual.md`)**:
     - `README.md`: 上品・謙遜な文体、Edge-TTS の正確で控えめな位置づけ（コミュニティ製ライブラリとしての試行的利用・公式クラウドAPIやローカルエンジンとの併用フォールバック設計）、未来の予約発声や最新機能の簡潔な紹介。
     - `Manual.md`: 目次・本文を最新化。4.6 発声時刻指定（タイマー予約発声）仕様の新設、8.2 Alexa公式Everywhereグループ自動集約、8.4 ONVIFタイムアウト・リトライ通信堅牢化、10章 MCP最新ツール、11章 MQTTサマリーボード、12章 WebUI視覚的フィードバック、13章 予約発声・システムログAPI、15章 シームレスログ＆システム起動バナー仕様の完全網羅。
- **検証結果**:
  - `browser_subagent` による実機検証を実施：
    - MCP セグメントボタンの切り替え（青紫グラデーションアクティブ化）および設定 JSON URL の即時更新を確認（エビデンス: `mcp_settings_segment_1792341976467.png`）。
    - Webhook ビルダーの発声時刻指定セクション常時表示、クイックチップクリック（`+10分後`）および cURL / JSON スニペットへの連動を確認（エビデンス: `webhook_time_chips_verified_1792342095888.png`）。
    - ONVIF スキャンボタン押下時のプログレスバー表示および完了後の14台検出表示を確認（エビデンス: `onvif_scan_completed_1792342159371.png`）。
    - MQTT ブローカー設定の保存ボタンによる保存中スピナーおよびエメラルドグリーン完了チェックマークの遷移を確認（エビデンス: `mqtt_saved_success_1792341881928.png`）。

## 2026-10-19 01:12 - Alexa全台／カメラ全台発声時の0台成功バグ解消（ネイティブグループ集約＆セマフォ制御・タイムアウト拡大）＆ リロード時タブ復元バグの修復
- **背景と課題**:
  1. **Alexa全台・カメラ全台発声の失敗 (0台成功)**:
     - WebUI の即時発言画面から「Alexa全台」や「カメラ全台」を選択して発声させた際に、送信は完了するものの「0台成功」や過半数の失敗が発生するケースが多発していた。
  2. **F5リロード時のタブ復元不全**:
     - 直前に開いていたタブ（「📜 システムログ」や「拡張・システム設定」等）がブラウザのF5/リロード後に復元されず、常に初期画面（「即時発言」）に戻ってしまう状態になっていた。
- **原因の特定**:
  1. **Alexa**: 登録端末36台に対して同時に 36 プロセスの `bash alexa_remote_control.sh` が一斉起動し、同一の `.alexa.cookie` を同時に読み書きしながら Amazon サーバーへ集中アクセスしたため、Amazon 側のレートリミット（`Rate exceeded`）に引っかかり全端末のリクエストが拒絶・失敗していた。また、Google Cast で行っているような公式スピーカーグループへの自動集約機構が Alexa には未導入だった。
  2. **カメラ (ONVIF)**: 登録10台のカメラへ同時に go2rtc バックチャンネルプッシュを行う際、httpx のタイムアウトが 5秒と短すぎたため、Wi-Fi カメラやスリープ状態のカメラとの RTSP/2-way audio ハンドシェイクが間に合わず `ReadTimeout` や `can't find consumer` が多発していた。
  3. **タブ復元**: `public/app.js` の末尾（7632行目）に新機能（システムログ）追加時の簡易 `async function init()` が重複して定義されたことで、JavaScript のホイスティング・上書き仕様によりファイル先頭（143行目）にあった本来の `init()`（`setupSettingsHandlers`, `restoreActiveTabs`, `loadInitialData` 等を実行する本体）が丸ごと上書きされ、リロード時のタブ復元関数 `restoreActiveTabs()` が一切実行されなくなっていた。
- **修正内容**:
  1. **Alexa ネイティブグループ集約 ＆ レートリミット防止 (`app/services/speech_service.py`, `app/services/alexa_service.py`)**:
     - `speech_service.py`: Google Cast 同様、Alexa 全台指定（`AL:ALL` や 4台以上のAlexa端末指定）時に、公式スピーカーグループ（ユーザー環境にある `"Alexa (全部)"` または `"Alexa (全部の部屋)"`）が存在すればグループ1台に自動集約するロジックを実装。1回のリクエストで全室 Echo から綺麗に同期発声。
     - `alexa_service.py`: セマフォ（最大2並列）による並行数制御、コマンド実行間インターバル（0.15s）、`Rate exceeded` 検知時の自動リトライ、および `list_devices()` でのグループ自動判定（`isGroup: True`）を実装。
  2. **カメラ (ONVIF) タイムアウト拡大 ＆ セマフォ・リトライ制御 (`app/services/onvif_service.py`)**:
     - `onvif_service.py`: セマフォ（最大3並列）による同時接続数制御、httpx タイムアウトを 5秒から 15秒へ大幅拡大、`can't find consumer` 発生時の自動ストリーム再登録＆リトライ機構を実装。
  3. **WebUI タブ復元機能の修復 ＆ トーストフィードバック改善 (`public/app.js`)**:
     - `app.js`: 末尾の重複 `init()` 定義を完全削除し、先頭の正規 `init()` 内で `setupSystemLogsTab()` および `restoreActiveTabs()` が確実に実行されるよう修復。
     - 即時発声完了トーストにおいて、全台失敗時は赤色エラー（`0台成功でした。ログを確認してください`）、一部成功時は黄色警告（`X / Y 台成功`）、全台成功時は緑色と正確にフィードバックするよう改善。
- **検証結果**:
  - **Alexa 全台送信テスト**: `Alexa (全部)` グループへ自動集約され、100% 成功（1台送信完了・全室同期発声）を確認。
  - **カメラ全台送信テスト**: `ReadTimeout` が完全に解消され、現在バックチャンネル接続が有効なカメラ（7/10台）で安定して音声再生が成功することを確認。
  - **ブラウザ実機テスト**: `browser_subagent` による実機検証を実施し、リロード後も直前に開いていた「📜 システムログ」タブが確実に復元されることを確認。

## 2026-10-19 01:00 - システム起動・再起動・シャットダウンの明示的バナーロギング強化 ＆ WebUIモジュール絞り込み対応
- **背景と課題**:
  1. システム再起動やコンテナ再起動、またはクラッシュ後の再開が発生した際に、ログを一目見るだけで「いつ再起動されたか」「正常終了か異常終了か」が瞬時に判断できるようにしたいという要望。
  2. 従来のログでも Uvicorn の起動ログや各ワーカーの開始ログは出力されていたが、標準のログフォーマット（タイムスタンプ・モジュール名・レベル）に統一された目立つ境界線バナーを出力することで、WebUI 上や grep 検索で瞬時に特定できるように改善。
- **修正内容**:
  1. **起動・再起動・シャットダウンバナーの導入 (`app/main.py`)**:
     - `lifespan` 起動時に `VoiceHub.System` モジュールから `🚀 [VoiceHub] システム起動 / 再起動 (VoiceHub Engine Started)` およびプロセスPID、環境、ポート情報を挟んだ目立つ区切り線ログを出力。
     - 正常終了（シャットダウン）時に `🛑 [VoiceHub] システム終了 / シャットダウン処理開始` および `✅ [VoiceHub] シャットダウン完了` を出力。
  2. **WebUI ログビューアのモジュール絞り込み拡張 (`public/index.html`)**:
     - モジュール選択ドロップダウンに `System (起動・再起動・終了)` および `ScheduledSpeech (予約発声)` を追加。クリック1つでシステムの起動・再起動履歴をピンポイント抽出可能に。
- **検証結果**:
  - コンテナ再起動テストを実施し、`/logs/container.log` に `🚀 [VoiceHub] システム起動 / 再起動 (VoiceHub Engine Started)` が境界線付きで確実に記録されることを確認。
  - API (`/api/logs?module=System`) および WebUI 画面上で起動バナーが綺麗に表示されることを確認。

## 2026-10-19 00:52 - WebUIシステムログのシームレス連携（退避後も最大1,000行を維持表示）＆ 発声時刻指定オプション（過去即時・未来予約発声・再起動耐性）の実装
- **背景と課題**:
  1. **WebUIログのシームレス表示**:
     - 1,000行超過時や日付変更時に `container-archive.log` へ退避された直後、アクティブログの行数がリセットされてしまい、WebUIの表示が一時的に数行〜ゼロ行になって過去のログの流れが見えなくなる課題があった。
     - WebUI（およびAPI）側でアクティブログが 1,000行 未満の場合、`container-archive.log` の直近末尾行から自動補充・結合し、画面上は常に最新最大1,000行が途切れずシームレスにスクロール閲覧できるようにする。
  2. **発声時刻指定オプション（過去即時・未来予約発声）**:
     - Webhook、REST API、MQTT、MCPツール、WebUIの各種連携において、「発声時刻」オプション（`at`, `time`, `scheduled_at`, `datetime`）を指定可能にし、過去日時なら即時発声、未来日時ならその時刻に自動発声するタイマー予約機能の実装が求められた。
     - コンテナの再起動やホスト再起動、エラー中断が発生しても予約タスクが失われないよう、永続化キューに安全に保存し、起動時に自動復旧・遅延回収する再起動耐性を備えること。
- **修正内容**:
  1. **シームレスログ取得機能の実装 (`app/routers/logs.py`)**:
     - 大容量アーカイブファイル（最大100MB）でも高速かつ低メモリで安全に読み込める `read_tail_lines()` を実装（末尾逆シーク・64KBチャンク走査）。
     - `GET /api/logs` において `active_lines` が要求 `limit` 未満の場合、`container-archive.log` の末尾から不足分を自動補完・結合。
     - レスポンスに `seamless_total`, `is_seamless` メタデータを追加し、WebUI ログビューアの件数バッジに反映。
  2. **発声時刻指定＆予約発声サービスの実装 (`app/services/scheduled_speech_service.py`)**:
     - `parse_schedule_time()`: ISO 8601、時刻文字列（`HH:MM`）、相対時間指定（`+5m`, `+10min`, `+1h`, `+30s`）、UNIXタイムスタンプを柔軟にパース。
     - 過去判定（現在時刻以前）: 通常の `speech_service.speak` を即時実行（`scheduled: false`）。
     - 未来判定: 永続ファイル `DATA_DIR / "scheduled_speeches.json"`（名前付きボリューム `voice_data`）にアトミック保存し、即時受付レスポンス（`scheduled: true`, `status: "scheduled"`）を返却。
     - バックグラウンドワーカー `_worker_loop()`: 毎秒チェックし、期日到来時に自動発声ディスパッチ。多重実行を防止する `status: "running"` アトミック更新。
     - サービス起動時の復旧処理: 停止中に予定時刻を過ぎたタスクも起動時に即座に遅延実行・回収。
     - 予約一覧取得 API (`GET /api/scheduled-speeches`)、予約キャンセル API (`DELETE /api/scheduled-speeches/{id}`) を実装。
  3. **アプリケーション起動連動 (`app/main.py`)**:
     - FastAPI `lifespan` 内で `scheduled_speech_service.start()` を登録し、バックグラウンドワーカーを常駐稼働。
  4. **各種連携プロトコルへの時刻オプション追加**:
     - **Webhook / REST API (`app/routers/speech.py`)**: `SayRequest` に `at`, `time`, `scheduled_at`, `datetime` を追加。`POST /api/say`, `POST /api/webhook`, `GET /api/say` で時刻指定を受け付け。
     - **MQTT (`app/services/mqtt_service.py`)**: JSON ペイロード内の `time`, `at`, `scheduled_at`, `datetime` を解析して `schedule_or_speak` にディスパッチ。
     - **MCP ツール (`app/services/mcp_service.py`)**: `speak` ツールの inputSchema に `at` プロパティを追加。さらに `list_scheduled_speeches`, `cancel_scheduled_speech` ツールを新設。
  5. **WebUI マークアップ & フロントエンド制御 (`public/index.html`, `public/app.js`, `public/style.css`)**:
     - 即時発声タブ: 「⏰ 発声時刻を指定する (日時指定・タイマー予約)」アコーディオンを新設。`<input type="datetime-local">`、リセットボタン、クイックボタン（`+5分`, `+10分`, `+15分`, `+30分`, `+1時間`）。未来時刻選択時は発声ボタンが「⏰ [時刻] に予約発声する」へ自動切り替え。
     - Webhook URL ビルダー: オプション内に「⏰ 発声時刻指定 (at / time)」入力欄を新設し、cURL (POST/GET)、JSON、IFTTT のコードスニペットへリアルタイム自動反映。
     - スケジュールタブ: 「⏰ 予約中の発声タスク (One-off Speeches)」カードを新設。待機タスク一覧、残り時間バッジ、宛先、文言、手動更新ボタン、🗑️ 取消ボタンを装備。
- **検証結果**:
  - コンテナ内テストスクリプトにより以下を検証し、全テスト通過：
    1. 過去日時指定（2020年）での即時発声 (`scheduled: false`) 成功
    2. 未来日時指定（`+8s`）での予約登録、待機一覧確認、8秒後の自動発声実行・ステータス `completed` 遷移成功
    3. 予約キャンセル（`DELETE /api/scheduled-speeches/{id}` -> `cancelled`）成功
    4. シームレスログ取得 API の動作確認
  - `browser_subagent` によるブラウザ実機確認を実施し、即時発声タブでの日時選択・予約ボタン変化、およびスケジュールタブでの予約タスク一覧表示・残り時間バッジ描画を確認。

## 2026-10-19 00:34 - システムログビューアの行間・余白の是正（不要空行の解消と等幅ターミナルコンソール表示の最適化）
- **背景と課題**:
  1. WebUI の「📜 システムログ」タブで、ログの各行の間に2〜3行分に相当する大きな空白（空行）が空いてしまい、画面内の情報密度が低く、スクロールしないとログの流れを追えない状態となっていた。
  2. 原因調査の結果、`#logsTerminal` のコンテナに `white-space: pre-wrap;` が指定されていたこと、および `app.js` のテンプレートリテラル内に含まれていた改行・インデントコードが親要素の `pre-wrap` によって空行としてブラウザにレンダリングされていたことが判明。
- **修正内容**:
  1. **マークアップのスタイル見直し (`public/index.html`)**:
     - `#logsTerminal` のインラインスタイルから `white-space: pre-wrap;` を除去。
  2. **スタイルシートの洗練 (`public/style.css`)**:
     - `.logs-terminal`: `display: flex; flex-direction: column; gap: 2px;` を追加し、各行を規則正しい等間隔グリッドとして整列。
     - `.log-line-item`: パディングを `2px 6px`、`line-height: 1.4`、`min-height: 24px` に調整。
     - `.log-badge-level`, `.log-badge-module`: `white-space: nowrap;`、行高 `1.25` でテキストとの縦位置を最適化。
     - `.log-message-content`: `white-space: pre-wrap; word-break: break-all;` を個別適用し、ログ本文の改行のみを適切に保持。
  3. **行要素生成コードの最適化 (`public/app.js`)**:
     - `app.js` の `renderSystemLogs()` において、テンプレートリテラルの余分な改行・インデントを除去し、1行のコンパクトな HTML 文字列として結合するよう改善。
- **検証結果**:
  - `browser_subagent` を用いて実機 WebUI を確認（`system_logs_page_1792337656881.png`）。
  - 各行の間に挟まっていた無駄な空行が解消され、一般的な Linux ターミナルや VS Code のコンソールと同様に、1画面で20行以上のログが等間隔でスッキリと一覧・視認できるようになったことを確認。

## 2026-10-19 00:25 - システムログタブ新設・永続Volumeローテーション（1000行退避＆100MB zstd圧縮10世代保持）・プロジェクト全体ログ出力強化
- **背景と課題**:
  1. **WebUI システムログタブ新設**:
     - コンテナのコンソールログを WebUI 上からリアルタイムに閲覧・確認・検索できるようにするため、メインタブ「拡張・システム設定」の右隣に「📜 システムログ」タブを新設。
  2. **永続 Volume 保存と高度なログローテーション仕様**:
     - ログを Docker 名前付き永続ボリューム（`voice_logs:/logs`）配下の `/logs/container.log` に確実に永続化。
     - **行数・日跨ぎ退避**: ログ行数が 1,000 行を超えるか、日付が変わったタイミングで `container-archive.log` に移動（追記退避）。
     - **サイズ上限 & zstd 圧縮保持**: `container-archive.log` が 100MB を超えた場合、高速高圧縮な `zstd` で圧縮し、最大 10 世代保持（`container-archive.log.{1..10}.zst`）。11世代以上の最古アーカイブは自動パージ。
  3. **プロジェクト全体のログ出力強化 (トラブルシューティング容易化)**:
     - 前回ログ改修以降に実装された新機能群（TTS多段フォールバック推移、Azure/GCPクォータガード判定、ローカル音声エンジンのGPU/CPU自動ルーティング＆死活監視、Cast/ONVIFスピーカー再生、MQTT Discovery、MCP連携等）を含め、何が起きたかを瞬時に把握できるようログ出力を全面強化。
- **修正内容**:
  1. **Docker 構成・環境依存関係の拡張 (`docker-compose.yml`, `Dockerfile`, `requirements.txt`)**:
     - `docker-compose.yml`: `voice-hub` サービスに `- voice_logs:/logs` をマウントし、`volumes:` に `voice_logs: name: smart_speaker_logs` を新設。
     - `Dockerfile`: Debian パッケージに `zstd` を追加。
     - `requirements.txt`: Python パッケージ `zstandard>=0.23.0` を追加。
  2. **ログローテーター基盤の実装 (`app/core/log_rotator.py`, `app/core/logger.py`)**:
     - `ContainerLogHandler`: 1,000行超過または日付跨ぎでの `container-archive.log` へのアトミック退避、100MB 超過時の `zstandard` ストリーム圧縮、ローテーションおよび 10 世代パージを安全に実行するハンドラーを実装。
     - `StdStreamTee`: `sys.stdout` および `sys.stderr` をフックし、標準出力・標準エラー出力・uvicorn アクセスログをコンソールと `/logs/container.log` の双方へ安全に Tee 出力。
  3. **ログ管理 API の新設 (`app/routers/logs.py`, `app/main.py`)**:
     - `GET /api/logs`: リアルタイムログ取得（件数制限 `limit` 最大1000件、`level` フィルタ、`module` フィルタ、キーワード検索）。現在の行数、ファイルサイズ、アーカイブサイズ、保持世代数を含むメタデータも返却。
     - `GET /api/logs/download`: `current`（アクティブログ）、`archive`（未圧縮アーカイブ）、`compressed`（zstd圧縮アーカイブ）の安全なダウンロード。
     - `DELETE /api/logs`: 手動アーカイブ退避＆アクティブログのクリア。
     - `app/main.py`: アプリケーション起動時に `init_system_logging()` を実行、ルーター登録。WebUI ログ自動更新による `/api/logs` のアクセスログ自己増殖を抑制。
  4. **WebUI システムログタブ UI & 制御ロジック (`public/index.html`, `public/style.css`, `public/app.js`)**:
     - メインタブバーに「📜 システムログ LIVE」ボタン（`#btnTabLogs`）を新設。
     - ツールバー: 3秒自動更新スイッチ（LIVEパルス点滅アニメーション）、末尾自動スクロール追従、キーワード検索、ログレベル選択、モジュール選択、アクティブログ保存、アーカイブ保存、ログ消去ボタン、ステータスバッジ（行数・サイズ・アーカイブ情報）。
     - ターミナル風ダークビューア: JetBrains Mono 等幅フォント、ログレベル別カラータグ（DEBUG/INFO/WARNING/ERROR）、モジュール別カラーバッジ、キーワードハイライト、マウススクロール検知による自動スクロール一時解除/復帰。
     - `localStorage` によるタブ状態復元、アクティブタブ切り替え時の即時取得を連動。
  5. **プロジェクト全体のログ出力見直し & 詳細ログ強化**:
     - `app/services/tts_service.py`: `get_logger("TTS")` により、一次エンジン指定、テキスト文字数、キャッシュHIT/MISS、合成処理時間、GCP9割ガード発動、Azure 429フォールバック推移、最速並行レースのログを詳細化。
     - `app/services/tts/azure_provider.py`: `get_logger("TTS.Azure")` により、429上限エラー、401認証エラー、合成成功ステータスログを追加。
     - `app/services/tts/gcp_provider.py`: `get_logger("TTS.GCP")` により、403認証エラー、429制限、合成成功ステータスログを追加。
     - `app/services/tts/voicevox_provider.py`: `get_logger("TTS.VoiceEngine")` により、合成成功ログ（wav->mp3サイズ変換情報）を追加。
     - `app/services/tts/edge_provider.py`: `get_logger("TTS.Edge")` により、合成成功ログを追加。
     - `app/services/tts/usage_tracker.py`: `get_logger("TTS.Usage")` により、文字数加算ログを追加。
     - `app/services/cast_service.py`: `print` を `get_logger("Cast")` に刷新、Chromecast 接続、メディアロード、再生開始、エラーハンドリングログを強化。
     - `app/services/onvif_service.py`: `print` を `get_logger("ONVIF")` に刷新、go2rtc連携、2-way audioストリーム再生ログを強化。
     - `app/routers/speech.py`: `get_logger("Speech")` により、リクエスト受信、話者解決、ハードウェア自動判定（GPU/CPU優先選択）のログを強化。
- **検証結果**:
  - `ContainerLogHandler` の単体テスト（1000行退避、日付跨ぎ、10世代パージ）を実施し全テスト通過。
  - Docker コンテナビルドおよび再起動が正常完了。
  - `/logs/container.log` にログが出力され、`/api/say` テスト実行時に TTS -> Speech -> Cast の一連の処理ログが記録されることを確認。
  - WebUI ブラウザ検証にて、システムログタブの表示、色分けバッジ、自動更新、検索・レベルフィルタ、ステータス表示が完全稼働することを確認済み。

## 2026-10-18 23:55 - Google Cloud Text-to-Speech (GCP) 無料枠9割到達時自動フォールバック（課金防止安全ガード）実装
- **背景と課題**:
  1. Azure Speech Service（F0 無料プラン）は月間 50 万文字の上限に達すると API から HTTP 429 エラーが返り、自動的に他エンジンへフォールバックされるが、Google Cloud TTS は従量課金アカウントが紐づいているため、無料枠（月間 100 万文字）を超過しても API が成功し続け、そのまま課金が発生してしまう。
  2. ユーザーが意図しない課金を防止するため、当月の無料枠使用量が 9 割（90% = 900,000文字）に達した段階で、自動的にローカル音声エンジン（VOICEVOX / SHAREVOX / COEIROINK 等）や Azure / Edge-TTS へフォールバックするオプション機能の追加要望。
- **修正内容**:
  1. **バックエンド使用量判定ロジック新設 (`app/services/tts/usage_tracker.py`)**:
     - `is_quota_near_limit(provider="gcp", model_type="neural", threshold_ratio=0.9) -> bool`: 当月の使用文字数を取得し、90%（900,000文字）以上か否かを判定するセーフティ判定関数を実装。
  2. **GCP プロバイダー設定拡張 (`app/services/tts/gcp_provider.py`)**:
     - `fallback_on_quota_near_limit: bool = True` 属性、および `update_config` での受領処理、プロバイダー単体での `is_quota_near_limit()` 判定メソッドを追加。
  3. **TTS サービス統合制御 (`app/services/tts_service.py`)**:
     - `sync_settings()`: 設定 JSON から `fallbackOnQuotaNearLimit` を GCP プロバイダーへ同期。
     - `get_fallback_candidates()`: 90% 到達時かつオプション有効時、GCP をフォールバック試行リストから自動除外。
     - `_synthesize_raw()`: ユーザーまたは API 呼び出し元が一次プロバイダーとして明示的に GCP を指定した場合でも、90% 到達時は安全にスキップして次候補への段階的フォールバックへルーティング。
     - 緊急速報時の最速並行生成（`urgent_fastest`）レース対象からも、90% 到達時は GCP を除外。
     - `get_providers_status()`: WebUI 向けに `fallbackOnQuotaNearLimit` の現在設定値を返却。
  4. **WebUI マークアップ & デザイン (`public/index.html`)**:
     - GCP 設定カード内（無料枠プログレスバー直下）に「🛡️ 無料枠9割（90%）到達時に自動フォールバック（課金防止安全ガード）」トグルスイッチ（`#settingGcpFallbackNearLimit`）および注意書き・到達時警告バッジ（`#badgeGcpQuotaGuard`）を配置。
  5. **WebUI 連動制御 (`public/app.js`)**:
     - `loadTtsProvidersSettings()`: バックエンドから設定値をロードしてトグルへ反映。また、使用量が 90% を超えている場合はプログレスバーを警告色（オレンジ `#f59e0b`）に変更し、警告バッジを表示。
     - `saveTtsProvidersSettings()`: 保存時に `fallbackOnQuotaNearLimit` をペイロードに含めてバックエンドへ永続化。
- **検証結果**:
  - コンテナ内での単体テストスクリプトにより以下を実証：
    - 通常時（100文字使用）: フォールバック候補に GCP が正常に含まれる。
    - 9割到達時（900,001文字使用）: フォールバック候補から GCP が自動除外される。
    - 一次プロバイダーに GCP を指定して音声生成を要求した場合でも、API 呼び出しを未然に防ぎ、次候補（Azure/VOICEVOX等）へシームレスに自動フォールバックされることを確認。

## 2026-10-18 23:40 - ローカル音声エンジンのONVIF風接続テスト後登録フロー刷新・オンライン死活監視テーブル実装・話者グループ名標準化
- **背景と課題**:
  1. **ONVIF風の接続テスト後登録フローへの刷新**:
     - 従来の「空の枠を追加して直接編集保存する方式」から、ONVIFカメラと同様に、接続先 URL を入力して「🔌 接続テスト」に成功した場合のみ「＋ 登録する」ボタンが活性化し、安全かつ確実に登録できるフローへの改善要望。
  2. **有効な音声エンジン一覧（オンライン/オフライン死活監視テーブル）の実装**:
     - 登録された複数台の音声エンジン（VOICEVOX / SHAREVOX / COEIROINK / 互換）の稼働状態（🟢 稼働中: GPU/CPU/レイテンシ / 🔴 停止中 / ⏳ 未確認）、種別、管理用表示名、接続先 URL、有効/無効スイッチ、および単体再テスト・削除ボタンを備えた一覧テーブルを新設。全台一括の死活再確認ボタンも装備。
  3. **話者選択肢のグループ表示名統一 & 重複排除**:
     - 登録時にユーザーが命名した管理用表示名（例: メインGPU機、書斎ミニPC等）が話者選択画面のグループ名に出てしまい、複数台追加した際にどのエンジンか混乱を招くのを防ぐため、話者グループを一律「VOICEVOX」「SHAREVOX」「COEIROINK」に標準化。同一話者が複数サーバーから重複取得された場合の重複排除も実施。
- **修正内容**:
  1. **話者名・プロバイダー名標準化 & 重複排除 (バックエンド & フロントエンド)**:
     - `app/services/tts/voicevox_provider.py`: 話者一覧取得時に `id` を `{eng_type}:{style_id}`、`provider` を `{eng_type}`（`voicevox`/`sharevox`/`coeiroink`）、`providerName` を大文字正規化。
     - `app/services/tts_service.py`: `get_voices()` 内で `seen_voice_keys` を用い、同一種別・同一IDの話者を重複排除。
     - `public/app.js`: `renderVoiceSelects()` で `v.provider` を正規化マッピングし、グループラベル（`<optgroup>`）を一律「VOICEVOX」「SHAREVOX」「COEIROINK」に統一。
  2. **WebUI マークアップ刷新 (`public/index.html`)**:
     - `subtab-settings-tts` 内のローカル音声エンジン設定エリアを全面刷新。
     - ONVIF と共通のトーン＆マナーを持つ「➕ 音声エンジンを追加 (接続テスト＆登録)」フォーム（エンジン種別、管理用表示名、接続先URL、タイムアウト、接続テストボタン、登録ボタン、リアルタイムフィードバック）および「🔊 登録済み音声エンジン一覧 (稼働状態・オンライン監視)」テーブル（`#voiceEnginesTableBody`）を配置。
     - ヘッダーに「🔄 全台の死活を再確認」ボタンと総登録件数バッジを配備。
  3. **動的登録・死活監視・保存ロジック刷新 (`public/app.js`)**:
     - `setupVoiceEngineRegistrationForm()`: 入力変更時の登録ボタン非活性化リセット、接続テスト成功時のみ `tempTestedNewEngine` にハードウェア情報（GPU/CPU/レイテンシ）を保持して「＋ 登録する」ボタンを活性化する安全な登録フローを実装。
     - `renderVoiceEnginesTable()`: テーブル形式での一覧描画、有効/無効トグル変更時のサイレント自動保存、単体再テスト、削除処理を実装。
     - `checkAllVoiceEnginesStatus()`: 登録されている全音声エンジンへ並列で死活テストを実施し、稼働中/停止中状態およびハードウェア性能バッジをテーブルにリアルタイム反映。
     - `saveTtsProvidersSettings(silent)`: `state.voiceEngines` と直接同期し、サイレント自動保存および通常保存に対応。
- **検証結果**:
  - `browser_subagent` による実機検証にて、最新の ONVIF 風フォームおよび一覧テーブルが正常に描画されることを確認。
  - 存在しないアドレスに対する接続テストでエラーメッセージが表示され、「＋ 登録する」ボタンが無効化のまま保持される安全設計を確認。
  - 「🔄 全台の死活を再確認」ボタンおよび単体再テストボタンの押下で、各エンジンの稼働状態（停止中・稼働中）がテーブルにリアルタイム反映されることを確認。
  - 即時発言画面の話者セレクトボックスにて、登録名に依存せず一律標準名（「VOICEVOX」「SHAREVOX」「COEIROINK」「Azure Speech」「Google Cloud TTS」）で綺麗にグループ化されていることを確認。

## 2026-10-18 23:00 - Google Cast (Chromecast) 304再生停止バグ解消・F5タブ復元・GPU自動判別＆優先ルーティング・TTSキャッシュ健全化
- **背景と課題**:
  1. Google Home（Chromecast）で Azure 音声を再生しようとした際、音声が流れない問題が発生していた。
     - 原因特定:
       - 同一 URL を再取得する際、旧実装（StaticFiles）が `HTTP 304 Not Modified` を返却し、Chromecast が無音で再生を停止していた。
       - この 304 を防止しようと URL に付与したキャッシュバスター `?t=...` が原因で、Google Cast の MediaController がクエリ文字列付き URL を無効とみなし、サーバーへのリクエスト（GET）自体を行わなくなっていた。
  2. ブラウザをリロード（F5）した際、常に初期画面（即時発言タブ）に戻ってしまい、直前に操作していた設定サブタブ（TTS等）へ手動で戻る手間が発生していた。
  3. 即時発言画面の「話者 (Edge TTS)」ラベル表記の是正。
  4. ローカル音声エンジン（VOICEVOX / SHAREVOX / COEIROINK）の接続テスト時に GPU/CPU のハードウェア自動判定およびレイテンシ計測を行いたい。
  5. 同一エンジンが複数登録されている場合、GPU 搭載機・高速応答機を自動的に優先ルーティングし、障害時には他機へフェイルオーバーしたい。
  6. キャッシュ機能の総合的な健全性検証（TTS キャッシュ生成・LRU クリーンアップ・HTTP 配信ヘッダー・キャッシュヒット時の無音防止）。
- **修正内容**:
  1. **Google Cast メディア URL 是正 & 304 撲滅**:
     - `app/services/speech_service.py`: `audio_url` からクエリパラメータ `?t=...` を完全撤去し、純粋な `.mp3` URL に統一。
     - `app/main.py`: `/voice/{filename}` 専用エンドポイント（`FileResponse`）を新設し、`methods=["GET", "HEAD"]`、`Cache-Control: no-cache, no-store, must-revalidate`、`Accept-Ranges: bytes` を設定。Starlette の `FileResponse` により Range リクエスト（206 Partial Content）をネイティブ処理し、クライアントからの `If-None-Match` に対しても 304 を返さず実データを常時配信。
  2. **F5 / リロード時のタブ状態自動復元**:
     - `public/app.js`: メインタブおよび設定サブタブの選択状態を `localStorage`（`voicehub_active_main_tab`, `voicehub_active_settings_subtab` 等）に自動退避。初期化完了時に `restoreActiveTabs()` で直前のタブ画面をシームレスに自動展開。
  3. **話者ラベル表記是正**:
     - `public/index.html`: `話者 (Edge TTS)` を `話者` に変更。
  4. **ローカル音声エンジンの GPU 自動判別 & レイテンシ計測**:
     - `app/routers/speech.py`: `detect_local_engine_hardware()` を新設。`/supported_devices` API 照会（CUDA/DirectML）＋短文ベンチマーク（所要時間 ms 計測）によるハイブリッド判定を接続テスト API に統合。
     - `public/app.js`: エンジンカードヘッダーに `🚀 GPU (CUDA) 85ms` / `🐢 CPU` バッジをリアルタイム反映し、設定データに保持。
  5. **GPU 優先ルーティング & 自動フェイルオーバー**:
     - `app/services/tts_service.py`: `sync_settings()` で各エンジンに `is_gpu`, `latency_ms` を保持。同一種別（voicevox 等）の複数登録時に GPU 搭載・低レイテンシ機をプライマリに自動選定。さらに `get_fallback_candidates()` でも GPU/高速機順にソートして自動フェイルオーバーするように実装。
  6. **TTS キャッシュ機能の検証**:
     - 新規音声生成時のキャッシュファイル保存、2回目発話時のキャッシュヒット（Azure API 通信スキップ・消費文字数ゼロ）、および Google Home 実機での HTTP 206 Partial Content による連続正常再生を確認。
- **検証結果**:
  - 実機 Google Home（部屋: 192.168.11.97）への発話テストにて、初回およびキャッシュヒット時の双方が `HTTP 206 Partial Content` で受信され、正常に再生されることをログにて確認。
  - `browser_subagent` による実機検証にて、F5 リロード後も「⚙️ 拡張・システム設定」の「🎙️ 外部音声エンジン (TTS)」画面が即座に自動復元されることを確認。

## 2026-10-18 22:30 - MCP ツール連携における Cloudflare Tunnel FQDN 自動置換機能・手動入力対応・トークン自動同期の実装
- **背景と課題**:
  - MCP ツール連携（Claude Desktop / Cursor / Cline）において、接続環境「🌐 インターネット」を選択した際、URL に `your-tunnel-domain.com` というプレースホルダーが表示されたままとなり、設定されている Tunnel ドメインが自動反映されていなかった。
  - また、設定画面上で Tunnel FQDN を確認・手動上書き・リセットできる UI がなく、Webhook トークンの変更もリアルタイムにスニペットに反映されていなかった。
- **修正内容**:
  - `public/index.html`: MCP 連携画面の接続環境選択下に「🌐 Cloudflare Tunnel FQDN」入力欄、自動検出バッジ、および「🔄 リセット」ボタンを配置。
  - `public/app.js`:
    - `loadServerStatus` / `loadInitialData` 完了時に Tunnel ドメインおよび Webhook トークンを MCP スニペットに即時反映。
    - `updateMcpConfigSnippets()` で `state.serverInfo?.tunnelDomain` や入力欄から Tunnel FQDN を動的取得し、インターネット選択時に URL を自動生成。
    - Webhook 認証トークン保存時にも連動して MCP 設定 JSON を即時更新。
- **検証結果**:
  - `browser_subagent` による実機検証にて、「🌐 インターネット」選択時に `webhook.kit-a.net` が自動入力され、Claude Desktop / Cursor 設定 JSON 内の URL が `https://webhook.kit-a.net/mcp/sse?token=...` に自動置換されていることを確認。

## 2026-10-18 22:15 - TTS エンジン構成再編・名称是正・多段フォールバック・ローカル音声エンジン動的複数追加の実装
- **背景と課題**:
  - `Microsoft Edge TTS` という表記について、利用実態が非公式 Python ライブラリ（edge-tts）であるため、Microsoft の名を排して `Edge-TTS` に統一。
  - 公式 SLA を持つ Azure Speech Service 有効時は、通常の話者選択肢から Edge-TTS を除外し、全エンジン障害時の「いざというときの最終手段（セーフティネット）」として待機させる設計へ変更。
  - 障害発生時のフォールバック処理を、設定されているエンジンを優先度順（Azure → GCP → ローカル音声エンジン群）に順次試行し、すべて失敗した場合の最後の命綱として Edge-TTS で合成する「多段フォールバック（Cascading Fallback）」に刷新。
  - VOICEVOX / SHAREVOX / COEIROINK 等のローカル音声エンジンを単一エリアに統合し、別 PC や GPU サーバー上の複数インスタンスを無制限に「➕ 音声エンジンを追加」できる動的リスト構造へ拡張。
  - 設定画面の並び順を `Azure` & `GCP`（上段）→ `ローカル音声エンジン群`（中段）→ `Edge-TTS (最終フォールバック)`（下段）に最適化。
- **修正内容**:
  - バックエンド: `app/services/settings_service.py`, `app/services/tts_service.py`, `app/services/tts/edge_provider.py`, `app/routers/speech.py`
  - フロントエンド: `public/index.html`, `public/app.js`
  - ドキュメント: `Manual.md`, `README.md`
- **検証結果**:
  - 無効エンジン指定時の多段フェイルオーバー検証（HTTP 200, 59KB）、および Azure/GCP を停止した全滅時テストで Edge-TTS が最後の命綱として発動（HTTP 200, 30KB, `Was Fallback: True`）することを確認。
  - `browser_subagent` による UI 並び順、動的エンジン追加、設定保存、バッジ表示の正常確認。

## 2026-10-18 21:52 - 音声エンジン設定保存時の `fetchVoices is not defined` エラーの解消
- **背景と課題**:
  - WebUI 設定画面の「💾 音声エンジン設定を保存」ボタンを押下した際、サーバー側への設定保存（HTTP 200）は完了したものの、直後の画面更新処理で `fetchVoices is not defined` の ReferenceError が発生し、画面上に「設定保存エラー: fetchVoices is not defined」と表示されていた。
- **原因と修正内容**:
  - `public/app.js` の `saveTtsProvidersSettings()` 内において、既存の話者一覧取得関数が `loadVoices()` であったのに対し、推測で `fetchVoices()` を呼び出していたため ReferenceError が発生していた。
  - `public/app.js` の該当箇所を `if (typeof loadVoices === 'function') await loadVoices();` に是正。
- **検証結果**:
  - `browser_subagent` による実機ブラウザ操作にて、「💾 音声エンジン設定を保存」ボタン押下後にエラーが発生せず、「外部音声エンジン (TTS) 設定を保存しました」の成功トーストが正常に表示されることを確認。
- **再発防止策**:
  - `logs/past-mistake.md` および `logs/past-mistake-title.md` に [2026-10-18 06] として記録。

## 2026-10-18 21:47 - Edge TTS の非公式・仕様変更リスクの客観的明記と公式 Azure Speech Service（推奨）への位置づけ是正
- **背景と目的**:
  - 標準の Edge TTS は初期設定不要で動作する反面、Microsoft Edge ブラウザの内部通信を利用した非公式（グレー）な手法であり、Microsoft 側のサイレント仕様変更によって世界規模で利用不能になるリスクが過去にも頻発している。
  - 一方で Azure Speech Service は Microsoft 公式の正規 SLA を持つクラウド API であり、家庭内アナウンス・防災速報の長期安定稼働における本命・バックアップとしての真の価値を持つ。
  - 先の案内で「Edge TTS と全く同じなので無理に Azure を登録しなくてよい」と過度な安心感を与えてしまっていた表現を猛省し、プロジェクトの「慎みをもって上品・客観的に記載する」方針に則り是正。
- **実施内容**:
  1. **Web GUI 実装 (`public/index.html`)**:
     - Azure カードの折りたたみガイド冒頭の案内文を改定。Edge TTS が手軽な反面非公式で仕様変更リスクを伴うこと、および公式 Azure Speech が突然の停止リスクのない「長期安定運用や Edge TTS 不調時の堅牢なバックアップとしての推奨選択肢」であることを誠実に明記。
  2. **技術仕様書更新 (`Manual.md`)**:
     - 4.5.1 節のプロバイダー一覧表における Edge TTS のプロトコル種別を「非公式ブラウザストリーミング」と明記し、Azure Speech を「公式 SLA に基づき永続的・安定的に稼働する堅牢なバックアップ」と位置づけ。
     - 4.5.5 節の Azure ガイド補足を「公式 Azure Speech をおすすめする理由」へと差し替え。
  3. **ミス・再発防止記録更新**:
     - `logs/past-mistake.md` および `logs/past-mistake-title.md` に [2026-10-18 05] として「非公式・非保証ライブラリ（Edge TTS）を公式クラウドAPIと同等と過大表現し誤った安心感を与えてしまった」事象・原因・防止策を記録。
- **検証結果**:
  - `browser_subagent` による実機検証にて、WebUI 設定画面上で客観的かつ納得感のある注意書きと手順が表示されることを確認。

## 2026-10-18 21:34 - WebUI および Manual.md への GCP / Azure API キー取得手順の折りたたみヘルプ追加
- **背景と目的**:
  - 外部音声エンジンとして Google Cloud TTS や Azure Speech Service を初めて導入するユーザーが、迷わずスムーズに API Key や Speech Key・リージョンを取得・設定できるよう、画面内および仕様書にガイドを追加。
  - 画面を煩雑にせず必要な時だけ閲覧できるよう、HTML の `<details>` タグを用いたアコーディオン形式（折りたたみUI）で配置。
- **実施内容**:
  1. **Web GUI 実装 (`public/index.html`)**:
     - Google Cloud TTS 設定カード内に「💡 Google Cloud API Key の取得方法・無料枠について」の折りたたみガイドを配置（コンソールログイン、Text-to-Speech API 有効化、API キー生成、推奨される API制限、月間 100万字/400万字の無料枠解説）。
     - Azure Speech Service 設定カード内に「💡 Azure Speech Key・リージョンの取得方法・無料枠について」の折りたたみガイドを配置（ポータルサインイン、音声サービスリソース作成、F0 無料プラン選択、東日本/japaneast 推奨、キーとエンドポイントの取得手順、月間 50万字の無料枠解説）。
  2. **技術仕様書更新 (`Manual.md`)**:
     - 第4章に「4.5.5 クラウド音声エンジン（GCP / Azure）のキー取得手順」を新設し、Markdown の `<details>` 折りたたみ形式で同一の取得ステップと無料枠の仕様を完全網羅。
- **検証結果**:
  - `browser_subagent` による実機ブラウザ操作にて、両方の折りたたみガイドが初期状態でスマートに収まり、クリックによってスムーズに開閉展開できることをスクリーンショット（エビデンス画像）にて確認。

## 2026-10-18 21:28 - 外部音声エンジン（TTS）自由追加アーキテクチャの実装・実機疎通検証・最速並行生成・UI連動
- **背景と目的**:
  - 音声・アナウンス機能において、標準提供の Edge TTS（高品質日本語7話者）に加えて、VOICEVOX、SHAREVOX、COEIROINK、Google Cloud TTS、Azure Speech などの外部音声エンジンをユーザー環境に合わせて自由に追加・利用できるプラグイン構造を導入。
  - 「無くても当然動く（無駄な依存を持たず自律稼働する）」「有ったら声のバリエーションが広がる」という設計思想に基づき、タイムアウト（デフォルト5秒）制御と Edge TTS（七海）への安全な自動フォールバックを徹底。
  - また、VOICEVOX 系のモデル読み込み負荷（コールドスタート遅延）を軽減するためのバックグラウンド事前初期化（プリロード）、クラウド無料枠（GCP / Azure）の月次自動集計と可視化、そして緊急速報（`urgent: true`）発令時に有効な全エンジンから最も早く生成を完了した音声を即時採用する「最速並行生成（Fastest Wins）」機構を実装。
- **実施内容**:
  1. **TTS プロバイダー基盤の新設 (`app/services/tts/`)**:
     - `BaseTtsProvider`: 抽象基底クラスを定義し、各エンジンの接続確認（`is_available`）、話者一覧取得（`get_voices`）、音声合成（`synthesize`）、事前初期化（`initialize_speaker`）の共通インターフェースを策定。
     - `VoicevoxProvider` / `SharevoxProvider` / `CoeiroinkProvider`: ローカル系 TTS エンジン対応。VOICEVOX / SHAREVOX の 2 段階クエリ（audio_query → synthesis）および COEIROINK v2 API（`/v1/predict` ダイレクト合成）に対応。また、SHAREVOX 等の常時初期化済み環境における 500 エラーを避けるため、事前に `is_initialized_speaker` を確認する安全設計を採用。FFmpeg を用いた WAV から MP3（128kbps）への高速ストリーム変換を内包。
     - `GcpTtsProvider` / `AzureTtsProvider`: クラウド系 TTS エンジン対応。API キー、リージョン指定、SSML / Neural 音声に対応。
     - `UsageTracker`: クラウド無料枠管理マネージャー。GCP（Neural2 100万字/Standard 400万字）および Azure（50万字）の月次消費文字数を自動記録し、`data/tts_usage.json` に永続化。月替わり時の自動リセット機構を実装。
  2. **統合 TTS サービス (`app/services/tts_service.py`) の機能強化**:
     - `voice_id` プレフィックス（`voicevox:2`, `sharevox:21`, `coeiroink:140`, `gcp:...`, `azure:...`）による動的プロバイダー解決。
     - タイムアウト（デフォルト5秒）監視および通信障害時の Edge TTS（七海）自動フォールバック。
     - 緊急速報（`urgent: true`）時の複数エンジン並行最速生成（`asyncio.wait(FIRST_COMPLETED)`）と遅延タスクの即時キャンセル機構。
     - 起動時・設定保存時における推奨デフォルトモデル（四国めたん、らごぱすブラック、アメノちゃん等）のバックグラウンド事前初期化および話者キャッシュ先読み。
  3. **REST API エンドポイントの実装・拡張 (`app/routers/speech.py`)**:
     - `GET /api/tts/voices`: 有効な全プロバイダーの話者を統合返却（合計211話者スタイル）。
     - `GET /api/tts/providers`: 各プロバイダーの稼働状態、設定、当月文字数使用量・無料枠情報を返却。
     - `POST /api/tts/providers/test`: 接続テスト、話者検出、事前初期化検証。
     - `PUT /api/tts/providers/settings`: プロバイダー設定（有効化、URL、APIキー、タイムアウト、最速並行生成フラグ）の保存とエンジンへの動的反映。
  4. **Web GUI 実装 (`public/index.html`, `public/app.js`, `public/style.css`)**:
     - 「拡張・システム設定」に「🎙️ 外部音声エンジン (TTS)」カードを新設。
     - 緊急速報最速並行生成トグル、各エンジンカード、無料枠プログレスバー、ワンクリック接続テストボタン。
     - 即時発話画面の話者セレクトボックス（`#sayVoiceSelect`）を `<optgroup>` でプロバイダー別に整理し、211話者を美しく分類表示。
  5. **実機 3 エンジンおよびフォールバックの動作検証**:
     - 実機環境（VOICEVOX: `192.168.11.200:50021`、SHAREVOX: `192.168.11.207:50025`、COEIROINK: `192.168.11.245:50031`）での接続テスト、話者検出、事前初期化、音声合成（WAV→MP3）の全項目正常稼働を確認。
     - 緊急速報時の最速並行生成（4エンジン並行生成から最速完了音声を即時採用、他タスク自動キャンセル）の正常動作を確認。
     - 外部エンジン停止・遅延時の Edge TTS（七海）自動フォールバックが機能することを確認。
     - 実機ブラウザによる UI 描画・操作検証（スクリーンショット確認）。
  6. **技術仕様書の更新 (`Manual.md`)**:
     - 第4章に 4.5 節「外部音声エンジン自由追加アーキテクチャ」を追記し、第13章（TTS API群）、第14章（ファイル構成）、第15章（モジュール仕様）を完全網羅。
- **検証結果**:
  - 全エンジン（Edge TTS, VOICEVOX, SHAREVOX, COEIROINK）において `fallback: False` でネイティブ音声合成に完全成功。
  - 緊急速報指定時の最速並行生成および外部エンジン停止時の Edge TTS 安全フォールバックを確認。

## 2026-10-18 20:17 - Git ブランチの `main` 一本化および旧 `master` の完全削除
- **背景と課題**:
  - `master` と `main` の 2 本が並行して存在し、最新の開発作業がローカルの `master` で行われていた一方、`main` は 19 コミット前の古い状態（Python移行前）で止まっていた。
  - Portainer の Stack 設定やドキュメントが `main` を指定していたため、Portainer 経由でビルド・再デプロイした際に古いコードが実行されるリスクと、二重管理による運用の混乱があった。
- **実施内容**:
  1. **`main` の Fast-forward マージとプッシュ**:
     - `master` の最新コミット（Python 3.14 移行、FastAPI、Homebridge プラグイン、MCP サーバー、マルチ MQTT、ドキュメント刷新等 19 コミット）を `main` へ完全に追いつかせ、GitHub の `origin/main` へプッシュ完了。
  2. **GitHub デフォルトブランチの確認**:
     - GitHub CLI（`gh repo view`）にて、リポジトリの Default branch が元々 `main` であったことを確認。
  3. **旧 `master` ブランチの削除**:
     - リモートブランチ `origin/master` を削除（`git push origin --delete master`）。
     - ローカルブランチ `master` を削除（`git branch -d master`）。
  4. **作業環境の `main` への一本化**:
     - リモート HEAD を `origin/main` に設定（`git remote set-head origin main`）。
     - ローカルのデフォルト作業ブランチを `main` に一本化。
- **検証結果**:
  - `git branch -a` で `main` のみが最新コミット `1cfed9e` として追従していることを確認。
  - これにより、Portainer が `main` を参照して常に最新版をビルド・起動できる環境が整い、二重管理が解消。

## 2026-10-18 20:07 - ドキュメント全面刷新（README.md・Manual.md・Plugin解説書の最新化と上品・謙遜な表現への統一）
- **背景と課題**:
  - `README.md` に内部プロトコル（SOAP、Profile T、Atnr手動トークン取得等）や長大なパラメータ表が混在し、前提知識のない初見ユーザーにとって敷居が高くなっていた。
  - `Manual.md` の第11章が「リファクタリング計画（未実装）」のまま残っており、実装完了済みの Python 3.14 + FastAPI フル非同期アーキテクチャ、Homebridge 専用プラグイン、MCP サーバー、マルチ MQTT / HA Discovery、縦型サイドメニューUI 等の最新仕様が網羅されていなかった。
  - ドキュメント全体のトーン＆マナーとして「過大には記載せず、慎みをもって上品な記載にすること。言い過ぎない。謙遜した描写でちょうどいいかも」という方針の徹底。
- **改訂内容**:
  1. **`README.md` の刷新 (入門・概要編)**:
     - 前提知識のないユーザー向けに構成を再編。細かい技術詳細・プロトコル内部仕様・パラメータ一覧はすべて [Manual.md](Manual.md) へ誘導。
     - 誇大な煽り文句を完全に排し、個人用途から始まったツールの背景に配慮した、控えめで上品・丁寧な文体に統一。
     - 「何ができるか」「Docker Compose での簡単な始め方」「Web画面・Webhook・Siri（Homebridgeプラグイン）での基本的な使い方」にフォーカス。
  2. **`Manual.md` の全面更新 (総合技術仕様書)**:
     - 不具合情報やセキュリティリスク（ユーザー固有の実ドメイン・実トークン等）を除く、すべての技術仕様を完全網羅。
     - 旧第11章の「未実装計画」を撤廃し、現行の「Python 3.14 + FastAPI システム内部アーキテクチャ詳細」としてモジュール仕様（`app/core/`, `app/services/`, `app/routers/`）を正式化。
     - 以下の最新機能を網羅した独立章を体系的に新設・拡充：
       - **各種スピーカー接続仕様**: Google Cast, Alexa (Atnr手動取得手順をREADMEから移管), HomePod (pyatv / mDNSネットワーク要件), ONVIF Profile T (go2rtc / PCMU), DLNA MediaRenderer (SSDP / SOAP)。
       - **Homebridge 公式準拠プラグイン (`homebridge-voicehub`)**: ゼロ依存 DynamicPlatformPlugin、DNDスイッチ、プリセット発話スイッチ、各部屋音量スライダー、`config.json` スキーマ。
       - **MCP (Model Context Protocol) サーバー**: FastAPI ネイティブ SSE (`/mcp/sse`, `/mcp/messages`)、JSON-RPC 2.0、提供5大ツール、Claude Desktop / Cursor / Cline 設定例。
       - **マルチ MQTT ブローカー ＆ HA Discovery**: 複数ブローカー同時接続、トピック設計、Home Assistant 自動エンティティ生成仕様。
       - **Web GUI 仕様**: macOS 風 2カラム縦型設定ナビゲーション、発言履歴、Webhook コマンドビルダー、プラグイン解説書モーダル。
       - **AI 連携仕様**: Gemini / OpenAI のモデル自動ディスカバリー・自動正規化、503/429耐性フォールバック。
       - **完全 REST API リファレンス**: 全エンドポイントのメソッド・URL・JSON仕様。
  3. **プラグイン解説書 (`plugins/homebridge-voicehub/README.md`, `public/...`) のトーン調整**:
     - 「爆速」等の過大な語彙を「迅速に」等の上品・控えめな表現に是正し、WebUI モーダル配信ファイルとも完全同期。
- **検証結果**:
  - 全リポジトリ検索により、ユーザー固有の実ドメインや実トークン等の秘密情報の漏洩がゼロであることを厳格検証。
  - 初心者向けの平易さと、開発者・パワーユーザー向けの完全網羅性が両立されていることを確認。

## 2026-10-18 19:58 - プラグイン解説書の404 Not Found解消と専用ガイドモーダルUIの実装
- **背景と課題**:
  - WebUI（HomeKit連携カード）の「📖 プラグイン解説書」リンク（`/plugins/homebridge-voicehub/README.md`）をクリックした際、FastAPI の静的マウント対象（`public/`）外であったため 404 Not Found となっていた。
- **実装内容**:
  1. **静的ファイル配置の是正**:
     - `public/plugins/homebridge-voicehub/README.md` を作成・配置。これにより URL 直接アクセス時も `HTTP 200 OK`（text/markdown）で正常配信されるよう解消。
  2. **リッチな解説書モーダルUIの新設 (`public/index.html`, `public/app.js`)**:
     - ボタンを「📖 プラグイン解説書を見る」（モーダル展開）と「📄 Raw Markdown」（別タブで直接開く）の 2 系統に強化。
     - モーダル `#modalHomebridgeManual` を新設し、プラグイン概要、インストールコマンド（ワンクリックコピー付き）、`config.json` 設定例（ワンクリックコピー付き）、Siri 音声操作・オートメーション活用例を美しいダークグラスモーフィズムデザインで即座に閲覧可能にした。
- **検証結果**:
  - 実機ブラウザで「📖 プラグイン解説書を見る」押下時にモーダルが開き、コピーボタンや設定例が正常動作すること、および Raw Markdown の直リンク（HTTP 200）を検証確認。
- **再発防止記録**:
  - `logs/past-mistake-title.md` および `logs/past-mistake.md` に `[2026-10-18 04]` として記録。

## 2026-10-18 19:42 - 設定サイドバーの幅拡大 (290px)・ヘッダー削除・カテゴリタイトルの視認性強調
- **背景と課題**:
  - サイドバー幅が狭く「設定カテ/ゴリー」「音声・アナウン/ス」「おやすみ・/会議 (DND)」等の文字が不格好に折り返されていた。
  - 「設定カテゴリー」というヘッダー表記を削除してスッキリさせたい、各カテゴリのタイトル（白文字）を強調して階層の視認性を高めたいという要望。
- **実装内容 (`public/index.html`, `public/style.css`)**:
  - **ヘッダー削除**: `<div class="settings-sidebar-header">`（「⚙ 設定カテゴリー」）を削除。
  - **幅の拡大と折り返し防止**: `.settings-layout` のグリッド定義を `grid-template-columns: 290px 1fr` に拡張し、`.settings-nav-item` に `white-space: nowrap` を適用。全メニュー項目が 1 行でゆったり収まるように改善。
  - **カテゴリータイトルの強調**: `.settings-group-title` の文字色を純白（`#ffffff`、テキストシャドウ付）に引き上げ、下部に洗練されたアンダーライン境界線（`border-bottom: 1px solid rgba(255, 255, 255, 0.12)`）を追加。見出しとしての存在感と視認性を向上。
- **検証結果**:
  - 実機ブラウザでキャッシュバイパスアクセスを行い、折り返し解消・白文字強調・スッキリしたレイアウトをスクリーンショットで確認。

## 2026-10-18 19:28 - 「拡張・システム設定」のmacOS風縦型サイドメニューUI再編（案2）とMCP Tunnelドメイン動的反映
- **背景と課題**:
  - 設定タブ内のサブタブが8個横並びでごちゃごちゃしていたため、「案2: macOS / Home Assistant 風の縦型サイドメニュー（2カラム）UI」として再編。
  - Webhookタブでは実際のTunnelドメイン（`CLOUDFLARE_TUNNEL_DOMAIN`）が表示されている一方、MCPタブでは `your-tunnel-domain` が表示されていた不整合の解消。
  - ユーザー固有のドメインがコードベースにハードコードされていないかの安全性検証。
- **実装内容**:
  1. **縦型サイドメニューUIの導入 (`public/index.html`, `public/style.css`)**:
     - `tab-settings` を「左側サイドバー（`.settings-sidebar`）」＋「右側コンテンツ（`.settings-content`）」のグラスモーフィズム2カラムレイアウトに再設計。
     - 8個のサブタブを3つの論理カテゴリーにグループ化：
       - 🔊 **音声・アナウンス**: 音声・機能拡張、おやすみ・会議 (DND)、緊急速報・防災・天気
       - 🔗 **スマートホーム連携**: AI / Alexa / HomePod、ONVIF / DLNA、MQTT ブローカー連携
       - 🌐 **API・インフラ**: Webhook & Tunnel、MCP ツール連携
     - 画面幅992px以下での1カラムレスポンシブフォールバック対応。
  2. **MCPスニペットへのTunnelドメイン動的注入 (`public/app.js`)**:
     - `updateMcpConfigSnippets()` を改修し、サーバーの `/api/status` から返される `state.serverStatus?.tunnelDomain` を動的に反映。
     - コードやコミット対象ファイルにはドメインを一切ハードコードせず（`.my.env` からのみ読み込み）、画面上ではコピペで即座に Claude Desktop / Cursor / Cline に貼り付け可能なURLを動的生成。
  3. **ハードコード検証**:
     - 全リポジトリ検索により、固有ドメインのコードへのハードコードがゼロであることを確認。
- **検証結果**:
  - 実機ブラウザ検証（`http://192.168.11.244:8080/`）にて、美しい縦型サイドバーの描画、サブタブのスムーズな切り替え、および各設定機能の正常動作を確認。

## 2026-10-18 13:58 - Homebridge プラグインのホスト URL デフォルト値を汎用化 (`1.0.1`)
- **事象と修正**:
  - `config.schema.json` や `README.md` にユーザー環境固有の IP アドレス（`192.168.11.244`）がデフォルト値やプレースホルダーとして残っていたため、一般配布向けに汎用的な値へ修正。
  - `config.schema.json`: `"default": "http://127.0.0.1:8080"`, `"placeholder": "例: http://127.0.0.1:8080 または http://192.168.1.100:8080"` に更新。
  - `README.md`, `public/index.html`: 初期ホスト表示を `http://127.0.0.1:8080` に更新。
  - `package.json`, `CHANGELOG.md`: バージョンを `1.0.1` にインクリメントし、再ビルド完了。


## 2026-10-18 13:42 - Homebridge 専用プラグイン (`homebridge-voicehub`) 実装完了・公開パッケージ化
- **背景と目的**:
  - Homebridge 環境において、VoiceHub のスピーカー（Google Cast, Echo, HomePod, ONVIF/DLNA）や DND（会議・おやすみモード）を Apple HomeKit に自動検出・マッピングし、Siri やシーン・オートメーションから簡単に発話・制御できる専用プラグインを構築。
- **実装内容 (`plugins/homebridge-voicehub/`)**:
  - **DynamicPlatformPlugin 構造 (`src/platform.ts`, `src/index.ts`, `src/settings.ts`)**:
    - Homebridge 起動時 (`didFinishLaunching`) に VoiceHub の `/api/devices` を呼び出し、登録スピーカー一覧を自動検出・HomeKit アクセサリとして動的登録。不要になった古いアクセサリの自動削除クリーンアップ機能を完備。
  - **DND 切替スイッチ (`src/accessories/dnd-switch.ts`)**:
    - HomeKit の `Service.Switch` として動作し、ON でミュート開始、OFF で保留通知の Gemini AI 要約発話をトリガー。外部変更の定期ポーリング同期に対応。
    - VoiceHub バックエンド側にも `POST /api/dnd/toggle` を新設し、1 コールでのトグル切り替えを可能に改善。
  - **プリセット発話プッシュスイッチ (`src/accessories/preset-switch.ts`)**:
    - 「ご飯できたよ」「お風呂が沸いたよ」等の定型アナウンスをステートレススイッチ（押下後 1 秒で自動 OFF）として実装。Siri からの一言音声操作に対応。
  - **個別スピーカー音量制御 (`src/accessories/speaker.ts`)**:
    - HomeKit タイルでスライダー操作できるよう、明度スライダー（`Service.Lightbulb`）または標準 `Service.Speaker` を選択可能に設計。
  - **ゼロ依存 API クライアント (`src/voicehub-client.ts`)**:
    - Node.js 18+ ネイティブ Fetch を使用し、外部ランタイム依存ゼロ（Zero Dependencies）で高速・安全に動作。
  - **Verified プラグイン仕様準拠と公開準備**:
    - `config.schema.json`: Homebridge Config UI X によるグラフィカルな設定画面。
    - `package.json`, `tsconfig.json`: TypeScript 5.7+、ES2022、CommonJS 出力。Node.js & Bun 両対応。
    - `README.md`, `CHANGELOG.md`, `LICENSE` (Apache-2.0), `.npmignore`。
    - `npm pack --dry-run` にてわずか 15.9 kB の超軽量公開パッケージであることを検証確認。
- **検証結果**:
  - TypeScript コンパイル（`npm run build`）でエラーゼロ。
  - VoiceHub 実機 API との疎通テスト（66台のスピーカー検出、DNDステータス取得、テスト発話）に成功。


## 2026-10-18 13:35 - Geminiモデルラインナップの最新化（廃止済み1.5/2.0系の完全除去と現行2.5/3.5/3.8系の適正化）
- **事象と調査結果**:
  - ユーザーからの「Gemini 1.5ってもうないよね？」というご指摘に基づき、Google AI Studio API (`v1beta/models`) のアクティブモデル一覧を直接照合。
  - **事実確認**:
    - `gemini-1.5-flash` および `gemini-1.5-pro` は提供終了（HTTP 404 Not Found）しており、APIリストから消滅していた。
    - 一方、直前のテストで一時エラーになっていた `gemini-3.8-flash` や `gemini-3.5-flash`、`gemini-2.5-flash-lite` は実在する現行モデルであった（直前の失敗は Google 側サーバーの高負荷一時エラー HTTP 503 によるもの）。
- **実装内容**:
  - **モデル定義の刷新 (`app/routers/ai.py`, `public/index.html`)**:
    - 廃止された `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash` を完全に除去。
    - 現行モデル（`gemini-2.5-flash` [推奨・デフォルト], `gemini-2.5-pro`, `gemini-2.5-flash-lite`, `gemini-3.5-flash`, `gemini-3.8-flash`）に更新。
  - **自己修復・フォールバックの適正化 (`app/services/settings_service.py`, `app/services/ai_service.py`, `public/app.js`)**:
    - 廃止済みモデル（1.5系、2.0系等）が設定ファイルやローカルストレージに残存している場合、自動的に `gemini-2.5-flash` へ自己修復・永続化するマイグレーションロジックに修正。
    - 3.8系や3.5系など現行モデルを正当に受け入れつつ、Google サーバー側の高負荷（HTTP 503）や一時障害時にも主力推奨モデル `gemini-2.5-flash` へ自動リトライフェイルオーバーする堅牢性を維持。
- **検証とエビデンス**:
  - `POST /api/ai/summarize-test` にて正常に日本語要約文が生成されることを確認。
  - ヘッドレスブラウザによる WebUI 実機確認を実施。ドロップダウンの選択肢が最新ラインナップに刷新され、要約テスト試聴および音声プレビューが正常完了することを確認（`gemini_model_settings_1792297912065.png`）。


## 2026-10-18 13:25 - AI連携「要約テスト失敗: 要約の生成に失敗しました」の解消とモデル自動正規化・堅牢化
- **事象と原因**:
  - WebUI の「拡張・システム設定」→「🤖 AI 連携」タブで「📢 要約テスト試聴」を実行すると「❌ 要約テスト失敗: 要約の生成に失敗しました」が発生。
  - **原因1 (非実在モデル)**: HTML テンプレートのセレクト初期値に非実在のモデル名（`gemini-3.8-flash` 等）が記述されており、設定ファイルにもこれが保存されていたため Google AI Studio API から 404 Not Found が返却されていた。
  - **原因2 (API レスポンス構造の不一致)**: `GET /api/ai/models` が返却する辞書構造（`{"gemini": [...], "openai": [...]}`）と、フロントエンド `loadAiModels` が期待するプロパティ（`data.models`）が乖離していたため、動的な最新モデル取得が行われず架空モデルが残存した。
  - **原因3 (エラー握りつぶしと空文字判定)**: `_call_gemini` が 404 等の失敗時にログを出力せず空文字 `""` を返却し、上位の `summarize_dnd_messages` も空文字を返却したため、フロント側で `!data.summary` と評価されて「要約の生成に失敗しました」という汎用エラーがスローされていた。
- **実装内容**:
  - **設定の自動自己修復 (`app/services/settings_service.py`)**:
    - `_normalize_ai()` を新設。設定読み込み時に `geminiModel` を検査し、非実在・古いモデル（`3.8`, `3.5`, `argon` 等）が保存されていた場合は自動的に最新推奨の `gemini-2.5-flash` へ修復して永続化。
  - **AIサービス堅牢化と詳細ログ・自動フォールバック (`app/services/ai_service.py`)**:
    - `get_logger("AI")` による HTTP ステータスやレスポンス本文の詳細警告ロギングを実装。
    - モデル名検査および 404 発生時に自動的に安定版 `gemini-2.5-flash` へ切り替えて再試行するリトライフォールバック機構を導入。
    - 万一 AI API が空文字を返却した場合でも、テスト保留メッセージを自然に連結した文章を返却する安全ネットを整備。
  - **API ルーターの互換性向上 (`app/routers/ai.py`)**:
    - `GET /api/ai/models` で `models: [{"id": "gemini-2.5-flash", "name": "..."}, ...]` 形式と旧形式（`gemini: [...]`）の両方を返却するハイブリッド仕様に拡張。
    - `POST /api/ai/summarize-test` の空文字返却を防止。
  - **WebUI 修正 (`public/index.html`, `public/app.js`)**:
    - セレクトボックスの選択肢を実在する Gemini モデル（`gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`, `gemini-1.5-flash`, `gemini-1.5-pro`）に更新。
    - `loadAiModels` で `data.models` / `data[provider]` のどちらの形式でも安全にパースして無効モデルを自動選択解除する処理を追加。
- **検証とエビデンス**:
  - `POST /api/ai/summarize-test` にて Gemini API から実際の要約（「要点です。10時半に宅配便が届き、リビングで動体を検知しました。また、お風呂が沸いています。」）が正常返却されることを確認。
  - ヘッドレスブラウザによる WebUI 実機確認を実施。「📢 要約テスト試聴」ボタン押下により正常に要約テキストが描画され、プレビュー音声再生が実行されることをスクリーンショット（`ai_summary_test_success_1792297285500.png`）で確認。

- **要件**:
  - Voice Hub の MQTT ブローカー接続設定を、単一接続から「複数ブローカーを同時登録・並行接続できるマルチブローカー構成」に拡張する。
- **データ構造拡張と自動正規化・下位互換性 (`app/services/settings_service.py`)**:
  - `DEFAULT_SETTINGS["mqtt"]["brokers"] = []` を追加。
  - `_normalize_mqtt()` メソッドを新設し、従来の単一 `broker` 設定を自動的に `brokers[0]` にマイグレーションしつつ、単一ブローカー設定フィールド（`broker`, `port`, `username`, `clientId`, `baseTopic` 等）と双方向同期して完全な後方互換性を維持。
  - マスター有効化スイッチ（`enabled`）の独立管理に対応。
- **マルチワーカー MQTT サービス実装 (`app/services/mqtt_service.py`)**:
  - `MQTTBrokerWorker` クラスを新設。各ブローカーごとに独立した非同期接続ループ（LWT, 自動再接続, トピック購読, メッセージ解析, 個別 HA Discovery）を完全分離実行。
  - `MQTTService` オーケストレーター化。`workers: Dict[str, MQTTBrokerWorker]` で管理し、マルチキャスト発行（`publish_event`, `publish_dnd_state`）、ブローカー個別/一括 HA Discovery（`publish_ha_discovery`）、ブローカー別/全ブローカーテスト送信（`test_publish`）を実装。
  - 1台のブローカーが切断・障害になっても他のブローカーの送受信に一切影響を与えない堅牢なフォールトトレランスを実現。
- **API ルーター拡張 (`app/routers/mqtt.py`)**:
  - `POST /api/mqtt/test` および `POST /api/mqtt/ha-discovery` に `brokerId` 引数を追加し、ブローカー単位の個別操作・一括操作に対応。
  - `GET /api/mqtt/status` で各ブローカーの詳細ステータス（接続状態、受信数、最終受信時刻、エラー）を配列で返却。
- **WebUI マルチブローカー管理画面の実装 (`public/index.html`, `public/app.js`, `public/style.css`)**:
  - グラスモーフィズム調のブローカーカードアコーディオンコンポーネントを実装。
  - ブローカーごとの表示名、ホスト、ポート、認証、ベーストピック、スピーカー、TLS、個別 HA Discovery（再送・解除）のインライン設定。
  - ステータスバッジ（🟢 接続中 / 🔴 切断 / ⚪ 無効）、個別有効トグル、削除ボタン、新規追加ボタンを配置。
  - テスト送信カードに「送信先ブローカー」選択セレクトボックスを追加（個別指定 / 全ブローカー一括配信）。
  - `escapeHtml` に文字列キャストガードを追加し、数値パラメータ渡しの TypeError（`str.replace is not a function`）を恒久防止。
- **検証とエビデンス**:
  - 複数ブローカー（Home Assistant `192.168.11.248:1883` + Node-RED `192.168.11.248:1883`）の同時接続・個別トピック購読・一斉テスト送信・実機スマートスピーカー（部屋）からの正常発話を確認。
  - ヘッドレスブラウザによるスクリーンショット実機確認で美しいUIレンダリングと正常動作を確認。
  - MCP `speak` ツール経由でスマートスピーカーから作業完了を音声通知。

## 2026-10-18 12:02 - 旧Node環境ファイル完全クリーンアップ・リポジトリ最適化・MCP音声通知検証完了
- **旧Node系ファイル・バックアップの一括クリーンアップ**:
  - `src/` ディレクトリ配下（15ファイル、計276KB）の削除
  - `node_modules/` ディレクトリ（約33MB）の完全削除
  - `package.json`, `package-lock.json` の削除
  - 移行初期バックアップファイル（`Dockerfile.node.bak`, `docker-compose.node.bak`, `boot.bash.bak`, `docker-compose.yml.bak`, `local.my.env.bak`, `local-changes.patch`）の削除
- **設定ファイル・ドキュメントの最適化**:
  - `.dockerignore`: Python バイトコード（`__pycache__`, `*.pyc`）、仮想環境（`venv/`）、テストキャッシュ（`.pytest_cache/`）、`scratch/`、`.agents/` を除外し、ビルドコンテキストを最小化。
  - `.gitignore`: Python 向けキャッシュ（mypy, ruff 等）を整理し、純粋な Python プロジェクトとして最適化。
  - `Manual.md`, `README.md`: ディレクトリツリー（`src/` -> `app/`）および起動手順（npm -> pip/uvicorn、Python 3.14）を最新アーキテクチャに適合。
- **Docker Compose クリーンリビルド & 動作検証**:
  - ビルドコンテキスト転送がわずか 0.6 秒に高速化。コンテナ起動および全バックグラウンドワーカー（go2rtc, DND, カレンダー, 防災, MQTT, MCP）が正常動作することを確認。
- **MCP ツール経由でのデフォルトスピーカー音声通知**:
  - MCP `speak` ツールを介して、ユーザーへの作業完了通知（「旧環境のNodeファイルの完全削除とリポジトリの最適化が完了しました。システムはすべて正常に稼働しています。」）をデフォルトスピーカー（部屋）から正常発話。
- **問題の原因特定**:
  - Antigravity / Gemini CLI や最新の MCP クライアントが、SSE トランスポート設定（`url: "http://192.168.11.244:8080/mcp/sse"`）に対して直接 HTTP POST（Streamable HTTP トランスポート形式）で `initialize` JSON-RPC リクエストを送信していた。
  - Voice Hub の `/mcp/sse` エンドポイントが従来 `GET`（SSE ストリーム受信）のみを受け付けていたため、FastAPI が `405 Method Not Allowed` を返し、クライアント側で `Error: calling "initialize": sending "initialize": Method Not Allowed.` が発生していた。
- **Streamable HTTP & SSE ハイブリッドアーキテクチャの完全実装 (`app/routers/mcp.py`)**:
  - `POST /mcp/sse`, `POST /mcp`, `POST /mcp/messages`: すべてで JSON-RPC 2.0 リクエストを直接 HTTP レスポンス（HTTP 200 OK + `application/json`）として即時返却できるよう共通ハンドラ `handle_jsonrpc_post` を新設。
  - セッション自動解決: クエリパラメータ `sessionId` だけでなく、リクエストヘッダー `Mcp-Session-Id` / `x-session-id` からのセッション特定、未指定時のステートレス/自動新規セッション作成をサポート。
  - レスポンスヘッダーに `Mcp-Session-Id` および `Access-Control-Expose-Headers: Mcp-Session-Id` を付与し、MCP 仕様準拠のセッション管理を実現。
  - バッチリクエスト（JSON-RPC 2.0 list）および通知（idなし Notification への 202 Accepted）のサポート。
  - `GET /mcp`: `Accept: text/event-stream` の場合は SSE ストリーム、それ以外はステータス JSON を返却。
  - `DELETE /mcp/sse`, `DELETE /mcp`, `DELETE /mcp/messages`: セッション破棄（204 No Content）に対応。
- **MCP 互換性メソッド拡張 (`app/services/mcp_service.py`)**:
  - `resources/list`, `resources/templates/list`, `prompts/list`, `logging/setLevel` を追加し、クライアントからの周辺機能呼び出し時の未定義エラーを防止。
  - `initialize` 時にクライアントの `protocolVersion` を尊重して柔軟に応答。
- **宅内LAN認証と Cloudflare Tunnel の自動最適化 (`app/services/mcp_service.py`, `app/core/security.py`)**:
  - `verify_auth`: 宅内プライベートIP（192.168.x.x, 127.0.0.1 等）からのアクセス時はトークン未指定でも接続を自動許可。外部（Cloudflare Tunnel 等）経由時は Webhook トークンの一致を厳格に要求。
  - `check_tunnel_access`: Cloudflare Tunnel 経由でも `/mcp*` へのアクセスを許可（トークン認証は MCP ルーターで担保）。
- **検証と動作確認**:
  - `curl` での `POST /mcp/sse`（`initialize`, `tools/list`）、`POST /mcp`（`ping`）、`POST /mcp/messages`、`GET /mcp/sse` の正常動作を確認。
  - Antigravity クライアント（`192.168.11.244`）からの自動再接続で `POST /mcp/sse -> HTTP 200 OK` が記録され、MCP 初期化が完全に成功。
- **Home Assistant MQTT Auto-Discovery 規格のネイティブサポート (`app/services/mqtt_service.py`, `app/routers/mqtt.py`)**:
  - Voice Hub 自身が Home Assistant の MQTT Discovery 規格（トピック `{discovery_prefix}/...`）に準拠した構成トピックを自動生成・パブリッシュ（`retain=True`）する機構を開発。
  - Home Assistant 側で YAML 編集やアドオン/カスタム統合のインストールを一切行うことなく、同一ブローカーに接続するだけで「**SmartSpeaker Voice Hub**」デバイスが自動生成されるゼロコンフィグ体験を実現。
  - 自動生成される 6 つのエンティティ:
    1. `notify.voicehub_say`: HA のオートメーションやスクリプトから利用できる音声通知サービス。
    2. `switch.voicehub_dnd`: おやすみ・会議モード (DND) の即時切替スイッチ（`voicehub/dnd/set` 購読、`voicehub/dnd/state` パブリッシュ）。
    3. `sensor.voicehub_last_say`: 直前に読み上げられたメッセージ内容を記録するセンサー。
    4. `binary_sensor.voicehub_status`: Voice Hub サーバーの接続死活監視（LWT: Last Will & Testament により、不意の切断時にも自動で `offline` を通知）。
    5. `button.voicehub_test_speak`: HA ダッシュボードからワンタップで発話テストを実行するボタン。
    6. `button.voicehub_flush_queue`: DND 保留メッセージを強制消化するボタン。
- **Voice Hub - Home Assistant 間の双方向 DND 連動 (`app/routers/dnd.py`)**:
  - WebUI 上での手動ミュート、クイックDND、解除操作が行われた際にも `mqtt_service.publish_dnd_state()` を即時トリガー。HA 側のスイッチ表示がリアルタイムに双方向同期。
- **MQTT REST API の拡充 (`app/routers/mqtt.py`)**:
  - `POST /api/mqtt/ha-discovery`: Discovery トピックの強制再送信および HA からの登録解除（`clear: true`）API を新設。
- **WebGUI「拡張・システム設定」への HA Discovery コントロール＆エンティティガイド新設 (`public/index.html`, `public/app.js`)**:
  - 「🏠 Home Assistant 自動検出 (MQTT Discovery)」トグルスイッチおよび Discovery プレフィックス設定（デフォルト: `homeassistant`）。
  - 「🔄 Discovery トピック再送信」および「🗑️ HA から解除」ボタンを設置。
  - 右カラムに HA 自動生成エンティティの一覧および利用ガイドカードを美しく配置。
- **一時 Mosquitto ブローカーコンテナを用いた実機トピックパブリッシュ＆DND双方向検証**:
  - 一時コンテナ `test-temp-mosquitto` を起動し、実機 MQTT 通信を検証。
  - 全 6 エンティティの Discovery JSON パブリッシュ、LWT 登録、`voicehub/dnd/set`（ON/OFF）による DND 状態の即時同期、発話完了イベントのセンサー反映を完全確認。
  - 検証完了後、一時コンテナを適切に処分。
- **Docker Compose クリーンリビルド & ブラウザ実機検証**:
  - `docker compose build voice-hub && docker compose up -d voice-hub` を実行。ブラウザサブエージェントにより WebGUI 表示崩れのないことを確認完了。

## 2026-10-17 10:20 - MCP（Model Context Protocol）サーバー機能の実装・インターネット安全対応・Antigravityファーストユーザー実機検証完了
- **MCP (Model Context Protocol) サーバー機能の完全実装 (`app/services/mcp_service.py`, `app/routers/mcp.py`)**:
  - Claude Desktop、Cursor、Cline、AIエージェント等から自然言語でスマートスピーカー群を安全・高機能に操作できる標準 MCP サーバー（SSE トランスポート / JSON-RPC 2.0）を新設。
  - 公開ツール群（5種類）の実装:
    1. `speak`: 指定スピーカー（個別スピーカー、グループ、マクロ `ALL`, `GH:ALL`, `AL:ALL`, `HP:ALL`, `DLNA:ALL`）への音声読み上げ、音量・話者・緊急度指定。
    2. `list_speakers`: 自宅内の全スマートスピーカー（Google Cast, Alexa, HomePod, DLNA, ONVIF）一覧、グループ定義、デフォルトスピーカーの取得。
    3. `get_status`: システム稼働状態、現在のおやすみ・会議モード (DND) 判定、Google カレンダー進行中ミーティング情報の取得。
    4. `set_dnd`: 一時的な集中や会議に合わせた DND モードの即時有効化（指定時間タイマー付）・解除、保留通知の自動フラッシュ。
    5. `get_history`: 直近の発話履歴、配信先、ステータス、ソース（MCP含む）の取得。
  - セキュリティとインターネット経由（Cloudflare Tunnel 等）の安全なハンドリング:
    - MCP SSE 接続時およびメッセージ POST 時に Webhook トークン認証（クエリパラメータ `?token=...`、リクエストヘッダー `x-webhook-token`、または `Authorization: Bearer`）を強制。
    - トークン未指定または不正なアクセスは即時 HTTP 401 Unauthorized で弾き、外出先・インターネット経由でも安全に保護。
- **MQTT のインターネット対応強化（MQTTS / TLS/SSL 対応）**:
  - `app/services/mqtt_service.py` において、`use_tls`（ポート8883等）による安全な TLS/SSL 接続（`tls_params`）をサポート。宅内 Mosquitto だけでなく、HiveMQ Cloud、EMQX Cloud、AWS IoT 等のクラウド型 MQTT ブローカーへの暗号化通信に対応。
- **Web GUI「拡張・システム設定」への「🤖 MCP 連携」画面新設 (`public/index.html`, `public/app.js`)**:
  - 設定サブナビゲーションに「🤖 MCP 連携」ボタンを追加。
  - 常時稼働ステータスバッジ（ポート 8080 で常時稼働中、セッション数・総呼出回数表示）。
  - 接続環境切り替えトグル（🏡 宅内 LAN / 🌐 インターネット Cloudflare Tunnel）により、エンドポイントURLとトークンが埋め込まれた設定スニペットをワンクリックで切り替え。
  - Claude Desktop 用（`claude_desktop_config.json`）および Cursor / Cline 用のワンクリックコピーボタン。
  - ブラウザから各ツールの動作確認ができる「MCP ツール実行シミュレーター」を搭載。
- **Antigravity によるファーストユーザー実機検証＆デバッグ**:
  - Antigravity 自身が MCP クライアントとして SSE ストリーム（`/mcp/sse?token=...`）に直接接続。
  - `initialize`（プロトコル合意）、`tools/list`（ツール列挙）、`list_speakers`（57台検出）、`get_status`、`speak`（実機スピーカー発話確認）、`get_history`、`set_dnd` の全シーケンスを完全走破。
  - テスト過程で発見された `SpeechService` / `DndService` のメソッド不整合（`say` vs `speak`, `get_status` vs `get_global_status`）を特定し、エイリアス追加および堅牢化修正を完了。
- **Docker Compose クリーンリビルド & 動作健全性確認**:
  - `docker compose build voice-hub && docker compose up -d voice-hub` を実行し、全機能の正常稼働を確認。

## 2026-10-17 09:48 - MQTT連携機能の完全実装（Node-RED / n8n メッセージ読み上げ対応）
- **Python 3.14 対応非同期 MQTT サービスの新規構築 (`app/services/mqtt_service.py`)**:
  - `aiomqtt>=2.5.0` および `paho-mqtt>=2.1.0` を導入。FastAPI の lifespan ライフサイクルと協調する完全非同期・自動再接続付き MQTT クライアントサービスを開発。
  - トピック購読: `{baseTopic}/say` および `{baseTopic}/say/#`（ワイルドカード）に対応。サブトピック指定（例: `voicehub/say/living`, `voicehub/say/ALL`）によるスピーカー自動ルーティングをサポート。
  - ペイロード柔軟性: JSON 形式（`{ "text": "...", "target": "...", "volume": 0.8, "urgent": false }` 等の柔軟なキーマッピング）およびプレーンテキスト（文字列単体）の双方を自動判別して即時読み上げ。
  - イベント通知機能 (Publish): メッセージ発話完了時に `{baseTopic}/events/say` へ実行結果を自動パブリッシュ。Node-RED や n8n での後続処理トリガーとして活用可能。
  - 発言履歴連携: 送信元クライアント「MQTT (Node-RED/n8n)」としてトピック名やブローカー情報を正確に記録。
- **MQTT REST API ルーターの新設 (`app/routers/mqtt.py`)**:
  - `GET /api/mqtt/status`: 接続状態、ブローカー情報、受信件数、最終受信時刻、エラー状況のリアルタイム取得。
  - `POST /api/mqtt/restart`: 設定保存時や手動での MQTT クライアント再起動・再接続。
  - `POST /api/mqtt/test`: 接続中ブローカー経由でのテストメッセージ送信・読み上げ検証。
- **Web GUI「拡張・システム設定」への「📡 MQTT 連携」ペイン新設 (`public/index.html`, `public/app.js`)**:
  - 設定サブナビゲーションに「📡 MQTT 連携」ボタンを追加。
  - ブローカー接続設定カード（トグルスイッチ、稼働状態インジケーターバッジ、IP/ポート、ユーザー名/パスワード、トピック、クライアントID、デフォルトスピーカー選択、保存ボタン、再接続ボタン）。
  - テスト発話送信カードおよび Node-RED / n8n 連携ガイドカードを美しく配置。
  - デバイス一覧更新時にデフォルトスピーカーおよびテスト送信先の `<select>` 選択肢（個別スピーカー、マクロ、カスタムグループ）を自動同期。
- **Docker Compose クリーンリビルド & 実機ブラウザ検証**:
  - `docker compose build voice-hub` および `docker compose up -d voice-hub` を実行。バックグラウンドデーモンの正常起動と WebGUI の表示・連携動作を確認。

## 2026-10-17 09:15 - DLNA検出・登録機能のONVIF画面統合、自動スキャン＆手動IP登録、WebGUI/スピーカーディスパッチ完全対応
- **ONVIF / DLNA 設定画面およびAPIの完全統合**:
  - 設定画面のサブナビゲーションを「📷 ONVIF」から「📷 ONVIF / 🎵 DLNA」に改修。同一画面から防犯カメラ（Profile T 双方向音声）および DLNA / UPnP MediaRenderer スピーカーの双方を一括自動スキャン・管理可能に。
  - バックエンド API `app/routers/onvif_dlna.py` にて `/api/onvif/scan`, `/api/onvif-dlna/scan`, `/api/dlna/scan` を整備し、返却形式を `{ success: True, devices: [...], total: N }` に統一。
  - フロントエンド `public/app.js` 側でも配列直接返却および辞書返却の双方を安全に吸収するガード（`Array.isArray(data) ? data : (data.devices || [])`）を適用。
- **手動デバイス追加（IP直接登録）機能の新設**:
  - mDNS / SSDP / WS-Discovery が届かないネットワークや固定IP機器向けに「➕ 手動でデバイスを追加 (IP直接登録)」フォームを設置。
  - 種別（🎵 DLNA スピーカー / 📷 ONVIF カメラ）、表示名、IPアドレス、ポート番号を指定して直接 Voice Hub へ登録可能。
  - `/api/dlna/probe` により、指定された IP / ポートの MediaRenderer（AVTransport）の到達性を事前検証可能。
- **連携登録モーダルおよび登録済み一覧テーブルの洗練**:
  - 検出テーブルおよび登録済み一覧に「種別」列（📷 ONVIF / 🎵 DLNA バッジ）を新設。
  - 連携登録モーダルで DLNA デバイス選択時には不要なカメラ個別認証（パスワード入力欄）を非表示化し、スムーズな登録 UX を実現。
  - 登録済みデバイス一覧から DLNA スピーカーの「テスト発話」および「解除（削除）」が可能。
- **スピーカー選択チップおよび音声ディスパッチの連携**:
  - 登録された DLNA スピーカーはスピーカー一覧（`/api/devices`）にシームレスに連携され、即時発言タブのスピーカー選択チップで「🎵 [名前] (DLNA)」として表示・選択（シアン色ハイライト）可能。
  - `app/services/speech_service.py` および `dlna_service.py` により、マクロ `DLNA:ALL` や各DLNAスピーカー宛ての発話をホストLAN IP（`effective_wireless_ip`）経由の音声ストリーミングで完全再生。
- **Docker Compose クリーンリビルド & 健全性検証**:
  - `python:3.14-slim` 環境にて `docker compose build voice-hub` および `docker compose up -d voice-hub` を実行。全デーモン正常起動およびブラウザUI実機検証完了。

- **旧Node版APIパリティの完全補完**:
  - `app/routers/dnd.py` に `GET /api/queue` を実装し、旧Node版の永続化キュー状態確認 API `{ dndQueue: [], webhookQueue: [] }` を返却可能に。
  - `app/routers/settings.py` に `POST /api/settings` を追加し、PUTだけでなくPOSTリクエストによる設定更新にも完全対応。
- **全方式スピーカー実機発声エビデンス確認**:
  - Google Cast 単体（`192.168.11.97`）: 200 OK、発声確認
  - Google Cast ネイティブグループ（`192.168.11.85:32094`）: 200 OK、発声確認
  - Amazon Echo / Alexa（`alexa:廊下Echo Dot`）: 200 OK、発声確認
  - Apple HomePod（`homepod:F4:34:F0:0B:38:E7`）: 200 OK、発声確認
- **Docker Compose 完全リビルド & 健全稼働検証**:
  - `python:3.14-slim` + `go2rtc` 環境でクリーンビルドおよびコンテナ起動を実施。
  - P2PQuake WebSocket、DND監視、Calendarスケジューラ、go2rtc（1984, 8554）全デーモンの正常稼働を確認。
- **デバイス名の日本語表示（IP表示からの脱却）**:
  - `app/routers/status.py` に `defaultDeviceName` フィールドを追加し、設定された `DEFAULT_DEVICE` をもとに「デフォルト: 部屋」等の適切な日本語名を表示。
  - `public/app.js` に多段階解決関数 `getDeviceDisplayName(target)` を新設。IP、host、ID、英字名、IPエイリアス、マクロ名（ALL, GH:ALL, AL:ALL, HP:ALL）を完全解決。
  - Web GUI ヘッダー、定期スケジュール一覧の対象スピーカー列、カスタム部屋グループの所属スピーカー一覧、発言履歴一覧の対象スピーカー列に `getDeviceDisplayName` を適用。
  - `loadDevices()` 完了時にスケジュール表・グループ一覧・履歴・ヘッダーを一括再描画し、非同期取得順序によるIP一時表示レースコンディションを完全解消。
- **発言履歴ログ非表示問題の完全解決**:
  - `app/routers/history.py` で `{ "history": items, "total": len(items) }` の辞書形式を返却するように修復（`public/app.js` 側でも `Array.isArray(data) ? data : (data.history || [])` で互換ガード）。
  - `app/routers/speech.py` に `extract_client_ip`、`detect_user_agent_client`、`resolve_client_metadata` を実装。Webhook/外部API受信時に User-Agent（Discordbot, Slackbot, curl等）や X-Forwarded-For / Cloudflare ヘッダーから送信元クライアント・通信経路を自動抽出し、発言履歴へ連携。
  - ブラウザおよび実機テストにより、Webhook発話が即時履歴に登録・日本語デバイス名とともに表示されることを確認。

## 2026-10-17 03:25 - Python 3.14 アップグレード、天気予報・DNDパリティ、集中ロガー、.gitignore最適化
- **Python 3.14-slim への全面移行と Docker Compose 再構築**:
  - 全依存ライブラリ（FastAPI, Pydantic, edge-tts, pychromecast, pyatv 等）の wheels 互換性を検証し、`Dockerfile` を `python:3.14-slim` にアップグレード。
  - IPv6到達不能環境での接続タイムアウトを解消するため、`/etc/gai.conf` に `precedence ::ffff:0:0/96 100` を適用。
- **プロジェクト全体の集中ロギング設計・エラー握りつぶし撲滅**:
  - `app/core/logger.py` によるタイムスタンプ・モジュール名・レベル付き統一ロガーを全サービス・ルーターへ導入。
  - FastAPI ミドルウェアで HTTP 400/500 系のアクセスおよび未処理例外のスタックトレースを自動出力。
- **天気予報データ取得・防災機能の完全修復**:
  - `app/services/disaster_service.py` を気象庁 API / P2P地震情報 WebSocket / 警報ポーリング / 天気予報パースの完全な Python 実装として再構築。
  - フロントエンドが要求する `{ areaName, weather, tempMax, tempMin, pop, advice, summaryText }` オブジェクトを返却するように修正。
  - `/api/disaster/areas` の市区町村解決、および `/api/disaster/test` の各種テスト発話（eew, quake, warning, weather）を実装。
- **DND（おやすみ・会議モード）の Web GUI パリティ修復**:
  - `/api/dnd/status` の返却プロパティに `isActive`, `enabled`, `queuedCount`, `activeCalendarEvent` を追加し、GUI ヘッダーやミュートボタンの状態同期を修正。
  - `release_dnd_queue` での `asyncio` 未定義エラーを解消し、DND終了時のキュー自動消化バックグラウンドループを実装。
- **スピーカー全方式（Google Cast, Alexa, HomePod, DLNA）の再生修復と実機検証**:
  - HomePod: MACアドレス解決を修正し、`speech_service.py` からローカル MP3 ファイルパスを渡して AirPlay ストリーミングを完全成功化。
  - Alexa: 表示デバイス名の装飾（`Alexa (...)`）を正規表現でトリミングし、Amazon コマンドとの一致を確保。
  - Google Cast: ネイティブグループ（`:port`）宛の接続ポート保持を修正。
  - DLNA: SSDP M-SEARCH および SOAP コマンドのエラーログ・統一ロギングを適用。
- **OSS 汎用化 & `.gitignore` 最適化**:
  - 特定環境依存の IP ハードコードを排除し、環境変数または LAN IP 自動検出（`auto_detect_local_ip`）へフォールバック。
  - `.agents/`, `logs/`, `scratch/`, 一時ファイル、ローカル環境ファイルを `.gitignore` に追加・最適化。

## 2026-10-17 03:00 - Google Cast グループポート解決、結果プロパティ完全化、プレビューAPI復元
- Cast Group（`:port`）宛の接続時に動的ポートが 8009 に潰されるバグを修正。
- `/api/say` の返却値に `results: detailed_results`、`success`、`dndSuppressed` を追加し、Web GUI トーストと完全一致。
- 404 になっていた `/api/preview` を実装。

## 2026-10-17 02:30 - Alexa 認証プロキシの 100% Python 化
- `bin/alexa_proxy.js` を撤廃し、`aiohttp.web` による純粋な Python リバースプロキシ `app/services/alexa_proxy_service.py` を実装。
- Dockerfile を純粋な Python 3.12-slim + go2rtc に復元。

## 2026-10-17 02:00 - Google Cast スピーカーの音声不鳴動修正
- 音声配信ホストアドレスが `127.0.0.1` だった不具合をホスト LAN IP (`192.168.11.244`) に修正。
- `pychromecast` 接続時に `cast.start()` を呼ぶように修正。
