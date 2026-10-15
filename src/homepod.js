const { execFile } = require('child_process');
const path = require('path');
const fs = require('fs');

const DATA_DIR = path.resolve(__dirname, '../data');
const CACHE_FILE = path.join(DATA_DIR, 'homepod_devices.json');
const SCAN_SCRIPT = path.resolve(__dirname, '../bin/homepod_scan.py');
const STREAM_SCRIPT = path.resolve(__dirname, '../bin/homepod_stream.py');

// Python バイナリパスの解決 (コンテナ内 /opt/pyatv-env またはホスト側 /tmp/pyatv-env)
function getPythonPath() {
  const candidates = [
    '/opt/pyatv-env/bin/python3',
    '/tmp/pyatv-env/bin/python3',
    'python3'
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return 'python3';
}

class HomePodManager {
  constructor() {
    this.devicesCache = [];
    this.pythonBin = getPythonPath();
    this.loadCache();
  }

  loadCache() {
    try {
      if (fs.existsSync(CACHE_FILE)) {
        const raw = fs.readFileSync(CACHE_FILE, 'utf-8');
        this.devicesCache = JSON.parse(raw);
        console.log(`[HomePod] キャッシュから ${this.devicesCache.length} 件のデバイスを読み込みました`);
      }
    } catch (e) {
      console.warn('[HomePod] キャッシュ読み込み失敗:', e.message);
    }
  }

  saveCache(devices) {
    try {
      if (!fs.existsSync(DATA_DIR)) {
        fs.mkdirSync(DATA_DIR, { recursive: true });
      }
      fs.writeFileSync(CACHE_FILE, JSON.stringify(devices, null, 2), 'utf-8');
    } catch (e) {
      console.error('[HomePod] キャッシュ保存失敗:', e.message);
    }
  }

  /**
   * LAN 内の HomePod を高速スキャン (pyatv)
   */
  scanDevices() {
    return new Promise((resolve) => {
      this.pythonBin = getPythonPath();
      console.log(`[HomePod] デバイススキャン実行: ${this.pythonBin} ${SCAN_SCRIPT}`);

      execFile(this.pythonBin, [SCAN_SCRIPT], { timeout: 8000 }, (err, stdout) => {
        if (err && !stdout) {
          console.warn('[HomePod] スキャン失敗またはタイムアウト:', err.message);
          return resolve(this.devicesCache);
        }

        try {
          const list = JSON.parse(stdout.trim());
          if (Array.isArray(list) && list.length > 0) {
            const fullList = [
              {
                id: 'homepod_ALL',
                name: '全室 HomePod',
                ip: 'homepod:ALL',
                model: 'Apple HomePod Group',
                type: 'homepod'
              },
              ...list
            ];
            this.devicesCache = fullList;
            this.saveCache(fullList);
            console.log(`[HomePod] スキャン完了: ${list.length} 台の HomePod を認識しました`);
            return resolve(fullList);
          }
        } catch (e) {
          console.warn('[HomePod] スキャン出力のパース失敗:', e.message);
        }

        resolve(this.devicesCache);
      });
    });
  }

  async getDevices() {
    if (this.devicesCache.length > 0) {
      this.scanDevices().catch(() => {});
      return this.devicesCache;
    }
    return await this.scanDevices();
  }

  /**
   * 音声ファイルを HomePod で再生
   * @param {string} audioFilePath ローカルの mp3 ファイル絶対パス
   * @param {string} target 'ALL', 'homepod:ALL', 'homepod:MAC', '192.168.x.x', etc.
   */
  playAudio(audioFilePath, target) {
    return new Promise((resolve, reject) => {
      this.pythonBin = getPythonPath();

      if (!fs.existsSync(audioFilePath)) {
        return reject(new Error(`音声ファイルが存在しません: ${audioFilePath}`));
      }

      let cleanTarget = target;
      if (cleanTarget.startsWith('homepod:')) {
        cleanTarget = cleanTarget.slice(8);
      }

      // 'ALL' の場合はキャッシュされた個別全台に並行ストリーミング
      if (cleanTarget === 'ALL') {
        const individualDevices = this.devicesCache.filter(d => d.ip !== 'homepod:ALL');
        if (individualDevices.length === 0) {
          return reject(new Error('送信可能な HomePod デバイスが見つかりません'));
        }
        console.log(`[HomePod] 全室 HomePod (${individualDevices.length} 台) に一斉送信します`);
        const promises = individualDevices.map(d => this.playAudio(audioFilePath, d.ip));
        return Promise.allSettled(promises).then(results => {
          resolve({ target: 'ALL', results });
        });
      }

      // デバイス情報を検索（rawIp があれば rawIp、なければ MAC または cleanTarget）
      const found = this.devicesCache.find(d =>
        d.mac === cleanTarget || d.rawIp === cleanTarget || d.rawName === cleanTarget || d.ip === `homepod:${cleanTarget}`
      );

      const targetAddress = found && found.rawIp ? found.rawIp : cleanTarget;

      console.log(`[HomePod] 再生実行: ${this.pythonBin} ${STREAM_SCRIPT} ${targetAddress} ${audioFilePath}`);

      execFile(this.pythonBin, [STREAM_SCRIPT, targetAddress, audioFilePath], { timeout: 25000 }, (err, stdout, stderr) => {
        if (err) {
          console.error('[HomePod Error]:', err.message, stderr);
          return reject(new Error(`HomePod 再生失敗: ${err.message}`));
        }
        console.log(`[HomePod Response]: ${found ? found.name : targetAddress} での再生完了`);
        resolve({ target: cleanTarget, output: stdout.trim() });
      });
    });
  }
}

module.exports = new HomePodManager();
