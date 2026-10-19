# Smart Home Speaker Voice Hub プロジェクト全体監査レポート

- **監査対象**: `/root/google-home-voicetext-docker` (`Mastercentos` / `192.168.11.244`)
- **監査日時**: 2026-10-19
- **対象範囲**: バックエンド (`app/`)、フロントエンド (`public/`)、補助スクリプト (`bin/`)、Homebridge プラグイン (`plugins/homebridge-voicehub/`)、Docker/インフラ構成 (`Dockerfile`, `docker-compose.yml`, `entrypoint.sh`, `.dockerignore`, `.gitignore`)、永続化データ (`data/`, Docker Volume)、ドキュメント (`README.md`, `Manual.md`)、および実稼働コンテナ (`SmartSpeaker-VoiceHub`) の稼働ログ

---

## エグゼクティブサマリー（総括）

プロジェクト全体のソースコード、設定、インフラ構成、および稼働中のコンテナログを精査した結果、**現在進行形で新規音声の発声を不能にしている致命的なバグ (`NameError`)** や、**Cloudflare Tunnel 経由でインターネットから認証を100%バイパスして自宅スピーカーの操作・情報取得が可能になる重大なセキュリティ脆弱性** をはじめ、複数の不具合・不整合・最適化課題・未実装項目が特定されました。

### 重要度別サマリー

| 重要度 | カテゴリ | 主な検出事項（抜粋） |
| :--- | :--- | :--- |
| **🚨 Critical (最優先)** | **不具合** | `app/services/tts_service.py` に `import time` が欠落しており、**新規テキストの音声合成時に 100% `NameError` でクラッシュしてスピーカーから音が出ない**（実稼働ログでも発生中） |
| **🚨 Critical (最優先)** | **セキュリティ** | `network_mode: "host"` 環境下で `cloudflared` からのリクエスト元 IP が `127.0.0.1` になるため、**Cloudflare Tunnel 経由の外部アクセスで Webhook トークン認証および MCP 認証が完全にバイパスされる** |
| **⚠️ High (高)** | **不具合 / 不整合** | `SettingsManager.update()` の浅い辞書マージ仕様により、**WebUI から「カスタム部屋グループ」と「IPエイリアス」が絶対に削除できない** |
| **⚠️ High (高)** | **不具合 / 不整合** | `app/main.py` のミドルウェア内で `HTTPException(401/403)` を送出すると、未処理例外ハンドラに捕捉されて **すべて HTTP 500 Internal Server Error に化ける** |
| **⚠️ High (高)** | **不具合 / 不整合** | DND（おやすみモード）の `/api/dnd/mute`・`/api/dnd/toggle`・MCP `set_dnd`・HomeKit スイッチで時間省略時に `manualUntil: None` となり **DND が一切 ON にならない** |
| **⚠️ High (高)** | **不具合 / 不整合** | Alexa 個別指定時の名前二重ラップ (`Alexa (Alexa (...))`) による発声失敗、および防災速報（地震情報・気象警報・WebUI接続表示）の複数のロジックバグ |
| **⚠️ High (高)** | **セキュリティ** | `/api/settings`・`/api/devices`・`/api/status`・`/api/tts/providers` が **全 API キー・カメラ管理者パスワード・Webhook トークンを平文返却** しており、CORS `*` や `go2rtc` RTSP (`:8554`) の無認証公開と合わせて情報漏洩リスクがある |
| **⚡ High (高)** | **最適化 / 高速化** | 発声のたびに毎回 `bash alexa_remote_control.sh -a` が起動されるボトルネック、`get_voices()` 毎の全ローカル TTS エンジン再初期化、Alexa 単独発声時の不要な TTS 合成 |
| **📦 High (高)** | **欠落 (あるべきもの)** | 自動テスト・静的解析 (`ruff`/`pytest`) の不在、`Manual.md` に明記されている `sync_engine.py`（音ズレ補正）や `queue_manager.py`（Webhook WAL）や Homebridge スピーカー音量通信の未実装 |

---

## 1. 不具合・不整合（Bugs & Inconsistencies）

### 1.1 【Critical】`tts_service.py` の `import time` 欠落による新規音声合成時の 100% クラッシュ
- **該当箇所**: `app/services/tts_service.py` (L1-15, L531, L574)
- **事象と原因**:
  `synthesize()` の末尾 (L531) で呼び出される `self._cleanup_lru_cache()` の先頭 (L574) にて `now = time.time()` を実行していますが、`app/services/tts_service.py` の先頭に `import time` が存在しません。
- **影響**:
  キャッシュに存在する過去の音声ファイル（キャッシュ HIT 時）は `_cleanup_lru_cache()` を通らないため再生されますが、**キャッシュにない新しい文章を合成（キャッシュ MISS）するたびに、音声ファイル生成直後に `NameError: name 'time' is not defined` で例外終了し、スピーカーへのディスパッチ処理に到達せず発声が完全に失敗します**。
  実際に稼働中のコンテナログ (`/logs/container.log`) においても、直近の定時スケジュール発声が以下の通りクラッシュして不発となっています：
  ```text
  File "/app/app/services/tts_service.py", line 574, in _cleanup_lru_cache
    now = time.time()
  NameError: name 'time' is not defined. Did you forget to import 'time'?
  ```
- **対策**: `app/services/tts_service.py` の先頭に `import time` を追加してください。

---

### 1.2 【High】未インポート・未定義変数 (`NameError`) が潜在する他の3箇所
AST（抽象構文木）による全 Python ファイルの静的解析により、特定のエラーパスに入った瞬間に `NameError` でクラッシュする箇所が他に3箇所確認されました。
1. **`app/main.py` L203 (`serve_voice_file`)**:
   - `raise HTTPException(status_code=404, detail="Voice file not found")` を実行していますが、`app/main.py` の先頭 (`from fastapi import FastAPI, Request`) で `HTTPException` がインポートされていません。存在しない `/voice/xxx.mp3` にアクセスすると 404 ではなく `NameError` (HTTP 500) が発生します。
2. **`app/services/tts/azure_provider.py` L100 (`get_voices`)**:
   - モジュール先頭では `log = get_logger("TTS.Azure")` と定義されているにもかかわらず、L100 の `except Exception as e:` ブロック内で `logger.warning(...)` を呼び出しています。Azure API からの話者一覧取得が失敗した際、フォールバックプリセットへ移行できずに `NameError: name 'logger' is not defined` でクラッシュします。
