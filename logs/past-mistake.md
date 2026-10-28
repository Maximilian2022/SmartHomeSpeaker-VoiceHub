# 過去のミスと再発防止策

## [2026-10-17 01] Python移行方針に反して旧JSライブラリに依存したラッパーを作成してしまった
- **事象**: Alexa認証プロキシを実装する際、旧Node版の `alexa-cookie2` に引きずられて `bin/alexa_proxy.js` を作成し node で動かそうとしてユーザーから厳しく指摘された。
- **原因**: 既存ライブラリをそのまま使えば早いという安易な妥協。
- **防止策**: 原則「100% Pythonネイティブ」を絶対遵守する。外部Node/JSに頼らず、aiohttp/FastAPI/httpx等の標準Pythonスタックで自作する。

## [2026-10-17 02] WebUIとAPIレスポンスのプロパティ不一致による表示エラー・成功判定漏れ
- **事象**: `/api/say` のレスポンスに `results` 配列や `dndSuppressed` プロパティが無く、Web UI上で「0台成功」と誤認表示されたりDNDトーストが出なかった。
- **原因**: フロントエンド `public/app.js` が期待しているデータ構造とPython側の返却辞書の照合不足。
- **防止策**: フロントエンドの `fetch` レスポンス処理を必ず精読し、期待されるキー（`results`, `success`, `dndSuppressed`, `message` 等）を完全に返却する。

## [2026-10-17 03] ロギング不足と例外握りつぶしによるトラブルシューティング困難
- **事象**: Web GUIでエラーが発生してもコンテナログに原因やスタックトレースが出力されず、トラブルシューティングが極めて困難だった。
- **原因**: `except Exception:` でログを出さずに握りつぶしていたり、FastAPIのグローバル例外ハンドラでスタックトレースを出力していなかった。
- **防止策**: 全エンドポイント・ミドルウェア・外部デバイス通信（Cast, Alexa, HomePod, ONVIF, 天気等）で `traceback.format_exc()` や詳細コンテキスト（引数、URL、デバイスIP）を確実にロギングする。

## [2026-10-17 04] API返却型とフロントエンド期待構造の不一致による発言履歴非表示
- **事象**: Webhookから発話通知が届いた後、Web GUIの発言履歴タブを開いても履歴が1件も表示されなかった。
- **原因**: 旧Node版は `{ history: [...], total: ... }` を返していたが、Python版 `/api/history` が `list`（`[...]`）を直接返却したため、`public/app.js` 側で `data.history` が `undefined`（空）と判定された。
- **防止策**: APIは常に `{ history: items, total: len(items) }` の辞書形式で返し、フロントエンド側でも `Array.isArray(data) ? data : (data.history || [])` のように互換ガードを設ける。

## [2026-10-17 05] サービス内メソッド名不一致（speak vs say）によるAttributeError
- **事象**: MCP や MQTT サービスから `speech_service.say(...)` を呼び出したところ、`'SpeechService' object has no attribute 'say'` が発生した。
- **原因**: `SpeechService` クラス内の主要発話メソッド名が `speak` だったのに対し、ルーター等（`/api/say`）の命名に引きずられて未確認のまま `say` を呼んでしまった。
- **防止策**: 内部サービスを呼び出す際は必ずサービス側のメソッドシグネチャを grep で事前確認する。さらに、よく使われる命名揺れ（`say` と `speak`）についてはクラス内で `say = speak` のようにエイリアスを定義して相互運用性を高める。

## [2026-10-18 01] escapeHtmlの引数型チェック不足によるTypeError
- **事象**: WebUIの設定ロード時（`loadSettings()`）に `str.replace is not a function` のTypeErrorが発生し、後続のUI描画処理（MQTTブローカー一覧レンダリング等）が中断した。
- **原因**: テンプレートリテラル内で `escapeHtml(b.port)` のように数値型が渡された際、`escapeHtml` 側で `str.replace` を直接呼び出していたため、文字列以外が渡された際に例外が発生した。
- **防止策**: `escapeHtml` などの文字列ヘルパー関数では、必ず `if (str === null || str === undefined) return ''; return String(str)...` のように明示的に文字列型へのキャストガードを行う。

## [2026-10-18 02] 外部API呼び出しの非実在モデル名指定と空文字握りつぶしによるUIエラー
- **事象**: WebUIの「AI連携」設定画面で「要約テスト試聴」を実行すると「要約テスト失敗: 要約の生成に失敗しました」が発生した。
- **原因**: API呼び出し失敗時にバックエンドがエラーログを出さずに空文字 `""` を返却し、フロントエンド側でも空文字判定で例外をスローしていた。加えてモデル一覧取得APIの戻り値フォーマットがフロントエンド期待値と乖離していた。
- **防止策**: 
  1. 外部AIモデル名は実在する安定モデル（`gemini-2.5-flash` 等）をデフォルト・フォールバックとして設定し、ロード時に廃止モデルが指定されている場合は自動自己修復する。
  2. 外部API呼び出しのエラー時は必ずHTTPステータスとレスポンスをロギングし、404等のモデル未検出時は推奨モデルへ自動リトライする。
  3. API側で空文字ではなくフォールバックテキストを返し、フロントエンドでもエラー理由（HTTPステータスやメッセージ）をユーザーに明示する。

