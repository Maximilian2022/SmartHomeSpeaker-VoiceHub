# 🎙️ VoiceHub PC Speaker Client

**Windows / Mac / Linux** のPC本体スピーカーや接続ヘッドホンから、VoiceHub のアナウンス音声を直接再生できる超軽量な常駐クライアントです。

作業中やテレワーク中、ゲーム中など、リビングのスマートスピーカーから離れていても、PCから直接クリアな音声通知を受け取ることができます。

---

## ✨ 主な特徴

- **圧倒的な軽快さと省メモリ**:
  - 常駐待機時のメモリ消費はわずか **約 15MB 〜 20MB**。
  - 待機中の CPU 使用率は **0.0%**。PCのパフォーマンスに一切影響を与えません。
- **事前の Python インストール不要 (Zero Setup) ＆ 自動アップデート対応**:
  - `uv` の自動ブートストラップ機構を内蔵しているため、**Python がインストールされていない初期状態の PC でも、Web UI のワンライナーまたは `run.bat` / `run.sh` を叩くだけで全自動でセットアップ** されます。
  - **クライアント自動アップデート (Auto Self-Update)**: VoiceHub サーバー側の `voicehub_speaker.py` が更新されると、接続中または再接続時に SHA-256 ハッシュを照合して自動的に最新スクリプトをダウンロード＆プロセス再起動します。
- **マルチオーディオ出力デバイスの個別検出・ON/OFF・メイン出力指定**:
  - 1台の PC に複数の物理スピーカー（例: `Logicool G560`、モニター内蔵スピーカー）や仮想オーディオデバイス（`SteelSeries Sonar` 等）が接続されている場合、全出力デバイスを自動検出して VoiceHub に個別登録します。
  - VoiceHub の Web 画面（設定 ＞ スマートホーム連携 ＞ PC スピーカー連携）の **「🔊 接続中 PC の出力スピーカー管理」** パネルから、不要な出力デバイスの **有効/無効 (ON/OFF)** 切り替えや、`ALL` / `PC:ALL` 一斉放送時に鳴らす **「⭐ メイン出力」** の指定がワンクリックで行えます。
- **NAT・ファイアウォール完全スルー**:
  - PC から VoiceHub サーバーへの外向き HTTP (SSE: Server-Sent Events) 接続のみで通信。ルーターのポート開放や Windows Defender Firewall の警告に悩まされません。
- **自動オンライン認識（動的ディスカバリ）**:
  - スクリプトを起動すると、VoiceHub の Web 画面に **「💻 PC名 (出力デバイス名)」が自動的に出現** します。
  - PC をシャットダウンしたりスリープすると自動的にオフライン扱いになり、不在時のエラーを防ぎます。
- **家中一斉放送 ＆ 個別出力指定に対応**:
  - `devices: ["ALL"]`（家中一斉）や `devices: ["PC:ALL"]` では、各 PC の **「⭐ メイン出力」1台のみ** が鳴ります（PC内の複数スピーカーから同時に鳴るのを防止）。
  - 個別指定（例: `devices: ["My-Windows-PC (SteelSeries Sonar - Gaming)"]`）では、有効な任意のスピーカーやヘッドセットを個別に鳴らせます。
- **ワンライナー＆ワンクリック自動起動（完全画面非表示常駐）**:
  - Web UI 上に **①一時起動、②自動起動（常駐化）、③自動起動の解除** の3種類のワンライナーを用意。
  - Windows では黒いコマンドプロンプト画面を出さずに即時バックグラウンド常駐を開始し、次回PC起動時からも自動常駐します。macOS (LaunchAgents) や Linux (`systemd --user`) にも完全対応しています。

---

## 🚀 クイックスタート (使い方)

### 🪟 Windows の場合

1. `clients/speaker/` フォルダを開きます。
2. **`run.bat`** をダブルクリックして起動します。
   *(※初回起動時、Python/uv がない環境では自動セットアップの確認メッセージが表示されますので「Y」を押すだけで自動完了します)*
3. サーバーURLを指定したい場合は、コマンドプロンプトやショートカットから以下のように引数を渡せます：
   ```cmd
   run.bat --server http://192.168.1.100:8080 --name "自室PC"
   ```

### 🍎 macOS の場合

ターミナルを開き、以下のコマンドを実行します：

```bash
cd clients/speaker
./run.sh --server http://192.168.1.100:8080 --name "MacBook"
```
*(※macOS 標準の `afplay` を使用するため、外部音声ライブラリ不要で極めて低遅延・高音質に再生されます)*

### 🐧 Linux の場合

```bash
cd clients/speaker
./run.sh --server http://192.168.1.100:8080 --name "Linux-Desktop"
```

---

## ⚙️ PC起動時の自動起動（常駐化）

「毎回手動で起動するのではなく、PCを起動したら勝手に裏で待機していてほしい」という場合は、ワンクリックで自動起動を登録できます。

### Windows
- **自動起動を有効化**: **`enable_autostart.bat`** をダブルクリック
  - スタートアップに登録されます。**黒いコンソール画面は一切表示されず**、タスクマネージャーの裏で完全に無音・無画面で常駐します。
- **自動起動を解除**: **`disable_autostart.bat`** をダブルクリック

### macOS
- **自動起動を有効化**: `./enable_autostart.sh --server http://<VoiceHubのIP>:8080`
  - `~/Library/LaunchAgents` に登録され、ログイン時に自動常駐します。
- **自動起動を解除**: `./disable_autostart.sh`

### Linux
- **自動起動を有効化**: `./enable_autostart.sh --server http://<VoiceHubのIP>:8080`
  - `systemd --user` サービスとして登録・常駐化されます。
- **自動起動を解除**: `./disable_autostart.sh`

---

## 🛠️ コマンドライン引数リファレンス

直接 `uv run voicehub_speaker.py` または `run.bat` / `run.sh` に渡せる引数一覧です：

| オプション | デフォルト値 | 説明 |
| :--- | :--- | :--- |
| `--server` | `http://localhost:8080` | VoiceHub サーバーのベース URL |
| `--name` | ホスト名 | VoiceHub の Web UI や API 上に表示されるスピーカー名 |
| `--id` | 自動生成 | 一意のクライアント識別子（省略時はホスト名から生成） |
| `--token` | なし | VoiceHub で Webhook トークンまたは管理者パスワードを設定している場合の認証キー |
| `--autostart` | なし | `enable`（自動起動登録）/ `disable`（登録解除）/ `status`（状態確認） |

---

## 📣 Webhook や API から呼び出す例

PC クライアントが接続されると、VoiceHub の通常スピーカーと同様に cURL や Webhook から指定できます：

```bash
# PC だけに喋らせる例
curl -X POST http://<サーバーIP>:8080/api/say \
  -H "Content-Type: application/json" \
  -d '{
    "text": "作業お疲れ様です。少し休憩しませんか？",
    "devices": ["My-Windows-PC"]
  }'

# 接続中の全PCスピーカーにまとめて喋らせるマクロ
curl -X POST http://<サーバーIP>:8080/api/say \
  -H "Content-Type: application/json" \
  -d '{
    "text": "PCスピーカー全台へのテスト通知です",
    "devices": ["PC:ALL"]
  }'
```
