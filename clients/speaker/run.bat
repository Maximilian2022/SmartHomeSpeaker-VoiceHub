@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

echo ===================================================================
echo   🎙️ Smart Speaker VoiceHub - PC Speaker (Windows Launcher)
echo ===================================================================

:: 1. システム PATH 上の uv をチェック
where uv >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    uv run voicehub_speaker.py %*
    exit /b %ERRORLEVEL%
)

:: 2. 一般的なローカルインストール先の uv をチェック
if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    uv run voicehub_speaker.py %*
    exit /b %ERRORLEVEL%
)
if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    uv run voicehub_speaker.py %*
    exit /b %ERRORLEVEL%
)

:: 3. Python が直接インストールされているかチェック
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Python を検出しました。起動を試みます...
    python voicehub_speaker.py %*
    if %ERRORLEVEL% EQU 0 exit /b 0
)

:: 4. uv も Python も見つからない場合 -> uv のワンクリック自動セットアップ
echo.
echo [!] Python または uv が見つかりませんでした。
echo     VoiceHub PC Speaker は、超高速ツール「uv」を利用することで、
echo     事前の Python 手動インストールなしで全自動で動作します。
echo.
set /p INSTALL_CHOICE="今すぐ uv を自動インストールしますか？ (推奨) [Y/n]: "
if /i "%INSTALL_CHOICE%"=="n" (
    echo 起動を中止しました。
    pause
    exit /b 1
)

echo.
echo [*] Astral 公式インストーラーから uv をダウンロード・配置しています...
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"

set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
where uv >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] uv の自動セットアップが完了しました！VoiceHub Speaker を起動します...
    echo.
    uv run voicehub_speaker.py %*
    exit /b %ERRORLEVEL%
) else (
    echo.
    echo [エラー] uv の自動インストールに失敗しました。
    echo 手動で https://astral.sh/uv または Python をインストールしてください。
    pause
    exit /b 1
)
