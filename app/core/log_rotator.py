import os
import sys
import time
import shutil
import logging
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# ログディレクトリとファイル定義
LOG_DIR = Path("/logs")
ACTIVE_LOG_FILE = LOG_DIR / "container.log"
ARCHIVE_LOG_FILE = LOG_DIR / "container-archive.log"

MAX_ACTIVE_LINES = 1000
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024  # 100MB
MAX_ARCHIVE_GENERATIONS = 10


def compress_file_zstd(src_path: Path, dest_path: Path) -> bool:
    """ファイルを zstd で圧縮する（Pythonモジュール優先、コマンドラインフォールバック）"""
    try:
        import zstandard as zstd  # type: ignore
        cctx = zstd.ZstdCompressor(level=3)
        with open(src_path, "rb") as f_in, open(dest_path, "wb") as f_out:
            cctx.copy_stream(f_in, f_out)
        return True
    except ImportError:
        pass
    except Exception as e:
        sys.__stderr__.write(f"[LogRotator] zstandard python compression error: {e}\n")

    # システムの zstd コマンドによるフォールバック
    zstd_bin = shutil.which("zstd")
    if zstd_bin:
        try:
            import subprocess
            res = subprocess.run(
                [zstd_bin, "-3", "-f", "-q", str(src_path), "-o", str(dest_path)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return True
        except Exception as e:
            sys.__stderr__.write(f"[LogRotator] zstd command compression error: {e}\n")

    # 万一 zstd が利用できない場合の gzip フォールバック (安全策)
    try:
        import gzip
        dest_gz = src_path.with_name(f"{src_path.name}.gz")
        with open(src_path, "rb") as f_in, gzip.open(dest_gz, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)
        return True
    except Exception as e:
        sys.__stderr__.write(f"[LogRotator] gzip fallback compression error: {e}\n")
        return False


class ContainerLogHandler(logging.Handler):
    """
    VoiceHub 専用コンソール・コンテナログローテーションハンドラ
    - /logs/container.log に出力
    - 行数が 1000 行を超えるか、日付が変わったら container-archive.log に移動（退避追記）
    - container-archive.log が 100MB を超えたら zstd 圧縮して最大 10 世代保持
    """

    def __init__(self, log_dir: Path = LOG_DIR):
        super().__init__()
        self.log_dir = log_dir
        self.active_file = log_dir / "container.log"
        self.archive_file = log_dir / "container-archive.log"
        self.lock = threading.RLock()
        
        # ディレクトリ準備
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            sys.__stderr__.write(f"[LogRotator] Failed to create log dir: {e}\n")

        self._current_date = date.today()
        self._current_line_count = self._count_lines_safe(self.active_file)
        self._file_stream = None
        self._open_active_file()

    def _open_active_file(self):
        try:
            if self._file_stream and not self._file_stream.closed:
                self._file_stream.close()
            self._file_stream = open(self.active_file, "a", encoding="utf-8", errors="replace", buffering=1)
        except Exception as e:
            sys.__stderr__.write(f"[LogRotator] Failed to open {self.active_file}: {e}\n")
            self._file_stream = None

    def _count_lines_safe(self, path: Path) -> int:
        if not path.exists():
            return 0
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record) + "\n"
            self.write_raw(msg)
        except Exception:
            self.handleError(record)

    def write_raw(self, text: str):
        """生のテキスト行を container.log に書き込み、条件を満たせばローテーション"""
        with self.lock:
            # 日付変更または行数オーバーの事前チェック
            today = date.today()
            if today != self._current_date or self._current_line_count >= MAX_ACTIVE_LINES:
                self._rotate_active_to_archive()

            if not self._file_stream or self._file_stream.closed:
                self._open_active_file()

            if self._file_stream:
                try:
                    self._file_stream.write(text)
                    self._file_stream.flush()
                    # 改行数を加算
                    lines_in_text = text.count("\n")
                    self._current_line_count += max(1, lines_in_text)
                except Exception as e:
                    sys.__stderr__.write(f"[LogRotator] Write failed: {e}\n")

            # 書き込み後に行数が 1000 行に達していたらローテーション
            if self._current_line_count >= MAX_ACTIVE_LINES:
                self._rotate_active_to_archive()

    def _rotate_active_to_archive(self):
        """container.log を container-archive.log に追記移動し、container.log を空にする"""
        try:
            if self._file_stream and not self._file_stream.closed:
                self._file_stream.flush()
                self._file_stream.close()
                self._file_stream = None

            if self.active_file.exists() and self.active_file.stat().st_size > 0:
                # container-archive.log にアペンド
                with open(self.active_file, "rb") as f_src, open(self.archive_file, "ab") as f_dst:
                    shutil.copyfileobj(f_src, f_dst)
                
                # container.log を空で再作成
                with open(self.active_file, "wb") as f_trunc:
                    f_trunc.truncate(0)

            self._current_line_count = 0
            self._current_date = date.today()
            self._open_active_file()

            # アーカイブが 100MB を超えていれば圧縮ローテーションを実行
            self._check_archive_rotation()
        except Exception as e:
            sys.__stderr__.write(f"[LogRotator] Active rotation error: {e}\n")
            self._open_active_file()

    def _check_archive_rotation(self):
        """container-archive.log が 100MB を超えたら zstd 圧縮して世代管理"""
        try:
            if not self.archive_file.exists():
                return
            
            archive_size = self.archive_file.stat().st_size
            if archive_size < MAX_ARCHIVE_BYTES:
                return

            # 世代ローテーション (10世代保持)
            # 10世代目のファイルを削除
            gen10 = self.log_dir / f"container-archive.log.{MAX_ARCHIVE_GENERATIONS}.zst"
            if gen10.exists():
                try:
                    gen10.unlink()
                except Exception:
                    pass

            # 9 -> 10, 8 -> 9, ... 1 -> 2
            for i in range(MAX_ARCHIVE_GENERATIONS - 1, 0, -1):
                src = self.log_dir / f"container-archive.log.{i}.zst"
                dst = self.log_dir / f"container-archive.log.{i + 1}.zst"
                if src.exists():
                    try:
                        src.rename(dst)
                    except Exception:
                        pass

            # container-archive.log を container-archive.log.1.zst に圧縮
            dest_gen1 = self.log_dir / "container-archive.log.1.zst"
            success = compress_file_zstd(self.archive_file, dest_gen1)
            if success:
                # 圧縮成功したら archive を空にする
                with open(self.archive_file, "wb") as f_trunc:
                    f_trunc.truncate(0)
            else:
                sys.__stderr__.write("[LogRotator] Failed to compress archive, keeping raw file\n")
        except Exception as e:
            sys.__stderr__.write(f"[LogRotator] Archive compression rotation error: {e}\n")

    def manual_flush_archive(self):
        """手動で現在の container.log をアーカイブにフラッシュする"""
        with self.lock:
            self._rotate_active_to_archive()

    def close(self):
        with self.lock:
            if self._file_stream and not self._file_stream.closed:
                try:
                    self._file_stream.flush()
                    self._file_stream.close()
                except Exception:
                    pass
                self._file_stream = None
        super().close()


# シングルトンハンドラーインスタンス
_container_handler: Optional[ContainerLogHandler] = None
_handler_lock = threading.Lock()


def get_container_log_handler() -> ContainerLogHandler:
    global _container_handler
    if _container_handler is None:
        with _handler_lock:
            if _container_handler is None:
                _container_handler = ContainerLogHandler()
    return _container_handler


class StdStreamTee:
    """標準出力/標準エラー出力を元のストリームに出しながら container.log にも書き込むラッパー"""

    def __init__(self, original_stream, handler: ContainerLogHandler, prefix: str = ""):
        self.original_stream = original_stream
        self.handler = handler
        self.prefix = prefix

    def write(self, data: str):
        if self.original_stream:
            self.original_stream.write(data)
        if data:
            self.handler.write_raw(data)

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()

    def fileno(self):
        if hasattr(self.original_stream, "fileno"):
            return self.original_stream.fileno()
        raise OSError("fileno not supported")

    def isatty(self):
        if hasattr(self.original_stream, "isatty"):
            return self.original_stream.isatty()
        return False