3. **`app/services/tts/gcp_provider.py` L116 (`get_voices`)**:
   - 上記と同様に `log = get_logger("TTS.GCP")` に対して L116 で `logger.warning(...)` を呼び出しており、GCP API エラー時に `NameError` でクラッシュします。

---

### 1.3 【High】カスタム部屋グループおよび IP エイリアスが削除できないバグ
- **該当箇所**: `app/services/settings_service.py` (L185-191), `public/app.js` (L4363-4374, L4402-4418)
- **事象と原因**:
  WebUI でカスタムグループや IP エイリアスの「削除」ボタンを押すと、`public/app.js` は `delete state.deviceGroups[name]` または `delete state.ipAliases[ip]` を実行した上で、`saveAllSettings()` により `PUT /api/settings` へ残りの辞書データを送信します。
  しかし、バックエンドの `SettingsManager.update()` は以下のように第1階層の辞書を常に既存辞書と浅いマージ (`{**self.settings[k], **v}`) する実装になっています：
  ```python
  for k, v in new_data.items():
      if isinstance(v, dict) and k in self.settings and isinstance(self.settings[k], dict):
          self.settings[k] = {**self.settings[k], **v}
  ```
- **影響**:
  `deviceGroups` や `ipAliases` のキーをフロントエンド側で削除して送信しても、サーバー側で既存の `self.settings["deviceGroups"]` / `self.settings["ipAliases"]` とマージされるため、**削除したはずのグループや IP エイリアスが `settings.json` から絶対に消えず、リロードや次回発声時に復活します**。
- **対策**:
  `k in ("deviceGroups", "ipAliases")` のように辞書全体が置換対象であるキーについては、マージではなく `self.settings[k] = v` で上書き置換するように修正してください。

---

### 1.4 【High】ミドルウェア内の `HTTPException` がすべて HTTP 500 に化けるバグ
- **該当箇所**: `app/main.py` (L97-130)
- **事象と原因**:
  `@app.middleware("http")` (`logging_and_security_middleware`) の冒頭で `check_tunnel_access(request)` および `check_admin_auth(request)` を呼び出しています。
  Starlette / FastAPI の仕様上、`@app.middleware("http")` (`BaseHTTPMiddleware`) の内部で送出された `HTTPException` はルーティング層の `HTTPException` ハンドラでは捕捉されず、外側の `@app.exception_handler(Exception)` (`global_exception_handler`) に捕捉されて無条件に `status_code=500` の `JSONResponse` に変換されます。
- **影響**:
  - Cloudflare Tunnel 経由で管理画面へアクセスした際、本来返るべき `403 Forbidden` ではなく `500 Internal Server Error` が返り、コンテナログに毎回未処理例外の Traceback ERROR が出力されます（実機にて再現確認済み）。
  - `ADMIN_PASSWORD` 設定時に未認証クライアントが API にアクセスした際も `401 Unauthorized` ではなく `500 Internal Server Error` になります。
- **対策**:
  ミドルウェア内で `try ... except HTTPException as exc:` をキャッチして `JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "detail": exc.detail})` を直接 return するように修正してください。

---

### 1.5 【High】DND（おやすみ・会議モード）のミュート・トグル・HomeKit・MCP 連携が機能しないバグ
- **該当箇所**:
  - `app/routers/dnd.py` (L27-44 `mute_dnd`, L58-63 `toggle_dnd`)
  - `app/services/mcp_service.py` (L313-325 `set_dnd`)
  - `plugins/homebridge-voicehub/src/accessories/dnd-switch.ts` (L35) & `voicehub-client.ts` (L181-195)
- **事象と原因**:
  `POST /api/dnd/mute` において、`req.durationMinutes` と `req.until` がともに指定されない場合、`until_ts` が `None` のまま `"manualUntil": None` として保存されます。
  しかし `dnd_service.evaluate()` (L105-120) では `if manual_until:` が真かつ現在時刻より未来のタイムスタンプである場合のみ DND 有効と判定します。
- **影響**:
  1. `POST /api/dnd/toggle` は内部で引数なしの `await mute_dnd()` を呼ぶため、**DND が OFF の状態で `/api/dnd/toggle` を呼んでも `manualUntil: None` が書き込まれるだけで DND が ON になりません**。
  2. Homebridge プラグインの DND スイッチ (`dnd-switch.ts`) は `client.setDnd(true, 'HomeKit 操作')`（`durationMinutes` 省略）で `/api/dnd/mute` を呼ぶため、**iPhone のホームアプリから DND スイッチを ON にしてもサーバー側で DND が有効にならず、次のポーリングで勝手に OFF に戻ります**。
  3. MCP の `set_dnd` ツールでも `durationMinutes` を省略すると `until_ts = None` となり、**AI アシスタントから「おやすみモードを ON にして」と指示しても有効になりません**。
- **対策**:
  `quick_dnd` や `mqtt_service.py` と同様に、`durationMinutes` および `until` が未指定の場合は `until_ts = now_ts + (365 * 24 * 3600)`（実質無期限）を設定するように統一してください。

---

### 1.6 【High】DND の対象デバイス絞り込み (`targetScope`) 無視と DND 抑制履歴の不記録
- **該当箇所**: `app/services/speech_service.py` (L88-145), `app/services/dnd_service.py` (L49-65)
- **事象と原因**:
  1. `dnd_service.py` には DND 抑制履歴を記録する `record_history()` と `/api/dnd/history` エンドポイントが存在しますが、`speech_service.py` 側では通常の `self.record_history()` (`history_manager.add_entry`) しか呼んでおらず、`dnd_service.record_history()` をどこからも呼び出していません。そのため **WebUI の「DND 抑制・作動履歴」は永久に 0 件のまま** になります。
  2. DND 設定には `targetScope` (`"all"` または特定デバイス) と `targetDevices` が存在し、`dnd_service.evaluate()` もそれを返していますが、`speech_service.py` では宛先スピーカーを展開する**前**に全体を一律ブロックしているため、**特定スピーカーのみを DND 対象にする設定が機能していません**。

---

