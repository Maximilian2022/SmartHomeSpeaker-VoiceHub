import asyncio
import json
import time
from typing import Dict, Any, Optional
import aiomqtt
from app.services.settings_service import settings_manager
from app.services.speech_service import speech_service
from app.services.dnd_service import dnd_service
from app.core.logger import get_logger

log = get_logger("MQTT")

class MQTTService:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._client: Optional[aiomqtt.Client] = None
        self.is_connected = False
        self.last_error: Optional[str] = None
        self.last_message_at: Optional[str] = None
        self.received_count = 0

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        log.info("[MQTT] Background service started.")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self.is_connected = False
        log.info("[MQTT] Background service stopped.")

    async def restart(self):
        await self.stop()
        self.start()

    def get_status(self) -> Dict[str, Any]:
        conf = settings_manager.get().get("mqtt", {})
        return {
            "enabled": conf.get("enabled", False),
            "connected": self.is_connected,
            "broker": conf.get("broker", ""),
            "port": conf.get("port", 1883),
            "clientId": conf.get("clientId", "voice-hub"),
            "baseTopic": conf.get("baseTopic", "voicehub"),
            "defaultTarget": conf.get("defaultTarget", ""),
            "tls": bool(conf.get("tls", False)),
            "haDiscoveryEnabled": bool(conf.get("haDiscoveryEnabled", True)),
            "haDiscoveryPrefix": conf.get("haDiscoveryPrefix", "homeassistant"),
            "receivedCount": self.received_count,
            "lastMessageAt": self.last_message_at,
            "lastError": self.last_error
        }

    async def publish_event(self, sub_topic: str, payload: Dict[str, Any], retain: bool = False):
        conf = settings_manager.get().get("mqtt", {})
        if not self.is_connected or not self._client or not conf.get("publishEvents", True):
            return
        base_topic = conf.get("baseTopic", "voicehub").rstrip("/")
        full_topic = f"{base_topic}/{sub_topic.lstrip('/')}"
        try:
            await self._client.publish(full_topic, json.dumps(payload, ensure_ascii=False), retain=retain)
        except Exception as e:
            log.warning(f"[MQTT] Failed to publish event to {full_topic}: {e}")

    async def publish_dnd_state(self):
        """現在の DND 状態（ON/OFF）を MQTT にパブリッシュ"""
        conf = settings_manager.get().get("mqtt", {})
        if not self.is_connected or not self._client:
            return
        base_topic = conf.get("baseTopic", "voicehub").rstrip("/")
        status = dnd_service.get_global_status()
        is_active = status.get("active", False) or status.get("isActive", False)
        payload = "ON" if is_active else "OFF"
        try:
            await self._client.publish(f"{base_topic}/dnd/state", payload, retain=True)
        except Exception as e:
            log.warning(f"[MQTT] Failed to publish DND state: {e}")

    async def publish_ha_discovery(self, clear: bool = False) -> Dict[str, Any]:
        """Home Assistant MQTT Auto-Discovery トピックをパブリッシュ"""
        conf = settings_manager.get().get("mqtt", {})
        if not self.is_connected or not self._client:
            return {"success": False, "message": "MQTT ブローカーに接続されていません"}

        ha_prefix = (conf.get("haDiscoveryPrefix") or "homeassistant").strip().rstrip("/")
        base_topic = (conf.get("baseTopic") or "voicehub").strip().rstrip("/")
        node_id = base_topic

        from app.config import settings
        server_ip = settings.effective_wireless_ip
        server_url = f"http://{server_ip}:{settings.server_port}"

        device_info = {
            "identifiers": ["smart_speaker_voicehub"],
            "name": "SmartSpeaker Voice Hub",
            "model": "Unified Audio & TTS Engine",
            "manufacturer": "VoiceHub",
            "sw_version": "2.0.0",
            "configuration_url": server_url
        }

        # エンティティ定義一覧
        entities = [
            # 1. notify (HA 2024.2+ MQTT Notify)
            {
                "component": "notify",
                "object_id": "say",
                "config": {
                    "name": "Voice Hub 通知",
                    "unique_id": f"{node_id}_notify",
                    "command_topic": f"{base_topic}/say",
                    "device": device_info
                }
            },
            # 2. switch (おやすみ・会議モード DND)
            {
                "component": "switch",
                "object_id": "dnd",
                "config": {
                    "name": "Voice Hub おやすみモード (DND)",
                    "unique_id": f"{node_id}_dnd_switch",
                    "command_topic": f"{base_topic}/dnd/set",
                    "state_topic": f"{base_topic}/dnd/state",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "state_on": "ON",
                    "state_off": "OFF",
                    "icon": "mdi:bell-cancel",
                    "device": device_info
                }
            },
            # 3. sensor (直前発話内容)
            {
                "component": "sensor",
                "object_id": "last_say",
                "config": {
                    "name": "Voice Hub 直前発話内容",
                    "unique_id": f"{node_id}_last_say",
                    "state_topic": f"{base_topic}/events/say",
                    "value_template": "{{ value_json.text }}",
                    "icon": "mdi:text-to-speech",
                    "device": device_info
                }
            },
            # 4. binary_sensor (接続ステータス)
            {
                "component": "binary_sensor",
                "object_id": "connectivity",
                "config": {
                    "name": "Voice Hub 接続状態",
                    "unique_id": f"{node_id}_connectivity",
                    "state_topic": f"{base_topic}/status",
                    "payload_on": "online",
                    "payload_off": "offline",
                    "device_class": "connectivity",
                    "device": device_info
                }
            },
            # 5. button (テスト発話ボタン)
            {
                "component": "button",
                "object_id": "test_speak",
                "config": {
                    "name": "Voice Hub テスト発話",
                    "unique_id": f"{node_id}_test_speak",
                    "command_topic": f"{base_topic}/say",
                    "payload_press": "Voice Hub と Home Assistant の連携テストです",
                    "icon": "mdi:volume-high",
                    "device": device_info
                }
            },
            # 6. button (DND保留キューフラッシュボタン)
            {
                "component": "button",
                "object_id": "flush_queue",
                "config": {
                    "name": "Voice Hub 保留通知フラッシュ",
                    "unique_id": f"{node_id}_flush_queue",
                    "command_topic": f"{base_topic}/dnd/flush",
                    "payload_press": "FLUSH",
                    "icon": "mdi:playlist-play",
                    "device": device_info
                }
            }
        ]

        published_count = 0
        for ent in entities:
            topic = f"{ha_prefix}/{ent['component']}/{node_id}/{ent['object_id']}/config"
            payload = "" if clear else json.dumps(ent["config"], ensure_ascii=False)
            try:
                await self._client.publish(topic, payload, retain=True)
                published_count += 1
            except Exception as e:
                log.warning(f"[MQTT] Failed to publish HA Discovery config to {topic}: {e}")

        action_str = "cleared" if clear else "published"
        log.info(f"[MQTT] Home Assistant MQTT Discovery {action_str} ({published_count} entities, prefix='{ha_prefix}')")
        return {"success": True, "count": published_count, "action": action_str, "prefix": ha_prefix}

    async def _run_loop(self):
        reconnect_delay = 5
        while self._running:
            conf = settings_manager.get().get("mqtt", {})
            enabled = conf.get("enabled", False)
            broker = (conf.get("broker") or "").strip()
            port = int(conf.get("port") or 1883)
            username = (conf.get("username") or "").strip() or None
            password = conf.get("password") or None
            client_id = (conf.get("clientId") or "voice-hub").strip()
            keepalive = int(conf.get("keepalive") or 60)
            base_topic = (conf.get("baseTopic") or "voicehub").strip().rstrip("/")

            if not enabled or not broker:
                self.is_connected = False
                # 有効化されるまで待機
                await asyncio.sleep(5)
                continue

            use_tls = bool(conf.get("tls", False)) or port == 8883
            tls_params = None
            if use_tls:
                import ssl
                ssl_ctx = ssl.create_default_context()
                tls_params = aiomqtt.TLSParameters(context=ssl_ctx)

            # LWT (Last Will and Testament): 切断時に offline をパブリッシュ
            will = aiomqtt.Will(
                topic=f"{base_topic}/status",
                payload="offline",
                retain=True
            )

            try:
                log.info(f"[MQTT] Connecting to broker {broker}:{port} (tls={use_tls}, client_id={client_id})...")
                self.last_error = None
                
                async with aiomqtt.Client(
                    hostname=broker,
                    port=port,
                    username=username,
                    password=password,
                    identifier=client_id,
                    keepalive=keepalive,
                    timeout=10,
                    tls_params=tls_params,
                    will=will
                ) as client:
                    self._client = client
                    self.is_connected = True
                    log.info(f"[MQTT] Connected successfully to {broker}:{port}")

                    # オンラインステータスを発行 (Retain)
                    await client.publish(f"{base_topic}/status", "online", retain=True)

                    # トピック購読
                    # 1. base_topic/say
                    # 2. base_topic/say/# (例: voicehub/say/living)
                    # 3. base_topic/dnd/set (Home Assistant からの DND 操作)
                    # 4. base_topic/dnd/flush (Home Assistant からの キューフラッシュ)
                    sub_say = f"{base_topic}/say"
                    sub_say_wild = f"{base_topic}/say/#"
                    sub_dnd_set = f"{base_topic}/dnd/set"
                    sub_dnd_flush = f"{base_topic}/dnd/flush"

                    await client.subscribe(sub_say)
                    await client.subscribe(sub_say_wild)
                    await client.subscribe(sub_dnd_set)
                    await client.subscribe(sub_dnd_flush)
                    log.info(f"[MQTT] Subscribed to say & DND control topics")

                    # DND 状態を発行
                    await self.publish_dnd_state()

                    # Home Assistant MQTT Discovery の自動発行
                    if conf.get("haDiscoveryEnabled", True):
                        await self.publish_ha_discovery(clear=False)

                    # メッセージ受信ループ
                    async for message in client.messages:
                        if not self._running:
                            break
                        asyncio.create_task(self._handle_message(message, base_topic))

            except asyncio.CancelledError:
                break
            except aiomqtt.MqttError as e:
                self.is_connected = False
                self.last_error = f"MQTT error: {e}"
                log.warning(f"[MQTT] Connection lost / error: {e}. Reconnecting in {reconnect_delay}s...")
                await asyncio.sleep(reconnect_delay)
            except Exception as e:
                self.is_connected = False
                self.last_error = f"Unexpected error: {e}"
                log.error(f"[MQTT] Exception in MQTT loop: {e}", exc_info=True)
                await asyncio.sleep(reconnect_delay)
            finally:
                self.is_connected = False
                self._client = None

    async def _handle_message(self, message: aiomqtt.Message, base_topic: str):
        topic_str = str(message.topic)
        self.received_count += 1
        self.last_message_at = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            payload_str = message.payload.decode("utf-8").strip()
        except Exception as e:
            log.warning(f"[MQTT] Failed to decode payload as utf-8: {e}")
            return

        log.info(f"[MQTT] Received message on topic '{topic_str}': {payload_str[:120]}")

        # Home Assistant DND 操作トピックの判定
        if topic_str == f"{base_topic}/dnd/set":
            cmd = payload_str.upper()
            dnd_conf = settings_manager.get().get("dnd", {})
            if cmd in ("ON", "TRUE", "1", "ENABLE"):
                now_ts = time.time()
                until_ts = now_ts + (365 * 24 * 3600)  # 実質無期限
                settings_manager.update({
                    "dnd": {
                        **dnd_conf,
                        "manualUntil": until_ts,
                        "manualReason": "Home Assistant からの有効化"
                    }
                })
                log.info("[MQTT -> DND] Enabled DND mode via MQTT command")
            elif cmd in ("OFF", "FALSE", "0", "DISABLE"):
                settings_manager.update({
                    "dnd": {
                        **dnd_conf,
                        "manualUntil": None,
                        "manualReason": ""
                    }
                })
                await dnd_service.check_and_flush_queue()
                log.info("[MQTT -> DND] Disabled DND mode via MQTT command, flushed queue")
            await self.publish_dnd_state()
            return

        if topic_str == f"{base_topic}/dnd/flush":
            log.info("[MQTT -> DND] Flushing DND queue via MQTT command")
            await dnd_service.check_and_flush_queue()
            return

        # トピックからターゲットスピーカーを推論
        # 例: base_topic/say/living -> target = "living"
        # 例: base_topic/say -> target = None
        topic_target: Optional[str] = None
        say_prefix = f"{base_topic}/say/"
        if topic_str.startswith(say_prefix):
            sub_part = topic_str[len(say_prefix):].strip()
            if sub_part:
                topic_target = sub_part

        # ペイロードの解析 (JSON または プレーンテキスト)
        text = ""
        target = topic_target
        voice = None
        volume = None
        speed = None
        pitch = None
        chime = None
        urgent = False

        try:
            data = json.loads(payload_str)
            if isinstance(data, dict):
                text = (
                    data.get("text") or
                    data.get("message") or
                    data.get("msg") or
                    data.get("content") or
                    ""
                )
                # JSON内のターゲット指定があれば優先（無ければトピック指定を採用）
                json_target = data.get("target") or data.get("device") or data.get("speaker")
                if json_target:
                    target = json_target
                voice = data.get("voice")
                volume = data.get("volume") if data.get("volume") is not None else data.get("volumeLevel")
                speed = data.get("speed") or data.get("rate")
                pitch = data.get("pitch")
                chime = data.get("chime")
                urgent = bool(data.get("urgent", False))
            else:
                text = str(data)
        except (json.JSONDecodeError, TypeError):
            # プレーンテキスト
            text = payload_str

        text = text.strip()
        if not text:
            log.warning(f"[MQTT] Message payload contained empty text. Skipping.")
            return

        # ターゲットが未指定の場合、設定の defaultTarget を使用
        conf = settings_manager.get().get("mqtt", {})
        if not target:
            target = conf.get("defaultTarget") or ""

        log.info(f"[MQTT -> Speech] Dispatching: text='{text}', target='{target or 'DEFAULT'}', urgent={urgent}")

        try:
            broker_ip = conf.get("broker", "mqtt")
            result = await speech_service.speak(
                text=text,
                targets=[target] if target else [],
                voice=voice,
                volume_level=volume,
                speed=speed,
                pitch=pitch,
                chime=chime,
                client_name=f"MQTT ({topic_str})",
                client_ip=broker_ip,
                source="mqtt",
                source_label="MQTT (Node-RED/n8n)",
                urgent=urgent
            )

            # 完了イベントを発行 (Node-RED / n8n での後続トリガー用)
            await self.publish_event("events/say", {
                "status": "completed",
                "topic": topic_str,
                "text": text,
                "target": target,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "result": result
            })

        except Exception as e:
            log.error(f"[MQTT] Failed to execute speech: {e}", exc_info=True)
            self.last_error = f"Speech error: {e}"

    async def test_publish(self, text: str, target: Optional[str] = None):
        """テスト用: 自身が接続中のブローカーにPublishして発話パイプラインをテスト"""
        conf = settings_manager.get().get("mqtt", {})
        if not self.is_connected or not self._client:
            raise RuntimeError("MQTT ブローカーに接続されていません")
        base_topic = conf.get("baseTopic", "voicehub").rstrip("/")
        topic = f"{base_topic}/say/{target}" if target else f"{base_topic}/say"
        payload = json.dumps({"text": text, "target": target}, ensure_ascii=False)
        await self._client.publish(topic, payload)
        return {"success": True, "topic": topic, "payload": payload}

mqtt_service = MQTTService()
