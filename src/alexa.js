const { execFile } = require('child_process');
const path = require('path');
const fs = require('fs');
const alexaCookie = require('alexa-cookie2');

const SCRIPT_PATH = path.resolve(__dirname, '../bin/alexa_remote_control.sh');
const DATA_DIR = path.resolve(__dirname, '../data');
const CREDENTIALS_PATH = path.join(DATA_DIR, 'alexa_credentials.json');

class AlexaManager {
  constructor() {
    this.amazonDomain = process.env.ALEXA_AMAZON || 'amazon.co.jp';
    this.alexaDomain = process.env.ALEXA_ALEXA || 'alexa.amazon.co.jp';
    this.defaultDevice = process.env.ALEXA_DEFAULT_DEVICE || 'ALL';

    this.credentials = null;
    this.configured = false;
    this.proxyRunning = false;
    this.proxyUrl = null;
    this.proxyError = null;
    this.devicesCache = [];

    this._ensureDataDir();
    this.loadCredentials();
  }

  _ensureDataDir() {
    if (!fs.existsSync(DATA_DIR)) {
      try { fs.mkdirSync(DATA_DIR, { recursive: true }); } catch (e) {}
    }
  }

  loadCredentials() {
    try {
      if (fs.existsSync(CREDENTIALS_PATH)) {
        const raw = fs.readFileSync(CREDENTIALS_PATH, 'utf-8');
        this.credentials = JSON.parse(raw);
        if (this.credentials && (this.credentials.refreshToken || this.credentials.localCookie)) {
          this.configured = true;
          console.log('[Alexa] 保存済み認証情報を読み込みました (連携有効)');
          return;
        }
      }
    } catch (err) {
      console.warn('[Alexa] 認証情報の読み込みに失敗:', err.message);
    }

    if (process.env.ALEXA_REFRESH_TOKEN) {
      this.credentials = { refreshToken: process.env.ALEXA_REFRESH_TOKEN };
      this.configured = true;
      console.log('[Alexa] 環境変数の ALEXA_REFRESH_TOKEN を使用します');
    } else {
      this.configured = false;
    }
  }

  saveCredentials(data) {
    try {
      this._ensureDataDir();
      fs.writeFileSync(CREDENTIALS_PATH, JSON.stringify(data, null, 2), 'utf-8');
      this.credentials = data;
      this.configured = true;
      console.log('[Alexa] 認証情報を保存しました:', CREDENTIALS_PATH);
    } catch (err) {
      console.error('[Alexa] 認証情報保存エラー:', err.message);
    }
  }

  logout() {
    try {
      if (fs.existsSync(CREDENTIALS_PATH)) {
        fs.unlinkSync(CREDENTIALS_PATH);
      }
    } catch (e) {}
    this.credentials = null;
    this.configured = false;
    this.devicesCache = [];
    console.log('[Alexa] 連携を解除しました');
  }

  isEnabled() {
    return this.configured || process.env.ALEXA_ENABLED === 'true';
  }

  getAuthStatus(hostIp = '127.0.0.1') {
    return {
      enabled: this.isEnabled(),
      configured: this.configured,
      proxyRunning: this.proxyRunning,
      proxyUrl: this.proxyRunning ? this.proxyUrl : null,
      proxyError: this.proxyError,
      deviceCount: this.devicesCache.length
    };
  }

  /**
   * Alexa ログイン用プロキシを開始
   */
  startProxyAuth(hostIp = '192.168.11.244', port = 8081) {
    return new Promise((resolve, reject) => {
      if (this.proxyRunning) {
        return resolve({
          success: true,
          alreadyRunning: true,
          loginUrl: this.proxyUrl
        });
      }

      this.proxyRunning = true;
      this.proxyError = null;
      this.proxyUrl = `http://${hostIp}:${port}`;

      const config = {
        logger: (msg) => console.log('[Alexa Cookie]', msg),
        proxyOwnIp: hostIp,
        proxyPort: port,
        proxyListenBind: '0.0.0.0',
        amazonPage: this.amazonDomain,
        baseAmazonPage: this.amazonDomain,
        acceptLanguage: 'ja-JP',
        amazonPageProxyLanguage: 'ja_JP',
        proxyOnly: true,
        setupProxy: true,
        formerRegistrationData: this.credentials || undefined,
        proxyCloseWindowHTML: `
          <!DOCTYPE html>
          <html>
          <head><meta charset="utf-8"><title>認証成功</title></head>
          <body style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#0d1117;color:#e6edf3;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
            <div style="background:#161b22;border:1px solid #30363d;padding:40px;border-radius:12px;text-align:center;max-width:480px;box-shadow:0 8px 24px rgba(0,0,0,0.5);">
              <div style="font-size:48px;margin-bottom:16px;">🎉</div>
              <h2 style="color:#3fb950;margin-top:0;">Amazon Alexa 認証に成功しました！</h2>
              <p style="color:#8b949e;line-height:1.6;">認証トークンが正常にシステムへ保存されました。<br>このウィンドウを閉じて、管理画面（Web GUI）にお戻りください。</p>
            </div>
          </body>
          </html>
        `
      };

      console.log(`[Alexa Proxy] プロキシサーバーを起動します: ${this.proxyUrl}`);

      alexaCookie.generateAlexaCookie(config, (err, result) => {
        // プロキシ起動直後の通知メッセージ（Please open http:...）は正常な待機状態
        if (err && err.message && err.message.includes('Please open')) {
          console.log('[Alexa Proxy] プロキシサーバー起動完了。ユーザーのログインを待機しています...');
          this.proxyRunning = true;
          this.proxyError = null;
          return;
        }

        this.proxyRunning = false;
        try { alexaCookie.stopProxyServer(); } catch (e) {}

        if (err || !result) {
          console.error('[Alexa Proxy Error]:', err ? err.message : '空のレスポンス');
          this.proxyError = err ? err.message : '認証に失敗しました';
          return;
        }

        console.log('[Alexa Proxy] 認証完了！トークンを取得しました');
        this.saveCredentials(result);

        // 即座にデバイス一覧を更新
        this.listDevices().catch(() => {});
      });

      resolve({
        success: true,
        loginUrl: this.proxyUrl
      });
    });
  }

