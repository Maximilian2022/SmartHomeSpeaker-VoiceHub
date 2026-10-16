const { exec } = require('child_process');
const alexaManager = require('./alexa');
const homepodManager = require('./homepod');
const settingsManager = require('./settings');
const onvifManager = require('./onvif');

// 事前に検出確認済みのデバイス一覧（空配列にして mDNS / Avahi による完全自動検出とする）
const KNOWN_DEVICES = [];

/**
 * Avahi の \DDD (10進数バイトエスケープ) を UTF-8 デコード
 * 例: \233\131\168\229\177\139 -> "部屋"
 */
function decodeAvahiString(str) {
  if (!str) return '';
  const bytes = [];
  for (let i = 0; i < str.length; i++) {
    if (str[i] === '\\' && i + 3 < str.length && /^\d{3}$/.test(str.slice(i + 1, i + 4))) {
      bytes.push(parseInt(str.slice(i + 1, i + 4), 10));
      i += 3;
    } else {
      bytes.push(str.charCodeAt(i));
    }
  }
  return Buffer.from(bytes).toString('utf8');
}

class DeviceManager {
  constructor() {
    this.devices = new Map();
    // 初期データを登録
    KNOWN_DEVICES.forEach(dev => this.devices.set(dev.ip, { ...dev }));

    // スキャン実行
    this.scanDevices();
    // 10分ごとに再スキャン
    setInterval(() => this.scanDevices(), 10 * 60 * 1000).unref();
  }

  getDefaultDeviceIp() {
    const configured = settingsManager.getDefaultDeviceId();
    if (configured) return configured;
    // 設定がない場合は最初に見つかったデバイス
    const firstDev = Array.from(this.devices.values())[0];
    return firstDev ? firstDev.ip : (process.env.GOOGLE_HOME_IP || '');
  }

  setDefaultDeviceIp(id) {
    return settingsManager.setDefaultDeviceId(id);
  }

  /**
   * デバイスのカテゴリ優先順位を取得:
   * 1: Group GH (Google Home グループ)
   * 2: Group Alexa (Alexa グループ)
   * 3: Group Homepod (HomePod グループ)
   * 4: GH (単体 Google Home)
   * 5: Alexa (単体 Alexa)
   * 6: Homepod (単体 HomePod)
   */
  getDeviceCategoryOrder(dev) {
    const type = (dev.type || 'google').toLowerCase();
    const name = (dev.name || '').toLowerCase();
    const model = (dev.model || '').toLowerCase();
    const ip = (dev.ip || '').toLowerCase();

    const isGroup = !!dev.isGroup ||
      ip.endsWith(':all') ||
      model.includes('group') ||
      model.includes('グループ') ||
      name.includes('全室') ||
      name.includes('グループ');

    if (isGroup) {
      if (type === 'google') return 1; // Group GH
      if (type === 'alexa') return 2;  // Group Alexa
      if (type === 'homepod') return 3;// Group HomePod
      return 1;
    } else {
      if (type === 'google') return 4; // GH
      if (type === 'alexa') return 5;  // Alexa
      if (type === 'homepod') return 6;// HomePod
      if (type === 'onvif') return 7;  // ONVIF Camera
      return 4;
    }
  }

