import asyncio
import re
import time
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from app.version import __version__, GITHUB_RELEASES_API, GITHUB_RELEASES_URL
from app.services.settings_service import settings_manager
from app.core.logger import logger

def parse_semver(v_str: str) -> Tuple[int, ...]:
    """バージョン文字列 ('v1.0.11' や '1.2.3-beta') を比較可能な数値タプルに変換"""
    if not v_str:
        return (0, 0, 0)
    cleaned = v_str.strip().lstrip("vV")
    # 数字とドットの先頭部分のみ抽出
    match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?", cleaned)
    if match:
        major = int(match.group(1) or 0)
        minor = int(match.group(2) or 0)
        patch = int(match.group(3) or 0)
        return (major, minor, patch)
    return (0, 0, 0)

def is_newer_version(latest_str: str, current_str: str) -> bool:
    """latest が current より新しい場合に True を返却"""
    return parse_semver(latest_str) > parse_semver(current_str)

class UpdateService:
    def __init__(self):
        self._cached_release: Optional[Dict[str, Any]] = None
        self._last_checked_time: float = 0.0
        self._cache_ttl_seconds: float = 24 * 3600  # 1日1回 (24時間)
        self._bg_task: Optional[asyncio.Task] = None
        self._last_auto_update_day: str = ""

    def get_current_version(self) -> str:
        return __version__

    async def check_for_updates(self, force_refresh: bool = False) -> Dict[str, Any]:
        """GitHub Releases API から最新バージョン情報を取得 (24時間キャッシュ)"""
        now = time.time()
        if not force_refresh and self._cached_release and (now - self._last_checked_time < self._cache_ttl_seconds):
            return self._cached_release

        current_ver = self.get_current_version()
        res_data: Dict[str, Any] = {
            "currentVersion": f"v{current_ver}",
            "latestVersion": f"v{current_ver}",
            "hasUpdate": False,
            "releaseName": "",
            "releaseNotes": "",
            "publishedAt": "",
            "releaseUrl": GITHUB_RELEASES_URL,
            "checkedAt": int(now),
            "status": "up_to_date"
        }

        try:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": f"VoiceHub/{current_ver} (+https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub)"
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(GITHUB_RELEASES_API, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    tag_name = data.get("tag_name", "").strip()
                    clean_tag = tag_name.lstrip("vV")
                    
                    has_update = is_newer_version(clean_tag, current_ver)
                    res_data["latestVersion"] = tag_name or f"v{clean_tag}"
                    res_data["hasUpdate"] = has_update
                    res_data["releaseName"] = data.get("name") or tag_name
                    res_data["releaseNotes"] = data.get("body") or ""
                    res_data["publishedAt"] = data.get("published_at") or ""
                    res_data["releaseUrl"] = data.get("html_url") or GITHUB_RELEASES_URL
                    res_data["status"] = "update_available" if has_update else "up_to_date"
                    
                    self._cached_release = res_data
                    self._last_checked_time = now
                    if has_update:
                        logger.info(f"[UpdateService] 新しいバージョンが利用可能です: {tag_name} (現在: v{current_ver})")
                    else:
                        logger.info(f"[UpdateService] VoiceHub は最新バージョンです: v{current_ver}")
                    return res_data
                elif resp.status_code == 403:
                    logger.warning("[UpdateService] GitHub API レート制限のため更新確認をスキップしました")
                    res_data["status"] = "rate_limited"
                elif resp.status_code == 404:
                    logger.info("[UpdateService] GitHub Release が未公開のため現在のバージョンを維持します")
                    res_data["status"] = "up_to_date"
                else:
                    logger.warning(f"[UpdateService] GitHub API エラー: HTTP {resp.status_code}")
                    res_data["status"] = "api_error"
        except Exception as e:
            logger.warning(f"[UpdateService] 更新確認通信エラー: {e}")
            res_data["status"] = "network_error"

        # エラー時は直前の有効キャッシュがあればそれを返却
        if self._cached_release:
            return self._cached_release

        return res_data

    async def check_watchtower_health(self) -> Dict[str, Any]:
        """
        Watchtower HTTP API の稼働状態を確認。
        注意: Watchtower の /v1/update は GET リクエストであっても有効な Bearer トークンを渡すと
        即時アップデートが発動してしまう仕様のため、ヘルスチェック時はトークンを付与せず
        HTTP 応答 (401 Unauthorized / 404 / 405 / 200) の有無のみでプロセス生存を安全に判定する。
        """
        conf = settings_manager.get().get("systemUpdate", {})
        wt_url = (conf.get("watchtowerUrl") or "http://127.0.0.1:8082").rstrip("/")

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{wt_url}/v1/update")
                is_ready = resp.status_code in (200, 401, 404, 405)
                return {
                    "available": is_ready,
                    "url": wt_url,
                    "statusCode": resp.status_code,
                    "message": "Watchtower 待機中 (接続正常)" if is_ready else f"応答コード: {resp.status_code}"
                }
        except httpx.ConnectError:
            return {
                "available": False,
                "url": wt_url,
                "message": "Watchtower が起動していません (未実行またはポート不一致)"
            }
        except Exception as e:
            return {
                "available": False,
                "url": wt_url,
                "message": f"Watchtower 接続エラー: {str(e)}"
            }

    async def trigger_update(self) -> Dict[str, Any]:
        """Watchtower の /v1/update を呼び出してコンテナを即時更新"""
        conf = settings_manager.get().get("systemUpdate", {})
        wt_url = (conf.get("watchtowerUrl") or "http://127.0.0.1:8082").rstrip("/")
        token = conf.get("watchtowerToken") or "voicehub-watchtower-token"

        logger.info(f"[UpdateService] Watchtower への更新要求を送信します ({wt_url}/v1/update)...")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"Authorization": f"Bearer {token}"}
                resp = await client.post(f"{wt_url}/v1/update", headers=headers)
                if resp.status_code in (200, 204):
                    logger.info("[UpdateService] ✅ Watchtower に更新指示が受理されました。コンテナの再作成が開始されます。")
                    return {
                        "success": True,
                        "message": "アップデート処理を開始しました。数分後に自動でコンテナが再起動します。"
                    }
                elif resp.status_code == 401:
                    logger.error("[UpdateService] ❌ Watchtower 認証エラー (トークン不一致)")
                    return {
                        "success": False,
                        "error": "Watchtower 認証トークンが一致しません。設定を確認してください。"
                    }
                else:
                    err_msg = f"Watchtower 応答エラー: HTTP {resp.status_code} ({resp.text[:100]})"
                    logger.error(f"[UpdateService] ❌ {err_msg}")
                    return {"success": False, "error": err_msg}
        except httpx.ConnectError:
            err_msg = f"Watchtower ({wt_url}) に接続できませんでした。docker-compose で watchtower コンテナが起動しているか確認してください。"
            logger.warning(f"[UpdateService] ⚠️ {err_msg}")
            return {"success": False, "error": err_msg}
        except Exception as e:
            logger.error(f"[UpdateService] ❌ アップデート呼び出しエラー: {e}", exc_info=True)
            return {"success": False, "error": "アップデート呼び出し中に予期せぬエラーが発生しました"}

    async def _worker_loop(self):
        """1日1回の更新確認 & 自動更新時刻の監視ワーカー"""
        logger.info("[UpdateService] アップデート監視バックグラウンドワーカーを開始しました")
        # 起動直後に1回チェック (5秒待機してアプリ起動完了を待つ)
        await asyncio.sleep(5)
        try:
            await self.check_for_updates(force_refresh=False)
        except Exception as e:
            logger.warning(f"[UpdateService] 起動時更新チェック例外: {e}")

        while True:
            try:
                # 60秒ごとにループ
                await asyncio.sleep(60)
                now_dt = datetime.now()
                now_time_str = now_dt.strftime("%H:%M")
                today_str = now_dt.strftime("%Y-%m-%d")

                # 24時間以上経過していれば定期再チェック
                if time.time() - self._last_checked_time >= self._cache_ttl_seconds:
                    await self.check_for_updates(force_refresh=True)

                # 自動更新の設定確認
                conf = settings_manager.get().get("systemUpdate", {})
                auto_update = bool(conf.get("autoUpdate", False))
                target_time = str(conf.get("autoUpdateTime") or "04:00").strip()

                if auto_update and now_time_str == target_time and self._last_auto_update_day != today_str:
                    update_info = await self.check_for_updates(force_refresh=True)
                    if update_info.get("hasUpdate"):
                        logger.info(f"[UpdateService] 自動更新スケジュール発動 ({target_time}): {update_info.get('latestVersion')} へのアップデートを実行します")
                        self._last_auto_update_day = today_str
                        await self.trigger_update()
                    else:
                        logger.info(f"[UpdateService] 自動更新チェック ({target_time}): 最新版のため更新は不要です")
                        self._last_auto_update_day = today_str
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[UpdateService] ワーカー内予期せぬ例外: {e}")
                await asyncio.sleep(30)

    def start(self):
        if self._bg_task is None or self._bg_task.done():
            self._bg_task = asyncio.create_task(self._worker_loop())

    def stop(self):
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()

update_service = UpdateService()
