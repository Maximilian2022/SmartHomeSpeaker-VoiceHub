# Smart Home Speaker Voice Hub Comprehensive Technical Manual (MANUAL-en.md) 📘

[日本語 (Japanese)](Manual.md) | **English**

This document serves as the comprehensive technical manual for **Smart Home Speaker Voice Hub**, covering system architecture, smart speaker integration specifications, the companion Homebridge plugin, Model Context Protocol (MCP) server, multi-MQTT broker connectivity, access control & perimeter security design, and the complete REST API reference omitted from [README-en.md](README-en.md).

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Network, Access Control & Security Architecture](#2-network-access-control--security-architecture)
   - 2.1 [Dual-Layer Perimeter Defense (LAN vs Cloudflare Tunnel)](#21-dual-layer-perimeter-defense-lan-vs-cloudflare-tunnel)
   - 2.2 [Webhook Token Authentication (WEBHOOK_TOKEN)](#22-webhook-token-authentication-webhook_token)
   - 2.3 [Web GUI Administrator Authentication (ADMIN_PASSWORD)](#23-web-gui-administrator-authentication-admin_password)
   - 2.4 [IPv6 Loopback Binding Architecture](#24-ipv6-loopback-binding-architecture)
   - 2.5 [Client Identification, IP Aliasing & Deduplication](#25-client-identification-ip-aliasing--deduplication)
3. [Target Resolution Macros & Speaker Control Specifications](#3-target-resolution-macros--speaker-control-specifications)
   - 3.1 [Target Notation & Macro Reference Table](#31-target-notation--macro-reference-table)
   - 3.2 [Speaker Type Auto-Detection & Resolution Algorithm](#32-speaker-type-auto-detection--resolution-algorithm)
   - 3.3 [Multi-Platform Latency Compensation Engine (Sync Engine)](#33-multi-platform-latency-compensation-engine-sync-engine)
4. [Text-to-Speech (TTS) & Audio Pipeline Specifications](#4-text-to-speech-tts--audio-pipeline-specifications)
   - 4.1 [Edge-TTS Parameters](#41-edge-tts-parameters)
   - 4.2 [Chime Audio Mixing (FFmpeg / Byte Concatenation)](#42-chime-audio-mixing-ffmpeg--byte-concatenation)
   - 4.3 [Audio Cache Management (MD5, LRU & Size Limits)](#43-audio-cache-management-md5-lru--size-limits)
   - 4.4 [Time-Based Auto Volume Curves](#44-time-based-auto-volume-curves)
   - 4.5 [TTS Engine Extensibility Architecture](#45-tts-engine-extensibility-architecture)
   - 4.6 [Scheduled Speech (Timer / Future Speech Reservation)](#46-scheduled-speech-timer--future-speech-reservation)
5. [Do Not Disturb (DND) & Meeting Mode Specifications](#5-do-not-disturb-dnd--meeting-mode-specifications)
   - 5.1 [DND Priority Evaluation Pipeline](#51-dnd-priority-evaluation-pipeline)
   - 5.2 [Three Suppression Modes (Skip / Whisper / Queue)](#52-three-suppression-modes-skip--whisper--queue)
   - 5.3 [Queue Persistence (WAL) & Safe Recovery on Startup](#53-queue-persistence-wal--safe-recovery-on-startup)
   - 5.4 [AI Auto-Summarization & Catch-Up for Queued Messages](#54-ai-auto-summarization--catch-up-for-queued-messages)
   - 5.5 [External Device & Shortcut Integration (Logitech G HUB / Stream Deck)](#55-external-device--shortcut-integration-logitech-g-hub--stream-deck)
6. [Disaster Alert, Emergency Information & Weather Integration (Japan Only)](#6-disaster-alert-emergency-information--weather-integration-japan-only)
   - 6.1 [P2P Quake WebSocket Integration (EEW / Seismic Intensity)](#61-p2p-quake-websocket-integration-eew--seismic-intensity)
   - 6.2 [JMA Weather Warning API Polling & Diff State Machine](#62-jma-weather-warning-api-polling--diff-state-machine)
   - 6.3 [JMA Weather Forecast Integration (Morning Summary Injection)](#63-jma-weather-forecast-integration-morning-summary-injection)
   - 6.4 [Notification Speaker Control & Urgent Mode](#64-notification-speaker-control--urgent-mode)
7. [AI Integration Engine (AI Service)](#7-ai-integration-engine-ai-service)
   - 7.1 [Supported Providers (Google Gemini / OpenAI / Local LLM)](#71-supported-providers-google-gemini--openai--local-llm)
   - 7.2 [Model Auto-Discovery & Resilient Fallback (503 / 429 Resilience)](#72-model-auto-discovery--resilient-fallback-503--429-resilience)
   - 7.3 [Morning Agenda Summary & Context Injection](#73-morning-agenda-summary--context-injection)
8. [Speaker & Audio Hardware Connection Specifications](#8-speaker--audio-hardware-connection-specifications)
   - 8.1 [Google Home / Nest (Google Cast)](#81-google-home--nest-google-cast)
   - 8.2 [Amazon Echo / Alexa (Remote Control & Atnr Token)](#82-amazon-echo--alexa-remote-control--atnr-token)
   - 8.3 [Apple HomePod (AirPlay 2 / pyatv)](#83-apple-homepod-airplay-2--pyatv)
   - 8.4 [ONVIF Network Camera (Two-Way Audio / Profile T)](#84-onvif-network-camera-two-way-audio--profile-t)
   - 8.5 [DLNA / UPnP Network Audio (MediaRenderer)](#85-dlna--upnp-network-audio-mediarenderer)
9. [Apple HomeKit / Homebridge Plugin Specifications (`homebridge-voicehub`)](#9-apple-homekit--homebridge-plugin-specifications-homebridge-voicehub)
   - 9.1 [Plugin Overview & Architecture](#91-plugin-overview--architecture)
   - 9.2 [Provided Accessory Specifications](#92-provided-accessory-specifications)
   - 9.3 [Configuration Schema (`config.json`)](#93-configuration-schema-configjson)
   - 9.4 [Setup Instructions](#94-setup-instructions)
10. [MCP (Model Context Protocol) Server Specifications](#10-mcp-model-context-protocol-server-specifications)
    - 10.1 [Architecture & Endpoints](#101-architecture--endpoints)
    - 10.2 [Provided Tools Reference](#102-provided-tools-reference)
    - 10.3 [AI Assistant Setup Examples (Claude Desktop / Cursor / Cline)](#103-ai-assistant-setup-examples-claude-desktop--cursor--cline)
11. [Multi-MQTT Broker & Home Assistant MQTT Discovery Specifications](#11-multi-mqtt-broker--home-assistant-mqtt-discovery-specifications)
    - 11.1 [Multi-Broker Connection Architecture](#111-multi-broker-connection-architecture)
    - 11.2 [Topic Design & Message Specifications](#112-topic-design--message-specifications)
    - 11.3 [Home Assistant MQTT Discovery Entity Specifications](#113-home-assistant-mqtt-discovery-entity-specifications)
    - 11.4 [Real-Time Connection Status Summary Board](#114-real-time-connection-status-summary-board)
12. [Web GUI Interface Specifications](#12-web-gui-interface-specifications)
    - 12.1 [macOS-Style 2-Column Vertical Navigation](#121-macos-style-2-column-vertical-navigation)
    - 12.2 [Speech History (Real-Time Recording, Replay, Preview)](#122-speech-history-real-time-recording-replay-preview)
    - 12.3 [Webhook Command Builder & Plugin Documentation Modal](#123-webhook-command-builder--plugin-documentation-modal)
    - 12.4 [Visual Feedback & Modern Micro-Animations](#124-visual-feedback--modern-micro-animations)
13. [Complete REST API Reference](#13-complete-rest-api-reference)
14. [File Structure & Persistent Directories](#14-file-structure--persistent-directories)
15. [Internal System Architecture (FastAPI Modules)](#15-internal-system-architecture-fastapi-modules)
    - 15.1 [Core Modules (`app/core/`)](#151-core-modules-appcore)
    - 15.2 [Service Modules (`app/services/`)](#152-service-modules-appservices)
    - 15.3 [Logging & Operational Infrastructure (Seamless Log & Startup Banner)](#153-logging--operational-infrastructure-seamless-log--startup-banner)

---

## 1. System Architecture Overview

Smart Home Speaker Voice Hub unifies 5 distinct smart speaker and network audio platforms (**Google Home / Cast**, **Amazon Echo / Alexa**, **Apple HomePod / AirPlay 2**, **ONVIF Network Cameras**, and **DLNA / UPnP MediaRenderer**) under a single abstraction layer, delivering synthesized speech (Edge-TTS, Azure, GCP, or local engines) to devices across your home network.

The backend is built entirely on **Python 3.14 + FastAPI** using an asynchronous event-driven architecture (`async/await`), providing rapid response times, low latency, and high concurrency.

```text
[External Webhook / IFTTT]    [Browser Web GUI]    [HomeKit / Siri]    [MCP Client]    [MQTT Broker]
          │                         │                    │                  │                │
          ▼                         ▼                    ▼                  ▼                ▼
    ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
    │                       FastAPI Core Engine (Python 3.14 Fully Async)                         │
    │                                                                                             │
    │  ┌───────────────────────┐  ┌───────────────────────────────────────┐  ┌─────────────────┐  │
    │  │ Security Perimeter    │  │ Deduplication & Priority Filter       │  │ MCP Server      │  │
    │  │ (Tunnel / Auth / IPv6)│  │ (DND / Meeting Keywords / Urgent)     │  │ (SSE / Tools)   │  │
    │  └───────────────────────┘  └───────────────────────────────────────┘  └─────────────────┘  │
    │                                                                                             │
    │  ┌───────────────────────┐  ┌───────────────────────────────────────┐  ┌─────────────────┐  │
    │  │ Edge TTS + Chime Mix  │  │ In-Memory Queue & DND Disk WAL        │  │ Multi MQTT Hub  │  │
    │  │ (LRU Caching & Probe) │  │ (Non-blocking & DND Queue Recovery)   │  │ (HA Discovery)  │  │
    │  └───────────────────────┘  └───────────────────────────────────────┘  └─────────────────┘  │
    │                                                                                             │
    │  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
    │  │               Cross-Platform Sync Engine (Static Offset Compensation)                 │  │
    │  └───────────────────────────────────────────────────────────────────────────────────────┘  │
    └───┬──────────────────┬──────────────────┬──────────────┬───────────────┬────────────────────┘
        │                  │                  │              │               │
        ▼                  ▼                  ▼              ▼               ▼
 [ Google Cast ]    [ Amazon Alexa ]   [ Apple HomePod ] [ ONVIF Camera ] [ DLNA / UPnP ]
(pychromecast)     (Remote Control)   (pyatv / AirPlay) (go2rtc / Profile T) (async_upnp_client)
```

---

## 2. Network, Access Control & Security Architecture

To accommodate both public incoming webhooks from external automation services (IFTTT, Slack, Home Assistant, etc.) and private Web GUI management on the home LAN, Voice Hub implements multi-layered perimeter security.

### 2.1 Dual-Layer Perimeter Defense (LAN vs Cloudflare Tunnel)

When exposing an external domain (e.g., `voicehub.example.com`) using Cloudflare Tunnel (`cloudflared`), the server inspects the ingress path of each incoming request:

* **Ingress Detection Criteria (`is_tunnel_request`)**:
  - Checks if headers include `CF-Ray`, `CF-Connecting-IP`, or `CF-IPCountry`.
  - Checks if the HTTP `Host` header matches the `TUNNEL_DOMAIN` environment variable.
* **Access Policy**:
  - **Tunnel Requests**: Access is strictly limited to **`/api/say`**, **`/api/webhook`**, and **`/mcp/sse`, `/mcp/messages`**.
  - Access to the Web GUI (`/`, `index.html`, `app.js`) and administrative management APIs (`/api/settings`, `/api/devices`, `/api/history`, etc.) is immediately blocked with **`403 Forbidden`**.
  - This structurally prevents unauthorized configuration tampering, speech history inspection, or credential leakage even if the public tunnel domain is discovered.

### 2.2 Webhook Token Authentication (WEBHOOK_TOKEN)

When the environment variable `WEBHOOK_TOKEN` (or a token set in Web GUI settings) is configured, incoming webhook calls require authentication.

* **Supported Token Transport Methods (choose any one)**:
  1. `Authorization: Bearer <WEBHOOK_TOKEN>` header
  2. `X-API-KEY: <WEBHOOK_TOKEN>` header
  3. URL query parameter `?token=<WEBHOOK_TOKEN>`
  4. JSON request body `"token": "<WEBHOOK_TOKEN>"` field
* **Automatic LAN Bypass**:
  - Same-origin browser requests originating from private LAN subnets (`127.0.0.1`, `::1`, `192.168.x.x`) via the Web GUI (`Referer` or `Sec-Fetch-Site: same-origin`) are automatically exempt from token requirements for convenience.

### 2.3 Web GUI Administrator Authentication (ADMIN_PASSWORD)

When `ADMIN_PASSWORD` (or `WEB_PASSWORD`) is set, access to the Web GUI and all management APIs (`/api/*`) is password-protected.

* **Authentication Mechanisms**:
  - **Session Cookie (`auth_token`)**: Submitting the password to `/api/auth/login` issues a cryptographically secure random token (SHA-256), stored as an HttpOnly cookie with a 30-day lifetime.
  - **Direct Header (for external scripts)**: Supplying `X-Admin-Password: <password>` or `Authorization: Bearer <password>` grants direct access to management endpoints without an interactive login.

### 2.4 IPv6 Loopback Binding Architecture

In certain domestic IPv6 environments (such as IPoE / NGN networks), external IPv6 packets can reach home servers directly without router port forwarding. Voice Hub prevents inadvertent public exposure by strictly separating IP bindings:

* **IPv4**: Bound to `0.0.0.0:8080` (accessible from the local LAN).
* **IPv6**: Bound strictly to **`[::1]:8080` (Loopback Only)**.
* This blocks direct attacks against external global IPv6 addresses while preserving standard local resolution for `localhost` (`::1`).

### 2.5 Client Identification, IP Aliasing & Deduplication

* **Client Identification**: Automatically identifies callers via `from`, `client`, or `sender` parameters, IP alias mappings (friendly names configured in settings, e.g., "Front Door Intercom", "Home Assistant"), and User-Agents (IFTTT, Slack, Discord, etc.), displaying colored badges in the speech history.
* **Deduplication Engine (`deduplication`)**:
  - Prevents rapid repeated announcements triggered by motion sensors or camera bursts.
  - If identical text is sent from the same source within the cooldown window (`cooldownSeconds`, default 30s), playback is safely skipped and `200 OK` (`deduplicated: true`) is returned.

---

## 3. Target Resolution Macros & Speaker Control Specifications

### 3.1 Target Notation & Macro Reference Table

In the `/api/say` endpoint, `devices` or `targets` accepts individual device names, raw IP addresses, short macros, or custom device groups.

| Target Identifier | Target Speakers & Behavior |
|---|---|
| `ALL` or `*` | **All speakers in the home**. Concurrently targets the whole-home Google Cast group, all Amazon Echo devices, all HomePods, registered ONVIF cameras, and DLNA renderers. |
| `GH:ALL` / `GOOGLE:ALL` | All Google Home / Nest devices in the home (prefers Cast groups). |
| `AL:ALL` / `ALEXA:ALL` | All Amazon Echo devices in the home (prefers Alexa Everywhere group). |
| `HP:ALL` / `HOMEPOD:ALL` | All Apple HomePod devices in the home. |
| `ONVIF:ALL` / `CAM:ALL` | All registered ONVIF network cameras. |
| `DLNA:ALL` | All registered DLNA / UPnP network speakers. |
| `default` | System default speaker (specified via `GOOGLE_HOME_IP` or Web GUI). |
| Custom Group Name (e.g., `1F`, `LDK`) | Expands custom speaker combinations defined under "Device Groups" in settings. |
| Display Name (e.g., `Living Room`) | Resolves devices via case-insensitive partial substring match. |
| `alexa:<DeviceName>` | Explicitly targets a specific Amazon Echo device. |
| `homepod:<IP or MAC>` | Explicitly targets a specific Apple HomePod device. |
| `onvif:<IP>` | Explicitly targets a specific ONVIF network camera. |
| `dlna:<IP>` | Explicitly targets a specific DLNA / UPnP renderer. |
| Raw IPv4 (e.g., `192.168.1.50`) | Directly targets a Google Cast device by IP address. |

### 3.2 Speaker Type Auto-Detection & Resolution Algorithm

Resolution proceeds in the following priority order:

1. **Macro & Group Expansion**: Expands `ALL`, `CAM:ALL`, `DLNA:ALL`, or custom groups into concrete device lists.
2. **Google Cast Group Aggregation (`preferNativeGroups`)**:
   - Broadcasting to multiple Google Home units individually can produce echoes due to Wi-Fi jitter.
   - When `ALL` or whole-home scope is selected, individual Cast IPs are consolidated into a native **Google Cast Group (port 32xxx)**, enabling native protocol-level synchronization.
3. **Protocol Dispatching**:
   - **Google Cast**: `type: google` (pychromecast)
   - **Amazon Alexa**: `type: alexa` (Alexa Remote Control)
   - **Apple HomePod**: `type: homepod` (pyatv AirPlay 2)
   - **ONVIF Camera**: `type: onvif` (go2rtc Two-Way Audio / Profile T)
   - **DLNA Renderer**: `type: dlna` (UPnP AVTransport / RenderingControl)
4. **Deduplication**: Automatically suppresses duplicate streaming calls if an IP or target is referenced multiple times.

### 3.3 Multi-Platform Latency Compensation Engine (Sync Engine)

Because Google Cast, Amazon Alexa (cloud proxy), and Apple HomePod (AirPlay 2) utilize distinct transport protocols, their internal startup latencies vary.

* **Offset Delay Controls (`alexaDelayMs`, `homepodDelayMs`, `googleDelayMs`)**:
  - Compensates for Alexa's cloud latency by intentionally introducing a millisecond delay to responsive local protocols (Google Cast / HomePod), synchronizing audio across different speaker ecosystems. Offsets are customizable (0–5000ms) under `settings.json`.

---

## 4. Text-to-Speech (TTS) & Audio Pipeline Specifications

### 4.1 Edge-TTS Parameters

Leverages Edge-TTS Neural voice models with full SSML support.

* **Standard Voices (`voice`)**:
  - `ja-JP-NanamiNeural`: Nanami (Female, clear and natural tone, standard default)
  - `ja-JP-KeitaNeural`: Keita (Male, calm and professional)
  - `ja-JP-AoiNeural`: Aoi (Female, gentle and warm)
  - `ja-JP-DaichiNeural`: Daichi (Male, deep and distinct)
  - `ja-JP-MayuNeural`: Mayu (Female, cheerful and lively)
  - `ja-JP-NaokiNeural`: Naoki (Male, news broadcast style)
  - `ja-JP-ShioriNeural`: Shiori (Female, news broadcast style)
* **Acoustic Parameters**:
  - **Speech Rate (`rate`)**: `+0%` (standard), `+20%` (fast), `-10%` (slow)
  - **Pitch (`pitch`)**: `+0Hz` (standard), `+50Hz` (higher), `-30Hz` (lower)
  - **Volume Gain (`volume`)**: `+0%` (standard), `+20%`, `-10%`

### 4.2 Chime Audio Mixing (FFmpeg / Byte Concatenation)

Prepends a chime sound before the speech synthesis to capture attention.

* **Chime Types (`chime`)**:
  - `dingdong`: Standard doorbell chime (`/public/sound/dingdong.mp3`)
  - `bell`: Soft notification bell (`/public/sound/bell.mp3`)
  - `none`: No chime (immediate speech only)
* **Audio Concatenation**:
  - Uses system `ffmpeg` to re-encode and concatenate audio streams as 128kbps MP3, eliminating pops and sample-rate mismatches.
  - Automatically falls back to binary MP3 frame joining if `ffmpeg` is unavailable.
* **Duration Measurement**:
  - Measures millisecond-accurate audio length via `ffprobe` to coordinate playback completion across sync pipelines (with character-count estimation as fallback).

### 4.3 Audio Cache Management (MD5, LRU & Size Limits)

Generated audio clips are saved to persistent cache storage (Docker volume `smart_speaker_cache` / `/public/voice`).

* **Cache Key**:
  `MD5(text + "_" + voice + "_" + rate + "_" + pitch + "_" + volume + "_" + chimeType)`
* **LRU Access Updates**:
  When a cached file is re-requested, its disk modification timestamp (`mtime`) is updated to extend its cache lifetime.
* **Automatic Eviction**:
  - Evaluates cache size hourly.
  - If total size exceeds `MAX_CACHE_SIZE_MB` (default: 1024MB), files with the oldest access times are purged until capacity shrinks to 90% of the maximum limit.

### 4.4 Time-Based Auto Volume Curves

Dynamically adapts speaker volume based on the time of day (morning wake-up, daytime active hours, night quiet hours).

* **Overnight Rule Support**:
  - Example: `23:00`–`07:00` set to `25%`, `07:00`–`09:00` set to `60%`, `09:00`–`18:00` set to `70%`.
* When an explicit `volumeLevel` is omitted from an API call, the curve's scheduled volume is applied automatically.

### 4.5 TTS Engine Extensibility Architecture

While Voice Hub operates autonomously with Edge-TTS, it features a pluggable architecture supporting multiple local engines (running across your LAN) as well as official cloud APIs (Azure Speech / Google Cloud TTS).

```text
                     ┌──────────────────────────────────────────────┐
                     │          Speech Request (say / urgent)       │
                     └──────────────────────┬───────────────────────┘
                                            │
                ┌────────────────────────────┴───────────────────────────┐
                ▼ (Normal Announcement)                                  ▼ (Urgent Alert: urgent=True)
     [Selected Provider Synthesis]                               [Fastest-Wins Parallel Racing]
     ├─► Azure Speech Service (Official Cloud SLA)               ├─► Azure Speech
     ├─► Google Cloud TTS (Neural2/Standard)                     ├─► Google Cloud TTS
     ├─► Local TTS Engines (Dynamic Multiple)                    ├─► VOICEVOX / SHAREVOX / COEIROINK
     │   ├─► VOICEVOX (GPU Server / Desktop)                     └─► Additional Local Engines
     │   ├─► SHAREVOX                                                        │
     │   └─► COEIROINK (192.168.1.50, etc.)                        asyncio.wait(FIRST_COMPLETED)
     └─► Edge-TTS (Default when Azure is unconfigured)                       │
                │                                                            ▼
        (Timeout / Connection Error)                             Fastest Audio Broadcast Immediately
                │                                                (Remaining slow tasks cancelled)
                ▼
     【Cascading Fallback】
     Azure → GCP → Local Engines → 🛡️ Safety Net: Edge-TTS
     (Ensures domestic announcements are never dropped)
```

#### 4.5.1 Supported TTS Providers

| Provider | Type | Protocol | Highlights & Recommended Voice |
|---|---|---|---|
| **Azure Speech Service** | Cloud (Official / Free tier) | Cognitive Services REST API | **Recommended**. Microsoft official enterprise cloud TTS with guaranteed SLA. When enabled, Edge-TTS is placed on standby as an emergency safety net. Recommended: `azure:ja-JP-NanamiNeural`. |
| **Google Cloud TTS (GCP)** | Cloud (Pay-as-you-go / Free tier) | Cloud Text-to-Speech API | High-fidelity Neural2, Journey, and Wavenet voices. Recommended: `gcp:ja-JP-Neural2-B`. |
| **Local TTS Engines (VOICEVOX / SHAREVOX / COEIROINK)** | Local / LAN | REST API / Dynamic Multi-Engine | Connect **unlimited local instances** on your LAN. Supports popular models (Zundamon, Shikoku Metan, etc.) with pre-initialization support (`initialize_speaker`). |
| **Edge-TTS (Built-in)** | Cloud (Free) | Unofficial Web Endpoint | **Built-in default**. 7 natural Japanese voices without requiring API keys. May be subject to upstream endpoint adjustments. |

#### 4.5.2 Resilient Automatic Fallback Design
* If an external engine is unreachable, PC is asleep, or synthesis exceeds `timeoutSeconds` (default: 5.0s), Voice Hub automatically falls back to **Edge-TTS (Nanami)** to guarantee delivery.
* Fallback occurrences are marked in the speech history log (`fallback: true`).

#### 4.5.3 Urgent Alert Parallel Generation (Fastest Wins)
* For critical alerts (Earthquake Early Warnings, severe weather alerts, `urgent: true`), synthesis requests are dispatched concurrently to all enabled engines.
* Using `asyncio.wait(..., return_when=FIRST_COMPLETED)`, the **first audio stream completed is immediately routed to speakers**, and slower tasks are cancelled, ensuring minimal alert latency.

#### 4.5.4 Cloud Free Tier Monthly Usage Tracker
* Tracks monthly character usage for Google Cloud TTS (1M chars/mo Neural2, 4M chars/mo Standard) and Azure Speech (500k chars/mo F0 tier) to prevent accidental charges.
* Persisted in `data/tts_usage.json` with automatic monthly reset on the 1st of each month.
* Displays real-time progress bars in the Web GUI settings.

#### 4.5.5 Cloud TTS API Key Setup Guides

<details>
<summary><strong>💡 Google Cloud Text-to-Speech (GCP) API Key Setup</strong></summary>

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
2. Go to "APIs & Services" → "Library", search for **"Cloud Text-to-Speech API"**, and click "Enable".
3. Under "APIs & Services" → "Credentials", click "+ Create Credentials" → **"API Key"**.
4. Copy the generated key (`AIzaSy...`) and paste it into the Web UI "API Key" field.
5. *(Recommended)*: Restrict the key to the Cloud Text-to-Speech API under key settings.

* **Free Tier**: 1 million characters/month for Neural2/Journey voices; 4 million characters/month for Standard voices.
</details>

<details>
<summary><strong>💡 Azure Speech Service Key & Region Setup</strong></summary>

1. Sign in to the [Azure Portal](https://portal.azure.com/).
2. Search for "Speech Services" and click "Create".
3. Select your Subscription and Resource Group, and choose a Region (e.g., **`japaneast`**).
4. Under Pricing Tier, select **"Free F0"** and deploy the resource.
5. Once created, open the resource, navigate to "Keys and Endpoint" under Resource Management.
6. Copy **Key 1** to the "Speech Key" field, and enter your location (e.g., `japaneast`) into the "Region" field.

* **Free Tier**: F0 plan includes 500,000 characters/month.
</details>

### 4.6 Scheduled Speech (Timer / Future Speech Reservation)

Schedule announcements for future execution (e.g., "Remind me in 10 minutes that the laundry is done", "Dinner announcement at 19:30").

* **Supported Parameter Names**:
  `at`, `time`, `scheduled_at`, `datetime` (treated as interchangeable aliases)
* **Accepted Time Formats**:
  1. **Relative Delays**: `+10m` (10 minutes), `+30m` (30 minutes), `+1h` (1 hour), `+45s` (45 seconds), supporting units `s` (seconds), `m` (minutes), `h` (hours), `d` (days).
  2. **Wall-Clock Times**: `19:30`, `08:00:00` (scheduled for today; if passed, schedules for tomorrow).
  3. **Full Datetime**: ISO 8601 strings (e.g., `2026-10-19T15:00:00`).
* **Execution Lifecycle**:
  1. **Immediate Async Response**: When a future timestamp is detected, a background task is scheduled and returns HTTP 200 OK immediately (`{"status": "scheduled", "task_id": "...", "scheduled_at": "..."}`), preventing caller timeouts.
  2. **Scheduled Trigger**: Upon reaching the specified time, the speech pipeline resolves targets, applies DND rules, and broadcasts the audio.
  3. **Zero / Past Times**: Requests with empty or elapsed times execute immediately without delay.
  4. **Universal Integration**: Fully accessible via Web UI (quick chips), REST API (`/api/say`), Webhook, MQTT (`voicehub/say`), and MCP Server (`speak(at=...)`, `list_scheduled_speeches`, `cancel_scheduled_speech`).

---

## 5. Do Not Disturb (DND) & Meeting Mode Specifications

Prevents unexpected loud speaker broadcasts during sleep hours or remote work video meetings.

### 5.1 DND Priority Evaluation Pipeline

Incoming speech requests are evaluated against the following priority chain:

```text
[Incoming Speech Request]
         │
         ├─► 1. Emergency Bypass (urgent === true or bypassDnd === true)
         │         └─► 【Immediate Broadcast】 (Bypasses all DND, meetings, and mutes)
         │
         ├─► 2. One-Tap Quick Mute (Top bar mute / manualUntil)
         │         └─► 【DND Active】 (Suppressed until expiration or manual release)
         │
         ├─► 3. Calendar Meeting Check (Google Calendar Sync)
         │         └─► Active event matching meeting keywords (MTG, Meeting, Zoom, etc.)
         │                   └─► 【DND Active】 (Suppressed until meeting end time)
         │
         ├─► 4. Scheduled Quiet Hours (Weekday work hours, bedtime, etc.)
         │         └─► Current time matches active recurring DND rules
         │                   └─► 【DND Active】 (Suppressed until schedule ends)
         │
         └─► 5. No Rules Matched
                   └─► 【Normal Broadcast】
```

### 5.2 Three Suppression Modes (Skip / Whisper / Queue)

1. **`skip`**: Discards the announcement silently. The suppression reason is logged in history.
2. **`whisper`**: Broadcasts quietly at a reduced volume (default: `10%`).
3. **`queue`**: Stores the message in a retention queue, automatically playing it back once meetings or DND end.

### 5.3 Queue Persistence (WAL) & Safe Recovery on Startup

* **Disk Persistence (`/app/data/dnd_queue.json`)**: Queued messages are immediately persisted to disk.
* **Startup Safe Recovery**: On server restart, queue flushing is paused until the initial Google Calendar synchronization completes, preventing accidental loud bursts if a meeting is actively in progress.

### 5.4 AI Auto-Summarization & Catch-Up for Queued Messages

When multiple messages accumulate in the queue (default: 2 or more), Voice Hub invokes an AI provider (Gemini / OpenAI) to condense them into a single, cohesive spoken summary rather than playing every message back-to-back.

### 5.5 External Device & Shortcut Integration (Logitech G HUB / Stream Deck)

Enables one-touch DND control from mouse buttons, keyboard G keys, or dedicated macro pads during gaming, deep work, or sudden conference calls, without needing to open the Web UI.

* **Supported Script Formats**:
  - **`.vbs` (VBScript / Recommended)**: Built using Windows standard `MSXML2.ServerXMLHTTP`. Executes 100% silently in the background with zero command-prompt flickering.
  - **`.bat` (Windows Batch)**: Uses Windows built-in `curl.exe` for quick testing.
  - **`.sh` (Bash Shell Script)**: Ready for macOS and Linux desktops.
* **One-Tap Action Types**:
  - **Toggle DND (`toggle`)**: Inverts state between Normal and Muted (ideal for mouse side buttons).
  - **30m / 60m Meeting Mute (`30m` / `60m`)**: Temporarily buffers speech for meetings.
  - **Unmute & Flush (`unmute`)**: Manually unblocks and summarizes all accumulated messages.
* **One-Click Generation via Web UI**:
  - Download pre-configured scripts with embedded local host URLs and authentication directly from Web UI (Extended Settings > Do Not Disturb).
  - **Logitech G HUB**: Assign via "System" -> "Launch Application" to any G key or mouse button.
  - **Elgato Stream Deck**: Drag the "System" -> "Open" action to a key and select the downloaded script.

---

## 6. Disaster Alert, Emergency Information & Weather Integration (Japan Only)

### 6.1 P2P Quake WebSocket Integration (EEW / Seismic Intensity)

Maintains a persistent WebSocket connection to the P2P Quake API (`wss://api.p2pquake.net/v2/ws`) for low-latency JMA disaster monitoring.

* **Earthquake Early Warning (EEW / Code `556`)**:
  - Broadcasts immediate warnings when strong shaking is detected.
  - **Duplicate Suppression**: Tracks `issue.eventId` in memory to prevent repeated warnings across updates 2 and 3 for the same event.
  - **Cancellation Alerts**: Automatically announces if JMA issues a cancellation report (`cancelled: true`).
* **Seismic Intensity Bulletins (Code `551`)**:
  - Configurable minimum intensity threshold (Intensity 1–7) to ignore minor tremors.
  - Generates unique event keys (`time_hypocenter_maxScale`) to avoid duplicate announcements.

### 6.2 JMA Weather Warning API Polling & Diff State Machine

Polls official JMA endpoints (`https://www.jma.go.jp/bosai/warning/data/warning/{prefCode}.json`) every 5 minutes.

* **Municipal Precision**: Tracks warning arrays for specific municipality codes (`class20`, e.g., Chiyoda Ward `1310100`).
* **Flexible Severity Filtering**: Choose between Emergency Warnings Only, Warnings & Above (default), or Advisories Included.
* **Cancellation Notices**: Optional notification when active warnings are lifted.
* **Diff State Machine**: Only broadcasts changes since the previous check.

### 6.3 JMA Weather Forecast Integration (Morning Summary Injection)

Extracts current day weather, high/low temperatures, and precipitation probabilities from JMA weekly forecasts. Automatically injects weather conditions and practical advice (e.g., bringing an umbrella) into the morning briefing before reading calendar events.

### 6.4 Notification Speaker Control & Urgent Mode

The **"📢 Notification Speakers"** setting under Disaster Alerts offers 3 scopes:
1. **`all` (All speakers)**: Broadcasts across Google Home, Echo, and HomePod throughout the home.
2. **`default` (Default speaker only)**: Plays on the designated primary device.
3. **`specific` (Selected devices)**: Restricts playback to chosen rooms or devices.

When **Urgent Mode** is active, alerts bypass active DND and meetings with highest priority.

### 6.5 Smart Home Disaster Automation Triggers (Apple Home / Home Assistant / Alexa / Google Home)

Real-time disaster and severe weather alert states can be used as native "triggers" for smart home automations.

* **HomeKit (Apple Home) Virtual Motion Sensors**:
  - The Homebridge plugin (`homebridge-voicehub`) exposes 3 virtual motion sensors (`Service.MotionSensor`) to Apple Home:
    - `EEW Alert` (Earthquake Early Warning)
    - `Weather Warning` (Meteorological warning)
    - `Rain Approaching` (Approaching rain / precipitation alarm)
  - During active alerts, `MotionDetected = true` is asserted, resetting to `false` when cleared or after the timeout duration.
  - **Automation Examples**:
    - Turn on all corridor and living room smart lights to 100% cool white upon Earthquake Early Warning.
    - Cut off smart plugs supplying power to high-heat appliances or space heaters.
    - Automatically close motorized storm shutters upon heavy rain or storm warnings.
* **Home Assistant (MQTT Discovery) Binary Sensors**:
  - Entities are automatically registered via MQTT Discovery:
    - `binary_sensor.<node_id>_eew_alert` (`device_class: safety`)
    - `binary_sensor.<node_id>_weather_warning` (`device_class: safety`)
    - `binary_sensor.<node_id>_rain_alarm` (`device_class: moisture`)
* **Simulation & Test Function**:
  - Test smart home automations on-demand via the Web UI "Test ON for 10s" buttons or `POST /api/disaster/triggers/test`.


---

## 7. AI Integration Engine (AI Service)

### 7.1 Supported Providers (Google Gemini / OpenAI / Local LLM)

Easily switch between AI providers by entering an API key or custom endpoint in settings:

* **Google Gemini API**: Current models including `gemini-2.5-flash` and `gemini-2.5-pro`
* **OpenAI API**: `gpt-4o`, `gpt-4o-mini`, `o3-mini`, etc.
* **Local LLM (Ollama)**: Local instances (e.g., `http://localhost:11434` running Llama 3 or Qwen)
* **DeepSeek API**: `deepseek-chat` and compatible models

### 7.2 Model Auto-Discovery & Resilient Fallback (503 / 429 Resilience)

* **Automatic Model Normalization**: Automatically migrates deprecated models found in configuration files to current recommendations (`gemini-2.5-flash`).
* **Dynamic Discovery**: The "Refresh Models" button queries provider APIs for the latest available models.
* **503 / 429 Failover**: If external AI APIs encounter transient rate limits or outages, Voice Hub gracefully falls back to rule-based templated summaries to keep announcements running.

### 7.3 Morning Agenda Summary & Context Injection

During morning briefings, Voice Hub supplies the AI engine with structured context:
1. Current date, time, and day of the week
2. Synchronized calendar events for the day (times, titles, locations)
3. Local weather forecasts, high/low temperatures, and precipitation odds
4. Custom user prompt directives (e.g., "Polite and concise tone", "Focus on schedule highlights")

---

## 8. Speaker & Audio Hardware Connection Specifications

### 8.1 Google Home / Nest (Google Cast)
- **Protocol**: Google Cast (castv2 / Avahi mDNS discovery)
- **Library**: `pychromecast` (Native Python implementation)
- **Features**: Supports speaker groups configured in the Google Home app for synchronized playback without audio delay.

### 8.2 Amazon Echo / Alexa (Remote Control & Atnr Token)
- **Protocol**: Amazon Alexa Remote Control (HTTPS / Cookie Session)
- **Integration Methods**:
  1. **Browser Proxy Login (Recommended)**: Initiate login from the Web GUI and complete Amazon authentication in your browser.
  2. **Refresh Token (`Atnr|...`) Manual Entry**: Extract a refresh token using `npx alexa-cookie2` and store it in the Web GUI or `.my.env` (`REFRESH_TOKEN`).
- **Everywhere Group Consolidation**: When broadcasting to all Echo units (`devices: ["ALL"]` or `AL:ALL`), Voice Hub consolidates requests into Amazon's native "Everywhere" group command, avoiding 429 rate limits and multi-room echoes.

### 8.3 Apple HomePod (AirPlay 2 / pyatv)
- **Protocol**: Apple AirPlay 2 / RAOP (Bonjour / mDNS discovery)
- **Library**: `pyatv`
- **Network Requirements**:
  - The Voice Hub host/container and Apple HomePods must reside on the **same local subnet/LAN**.
  - Docker `network_mode: host` is strongly recommended. Router AP isolation or cross-VLAN setups will block mDNS discovery.

### 8.4 ONVIF Network Camera (Two-Way Audio / Profile T)
- **Protocol**: ONVIF Profile T (WS-Discovery on UDP 3702, go2rtc RTSP backchannel)
- **Codec**: G.711 PCMU (8kHz 64kbps)
- **Integration**: WS-Discovery detects cameras on the local network automatically. Cameras with two-way audio (Profile T) can be registered with a single click.
- **Robust Communication & Retry Handling**: Audio push requests to go2rtc implement a 30-second timeout (`httpx.Timeout(30.0)`) and async retries to handle camera boot latencies or Wi-Fi fluctuations.

### 8.5 DLNA / UPnP Network Audio (MediaRenderer)
- **Protocol**: UPnP AVTransport / RenderingControl (SSDP on UDP 1900, SOAP control)
- **Compatible Devices**: Bose SoundTouch, Sonos, Denon HEOS, Yamaha MusicCast, foobar2000 UPnP, etc.
- **Integration**: Auto-detected via SSDP scanning in the ONVIF/DLNA tab; ready for playback without authentication.

---

## 9. Apple HomeKit / Homebridge Plugin Specifications (`homebridge-voicehub`)

Includes a dedicated companion plugin **`homebridge-voicehub`** for Homebridge users.

### 9.1 Plugin Overview & Architecture
- **Directory**: `plugins/homebridge-voicehub/`
- **Type**: Dynamic Platform Plugin (`VoiceHubPlatform`)
- **Design**: **Zero external runtime dependencies**, utilizing Node.js 18+ native `fetch` for lightweight and dependable operation.

### 9.2 Provided Accessory Specifications
1. **📢 Preset Speech Switches (`VoiceHubPresetSwitch`)**:
   - Maps recurring messages ("Dinner is ready", "Bath is ready") to HomeKit switches.
   - Triggering via Siri calls the Voice Hub API and auto-resets the switch to OFF upon completion.
2. **🌙 DND / Meeting Mode Switch (`VoiceHubDndSwitch`)**:
   - Bi-directionally synchronized with Voice Hub's DND state.
   - Toggle DND manually or link with Apple Home "Good Night" bedtime scenes and automations.
3. **🔊 Speaker Volume Sliders (`VoiceHubSpeakerAccessory`)**:
   - Maps speakers as light accessories with brightness sliders.
   - Adjust volume via Siri commands (e.g., "Set living room volume to 50%").

### 9.3 Configuration Schema (`config.json`)

```json
{
  "platforms": [
    {
      "platform": "VoiceHubPlatform",
      "name": "VoiceHub",
      "host": "http://127.0.0.1:8080",
      "webhookToken": "YOUR_OPTIONAL_TOKEN",
      "enableDndSwitch": true,
      "autoDiscoverSpeakers": true,
      "volumeAsLightbulb": true,
      "pollInterval": 30,
      "presets": [
        {
          "name": "Dinner is ready",
          "text": "Dinner is served. Please come to the dining room.",
          "target": "ALL",
          "volume": 70
        },
        {
          "name": "Bath is ready",
          "text": "The bath is ready.",
          "target": "ALL",
          "volume": 60
        }
      ]
    }
  ]
}
```

### 9.4 Setup Instructions

```bash
cd plugins/homebridge-voicehub
npm install    # or bun install
npm run build  # or bun run build
npm link
```
Alternatively, search for `homebridge-voicehub` in the Homebridge Config UI X plugins tab to install.

---

## 10. MCP (Model Context Protocol) Server Specifications

Features a built-in FastAPI-native **MCP (Model Context Protocol) Server**, allowing AI assistants such as Claude Desktop, Cursor, and Cline to interact directly with your smart speakers.

### 10.1 Architecture & Endpoints
- **Protocol**: MCP 2024-11-05 (JSON-RPC 2.0 over Server-Sent Events)
- **Endpoints**:
  - `GET /mcp/sse`: Client connection SSE stream.
  - `POST /mcp/messages`: JSON-RPC 2.0 message dispatch endpoint.
- **Security**:
  - Requires `Authorization: Bearer <WEBHOOK_TOKEN>` header when `WEBHOOK_TOKEN` is configured.
  - Safely accessible via Cloudflare Tunnel for remote AI client interactions.

### 10.2 Provided Tools Reference

| Tool Name | Description | Key Arguments |
|---|---|---|
| `speak` | Broadcast or schedule a voice announcement to speakers | `text` (required), `target`, `volume`, `voice`, `urgent`, `at` (optional future time: `+10m`, `19:30`, etc.) |
| `list_speakers` | List all discovered speakers across Google, Alexa, HomePod, ONVIF, and DLNA | None |
| `get_status` | Retrieve system status (DND state, queued messages, default device) | None |
| `set_dnd` | Enable or disable Do Not Disturb (DND) / Meeting Mode | `enabled` (required), `durationMinutes`, `reason` |
| `get_history` | Retrieve recent speech history log entries (last N items) | `limit` (default: 10) |
| `list_scheduled_speeches` | List all currently scheduled future speech tasks | None |
| `cancel_scheduled_speech` | Cancel a scheduled future speech task by its ID | `task_id` (required) |

### 10.3 AI Assistant Setup Examples (Claude Desktop / Cursor / Cline)

The Web GUI MCP settings screen provides a toggle between **"🏠 Local LAN"** and **"🌐 Internet (Cloudflare Tunnel)"**, dynamically generating configuration JSON snippets for your client.

Example configuration for `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "voicehub": {
      "url": "http://127.0.0.1:8080/mcp/sse",
      "headers": {
        "Authorization": "Bearer YOUR_OPTIONAL_TOKEN"
      }
    }
  }
}
```

---

## 11. Multi-MQTT Broker & Home Assistant MQTT Discovery Specifications

Voice Hub includes a multi-broker MQTT client capable of maintaining concurrent connections to multiple brokers (e.g., local Mosquitto and cloud MQTT) for Node-RED, Home Assistant, and custom automations.

### 11.1 Multi-Broker Connection Architecture
- **Library**: `aiomqtt` (Asynchronous MQTT 3.1.1 / 5.0 client)
- **Features**:
  - Connect to multiple brokers simultaneously.
  - **mDNS (.local) Resolution**: Built-in Zeroconf resolver (`MDNSResolver`) dynamically resolves `.local` hostnames inside Docker without modifying `/etc/hosts` or `extra_hosts`.
  - Supports MQTTS (TLS encryption) and username/password authentication.
  - Automatic exponential backoff reconnection.

### 11.2 Topic Design & Message Specifications

| Topic | Type | Description & Payload Example |
|---|---|---|
| `voicehub/say` | Subscribe (Incoming) | Trigger speech. Accepts JSON: `{"text": "Hello", "devices": ["ALL"], "at": "+10m"}` or plain text |
| `voicehub/dnd/set` | Subscribe (Incoming) | Toggle DND: `ON`, `OFF`, `30`, `60`, `120` |
| `voicehub/status` | Publish (Outgoing) | Periodic status reports. JSON: `{"status": "online", "dnd": false, "queued": 0}` |
| `voicehub/availability` | LWT (Last Will) | Broker connection status: `online` / `offline` |

*Note: Specifying `"at": "+10m"` or `"at": "19:30"` in `voicehub/say` schedules the announcement automatically.*

### 11.3 Home Assistant MQTT Discovery Entity Specifications
When "Home Assistant Discovery" is enabled, Voice Hub publishes discovery payloads to `homeassistant/<component>/voicehub/.../config`, generating entities in Home Assistant:
- **Text (`text`)**: Announcement text input field
- **Switch (`switch`)**: DND toggle switch
- **Select (`select`)**: Target speaker selection dropdown
- **Number (`number`)**: Master volume slider
- **Sensors (`sensor`)**: Last spoken message, DND status

### 11.4 Real-Time Connection Status Summary Board
The Web GUI displays a live status dashboard for all registered brokers:
- **Active Brokers Badge**: Live tally of connected vs registered brokers (e.g., `1/1 Online`)
- **Host Info**: Connected IP / port specifications
- **Topic Counters**: Real-time incoming/outgoing message metrics
- **Home Assistant Status**: Discovery state and published entity counts

---

## 12. Web GUI Interface Specifications

### 12.1 macOS-Style 2-Column Vertical Navigation
The settings panel features a clean two-column layout:
- **Left Column**: Category-based menu (General & Speech, Integrations & APIs, Advanced System Settings).
- **Right Column**: Responsive configuration cards corresponding to the selected category.

### 12.2 Speech History (Real-Time Recording, Replay, Preview)
Maintains a rolling log of the last 100 announcements:
- Color-coded badges denote request sources (Web UI, schedules, calendar, external APIs).
- One-click actions for Re-broadcast, Browser Preview, and Text Copy.

### 12.3 Webhook Command Builder & Plugin Documentation Modal
- **Webhook Command Builder**: Interactively select speakers and enter text to generate ready-to-copy cURL, JSON, and IFTTT snippets.
  - **⏰ Scheduled Speech (at / time) Section**: Quick-select chips (+5m, +10m, +15m, +30m, +1h) update commands in real time.
- **Plugin Documentation Modal**: Built-in modal guide providing step-by-step Homebridge setup instructions and sample `config.json` blocks.

### 12.4 Visual Feedback & Modern Micro-Animations
- **Two-Stage Save Button Feedback**: Save buttons morph into a spinner during transmission and an emerald checkmark on completion before resetting.
- **Gradient Glow on Active Controls**: Active segments and filter buttons illuminate with vibrant gradients and subtle glow shadows.
- **Scanning Progress Bar**: Visual progress indicator activates during ONVIF and DLNA network device discovery scans.

---

## 13. Complete REST API Reference

All API endpoints return JSON responses.

### 13.1 Speech & Webhook API
- **`POST /api/say`** / **`GET /api/say`**: Trigger an announcement on speakers.
  - **Key Parameters**:
    - `text` (required): Spoken text
    - `targets` / `devices` / `target`: Target speakers (array or single string)
    - `volumeLevel` / `volume`: Volume level (0–100)
    - `rate` / `speed`: Speech rate (`+10%`, `-10%`, etc.)
    - `pitch`: Pitch adjustment (`+5Hz`, `-5Hz`, etc.)
    - `voice`: TTS model name (Edge-TTS, Azure, or local engines)
    - `chime`: Pre-announcement chime sound (`dingdong`, `bell`, `none`)
    - `urgent` / `bypassDnd`: Force bypass active DND rules
    - `at` / `time` / `scheduled_at`: Scheduled execution time (`+10m`, `19:30`, etc.)
- **`POST /api/webhook`** / **`GET /api/webhook`**: Trigger announcements via external webhook format.
- **`POST /api/tts`**: Synthesize and download raw audio file (MP3).

### 13.2 Scheduled Speech API
- **`GET /api/schedule/speeches`**: List all currently scheduled future speech tasks.
- **`POST /api/schedule/speeches/{id}/cancel`**: Cancel a specific scheduled speech task.

### 13.3 Auth API
- **`GET /api/auth/status`**: Check authentication configuration and current login state.
- **`POST /api/auth/login`**: Authenticate using administrator password (sets session cookie).
- **`POST /api/auth/logout`**: Log out and invalidate session cookie.

### 13.4 History & Queue API
- **`GET /api/history`**: Retrieve recent speech history log (last 100 items).
- **`DELETE /api/history`**: Clear speech history log.
- **`GET /api/queue`**: List pending queued webhook items.

### 13.5 Device & Speaker API
- **`GET /api/devices`**: List all discovered speakers and speaker groups.
- **`POST /api/devices/default`**: Update default speaker IP address.

### 13.6 Schedule API
- **`GET /api/schedules`**: List scheduled recurring broadcasts.
- **`POST /api/schedules`**: Create a new recurring schedule.
- **`PUT /api/schedules/{id}`**: Update an existing schedule.
- **`DELETE /api/schedules/{id}`**: Delete a schedule.
- **`POST /api/schedules/{id}/toggle`**: Enable or disable a schedule.
- **`POST /api/schedules/{id}/run`**: Manually trigger a test run of a schedule.

### 13.7 Calendar API
- **`GET /api/calendar/events`**: List synchronized calendar events.
- **`POST /api/calendar/sync`**: Force immediate resync with Google Calendar.
- **`POST /api/calendar/summary`**: Trigger test run of morning agenda summary speech.

### 13.8 Do Not Disturb (DND) API
- **`GET /api/dnd/status`**: Get current DND status and queued message count.
- **`POST /api/dnd/toggle`**: Toggle DND state (Normal ⇄ Muted).
- **`POST /api/dnd/mute`**: Activate immediate mute (Parameters: `durationMinutes`, `until`, `reason`).
- **`POST /api/dnd/unmute`**: Deactivate mute and flush queued messages.
- **`POST /api/dnd/quick`**: Toggle one-tap quick mute mode on or off (Parameters: `minutes`, `reason`).
- **`GET /api/dnd/script/preview`**: Preview integration script content (Query: `action`, `format`, `host`, `password`).
- **`GET /api/dnd/script/download`**: Download integration script (.vbs / .bat / .sh).
- **`GET /api/dnd/history`**: Retrieve DND suppression log records.
- **`DELETE /api/dnd/history`**: Clear DND suppression history.

### 13.9 Disaster & Weather API (Japan Only)
- **`GET /api/disaster/settings`**: Get disaster and weather monitoring configuration.
- **`PUT /api/disaster/settings`**: Update disaster and weather monitoring configuration.
- **`GET /api/disaster/areas`**: List available municipality codes and area master records.
- **`GET /api/disaster/weather`**: Retrieve latest weather and advice for configured area.
- **`GET /api/disaster/status`**: Get WebSocket status and currently active warnings.
- **`POST /api/disaster/test`**: Trigger simulated disaster alert broadcast.
- **`GET /api/disaster/triggers`**: Get current smart home disaster automation trigger states (EEW, weather warning, rain).
- **`POST /api/disaster/triggers/test`**: Trigger simulated smart home disaster trigger state (JSON: `target`, `duration`).


### 13.10 AI API
- **`GET /api/ai/status`**: Check AI service connectivity and configuration.
- **`POST /api/ai/test`**: Validate AI provider API key.
- **`GET /api/ai/models`**: Query available models dynamically from provider.
- **`POST /api/ai/summarize-test`**: Generate test summary preview for queued messages.
- **`POST /api/ai/calendar-test`**: Generate test summary preview for calendar briefing.

### 13.11 System Settings API
- **`GET /api/settings`**: Retrieve system configuration.
- **`PUT /api/settings`**: Update system configuration.
- **`POST /api/settings/sync-test`**: Broadcast multi-speaker audio sync test tone.

### 13.12 Hardware Specific API
- **`GET /api/alexa/status`**: Check Alexa integration status.
- **`POST /api/alexa/auth/start`**: Start Alexa proxy authentication server.
- **`POST /api/alexa/auth/stop`**: Stop Alexa proxy authentication server.
- **`POST /api/alexa/token`**: Register Alexa refresh token directly.
- **`POST /api/alexa/logout`**: Disconnect Alexa account.
- **`GET /api/homepod/status`**: List discovered Apple HomePod devices.
- **`POST /api/homepod/scan`**: Force mDNS rescan for Apple HomePods.
- **`POST /api/onvif/scan`**: Trigger network scan for ONVIF cameras and DLNA speakers.
- **`POST /api/onvif/register`**: Register, update, or remove ONVIF/DLNA devices.
- **`POST /api/onvif/test`**: Test audio transmission to an ONVIF or DLNA target.
- **`POST /api/onvif/default-auth`**: Save default camera credentials.

### 13.13 MQTT API
- **`GET /api/mqtt/status`**: Check connection status of all configured MQTT brokers.
- **`POST /api/mqtt/test`**: Test connection to a specific broker configuration.
- **`POST /api/mqtt/reconnect`**: Force reconnection of all configured MQTT brokers.

### 13.14 External TTS Provider API
- **`GET /api/tts/voices`**: List available voices across all active providers (Edge, VOICEVOX, GCP, Azure, etc.).
- **`GET /api/tts/providers`**: Get provider status, URLs, and monthly free tier usage.
- **`POST /api/tts/providers/test`**: Validate connectivity and initialize speaker models for a provider.
- **`PUT /api/tts/providers/settings`**: Update TTS provider configurations and timeout thresholds.

### 13.15 System Logs API
- **`GET /api/logs`**: Retrieve unified system logs merging in-memory ring buffer and persistent log files (`limit`, `level`).

---

## 14. File Structure & Persistent Directories

```text
/root/google-home-voicetext-docker/
├── .my.env                     # Environment variables (secrets, ports, etc.)
├── .my.env.sample              # Environment configuration template
├── docker-compose.yml          # Production Docker Compose specification
├── Dockerfile                  # Python 3.14 + go2rtc container build
├── Manual.md                   # Japanese comprehensive technical manual
├── MANUAL-en.md                # English comprehensive technical manual (this document)
├── README.md                   # Japanese project README
├── README-en.md                # English project README
├── CONTRIBUTING.md             # Japanese contributing guide
├── CONTRIBUTING-en.md          # English contributing guide
├── SECURITY.md                 # Japanese security policy
├── SECURITY-en.md              # English security policy
│
├── data/                       # [Named Volume: smart_speaker_data]
│   ├── settings.json           # System configuration (DND, disaster, AI, devices, MQTT, TTS)
│   ├── tts_usage.json          # Cloud TTS (GCP/Azure) monthly character consumption tracker
│   ├── schedules.json          # Scheduled recurring broadcasts
│   ├── dnd_queue.json          # DND queued messages (WAL)
│   ├── homepod_devices.json    # HomePod discovery cache
│   └── .alexa.cookie           # Alexa session cookie
│
├── public/                     # Static Web frontend assets
│   ├── index.html              # Web GUI Single Page Application
│   ├── app.js                  # Frontend controller logic
│   ├── style.css               # Glassmorphism styling rules
│   ├── sound/                  # Audio chimes (dingdong.mp3, bell.mp3, etc.)
│   ├── plugins/                # Distributable static plugin packages
│   └── voice/                  # [Named Volume: smart_speaker_cache] TTS audio cache
│
├── app/                        # Backend implementation (Python 3.14 + FastAPI)
│   ├── main.py                 # FastAPI application, lifespan events, middleware
│   ├── config.py               # Pydantic Settings environment configuration
│   ├── core/                   # Perimeter security, auth, logging, and deduplication
│   ├── routers/                # REST API, SSE, and MCP routers
│   └── services/               # Services: TTS, Cast, Alexa, HomePod, ONVIF/DLNA, DND, MQTT, MCP
│       └── tts/                # TTS provider modules (Edge, Voicevox, Sharevox, Coeiroink, GCP, Azure)
│
├── plugins/
│   └── homebridge-voicehub/    # Homebridge platform plugin
│       ├── package.json
│       ├── tsconfig.json
│       ├── config.schema.json
│       ├── README.md
│       └── src/
│
└── bin/
    └── alexa_remote_control.sh # Alexa automation script
```

---

## 15. Internal System Architecture (FastAPI Modules)

Designed so all operations run non-blockingly on the asynchronous event loop (`asyncio`).

### 15.1 Core Modules (`app/core/`)
- **`security.py`**:
  Manages Cloudflare Tunnel verification, administrator session cookies, and Webhook Bearer tokens.
- **`deduplication.py`**:
  In-memory anti-spam deduplication engine suppressing rapid duplicate requests from the same client.
- **`logger.py`**:
  Unified logger with standard output capture (`TeeStream`), access log filtering, and credential masking.
- **`log_rotator.py`**:
  Container log size monitor supporting automatic rotation and zstd / gzip compression.

### 15.2 Service Modules (`app/services/`)
- **`speech_service.py`**:
  Coordinates speech synthesis, DND evaluation, `syncOffsets` delay management, parallel dispatch across speakers, and persistent history logging.
- **`dnd_service.py`**:
  Evaluates calendar, schedule, and quick mute rules; manages disk queue persistence (`dnd_queue.json`) and post-meeting flushing.
- **`tts_service.py`**:
  Dynamic provider routing, Edge-TTS fallback on timeout, Fastest-Wins parallel racing for urgent alerts, FFmpeg chime concatenation, and LRU cache eviction.
- **`tts/` package**:
  - `base.py`: `BaseTtsProvider` abstract interface
  - `usage_tracker.py`: Monthly character consumption tracking for GCP/Azure
  - `edge_provider.py`: Edge-TTS provider
  - `voicevox_provider.py`: VOICEVOX / SHAREVOX / COEIROINK (v2 API) client
  - `gcp_provider.py`: Google Cloud Text-to-Speech client
  - `azure_provider.py`: Azure Cognitive Services Speech client
- **`cast_service.py`**:
  `pychromecast` integration for Google Cast device and speaker group discovery and playback.
- **`alexa_service.py`**:
  Amazon Echo announcement dispatch and browser proxy login management.
- **`homepod_service.py`**:
  `pyatv` integration for Apple HomePod Bonjour mDNS discovery and AirPlay 2 streaming.
- **`onvif_service.py`**:
  WS-Discovery for camera detection and RTSP two-way audio backchannel streaming via bundled `go2rtc`.
- **`dlna_service.py`**:
  SSDP renderer discovery and UPnP AVTransport / RenderingControl SOAP playback control.
- **`calendar_service.py`**:
  Asynchronous iCal synchronization across multiple Google Calendars, meeting keyword detection, and briefing generation.
- **`disaster_service.py`**:
  Maintains P2P Quake WebSocket connectivity, polls JMA warning APIs, and manages event deduplication.
- **`ai_service.py`**:
  Gemini and OpenAI API integration, dynamic model discovery, and 503/429 failover.
- **`mqtt_service.py`**:
  `aiomqtt` multi-broker client handling topic subscriptions, broadcasts, and Home Assistant MQTT Discovery.
- **`mcp_service.py`**:
  Model Context Protocol JSON-RPC 2.0 processor, SSE connection management, and tool routing (`speak`, `list_speakers`, `get_status`, etc.).
- **`scheduler_service.py`**:
  In-memory scheduled speech task manager, relative/absolute datetime parser, background execution loop, and cancellation handling.

### 15.3 Logging & Operational Infrastructure (Seamless Log & Startup Banner)
- **Seamless Log Mechanism (`core/logger.py`)**:
  - **Memory Buffer**: Holds the last 2,000 log entries in a `collections.deque` ring buffer for instant Web GUI viewing.
  - **Persistent Log (`logs/app.log`)**: Continuously written to disk to survive container restarts.
  - **Automatic Merging (`GET /api/logs`)**: Chronologically merges in-memory records with pre-restart disk logs, ensuring smooth debugging across reboots.
- **Startup Banner**:
  - Emits an ASCII art banner on FastAPI startup recording system version, Python runtime, active IP/port bindings, enabled speaker integrations (Cast, Alexa, HomePod, ONVIF, DLNA), multi-MQTT broker configurations, and MCP listener status.
