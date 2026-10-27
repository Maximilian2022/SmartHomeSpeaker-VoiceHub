# 🎙️ VoiceHub PC Speaker Client

**Windows / Mac / Linux** のPC本体スピーカーや接続ヘッドホンから、VoiceHub のアナウンス音声を直接再生できる超軽量な常駐クライアントです。

作業中やテレワーク中、ゲーム中など、リビングのスマートスピーカーから離れていても、PCから直接クリアな音声通知を受け取ることができます。

---

## ✨ 主な特徴

- **圧倒的な軽快さと省メモリ**:
  - 常駐待機時のメモリ消費はわずか **約 15MB 〜 20MB**。
  - 待機中の CPU 使用率は **0.0%**。PCのパフォーマンスに一切影響を与えません。
- **事前の Python インストール不要 (Zero Setup)**:
  - `uv` の自動ブートストラップ機構を内蔵しているため、**Python がインストールされていない初期状態の PC でも、`run.bat` / `run.sh` を叩くだけで全自動でセットアップ** されます。
- **NAT・ファイアウォール完全スルー**:
  - PC から VoiceHub サーバーへの外向き HTTP (SSE: Server-Sent Events) 接続のみで通信。ルーターのポート開放や Windows Defender Firewall の警告に悩まされません。
- **自動オンライン認識（動的ディスカバリ）**:
  - スクリプトを起動すると、VoiceHub の Web 画面に **「💻 PC名」が自動的に出現** します。
  - PC をシャットダウンしたりスリープすると自動的にオフライン扱いになり、不在時のエラーを防ぎます。
- **家中一斉放送 ＆ 個別指定に対応**:
  - `devices: ["ALL"]`（家中一斉）での同時アナウンスはもちろん、`devices: ["My-Windows-PC"]` や `devices: ["PC:ALL"]` による個別呼び出しも可能です。
- **ワンクリック自動起動（完全画面非表示常駐）**:
  - Windows では黒いコマンドプロンプト画面を出さずにバックグラウンド常駐する VBScript を自動生成。
  - macOS (LaunchAgents) や Linux (systemd) のログイン時自動起動にも完全対応しています。

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
