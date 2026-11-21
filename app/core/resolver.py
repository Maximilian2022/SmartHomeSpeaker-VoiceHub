import asyncio
import ipaddress
import socket
import threading
import time
from typing import Dict, Tuple, Optional
from zeroconf import Zeroconf, AddressResolver, IPVersion
from app.core.logger import get_logger

log = get_logger("Resolver")

class MDNSResolver:
    """ローカルネットワーク内の mDNS (.local) 動的名前解決マネージャー"""

    def __init__(self, ttl: float = 60.0):
        self.ttl = ttl
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._sync_lock = threading.Lock()
        self._internal_zc: Optional[Zeroconf] = None

    def is_ip_address(self, host: str) -> bool:
        """文字列がすでに有効な IPv4/IPv6 アドレスであるか判定"""
        if not host:
            return False
        try:
            ipaddress.ip_address(host.strip())
            return True
        except ValueError:
            return False

    def is_mdns_host(self, host: str) -> bool:
        """ホスト名が .local ドメインであるか判定"""
        if not host:
            return False
        h = host.strip().lower().rstrip(".")
        return h.endswith(".local")

    def _get_zeroconf(self) -> Zeroconf:
        """既存の DeviceManager の Zeroconf または内部シングルトン Zeroconf を取得"""
        try:
            from app.services.devices_service import device_manager
            if device_manager._zc is not None:
                return device_manager._zc
        except Exception:
            pass

        with self._sync_lock:
            if self._internal_zc is None:
                from zeroconf import InterfaceChoice
                self._internal_zc = Zeroconf(interfaces=InterfaceChoice.All, ip_version=IPVersion.All)
            return self._internal_zc

    async def resolve_host(self, host: str, timeout: float = 3.0) -> str:
        """ホスト名を解決して IP アドレス (文字列) を返却。
        .local の場合は別スレッド経由の同期解決 (Zeroconf + OS DNSフォールバック) に委譲し、
        FastAPI メインループと Zeroconf 内部イベントループの衝突を完全に回避する。
        """
        if not host:
            return ""

        clean_host = host.strip()
        if self.is_ip_address(clean_host):
            return clean_host

        if not self.is_mdns_host(clean_host):
            # .local 以外は通常の DNS (OS 解決) に委ねる
            return clean_host

        norm_key = clean_host.lower().rstrip(".")
        now = time.monotonic()

        with self._sync_lock:
            if norm_key in self._cache:
                cached_ip, expire_at = self._cache[norm_key]
                if now < expire_at:
                    log.debug(f"[Resolver] Cache hit for '{clean_host}' -> {cached_ip}")
                    return cached_ip
                else:
                    del self._cache[norm_key]

        return await asyncio.to_thread(self.resolve_host_sync, clean_host, timeout)

    def _resolve_via_os(self, host_name: str) -> Optional[str]:
        """OS の getaddrinfo による IPv4 名前解決フォールバック"""
        try:
            infos = socket.getaddrinfo(host_name, None, socket.AF_INET, socket.SOCK_STREAM)
            for info in infos:
                addr = info[4][0]
                if addr and self.is_ip_address(addr):
                    return addr
        except OSError:
            pass
        return None

    def resolve_host_sync(self, host: str, timeout: float = 3.0) -> str:
        """同期コンテキスト用の名前解決メソッド"""
        if not host:
            return ""

        clean_host = host.strip()
        if self.is_ip_address(clean_host):
            return clean_host

        if not self.is_mdns_host(clean_host):
            return clean_host

        norm_key = clean_host.lower().rstrip(".")
        now = time.monotonic()

        with self._sync_lock:
            if norm_key in self._cache:
                cached_ip, expire_at = self._cache[norm_key]
                if now < expire_at:
                    return cached_ip
                else:
                    del self._cache[norm_key]

        query_fqdn = f"{norm_key}."
        zc = self._get_zeroconf()

        try:
            resolver = AddressResolver(query_fqdn)
            success = resolver.request(zc, int(timeout * 1000))
            if success:
                addrs = resolver.parsed_addresses(IPVersion.V4Only)
                if not addrs:
                    addrs = [a for a in resolver.parsed_addresses() if "." in a]
                if addrs:
                    resolved_ip = addrs[0]
                    with self._sync_lock:
                        self._cache[norm_key] = (resolved_ip, now + self.ttl)
                    log.info(f"[Resolver] mDNS resolved '{clean_host}' -> {resolved_ip} (ttl={int(self.ttl)}s)")
                    return resolved_ip

            # Zeroconf 応答が得られなかった場合は OS / Avahi / hosts 解決を試行
            os_ip = self._resolve_via_os(norm_key)
            if os_ip:
                with self._sync_lock:
                    self._cache[norm_key] = (os_ip, now + self.ttl)
                log.info(f"[Resolver] OS resolved '{clean_host}' -> {os_ip} (ttl={int(self.ttl)}s)")
                return os_ip

            log.warning(f"[Resolver] mDNS query timed out or not found for '{clean_host}'. Falling back to original.")
            return clean_host
        except Exception as e:
            os_ip = self._resolve_via_os(norm_key)
            if os_ip:
                with self._sync_lock:
                    self._cache[norm_key] = (os_ip, now + self.ttl)
                return os_ip
            log.warning(f"[Resolver] Error resolving '{clean_host}': {e}. Falling back to original.")
            return clean_host

    def clear_cache(self):
        """キャッシュを手動クリア"""
        with self._sync_lock:
            self._cache.clear()

resolver = MDNSResolver()

async def resolve_host(host: str, timeout: float = 3.0) -> str:
    """便利な共通ヘルパー関数"""
    return await resolver.resolve_host(host, timeout=timeout)

def resolve_host_sync(host: str, timeout: float = 3.0) -> str:
    """便利な共通同期ヘルパー関数"""
    return resolver.resolve_host_sync(host, timeout=timeout)
