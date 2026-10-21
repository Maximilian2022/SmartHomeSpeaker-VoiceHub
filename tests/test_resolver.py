import asyncio
import unittest
from unittest.mock import patch, MagicMock
from app.core.resolver import MDNSResolver, resolve_host, resolve_host_sync
from app.services.mqtt_service import MQTTBrokerWorker, MQTTService

class TestMDNSResolver(unittest.TestCase):
    def setUp(self):
        self.resolver = MDNSResolver(ttl=5.0)

    def test_is_ip_address(self):
        self.assertTrue(self.resolver.is_ip_address("192.168.1.1"))
        self.assertTrue(self.resolver.is_ip_address("127.0.0.1"))
        self.assertTrue(self.resolver.is_ip_address("::1"))
        self.assertTrue(self.resolver.is_ip_address("fe80::1"))
        self.assertFalse(self.resolver.is_ip_address("example.com"))
        self.assertFalse(self.resolver.is_ip_address("test.local"))
        self.assertFalse(self.resolver.is_ip_address(""))
        self.assertFalse(self.resolver.is_ip_address("   "))

    def test_is_mdns_host(self):
        self.assertTrue(self.resolver.is_mdns_host("MasterProDesk400G5.local"))
        self.assertTrue(self.resolver.is_mdns_host("masterprodesk400g5.local."))
        self.assertTrue(self.resolver.is_mdns_host("DEVICE.LOCAL"))
        self.assertFalse(self.resolver.is_mdns_host("example.com"))
        self.assertFalse(self.resolver.is_mdns_host("192.168.11.115"))
        self.assertFalse(self.resolver.is_mdns_host("local"))
        self.assertFalse(self.resolver.is_mdns_host(""))

    def test_resolve_ip_directly(self):
        # IP は解決を行わずそのまま即時返却
        res = resolve_host_sync("192.168.1.50")
        self.assertEqual(res, "192.168.1.50")

    def test_resolve_normal_domain(self):
        # 通常ドメインも mDNS 解決をスキップしてそのまま返却
        res = resolve_host_sync("broker.hivemq.com")
        self.assertEqual(res, "broker.hivemq.com")

    def test_cache_hit(self):
        # キャッシュの動作検証
        resolver = MDNSResolver(ttl=10.0)
        norm_key = "testbroker.local"
        resolver._cache[norm_key] = ("192.168.11.200", 9999999999.0)

        # 非同期テスト
        async def run_async():
            return await resolver.resolve_host("TestBroker.local")

        res = asyncio.run(run_async())
        self.assertEqual(res, "192.168.11.200")

        # 同期テスト
        sync_res = resolver.resolve_host_sync("TestBroker.local")
        self.assertEqual(sync_res, "192.168.11.200")

    def test_resolve_fallback_on_failure(self):
        # 解決不能なホスト名の場合、例外を出さず元のホスト名に安全にフォールバックすること
        resolver = MDNSResolver(ttl=5.0)
        mock_instance = MagicMock()
        mock_instance.async_request = MagicMock(side_effect=asyncio.coroutine(lambda *args, **kwargs: False) if hasattr(asyncio, 'coroutine') else None)
        
        async def mock_async_request(*args, **kwargs):
            return False

        mock_instance.async_request = mock_async_request
        mock_instance.parsed_addresses.return_value = []

        with patch("app.core.resolver.AddressResolver", return_value=mock_instance):
            async def run_async():
                return await resolver.resolve_host("unresolved-host.local", timeout=0.1)

            res = asyncio.run(run_async())
            self.assertEqual(res, "unresolved-host.local")

    def test_mqtt_worker_status_has_resolved_broker(self):
        service = MQTTService()
        conf = {
            "id": "broker-1",
            "name": "Test Broker",
            "broker": "MasterProDesk400G5.local",
            "port": 1883,
            "enabled": True
        }
        worker = MQTTBrokerWorker(conf, service)
        worker.resolved_ip = "192.168.11.115"
        status = worker.get_status()
        self.assertEqual(status["broker"], "MasterProDesk400G5.local")
        self.assertEqual(status["resolvedBroker"], "192.168.11.115")

    def test_live_mdns_query(self):
        # 実際にネットワーク上の MasterProDesk400G5.local を解決できるかテスト
        # （応答があれば 192.168.11.115、なければ安全にフォールバックされる）
        res = resolve_host_sync("MasterProDesk400G5.local", timeout=2.0)
        self.assertTrue(res == "192.168.11.115" or res == "MasterProDesk400G5.local")

if __name__ == "__main__":
    unittest.main()