  /**
   * プロキシサーバーを強制停止
   */
  stopProxyAuth() {
    try {
      alexaCookie.stopProxyServer();
    } catch (e) {}
    this.proxyRunning = false;
    this.proxyUrl = null;
    console.log('[Alexa Proxy] プロキシサーバーを停止しました');
  }

  getEnvOptions() {
    const env = { ...process.env };
    if (this.credentials && this.credentials.refreshToken) {
      env.REFRESH_TOKEN = this.credentials.refreshToken;
    } else if (process.env.ALEXA_REFRESH_TOKEN) {
      env.REFRESH_TOKEN = process.env.ALEXA_REFRESH_TOKEN;
    }
    env.AMAZON = this.amazonDomain;
    env.ALEXA = this.alexaDomain;
    env.TMP = DATA_DIR; // Cookie などの書き込み先をマウントされた data ディレクトリに
    return env;
  }

  /**
   * Alexa デバイスに発言させる
   * @param {string} text 発言テキスト
   * @param {string} deviceName デバイス名（'ALL' で全室Echo）
   */
  speak(text, deviceName = null) {
    return new Promise((resolve, reject) => {
      if (!this.isEnabled()) {
        return reject(new Error('Alexa 連携が設定されていません。管理画面の「接続デバイス」タブから Amazon ログインを行ってください。'));
      }

      const target = deviceName || this.defaultDevice;
      const cleanText = text.replace(/'/g, '');
      const args = ['-d', target, '-e', `speak:${cleanText}`];

      console.log(`[Alexa] 発言リクエスト: デバイス="${target}", テキスト="${cleanText}"`);

      execFile(SCRIPT_PATH, args, { env: this.getEnvOptions(), timeout: 25000 }, (err, stdout, stderr) => {
        if (err) {
          console.error('[Alexa Error]:', err.message, stderr);
          return reject(new Error(`Alexa 発言失敗: ${err.message}`));
        }
        console.log('[Alexa Response]:', stdout.trim());
        resolve({ target, output: stdout.trim() });
      });
    });
  }

  /**
   * 登録済み Alexa デバイス一覧を取得
   */
  listDevices() {
    return new Promise((resolve) => {
      if (!this.isEnabled()) {
        this.devicesCache = [];
        return resolve([]);
      }

      execFile(SCRIPT_PATH, ['-a'], { env: this.getEnvOptions(), timeout: 15000 }, (err, stdout) => {
        if (err || !stdout) {
          console.warn('[Alexa] デバイス一覧の取得をスキップ:', err?.message || '空の応答');
          if (this.configured) {
            this.devicesCache = [
              { id: 'alexa_ALL', name: 'Alexa (全室 Echo)', ip: 'alexa:ALL', model: 'Amazon Echo Group', type: 'alexa' }
            ];
          } else {
            this.devicesCache = [];
          }
          return resolve(this.devicesCache);
        }

        const lines = stdout.split('\n');
        const devices = [
          { id: 'alexa_ALL', name: 'Alexa (全室 Echo)', ip: 'alexa:ALL', model: 'Amazon Echo Group', type: 'alexa' }
        ];

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith('===') || trimmed.includes('the following devices exist')) continue;
          devices.push({
            id: `alexa_${trimmed.replace(/\s+/g, '_')}`,
            name: `Alexa: ${trimmed}`,
            ip: `alexa:${trimmed}`,
            model: 'Amazon Echo',
            type: 'alexa'
          });
        }

        this.devicesCache = devices;
        resolve(devices);
      });
    });
  }
}

module.exports = new AlexaManager();
