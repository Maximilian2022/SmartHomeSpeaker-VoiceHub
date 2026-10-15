const fs = require('fs');
const path = require('path');

const DATA_DIR = path.resolve(__dirname, '../data');
const SETTINGS_FILE = path.join(DATA_DIR, 'settings.json');

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

const DEFAULT_SETTINGS = {
  defaultDeviceId: process.env.GOOGLE_HOME_IP || '',
  webhookToken: process.env.WEBHOOK_TOKEN || '',
  calendar: {
    enabled: false,
    icalUrl: '',
    remindMinutesBefore: 10,
    dailySummaryEnabled: true,
    dailySummaryTime: '07:30',
    targetDevices: ['default'],
    voice: 'ja-JP-NanamiNeural',
    volumeLevel: ''
  }
};

class SettingsManager {
  constructor() {
    this.settings = { ...DEFAULT_SETTINGS };
    this.load();
  }

  load() {
    try {
      if (fs.existsSync(SETTINGS_FILE)) {
        const raw = fs.readFileSync(SETTINGS_FILE, 'utf8');
        const parsed = JSON.parse(raw);
        this.settings = {
          ...DEFAULT_SETTINGS,
          ...parsed,
          calendar: {
            ...DEFAULT_SETTINGS.calendar,
            ...(parsed.calendar || {})
          }
        };
      } else {
        this.settings = { ...DEFAULT_SETTINGS };
        this.save();
      }
    } catch (err) {
      console.error('[Settings] 設定ファイル読み込みエラー:', err.message);
      this.settings = { ...DEFAULT_SETTINGS };
    }
  }

  save() {
    try {
      fs.writeFileSync(SETTINGS_FILE, JSON.stringify(this.settings, null, 2), 'utf8');
    } catch (err) {
      console.error('[Settings] 設定ファイル保存エラー:', err.message);
    }
  }

  get() {
    return this.settings;
  }

  update(updates) {
    if (updates.defaultDeviceId !== undefined) {
      this.settings.defaultDeviceId = updates.defaultDeviceId;
    }
    if (updates.webhookToken !== undefined) {
      this.settings.webhookToken = updates.webhookToken;
    }
    if (updates.calendar) {
      this.settings.calendar = {
        ...this.settings.calendar,
        ...updates.calendar
      };
    }
    this.save();
    return this.settings;
  }

  getDefaultDeviceId() {
    return this.settings.defaultDeviceId || process.env.GOOGLE_HOME_IP || '';
  }

  setDefaultDeviceId(id) {
    this.settings.defaultDeviceId = id;
    this.save();
    return this.settings.defaultDeviceId;
  }

  getWebhookToken() {
    return this.settings.webhookToken || process.env.WEBHOOK_TOKEN || '';
  }

  setWebhookToken(token) {
    this.settings.webhookToken = token;
    this.save();
    return this.settings.webhookToken;
  }
}

module.exports = new SettingsManager();
