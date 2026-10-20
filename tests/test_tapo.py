import pytest
import hashlib
from fastapi.testclient import TestClient
from app.main import app
from app.services.settings_service import settings_manager
from app.services.speech_service import speech_service
from app.services.devices_service import device_manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def preserve_settings():
    original = dict(settings_manager.get())
    yield
    settings_manager.update(original)

def test_tapo_auth_and_hashing():
    raw_pass = "TestPassword!123"
    test_email = "test@example.com"
    expected_hash = hashlib.sha256(raw_pass.encode("utf-8")).hexdigest().upper()

    # 1. 保存APIテスト (email + password)
    resp = client.post("/api/onvif/tapo-auth", json={"email": test_email, "password": raw_pass})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    # 2. 設定取得確認
    cfg_resp = client.get("/api/onvif/config")
    assert cfg_resp.status_code == 200
    cfg = cfg_resp.json()
    assert cfg.get("tapoAuthConfigured") is True
    assert cfg.get("tapoEmail") == test_email

    # 3. 内部設定に大文字SHA256ハッシュおよびemailが存在すること
    saved_cfg = settings_manager.get().get("onvif", {})
    assert saved_cfg.get("tapoPasswordHash") == expected_hash
    assert saved_cfg.get("tapoEmail") == test_email


def test_tapo_register_and_device_dispatch():
    # Tapo デバイスの登録
    dev_ip = "192.168.11.235"
    reg_resp = client.post("/api/onvif/register", json={
        "device": {
            "ip": dev_ip,
            "name": "テストTapoスピーカー",
            "type": "tapo",
            "model": "C212 (Tapo)"
        }
    })
    assert reg_resp.status_code == 200

    # devices_service で認識されること
    dev = device_manager.find_device(f"tapo:{dev_ip}")
    assert dev is not None
    assert dev["type"] == "tapo"
    assert dev["rawIp"] == dev_ip

    # speech_service マクロ展開テスト
    import asyncio
    all_devs = [
        {"id": "g1", "name": "Google Nest", "ip": "192.168.11.10", "type": "google"},
        {"id": "o1", "name": "ONVIF Cam", "ip": "onvif:192.168.11.20", "type": "onvif"},
        {"id": "t1", "name": "Tapo Cam", "ip": "tapo:192.168.11.235", "type": "tapo"}
    ]
    expanded = asyncio.run(speech_service.resolve_targets(["CAM:ALL"], all_devs))
    assert len(expanded) == 2
    assert any(d["type"] == "onvif" for d in expanded)
    assert any(d["type"] == "tapo" for d in expanded)

    expanded_tapo = asyncio.run(speech_service.resolve_targets(["TAPO:ALL"], all_devs))
    assert len(expanded_tapo) == 2  # CAM:ALL と同様に onvif & tapo を含む

