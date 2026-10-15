require('dotenv').config({ path: require('path').resolve(__dirname, '../.my.env') });
const express = require('express');
const path = require('path');
const os = require('os');
const ttsManager = require('./tts');
const castManager = require('./cast');
const deviceManager = require('./devices');
const schedulerManager = require('./scheduler');
const alexaManager = require('./alexa');

const app = express();
const PORT = process.env.PORT || process.env.SERVER_PORT || 8080;
const TUNNEL_DOMAIN = process.env.CLOUDFLARE_TUNNEL_DOMAIN || '';

// サーバーIPの解決 (Google HomeがアクセスするURL用)
function resolveServerIp() {
  if (process.env.WIRELESS_IP) return process.env.WIRELESS_IP;
  if (process.env.SERVER_IP) return process.env.SERVER_IP;

  const interfaces = os.networkInterfaces();
  const ifaceName = process.env.WIRELESS_MODULE_NAME || 'ens192';

  if (interfaces[ifaceName]) {
    for (const iface of interfaces[ifaceName]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address;
      }
    }
  }

  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address;
      }
    }
  }
  return '127.0.0.1';
}

const SERVER_IP = resolveServerIp();
console.log(`[Config] サーバーホストIP: ${SERVER_IP}, ポート: ${PORT}`);
console.log(`[Config] デフォルトデバイスIP: ${deviceManager.getDefaultDeviceIp()}`);
if (TUNNEL_DOMAIN) {
  console.log(`[Config] Cloudflare Tunnel ドメイン: ${TUNNEL_DOMAIN}`);
}

// CORSミドルウェア
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization, X-API-KEY');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }
  next();
});

// JSON & URLエンコードパーサー
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Cloudflare Tunnel 経由のリクエスト判定
function isTunnelRequest(req) {
  const host = req.headers['host'] || '';
  const hasCfHeaders = !!req.headers['cf-ray'] || !!req.headers['cf-connecting-ip'] || !!req.headers['cf-ipcountry'];
  const isTunnelHost = !!TUNNEL_DOMAIN && host.toLowerCase().includes(TUNNEL_DOMAIN.toLowerCase());
  return hasCfHeaders || isTunnelHost;
}

// セキュリティフィルター: Cloudflare Tunnel からのアクセス時は Web GUI へのアクセスを遮断
app.use((req, res, next) => {
  if (isTunnelRequest(req)) {
    // 許可するエンドポイント: Webhook (/api/say, /google-home-voicetext)
    const allowedPaths = ['/api/say', '/google-home-voicetext'];
    const isAllowed = allowedPaths.some(p => req.path.startsWith(p));

    if (!isAllowed) {
      console.warn(`[Security Block] Cloudflare Tunnel 経由での不正なアクセスを遮断: ${req.method} ${req.path} (Host: ${req.headers['host']})`);
      return res.status(403).json({
        error: 'Forbidden',
        message: 'Web GUI および管理 API はローカルネットワーク内からのみアクセス可能です。'
      });
    }
  }
  next();
});

// 静的ファイルの提供
const PUBLIC_DIR = path.resolve(__dirname, '../public');
app.use(express.static(PUBLIC_DIR));

// ルートパスで index.html を確実に配信
app.get('/', (req, res) => {
  res.sendFile(path.join(PUBLIC_DIR, 'index.html'));
});

// 音声ファイルホスティング (1GB LRU キャッシュ)
const VOICE_DIR = path.resolve(__dirname, '../public/voice');
app.use('/voice', express.static(VOICE_DIR));
app.use('/googlehome', express.static(VOICE_DIR)); // 過去互換URL

/**
 * 複数デバイスへの同時発信ロジック (Google Home + Alexa)
 * @param {string} text 喋らせる文言
 * @param {Array<string>} targetList 送信先IPまたはデバイス名リスト
 * @param {Object} options voice, rate, pitch, volume, volumeLevel
 */
