#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "==================================================================="
echo "  🎙️ Smart Speaker VoiceHub - PC Speaker (Mac/Linux Launcher)"
echo "==================================================================="

# 1. システム PATH 上の uv
if command -v uv >/dev/null 2>&1; then
    exec uv run voicehub_speaker.py "$@"
fi

# 2. ローカルディレクトリの uv
if [ -f "$HOME/.local/bin/uv" ]; then
    export PATH="$HOME/.local/bin:$PATH"
    exec uv run voicehub_speaker.py "$@"
elif [ -f "$HOME/.cargo/bin/uv" ]; then
    export PATH="$HOME/.cargo/bin:$PATH"
    exec uv run voicehub_speaker.py "$@"
fi

# 3. システム Python3 が直接使えるか
if command -v python3 >/dev/null 2>&1; then
    # 依存ライブラリの確認
    if python3 -c "import httpx" >/dev/null 2>&1; then
        exec python3 voicehub_speaker.py "$@"
    fi
fi

# 4. uv も適切な Python 環境もない場合 -> uv の自動セットアップ案内
echo ""
echo "[!] Python または uv が見つかりませんでした。"
echo "    VoiceHub PC Speaker は、超高速ツール「uv」を利用することで、"
echo "    事前の Python 手動インストールなしで全自動で動作します。"
echo ""
read -p "今すぐ uv を自動インストールしますか？ (推奨) [Y/n]: " yn
case "$yn" in
    [nN]*)
        echo "起動を中止しました。"
        exit 1
        ;;
    *)
        echo ""
        echo "[*] Astral 公式インストーラーから uv をインストールしています..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
        if command -v uv >/dev/null 2>&1; then
            echo ""
            echo "[OK] uv の自動セットアップが完了しました！VoiceHub Speaker を起動します..."
            echo ""
            exec uv run voicehub_speaker.py "$@"
        else
            echo "[エラー] uv のインストールに失敗しました。"
            echo "手動で https://astral.sh/uv または Python をインストールしてください。"
            exit 1
        fi
        ;;
esac
