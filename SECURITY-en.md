# Security Policy

[日本語 (Japanese)](SECURITY.md) | **English**

Thank you for using "Smart Home Speaker Voice Hub" and for helping improve its security.
This project strives to maintain robust security so that it can be operated safely across home networks and external webhooks.

---

## 1. Supported Versions

Security fixes and feature updates are primarily targeted at the `main` branch (latest release).

| Version / Branch | Supported | Notes |
|---|:---:|---|
| **`main` branch (Latest commit / Latest release)** | **✅ Supported** | Security patches and bug fixes are actively provided. |
| Prior releases / Older commits | ❌ Unsupported | We strongly recommend upgrading to the latest version. |

---

## 2. Reporting a Vulnerability

If you discover a security vulnerability or concern regarding this software, **please do NOT file a public issue**. Instead, report it privately using one of the following methods:

> [!CAUTION]
> Posting vulnerability details, exploitation steps, or proofs of concept in public issues or discussion forums risks exploitation by malicious actors before a patch is released. Please report all vulnerabilities privately.

### 1. GitHub Private Vulnerability Reporting (Recommended)
You can report directly and confidentially to maintainers via the **"Report a vulnerability"** button located on the repository's **[Security Tab](https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/security)**.

### 2. Preliminary Inquiry via GitHub Discussions
For general questions, architecture security concerns, or configuration discussions, feel free to use **[GitHub Discussions](https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/discussions)**.
*Please do not include confidential credentials or specific exploit payloads in public discussions.*

---

## 3. What to Include in Your Report

To help us investigate and remediate the issue as quickly as possible, please include:

- Affected component (API endpoints, Web UI, Homebridge plugin, authentication middleware, etc.)
- Vulnerability category (Authentication bypass, command injection, sensitive data exposure, XSS, etc.)
- Step-by-step reproduction instructions or a minimal Proof of Concept (PoC)
- Environment details (OS, Docker version, reverse proxy / Cloudflare Tunnel configuration, etc.)

---

## 4. Remediation Process

1. **Acknowledgment**: Upon receiving a report, we will review and investigate as promptly as possible (as an open-source project managed by individual contributors, responses are provided on a best-effort basis).
2. **Verification & Fix**: We reproduce the issue, develop a patch, and verify the fix across test environments.
3. **Release & Notice**: We publish an updated release containing the fix and notify the reporter upon resolution.

---

## 5. Out of Scope

The following items are outside the scope of this repository's security vulnerability program:

- **Third-Party Service Specifications & Upstream Downtime**:
  - Disruptions caused by upstream changes in third-party services (e.g., Edge-TTS unofficial endpoints, Amazon Alexa remote control scripts).
- **User Misconfigurations**:
  - Issues arising from weak or default `TOKEN_SECRET` / passwords, or exposing the container directly to the public internet without proper authentication.
- **DoS / DDoS Attacks**:
  - Service disruptions caused by volumetric flooding or heavy traffic (which should be mitigated via reverse proxies, Cloudflare, or network firewalls).