## [2026-10-18 03] 外部AIモデルの世代・ライフサイクル誤認による廃止モデル指定と現行モデル除外
- **事象**: Gemini 1.5系（`gemini-1.5-flash`, `gemini-1.5-pro`）が既に提供終了（HTTP 404）しているにもかかわらず安定版としてUIやコードに追加してしまい、逆に実在する現行モデル（3.8系・3.5系）を一時的なHTTP 503（高負荷Unavailable）エラーを見て非実在と誤認して除外してしまった。
- **原因**: 外部API（Google AI Studio）のモデル一覧API（`GET /v1beta/models`）を直接叩いて実態を事実確認せず、古い知識や一時的な高負荷エラーの現象面から誤った推測を行った。
- **防止策**: 外部APIの対応モデルや仕様変更を扱う際は、推測で判断せず必ず公式モデル一覧エンドポイントを直接呼び出して最新のアクティブモデル一覧・サポートメソッドを事実確認してからコードや選択肢に反映する。また一時的な503エラーと404 Not Foundを明確に区別し、障害時のフェイルオーバー設計を徹底する。

## [2026-10-18 04] WebUIからの静的ファイルリンクがFastAPI静的マウント対象外のパスを参照し404エラー
- **事象**: WebUI（HomeKit連携カード）の「📖 プラグイン解説書」リンク（`/plugins/homebridge-voicehub/README.md`）をクリックした際に 404 Not Found となった。
- **原因**: 
  1. `docker-compose.yml` でホストからコンテナにマウントされているのは `./public`（`/app/public`）と `./app`（`/app/app`）のみであり、プロジェクトルートの `./plugins/` はコンテナ内にマウントされていなかった。
  2. FastAPI 側の静的配信も `app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True))` となっており、`public/` 外のパスは配信対象になっていなかった。
- **防止策**: 

## [2026-10-18 05] 非公式・非保証ライブラリ（Edge TTS）を公式クラウドAPIと同等と過大表現し、誤った安心感を与えてしまった
- **事象**: Azure Speech Key 取得手順のヘルプにおいて、標準の Edge TTS が内部的に同一の Neural 音声エンジンを採用していることのみに着目し、「全く同じなので無理に Azure を登録しなくてもよい」と案内してしまった。
- **原因**: 
  1. Edge TTS が Microsoft Edge ブラウザの内部通信をリバースエンジニアリングした非公式（グレー）な手法であり、Microsoft のサイレント仕様変更によって過去にも世界規模で利用不能になる障害が頻発しているリスクの考慮不足。
  2. 一方で Azure Speech が公式 SLA と正当な API キー認証に基づく正規サービス（家庭内インフラ・防災アナウンスの長期安定運用における本命）であるという決定的な差異への配慮不足。
  3. 「過大には記載せず、慎みをもって上品な記載にすること。言い過ぎない。謙遜した描写でちょうどいいかも」というプロジェクト方針に反する過大表現。
- **防止策**: 
  1. 技術的な位置づけを案内する際は、手軽さ・無料の利点のみならず、公式・非公式の規約的・運用的リスク（SLA、仕様変更耐性）を客観的かつ誠実に記述する。
  2. 標準の Edge TTS は「初期設定不要ですぐに動く手軽な選択肢」として謙虚に位置づけ、公式 Azure Speech Service は「仕様変更リスクのない、長期安定運用や Edge TTS 不調時の堅牢なバックアップとしての推奨選択肢」として正確に案内する。

## [2026-10-18 06] フロントエンドでの未定義関数呼び出し（fetchVoices）による ReferenceError
- **事象**: 設定画面の「💾 音声エンジン設定を保存」ボタン押下時、API への設定保存（HTTP 200）は成功したものの、直後の画面更新処理で `fetchVoices is not defined` の ReferenceError が発生し、「設定保存エラー: fetchVoices is not defined」とエラーメッセージが表示された。
- **原因**: 既存コードで定義されていた話者一覧取得関数が `loadVoices()` であったのに対し、事前の定義確認を怠り、推測で `fetchVoices()` を呼び出してしまったことによる名前の不一致。
- **防止策**: 
  1. フロントエンドで既存のロード関数やハンドラを呼び出す際は、必ず `grep` で正確な関数名・スコープを事前確認してから記述する。
  2. 念のため `if (typeof func === 'function')` 等の存在チェックを噛ませ、想定外の ReferenceError で後続処理やユーザー体験が中断されるのを防ぐ。

## [2026-10-18 07] Google Cast (Chromecast) でのメディアURLクエリパラメータによるロード拒否と、静的配信304による再生スキップ問題
- **事象**: 
  1. Google Home（Chromecast）で同一音声を再取得する際、旧実装（StaticFiles）がクライアントの `If-None-Match` に対し `HTTP 304 Not Modified` を返却したため、Chromecast が実データがないと判断して再生を即座にスキップ（無音終了）した。
  2. この 304 を防止しようとして、音声 URL に `?t={timestamp}`（キャッシュバスター）を付与したところ、Google Cast の MediaController / Cast Receiver がクエリ文字列付き URL を無効とみなし、サーバーへのフェッチ（GETリクエスト）すら行わなくなるという二次障害を誘発してしまった。
