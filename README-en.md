# Smart Speaker Voice Hub 🎙️

[日本語 (Japanese)](README.md) | **English** | [📖 Manual & Technical Specifications (MANUAL-en.md)](MANUAL-en.md)

A smart home voice announcement hub that unifies heterogeneous speakers across your home—including Google Home / Nest, Amazon Alexa (Echo), Apple HomePod, ONVIF network cameras, and DLNA network audio—enabling automated natural text-to-speech (Edge-TTS) broadcasts triggered via Webhooks, AI assistants, and external APIs.

Originally created as a personal home automation utility to deliver daily notifications and reminders comfortably and effortlessly throughout the house.

> [!TIP]
> 📖 **Looking for step-by-step setup guides or full technical details?**  
> For speaker-by-speaker setup procedures (Google Cast, Alexa, HomePod, ONVIF cameras, DLNA), AI assistant configurations, HomeKit/Siri setup, and complete REST API references, please check out the **[Comprehensive Technical Manual (MANUAL-en.md)](MANUAL-en.md)**!

---

## 🌿 Key Features

- **Unified Multi-Speaker Broadcasting**:
  Deliver audio announcements to individual speakers or simultaneously broadcast across Google Home (Nest), Amazon Alexa (Echo), Apple HomePod, ONVIF network cameras, and DLNA / UPnP audio devices throughout your home.
- **Effortless Speech Synthesis & Extensible Engine**:
  Out-of-the-box text-to-speech powered by community-maintained Edge-TTS, with seamless plug-and-play extension and cascading fallback to official Azure Speech Service, Google Cloud TTS, or fully offline local engines (VOICEVOX, SHAREVOX, COEIROINK).
  *(Note: Edge-TTS relies on unofficial endpoints; for mission-critical guarantees, using the official Azure Speech Service free-tier is supported and recommended).*
- **Intuitive Web UI & Real-Time Controls**:
  Easily send announcements directly from your desktop or mobile browser. Includes live browser preview, filtered speech history (by rain alarm, disaster, schedule, etc.), one-click replay, and a real-time rain radar overlay with official JMA color legends.
- **Scheduled & Future Speech (Timers & Reminders)**:
  Schedule broadcasts for future execution with intuitive syntax, such as `at: "+10m"` (remind in 10 minutes) or `at: "19:30"` (dinner announcement at 19:30). Configurable via Web UI, Webhook, MQTT, or MCP.
- **Daily Schedules & Calendar Sync**:
  Automate daily recurring announcements (morning greetings, trash collection reminders) and sync with Google Calendar for proactive meeting alerts and morning agenda summaries.
- **Do Not Disturb (DND) & Real-time Synchronization**:
  Automatically suppress announcements during sleep hours or active online meetings (synced with calendar events), with support for quiet whispering, message queuing, or AI-generated catch-up summaries once meetings end. Features real-time Server-Sent Events (SSE) synchronization: muting or unmuting via Apple HomeKit or external scripts (Logitech G HUB / Stream Deck) instantly updates the Web UI button and banner without page reloads.
- **Apple HomeKit & Siri Integration**:
  Includes a dedicated companion Homebridge plugin (`homebridge-voicehub`). Create custom announcement switches (e.g., "Dinner is ready") in the Apple Home app and trigger broadcasts hands-free using Siri.
- **Smart Disaster & Weather Automation Triggers (Japan Only)**:
  Integrates with open disaster data from the Japan Meteorological Agency (JMA) and P2P Quake to automatically broadcast Earthquake Early Warnings (EEW), severe weather alerts, and approaching rain forecasts. Additionally, these alert states are exposed as native automation triggers for Apple HomeKit (virtual motion sensors) and Home Assistant (MQTT binary sensors), enabling safety automations such as turning on escape route lighting or cutting off high-heat appliance plugs during emergency alerts. *(Note: This feature uses domestic Japanese APIs and is intended for use within Japan).*
- **Seamless External Integrations (Webhook / MQTT / MCP Server)**:
  Native integrations with automation platforms like IFTTT, Home Assistant (with MQTT Discovery), Node-RED, and a built-in MCP (Model Context Protocol) server allowing AI assistants such as Claude Desktop and Cursor to operate your speakers directly.


