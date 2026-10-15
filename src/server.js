require('dotenv').config({ path: require('path').resolve(__dirname, '../.my.env') });
const express = require('express');
const path = require('path');
const os = require('os');
const ttsManager = require('./tts');
const castManager = require('./cast');
const deviceManager = require('./devices');
const schedulerManager = require('./scheduler');
const alexaManager = require('./alexa');
const homepodManager = require('./homepod');
const settingsManager = require('./settings');
const calendarManager = require('./calendar');
const dndManager = require('./dnd');
const historyManager = require('./history');

const app = express();
const PORT = process.env.PORT || process.env.SERVER_PORT || 8080;
const TUNNEL_DOMAIN = process.env.CLOUDFLARE_TUNNEL_DOMAIN || '';

// サーバーIPの解決 (Google HomeがアクセスするURL用)
function resolveServerIp() {
  if (process.env.WIRELESS_IP) return process.env.WIRELESS_IP;
  if (process.env.SERVER_IP) return process.env.SERVER_IP;

  const interfaces = os.networkInterfaces();
  const candidates = [];

  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        // 192.168.x.x または 10.x.x.x などのローカル LAN プライベート IP を最優先
        if (iface.address.startsWith('192.168.') || iface.address.startsWith('10.')) {
          return iface.address;
        }
        candidates.push(iface.address);
      }
    }
  }

  if (candidates.length > 0) return candidates[0];
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

// クライアントIPアドレスの抽出 (Cloudflare Tunnel, リバースプロキシ, 直結対応)
function extractClientIp(req) {
  const cfIp = req.headers['cf-connecting-ip'];
  if (cfIp) return String(cfIp).trim();

  const xff = req.headers['x-forwarded-for'];
  if (xff) {
    const first = String(xff).split(',')[0].trim();
    if (first) return first;
  }

  const raw = req.socket?.remoteAddress || req.connection?.remoteAddress || '';
  return raw.replace(/^::ffff:/, '');
}

// User-Agent ヘッダーからの送信元クライアント自動判定
function detectUserAgentClient(userAgent = '') {
  const ua = String(userAgent).toLowerCase();
  if (!ua) return null;
  if (ua.includes('ifttt') || ua.includes('applets/')) return 'IFTTT';
  if (ua.includes('slackbot') || ua.includes('slack')) return 'Slack';
  if (ua.includes('discordbot') || ua.includes('discord')) return 'Discord';
  if (ua.includes('homeassistant') || ua.includes('home-assistant') || ua.includes('aiohttp')) return 'Home Assistant';
  if (ua.includes('line-bot') || ua.includes('line/')) return 'LINE Bot';
  if (ua.includes('curl/')) return 'curl';
  if (ua.includes('python-requests') || ua.includes('python/')) return 'Python';
  if (ua.includes('postmanruntime') || ua.includes('postman')) return 'Postman';
  if (ua.includes('axios') || ua.includes('node-fetch') || ua.includes('undici')) return 'Node.js';
  if (ua.includes('go-http-client')) return 'Go Client';
  return null;
}