- **原因**: 
  1. Google Cast（Chromecast Default Media Receiver）はメディア URL の末尾拡張子や URL 構文を厳格に判定しており、`?t=...` などのクエリパラメータが付与されているとメディア読み込みを拒絶・スキップする仕様であったことの認識不足。
  2. Starlette の `StaticFiles` はクライアントが `If-None-Match` や `If-Modified-Since` を送信すると自動的に `HTTP 304` を返却するが、Chromecast はオーディオストリームとして実データ（200 OK または 206 Partial Content）を必要とするため、304 では再生できない。
- **防止策**: 
  1. スマートスピーカー（Google Cast / DLNA）へ渡すメディア URL は一切のクエリパラメータを付与せず、純粋な拡張子付き URL（`http://.../voice/speech_xxx.mp3`）に統一する。
  2. FastAPI 側で `/voice/{filename}` 専用エンドポイント（`FileResponse`）を設け、`methods=["GET", "HEAD"]` と `Cache-Control: no-cache, no-store, must-revalidate`、`Accept-Ranges: bytes` を設定する。
  3. Starlette の `FileResponse` により、Range リクエスト（206 Partial Content）をネイティブ処理しつつ、304 を一切返さず常に実データ（200/206）を配信するアーキテクチャを確立する。

## [2026-10-18 08] サブエージェントの検証メモ引きずりによるポート番号混同（Alexa用8081とWebUI本体8080の誤記報告）
- **事象**: ブラウザ検証用のサブエージェント（`browser_subagent`）が検証作業を行う際、自身の思考用スクラッチパッドや完了報告テキストに「ブラウザにて `http://localhost:8081/`（音声ハブ）にアクセスし…」「音声ハブのサーバーがポート8081で稼働していることを確認」と記述し、ユーザーに混乱と不審（「なんで8081？8080じゃなくて？」）を与えてしまった。
- **原因**: 
  1. VoiceHub 本体（FastAPI / WebUI）の正式な稼働ポートは一貫して `8080`（`docker-compose.yml`, `PORT=8080`）である。
  2. 一方、リポジトリ内には Alexa 認証プロキシ（`alexa_proxy_service.py`）用として `8081` が割り当てられており、Dockerfile にも `EXPOSE 8080 8081` と記載されている。
  3. 以前の別セッション時のブラウザログやスクラッチパッドに残っていた「8081」という数値をサブエージェントが無批判に引き継ぎ、親エージェントがタスク指示文で「http://localhost:8080/ を開きます（ポートは8080です）」と指定していたにもかかわらず、自身の完了レポートに「8081」と記載してしまった。
## [2026-10-19 01] JavaScriptファイル末尾での重複したinit()宣言による初期化コード上書きとタブ復元不全
- **事象**: WebUI（`public/app.js`）において、F5キーやブラウザリロード時に直前に開いていたタブ（例: 「📜 システムログ」や「拡張・システム設定」）が保持されず、常に初期画面（「即時発言」）に戻ってしまう不具合が発生した。
- **原因**: 
  1. 新機能（システムログタブ）の初期化コードを追加する際、`public/app.js` の末尾（7632行目）に誤って簡易的な `async function init()` を二重定義してしまった。
  2. JavaScript の仕様（関数宣言のホイスティングと上書き）により、ファイル先頭（143行目）にあった本来の `init()`（`setupWebhookBuilder`, `setupSettingsHandlers`, `restoreActiveTabs`, `loadInitialData` 等をすべて実行するコード）が丸ごと末尾の簡易 `init()` で上書きされ、リロード時のタブ復元関数 `restoreActiveTabs()` や各機能のイベント登録が一切実行されなくなっていた。
- **防止策**: 
  1. 同一スコープ内で `init()` などのグローバル/クロージャ初期化関数を複数箇所で定義しない。機能追加時の初期化処理は既存の正規 `init()` 関数内に追記することを徹底する。
  2. 単体ファイルの編集後やリファクタリング時には、重要関数（`init`, `setupEventListeners` 等）の名称が重複していないか静的チェック（grep検索）を行い、不意の上書き事故を未然に防止する。
## [2026-10-19 02] .gitignore による public/sound の未追跡と config.py での自動作成漏れによる、クリーン環境での StaticFiles マウント時 RuntimeError
- **事象**: GitHub Actions 上でクリーンな Docker ビルドを行い、コンテナ内でテストを実行したところ、`app.main` のインポート時に `RuntimeError: Directory '/app/public/sound' does not exist` が発生し、単体テストが失敗した。
- **原因**: 
  1. `app/config.py` において、`DATA_DIR` と `VOICE_DIR` は `mkdir(parents=True, exist_ok=True)` されていたが、`SOUND_DIR`（`/app/public/sound`）の自動作成が漏れていた。
  2. `public/sound/` 配下には効果音 MP3（`alert.mp3`, `dingdong.mp3` 等）しか置かれておらず、`.gitignore` で `*.mp3` が除外されていたため、Git リポジトリに `public/sound/` ディレクトリ自体が含まれていなかった。
  3. ホスト環境では過去の実行でディレクトリが存在していたためテストが通過していたが、CI のようなまっさらなクローン環境ではディレクトリが存在せず、Starlette の `StaticFiles(directory=str(SOUND_DIR))` が起動時に例外を送出してクラッシュした。
