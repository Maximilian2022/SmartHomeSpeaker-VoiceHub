const { exec } = require('child_process');
const alexaManager = require('./alexa');

// 事前に検出確認済みのデバイス一覧（フォールバックおよび正確な日本語名マップ）
const KNOWN_DEVICES = [
  { id: 'room', name: '部屋', ip: '192.168.11.97', model: 'Google Nest Hub', type: 'google' },
  { id: 'study', name: '書斎', ip: '192.168.11.147', model: 'Google Home Mini', type: 'google' },
  { id: 'living', name: 'リビング', ip: '192.168.11.96', model: 'Google Nest Hub Max', type: 'google' },
  { id: 'bedroom', name: '寝室', ip: '192.168.11.81', model: 'Google Nest Hub', type: 'google' },
  { id: 'japanese_room', name: '和室', ip: '192.168.11.176', model: 'Google Home Mini', type: 'google' },
  { id: 'kitchen', name: 'キッチン', ip: '192.168.11.178', model: 'Google Home Mini', type: 'google' },
  { id: 'toilet_1f', name: 'トイレ1F', ip: '192.168.11.92', model: 'Google Home Mini', type: 'google' },
  { id: 'toilet_2f', name: 'トイレ2F', ip: '192.168.11.121', model: 'Google Home Mini', type: 'google' },
  { id: 'entrance', name: '玄関', ip: '192.168.11.9', model: 'Google Home Mini', type: 'google' },
  { id: 'living_tv', name: 'リビングTV', ip: '192.168.11.185', model: 'Google TV Streamer', type: 'google' },
  { id: 'bedroom_cast', name: '寝室キャスト', ip: '192.168.11.94', model: 'Chromecast', type: 'google' }
];

class DeviceManager {
  constructor() {
    this.devices = new Map();
    // 初期データを登録
    KNOWN_DEVICES.forEach(dev => this.devices.set(dev.ip, { ...dev }));

    // スキャン実行
    this.scanDevices();
    // 10分ごとに再スキャン
    setInterval(() => this.scanDevices(), 10 * 60 * 1000);
  }

  getDefaultDeviceIp() {
    return process.env.GOOGLE_HOME_IP || '192.168.11.97';
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

    return result;
  }

  findDevice(query) {
    if (!query) return null;
    const normalized = query.trim();

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