---

## 🚀 Getting Started

The easiest and recommended method is running via Docker Compose. Multi-architecture images (amd64 / arm64) are published on [Docker Hub (madpiero/smarthomespeaker-voicehub)](https://hub.docker.com/r/madpiero/smarthomespeaker-voicehub), allowing instant deployment on Raspberry Pi, NAS, or PC without build times.

### Method A: For General Users (Easiest — No git clone needed)

Create a working directory, download `docker-compose.yml`, and launch:

```bash
# 1. Create a working directory
mkdir -p voicehub && cd voicehub

# 2. Download docker-compose.yml
curl -O https://raw.githubusercontent.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/main/docker-compose.yml

# 3. Start container (automatically pulls pre-built image from Docker Hub)
docker compose up -d
```

### Method B: For Developers (Build & Hot-Reload Locally)

Clone the repository to automatically use local builds with bind-mounted source directories for immediate hot-reloading:

```bash
git clone https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub.git
cd SmartHomeSpeaker-VoiceHub
docker compose up -d --build
```

---

Once the container is up and running, open your web browser and navigate to:

```text
http://<SERVER_IP_ADDRESS>:8080
```
*(If accessing from the host machine itself, use `http://localhost:8080`)*

> 💡 **Initial Setup & Speaker Pairing**  
> On your first visit, the Web UI will automatically discover compatible speakers on your local network.  
> For devices requiring credentials or specialized authentication (Amazon Echo, Apple HomePod, Tapo ONVIF cameras, DLNA renderers), follow the detailed setup guides in **[Manual (MANUAL-en.md) - Speaker Connection Specifications](MANUAL-en.md#8-smart-speaker--audio-device-connection-specifications)**.

---

## 💡 Basic Usage

### 1. Announce from the Web UI
Open the Web UI in your browser, enter your message in the text field, and click **"Speak"** to play the announcement on registered speakers. Click **"Preview"** to listen locally in your browser before broadcasting.

### 2. Trigger from External Sources (Webhook Example)
Send announcements via simple cURL commands or automation scripts:

```bash
curl -X POST http://<SERVER_IP>:8080/api/say \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Dinner is ready",
    "devices": ["ALL"]
  }'
```

To schedule a delayed or timed announcement, include `"at": "+10m"` (relative time) or `"at": "19:30"` (scheduled time):

```bash
# Example: Announce a reminder 10 minutes from now
curl -X POST http://<SERVER_IP>:8080/api/say \
  -H "Content-Type: application/json" \
  -d '{
    "text": "It has been 10 minutes since the bath finished filling",
    "devices": ["ALL"],
    "at": "+10m"
  }'
```

*Tip: Use the interactive **Webhook Command Builder** under the Webhook & Tunnel tab in the Web UI to generate customized cURL, JSON, and IFTTT commands with quick-select delay chips (+5m, +10m, etc.).*

### 3. Use with Siri & Apple Home (Homebridge Plugin)
For homes utilizing Homebridge, install the bundled **`homebridge-voicehub`** plugin:
- Expose routine messages ("Dinner's ready", "Laundry is done") as virtual switches in Apple Home, callable via Siri.
- Control speaker volume sliders or sync DND status directly with Apple Sleep scenes.

For comprehensive setup instructions, see the [Plugin Guide (plugins/homebridge-voicehub/README.md)](plugins/homebridge-voicehub/README.md).

---

## 📖 Technical Manual & Specifications (MANUAL-en.md)

This system offers extensive configuration options and integration capabilities tailored for flexible smart home environments.  
For complete technical details, setup walkthroughs, and architecture designs, refer to the **[Comprehensive Technical Manual (MANUAL-en.md)](MANUAL-en.md)**:

- **[Speaker Connection Specifications (MANUAL-en.md Chapter 8)](MANUAL-en.md#8-smart-speaker--audio-device-connection-specifications)**:
  Amazon Echo (Atnr token extraction), Apple HomePod (AirPlay 2 pairing), ONVIF cameras (Two-Way Audio), DLNA renderers
- **[Extensible TTS Engine Architecture (MANUAL-en.md Section 4.5)](MANUAL-en.md#45-external-tts-engine-extensibility-tts-engine-extensibility)**:
  Azure Speech Service, Google Cloud TTS, and offline engines (VOICEVOX, SHAREVOX, COEIROINK) with cascading fallback
- **[Apple HomeKit / Homebridge Plugin (MANUAL-en.md Chapter 9)](MANUAL-en.md#9-apple-homekit--homebridge-plugin-specifications-homebridge-voicehub)**:
  Siri voice announcements, Home app custom switches, volume sliders, and DND synchronization
- **[Smart Disaster & Weather Triggers (MANUAL-en.md Chapter 6)](MANUAL-en.md#6-emergency-alerts-disaster-info-and-weather-forecast-integration-specifications)**:
  Automated JMA Earthquake Early Warnings (EEW), weather alarms, approaching rain radar, and HomeKit / MQTT safety triggers
- **[Model Context Protocol (MCP) Server (MANUAL-en.md Chapter 10)](MANUAL-en.md#10-mcp-model-context-protocol-server-specifications)**:
  Operating speakers and checking status directly from AI assistants (Claude Desktop, Cursor, Cline)
- **[Multi-MQTT Broker Connections (MANUAL-en.md Chapter 11)](MANUAL-en.md#11-multi-mqtt-broker-integration-specifications)**:
  Simultaneous multi-broker connections, Home Assistant MQTT Discovery auto-registration, topic subscriptions
- **[Complete REST API Reference (MANUAL-en.md Chapter 12)](MANUAL-en.md#12-complete-rest-api-specification-reference)**:
  Detailed schemas and examples for `/api/say`, `/api/devices`, `/api/dnd`, `/api/disaster`, and more
- **[Network Perimeter Security & Access Control (MANUAL-en.md Chapter 2)](MANUAL-en.md#2-network-access-control-and-security-architecture)**:
  LAN vs Cloudflare Tunnel boundary defense, Webhook bearer tokens, and administrative password protection

---

## 🤝 Community & Contributing

We welcome bug reports, feature suggestions, documentation enhancements, and pull requests!

- **Questions & Ideas**: Feel free to share in **[GitHub Discussions](https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/discussions)**.
- **Contribution Guidelines**: See our **[Contributing Guide (CONTRIBUTING-en.md)](CONTRIBUTING-en.md)** for development setup and coding standards.
- **Code of Conduct**: Please follow the community standards in our **[Code of Conduct (CODE_OF_CONDUCT.md)](CODE_OF_CONDUCT.md)**.
- **Security Reports**: For security vulnerabilities, please refer to our **[Security Policy (SECURITY-en.md)](SECURITY-en.md)** for private reporting guidelines.

---

## 📜 License & Acknowledgments

This project is licensed under the **[MIT License](LICENSE)**.
For third-party open-source software licenses and copyright notices, please refer to **[Third-Party Licenses (THIRD_PARTY_LICENSES.md)](THIRD_PARTY_LICENSES.md)**.

### Special Thanks
We extend our deepest gratitude to the developers and communities who share their valuable research and open-source libraries in smart home automation and speech synthesis:

- **[google-home-voicetext](https://github.com/sikkimtemi/google-home-voicetext-docker)** (by Taro TAKAHASHI) - The wonderful original inspiration for smart speaker voice notifications
- **[edge-tts](https://github.com/rany2/edge-tts)** - Providing natural, expressive voice synthesis
- **[PyChromecast](https://github.com/home-assistant-libs/pychromecast)** - Reliable communication framework for Google Cast devices
- **[pyatv](https://github.com/postlund/pyatv)** - AirPlay 2 streaming foundation for Apple HomePod
- **[alexa-remote-control](https://github.com/thorsten-gehrig/alexa-remote-control)** - Invaluable insight into Amazon Echo automation
- **[go2rtc](https://github.com/AlexxIT/go2rtc)** - High-performance two-way audio streaming to network cameras
- **[aiomqtt](https://github.com/sbtinstruments/aiomqtt)** - Asynchronous MQTT communication foundation