- **防止策**: 
  1. FastAPI / Starlette の `StaticFiles` でマウントするディレクトリは、`app/config.py` のインポート時や起動時フックで必ず `mkdir(parents=True, exist_ok=True)` を実行し、ディレクトリ不在によるクラッシュを構造的に防止する。
  2. アプリの動作に必須な静的リソースディレクトリ（効果音等）は、`.gitignore` で除外されないようホワイトリスト指定（`!public/sound/*.mp3`）し、`.gitkeep` を配置して空ディレクトリとしても確実に追跡・コミットされるようにする。
  3. Dockerfile にも `mkdir -p` を明記し、イメージ単体で起動した場合でも必要なディレクトリ構成が欠落しないよう多重防御を行う。

## [2026-10-19 03] Dockerfile 内での C/C++ コンパイラ欠落による ARM64 マルチアーキテクチャビルド時の wheel ビルド失敗
- **事象**: GitHub Actions でのマルチアーキテクチャ（amd64 / arm64）Docker イメージビルドにおいて、amd64 側のビルドおよびテストは成功したものの、arm64 側のビルド時に `pip install -r requirements.txt` 内で `miniaudio` のビルド時に `FileNotFoundError: [Errno 2] No such file or directory: 'c++'` が発生し、ビルドジョブが失敗した。
- **原因**: 
  1. `python:3.14-slim` ベースの軽量イメージには C/C++ コンパイラ（`gcc`, `g++`）が含まれていない。
  2. `amd64` では `miniaudio` の pre-built binary wheel が PyPI 上に存在していたためコンパイル不要でインストールできたが、`arm64`（特に Python 3.14 向け）の wheel が未配布だったため、ソース（C++）からのビルドがトリガーされた。
  3. Dockerfile の `apt-get` に `gcc` および `g++` が含まれていなかったため、`subprocess.Popen(['c++', ...])` が実行できずビルド失敗となった。
- **防止策**: 
  1. マルチアーキテクチャ（特に ARM64 や新規 Python バージョン）を対象にする Dockerfile では、一部の C/C++ 拡張パッケージの wheel が未提供である可能性を常に考慮し、`gcc` および `g++` 等のビルドツールを apt-get のインストール対象に含めておく。
  2. ビルド時エラー発生時は GitHub CLI（`gh run view <id> --log-failed`）を用いて直ちにアーキテクチャ固有のエラーログを特定し、最小限のパッケージ追加で迅速に解消する。

## [2026-10-20 01] Docker Hub のユーザー名（Docker ID）が変更可能であると誤認して案内してしまった
- **事象**: ユーザーのDocker Hubアカウント名が `madpiero` で作成されていた際、リポジトリ名 `maximilian2022` と統一するために「Docker Hubのアカウント設定からChange usernameで変更できる」と案内したが、実際には設定項目が存在しなかった。
- **原因**: 
## [2026-10-20 02] pytapoの認証引数不一致（admin固定・ハッシュ渡し）によるエラーを「取得不可」と早合点して自動取得ロジックを撤廃してしまった
- **事象**: Tapoカメラのデバイス名（`device_alias`）取得において、`pytapo` でローカルAPI接続時に `Temporary Suspension` や認証エラーが発生した際、その原因を「平文ではなく不可逆SHA256ハッシュを渡しているためTapoの仕様上取得不可能である」と誤認し、ポート443アクセスを撤廃してしまった。しかし実際には、ユーザー名に `admin` ではなく TP-Link ID（メールアドレス）を正しく渡し、平文クラウドパスワードでアクセスすれば、`192.168.11.211` から「ウッドスロープ」、`192.168.11.212` から「ウッドデッキ」といったデバイス名が即座に取得可能であった。
- **原因**: 
  1. `pytapo.Tapo(ip, user, password, cloudPassword=...)` の第2引数 `user` にメールアドレスではなく誤って固定値 `"admin"` を渡していたこと、および `password` に平文ではなく不可逆ハッシュを渡していたため認証失敗が起きていた。
  2. 以前の検証で実際に `リビングTapo` が取得できていた事実があるにもかかわらず、直近のエラーログ（Temporary Suspension）を見て「ハック通信では取得できない」と早合点してロジックを削除してしまった。