### 1.7 【High】Alexa デバイスの名前二重ラップバグとカスタムグループ検索漏れ
- **該当箇所**: `app/services/devices_service.py` (L184-192), `app/services/alexa_service.py` (L145-147, L168-175)
- **事象と原因**:
  1. `alexa_service.list_devices()` は各 Echo 端末の `name` を `"Alexa (キッチン)"` の形式で返します。
  2. ユーザーが `"Alexa (キッチン)"` を指定して発声すると、`devices_service.find_device()` の L184 (`if norm.startswith("alexa:") or "alexa" in norm_lower ...`) にマッチし、`alexa_target = "Alexa (キッチン)"` のまま再度 `"name": f"Alexa ({alexa_target})"` でラップして **`"Alexa (Alexa (キッチン))"`** を返します。
  3. `alexa_service.speak()` の `re.sub(r"^Alexa \((.+)\)$", r"\1", clean_name)` は外側の1回しか剥がさないため、スクリプトに `-d "Alexa (キッチン)"` が渡され、デバイス名不一致で発声に失敗します。
  4. 逆に、カスタムグループ等に `"キッチン"` のように `"alexa"` や `"echo"` という文字列を含まない名前で登録した場合、`find_device()` は `alexa_service.devices_cache` を一切検索しないため、デバイスが見つからず `None` となります。
  5. また `devices_service.get_devices()` (L80-86) では、Alexa デバイスに対してのみ `isDefault` プロパティが付与されていません。

---

### 1.8 【High】防災速報 (`disaster_service.py`) と WebUI 表示における複数の不具合
1. **地震情報 (`_handle_quake_report`, Code 551) で地域設定 (`targetScope: "local"`) が無視される**:
   - `app/services/disaster_service.py` L361-380: 緊急地震速報 (`_handle_eew`) には都道府県マッチングがありますが、通常の地震情報 (`_handle_quake_report`) には地域フィルタ処理が一切ありません。そのため設定が「自宅地域のみ (`local`)」であっても、**日本全国のどこかで設定震度以上の地震が起きるたびに毎回スピーカーが鳴動します**。
2. **気象警報 (`check_weather_warnings`) のコンテナ再起動時の誤発報**:
   - L130, L429-443: `self._last_known_warnings` が空集合 `set()` で初期化されるため、コンテナ起動・再起動の10秒後に実行される初回ポーリング時にすでに発表中・継続中の警報や注意報が存在すると、すべて「新規発表」と判定されて誤発報します（また、地域設定を変更した際にも `_last_known_warnings` がクリアされないため差分誤判定が起きます）。
3. **設定値 `checkIntervalMinutes` と `includeAdvice` の無視**:
   - `weatherWarning.checkIntervalMinutes` 設定（デフォルト5分）が `_run_warning_poll_loop` (L389 `await asyncio.sleep(300)`) で参照されておらず、また `dailyWeather.includeAdvice` 設定も `get_today_weather()` (L247-259) で参照されずに常時アドバイス文が付加されています。
4. **WebUI で P2P地震速報が常に「再接続待機中」になる表示バグ**:
   - `app/routers/disaster.py` L32-42 の `GET /api/disaster/status` は `{"connected": True, "isWsConnected": True, ...}` を返しますが、`public/app.js` L6516 は `if (status.wsConnected)` をチェックしています。プロパティ名が一致しないため、**WebSocket が正常接続されていても WebUI 上では常に「P2P地震速報: 再接続待機中」と表示されます**。

---

### 1.9 【Medium】TTS フォールバック時および緊急最速並行生成時のキャッシュファイル汚染
- **該当箇所**: `app/services/tts_service.py` (L330-375, L475-535)
- **事象と原因**:
  `synthesize()` はリクエストされた引数 `voice` を元にキャッシュファイル名 `speech_{key}.mp3` を決定します。
  しかし、指定されたローカル TTS（例: `voicevox:3`）が一時的にオフラインで `Edge-TTS`（`ja-JP-NanamiNeural`）にフォールバックした場合や、`urgent=True` の最速並行生成で別プロバイダーのデフォルト話者が採用された場合でも、**生成された別話者の音声が元のリクエスト `voice` のキャッシュファイル名 `speech_{key}.mp3` として保存されます**。
- **影響**:
  後から VOICEVOX サーバーが復旧しても、同じテキストを `voicevox:3` でリクエストするとキャッシュ HIT してしまい、キャッシュが手動削除されるまで永久にフォールバック時の Edge-TTS 音声が再生され続けます。
- **対策**:
  `was_fallback=True` の場合や `actual_voice != voice` の場合は、リクエストされた `voice` のキーではなく `actual_voice` のキーで保存するか、フォールバック音声はキャッシュ保存しないように修正してください。

---

### 1.10 【Medium】スピーカー種別ごとの音量調整・DLNA URL ハードコード問題
- **該当箇所**: `app/services/speech_service.py` (L255-282), `app/services/tts_service.py` (L538-568)
- **事象**:
  1. `speech_service.py` から `homepod_service.play_audio()` および `alexa_service.speak()` を呼び出す際、`effective_vol`（指定音量や夜間自動音量、DND 囁き音量）が渡されておらず、**HomePod と Alexa では音量制御や DND 囁きモードが一切効きません**。
  2. `tts_service.adjust_volume()` はコメントに `(ONVIF/DLNA用)` と記載されていますが、戻り値が `f"http://127.0.0.1:8080/voice/{output_filename}"` とループバックアドレス＆固定ポートでハードコードされています（ONVIF のローカル `go2rtc` から読む場合は動きますが、LAN 内の DLNA 機器や別ポート運用時にはアクセス不能になります）。

---

### 1.11 【Medium】カレンダー連携 (`calendar_service.py`) および AI 連携 (`ai_service.py`) の不整合
1. **終日予定の DND 設定 (`calendarIncludeAllDay`) 無視と複数予定の判定漏れ (`app/services/calendar_service.py` L80-86)**:
   - WebUI には「終日予定も DND に含める (`dndCalendarIncludeAllDay`)」の設定がありますが、`get_current_meeting_title()` が `if ev.get("isAllDay"): continue` で無条件スキップしています。
   - また、現在時刻に複数の予定が重なっている場合、最初の1件のタイトルしか返さないため、1件目が会議キーワードを含まず2件目が「Zoom会議」だった場合に DND が発動しません。
