require('dotenv').config({ path: require('path').resolve(__dirname, '../.my.env') });
const express = require('express');
const path = require('path');
const os = require('os');
const ttsManager = require('./tts');
const castManager = require('./cast');
const deviceManager = require('./devices');
const schedulerManager = require('./scheduler');

const app = express();
const PORT = process.env.PORT || process.env.SERVER_PORT || 8080;

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

// 静的ファイルの提供
const PUBLIC_DIR = path.resolve(__dirname, '../public');
app.use(express.static(PUBLIC_DIR));

// ルートパスで index.html を確実に配信
app.get('/', (req, res) => {
  res.sendFile(path.join(PUBLIC_DIR, 'index.html'));
});

// 音声ファイルホスティング
const VOICE_DIR = path.resolve(__dirname, '../public/voice');
app.use('/voice', express.static(VOICE_DIR));
app.use('/googlehome', express.static(VOICE_DIR)); // 過去互換URL

// 共通の発声ロジック
async function speakText(text, options = {}) {
  // 音声ファイルの生成 (Edge TTS)
  const speech = await ttsManager.generateSpeech(text, {
    voice: options.voice,
    rate: options.rate,
    pitch: options.pitch,
    volume: options.volume
  });

  // Google Homeが取得するURL
  const audioUrl = `http://${SERVER_IP}:${PORT}${speech.urlPath}`;

  // 送信先デバイスの決定
  let targetIp = options.deviceIp;
  if (!targetIp && options.device) {
    const dev = deviceManager.findDevice(options.device);
    if (dev) targetIp = dev.ip;
  }
  if (!targetIp) {
    targetIp = deviceManager.getDefaultDeviceIp();
  }

  console.log(`[Speak] 送信先: ${targetIp}, 音声URL: ${audioUrl}, 文言: "${text}"`);
  
  // Google Home にキャスト
  const result = await castManager.playMedia(targetIp, audioUrl, {
    volumeLevel: options.volumeLevel
  });

  return {
    success: true,
    text,
    deviceIp: targetIp,
    audioUrl,
    result
  };
}

// スケジューラーに実行エンジンを紐付け
schedulerManager.setExecutor(async (text, options) => {
  return await speakText(text, options);
});

// Webhook認証ミドルウェア (外部Cloudflare Tunnel等からのアクセス保護用)
function requireWebhookAuth(req, res, next) {
  const token = process.env.WEBHOOK_TOKEN;
  // トークン未設定の場合は認証なしで通過
  if (!token) return next();

  // ローカルホストまたはプライベートLANからのWeb GUIアクセスは許可
  const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress || '';
  const isLocal = clientIp.includes('127.0.0.1') || clientIp.includes('::1') || clientIp.includes('192.168.');
  // Referer が自サーバーなら Web GUI からの操作と判定
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

// 1. 発声 API (最新)
app.post('/api/say', requireWebhookAuth, async (req, res) => {
  const text = req.body.text || req.query.text;
  if (!text) {
    return res.status(400).json({ error: 'パラメータ "text" は必須です' });
  }

  try {
    const result = await speakText(text, {
      deviceIp: req.body.deviceIp || req.body.ip || req.query.deviceIp,
      device: req.body.device || req.query.device,
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
    const result = await speakText(text, {
      deviceIp: req.body.deviceIp || req.body.ip,
      voice: req.body.voice
    });
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

// 4. 利用可能な Google Home デバイス一覧
app.get('/api/devices', (req, res) => {
  res.json({
    devices: deviceManager.getDevices(),
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

// 7. システム情報
app.get('/api/status', (req, res) => {
  res.json({
    serverIp: SERVER_IP,
    port: PORT,
    defaultDeviceIp: deviceManager.getDefaultDeviceIp(),
    nodeVersion: process.version,
    uptime: Math.floor(process.uptime()),
    hasWebhookToken: !!process.env.WEBHOOK_TOKEN
  });
});

// 起動
app.listen(PORT, '0.0.0.0', () => {
  console.log('====================================================');
  console.log(` Google Home TTS Platform (Edge TTS Edition) 起動完了`);
  console.log(` Web GUI:         http://localhost:${PORT}`);
  console.log(` LAN Web GUI:     http://${SERVER_IP}:${PORT}`);
  console.log(` Webhook URL:     http://${SERVER_IP}:${PORT}/api/say`);
  console.log(` 互換 URL:        http://${SERVER_IP}:${PORT}/google-home-voicetext`);
  console.log('====================================================');
});
