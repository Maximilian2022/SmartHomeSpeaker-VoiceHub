#!/usr/bin/env bash
set -e

echo "==================================================================="
echo "  🎙️ Smart Speaker VoiceHub - PC Speaker (Mac/Linux Launcher)"
echo "==================================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || pwd)"
if [ -f "$SCRIPT_DIR/voicehub_speaker.py" ]; then
    SPEAKER_SCRIPT="$SCRIPT_DIR/voicehub_speaker.py"
else
    mkdir -p "$HOME/.voicehub"
    SPEAKER_SCRIPT="$HOME/.voicehub/voicehub_speaker.py"
    SERVER_URL=""
    PREV=""
    for arg in "$@"; do
        if [ "$PREV" = "--server" ]; then
            SERVER_URL="${arg%/}"
            break
        fi
        PREV="$arg"
    done
    if [ -n "$SERVER_URL" ] && curl -fsSL "$SERVER_URL/clients/speaker/voicehub_speaker.py" -o "$SPEAKER_SCRIPT" 2>/dev/null; then
        :
    elif [ ! -f "$SPEAKER_SCRIPT" ]; then
        curl -fsSL "https://raw.githubusercontent.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/main/clients/speaker/voicehub_speaker.py" -o "$SPEAKER_SCRIPT"
    fi
fi

# 1. システム PATH またはローカルディレクトリの uv をチェック
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if command -v uv >/dev/null 2>&1; then
    exec uv run "$SPEAKER_SCRIPT" "$@"
fi

# 2. システム Python3 が直接使えるか
if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import httpx" >/dev/null 2>&1; then
        exec python3 "$SPEAKER_SCRIPT" "$@"
    fi
fi

# 3. uv も適切な Python 環境もない場合 -> uv の自動セットアップ
echo ""
echo "[*] Python / uv を自動セットアップしています (Zero-Setup)..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if command -v uv >/dev/null 2>&1; then
    echo ""
    echo "[OK] uv の自動セットアップが完了しました！VoiceHub Speaker を起動します..."
    echo ""
    exec uv run "$SPEAKER_SCRIPT" "$@"
else
    echo "[エラー] uv のインストールに失敗しました。"
    echo "手動で https://astral.sh/uv または Python をインストールしてください。"
    exit 1
fi
