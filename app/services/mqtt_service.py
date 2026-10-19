import asyncio
import json
import time
from typing import Dict, Any, Optional, List
import aiomqtt
from app.services.settings_service import settings_manager
from app.services.speech_service import speech_service
from app.services.scheduled_speech_service import scheduled_speech_service
from app.services.dnd_service import dnd_service
from app.core.logger import get_logger

log = get_logger("MQTT")

class MQTTBrokerWorker:
    """単一 MQTT ブローカーへの接続・購読・送受信を独立管理するワーカー"""
    def __init__(self, broker_conf: Dict[str, Any], service: 'MQTTService'):
        self.conf = dict(broker_conf)
        self.broker_id = str(self.conf.get("id") or self.conf.get("broker") or "default")
        self.name = self.conf.get("name") or self.conf.get("broker") or "Broker"
        self.service = service
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._client: Optional[aiomqtt.Client] = None
        self.is_connected = False
        self.last_error: Optional[str] = None
        self.last_message_at: Optional[str] = None
        self.received_count = 0

    def start(self):
        if self._running or not self.conf.get("enabled", True):
            return
        broker_host = (self.conf.get("broker") or "").strip()
        if not broker_host:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        log.info(f"[MQTT Worker:{self.name}] Started background worker for {broker_host}:{self.conf.get('port', 1883)}")

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
        self._client = None
        log.info(f"[MQTT Worker:{self.name}] Stopped.")

    def get_status(self) -> Dict[str, Any]:
        return {
            "id": self.broker_id,
            "name": self.name,
            "enabled": bool(self.conf.get("enabled", True)),
            "connected": self.is_connected,
            "broker": self.conf.get("broker", ""),
            "port": int(self.conf.get("port") or 1883),
            "clientId": self.conf.get("clientId", "voice-hub"),
            "baseTopic": self.conf.get("baseTopic", "voicehub"),
            "defaultTarget": self.conf.get("defaultTarget", ""),
            "tls": bool(self.conf.get("tls", False)),
            "haDiscoveryEnabled": bool(self.conf.get("haDiscoveryEnabled", True)),
            "haDiscoveryPrefix": self.conf.get("haDiscoveryPrefix", "homeassistant"),
            "publishEvents": bool(self.conf.get("publishEvents", True)),
            "receivedCount": self.received_count,
            "lastMessageAt": self.last_message_at,
            "lastError": self.last_error
        }

    async def publish(self, topic: str, payload: str, retain: bool = False):
        if not self.is_connected or not self._client:
            return
        try:
            await self._client.publish(topic, payload, retain=retain)
        except Exception as e:
            log.warning(f"[MQTT Worker:{self.name}] Failed to publish to {topic}: {e}")

    async def publish_event(self, sub_topic: str, payload: Dict[str, Any], retain: bool = False):
        if not self.is_connected or not self._client or not self.conf.get("publishEvents", True):
            return
        base_topic = self.conf.get("baseTopic", "voicehub").rstrip("/")
        full_topic = f"{base_topic}/{sub_topic.lstrip('/')}"
        await self.publish(full_topic, json.dumps(payload, ensure_ascii=False), retain=retain)

    async def publish_dnd_state(self):
        if not self.is_connected or not self._client:
            return
        base_topic = self.conf.get("baseTopic", "voicehub").rstrip("/")
        status = dnd_service.get_global_status()
        is_active = status.get("active", False) or status.get("isActive", False)
        payload = "ON" if is_active else "OFF"
        await self.publish(f"{base_topic}/dnd/state", payload, retain=True)

    async def publish_ha_discovery(self, clear: bool = False) -> Dict[str, Any]:
        """Home Assistant MQTT Auto-Discovery トピックをパブリッシュ"""
        if not self.is_connected or not self._client:
            return {"success": False, "message": f"ブローカー '{self.name}' に未接続です"}

        ha_prefix = (self.conf.get("haDiscoveryPrefix") or "homeassistant").strip().rstrip("/")
        base_topic = (self.conf.get("baseTopic") or "voicehub").strip().rstrip("/")
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

        entities = [
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

        count = 0
        for ent in entities:
            topic = f"{ha_prefix}/{ent['component']}/{node_id}/{ent['object_id']}/config"
            if clear:
                await self.publish(topic, "", retain=True)
            else:
                payload = json.dumps(ent["config"], ensure_ascii=False)
                await self.publish(topic, payload, retain=True)
            count += 1

        action_label = "cleared" if clear else "published"
        log.info(f"[MQTT Worker:{self.name}] Home Assistant MQTT Discovery {action_label} ({count} entities, prefix='{ha_prefix}')")
        return {"success": True, "count": count, "action": action_label, "prefix": ha_prefix, "broker": self.name}

    async def _run_loop(self):
        reconnect_delay = 5
        while self._running:
            broker = (self.conf.get("broker") or "").strip()
            port = int(self.conf.get("port") or 1883)
            username = (self.conf.get("username") or "").strip() or None
            password = self.conf.get("password") or None
            client_id = (self.conf.get("clientId") or f"voice-hub-{self.broker_id}").strip()
            keepalive = int(self.conf.get("keepalive") or 60)
            base_topic = (self.conf.get("baseTopic") or "voicehub").strip().rstrip("/")

            if not broker:
                await asyncio.sleep(5)
                continue

            use_tls = bool(self.conf.get("tls", False)) or port == 8883
            tls_params = None
            if use_tls:
                import ssl
                ssl_ctx = ssl.create_default_context()
                tls_params = aiomqtt.TLSParameters(context=ssl_ctx)

            will = aiomqtt.Will(
                topic=f"{base_topic}/status",
                payload="offline",
                retain=True
            )

            try:
                log.info(f"[MQTT Worker:{self.name}] Connecting to broker {broker}:{port} (tls={use_tls}, client_id={client_id})...")
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
                    log.info(f"[MQTT Worker:{self.name}] Connected successfully to {broker}:{port}")

                    # オンラインステータスを発行 (Retain)
                    await client.publish(f"{base_topic}/status", "online", retain=True)

                    # トピック購読 (# ワイルドカードは base_topic/say 自体にもマッチするため重複購読を防止)
                    sub_say_wild = f"{base_topic}/say/#"
                    sub_dnd_set = f"{base_topic}/dnd/set"
                    sub_dnd_flush = f"{base_topic}/dnd/flush"

                    await client.subscribe(sub_say_wild)
                    await client.subscribe(sub_dnd_set)
                    await client.subscribe(sub_dnd_flush)
                    log.info(f"[MQTT Worker:{self.name}] Subscribed to say & DND control topics")

                    # DND 状態を発行
                    await self.publish_dnd_state()

                    # Home Assistant MQTT Discovery の自動発行
                    if self.conf.get("haDiscoveryEnabled", True):
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
                log.warning(f"[MQTT Worker:{self.name}] Connection lost / error: {e}. Reconnecting in {reconnect_delay}s...")
                await asyncio.sleep(reconnect_delay)
            except Exception as e:
                self.is_connected = False
                self.last_error = f"Unexpected error: {e}"
                log.error(f"[MQTT Worker:{self.name}] Exception in MQTT loop: {e}", exc_info=True)
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
            log.warning(f"[MQTT Worker:{self.name}] Failed to decode payload as utf-8: {e}")
            return

        log.info(f"[MQTT Worker:{self.name}] Received on '{topic_str}': {payload_str[:120]}")

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
                        "manualReason": f"MQTT ({self.name}) からの有効化"
                    }
                })
                log.info(f"[MQTT Worker:{self.name} -> DND] Enabled DND mode")
            elif cmd.isdigit() and int(cmd) > 0:
                mins = int(cmd)
                now_ts = time.time()
                until_ts = now_ts + (mins * 60)
                settings_manager.update({
                    "dnd": {
                        **dnd_conf,
                        "manualUntil": until_ts,
                        "manualReason": f"MQTT ({self.name}) からの {mins}分間タイマーミュート"
                    }
                })
                log.info(f"[MQTT Worker:{self.name} -> DND] Enabled DND mode for {mins} minutes")
            elif cmd in ("OFF", "FALSE", "0", "DISABLE"):
                settings_manager.update({
                    "dnd": {
                        **dnd_conf,
                        "manualUntil": None,
                        "manualReason": ""
                    }
                })
                await dnd_service.check_and_flush_queue()
                log.info(f"[MQTT Worker:{self.name} -> DND] Disabled DND mode, flushed queue")
            # 全ワーカーに DND 状態をマルチキャスト
            await self.service.publish_dnd_state()
            return

        if topic_str == f"{base_topic}/dnd/flush":
            log.info(f"[MQTT Worker:{self.name} -> DND] Flushing DND queue")
            await dnd_service.check_and_flush_queue()
            return

        # トピックからターゲットスピーカーを推論
        topic_target: Optional[str] = None
        say_prefix = f"{base_topic}/say/"
        if topic_str.startswith(say_prefix):
            sub_part = topic_str[len(say_prefix):].strip()
            if sub_part:
                topic_target = sub_part

        # ペイロードの解析
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
                json_target = data.get("target") or data.get("device") or data.get("speaker")
                if json_target:
                    target = json_target
                voice = data.get("voice")
                volume = data.get("volume") if data.get("volume") is not None else data.get("volumeLevel")
                speed = data.get("speed") or data.get("rate")
                pitch = data.get("pitch")
                chime = data.get("chime")
                urgent = bool(data.get("urgent", False))
                time_spec = data.get("time") or data.get("at") or data.get("scheduled_at") or data.get("datetime")
            else:
                text = str(data)
                time_spec = None
        except (json.JSONDecodeError, TypeError):
            text = payload_str
            time_spec = None

        text = text.strip()
        if not text:
            return

        if not target:
            target = self.conf.get("defaultTarget") or ""

        log.info(f"[MQTT Worker:{self.name} -> Speech] text='{text}', target='{target or 'DEFAULT'}', urgent={urgent}, time='{time_spec}'")

        try:
            broker_ip = self.conf.get("broker", "mqtt")
            if time_spec:
                result = await scheduled_speech_service.schedule_or_speak(
                    text=text,
                    time_spec=time_spec,
                    targets=[target] if target else [],
                    voice=voice,
                    volume_level=volume,
                    rate=speed,
                    pitch=pitch,
                    chime=chime,
                    client_name=f"MQTT ({self.name}:{topic_str})",
                    client_ip=broker_ip,
                    source="mqtt",
                    source_label=f"MQTT ({self.name})",
                    urgent=urgent
                )
            else:
                result = await speech_service.speak(
                    text=text,
                    targets=[target] if target else [],
                    voice=voice,
                    volume_level=volume,
                    rate=speed,
                    pitch=pitch,
                    chime=chime,
                    client_name=f"MQTT ({self.name}:{topic_str})",
                    client_ip=broker_ip,
                    source="mqtt",
                    source_label=f"MQTT ({self.name})",
                    urgent=urgent
                )

            # 完了イベントを発行 (接続中ワーカーへ)
            await self.publish_event("events/say", {
                "status": "completed",
                "broker": self.name,
                "topic": topic_str,
                "text": text,
                "target": target,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "result": result
            })

        except Exception as e:
            log.error(f"[MQTT Worker:{self.name}] Speech execution error: {e}", exc_info=True)
            self.last_error = f"Speech error: {e}"


