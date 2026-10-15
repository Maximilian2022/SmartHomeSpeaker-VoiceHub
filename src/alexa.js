const { execFile } = require('child_process');
const path = require('path');
const fs = require('fs');

const SCRIPT_PATH = path.resolve(__dirname, '../bin/alexa_remote_control.sh');

class AlexaManager {
  constructor() {
    this.enabled = process.env.ALEXA_ENABLED === 'true';
    this.amazonDomain = process.env.ALEXA_AMAZON || 'amazon.co.jp';
    this.alexaDomain = process.env.ALEXA_ALEXA || 'alexa.amazon.co.jp';
    this.defaultDevice = process.env.ALEXA_DEFAULT_DEVICE || 'ALL';
  }

  isEnabled() {
    return process.env.ALEXA_ENABLED === 'true';
  }

  getEnvOptions() {
    const env = { ...process.env };
    if (process.env.ALEXA_EMAIL) env.EMAIL = process.env.ALEXA_EMAIL;
    if (process.env.ALEXA_PASSWORD) env.PASSWORD = process.env.ALEXA_PASSWORD;
    if (process.env.ALEXA_MFA_SECRET) env.MFA_SECRET = process.env.ALEXA_MFA_SECRET;
    env.AMAZON = this.amazonDomain;
    env.ALEXA = this.alexaDomain;
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
        return reject(new Error('Alexa 連携が無効になっています (.my.env で ALEXA_ENABLED=true に設定してください)'));
      }

      const target = deviceName || this.defaultDevice;
      // シングルクォートなどのエスケープ
      const cleanText = text.replace(/'/g, '');

      const args = ['-d', target, '-e', `speak:${cleanText}`];

      console.log(`[Alexa] 発言リクエスト: デバイス="${target}", テキスト="${cleanText}"`);

      execFile(SCRIPT_PATH, args, { env: this.getEnvOptions(), timeout: 20000 }, (err, stdout, stderr) => {
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
        return resolve([]);
      }

      execFile(SCRIPT_PATH, ['-a'], { env: this.getEnvOptions(), timeout: 15000 }, (err, stdout) => {
        if (err || !stdout) {
          console.warn('[Alexa] デバイス一覧の取得をスキップ:', err?.message || '空の応答');
          // スクリプト未認証時でも "ALL (全室Alexa)" だけは選択肢として返す
          return resolve([
            { id: 'alexa_ALL', name: 'Alexa (全室 Echo)', ip: 'alexa:ALL', model: 'Amazon Echo', type: 'alexa' }
          ]);
        }

        const lines = stdout.split('\n');
        const devices = [
          { id: 'alexa_ALL', name: 'Alexa (全室 Echo)', ip: 'alexa:ALL', model: 'Amazon Echo Group', type: 'alexa' }
        ];

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith('===') || trimmed.includes('the following devices exist')) continue;
          // デバイス名を取り出す
          devices.push({
            id: `alexa_${trimmed.replace(/\s+/g, '_')}`,
            name: `Alexa: ${trimmed}`,
            ip: `alexa:${trimmed}`,
            model: 'Amazon Echo',
            type: 'alexa'
          });
        }

        resolve(devices);
      });
    });
  }
}

module.exports = new AlexaManager();
