import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import speech_service as speech_module
from app.services.speech_service import speech_service


def _cast_device(name, host):
    return {
        "id": f"dev_{host.replace('.', '_')}",
        "name": name,
        "ip": host,
        "host": host,
        "port": 8009,
        "isGroup": False,
        "type": "google",
    }


def test_retry_does_not_replay_on_unrelated_speaker():
    """rawName を持たない Cast 端末同士が None == None で一致し、別端末へ再送されないこと"""
    online = _cast_device("部屋", "192.168.11.97")
    offline = _cast_device("寝室", "192.168.11.81")
    devices = [online, offline]

    manager = MagicMock()
    manager.get_devices = AsyncMock(return_value=devices)
    manager.find_device.side_effect = lambda name: next(d for d in devices if d["name"] == name)

    tts = MagicMock()
    tts.get_default_voice_id.return_value = "voice"
    tts.synthesize = AsyncMock(
        return_value={"filename": "a.mp3", "filepath": "/tmp/a.mp3", "duration": 1.0, "voice": "voice"}
    )

    cast = MagicMock()
    cast.play_audio = AsyncMock(side_effect=lambda host, *_: host == online["host"])

    settings = MagicMock()
    settings.get.return_value = {"fallbackSpeaker": "none"}
    settings.is_device_disabled.return_value = False

    with (
        patch.object(speech_module, "device_manager", manager),
        patch.object(speech_module, "tts_service", tts),
        patch.object(speech_module, "cast_service", cast),
        patch.object(speech_module, "settings_manager", settings),
        patch.object(speech_module.SpeechService, "record_history", MagicMock()),
    ):
        asyncio.run(speech_service.speak("テスト", targets=["部屋", "寝室"], urgent=True))

    hosts = [call.args[0] for call in cast.play_audio.await_args_list]
    assert hosts.count(online["host"]) == 1
    assert hosts.count(offline["host"]) == 3
