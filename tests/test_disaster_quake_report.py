import unittest
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.disaster_service import DisasterService


class TestDisasterQuakeReport(unittest.TestCase):
    def setUp(self):
        self.disaster = DisasterService()
        self.spoken_texts = []

        async def mock_speak(text: str, urgent: bool = False, **kwargs):
            self.spoken_texts.append({"text": text, "urgent": urgent, "kwargs": kwargs})

        self.disaster.speak = mock_speak

    def test_scale_prompt_ignored_for_other_region_when_local(self):
        """ユーザー設定が東京都かつlocalの場合、熊本の震度速報(震源地名空文字)で誤発報されないこと"""
        settings = {
            "enabled": True,
            "area": {
                "prefName": "東京都",
                "cityName": "町田市"
            },
            "earthquake": {
                "enabled": True,
                "reportEnabled": True,
                "minScale": 30,
                "targetScope": "local",
                "reportUrgent": False
            }
        }
        # 実際に2026/10/26 23:35に受信したデータ（熊本天草で震度3、hypocenter.nameは空文字）
        data = {
            "code": 551,
            "issue": {"type": "ScalePrompt"},
            "earthquake": {
                "time": "2026/10/26 23:34:00",
                "hypocenter": {"name": "", "depth": -1, "magnitude": -1},
                "maxScale": 30
            },
            "points": [
                {"pref": "熊本県", "addr": "熊本県天草・芦北", "scale": 30, "isArea": True}
            ]
        }

        asyncio.run(self.disaster._handle_quake_report(data, settings))
        # 東京都と無関係なため発話されないこと
        self.assertEqual(len(self.spoken_texts), 0)

    def test_scale_prompt_speaks_area_name_when_matched_local(self):
        """ユーザー設定が東京都かつlocalで、東京都内で震度3を観測した場合、地点名を含む発話になること"""
        settings = {
            "enabled": True,
            "area": {
                "prefName": "東京都",
                "cityName": "町田市"
            },
            "earthquake": {
                "enabled": True,
                "reportEnabled": True,
                "minScale": 30,
                "targetScope": "local",
                "reportUrgent": False
            }
        }
        data = {
            "code": 551,
            "issue": {"type": "ScalePrompt"},
            "earthquake": {
                "time": "2026/10/26 23:34:00",
                "hypocenter": {"name": "", "depth": -1, "magnitude": -1},
                "maxScale": 30
            },
            "points": [
                {"pref": "東京都", "addr": "東京多摩南部", "scale": 30, "isArea": True}
            ]
        }

        asyncio.run(self.disaster._handle_quake_report(data, settings))
        self.assertEqual(len(self.spoken_texts), 1)
        text = self.spoken_texts[0]["text"]
        self.assertIn("東京多摩南部", text)
        self.assertIn("最大震度3の揺れを観測しました", text)
        self.assertNotIn("。で最大", text)

    def test_scale_prompt_nationwide_all_scope(self):
        """targetScopeがallの場合、震度速報でもpointsから観測地域名を抽出してアナウンスすること"""
        settings = {
            "enabled": True,
            "area": {"prefName": "東京都"},
            "earthquake": {
                "enabled": True,
                "reportEnabled": True,
                "minScale": 30,
                "targetScope": "all",
                "reportUrgent": False
            }
        }
        data = {
            "code": 551,
            "issue": {"type": "ScalePrompt"},
            "earthquake": {
                "time": "2026/10/26 23:34:00",
                "hypocenter": {"name": ""},
                "maxScale": 30
            },
            "points": [
                {"pref": "熊本県", "addr": "熊本県天草・芦北", "scale": 30, "isArea": True}
            ]
        }

        asyncio.run(self.disaster._handle_quake_report(data, settings))
        self.assertEqual(len(self.spoken_texts), 1)
        text = self.spoken_texts[0]["text"]
        self.assertEqual(text, "地震情報です。熊本県天草・芦北で最大震度3の揺れを観測しました。")

    def test_scale_prompt_fallback_to_kakuchi_if_no_points(self):
        """pointsが空でも '各地' にフォールバックし、'で最大震度' のような脱字にならないこと"""
        settings = {
            "enabled": True,
            "earthquake": {
                "enabled": True,
                "reportEnabled": True,
                "minScale": 30,
                "targetScope": "all"
            }
        }
        data = {
            "code": 551,
            "earthquake": {
                "time": "2026/10/26 23:34:00",
                "hypocenter": {"name": ""},
                "maxScale": 30
            },
            "points": []
        }

        asyncio.run(self.disaster._handle_quake_report(data, settings))
        self.assertEqual(len(self.spoken_texts), 1)
        text = self.spoken_texts[0]["text"]
        self.assertEqual(text, "地震情報です。各地で最大震度3の揺れを観測しました。")

    def test_standard_report_with_hypocenter_name(self):
        """震源地が判明している通常地震情報では震源地名を発話すること"""
        settings = {
            "enabled": True,
            "earthquake": {
                "enabled": True,
                "reportEnabled": True,
                "minScale": 30,
                "targetScope": "all"
            }
        }
        data = {
            "code": 551,
            "earthquake": {
                "time": "2026/10/26 23:34:00",
                "hypocenter": {"name": "熊本県天草・芦北地方"},
                "maxScale": 30
            },
            "points": []
        }

        asyncio.run(self.disaster._handle_quake_report(data, settings))
        self.assertEqual(len(self.spoken_texts), 1)
        text = self.spoken_texts[0]["text"]
        self.assertEqual(text, "地震情報です。熊本県天草・芦北地方で最大震度3の地震が発生しました。")


if __name__ == "__main__":
    unittest.main()
