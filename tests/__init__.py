import os
import atexit
import shutil
import tempfile
from pathlib import Path

# テスト実行時の本番データ保護用一時ディレクトリ
_test_tmp_dir = tempfile.mkdtemp(prefix="voicehub_test_")
_test_data_dir = os.path.join(_test_tmp_dir, "data")
_test_logs_dir = os.path.join(_test_tmp_dir, "logs")
os.makedirs(_test_data_dir, exist_ok=True)
os.makedirs(_test_logs_dir, exist_ok=True)

# 環境変数を上書き（app インポート前に最優先で設定）
os.environ["VOICEHUB_DATA_DIR"] = _test_data_dir
os.environ["VOICEHUB_LOG_DIR"] = _test_logs_dir

def _cleanup():
    try:
        shutil.rmtree(_test_tmp_dir, ignore_errors=True)
    except Exception:
        pass

atexit.register(_cleanup)
