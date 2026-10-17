import logging
import sys

# VoiceHub 共通ロガー設定
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

logger = logging.getLogger("VoiceHub")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(handler)
logger.propagate = False

def get_logger(module_name: str) -> logging.Logger:
    mod_logger = logging.getLogger(f"VoiceHub.{module_name}")
    mod_logger.setLevel(logging.INFO)
    if not mod_logger.handlers:
        mod_logger.addHandler(handler)
    mod_logger.propagate = False
    return mod_logger
