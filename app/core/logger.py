import logging
import sys
from app.core.log_rotator import get_container_log_handler, StdStreamTee

# VoiceHub 共通ログフォーマット
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 1. コンソール出力ハンドラー
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

# 2. コンテナログファイル (/logs/container.log) ローテーションハンドラー
file_handler = get_container_log_handler()
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

# ルートロガー設定
logger = logging.getLogger("VoiceHub")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
logger.propagate = False


def get_logger(module_name: str) -> logging.Logger:
    """モジュール別のロガーを取得 (例: get_logger('TTS'))"""
    mod_logger = logging.getLogger(f"VoiceHub.{module_name}")
    mod_logger.setLevel(logging.INFO)
    if not mod_logger.handlers:
        mod_logger.addHandler(console_handler)
        mod_logger.addHandler(file_handler)
    mod_logger.propagate = False
    return mod_logger


_system_logging_initialized = False


def init_system_logging():
    """システム全体のロギング初期化 (Uvicorn, 標準出力キャプチャの統合)"""
    global _system_logging_initialized
    if _system_logging_initialized:
        return
    _system_logging_initialized = True

    # Uvicorn のロガーにファイルハンドラーを追加
    for uvicorn_log_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        u_logger = logging.getLogger(uvicorn_log_name)
        if file_handler not in u_logger.handlers:
            u_logger.addHandler(file_handler)

    # 標準出力・標準エラー出力を TeeStream でラップして container.log にも書き込む
    # (二重ラップを防止するため、型をチェック)
    if not isinstance(sys.stdout, StdStreamTee):
        sys.stdout = StdStreamTee(sys.stdout, file_handler, prefix="")
    if not isinstance(sys.stderr, StdStreamTee):
        sys.stderr = StdStreamTee(sys.stderr, file_handler, prefix="[STDERR] ")