2. **iCalendar 終日予定の `DTEND` 解釈バグと複数日予定の抽出漏れ (L35-48, L88-93)**:
   - RFC 5545 の終日予定は `DTEND` が「翌日」を指しますが、`datetime.combine(dtend, datetime.max.time())` により翌日 23:59:59 まで1日余分に延長されています。また `get_today_events()` が `ev["start"].date() == today` のみで判定しているため、複数日連続する予定の2日目以降が朝の予定サマリーに含まれません。
3. **AI 朝サマリーのカスタムプロンプト (`dailyCalendarPrompt`) 渡し忘れ (L139)**:
   - `ai_service.summarize_calendar_events()` に `custom_prompt=ai_conf.get("dailyCalendarPrompt")` が渡されていません。
4. **`POST /api/ai/calendar-test` が固定文字列のモック実装 (`app/routers/ai.py` L77-82)**:
   - 実際のカレンダー予定や AI API を一切呼ばず、固定文字列 `"おはようございます。本日は9時30分からチームミーティング..."` を返しています。
5. **AI モデル定義の不整合 (`app/routers/ai.py` L18-32, `app/services/ai_service.py` L214-230)**:
   - `GEMINI_MODELS` に Google API 上存在しない `gemini-3.5-flash` と `gemini-3.8-flash` が含まれており、選択すると毎回 HTTP 404 失敗後にフォールバック通信が発生して応答時間が倍増します。
   - `OPENAI_MODELS` に推論モデル `o1`, `o3-mini` が含まれていますが、`_call_openai_with_err` が `o1`/`o3` 系で廃止された `"max_tokens": 150` パラメータを送信するため（正しくは `max_completion_tokens`）、選択すると HTTP 400 エラーで失敗します。

---

### 1.12 【Medium】その他の機能バグ・不整合
1. **`volume_level=""`（空文字）指定時の `ValueError` クラッシュ**:
   - `app/services/scheduled_speech_service.py` L214 および `app/services/scheduler_service.py` L216 にて `float(volume_level) if volume_level is not None else None` を実行しているため、WebUI や設定から空文字 `""` が渡されると `ValueError: could not convert string to float: ''` で失敗します。
2. **発言履歴の送信元 (`source` / `sourceLabel`) の誤分類**:
   - `scheduler_service.py`（定期スケジュール）、`calendar_service.py`（カレンダー通知）、`disaster_service.py`（防災速報）が `speech_service.speak()` を呼ぶ際に `source="schedule"` 等を渡していないため、発言履歴上で全て `"api"`（外部 API / Webhook）として記録されます。
3. **MQTT トピックの重複購読による2重発声リスク (`app/services/mqtt_service.py` L267-271)**:
   - `voicehub/say` と `voicehub/say/#` の両方を購読しています。MQTT 仕様上 `voicehub/say/#` は親トピック `voicehub/say` にもマッチするため、Overlapping Subscriptions により `voicehub/say` へのメッセージが2回配信され、`urgent: true` 時や重複排除 OFF 時に2回連続で発声されるリスクがあります。
4. **Homebridge プラグインで `target: 'ALL'` が無視されるバグ (`plugins/homebridge-voicehub/src/voicehub-client.ts` L119)**:
   - `if (target && target.trim().length > 0 && target !== 'ALL')` と実装されているため、プリセットスイッチ等で `target: 'ALL'` を指定すると `body.target` が送信されず、全台ではなくデフォルトスピーカー1台のみが鳴動します。
5. **`GET /api/say` と `POST /api/say` の機能乖離 (`app/routers/speech.py` L240-295)**:
   - `GET /api/say` には Cloudflare Tunnel 経由時の非同期即時応答 (`BackgroundTasks`) や `async`/`wait`/`bypassDnd`/`client` パラメータがなく、`GET /api/webhook` ルートも定義されていません。
6. **`log_rotator.py` の gzip フォールバック時の拡張子バグ (`app/core/log_rotator.py` L49-56)**:
   - `zstd` が失敗して `gzip` フォールバックが動いた際、gzip 圧縮したファイルを `.zst` のファイル名 (`container-archive.log.1.zst`) にリネームしてしまうため、不正な `.zst` ファイルが生成されます。
7. **設定・環境変数の不一致**:
   - `.my.env.sample` では `SERVER_IP` と記載されていますが、`app/config.py` は `WIRELESS_IP` を参照しており `SERVER_IP` が無視されます。
   - `.my.env.sample` および `app/config.py` の `MAX_CACHE_SIZE_MB`（デフォルト 1024MB）が `tts_service.py` では参照されず、`self.max_cache_bytes = 200 * 1024 * 1024`（200MB）とハードコードされています。
8. **`onvif_service.py` のハードコードと競合**:
   - L172 に開発環境固有の IP 末尾判定 (`elif ip.endswith((".211", ".212", ".235")): port = 2020`) や Reolink 固有の RTSP パス (`/h264Preview_01_main`) がハードコードされています。
   - RTSP URL 組み立て時 (L227) にカメラの `username`/`password` が URL エンコード (`urllib.parse.quote`) されておらず、`@` や `#` 等を含むパスワードで接続が失敗します。
   - `_cleanup_stream_session` (L275) がタスク管理されていないため、同一カメラへ短時間に連続発声すると1回目のクリーンアップタイマーが2回目の再生中ストリームを途中で切断します。

---

## 2. セキュリティの問題（脆弱性・侵入経路・情報漏洩）

### 2.1 【Critical】Cloudflare Tunnel 経由での Webhook トークン認証バイパス脆弱性
- **該当箇所**: `app/core/security.py` (L34-46 `validate_webhook_token`), `docker-compose.yml`
- **脆弱性のメカニズム（侵入経路）**:
  `validate_webhook_token()` の先頭に以下の「宅内ブラウザ免除ロジック」が存在します：
  ```python
  client_host = request.client.host if request.client else ""
  sec_fetch_site = request.headers.get("sec-fetch-site", "")
  referer = request.headers.get("referer", "")
  if is_private_ip(client_host) and (sec_fetch_site in ("same-origin", "same-site") or referer):
      return True
  ```
  `docker-compose.yml` において `voice-hub` と `cloudflared` はともに `network_mode: "host"` で稼働しており、インターネットから Cloudflare Tunnel を経由して届いたリクエストは、ローカルの `cloudflared` プロセスから `127.0.0.1:8080` へ転送されます。
  その結果、**Cloudflare Tunnel 経由の外部リクエストであっても `request.client.host` (`client_host`) は常に `"127.0.0.1"` (`is_private_ip("127.0.0.1") == True`) になります**。