- **防止策**: 
## [2026-10-20 03] ユニットテスト追加時にグローバル未定義のclient変数を参照してNameError
- **事象**: `tests/test_smoke.py` にお気に入りAPI（`/api/devices/favorites` 等）のスモークテストを追加した際、`TestClient` のインポートおよび `client` インスタンスの生成を行わずに `client.get(...)` を記述したため、`NameError: name 'client' is not defined` でテスト実行が失敗した。
- **原因**: 
  1. 他のテストファイル（`test_tapo.py` など）では `setUp` 内で `self.client = TestClient(app)` を準備していたが、`test_smoke.py` では `client` がモジュールトップやクラス変数として定義されていなかった。
  2. 既存のコードベースでの `client` 定義の有無を確認せずに記述を進めてしまった。
- **防止策**: 
  1. ユニットテストで API エンドポイントを検証する際は、`from fastapi.testclient import TestClient` および `from app.main import app` から明示的に `client = TestClient(app)` をスコープ内で初期化するか、`setUp` メソッドで `self.client` を定義して利用すること。
  2. コード編集前に同ファイル内のスコープやインポート定義を `view_file` または `grep_search` で確認する習慣を徹底する。

## [2026-10-21 01] サービス間呼び出しで引数名ミス（speech_service.speakでtargetsではなくtargetと指定）によるTypeErrorと音声再生失敗
- **事象**: 雨アラーム機能（`RainAlarmService`）から音声発話（`SpeechService.speak`）を呼び出す際、テスト発声ボタンを押してもスピーカーから音声が再生されず、コンテナログに `SpeechService.speak() got an unexpected keyword argument 'target'. Did you mean 'targets'?` のエラーが出力されていた。
- **原因**: 
  1. `SpeechService.speak` の第2引数名は `targets: Optional[Union[str, List[str]]]` であるにもかかわらず、`rain_alarm_service.py` 内で `target=target` と単数形で記述してしまっていた。
  2. ユニットテストのモック検証で `mock_speak.assert_awaited_once()` のみを確認し、キーワード引数の完全一致チェックを行っていなかった。
- **防止策**: 
  1. サービス共通メソッド（`SpeechService.speak` 等）を呼び出す際は、必ず定義元のシグネチャを `view_file` または `grep_search` で確認し、正しい引数名（`targets`, `chime`, `urgent` 等）を指定する。
  2. ユニットテストでは可能な限り `mock_speak.assert_awaited_once_with(...)` または引数名のチェックを検証に含め、引数名の typo を CI・テスト段階で確実に検出できるようにする。

## [2026-10-21 02] i18n辞書およびHTML内での<br>タグ使用時にdata-i18n-html指定漏れによりraw文字列としてレンダリングされた問題
- **事象**: WebUI の Yahoo! Client ID 説明テキストに `<br>` という文字列がそのまま画面上に表示されていた。
- **原因**: 
  1. 多言語辞書（`ja.json`, `en.json`）内で `<br>` を記述していたが、HTML要素側の `data-i18n` 適用処理（`i18n.js`）は、デフォルトで安全のため `textContent`（テキストノード）として代入する仕様だった。
  2. `data-i18n-html="true"` が指定されていない要素に HTML タグを含めてしまったため、エスケープされずにタグの文字そのものが表示されていた。
- **防止策**: 
  1. i18n テキストには可能な限り生の HTML タグ（`<br>` 等）を直接含めず、セマンティックなブロック要素（`<div>`, `<p>`）または CSS の margin/padding で分割・レイアウトする。
  2. やむを得ず HTML タグを含む辞書キーを表示する場合は、対象要素に必ず `data-i18n-html="true"` を明示指定する。

## [2026-10-22 01] バックエンドAPI追加時にコンテナ（非reloadモード）を再起動せず、フロントエンド先行反映による404エラーを発生させてしまった
- **事象**: DNDの外部デバイス連携用スクリプトプレビューAPI（`/api/dnd/script/preview`）を追加した際、WebUI画面上に「// エラー: プレビュー取得失敗」と表示され、ブラウザからHTTP 404 Not Foundとなっていた。
- **原因**: 
  1. Dockerコンテナ（`SmartSpeaker-VoiceHub`）内の uvicorn は本番モード（`--reload` なし）で起動されており、ホスト側の `app/routers/dnd.py` を編集しただけではメモリ上のFastAPIアプリケーションに新しいルーターやエンドポイントが反映されていなかった。
  2. 一方、静的ファイル（`public/index.html`, `public/app.js`）はディスクから直接読まれるためフロントエンドのみが先行して新APIを呼び出してしまい、404 Not Found が発生した。
- **防止策**: 
  1. Python バックエンドのルーティングやサービスを変更・追加した際は、テスト実行だけでなく、稼働中のコンテナ（`docker restart SmartSpeaker-VoiceHub`）を再起動して uvicorn に新しいコードを確実に再読み込みさせること。
  2. 実装完了の報告前に、実際に稼働中のエンドポイント（`curl -i http://localhost:8080/api/...`）に対してHTTPリクエストを送信し、200 OKが返ることを実機レベルで確認する手順を必須とする。

