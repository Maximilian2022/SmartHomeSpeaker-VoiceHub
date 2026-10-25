import os
import shutil
import tempfile
import pytest

_test_tmp_dir = tempfile.mkdtemp(prefix="voicehub_test_")
_test_data_dir = os.path.join(_test_tmp_dir, "data")
_test_logs_dir = os.path.join(_test_tmp_dir, "logs")
os.makedirs(_test_data_dir, exist_ok=True)
os.makedirs(_test_logs_dir, exist_ok=True)

os.environ["VOICEHUB_DATA_DIR"] = _test_data_dir
os.environ["VOICEHUB_LOG_DIR"] = _test_logs_dir

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_env():
    yield
    shutil.rmtree(_test_tmp_dir, ignore_errors=True)