  async getDevices() {
    const defaultIp = this.getDefaultDeviceIp();
    const result = Array.from(this.devices.values()).map(dev => ({
      ...dev,
      isDefault: dev.ip === defaultIp
    }));

    // Alexa が有効なら Alexa デバイスも追加
    if (alexaManager.isEnabled()) {
      try {
        const alexaDevs = await alexaManager.listDevices();
        result.push(...alexaDevs);
      } catch (e) {
        console.warn('Alexa デバイス一覧取得エラー:', e.message);
      }
    }

    // HomePod デバイスの追加
    try {
      const homepodDevs = await homepodManager.getDevices();
      result.push(...homepodDevs);
    } catch (e) {
      console.warn('HomePod デバイス一覧取得エラー:', e.message);
    }

    // ONVIF 登録済みカメラの追加
    const onvifConfig = settingsManager.get().onvif || {};
    if (onvifConfig.enabled !== false && Array.isArray(onvifConfig.registeredDevices)) {
      for (const cam of onvifConfig.registeredDevices) {
        if (cam.enabled !== false) {
          result.push({
            id: cam.id || `onvif_${cam.ip.replace(/\./g, '_')}`,
            name: cam.name || cam.friendlyName || `ONVIF (${cam.ip})`,
            ip: `onvif:${cam.ip}`,
            rawIp: cam.ip,
            port: cam.port || 8000,
            model: cam.model || 'ONVIF Speaker',
            type: 'onvif',
            username: cam.username,
            password: cam.password,
            isDefault: `onvif:${cam.ip}` === defaultIp
          });
        }
      }
    }

    // 順序付け: Group GH -> Group Alexa -> Group Homepod -> GH -> Alexa -> Homepod -> ONVIF
    result.sort((a, b) => {
      const orderA = this.getDeviceCategoryOrder(a);
      const orderB = this.getDeviceCategoryOrder(b);
      if (orderA !== orderB) return orderA - orderB;
      if (a.isDefault && !b.isDefault) return -1;
      if (!a.isDefault && b.isDefault) return 1;
      return (a.name || '').localeCompare(b.name || '', 'ja');
    });

    return result;
  }

  findDevice(query) {
    if (!query) return null;
    const normalized = query.trim();

    // ONVIF カメラ指定の場合
    const onvifConfig = settingsManager.get().onvif || {};
    const regCams = (onvifConfig.registeredDevices || []).filter(c => c.enabled !== false);
    if (normalized.startsWith('onvif:')) {
      const targetIp = normalized.slice(6);
      const found = regCams.find(c => c.ip === targetIp || c.id === targetIp);
      if (found) {
        return {
          id: found.id || `onvif_${found.ip.replace(/\./g, '_')}`,
          name: found.name || `ONVIF (${found.ip})`,
          ip: `onvif:${found.ip}`,
          rawIp: found.ip,
          port: found.port || 8000,
          model: found.model || 'ONVIF Speaker',
          type: 'onvif',
          username: found.username,
          password: found.password
        };
      }
    }

    // HomePod デバイス指定の場合
    if (normalized.startsWith('homepod:') || normalized.toLowerCase().includes('homepod')) {
      const hpTarget = normalized.startsWith('homepod:') ? normalized.slice(8) : normalized;
      const found = homepodManager.devicesCache.find(d =>
        d.mac === hpTarget || d.rawIp === hpTarget || d.rawName === hpTarget || d.ip === `homepod:${hpTarget}`
      );
      if (found) return found;
      return {
        id: `homepod_${hpTarget.replace(/[^a-zA-Z0-9]/g, '_')}`,
        name: `HomePod (${hpTarget})`,
        ip: `homepod:${hpTarget}`,
        model: 'Apple HomePod',
        type: 'homepod'
      };
    }

    // Alexa デバイス指定の場合
    if (normalized.startsWith('alexa:') || normalized.toLowerCase().includes('alexa') || normalized.toLowerCase().includes('echo')) {
      const alexaTarget = normalized.startsWith('alexa:') ? normalized.slice(6) : normalized;
      return {
        id: `alexa_${alexaTarget.replace(/\s+/g, '_')}`,
        name: `Alexa (${alexaTarget})`,
        ip: `alexa:${alexaTarget}`,
        model: 'Amazon Echo',
        type: 'alexa'
      };
    }

    // ONVIF 名前一致 (完全または部分)
    for (const cam of regCams) {
      if ((cam.name && cam.name.toLowerCase() === normalized.toLowerCase()) || cam.ip === normalized) {
        return {
          id: cam.id || `onvif_${cam.ip.replace(/\./g, '_')}`,
          name: cam.name,
          ip: `onvif:${cam.ip}`,
          rawIp: cam.ip,
          port: cam.port || 8000,
          model: cam.model || 'ONVIF Speaker',
          type: 'onvif',
          username: cam.username,
          password: cam.password
        };
      }
    }

    // IP完全一致 または host:port 一致
    if (this.devices.has(normalized)) {
      return this.devices.get(normalized);
    }

    const normLower = normalized.toLowerCase();

    // 1. 完全一致 (グループを優先)
    for (const dev of this.devices.values()) {
      if (dev.isGroup && (dev.name.toLowerCase() === normLower || dev.ip === normalized || dev.id === normalized)) {
        return dev;
      }
    }
    for (const dev of this.devices.values()) {
      if (!dev.isGroup && (dev.name.toLowerCase() === normLower || dev.ip === normalized || dev.id === normalized)) {
        return dev;
      }
    }

    // 2. 部分一致 (グループ優先)
    for (const dev of this.devices.values()) {
      if (dev.isGroup && (dev.name.toLowerCase().includes(normLower) || normLower.includes(dev.name.toLowerCase()))) {
        return dev;
      }
    }
    for (const dev of this.devices.values()) {
      if (!dev.isGroup && dev.name.toLowerCase().includes(normLower)) {
        return dev;
      }
    }

    // IPアドレス形式なら一時デバイスとして返す
    if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$/.test(normalized)) {
      return { id: normalized, name: normalized, ip: normalized, model: 'Custom IP', type: 'google' };
    }