## [2026-10-23 01] dict.get(key, "").strip()でキーの値がNoneの場合にデフォルト値が効かずAttributeError
- **事象**: GitHub Actions の CI テスト（`Run unit & smoke tests inside container`）にて、クリーンな Docker 環境でのテスト実行時に `check_admin_auth` 内の `settings_manager.get().get("webhookToken", "").strip()` で `AttributeError: 'NoneType' object has no attribute 'strip'` が発生し、CI パイプラインが失敗した。
- **原因**: 
  1. Python の `dict.get(key, default)` は、辞書内に `key` が存在し、その値が `None`（JSON の `null` や未設定値）である場合、第2引数の `default` は返却されず格納されている `None` がそのまま返される。
  2. その戻り値に対して直接 `.strip()` を呼んでいたため、開発環境（実機設定で値が入っていた環境）では顕在化せず、初期状態・未設定状態のクリーンなテスト環境でのみ例外が誘発された。
- **防止策**: 
  1. 辞書から文字列値を取得して空白除去や前処理を行う場合は、必ず `(dict.get(key) or "").strip()` のように `or ""` で `None` を空文字列へフォールバックさせるイディオムを徹底する。
  2. テスト実施時は、実機ボリュームのマウントに依存せず、Clean Docker コンテナ（`docker run --rm ...`）で初期状態データでのテストスイート全体が通ることを検証する。

## [2026-10-24 01] コールバック関数の引数不一致（**kwargs欠落）によるTypeErrorで防災速報の発話と履歴保存が失敗した問題
- **事象**: 気象警報や地震速報（実機ログ: 2026-10-24 01:09:43 地震情報受信時）が発生した際、`[ERROR] [VoiceHub.Disaster] Speech dispatch error in disaster: lifespan.<locals>.on_disaster_speech() got an unexpected keyword argument 'source'` という TypeError が発生し、スピーカーから発話されず、発言履歴一覧にも残っていなかった。
- **原因**: 
  1. `disaster_service.speak` は内部で `self._speech_executor` に対し `source="disaster"`, `source_label="防災速報"`, `client_name="防災速報サービス"` 等のキーワード引数を渡して呼び出していた。
  2. 一方、`app/main.py` の lifespan で登録されていたコールバック `on_disaster_speech(text: str, targets=None, urgent: bool = True, volume_level: int = None)` はキーワード可変長引数（`**kwargs`）を受け取るシグネチャになっておらず、予期せぬ引数 `source` を受け取った時点で Python の `TypeError` が送出され、発話処理全体が中断していた。
- **防止策**: 
  1. 外部サービスや他モジュールから呼び出されるコールバック関数（特に `set_speech_executor` などの汎用発話エグゼキューター）を定義する際は、必ず末尾に `**kwargs` を受け取るシグネチャにし、転送先メソッド（`speech_service.speak`）へ `**kwargs` をそのまま渡す設計にする。
  2. サービス間のコールバック連携を検証する単体テスト（`tests/test_speech_dispatch.py`）を作成し、想定される追加引数（`source`, `source_label` 等）が渡された際にも例外なく処理されることをテストで永続的に担保する。

## [2026-10-24 02] ユニットテスト内で実機スピーカー送信処理（cast_service.play_audio）のモック漏れにより外部遮断CI環境でテスト失敗
- **事象**: GitHub Actions の CI テスト（`Run unit & smoke tests inside container`）にて、`test_speech_dispatch.py` の `test_deduplication_skip_recorded_in_history` が `AssertionError: False is not true (res1.get("success") == False)` で失敗し、Docker イメージビルドおよび v1.0.11 リリースパイプラインが停止した。
- **原因**: 
  1. `test_deduplication_skip_recorded_in_history` では `speech_service.speak` を呼び出して重複排除スキップを検証していたが、TTS（`tts_service.synthesize`）とデバイス検索（`device_manager.get_devices`）のみをモックし、実際の音声送信先である `cast_service.play_audio` のモックを欠落させていた。
  2. ローカル開発環境では LAN 上に実機 Google Cast スピーカーが存在し接続が成功していたためテストが通過していたが、外部ネットワークへのソケット通信が遮断された GitHub Actions CI / Docker クリーン環境では実機IPへの接続に失敗し、`speech_service.speak` の返り値が `success: False` となっていた。
- **防止策**: 
  1. ユニットテスト内で `speech_service.speak` 等のエンドツーエンドに近い処理をテストする場合、ネットワーク I/O を伴う全ドライバサービス（`cast_service.play_audio`, `homepod_service.play_audio`, `alexa_service.speak` 等）を必ず明示的にモック（`AsyncMock(return_value=True)`）する。
  2. テスト内でターゲットスピーカーを指定する際は `targets=["192.168.1.50"]` のように固定の仮想ターゲットを指定し、ローカル設定ファイル（`settings.json` の `defaultSpeaker` 等）の実機設定に影響されないよう完全にテスト環境を隔離する。

