@echo off
setlocal
cd /d "%~dp0"

echo ===================================================================
echo   🛑 VoiceHub PC Speaker - 自動起動の解除
echo ===================================================================
echo.
set /p CLEAN="ローカル設定・キャッシュフォルダ (~/.voicehub) も完全に削除しますか？ [y/N]: "
if /i "%CLEAN%"=="y" (
    call run.bat --autostart disable --clean %*
) else (
    call run.bat --autostart disable %*
)
pause
