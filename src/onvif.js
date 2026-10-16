const dgram = require('dgram');
const http = require('http');
const https = require('https');
const crypto = require('crypto');
const path = require('path');
const fs = require('fs');
const { execFile } = require('child_process');
const settingsManager = require('./settings');

const WS_DISCOVERY_PROBE = `<?xml version="1.0" encoding="utf-8"?>
<Envelope xmlns:tds="http://www.onvif.org/ver10/device/wsdl" 
          xmlns="http://www.w3.org/2003/05/soap-envelope" 
          xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <Header xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">
    <wsa:MessageID>urn:uuid:MESSAGE_ID</wsa:MessageID>
    <wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
    <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>
  </Header>
  <Body>
    <Probe xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
           xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
           xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery">
      <Types>dn:NetworkVideoTransmitter tds:Device</Types>
      <Scopes />
    </Probe>
  </Body>
</Envelope>`;

class OnvifManager {
  constructor() {
    this.cachedScanResults = [];
    this.isScanning = false;
    this.go2rtcApiUrl = process.env.GO2RTC_API_URL || 'http://127.0.0.1:1984';
  }

  /**
   * ONVIF WS-Security Header (PasswordDigest)
   */
  _buildWsSecurityHeader(username, password) {
    // ONVIF規格準拠: ミリ秒なしのUTC ISO文字列 (YYYY-MM-DDTHH:mm:ssZ)
    const created = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
    const nonceBytes = crypto.randomBytes(16);
    const nonceB64 = nonceBytes.toString('base64');

    const sha = crypto.createHash('sha1');
    sha.update(Buffer.concat([
      nonceBytes,
      Buffer.from(created, 'ascii'),
      Buffer.from(password, 'ascii')
    ]));
    const digestB64 = sha.digest('base64');

    return `
    <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
                   xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
      <wsse:UsernameToken>
        <wsse:Username>${username}</wsse:Username>
        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">${digestB64}</wsse:Password>
        <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">${nonceB64}</wsse:Nonce>
        <wsu:Created>${created}</wsu:Created>
      </wsse:UsernameToken>
    </wsse:Security>`;
  }