- **影響**:
  外部の攻撃者が `https://<tunnel_domain>/api/say` に対して、任意の `Referer: https://example.com` または `Sec-Fetch-Site: same-origin` ヘッダーを付与してリクエストを送るだけで、**`WEBHOOK_TOKEN` の検証が 100% バイパスされます**。これにより、第三者がインターネット越しに自宅の全スピーカーから任意の音声を大音量で再生させたり、有料クラウド TTS (Azure/GCP) のクォータを枯渇させたりすることが可能です。
- **対策**:
  1. `if not is_tunnel_request(request) and is_private_ip(client_host) ...` のように、トンネル経由のリクエストでは絶対にトークン検証を免除しないこと。
  2. そもそも HTTP の `Referer` や `Sec-Fetch-Site` ヘッダーは任意のクライアント（`curl` 等）で容易に偽装可能であるため、トークン免除の根拠にせず、WebUI からのリクエストにもセッション Cookie またはトークンを要求する設計に改めること。

---

### 2.2 【Critical】Cloudflare Tunnel 経由での MCP サーバー (`/mcp*`) 完全無認証アクセス脆弱性
- **該当箇所**: `app/core/security.py` (L24-32, L97-99), `app/routers/mcp.py` (L34-37, L113-135, L156-162), `app/services/mcp_service.py` (L197-206)
- **脆弱性のメカニズム（侵入経路）**:
  1. `check_tunnel_access()` は `path.startswith("/mcp")` のトンネル通過を許可しています。
  2. `check_admin_auth()` は `not path.startswith("/api/")` をすべて無条件通過させます。
  3. `app/routers/mcp.py` は `client_ip = request.client.host`（トンネル経由でも常に `"127.0.0.1"`）を取得し、`mcp_service.verify_auth(token, client_ip)` を呼び出します。
  4. `mcp_service.verify_auth()` はトークン未指定時に `if client_ip and is_private_ip(client_ip): return True` を返します。
  5. さらに `GET /mcp`（ステータス取得）と `DELETE /mcp`（セッション強制切断）に至っては `verify_auth()` すら呼ばれていません。
- **影響**:
  **インターネット上の誰もが、Cloudflare Tunnel ドメインの `/mcp` または `/mcp/sse` に対して一切のトークン・パスワード無しで接続し、すべての MCP ツール（`speak` による任意発声、`list_speakers` による宅内機器・IP構成の把握、`get_history` による家庭内の過去の発言・通知内容の盗み見、`set_dnd` による DND 解除、`cancel_scheduled_speech` による予約キャンセル）を無制限に実行可能です。**
- **対策**:
  `mcp.py` で `is_tunnel_request(request)` が真の場合は無条件にトークン一致 (`hmac.compare_digest`) を必須とし、`extract_client_ip(request)`（`cf-connecting-ip` 優先）を使用するとともに、`GET /mcp` および `DELETE /mcp` にも認証チェックを追加してください。また、`verify_auth()` で参照するトークンも `settings_manager.get().get("webhookToken") or settings.webhook_token` の両方を参照するようにしてください。

---

### 2.3 【High】API エンドポイントからの全クレデンシャル（APIキー・カメラパスワード・トークン）平文露出と CORS `*` の組み合わせ
- **該当箇所**:
  - `app/routers/settings.py` (`GET /api/settings`)
  - `app/services/devices_service.py` L98-109 (`GET /api/devices`)
  - `app/routers/status.py` L32 (`GET /api/status`)
  - `app/services/tts_service.py` L280 (`GET /api/tts/providers`)
  - `app/main.py` L89-95 (`CORSMiddleware`)
- **事象と影響**:
  1. `GET /api/settings` が `settings.json` の全内容（Gemini API Key, OpenAI API Key, GCP/Azure TTS API Key, ONVIF カメラのデフォルトパスワードおよび個別パスワード, MQTT パスワード, Webhook トークン）をマスク処理なしで平文のまま返却しています。
  2. デバイス一覧を取得するだけの `GET /api/devices` でも、登録済み全 ONVIF カメラの `username` と `password` が平文で返却されています。
  3. `GET /api/status` でも `webhookToken` の生文字列が返却されています。
  4. デフォルトでは `ADMIN_PASSWORD` が未設定（無認証）であり、さらに `app/main.py` で `allow_origins=["*"]` の CORS が有効になっているため、宅内 LAN 上の任意の端末からはもちろん、宅内 PC/スマホのブラウザで悪意ある外部サイトを開いた際にもクロスオリジンリクエスト経由でこれらの全秘密情報が窃取されるリスクがあります。
- **対策**:
  - API レスポンスでは秘密情報（API キー、パスワード）を `ai_service.mask_key()` のようにマスク（例: `"********"`）して返却し、更新時はマスク文字列や空文字であれば既存の秘密情報を維持する方式に変更してください。
  - `GET /api/devices` のレスポンスから `username` と `password` を除外してください。
  - `CORSMiddleware` の `allow_origins=["*"]` + `allow_credentials=True` を廃止し、同一オリジンまたは許可されたローカルオリジンのみに制限してください。

---

### 2.4 【High】`go2rtc` の RTSP (`:8554`) / WebRTC (`:8555`) 無認証 LAN 公開によるカメラ映像・音声の漏洩
- **該当箇所**: `entrypoint.sh` (L10-15), `data/go2rtc.yaml`, `app/services/onvif_service.py` (L226-288)
- **事象と影響**:
  `go2rtc.yaml` にて API ポートは `127.0.0.1:1984` に制限されましたが、`rtsp.listen: ":8554"` と `webrtc.listen: ":8555"` は全インターフェース (`0.0.0.0`) に無認証でバインドされています。
  `onvif_service.py` はカメラ再生時にカメラの ID・パスワードを含む RTSP URL を `onvif_192_168_11_xxx` として `go2rtc` に登録し、再生終了後の `_cleanup_stream_session()` ではアクティブセッションの切断 (`POST /api/streams?dst=...&src=`) のみを行い、ストリーム定義自体 (`DELETE /api/streams?src=...`) を削除していません。
  そのため、一度でもカメラで発声を行うと、**LAN 内の任意の端末から `rtsp://<server_ip>:8554/onvif_192_168_11_xxx` に接続することで、カメラのパスワードを知らなくても防犯カメラの映像・音声を無認証で視聴できてしまいます**。
