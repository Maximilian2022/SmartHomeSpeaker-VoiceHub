import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.routers.dnd import build_dnd_script

class TestDndScripts(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_build_dnd_script_vbs(self):
        filename, content, mime = build_dnd_script("toggle", "vbs", "http://192.168.1.50:8080", "secret123")
        self.assertEqual(filename, "voicehub_dnd_toggle.vbs")
        self.assertIn("text/plain", mime)
        self.assertIn('url = "http://192.168.1.50:8080/api/dnd/toggle"', content)
        self.assertIn('token = "secret123"', content)
        self.assertIn("MSXML2.XMLHTTP", content)

    def test_build_dnd_script_vbs_30m(self):
        filename, content, mime = build_dnd_script("30m", "vbs", "http://192.168.1.50:8080", "")
        self.assertEqual(filename, "voicehub_dnd_30m.vbs")
        self.assertIn('url = "http://192.168.1.50:8080/api/dnd/quick"', content)
        self.assertIn('""minutes"": 30', content)

    def test_build_dnd_script_ps1(self):
        filename, content, mime = build_dnd_script("toggle", "ps1", "http://192.168.1.50:8080", "secret123")
        self.assertEqual(filename, "voicehub_dnd_toggle.ps1")
        self.assertIn("text/plain", mime)
        self.assertIn('$url = "http://192.168.1.50:8080/api/dnd/toggle"', content)
        self.assertIn("$token = 'secret123'", content)
        self.assertIn("Invoke-RestMethod", content)

        # シングルクォートが含まれるパスワードのエスケープ検証
        _, content_esc, _ = build_dnd_script("toggle", "ps1", "http://192.168.1.50:8080", "sec'ret")
        self.assertIn("$token = 'sec''ret'", content_esc)

    def test_build_dnd_script_bat(self):
        filename, content, mime = build_dnd_script("toggle", "bat", "http://192.168.1.50:8080", "secret123")
        self.assertEqual(filename, "voicehub_dnd_toggle.bat")
        self.assertIn("application/x-bat", mime)
        self.assertIn('set "VOICEHUB_HOST=http://192.168.1.50:8080"', content)
        self.assertIn('curl -s -X POST "%VOICEHUB_HOST%/api/dnd/toggle?token=%TOKEN%" -H "x-admin-password: %TOKEN%"', content)

    def test_build_dnd_script_bat_no_pwd(self):
        filename, content, mime = build_dnd_script("60m", "bat", "http://192.168.1.50:8080", "")
        self.assertEqual(filename, "voicehub_dnd_60m.bat")
        self.assertIn('curl -s -X POST "%VOICEHUB_HOST%/api/dnd/quick"', content)
        self.assertIn('\\"minutes\\": 60', content)

    def test_api_script_preview(self):
        res = self.client.get("/api/dnd/script/preview?action=toggle&format=vbs&host=http://192.168.11.10:8080")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["filename"], "voicehub_dnd_toggle.vbs")
        self.assertIn("MSXML2.XMLHTTP", data["content"])

    def test_api_script_download(self):
        res = self.client.get("/api/dnd/script/download?action=30m&format=bat&host=http://192.168.11.10:8080")
        self.assertEqual(res.status_code, 200)
        self.assertIn("attachment; filename=\"voicehub_dnd_30m.bat\"", res.headers.get("content-disposition", ""))
        self.assertIn("VOICEHUB_HOST=http://192.168.11.10:8080", res.text)

    def test_build_dnd_script_sh(self):
        filename, content, mime = build_dnd_script("unmute", "sh", "http://192.168.1.50:8080", "secret123")
        self.assertEqual(filename, "voicehub_dnd_unmute.sh")
        self.assertIn("text/x-shellscript", mime)
        self.assertIn('#!/usr/bin/env bash', content)
        self.assertIn('VOICEHUB_HOST="http://192.168.1.50:8080"', content)
        self.assertIn('curl -s -X POST "$VOICEHUB_HOST/api/dnd/unmute?token=$TOKEN" -H "x-admin-password: $TOKEN"', content)

    def test_dnd_i18n_keys_symmetry(self):
        import json
        from pathlib import Path
        root = Path(__file__).parent.parent
        ja = json.loads((root / "public/locales/ja.json").read_text(encoding="utf-8"))
        en = json.loads((root / "public/locales/en.json").read_text(encoding="utf-8"))

        def get_keys(d, prefix=""):
            keys = set()
            for k, v in d.items():
                curr = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    keys.update(get_keys(v, curr))
                else:
                    keys.add(curr)
            return keys

        ja_keys = get_keys(ja.get("settingsDnd", {}))
        en_keys = get_keys(en.get("settingsDnd", {}))
        self.assertEqual(ja_keys, en_keys, f"Diff: ja - en: {ja_keys - en_keys}, en - ja: {en_keys - ja_keys}")

if __name__ == "__main__":
    unittest.main()