## [2026-10-25 01] API設定でマスクされたAPIキー(********)がフロントエンドからモデル取得APIに渡され外部APIから400エラーが記録された問題
- **事象**: コンテナログに `[WARNING] [VoiceHub.AI] [AiService] Geminiモデル動的取得エラー (HTTP 400): {"error": {"code": 400, "message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT"}}` が定期的に記録されていた。
- **原因**: 
  1. `/api/settings` の GET 応答時に、セキュリティ保護として `geminiApiKey` や `openaiApiKey` が `********`（8文字のアスタリスク）にマスクされてクライアントへ返却されていた。
  2. WebUI フロントエンド（`app.js` の `fetchAiModels`）が画面表示時に入力欄の `value`（`********`）を取得し、`/api/ai/models?provider=gemini&apiKey=********` としてそのままクエリパラメータで送信していた。
  3. バックエンド（`app/routers/ai.py` の `get_ai_models`）は `apiKey` パラメータが渡されるとそれを最優先で利用する仕様だったため、マスク文字列 `********` をそのまま Google Gemini API（または OpenAI API）に渡し、Google から `400: API key not valid` が返されていた。
- **防止策**: 
  1. バックエンドルーター（`app/routers/ai.py`）で、`apiKey` が渡された場合でもそれが空またはマスク値 `********` である場合は保存済みの本物のAPIキー（設定ファイルまたは環境変数）へ自動フォールバックする解決関数（`_resolve_key`）を実装した。
  2. サービス層（`app/services/ai_service.py`）でも多層防護として、`apiKey` が `********` の場合は外部APIへリクエストを送信せず安全にデフォルトリストやエラーを即時返却するようにした。
  3. フロントエンド（`public/app.js`）でも、入力値が `********` の場合はクエリパラメータやリクエストボディにキーを含めないようフィルタリングした。
  4. ユニットテスト（`tests/test_audit_fixes.py`）に `test_ai_models_mask_key_protection` を追加し、マスク文字列が渡された場合でも外部通信にマスク値が漏れず保存済みキーで動くことを自動テストで永続保証した。
## [2026-10-26 01] ヘッダー要素の折り返し防止(flex-wrap: nowrap)により要素幅超過時にブランドロゴ・タイトルとステータスチップが重なり重篤な表示崩れを起こした問題
- **事象**: DNDの動的な幅増加によるヘッダーの2段落ちを防ぐため、`.header-status` に `flex-wrap: nowrap` を適用したところ、画面幅に対して右側のチップ群（8個）の合計幅が大きすぎたため、左側のブランドロゴ・タイトル（`Smart Speaker Voice Hub`）の上に右側のチップ群が突き抜けて完全に重なってしまい、タイトルが判読不能になる重篤な表示崩れを発生させてしまった。
- **原因**: 
  1. ヘッダー内に固定的に表示されるべき静的な要素（ブランド、主要操作ボタン）と、動的に内容や幅が変動するステータスチップ群（サーバーIP、Cache、デフォルトスピーカー、DND状態・理由、ミュートボタン、ログアウト、バージョン、言語切替）が合計8個以上も存在し、1行の横幅キャパシティ（約 900px〜1000px）を根本的に超過していた。
  2. 構造的な要素分類（段分けやグループ化）を行わずに安易に `flex-wrap: nowrap` を設定したため、コンテナの `justify-content: space-between` で互いに押し合い、右側の要素が左側の要素へオーバーラップしてしまった。
- **防止策**: 
  1. ヘッダー内の要素をセマンティックかつ明確に「静的・主要エリア（1段目）」と「動的ステータス・詳細エリア（2段目）」に階層分離し、幅が変動する要素がタイトルやブランドロゴを侵食しない構造にする。
  2. CSSでの `flex-wrap: nowrap` 適用時は、各子要素の合計最大幅がコンテナの最小幅を超えないことを必ず検証し、幅変動要素には安全なレイアウト領域を割り当てる。

## [2026-10-26 02] 震度速報(ScalePrompt)受信時の震源地名空文字による「で最大震度」脱字および空文字部分一致による他地域地震の誤発報
- **事象**: 2026/10/26 23:35頃、熊本県天草・芦北で最大震度3の地震が発生した際、ユーザーの設定が「東京都・対象地域のみ（targetScope=local）」であったにもかかわらずスピーカーから「地震情報です。で最大震度3の地震が発生しました。」と場所が脱字した状態でアナウンスが実行され、ユーザーから「どこで？ｗ」と報告された。
- **原因**: 
  1. 気象庁およびP2P地震情報の第一報である「震度速報（ScalePrompt）」では震源地が未確定のため、API レスポンス内の `earthquake.hypocenter.name` が空文字列 `""` で送信される。
  2. バックエンド（`app/services/disaster_service.py`）で `hypocenter = eq.get("hypocenter", {}).get("name", "各地")` としていたが、キー `"name"` が存在し値が空文字 `""` だったため、`dict.get()` のデフォルト値 `"各地"` が無視され `hypocenter` が空文字列となった。その結果 `f"地震情報です。{hypocenter}で最大{scale_text}の地震が発生しました。"` が「地震情報です。で最大震度3の地震が発生しました。」と脱字を引き起こした。
  3. さらに、ローカル地域判定（`targetScope == "local"`）において、`if (target_pref in hypocenter or hypocenter in target_pref)` という条件式が存在していたが、`hypocenter` が空文字の場合、Python の仕様により `"" in target_pref`（`"" in "東京都"`）が常に `True` と評価されてしまい、東京都とは無関係な熊本県の地震がローカル判定をすり抜けて誤発報されていた。