async function speakToMultipleDevices(text, targetList = [], options = {}) {
  // リストが空の場合はデフォルト
  let targets = Array.isArray(targetList) ? targetList.filter(Boolean) : [targetList];
  if (!targets.length) {
    targets = [deviceManager.getDefaultDeviceIp()];
  }

  // 重複排除とデバイス解決
  const resolvedTargets = [];
  for (const t of targets) {
    const dev = deviceManager.findDevice(t);
    if (dev) {
      resolvedTargets.push(dev);
    } else {
      resolvedTargets.push({ id: t, name: t, ip: t, type: 'google' });
    }
  }

  // Google Home 向けと Alexa 向けを分類
  const googleDevices = resolvedTargets.filter(d => d.type !== 'alexa' && !d.ip.startsWith('alexa:'));
  const alexaDevices = resolvedTargets.filter(d => d.type === 'alexa' || d.ip.startsWith('alexa:'));

  const dispatchPromises = [];
  let audioUrl = null;

  // Google Home デバイスがある場合、Edge TTS 音声を 1 度だけ生成
  if (googleDevices.length > 0) {
    const speech = await ttsManager.generateSpeech(text, {
      voice: options.voice,
      rate: options.rate,
      pitch: options.pitch,
      volume: options.volume
    });
    audioUrl = `http://${SERVER_IP}:${PORT}${speech.urlPath}`;

    // 各 Google Home デバイスへ並行キャスト
    for (const dev of googleDevices) {
      console.log(`[Speak] Google Home 送信先: ${dev.name} (${dev.ip}), 音声URL: ${audioUrl}`);
      dispatchPromises.push(
        castManager.playMedia(dev.ip, audioUrl, { volumeLevel: options.volumeLevel })
          .then(res => ({ device: dev.name, ip: dev.ip, type: 'google', status: 'success', result: res }))
          .catch(err => ({ device: dev.name, ip: dev.ip, type: 'google', status: 'error', error: err.message }))
      );
    }
  }

  // Alexa デバイスがある場合、Alexa スクリプトを並行実行
  if (alexaDevices.length > 0) {
    for (const dev of alexaDevices) {
      const alexaTarget = dev.ip.startsWith('alexa:') ? dev.ip.slice(6) : (dev.name || 'ALL');
      console.log(`[Speak] Alexa 送信先: ${alexaTarget}`);
      dispatchPromises.push(
        alexaManager.speak(text, alexaTarget)
          .then(res => ({ device: dev.name, ip: dev.ip, type: 'alexa', status: 'success', result: res }))
          .catch(err => ({ device: dev.name, ip: dev.ip, type: 'alexa', status: 'error', error: err.message }))
      );
    }
  }

  // 全デバイスの完了を待機
  const results = await Promise.allSettled(dispatchPromises);
  const detailedResults = results.map(r => r.value || { status: 'error', error: r.reason?.message });

  const hasSuccess = detailedResults.some(r => r.status === 'success');

  return {
    success: hasSuccess,
    text,
    audioUrl,
    results: detailedResults
  };
}

// スケジューラーにマルチデバイス実行エンジンを紐付け
schedulerManager.setExecutor(async (text, options) => {
  const targets = options.deviceIps || (options.deviceIp ? [options.deviceIp] : []);
  return await speakToMultipleDevices(text, targets, options);
});

// Webhook認証ミドルウェア (外部Cloudflare Tunnel等からのアクセス保護用)
function requireWebhookAuth(req, res, next) {
  const token = process.env.WEBHOOK_TOKEN;
  if (!token) return next();

  // ローカルホストまたはプライベートLANからのWeb GUIアクセスはスキップ
  const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress || '';
  const isLocal = clientIp.includes('127.0.0.1') || clientIp.includes('::1') || clientIp.includes('192.168.');
  const referer = req.headers['referer'] || '';
  if (isLocal && (referer.includes(`:${PORT}`) || req.headers['sec-fetch-site'] === 'same-origin')) {
    return next();
  }

  // トークンチェック (Header: Authorization, X-API-KEY, または Body/Query: token)
  const authHeader = req.headers['authorization'] || '';
  const bearerToken = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : '';
  const customKey = req.headers['x-api-key'] || '';
  const paramToken = req.query.token || (req.body && req.body.token);

  if (bearerToken === token || customKey === token || paramToken === token) {
    return next();
  }

  return res.status(401).json({
    error: 'Unauthorized',
    message: '有効な WEBHOOK_TOKEN が必要です。ヘッダー Authorization: Bearer <TOKEN> または X-API-KEY: <TOKEN> を付与してください。'
  });
}

// ================= API エンドポイント =================