class MQTTService:
    """複数 MQTT ブローカーを統合管理するオーケストレーター"""
    def __init__(self):
        self.workers: Dict[str, MQTTBrokerWorker] = {}
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True

        mqtt_conf = settings_manager.get().get("mqtt", {})
        if not mqtt_conf.get("enabled", True):
            log.info("[MQTT] Service is disabled in settings.")
            return

        brokers = mqtt_conf.get("brokers", [])

        self.workers.clear()
        for b in brokers:
            worker = MQTTBrokerWorker(b, self)
            self.workers[worker.broker_id] = worker
            worker.start()

        log.info(f"[MQTT] Service started with {len(self.workers)} broker worker(s).")

    async def stop(self):
        self._running = False
        tasks = [w.stop() for w in self.workers.values()]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.workers.clear()
        log.info("[MQTT] Service stopped.")

    async def restart(self):
        await self.stop()
        self.start()

    @property
    def is_connected(self) -> bool:
        """1台でも接続されていれば True (下位互換)"""
        return any(w.is_connected for w in self.workers.values())

    def get_status(self) -> Dict[str, Any]:
        mqtt_conf = settings_manager.get().get("mqtt", {})
        worker_statuses = [w.get_status() for w in self.workers.values()]
        total_received = sum(w.received_count for w in self.workers.values())
        connected_count = sum(1 for w in self.workers.values() if w.is_connected)

        # 最初のワーカーまたは直下設定 (後方互換プロパティ)
        first_worker = worker_statuses[0] if worker_statuses else {}

        return {
            "enabled": bool(mqtt_conf.get("enabled", False)),
            "connected": self.is_connected,
            "totalBrokers": len(self.workers),
            "connectedCount": connected_count,
            "brokers": worker_statuses,
            # 下位互換用フィールド
            "broker": first_worker.get("broker", mqtt_conf.get("broker", "")),
            "port": first_worker.get("port", mqtt_conf.get("port", 1883)),
            "clientId": first_worker.get("clientId", mqtt_conf.get("clientId", "voice-hub")),
            "baseTopic": first_worker.get("baseTopic", mqtt_conf.get("baseTopic", "voicehub")),
            "defaultTarget": first_worker.get("defaultTarget", mqtt_conf.get("defaultTarget", "")),
            "tls": first_worker.get("tls", mqtt_conf.get("tls", False)),
            "haDiscoveryEnabled": first_worker.get("haDiscoveryEnabled", mqtt_conf.get("haDiscoveryEnabled", True)),
            "haDiscoveryPrefix": first_worker.get("haDiscoveryPrefix", mqtt_conf.get("haDiscoveryPrefix", "homeassistant")),
            "receivedCount": total_received,
            "lastMessageAt": max([w.last_message_at for w in self.workers.values() if w.last_message_at], default=None),
            "lastError": next((w.last_error for w in self.workers.values() if w.last_error), None)
        }

    async def publish_event(self, sub_topic: str, payload: Dict[str, Any], retain: bool = False):
        """全接続ブローカーへイベントをマルチキャスト発行"""
        tasks = [w.publish_event(sub_topic, payload, retain=retain) for w in self.workers.values() if w.is_connected]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def publish_dnd_state(self):
        """全接続ブローカーへ現在の DND 状態をマルチキャスト発行"""
        tasks = [w.publish_dnd_state() for w in self.workers.values() if w.is_connected]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def publish_ha_discovery(self, clear: bool = False, broker_id: Optional[str] = None) -> Dict[str, Any]:
        """Home Assistant MQTT Auto-Discovery トピックを発行"""
        results = []
        target_workers = []
        if broker_id:
            w = self.workers.get(str(broker_id))
            if w:
                target_workers.append(w)
        else:
            # haDiscoveryEnabled が True のワーカーすべて
            target_workers = [w for w in self.workers.values() if w.conf.get("haDiscoveryEnabled", True)]

        if not target_workers:
            return {"success": False, "message": "対象となる有効な MQTT ブローカーがありません"}

        for w in target_workers:
            res = await w.publish_ha_discovery(clear=clear)
            results.append(res)

        total_count = sum(r.get("count", 0) for r in results if r.get("success"))
        return {
            "success": any(r.get("success") for r in results),
            "count": total_count,
            "action": "cleared" if clear else "published",
            "results": results
        }

    async def test_publish(self, text: str, target: Optional[str] = None, broker_id: Optional[str] = None):
        """テスト発話メッセージをパブリッシュ"""
        target_workers = []
        if broker_id:
            w = self.workers.get(str(broker_id))
            if w:
                target_workers.append(w)
        else:
            target_workers = [w for w in self.workers.values() if w.is_connected]

        if not target_workers:
            raise RuntimeError("接続中の MQTT ブローカーがありません")

        results = []
        for w in target_workers:
            base_topic = w.conf.get("baseTopic", "voicehub").rstrip("/")
            topic = f"{base_topic}/say/{target}" if target else f"{base_topic}/say"
            payload = json.dumps({"text": text, "target": target}, ensure_ascii=False)
            await w.publish(topic, payload)
            results.append({"broker": w.name, "topic": topic})

        return {"success": True, "publishedTo": results}

mqtt_service = MQTTService()