- **防止策**: 
  1. `hypocenter.name` が空文字または None の場合、震度速報（`ScalePrompt`）の観測点配列 `points` から最大震度を観測した地域名（`addr` または `pref`）を自動抽出してアナウンス文章に組み込み、自然な日本語（「地震情報です。〇〇で最大震度Xの揺れを観測しました。」）を生成する。
  2. 万が一観測地点データが存在しない場合でも、`hypocenter_raw or "各地"` のように確実にフォールバックを効かせ、助詞「で」の手前が空欄になる文法破綻を完全に防止する。
  3. 文字列の部分一致（`in` 演算子）を行う際は、被検索文字列が非空であることを必ずチェック（`if hypocenter_raw and (target_pref in hypocenter_raw or hypocenter_raw in target_pref):`）し、空文字列による意図しない条件通過を徹底防御する。
  4. 同一地震の重複抑止キー（`event_key`）を `event_time` と `display_scale` を軸にしたキーとし、震度速報の後に震源情報（Destination）等が届いた場合でも同一震度であれば多重アナウンスされないよう改善した。
## [2026-10-27 01] GitHub Actionsのbash内インラインPythonで正規表現のエスケープ過多によるSyntaxErrorとCIビルド失敗
- **事象**: GitHub Actions ワークフロー（Build and Push Docker Image & Release）実行時、「Build and Push Docker Image」ジョブの `Get app version` ステップで `SyntaxError: closing parenthesis ']' does not match opening parenthesis '('` が発生し、Dockerイメージのビルド・プッシュおよびその後のGitHub Release作成ジョブが失敗・中断した。
- **原因**: 
  1. ワークフロー（`.github/workflows/docker-publish.yml`）内で `APP_VER=$(python3 -c "import re; m = re.search(r'__version__\s*=\s*[\"\\\']([^\"\\\']+)[\"\\\']', open('app/version.py').read()); print(m.group(1) if m else '')")` のように、bash のダブルクォート文字列の中でインライン Python コードに raw 文字列リテラル `r'...'` と多重エスケープ `\"\\\'` を埋め込んでいた。
  2. bash によりエスケープが展開された結果、Python の raw 文字列 `r'...'` 内で `\'` がシングルクォートのエスケープと認識され、文字列リテラルが閉じられずにパーサーが括弧の不整合を検知して SyntaxError となった。
  3. `app/version.py` は外部依存のない純粋な Python バージョン定義モジュール（`__version__ = "1.0.12"`）であるため、そもそも正規表現を文字列走査する必要がなく、`from app.version import __version__` で安全・直接に取得可能であった。
- **防止策**: 
  1. シェルスクリプトや CI ワークフロー定義内で Python のインライン実行（`python3 -c`）を行う際は、正規表現の複雑なエスケープを避け、Python の標準インポート構文 `python3 -c "from app.version import __version__; print(__version__)"` を使用する。
  2. バージョン取得や設定値抽出などの定型処理は、エスケープの衝突リスクがあるワンライナーではなく、モジュールの直接ロードか独立した検証済みスクリプトに委ねる。


## [2026-10-28 01] フロントエンドJS/JSONのキャッシュバスター(?v=)未更新による旧コード実行とプレースホルダー({SERVER_URL})未置換エラー
- **事象**: `index.html` と `app.js` に新しいワンライナー要素（`cmdWinAutostartEnable` 等）を追加した際、ブラウザでコピーしたコマンドに `--server {SERVER_URL}` が未置換のまま残り、PowerShell 上で `{SERVER_URL}` がスクリプトブロックとして解釈されて `error: argument --server: expected one argument` が発生した。
- **原因**:
  1. `public/index.html` 内の `<script src="app.js?v=1.0.22"></script>` や `i18n.js?v=1.0.5` のキャッシュバスター（`?v=`）を更新しなかったため、ブラウザが新しい `index.html` と古いキャッシュ済み `app.js` を組み合わせて実行し、新設した DOM ID（`cmdWinAutostartEnable` 等）の `{SERVER_URL}` 置換処理が走らなかった。
  2. また、ワンライナーの取得先 URL が GitHub の `raw.githubusercontent.com` 固定になっており、GitHub へ push する前のローカル改修内容がクライアント側から参照できなかった。
- **防止策**:
  1. `public/app.js`、`public/i18n.js`、`public/locales/*.json`、`public/style.css` を変更した際は、必ず `index.html` / `i18n.js` 内の `?v=` クエリパラメータも同時にインクリメントしてブラウザキャッシュを確実に無効化する。
  2. プレースホルダー（`{SERVER_URL}`）を含む DOM 要素は、`index.html` 直後のインラインスクリプト・`app.js` 初期化時・コピーボタン押下時の3段階で `window.location.origin` に置換する多重防御を行う。
  3. クライアント配布スクリプトは VoiceHub 自身の静的配信パス（`${serverUrl}/clients/speaker/...`）から直接取得するようにし、GitHub 未 push 時やローカル環境でも常にサーバーと同一バージョンのスクリプトが実行されるようにする。