- **対策**:
  `go2rtc.yaml` の `rtsp.listen` も `"127.0.0.1:8554"` に限定するか、再生完了時の `_cleanup_stream_session()` で `DELETE /api/streams?src={stream_name}` を呼んでストリーム定義自体を削除してください。

---

### 2.5 【Medium】その他のセキュリティ課題
1. **`.dockerignore` の `data/` 除外漏れによる機密情報の Docker イメージ混入**:
   - `.dockerignore` に `data/` が指定されていないため、`docker compose build` 時にホスト側 `./data/` 内の `.alexa.cookie`, `alexa_credentials.json`, `settings.json` が Docker イメージレイヤー内に `COPY . .` で含まれてしまいます。`.dockerignore` に `data/` と `logs/` を追加してください。
2. **アクセスログ (`/logs/container.log`) への `WEBHOOK_TOKEN` 平文記録**:
   - Homebridge プラグイン (`VoiceHubClient.getUrl()`) がすべてのリクエスト URL に `?token=<WEBHOOK_TOKEN>` を付与するため、`uvicorn.access` ログ（および WebUI のシステムログ画面）に 30 秒おきにトークン文字列が平文で記録されています。クエリパラメータでのトークン送信を廃止して HTTP ヘッダー (`Authorization` / `X-Webhook-Token`) のみに統一し、ログ出力時には `token=` パラメータをマスクしてください。
3. **SSRF（Server-Side Request Forgery）の踏み台リスク**:
   - `POST /api/tts/providers/test` (`baseUrl`), `POST /api/dlna/probe` (`location`), カレンダー同期 (`icalUrl`) は指定された任意の URL へサーバーから HTTP リクエストを発行します。`ADMIN_PASSWORD` 未設定時は外部サイトからの CSRF 等と組み合わせて内部ネットワーク探索に悪用される恐れがあります。
4. **管理者認証 (`auth.py`, `security.py`) の強化余地**:
   - パスワード比較に `hmac.compare_digest` を使用すること。
   - `/api/auth/login` にブルートフォース対策（試行回数制限または失敗時の遅延）を導入すること。
   - `ACTIVE_SESSIONS` に有効期限（TTL）と最大セッション数上限を設けること。
   - Alexa 認証プロキシ (`0.0.0.0:8081`) に自動停止タイムアウト（例: 10分）を設けること。

---

## 3. 最適化・高速化できる点（Optimization & Performance）

### 3.1 【High】発声のたびに毎回実行される `bash alexa_remote_control.sh -a` の排除
- **該当箇所**: `app/services/devices_service.py` (L80-86), `app/services/alexa_service.py` (L156-180), `app/services/speech_service.py` (L192)
- **現状の課題**:
  `speech_service.speak()` は発声リクエストのたびに毎回 `await device_manager.get_devices()` を呼び出し、その中で毎回 `await alexa_service.list_devices()` が実行されます。
  `alexa_service.list_devices()` は `self.devices_cache` が既に存在していてもキャッシュを返さず、**毎回 `bash bin/alexa_remote_control.sh -a` のサブプロセスを起動し、さらに `asyncio.sleep(0.15)` とセマフォ (`_semaphore`) を消費しています**。
- **高速化効果**:
  `list_devices(force_refresh: bool = False)` とし、`self.devices_cache` が存在する場合は即座にメモリキャッシュを返すように変更するだけで、**すべての発声リクエストおよび `/api/devices` 取得の初動レイテンシが 200ms〜数秒短縮され、Alexa 発声時のセマフォ競合も解消されます**。

---

### 3.2 【High】`tts_service.get_voices()` 呼び出しごとの `sync_settings()` と全ローカルエンジン再初期化の排除
- **該当箇所**: `app/services/tts_service.py` (L56-155, L182-220)
- **現状の課題**:
  `/api/voices` や `/api/tts/voices` が呼ばれるたびに `get_voices()` 冒頭で `self.sync_settings()` が呼ばれています。
  `sync_settings()` は毎回 `self.voice_engine_providers` の全インスタンスを新規生成して `_cached_voices`（話者一覧キャッシュ）を破棄した上、末尾で `loop.create_task(self.warmup_enabled_speakers())` を起動して全ローカルエンジンに `/initialize_speaker` と `/speakers` を送信しています。
  そのため、WebUI をリロードするたびにキャッシュが効かず、本体とウォームアップタスクの**二重で全 VOICEVOX / SHAREVOX / COEIROINK サーバーへ HTTP リクエストが飛んでいます**。
- **高速化効果**:
  `get_voices()` からは `self.sync_settings()` を呼ばず（設定変更時のみ `sync_settings()` を呼ぶ）、プロバイダーの `_cached_voices` を活かすことで、`/api/voices` の応答時間を数ミリ秒に短縮できます。

---

### 3.3 【High】Alexa 単独ターゲット時の不要な TTS 音声合成・FFmpeg 処理のスキップ
- **該当箇所**: `app/services/speech_service.py` (L236-282)
- **現状の課題**:
  発声先 (`unique_targets`) が Alexa デバイスのみ（例: `AL:ALL` や個別 Echo 指定）の場合であっても、毎回 `tts_service.synthesize()` を実行してクラウド/ローカル TTS での音声合成と FFmpeg によるチャイム結合を行ってから、`alexa_service.speak(name, text)` に生テキストだけを渡しています（生成した MP3 は一切使用されません）。
- **高速化・コスト削減効果**:
  `all(d.get("type") == "alexa" for d in unique_targets)` の場合は `tts_service.synthesize()` をスキップすることで、**Alexa 発声までの待ち時間を 1〜3 秒短縮し、Azure / GCP の月間無料枠文字数の無駄な消費とディスク I/O を完全にゼロにできます**。

---

