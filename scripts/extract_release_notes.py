#!/usr/bin/env python3
"""
scripts/extract_release_notes.py
logs/remediation_history.md (または CHANGELOG.md) から最新の変更履歴を抽出し、
GitHub Release 用の完全日本語リリースノート (Markdown) を生成する。
"""

import sys
import os
import re
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub"

def get_version() -> str:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        ver = sys.argv[1].strip()
        return ver if ver.startswith("v") else f"v{ver}"
    
    # app/version.py から取得
    version_file = BASE_DIR / "app" / "version.py"
    if version_file.exists():
        content = version_file.read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            ver = match.group(1).strip()
            return ver if ver.startswith("v") else f"v{ver}"
    return "v1.0.0"

def convert_local_links(text: str) -> str:
    """ローカル絶対パスリンク (file:///root/google-home-voicetext-docker/...) を GitHub blob URL に変換"""
    # 例: [app/services/foo.py](file:///root/google-home-voicetext-docker/app/services/foo.py#L12)
    #  -> [app/services/foo.py](https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/blob/main/app/services/foo.py#L12)
    pattern = r"file:///root/google-home-voicetext-docker/([^)\s]+)"
    replacement = rf"{REPO_URL}/blob/main/\1"
    return re.sub(pattern, replacement, text)

def extract_latest_remediation() -> str:
    history_file = BASE_DIR / "logs" / "remediation_history.md"
    if not history_file.exists():
        return ""
    
    lines = history_file.read_text(encoding="utf-8").splitlines()
    entry_lines = []
    found_first_h2 = False

    for line in lines:
        if line.startswith("## "):
            if found_first_h2:
                # 2つ目の ## が来たら終了
                break
            found_first_h2 = True
            entry_lines.append(line)
        elif found_first_h2:
            entry_lines.append(line)

    raw_text = "\n".join(entry_lines).strip()
    return convert_local_links(raw_text)

def extract_changelog_fallback(version_clean: str) -> str:
    """CHANGELOG.md から指定バージョンのセクションを抽出 (フォールバック用)"""
    changelog_file = BASE_DIR / "CHANGELOG.md"
    if not changelog_file.exists():
        return ""
    
    lines = changelog_file.read_text(encoding="utf-8").splitlines()
    entry_lines = []
    found_target = False

    for line in lines:
        if line.startswith("## "):
            if version_clean in line:
                found_target = True
                continue
            elif found_target:
                break
        elif found_target:
            entry_lines.append(line)

    return "\n".join(entry_lines).strip()

def get_git_commits() -> str:
    """直前のタグからのコミット一覧を取得"""
    try:
        # 最新のタグを取得
        latest_tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0", "HEAD^"],
            cwd=str(BASE_DIR), stderr=subprocess.DEVNULL, text=True
        ).strip()
        cmd = ["git", "log", f"{latest_tag}..HEAD", "--oneline", "--no-merges"]
    except Exception:
        cmd = ["git", "log", "-n", "10", "--oneline", "--no-merges"]

    try:
        out = subprocess.check_output(cmd, cwd=str(BASE_DIR), stderr=subprocess.DEVNULL, text=True).strip()
        if not out:
            return ""
        formatted = []
        for line in out.splitlines():
            parts = line.split(" ", 1)
            if len(parts) == 2:
                commit_hash, msg = parts
                commit_url = f"{REPO_URL}/commit/{commit_hash}"
                formatted.append(f"- [`{commit_hash}`]({commit_url}) {msg}")
            else:
                formatted.append(f"- {line}")
        return "\n".join(formatted)
    except Exception:
        return ""

def build_release_notes(version: str, changelog_text: str) -> str:
    version_clean = version.lstrip("vV")
    lines = []
    lines.append(f"## 🚀 VoiceHub {version} リリース")
    lines.append("")

    if not changelog_text:
        changelog_text = extract_changelog_fallback(version_clean)

    if changelog_text:
        lines.append("### 📋 主な改修・アップデート内容")
        lines.append("")
        c_lines = changelog_text.splitlines()
        if c_lines and c_lines[0].startswith("## "):
            title_line = c_lines[0].lstrip("#").strip()
            parts = title_line.split(" - ", 1)
            if len(parts) == 2:
                lines.append(f"**【{parts[0].strip()}】{parts[1].strip()}**")
            else:
                lines.append(f"**{title_line}**")
            lines.append("")
            body = "\n".join(c_lines[1:]).strip()
            if body:
                lines.append(body)
        else:
            lines.append(changelog_text)
    else:
        lines.append("本バージョンの変更履歴はリポジトリのコミットログをご確認ください。")

    # コミットログ
    git_commits = get_git_commits()
    if git_commits:
        lines.append("")
        lines.append("### 📝 コミット履歴")
        lines.append(git_commits)

    lines.append("")
    lines.append("---")
    lines.append("### 🐳 Docker イメージの更新・取得")
    lines.append("```bash")
    lines.append("docker pull madpiero/smarthomespeaker-voicehub:latest")
    lines.append(f"docker pull madpiero/smarthomespeaker-voicehub:{version}")
    lines.append("```")
    lines.append("")

    return "\n".join(lines).strip() + "\n"

def main():
    version = get_version()
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else BASE_DIR / "release_notes.md"

    changelog_text = extract_latest_remediation()
    notes = build_release_notes(version, changelog_text)

    output_path.write_text(notes, encoding="utf-8")
    print(f"✅ Generated release notes for {version} -> {output_path}")

if __name__ == "__main__":
    main()