// 1. 発声 API (最新・複数デバイス対応)
app.post('/api/say', requireWebhookAuth, async (req, res) => {
  const text = req.body.text || req.query.text;
  if (!text) {
    return res.status(400).json({ error: 'パラメータ "text" は必須です' });
  }

  // 複数デバイスの取得・正規化
  let targets = [];
  if (Array.isArray(req.body.devices)) {
    targets = req.body.devices;
  } else if (typeof req.body.devices === 'string') {
    targets = req.body.devices.split(',').map(s => s.trim());
  } else if (typeof req.body.device === 'string') {
    targets = req.body.device.split(',').map(s => s.trim());
  } else if (Array.isArray(req.body.deviceIp)) {
    targets = req.body.deviceIp;
  } else if (req.body.deviceIp) {
    targets = [req.body.deviceIp];
  } else if (req.query.device) {
    targets = req.query.device.split(',').map(s => s.trim());
  } else if (req.query.deviceIp) {
    targets = [req.query.deviceIp];
  }

  try {
    const result = await speakToMultipleDevices(text, targets, {
      voice: req.body.voice || req.query.voice,
      rate: req.body.rate || req.query.rate,
      pitch: req.body.pitch || req.query.pitch,
      volume: req.body.volume || req.query.volume,
      volumeLevel: req.body.volumeLevel !== undefined ? parseFloat(req.body.volumeLevel) : undefined
    });

    res.json(result);
  } catch (err) {
    console.error('[API Say Error]:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// 2. 以前の google-home-voicetext との後方互換エンドポイント
app.post('/google-home-voicetext', requireWebhookAuth, async (req, res) => {
  const text = req.body.text;
  if (!text) {
    return res.status(400).send('Please POST "text=Hello Google Home"');
  }

  try {
    const targets = req.body.deviceIp ? [req.body.deviceIp] : [];
    await speakToMultipleDevices(text, targets, { voice: req.body.voice });
    res.send(`Google Home will say: ${text}\n`);
  } catch (err) {
    console.error('[Legacy API Error]:', err.message);
    res.status(500).send(`Error: ${err.message}\n`);
  }
});

// 3. ブラウザでの事前試聴プレビュー用
app.get('/api/preview', async (req, res) => {
  const text = req.query.text;
  if (!text) return res.status(400).json({ error: 'text is required' });

  try {
    const speech = await ttsManager.generateSpeech(text, {
      voice: req.query.voice,
      rate: req.query.rate,
      pitch: req.query.pitch,
      volume: req.query.volume
    });
    res.sendFile(speech.filepath);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 4. 利用可能な Google Home / Alexa デバイス一覧
app.get('/api/devices', async (req, res) => {
  const devices = await deviceManager.getDevices();
  res.json({
    devices,
    defaultIp: deviceManager.getDefaultDeviceIp()
  });
});

// 5. 利用可能なボイス一覧
app.get('/api/voices', (req, res) => {
  res.json({
    voices: ttsManager.getVoices(),
    defaultVoice: ttsManager.defaultVoice
  });
});

// 6. スケジュール関連 API
app.get('/api/schedules', (req, res) => {
  res.json({
    schedules: schedulerManager.getSchedules(),
    history: schedulerManager.getHistory()
  });
});

app.post('/api/schedules', (req, res) => {
  try {
    const newSched = schedulerManager.addSchedule(req.body);
    res.status(201).json(newSched);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

app.put('/api/schedules/:id', (req, res) => {
  try {
    const updated = schedulerManager.updateSchedule(req.params.id, req.body);
    res.json(updated);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

app.delete('/api/schedules/:id', (req, res) => {
  try {
    const removed = schedulerManager.deleteSchedule(req.params.id);
    res.json(removed);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

app.post('/api/schedules/:id/toggle', (req, res) => {
  try {
    const updated = schedulerManager.toggleSchedule(req.params.id);
    res.json(updated);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

app.post('/api/schedules/:id/run', async (req, res) => {
  try {
    const result = await schedulerManager.runScheduleNow(req.params.id);
    res.json({ success: true, result });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 7. システム情報 & キャッシュ状況 & トンネルドメイン
app.get('/api/status', (req, res) => {
  res.json({
    serverIp: SERVER_IP,
    port: PORT,
    defaultDeviceIp: deviceManager.getDefaultDeviceIp(),
    tunnelDomain: TUNNEL_DOMAIN || null,
    cacheStats: ttsManager.getCacheStats(),
    alexaEnabled: alexaManager.isEnabled(),
    nodeVersion: process.version,
    uptime: Math.floor(process.uptime()),
    hasWebhookToken: !!process.env.WEBHOOK_TOKEN
  });
});

// 起動
app.listen(PORT, '0.0.0.0', () => {
  console.log('====================================================');
  console.log(` Google Home & Alexa TTS Platform 起動完了`);
  console.log(` Web GUI:         http://localhost:${PORT}`);
  console.log(` LAN Web GUI:     http://${SERVER_IP}:${PORT}`);
  console.log(` Webhook URL:     http://${SERVER_IP}:${PORT}/api/say`);
  if (TUNNEL_DOMAIN) {
    console.log(` Tunnel Webhook:  https://${TUNNEL_DOMAIN}/api/say`);
  }
  console.log('====================================================');
});