### 3.4 【Medium】TTS キャッシュヒット時の `ffprobe` サブプロセス起動のインメモリキャッシュ化と LRU 改善
- **該当箇所**: `app/services/tts_service.py` (L312-328, L485-496, L570-601)
- **現状の課題**:
  1. キャッシュ HIT 時 (L486) にも毎回 `await self.get_audio_duration(final_path)` を呼び、`ffprobe` サブプロセスを起動しています。
  2. `_cleanup_lru_cache()` は `st.st_atime`（最終アクセス時刻）でソートしていますが、Linux の標準マウントオプション (`relatime` / `noatime`) ではファイル読み込み時に `st_atime` が毎回更新されないため、よく使う定型文キャッシュが古い順に削除されてしまいます。
- **高速化効果**:
  `self._duration_cache: Dict[str, float] = {}` に再生時間をキャッシュし、キャッシュ HIT 時は `ffprobe` を起動せず辞書から即座に取得するとともに、キャッシュ HIT 時に `os.utime(final_path, None)`（またはインメモリ LRU 管理）を行うことで、プロセス起動オーバーヘッドの削減と正確な LRU キャッシュ維持を実現できます。

---

### 3.5 【Medium】WebUI 初回ロード時の `/api/settings` 4重リクエスト統合とポーリングログの抑制
- **該当箇所**: `public/app.js` (L198-218), `app/core/logger.py` (L46-52)
- **現状の課題**:
  1. `public/app.js` の `loadInitialData()` 内の `Promise.all` で、`loadCalendarSettings()`, `loadDndSettings()`, `loadSettings()`, `loadAiSettings()` がそれぞれ独立して `fetch('/api/settings')` を同時に呼び出しており、リロードのたびに同一の `/api/settings` リクエストが4回重複発生しています。
  2. `app/main.py` のミドルウェアでは `/api/dnd/status`, `/api/status`, `/api/logs` のポーリングログ出力を抑制していますが、`app/core/logger.py` で `uvicorn.access` ロガーに `file_handler` を直接追加しているため、`uvicorn.access` 側から毎秒〜数秒おきのポーリングログが `/logs/container.log` に大量出力され、数分おきに 1,000 行ローテーション（ファイルコピー）が発生しています。
- **最適化効果**:
  - `loadInitialData()` で最初に1回だけ `/api/settings` を取得して各関数に配布することで、初回ロード時のリクエスト数を削減できます。
  - `uvicorn.access` にポーリングパスを除外する `logging.Filter` を設定するか、`logging_and_security_middleware` のログに一本化することで、ログの視認性向上とディスク I/O 削減が同時に達成できます。

---

### 3.6 【Medium】その他のパフォーマンス改善点
1. **HomePod 再生時の毎回の `pyatv.scan` 短縮 (`app/services/homepod_service.py` L117)**:
   - 再生のたびに `await pyatv.scan(loop, hosts=hosts, timeout=4)` を実行しています。スキャン済み設定のキャッシュ活用やタイムアウト最適化により再生開始までの遅延を短縮できます。
2. **`httpx.AsyncClient` のコネクションプーリング活用**:
   - 各サービスでリクエストのたびに `async with httpx.AsyncClient() as client:` を生成・破棄しているため、毎回 TCP/TLS ハンドシェイクが発生しています。共有の `AsyncClient` インスタンスを Lifespan で管理することで外部 API（Azure, GCP, Gemini, OpenAI, JMA）やローカル `go2rtc` / `VOICEVOX` への通信を高速化できます。
3. **`cast_service.py` のスレッドリーク防止**:
   - `_get_cast()` で再接続する際に古い `Chromecast` インスタンスの `disconnect()` を呼んでおらず、再接続のたびにバックグラウンドソケットスレッドがリークする構造になっています。
4. **`DeviceManager.__init__()` のインポート時同期ブロッキング解消 (`app/services/devices_service.py` L31)**:
   - モジュールインポート時に同期的に `subprocess.run(["avahi-browse", ...], timeout=5)` を実行して起動をブロックしているため、`lifespan` での非同期実行に移行すべきです。

---

## 4. あるべきものが無い点（Missing Elements & Specification Gaps）

### 4.1 【High】自動テストスイート (`tests/`) および静的解析・構文チェックの不在
- `.gitignore` や `.dockerignore` には `.pytest_cache/` や `.ruff_cache/` の記述がありますが、プロジェクト内に `tests/` ディレクトリやテストコードが1つも存在しません。
- 今回判明した `tts_service.py` の `import time` 欠落や `main.py` の `HTTPException` 未インポート、`azure_provider.py` / `gcp_provider.py` の `logger` 未定義といった致命的な `NameError` は、`ruff check app/` や最小限の `pytest` スモークテストが1つでもあればデプロイ前に 100% 即座に検知できたものです。

### 4.2 【High】仕様書 (`Manual.md`) や UI に存在するがバックエンド実装が欠落している機能群
`Manual.md` および設定スキーマ (`settings_service.py`) と実コードを照合した結果、以下の機能が未実装（またはモック・ハリボテ状態）となっています：

1. **スピーカー間同期オフセット制御 (`app/core/sync_engine.py` / `syncOffsets`)**:
   - `Manual.md` 1章・15.1節に「`sync_engine.py`: 各スピーカーの RTT 計測結果に基づき、指数移動平均（EMA）で音ズレ補正オフセットを動的に計算」と記載され、`settings.json` にも `syncOffsets` (`alexaDelayMs`, `homepodDelayMs`, `googleDelayMs`, `dynamicAutoAdjust`) や `/api/settings/sync-test` が存在しますが、**実際には `app/core/sync_engine.py` は存在せず、`speech_service.py` でも `syncOffsets` は一切参照されていません**。
2. **Webhook WAL 永続化キュー (`app/core/queue_manager.py` / `webhook_queue.json`)**:
   - `Manual.md` 1章・14章・15.1節に「`queue_manager.py`: ディスク上の WAL ファイルと同期させプロセス再起動時にも未処理メッセージを復元」と記載され、`data/pending_webhooks.json` や `/api/queue` の `"webhookQueue": []` が存在しますが、実装されておらずインメモリの `BackgroundTasks` のみとなっています。
3. **Homebridge プラグインの個別スピーカー音量制御 (`plugins/homebridge-voicehub/src/accessories/speaker.ts`)**:
   - `Manual.md` 9.2節には「『リビングの音量を 50% にして』といった Siri からの音量操作が可能です」と記載されていますが、`speaker.ts` の `setBrightness()` / `setVolume()` / `setMute()` はローカル変数 `this.currentVolume` を書き換えてログ出力するだけで、**Voice Hub サーバーへの API 通信コードが1行も書かれていません**。