// セキュリティフィルター: Cloudflare Tunnel からのアクセス時は Web GUI へのアクセスを遮断
app.use((req, res, next) => {
  if (isTunnelRequest(req)) {
    // 許可するエンドポイント: Webhook (/api/say のみ)
    const allowedPaths = ['/api/say'];
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

// 重複通知防止 (Deduplication) のキャッシュ (key -> timestamp)
const recentDeduplicationCache = new Map();

function isDuplicateRequest(clientKey, text, cooldownSeconds = 30) {
  if (!cooldownSeconds || cooldownSeconds <= 0) return false;
  const now = Date.now();
  const cacheKey = `${clientKey}:::${String(text).trim()}`;
  const lastTime = recentDeduplicationCache.get(cacheKey);

  if (lastTime && (now - lastTime) < (cooldownSeconds * 1000)) {
    return true;
  }
  recentDeduplicationCache.set(cacheKey, now);

  // キャッシュ肥大化防止 (1000件超えたら古いものを削除)
  if (recentDeduplicationCache.size > 1000) {
    const expireThreshold = now - 3600000;
    for (const [k, v] of recentDeduplicationCache.entries()) {
      if (v < expireThreshold) recentDeduplicationCache.delete(k);
    }
  }
  return false;
}

// 時間帯別自動音量計算 (Auto Volume)
function getAutoVolumeLevel(now = new Date()) {
  const currentSettings = settingsManager.get();
  const autoVol = currentSettings.autoVolume;
  if (!autoVol || !autoVol.enabled || !Array.isArray(autoVol.rules)) {
    return null;
  }

  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const currentHM = `${hours}:${minutes}`;

  for (const rule of autoVol.rules) {
    if (!rule.startTime || !rule.endTime) continue;
    if (rule.startTime <= rule.endTime) {
      if (currentHM >= rule.startTime && currentHM < rule.endTime) {
        return Math.max(0.01, Math.min(1.0, (parseInt(rule.volume, 10) || 50) / 100));
      }
    } else {
      // 日跨ぎ (例: 23:00〜07:00)
      if (currentHM >= rule.startTime || currentHM < rule.endTime) {
        return Math.max(0.01, Math.min(1.0, (parseInt(rule.volume, 10) || 50) / 100));
      }
    }
  }
  return null;
}

/**
 * 複数デバイスへの同時発信ロジック (Google Home + Alexa + HomePod)
 * @param {string} text 喋らせる文言
 * @param {Array<string>} targetList 送信先IPまたはデバイス名リスト (ALL, GH:ALL, AL:ALL, HP:ALL, 1F, 2F, LDK 短縮マクロ対応)
 * @param {Object} options voice, rate, pitch, volume, volumeLevel, chime
 */
async function speakToMultipleDevices(text, targetList = [], options = {}) {
  // リストが空の場合はデフォルト
  let targets = Array.isArray(targetList) ? targetList.filter(Boolean) : [targetList];
  if (!targets.length) {
    targets = [deviceManager.getDefaultDeviceIp()];
  }

  // 利用可能な全デバイス一覧を取得し、短縮マクロ (ALL, GH:ALL, AL:ALL, HP:ALL) およびカスタム部屋グループ (1F, 2F, LDK等) を解決
  const allAvailableDevices = await deviceManager.getDevices();
  const currentSettings = settingsManager.get();
  const deviceGroups = currentSettings.deviceGroups || {};
  const expandedTargets = [];

  for (const t of targets) {
    const raw = String(t).trim();
    const upper = raw.toUpperCase();

    if (upper === 'ALL' || upper === '*') {
      expandedTargets.push(...allAvailableDevices);
    } else if (upper === 'GH:ALL' || upper === 'GOOGLE:ALL' || upper === 'GH_ALL') {
      const ghDevs = allAvailableDevices.filter(d => d.type === 'google' || (!d.ip.startsWith('alexa:') && !d.ip.startsWith('homepod:') && d.type !== 'alexa' && d.type !== 'homepod'));
      expandedTargets.push(...ghDevs);
    } else if (upper === 'AL:ALL' || upper === 'ALEXA:ALL' || upper === 'AL_ALL') {
      const alDevs = allAvailableDevices.filter(d => d.type === 'alexa' || d.ip.startsWith('alexa:'));
      expandedTargets.push(...alDevs);
    } else if (upper === 'HP:ALL' || upper === 'HOMEPOD:ALL' || upper === 'HP_ALL') {
      const hpDevs = allAvailableDevices.filter(d => d.type === 'homepod' || d.ip.startsWith('homepod:'));
      expandedTargets.push(...hpDevs);
    } else {
      // カスタム部屋グループ（大文字小文字問わずマッチ）
      let matchedGroup = null;
      for (const [groupName, groupMembers] of Object.entries(deviceGroups)) {
        if (groupName.toLowerCase() === raw.toLowerCase() && Array.isArray(groupMembers)) {
          matchedGroup = groupMembers;
          break;
        }
      }

      if (matchedGroup) {
        for (const memberName of matchedGroup) {
          const dev = deviceManager.findDevice(memberName);
          if (dev) {
            expandedTargets.push(dev);
          } else {
            expandedTargets.push({ id: memberName, name: memberName, ip: memberName, type: 'google' });
          }
        }
      } else {
        const dev = deviceManager.findDevice(raw);
        if (dev) {
          expandedTargets.push(dev);
        } else {
          expandedTargets.push({ id: raw, name: raw, ip: raw, type: 'google' });
        }
      }
    }
  }

  // 重複排除 (ip をキーとする)
  const resolvedTargets = [];
  const seenIps = new Set();
  for (const dev of expandedTargets) {
    if (!dev || !dev.ip) continue;
    if (!seenIps.has(dev.ip)) {
      seenIps.add(dev.ip);
      resolvedTargets.push(dev);
    }
  }

  // DND (おやすみ / 会議モード) 判定とフィルタリング
  const activeTargets = [];
  const queuedTargets = [];
  let isWhisperGlobal = false;
  let whisperVolGlobal = 10;
  let dndSuppressedCount = 0;
  let dndQueuedReason = '';

  for (const dev of resolvedTargets) {
    const dndCheck = dndManager.checkDndStatus(dev.ip, options);
    if (!dndCheck.isDnd) {
      activeTargets.push(dev);
    } else {
      // DND 発動中！
      if (dndCheck.action === 'whisper') {
        isWhisperGlobal = true;
        whisperVolGlobal = dndCheck.whisperVolume || 10;
        activeTargets.push(dev);
        dndManager.logEvent({
          text,
          targetDevice: dev.name || dev.ip,
          reason: dndCheck.reason,
          action: 'whisper',
          handledAs: `極小音量 (${whisperVolGlobal}%)`
        });
      } else if (dndCheck.action === 'queue') {
        queuedTargets.push(dev);
        dndQueuedReason = dndCheck.reason || 'DND発動中';
        dndManager.logEvent({
          text,
          targetDevice: dev.name || dev.ip,
          reason: dndCheck.reason,
          action: 'queue',
          handledAs: '保留キューへ追加'
        });
      } else {
        // 'skip'
        dndSuppressedCount++;
        console.log(`[DND] 発話をスキップしました (送信先: ${dev.name || dev.ip}, 理由: ${dndCheck.reason})`);
        dndManager.logEvent({
          text,
          targetDevice: dev.name || dev.ip,
          reason: dndCheck.reason,
          action: 'skip',
          handledAs: '完全スキップ (無音)'
        });
      }
    }
  }

  // 保留対象がある場合、1リクエストにつき1件としてキューに追加 (重複登録を防止)
  if (queuedTargets.length > 0) {
    dndManager.enqueue({
      text,
      targetDevices: queuedTargets.map(d => d.ip),
      targetDeviceNames: queuedTargets.map(d => d.name || d.ip),
      options: {
        ...options,
        wasQueued: true,
        originalSource: options.source,
        originalSourceLabel: options.sourceLabel,
        clientName: options.clientName,
        clientIp: options.clientIp
      },
      reason: dndQueuedReason
    });
  }

  // 送信先が 0 台になった場合は早期リターン
  if (activeTargets.length === 0) {
    const isQueuedOnly = queuedTargets.length > 0;
    const statusMsg = isQueuedOnly 
      ? `DND発動中のため保留キューに追加しました (${queuedTargets.length}台)` 
      : 'おやすみ・会議モード (DND) 発動中のため発話を保留/抑制しました';

    historyManager.addEntry({
      text,
      source: options.source || 'api',
      sourceLabel: options.sourceLabel,
      clientName: options.clientName || '',
      clientIp: options.clientIp || '',
      wasQueued: isQueuedOnly,
      targets: resolvedTargets.map(d => d.name || d.ip),
      voice: options.voice,
      rate: options.rate,
      pitch: options.pitch,
      volume: options.volume,
      volumeLevel: options.volumeLevel,
      status: isQueuedOnly ? 'queued' : 'suppressed',
      statusMessage: statusMsg,
      urgent: !!options.urgent,
      results: []
    });
    return {
      success: true,
      dndSuppressed: true,
      queued: isQueuedOnly,
      message: statusMsg,
      text,
      results: []
    };
  }

  // 音量レベルの決定 (未指定の場合は時間帯別自動音量カーブを適用)
  let effectiveVolumeLevel = options.volumeLevel;
  if (effectiveVolumeLevel === undefined) {
    const autoVol = getAutoVolumeLevel();
    if (autoVol !== null) {
      effectiveVolumeLevel = autoVol;
      console.log(`[AutoVolume] 現在時刻に応じた自動音量カーブを適用: ${Math.round(autoVol * 100)}%`);
    }
  }

  // 極小音量モードの場合は音量レベルを上書き (0.01〜1.0)
  if (isWhisperGlobal) {
    effectiveVolumeLevel = whisperVolGlobal / 100;
  }

  // Google Home 向け、Alexa 向け、HomePod 向けを分類
  const googleDevices = activeTargets.filter(d => d.type === 'google' || (!d.ip.startsWith('alexa:') && !d.ip.startsWith('homepod:') && d.type !== 'alexa' && d.type !== 'homepod'));
  const alexaDevices = activeTargets.filter(d => d.type === 'alexa' || d.ip.startsWith('alexa:'));
  const homepodDevices = activeTargets.filter(d => d.type === 'homepod' || d.ip.startsWith('homepod:'));

  const dispatchPromises = [];
  let audioUrl = null;
  let sharedSpeech = null;

  // Google Home または HomePod がある場合、Edge TTS 音声を 1 度だけ生成 (チャイム音結合オプション対応)
  if (googleDevices.length > 0 || homepodDevices.length > 0) {
    sharedSpeech = await ttsManager.generateSpeech(text, {
      voice: options.voice,
      rate: options.rate,
      pitch: options.pitch,
      volume: options.volume,
      chime: options.chime
    });
    audioUrl = `http://${SERVER_IP}:${PORT}${sharedSpeech.urlPath}`;
  }

  // Google Home デバイスへ並行キャスト
  if (googleDevices.length > 0 && sharedSpeech) {
    for (const dev of googleDevices) {
      console.log(`[Speak] Google Home 送信先: ${dev.name} (${dev.ip}), 音声URL: ${audioUrl}${isWhisperGlobal ? ` [DND極小音量: ${whisperVolGlobal}%]` : ''}`);
      dispatchPromises.push(
        castManager.playMedia(dev.ip, audioUrl, { volumeLevel: effectiveVolumeLevel })
          .then(res => ({ device: dev.name, ip: dev.ip, type: 'google', status: 'success', result: res }))
          .catch(err => ({ device: dev.name, ip: dev.ip, type: 'google', status: 'error', error: err.message }))
      );
    }
  }

  // HomePod デバイスへ並行 AirPlay ストリーミング
  if (homepodDevices.length > 0 && sharedSpeech) {
    for (const dev of homepodDevices) {
      console.log(`[Speak] HomePod 送信先: ${dev.name} (${dev.ip})`);
      dispatchPromises.push(
        homepodManager.playAudio(sharedSpeech.filepath, dev.ip)
          .then(res => ({ device: dev.name, ip: dev.ip, type: 'homepod', status: 'success', result: res }))
          .catch(err => ({ device: dev.name, ip: dev.ip, type: 'homepod', status: 'error', error: err.message }))
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
  const allSuccess = detailedResults.length > 0 && detailedResults.every(r => r.status === 'success');

  let historyStatus = 'error';
  let historyMessage = '全デバイスへの送信に失敗しました';
  if (allSuccess) {
    historyStatus = 'success';
    historyMessage = `${detailedResults.length} 台のスピーカーへ送信成功`;
  } else if (hasSuccess) {
    historyStatus = 'partial';
    const successCnt = detailedResults.filter(r => r.status === 'success').length;
    historyMessage = `一部端末のみ成功 (${successCnt}/${detailedResults.length} 台)`;
  }

  historyManager.addEntry({
    text,
    source: options.source || 'api',
    sourceLabel: options.sourceLabel,
    clientName: options.clientName || '',
    clientIp: options.clientIp || '',
    wasQueued: !!options.wasQueued,
    targets: resolvedTargets.map(d => d.name || d.ip),
    voice: options.voice,
    rate: options.rate,
    pitch: options.pitch,
    volume: options.volume,
    volumeLevel: effectiveVolumeLevel,
    status: historyStatus,
    statusMessage: historyMessage,
    urgent: !!options.urgent,
    results: detailedResults
  });

  return {
    success: hasSuccess,
    text,
    audioUrl,
    duration: sharedSpeech?.duration || Math.max(2.5, (String(text).length / 5.0) + (options.chime && options.chime !== 'none' ? 2.5 : 0.5)),
    results: detailedResults
  };
}

// スケジューラーにマルチデバイス実行エンジンを紐付け
schedulerManager.setExecutor(async (text, options) => {
  const targets = options.deviceIps || (options.deviceIp ? [options.deviceIp] : []);
  return await speakToMultipleDevices(text, targets, options);
});

// カレンダーマネージャーにマルチデバイス実行エンジンを紐付け
calendarManager.setExecutor(async (text, options) => {
  const targets = options.deviceIps || (options.deviceIp ? [options.deviceIp] : []);
  return await speakToMultipleDevices(text, targets, options);
});

// DND マネージャーの保留キュー消化エンジンを紐付け (複数ターゲット同時再生対応)
dndManager.setSpeakerExecutor(async (item) => {
  const targets = item.targetDevices || (item.targetDevice ? [item.targetDevice] : []);
  return await speakToMultipleDevices(item.text, targets, {
    ...(item.options || {}),
    bypassDnd: true,
    wasQueued: true, // 保留からの再生フラグ
    source: item.options?.originalSource || item.options?.source || 'api',
    sourceLabel: item.options?.originalSourceLabel || item.options?.sourceLabel,
    clientName: item.options?.clientName,
    clientIp: item.options?.clientIp
  });
});

// 初期カレンダーイベントの同期開始
calendarManager.syncEvents().catch(err => {
  console.warn('[Calendar] 初回同期エラー:', err.message);
});

// Webhook認証ミドルウェア (外部Cloudflare Tunnel等からのアクセス保護用)
function requireWebhookAuth(req, res, next) {
  const token = settingsManager.getWebhookToken();
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

// 1. 発声 API (最新・複数デバイス対応 & 非同期レスポンス対応)
const handleSay = async (req, res) => {
  const text = req.body?.text || req.query?.text;
  if (!text) {
    return res.status(400).json({ error: 'パラメータ "text" は必須です' });
  }

  // 複数デバイスの取得・正規化
  let targets = [];
  if (Array.isArray(req.body?.devices)) {
    targets = req.body.devices;
  } else if (typeof req.body?.devices === 'string') {
    targets = req.body.devices.split(',').map(s => s.trim());
  } else if (typeof req.body?.device === 'string') {
    targets = req.body.device.split(',').map(s => s.trim());
  } else if (Array.isArray(req.body?.deviceIp)) {
    targets = req.body.deviceIp;
  } else if (req.body?.deviceIp) {
    targets = [req.body.deviceIp];
  } else if (req.query?.device) {
    targets = req.query.device.split(',').map(s => s.trim());
  } else if (req.query?.deviceIp) {
    targets = [req.query.deviceIp];
  }

  try {
    const isUrgent = req.body?.urgent === true || req.body?.urgent === 'true' || req.query?.urgent === 'true' ||
                     req.body?.bypassDnd === true || req.body?.bypassDnd === 'true' || req.query?.bypassDnd === 'true';

    // 送信元クライアント & IP の判定
    const clientIp = extractClientIp(req);
    const userAgent = req.headers['user-agent'] || '';
    const rawFrom = req.body?.from || req.query?.from || 
                    req.body?.client || req.query?.client || 
                    req.body?.sender || req.query?.sender || '';

    // 送信元メタデータの判定 (通信経路)
    let source = req.body?.source || req.query?.source;
    let sourceLabel = req.body?.sourceLabel || req.query?.sourceLabel;
    const isTunnel = isTunnelRequest(req);

    if (!source) {
      if (isTunnel) {
        source = 'tunnel_webhook';
      } else {
        const referer = req.headers['referer'] || '';
        const origin = req.headers['origin'] || '';
        const fetchSite = req.headers['sec-fetch-site'] || '';
        if (referer.includes(`:${PORT}`) || origin.includes(`:${PORT}`) || fetchSite === 'same-origin') {
          source = 'web_ui';
        } else {
          source = 'api';
        }
      }
    }

    // IPエイリアスおよび User-Agent の照合
    const currentSettings = settingsManager.get();
    const ipAliases = currentSettings.ipAliases || {};
    const ipAlias = clientIp ? ipAliases[clientIp] : null;
    const uaDetected = detectUserAgentClient(userAgent);

    let clientName = '';
    if (rawFrom) {
      clientName = String(rawFrom).trim();
    } else if (ipAlias) {
      clientName = ipAlias;
    } else if (uaDetected) {
      clientName = uaDetected;
    } else if (source === 'web_ui') {
      clientName = 'Web UI';
    } else if (clientIp && !clientIp.startsWith('127.') && clientIp !== '::1') {
      clientName = clientIp;
    }

    // 送信元ラベルの構築 (通信経路そのものの名称)
    if (!sourceLabel) {
      if (source === 'tunnel_webhook') {
        sourceLabel = 'Cloudflare Tunnel';
      } else if (source === 'web_ui') {
        sourceLabel = 'Web UI';
      } else if (source === 'schedule') {
        sourceLabel = '定期スケジュール';
      } else if (source === 'calendar') {
        sourceLabel = 'カレンダー連携';
      } else {
        sourceLabel = '外部 API';
      }
    }

    // 1行アクセスログ出力 (トラブルシューティング & 監視用)
    const cleanLogText = String(text).replace(/[\r\n]+/g, ' ').slice(0, 50);
    const targetLogStr = targets.length > 0 ? targets.join(',') : 'default';
    console.log(`[API Request] [From: ${clientName || '未指定'}] [Via: ${sourceLabel}] [IP: ${clientIp || 'local'}] [Targets: ${targetLogStr}] [Text: "${cleanLogText}"]`);

    // 重複通知ブロック判定 (設定で有効化されている場合、クールダウン秒数以内の同一通知をスキップ)
    const dedupeConfig = currentSettings.deduplication || {};
    if (dedupeConfig.enabled && source !== 'web_ui') {
      const clientKey = clientName || clientIp || 'anonymous';
      if (isDuplicateRequest(clientKey, text, dedupeConfig.cooldownSeconds || 30)) {
        console.log(`[Deduplication] 重複通知を自動ブロックしました (${dedupeConfig.cooldownSeconds}秒クールダウン): [${clientKey}] "${cleanLogText}"`);
        return res.status(200).json({
          success: true,
          deduplicated: true,
          message: `直前の同一通知から ${dedupeConfig.cooldownSeconds} 秒以内のためスキップしました`,
          text
        });
      }
    }

    // 非同期応答（即時レスポンス）の判定:
    // 送信元（Slack, LINE, IFTTT 等）の3秒タイムアウトを防ぐため、外部 Webhook / API は原則として即時 200 OK を返却する
    const isExplicitSync = req.body?.wait === true || req.body?.wait === 'true' || req.query?.wait === 'true' ||
                           req.body?.sync === true || req.body?.sync === 'true' || req.query?.sync === 'true';

    const isExplicitAsync = req.body?.async === true || req.body?.async === 'true' || req.query?.async === 'true' || req.query?.async === '1' ||
                            req.body?.wait === false || req.body?.wait === 'false' || req.query?.wait === 'false';

    const isExternalWebhook = (source === 'tunnel_webhook' || source === 'api');
    const shouldRunAsync = isExplicitAsync || (isExternalWebhook && !isExplicitSync);

    const rawVol = req.body?.volumeLevel !== undefined ? req.body.volumeLevel : req.query?.volumeLevel;
    const parsedVol = (rawVol !== undefined && rawVol !== '') ? parseFloat(rawVol) : undefined;

    const speakOptions = {
      voice: req.body?.voice || req.query?.voice,
      rate: req.body?.rate || req.query?.rate,
      pitch: req.body?.pitch || req.query?.pitch,
      volume: req.body?.volume || req.query?.volume,
      volumeLevel: parsedVol,
      chime: req.body?.chime !== undefined ? req.body.chime : req.query?.chime,
      urgent: isUrgent,
      bypassDnd: isUrgent,
      source,
      sourceLabel,
      clientName,
      clientIp
    };

    if (shouldRunAsync) {
      // 送信元のタイムアウトを防ぐため、即座に 200 OK を返却（バックグラウンドで発声処理）
      res.status(200).json({
        success: true,
        status: 'accepted',
        async: true,
        message: '発声リクエストを受付けました（バックグラウンドで処理中）',
        text,
        targets: targets.length > 0 ? targets : [deviceManager.getDefaultDeviceIp()]
      });

      // バックグラウンドで非同期実行（発声履歴ログには完了時に自動追記される）
      speakToMultipleDevices(text, targets, speakOptions).catch(err => {
        console.error('[Async API Say Error]:', err.message);
      });
      return;
    }

    // 同期実行（完了を待機）
    const result = await speakToMultipleDevices(text, targets, speakOptions);
    res.json(result);
  } catch (err) {
    console.error('[API Say Error]:', err.message);
    res.status(500).json({ error: err.message });
  }
};

app.post('/api/say', requireWebhookAuth, handleSay);
app.get('/api/say', requireWebhookAuth, handleSay);

// 発声履歴 API (直近100件)
app.get('/api/history', (req, res) => {
  const limit = req.query.limit ? parseInt(req.query.limit, 10) : 100;
  res.json({
    history: historyManager.getHistory(limit),
    total: historyManager.history.length
  });
});

app.delete('/api/history', (req, res) => {
  historyManager.clearHistory();
  res.json({ success: true, message: '発言履歴をクリアしました' });
});

// 2. システム設定 API
app.get('/api/settings', (req, res) => {
  res.json(settingsManager.get());
});

app.put('/api/settings', (req, res) => {
  try {
    const updated = settingsManager.update(req.body);
    // カレンダー設定更新時に再同期
    if (req.body.calendar) {
      calendarManager.syncEvents().catch(() => {});
    }
    res.json(updated);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// デフォルトスピーカー変更 API
app.post('/api/devices/default', (req, res) => {
  try {
    const { ip, id } = req.body;
    const target = ip || id;
    if (!target) {
      return res.status(400).json({ error: 'デバイス識別子 (ip または id) が必要です' });
    }

    deviceManager.setDefaultDeviceIp(target);
    console.log(`[Config] デフォルトデバイスを変更しました: ${target}`);
    res.json({
      success: true,
      defaultDeviceIp: deviceManager.getDefaultDeviceIp()
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 3. カレンダー連携 API
app.get('/api/calendar/events', (req, res) => {
  res.json({
    today: calendarManager.getTodayEvents(),
    upcoming: calendarManager.getUpcomingEvents(),
    lastFetched: calendarManager.lastFetched
  });
});

app.post('/api/calendar/sync', async (req, res) => {
  try {
    const events = await calendarManager.syncEvents();
    res.json({ success: true, count: events.length, lastFetched: calendarManager.lastFetched });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/calendar/summary', async (req, res) => {
  try {
    const result = await calendarManager.speakDailySummary();
    res.json({ success: true, result });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 4. おやすみ・会議モード (DND) API
app.get('/api/dnd/status', (req, res) => {
  res.json(dndManager.getGlobalStatus());
});

app.post('/api/dnd/quick', (req, res) => {
  const minutes = parseInt(req.body.minutes ?? 30, 10);
  const reason = req.body.reason || '手動サイレント (即時)';
  const result = dndManager.setQuickDnd(minutes, reason);
  res.json(result);
});

app.get('/api/dnd/history', (req, res) => {
  res.json(dndManager.getHistory());
});

app.delete('/api/dnd/history', (req, res) => {
  dndManager.clearHistory();
  res.json({ success: true });
});

// 4. ブラウザでの事前試聴プレビュー用
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
    alexaConfigured: alexaManager.configured,
    homepodCount: homepodManager.devicesCache.length,
    nodeVersion: process.version,
    uptime: Math.floor(process.uptime()),
    hasWebhookToken: !!process.env.WEBHOOK_TOKEN,
    webhookToken: process.env.WEBHOOK_TOKEN || null
  });
});

// 8. HomePod 管理 API
app.get('/api/homepod/status', async (req, res) => {
  const devices = await homepodManager.getDevices();
  res.json({
    count: devices.length,
    devices
  });
});

app.post('/api/homepod/scan', async (req, res) => {
  try {
    const devices = await homepodManager.scanDevices();
    res.json({ success: true, count: devices.length, devices });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 8. Alexa 連携 & 認証管理 API
app.get('/api/alexa/status', (req, res) => {
  res.json(alexaManager.getAuthStatus(SERVER_IP));
});

app.post('/api/alexa/auth/start', async (req, res) => {
  try {
    const authPort = parseInt(process.env.ALEXA_PROXY_PORT || '8081', 10);
    const result = await alexaManager.startProxyAuth(SERVER_IP, authPort);
    res.json(result);
  } catch (err) {
    console.error('[Alexa Auth Start Error]:', err.message);
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/alexa/auth/stop', (req, res) => {
  alexaManager.stopProxyAuth();
  res.json({ success: true });
});

app.post('/api/alexa/logout', (req, res) => {
  alexaManager.logout();
  res.json({ success: true });
});

app.post('/api/alexa/token', (req, res) => {
  try {
    const token = req.body.token;
    const result = alexaManager.setRefreshToken(token);
    res.json(result);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
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
