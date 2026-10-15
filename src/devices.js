const { exec } = require('child_process');
const alexaManager = require('./alexa');
const homepodManager = require('./homepod');
const settingsManager = require('./settings');

// 事前に検出確認済みのデバイス一覧（空配列にして mDNS / Avahi による完全自動検出とする）
const KNOWN_DEVICES = [];

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

    return result;
  }

  findDevice(query) {
    if (!query) return null;
    const normalized = query.trim();

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

    // IP完全一致
    if (this.devices.has(normalized)) {
      return this.devices.get(normalized);
    }

    // 名前やIDでの検索
    for (const dev of this.devices.values()) {
      if (dev.name === normalized || dev.id === normalized || dev.name.includes(normalized)) {
        return dev;
      }
    }

    // IPアドレス形式なら一時デバイスとして返す
    if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(normalized)) {
      return { id: normalized, name: normalized, ip: normalized, model: 'Custom IP', type: 'google' };
    }

    return null;
  }

  /**
   * avahi-browse を利用して LAN 内の新規 Google Cast デバイスを動的追加
   */
  scanDevices() {
    exec('avahi-browse -r -t -p _googlecast._tcp', (err, stdout) => {
      if (err || !stdout) return;

      const lines = stdout.split('\n');
      for (const line of lines) {
        const parts = line.split(';');
        if (parts[0] === '=' && parts[2] === 'IPv4' && parts[7]) {
          const ip = parts[7];
          if (this.devices.has(ip)) {
            continue;
          }

          const txtRaw = parts[9] || '';
          let name = parts[3] || `Cast-${ip}`;
          let model = 'Google Cast';

          const mdMatch = txtRaw.match(/"md=([^"]+)"/);
          if (mdMatch) model = mdMatch[1];

          this.devices.set(ip, {
            id: `dev_${ip.replace(/\./g, '_')}`,
            name,
            ip,
            model,
            type: 'google'
          });
        }
      }
    });
  }
}

module.exports = new DeviceManager();