4. **サーバー再起動時のカレンダー初回同期完了前の DND キュー誤再生防止 (`Manual.md` 5.3節)**:
   - `Manual.md` 5.3節には「Google カレンダーとの初回同期が完了するまでキューの消化を一時保留します」と記載されていますが、`app/main.py` の `lifespan` では `calendar_loop()` より先に `dnd_service.start_background_tasks()` が起動され、初回同期完了フラグのチェックもありません。
5. **MQTT `voicehub/dnd/set` の分数指定および Home Assistant Discovery の一部エンティティ (`Manual.md` 11.2〜11.3節)**:
   - `Manual.md` 11.2節に記載の `voicehub/dnd/set` への数値送信（`30`, `60`, `120` 分のタイマーミュート）が `mqtt_service.py` で未処理です。
   - `Manual.md` 11.3節に記載の Home Assistant エンティティのうち、`text`（発話テキスト入力）、`select`（スピーカー選択）、`number`（音量スライダー）が `publish_ha_discovery()` に実装されていません。

### 4.3 【Medium】コンテナヘルスチェック・プロセス監視・グレースフルシャットダウンの欠落
1. **Docker `HEALTHCHECK` の未定義**:
   - `Dockerfile` および `docker-compose.yml` に `healthcheck` が設定されておらず、Uvicorn やイベントループがデッドロックしても Docker や Watchtower が異常を検知できません。
2. **`go2rtc` デーモンのプロセス死活監視の不在**:
   - `entrypoint.sh` で `/usr/local/bin/go2rtc ... &` とバックグラウンド起動したまま監視しておらず、稼働中に `go2rtc` が異常終了しても自動再起動されません。
3. **FastAPI `lifespan` シャットダウン時の各バックグラウンドタスク停止処理の欠落**:
   - `app/main.py` の `lifespan` 終了時には `await mqtt_service.stop()` しか呼ばれておらず、`disaster_service`, `scheduler_service`, `scheduled_speech_service`, `dnd_service`, `calendar_service` の各非同期ループタスクをキャンセル・停止する処理がありません。また `scheduled_speech_service.py` で実行中 (`status == "running"`) のまま再起動されたタスクを `load()` 時にリカバリする処理や、完了済みタスクの定期パージ処理も欠落しています。

### 4.4 【Low】ホスト側ディレクトリと Docker ボリュームの二重構造および不要ファイルの残存
1. **ホスト側 `./data/`, `./logs/`, `./public/voice/` と Docker Named Volume の乖離**:
   - `docker-compose.yml` では `voice_data:/app/data`, `voice_cache:/app/public/voice`, `voice_logs:/logs` と名前付きボリュームをマウントしているため、ホスト側の `/root/google-home-voicetext-docker/data/` にあるファイル（10月15日〜18日時点の古い `settings.json` 等）はコンテナから一切参照されておらず、管理上の混乱を招いています。
2. **不要な旧スクリプト・テスト残骸ファイル**:
   - `bin/homepod_scan.py`, `bin/homepod_stream.py`: 現在は `app/services/homepod_service.py` 内で直接 `pyatv` を呼んでおり、どこからも参照されていないデッドコードです。
   - `data/pending_webhooks.json`: どこからも参照されていない空ファイルです。
   - `public/voice/_wav_files` (0 byte), `public/voice/speech_aac5d58a57b7d8af42f650c958ac0c10.mp3` (0 byte), `public/voice/reolink_test.mp3`: ホスト側ディレクトリに取り残された古いファイル・破損ファイルです。
3. **`Manual.md` 15章のモジュール説明と実ファイル名の乖離**:
   - `Manual.md` 15.3節では `core/logging.py`（リングバッファ `collections.deque`・`logs/app.log`）と記載されていますが、実際の実装は `app/core/logger.py` + `app/core/log_rotator.py`（`/logs/container.log` + `/logs/container-archive.log`）となっており、ドキュメントの記述が古い設計のまま残っています。

---

## 5. 推奨される改修優先順位（アクションプラン）

1. **【即時対応（数分で完了・効果絶大）】クラッシュバグと認証バイパスの修正**
   - `app/services/tts_service.py` に `import time` を追加（現在停止している新規音声合成の即時復旧）。
   - `app/main.py` に `HTTPException` のインポート追加、およびミドルウェア内での `HTTPException` キャッチ＆レスポンス変換。
   - `app/services/tts/azure_provider.py` と `gcp_provider.py` の `logger.warning` を `log.warning` に修正。
   - `app/core/security.py` と `app/routers/mcp.py` で Cloudflare Tunnel 経由時 (`is_tunnel_request(request)`) のトークン免除を禁止し、`GET /mcp`・`DELETE /mcp` にも認証を適用。
2. **【短期対応】機能不具合と情報漏洩の修正**
   - `settings_service.py` の `deviceGroups` / `ipAliases` の更新を上書き方式に修正（削除機能の復旧）。
   - `dnd.py` / `mcp_service.py` の時間省略時 `manualUntil` を無期限値に修正、`speech_service.py` から `dnd_service.record_history()` を呼び出し。
   - `devices_service.py` の Alexa 二重ラップ解消と `alexa_service.devices_cache` 検索追加、および `/api/devices`・`/api/settings`・`/api/status` からのパスワード・APIキー平文露出のマスク化。
   - `disaster_service.py` の地震情報地域フィルタ追加・起動時警報ベースライン処理追加、`public/app.js` の `status.isWsConnected` 参照修正。
   - `go2rtc.yaml` の RTSP ポートのローカル限定化（または再生後のストリーム削除）と `.dockerignore` への `data/` 追加。
3. **【中期対応】パフォーマンス最適化と未実装仕様の統合**
   - `alexa_service.list_devices()` と `tts_service.get_voices()` のキャッシュ有効化、Alexa 単独時の TTS 合成スキップ、`ffprobe` 結果のインメモリキャッシュ化。
   - `uvicorn.access` のポーリングログ抑制とクエリパラメータ `?token=` のヘッダー移行。
   - `syncOffsets` の反映、HomePod/Alexa の音量制御対応、Homebridge プラグインの修正、および `pytest` / `ruff` による自動チェックの導入。
