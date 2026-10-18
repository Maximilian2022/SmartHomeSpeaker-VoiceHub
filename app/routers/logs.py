import re
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse
from app.core.log_rotator import (
    LOG_DIR,
    ACTIVE_LOG_FILE,
    ARCHIVE_LOG_FILE,
    MAX_ACTIVE_LINES,
    MAX_ARCHIVE_BYTES,
    MAX_ARCHIVE_GENERATIONS,
    get_container_log_handler,
)
from app.core.logger import get_logger

router = APIRouter(prefix="/api/logs", tags=["Logs"])
log = get_logger("LogsAPI")

# ログ行の正規表現パターン: [2026-10-19 00:15:30] [INFO] [VoiceHub.TTS] Message...
LOG_LINE_REGEX = re.compile(
    r"^\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+\[(?P<level>[A-Z]+)\]\s+(?:\[VoiceHub\.(?P<module>[^\]]+)\]|\[(?P<alt_module>[^\]]+)\])?\s*(?P<message>.*)$"
)


def parse_log_line(line_num: int, raw_line: str) -> Dict[str, Any]:
    """1行のログテキストを解析して構造化データを生成"""
    raw_clean = raw_line.rstrip("\r\n")
    match = LOG_LINE_REGEX.match(raw_clean)
    if match:
        groups = match.groupdict()
        module = groups.get("module") or groups.get("alt_module") or "SYSTEM"
        return {
            "line_num": line_num,
            "timestamp": groups["timestamp"],
            "level": groups["level"],
            "module": module,
            "message": groups["message"],
            "raw": raw_clean,
        }
    else:
        # パースできない行 (スタックトレースや生ログ)
        level = "INFO"
        upper = raw_clean.upper()
        if "ERROR" in upper or "TRACEBACK" in upper or "EXCEPTION" in upper:
            level = "ERROR"
        elif "WARN" in upper:
            level = "WARNING"

        return {
            "line_num": line_num,
            "timestamp": "",
            "level": level,
            "module": "CONSOLE",
            "message": raw_clean,
            "raw": raw_clean,
        }


