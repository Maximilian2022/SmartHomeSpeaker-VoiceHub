const { exec } = require('child_process');

// 事前に検出確認済みのデバイス一覧（フォールバックおよび正確な日本語名マップ）
const KNOWN_DEVICES = [
  { id: 'room', name: '部屋', ip: '192.168.11.97', model: 'Google Nest Hub' },
  { id: 'study', name: '書斎', ip: '192.168.11.147', model: 'Google Home Mini' },
  { id: 'living', name: 'リビング', ip: '192.168.11.96', model: 'Google Nest Hub Max' },
  { id: 'bedroom', name: '寝室', ip: '192.168.11.81', model: 'Google Nest Hub' },
  { id: 'japanese_room', name: '和室', ip: '192.168.11.176', model: 'Google Home Mini' },
  { id: 'kitchen', name: 'キッチン', ip: '192.168.11.178', model: 'Google Home Mini' },
  { id: 'toilet_1f', name: 'トイレ1F', ip: '192.168.11.92', model: 'Google Home Mini' },
  { id: 'toilet_2f', name: 'トイレ2F', ip: '192.168.11.121', model: 'Google Home Mini' },
  { id: 'entrance', name: '玄関', ip: '192.168.11.9', model: 'Google Home Mini' },
  { id: 'living_tv', name: 'リビングTV', ip: '192.168.11.185', model: 'Google TV Streamer' },
  { id: 'bedroom_cast', name: '寝室キャスト', ip: '192.168.11.94', model: 'Chromecast' }
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

  getDevices() {
    const defaultIp = this.getDefaultDeviceIp();
    return Array.from(this.devices.values()).map(dev => ({
      ...dev,
      isDefault: dev.ip === defaultIp
    }));
  }

  findDevice(query) {
    if (!query) return null;
    const normalized = query.trim();

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
      return { id: normalized, name: normalized, ip: normalized, model: 'Custom IP' };
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
          // KNOWN_DEVICES に既にあるIPはきれいな日本語名を維持
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
            model
          });
        }
      }
    });
  }
}

module.exports = new DeviceManager();