    return null;
  }

  /**
   * avahi-browse を利用して LAN 内の新規 Google Cast デバイスおよび Cast グループを動的追加
   */
  scanDevices() {
    exec('avahi-browse -r -t -p _googlecast._tcp', (err, stdout) => {
      if (err || !stdout) return;

      const lines = stdout.split('\n');
      for (const line of lines) {
        const parts = line.split(';');
        if (parts[0] === '=' && parts[2] === 'IPv4' && parts[7]) {
          const ip = parts[7];
          const port = parseInt(parts[8], 10) || 8009;
          const txtRaw = parts[9] || '';
          let name = `Cast-${ip}`;
          let model = 'Google Cast';

          // Google Cast の親しみやすい名前 (fn=...) を抽出してデコード
          const fnMatch = txtRaw.match(/"fn=([^"]+)"/);
          if (fnMatch) {
            name = decodeAvahiString(fnMatch[1]);
          } else if (parts[3]) {
            name = decodeAvahiString(parts[3]);
          }

          const mdMatch = txtRaw.match(/"md=([^"]+)"/);
          if (mdMatch) {
            model = decodeAvahiString(mdMatch[1]);
          }

          const isGroup = model === 'Google Cast Group' || (parts[3] && parts[3].startsWith('Google-Cast-Group'));
          const key = isGroup ? `group_${ip}_${port}` : ip;
          const formattedIp = isGroup ? `${ip}:${port}` : ip;

          if (this.devices.has(key)) {
            // 既に存在していても Friendly Name が取れていれば更新
            const existing = this.devices.get(key);
            if (fnMatch) existing.name = name;
            existing.port = port;
            existing.isGroup = isGroup;
            continue;
          }

          this.devices.set(key, {
            id: isGroup ? `group_${port}_${ip.replace(/\./g, '_')}` : `dev_${ip.replace(/\./g, '_')}`,
            name,
            ip: formattedIp,
            host: ip,
            port,
            model,
            isGroup,
            type: 'google'
          });
        }
      }
    });
  }

  getGoogleGroups() {
    return Array.from(this.devices.values()).filter(d => d.type === 'google' && d.isGroup);
  }

  getIndividualGoogleDevices() {
    return Array.from(this.devices.values()).filter(d => d.type === 'google' && !d.isGroup);
  }

  /**
   * ONVIF カメラデバイスの再読み込み
   */
  async reloadOnvifDevices() {
    // getDevices() 時に settingsManager の registeredDevices を動的に取得するため、
    // ここで最新のデバイス一覧を取得して返す
    return this.getDevices();
  }
}

module.exports = new DeviceManager();