  /**
   * SOAP リクエスト送信
   */
  async sendSoap(urlStr, action, bodyXml, username = '', password = '') {
    return new Promise((resolve, reject) => {
      const url = new URL(urlStr);
      const isHttps = url.protocol === 'https:';
      const secHeader = (username && password) ? this._buildWsSecurityHeader(username, password) : '';

      const soapXml = `<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:tds="http://www.onvif.org/ver10/device/wsdl"
               xmlns:trt="http://www.onvif.org/ver10/media/wsdl">
  <soap:Header>
    ${secHeader}
  </soap:Header>
  <soap:Body>
    ${bodyXml}
  </soap:Body>
</soap:Envelope>`;

      const options = {
        hostname: url.hostname,
        port: url.port || (isHttps ? 443 : 80),
        path: url.pathname + url.search,
        method: 'POST',
        headers: {
          'Content-Type': `application/soap+xml; charset=utf-8; action="${action}"`,
          'Content-Length': Buffer.byteLength(soapXml)
        },
        timeout: 4000
      };

      const req = (isHttps ? https : http).request(options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(data);
          } else {
            reject(new Error(`HTTP ${res.statusCode}: ${data.slice(0, 300)}`));
          }
        });
      });

      req.on('error', reject);
      req.on('timeout', () => {
        req.destroy();
        reject(new Error('SOAP Request Timeout'));
      });
      req.write(soapXml);
      req.end();
    });
  }

  /**
   * LAN 内の ONVIF デバイスを WS-Discovery でスキャン
   */
  async scanDevices(options = {}) {
    let timeoutMs = 3500;
    let authUser = '';
    let authPass = '';
    if (typeof options === 'number') {
      timeoutMs = options;
    } else if (typeof options === 'object' && options !== null) {
      if (options.timeoutMs && !isNaN(options.timeoutMs)) timeoutMs = options.timeoutMs;
      authUser = options.username || '';
      authPass = options.password || '';
    }

    if (this.isScanning) {
      return this.cachedScanResults;
    }
    this.isScanning = true;

    const discoveredMap = new Map();

    await new Promise((resolve) => {
      const client = dgram.createSocket({ type: 'udp4', reuseAddr: true });
      const msgId = crypto.randomUUID();
      const probeData = Buffer.from(WS_DISCOVERY_PROBE.replace('MESSAGE_ID', msgId), 'utf-8');

      client.on('error', (err) => {
        console.warn('[ONVIF Discovery Error]', err.message);
        try { client.close(); } catch (e) {}
        resolve();
      });

      client.on('message', (msg, rinfo) => {
        const raw = msg.toString('utf-8');
        const ip = rinfo.address;

        if (!discoveredMap.has(ip)) {
          discoveredMap.set(ip, {
            ip,
            xaddrs: [],
            scopes: [],
            types: [],
            rawXml: raw
          });
        }

        const dev = discoveredMap.get(ip);
        // XAddrs 抽出
        const xaddrMatch = raw.match(/<[^:]*:?XAddrs[^>]*>([^<]+)<\/[^:]*:?XAddrs>/i);
        if (xaddrMatch) {
          xaddrMatch[1].trim().split(/\s+/).forEach(x => {
            if (!dev.xaddrs.includes(x)) dev.xaddrs.push(x);
          });
        }
        // Scopes 抽出
        const scopesMatch = raw.match(/<[^:]*:?Scopes[^>]*>([^<]+)<\/[^:]*:?Scopes>/i);
        if (scopesMatch) {
          scopesMatch[1].trim().split(/\s+/).forEach(s => {
            if (!dev.scopes.includes(s)) dev.scopes.push(s);
          });
        }
      });

      client.bind(0, () => {
        try {
          client.setBroadcast(true);
          client.setMulticastTTL(2);
          client.send(probeData, 0, probeData.length, 3702, '239.255.255.250');
          // ブロードキャスト宛てにも送信
          client.send(probeData, 0, probeData.length, 3702, '255.255.255.255');
        } catch (e) {
          console.warn('[ONVIF Discovery Send Error]', e.message);
        }
      });

      setTimeout(() => {
        try { client.close(); } catch (e) {}
        resolve();
      }, timeoutMs);
    });

    const onvifConfig = settingsManager.get().onvif || {};
    const defaultUser = authUser || onvifConfig.defaultUsername || 'admin';
    const defaultPass = authPass || onvifConfig.defaultPassword || '';

    const registeredList = onvifConfig.registeredDevices || [];

    // スキャンで見つかった各デバイスの情報を並列で詳細化 (Scope, Model, Profile T 判定)
    const deviceEntries = Array.from(discoveredMap.entries());
    const parsePromises = deviceEntries.map(async ([ip, info]) => {
      let port = 8000;
      let onvifUrl = `http://${ip}:8000/onvif/device_service`;

      if (info.xaddrs.length > 0) {
        try {
          const parsed = new URL(info.xaddrs[0]);
          port = parseInt(parsed.port, 10) || 80;
          onvifUrl = info.xaddrs[0];
        } catch (e) {}
      } else if (ip.endsWith('.211') || ip.endsWith('.212') || ip.endsWith('.235')) {
        port = 2020;
        onvifUrl = `http://${ip}:2020/onvif/device_service`;
      }

      // モデル名 & カメラ設定名（friendlyName）の推定
      let model = 'ONVIF Camera';
      let customOdmName = '';
      let genericName = '';
      let isProfileT = false;
      let authStatus = 'unauthenticated';

      // WS-Discovery Scopes からの抽出 (未認証でも Profile T やモデル名、odm:name は取れる)
      info.scopes.forEach(s => {
        const decoded = decodeURIComponent(s);
        if (decoded.includes('Profile/T')) isProfileT = true;
        if (decoded.includes('hardware/')) {
          model = decoded.split('hardware/')[1].split('/')[0];
        }
        if (decoded.includes('odm:name:')) {
          customOdmName = decoded.split('odm:name:')[1].trim();
        } else if (decoded.includes('name/')) {
          const n = decoded.split('name/')[1].split('/')[0].trim();
          if (n && n !== 'IPC' && n !== 'IPC-BO' && n !== 'Camera') {
            genericName = n;
          } else if (!genericName) {
            genericName = n;
          }
        }
      });

      // 登録済みデバイスがあればその上書き設定を優先
      const reg = registeredList.find(r => r.ip === ip);
      const user = (reg && reg.username) ? reg.username : defaultUser;
      const pass = (reg && reg.password) ? reg.password : defaultPass;

      // 認証情報があれば ONVIF SOAP で追加検証 (Scopes & DeviceInfo & Hostname)
      if (pass) {
        try {
          // GetScopes
          const soapScopes = await this.sendSoap(onvifUrl, 'http://www.onvif.org/ver10/device/wsdl/GetScopes', '<tds:GetScopes/>', user, pass);
          authStatus = 'ok';
          const scopeMatches = soapScopes.match(/<[^:]*:?ScopeItem[^>]*>([^<]+)<\/[^:]*:?ScopeItem>/gi);
          if (scopeMatches) {
            scopeMatches.forEach(item => {
              const val = item.replace(/<[^>]+>/g, '').trim();
              if (val.includes('Profile/T')) isProfileT = true;
              if (val.includes('odm:name:')) {
                customOdmName = val.split('odm:name:')[1].trim();
              } else if (val.includes('hardware/')) {
                model = val.split('hardware/')[1].split('/')[0].trim();
              } else if (val.includes('name/') && !customOdmName) {
                const n = val.split('name/')[1].split('/')[0].trim();
                if (n && n !== 'IPC' && n !== 'IPC-BO') genericName = n;
              }
            });
          }

          // GetDeviceInformation
          try {
            const soapDevInfo = await this.sendSoap(onvifUrl, 'http://www.onvif.org/ver10/device/wsdl/GetDeviceInformation', '<tds:GetDeviceInformation/>', user, pass);
            const modelM = soapDevInfo.match(/<[^:]*:?Model[^>]*>([^<]+)<\/[^:]*:?Model>/i);
            if (modelM && modelM[1].trim()) model = modelM[1].trim();
          } catch (e) {}

          // GetHostname
          try {
            const soapHost = await this.sendSoap(onvifUrl, 'http://www.onvif.org/ver10/device/wsdl/GetHostname', '<tds:GetHostname/>', user, pass);
            const hostM = soapHost.match(/<[^:]*:?Name[^>]*>([^<]+)<\/[^:]*:?Name>/i);
            if (hostM && hostM[1].trim() && hostM[1].trim() !== 'reolink' && hostM[1].trim() !== 'localhost') {
              if (!customOdmName) genericName = hostM[1].trim();
            }
          } catch (e) {}
        } catch (e) {
          if (e.message && e.message.includes('401')) {
            authStatus = 'unauthorized';
          } else {
            authStatus = 'error';
          }
        }
      }

      // ユーザー設定の名前 > 検出名 > 機種名 > デフォルト名
      const friendlyName = customOdmName || genericName || '';
      const displayName = friendlyName || (model !== 'ONVIF Camera' ? model : `Camera-${ip}`);

      return {
        id: `onvif_${ip.replace(/\./g, '_')}`,
        ip,
        port,
        onvifUrl,
        model,
        name: displayName,
        friendlyName,
        status: authStatus,
        isProfileT, // スピーカー対応判定
        hasProfileT: isProfileT,
        supportsAudio: isProfileT,
        audioBackchannelSupported: isProfileT,
        isRegistered: registeredList.some(r => r.ip === ip && r.enabled !== false)
      };
    });

    const parsedResults = await Promise.allSettled(parsePromises);
    const results = parsedResults
      .filter(p => p.status === 'fulfilled')
      .map(p => p.value);

    // IP順にソート
    results.sort((a, b) => {
      const numA = a.ip.split('.').reduce((acc, oct) => (acc << 8) + parseInt(oct, 10), 0);
      const numB = b.ip.split('.').reduce((acc, oct) => (acc << 8) + parseInt(oct, 10), 0);
      return numA - numB;
    });

    this.cachedScanResults = results;
    this.isScanning = false;
    return results;
  }

  /**
   * 音声ファイルの音量を ffmpeg で調整したキャッシュファイルを生成または取得
   * @param {string} sourcePathOrUrl 元のファイルパスまたはURL
   * @param {number} volumeLevel 0.0〜1.0 (例: 0.5)
   * @returns {Promise<string>} 調整後のHTTP URL
   */
  async _adjustAudioVolume(sourcePathOrUrl, volumeLevel) {
    const VOICE_DIR = path.resolve(__dirname, '../public/voice');
    let filename = '';

    if (sourcePathOrUrl.startsWith('http://') || sourcePathOrUrl.startsWith('https://')) {
      try {
        const u = new URL(sourcePathOrUrl);
        filename = path.basename(u.pathname);
      } catch (e) {
        filename = path.basename(sourcePathOrUrl);
      }
    } else {
      filename = path.basename(sourcePathOrUrl);
    }

    const inputPath = path.join(VOICE_DIR, filename);
    if (!fs.existsSync(inputPath)) {
      return sourcePathOrUrl.startsWith('http') ? sourcePathOrUrl : `http://127.0.0.1:8080/voice/${filename}`;
    }

    const parsed = path.parse(filename);
    const volPercent = Math.round(volumeLevel * 100);
    const outputFilename = `${parsed.name}_vol${volPercent}${parsed.ext}`;
    const outputPath = path.join(VOICE_DIR, outputFilename);

    if (fs.existsSync(outputPath) && fs.statSync(outputPath).size > 0) {
      return `http://127.0.0.1:8080/voice/${outputFilename}`;
    }

    await new Promise((resolve) => {
      execFile('ffmpeg', [
        '-y',
        '-i', inputPath,
        '-filter:a', `volume=${volumeLevel.toFixed(2)}`,
        outputPath
      ], { timeout: 8000 }, (err) => {
        if (err) {
          console.warn('[ONVIF Volume Adjust Error]', err.message);
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });

    if (fs.existsSync(outputPath) && fs.statSync(outputPath).size > 0) {
      return `http://127.0.0.1:8080/voice/${outputFilename}`;
    }
    return `http://127.0.0.1:8080/voice/${filename}`;
  }

  /**
   * go2rtc 経由でカメラのスピーカーに音声を再生
   * @param {Object} camera 登録カメラ情報 ({ ip, port, username, password, ... })
   * @param {string} audioUrl サーバー上の音声URL またはローカルファイルパス
   * @param {number} duration 秒数
   * @param {number|null} volumeLevel 音量レベル (0.0〜1.0 またはパーセント数値)
   */
  async playAudio(camera, audioUrl, duration = 8, volumeLevel = null) {
    const onvifConfig = settingsManager.get().onvif || {};
    const username = camera.username || onvifConfig.defaultUsername || 'admin';
    const password = camera.password || onvifConfig.defaultPassword || '';
    const ip = camera.rawIp || camera.ip.replace(/^onvif:/, '');
    const rtspPort = camera.rtspPort || 554;
    const onvifPort = camera.port || 8000;
    const streamName = `onvif_${ip.replace(/\./g, '_')}`;

    // 1. go2rtc にストリームを登録 (RTSP + ONVIF の2ソースを PUT でまとめて定義)
    const rtspUrl = `rtsp://${encodeURIComponent(username)}:${encodeURIComponent(password)}@${ip}:${rtspPort}/h264Preview_01_main`;
    const onvifSrcUrl = `onvif://${encodeURIComponent(username)}:${encodeURIComponent(password)}@${ip}:${onvifPort}`;
    await this._ensureGo2rtcStream(streamName, rtspUrl, onvifSrcUrl);

    // 2. 音声URLの正規化および音量調整 (volumeLevel が指定されている場合は ffmpeg でゲイン調整)
    let resolvedAudioUrl = audioUrl;
    let normVol = volumeLevel;
    if (typeof normVol === 'string') normVol = parseFloat(normVol);
    if (typeof normVol === 'number' && !isNaN(normVol)) {
      if (normVol > 1.0) normVol = normVol / 100; // 0〜100 のパーセント指定を 0.0〜1.0 に正規化
      normVol = Math.max(0.01, Math.min(2.0, normVol));
      if (normVol !== 1.0) {
        resolvedAudioUrl = await this._adjustAudioVolume(audioUrl, normVol);
      }
    }

    if (!resolvedAudioUrl.startsWith('http://') && !resolvedAudioUrl.startsWith('https://')) {
      const filename = path.basename(resolvedAudioUrl);
      resolvedAudioUrl = `http://127.0.0.1:8080/voice/${filename}`;
    }

    // 3. 音声をバックチャンネルにプッシュ (PCMU コーデックで送信)
    const srcParam = `ffmpeg:${resolvedAudioUrl}#audio=pcmu#input=file`;
    const params = new URLSearchParams({
      dst: streamName,
      src: srcParam
    });

    // 再生開始
    const pushUrl = `${this.go2rtcApiUrl}/api/streams?${params.toString()}`;
    console.log(`[ONVIF Play] Starting audio playback on ${camera.name || ip} (${ip}) vol=${normVol !== null && normVol !== undefined ? Math.round(normVol*100)+'%' : 'default'} URL: ${resolvedAudioUrl}`);
    
    const startRes = await this._httpPost(pushUrl);
    if (startRes.statusCode !== 200) {
      throw new Error(`go2rtc 再生リクエスト失敗 (HTTP ${startRes.statusCode}): ${startRes.body}`);
    }

    // 音声の長さ（duration + 余裕）待機したのちセッション切断
    const playMs = Math.max(3000, (duration + 1.5) * 1000);
    setTimeout(async () => {
      try {
        const stopParams = new URLSearchParams({ dst: streamName, src: '' });
        await this._httpPost(`${this.go2rtcApiUrl}/api/streams?${stopParams.toString()}`);
        console.log(`[ONVIF Play] Playback completed on ${camera.name || ip} (${ip})`);
      } catch (e) {
        console.warn(`[ONVIF Play Cleanup Error] ${e.message}`);
      }
    }, playMs);

    return { success: true, message: 'Playback started' };
  }

  async _ensureGo2rtcStream(streamName, rtspUrl, onvifUrl) {
    try {
      // go2rtc に RTSP と ONVIF の2つのプロデューサーをまとめて登録/更新 (PUT /api/streams?name=...&src=...&src=...)
      const putUrl = `${this.go2rtcApiUrl}/api/streams?name=${encodeURIComponent(streamName)}&src=${encodeURIComponent(rtspUrl)}&src=${encodeURIComponent(onvifUrl)}`;
      await this._httpPut(putUrl);
    } catch (e) {
      console.warn('[go2rtc Stream Register Warning]', e.message);
    }
  }

  _httpGet(urlStr) {
    return new Promise((resolve, reject) => {
      const url = new URL(urlStr);
      http.get(url, (res) => {
        let body = '';
        res.on('data', c => body += c);
        res.on('end', () => resolve({ statusCode: res.statusCode, body }));
      }).on('error', reject);
    });
  }

  _httpPost(urlStr) {
    return new Promise((resolve, reject) => {
      const url = new URL(urlStr);
      const req = http.request(url, { method: 'POST', timeout: 5000 }, (res) => {
        let body = '';
        res.on('data', c => body += c);
        res.on('end', () => resolve({ statusCode: res.statusCode, body }));
      });
      req.on('error', reject);
      req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
      req.end();
    });
  }

  _httpPut(urlStr) {
    return new Promise((resolve, reject) => {
      const url = new URL(urlStr);
      const req = http.request(url, { method: 'PUT', timeout: 5000 }, (res) => {
        let body = '';
        res.on('data', c => body += c);
        res.on('end', () => resolve({ statusCode: res.statusCode, body }));
      });
      req.on('error', reject);
      req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
      req.end();
    });
  }
}

module.exports = new OnvifManager();