def read_tail_lines(file_path: Path, max_lines: int) -> List[str]:
    """ファイルの末尾から指定行数を高速に読み込む（大容量ファイルでも安全）"""
    if not file_path.exists() or max_lines <= 0:
        return []

    try:
        file_size = file_path.stat().st_size
        if file_size == 0:
            return []

        # 1MB 以下の小容量なら通常読み込み
        if file_size < 1024 * 1024:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                return lines[-max_lines:]

        # 1MB 以上の大容量ファイルは末尾から逆シークして必要な行数を取得
        buffer_size = 64 * 1024  # 64KB
        with open(file_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            position = f.tell()
            remaining_bytes = position
            accumulated_bytes = bytearray()

            while remaining_bytes > 0:
                read_size = min(buffer_size, remaining_bytes)
                position -= read_size
                f.seek(position)
                chunk = f.read(read_size)
                accumulated_bytes = chunk + accumulated_bytes
                remaining_bytes -= read_size

                # 改行数が max_lines より多ければ十分
                if accumulated_bytes.count(b"\n") >= max_lines + 1:
                    break

            text = accumulated_bytes.decode("utf-8", errors="replace")
            lines = text.splitlines(keepends=True)
            return lines[-max_lines:]
    except Exception as e:
        log.warning(f"Failed to read tail of {file_path}: {e}")
        return []


@router.get("", response_model=Dict[str, Any])
async def get_logs(
    limit: int = Query(default=500, ge=1, le=1000, description="取得する最大行数 (最大1000)"),
    level: Optional[str] = Query(default=None, description="フィルターするログレベル (INFO, WARNING, ERROR 等)"),
    module: Optional[str] = Query(default=None, description="フィルターするモジュール名"),
    search: Optional[str] = Query(default=None, description="検索キーワード (大文字小文字無視)"),
):
    """
    アクティブコンテナログ (/logs/container.log) の末尾からログ行を取得。
    行数が limit 未満の場合は /logs/container-archive.log から直近末尾をシームレスに結合して返却。
    """
    active_lines: List[str] = []
    if ACTIVE_LOG_FILE.exists():
        try:
            with open(ACTIVE_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                active_lines = f.readlines()
        except Exception as e:
            log.warning(f"Failed to read {ACTIVE_LOG_FILE}: {e}")

    total_active_lines = len(active_lines)
    file_size = ACTIVE_LOG_FILE.stat().st_size if ACTIVE_LOG_FILE.exists() else 0
    last_updated = (
        datetime.fromtimestamp(ACTIVE_LOG_FILE.stat().st_mtime).isoformat()
        if ACTIVE_LOG_FILE.exists()
        else datetime.now().isoformat()
    )

    # アーカイブ情報
    archive_size = ARCHIVE_LOG_FILE.stat().st_size if ARCHIVE_LOG_FILE.exists() else 0
    archive_generations = sum(1 for p in LOG_DIR.glob("container-archive.log.*.zst"))

    # シームレス連携: active_lines が limit に満たない場合、archive から末尾を補充
    needed_from_archive = max(0, limit - total_active_lines)
    archive_lines: List[str] = []
    if needed_from_archive > 0 and ARCHIVE_LOG_FILE.exists():
        archive_lines = read_tail_lines(ARCHIVE_LOG_FILE, needed_from_archive)

    # 合成行リスト (古い順: archive_lines + active_lines)
    combined_lines = archive_lines + active_lines

    # 解析とフィルタリング
    parsed_lines = []
    level_filter = level.upper() if level and level.upper() != "ALL" else None
    module_filter = module.upper() if module and module.upper() != "ALL" else None
    search_filter = search.lower() if search else None

    # 末尾から limit 件に収まるよう探索
    for idx, raw_line in enumerate(combined_lines, start=1):
        parsed = parse_log_line(idx, raw_line)

        # レベルフィルタ (WARNING は WARN も一致)
        if level_filter:
            p_lvl = parsed["level"]
            if level_filter == "WARN" and p_lvl == "WARNING":
                pass
            elif level_filter == "WARNING" and p_lvl == "WARN":
                pass
            elif p_lvl != level_filter:
                continue

        # モジュールフィルタ
        if module_filter:
            if module_filter not in parsed["module"].upper():
                continue

        # キーワード検索
        if search_filter:
            if search_filter not in parsed["raw"].lower():
                continue

        parsed_lines.append(parsed)

    # 最新 limit 件を取得
    if len(parsed_lines) > limit:
        parsed_lines = parsed_lines[-limit:]

    return {
        "lines": parsed_lines,
        "total_lines": total_active_lines,
        "seamless_total": len(combined_lines),
        "is_seamless": len(archive_lines) > 0,
        "max_lines": MAX_ACTIVE_LINES,
        "file_size": file_size,
        "archive_size": archive_size,
        "archive_generations": archive_generations,
        "last_updated": last_updated,
    }


@router.get("/download")
async def download_log(target: str = Query(default="current", description="ダウンロード対象: current, archive, compressed")):
    """ログファイルをダウンロード"""
    if target == "current":
        if not ACTIVE_LOG_FILE.exists() or ACTIVE_LOG_FILE.stat().st_size == 0:
            return Response(content="ログファイルは空です。", media_type="text/plain; charset=utf-8")
        return FileResponse(
            path=str(ACTIVE_LOG_FILE),
            filename="VoiceHub-container.log",
            media_type="text/plain; charset=utf-8",
        )
    elif target == "archive":
        if not ARCHIVE_LOG_FILE.exists() or ARCHIVE_LOG_FILE.stat().st_size == 0:
            return Response(content="アーカイブログファイルは空です。", media_type="text/plain; charset=utf-8")
        return FileResponse(
            path=str(ARCHIVE_LOG_FILE),
            filename="VoiceHub-container-archive.log",
            media_type="text/plain; charset=utf-8",
        )
    elif target == "compressed":
        gen1 = LOG_DIR / "container-archive.log.1.zst"
        if not gen1.exists():
            raise HTTPException(status_code=404, detail="圧縮アーカイブファイル (zst) はまだ作成されていません。")
        return FileResponse(
            path=str(gen1),
            filename="VoiceHub-container-archive.log.1.zst",
            media_type="application/octet-stream",
        )
    else:
        raise HTTPException(status_code=400, detail="不正な target です (current, archive, compressed のいずれか)")


@router.delete("", response_model=Dict[str, Any])
async def clear_logs():
    """
    現在の container.log をアーカイブにフラッシュ退避し、アクティブログを即時クリアする
    """
    handler = get_container_log_handler()
    handler.manual_flush_archive()
    log.info("Active log (container.log) was manually rotated and flushed to archive.")
    return {"success": True, "message": "現在のログをアーカイブへ退避し、アクティブログをクリアしました。"}
