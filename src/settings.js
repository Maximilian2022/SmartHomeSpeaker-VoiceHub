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
    calendars: [], // [{ id, name, icalUrl, enabled }]
    icalUrl: '', // 互換性維持
    remindEnabled: true,
    remindMinutesBefore: 10,
    dailySummaryEnabled: true,
    dailySummaryTime: '07:30',
    targetDevices: ['default'],
    voice: 'ja-JP-NanamiNeural',
    rate: '+0%',
    pitch: '+0Hz',
    volumeLevel: ''
  },
  dnd: {
    enabled: true,
    scheduleEnabled: false,
    schedules: [
      {
        id: 'dnd_work',
        name: '平日業務時間',
        days: ['1', '2', '3', '4', '5'],
        startTime: '09:00',
        endTime: '18:00',
        enabled: true
      },
      {
        id: 'dnd_night',
        name: '深夜帯',
        days: ['0', '1', '2', '3', '4', '5', '6'],
        startTime: '23:00',
        endTime: '07:00',
        enabled: false
      }
    ],
    calendarEnabled: true,
    calendarMode: 'keywords', // 'keywords' | 'all'
    calendarKeywords: 'MTG, 会議, Zoom, Teams, Meet, 打ち合わせ, 商談, 集中',
    calendarIncludeAllDay: false,
    manualUntil: null,
    manualReason: '',
    targetScope: 'all', // 'all' | 'specific'
    targetDevices: [],
    action: 'skip', // 'skip' | 'whisper' | 'queue'
    whisperVolume: 10
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
          },
          dnd: {
            ...DEFAULT_SETTINGS.dnd,
            ...(parsed.dnd || {})
          }
        };

        // 複数カレンダー構造への自動マイグレーション
        if (!Array.isArray(this.settings.calendar.calendars)) {
          this.settings.calendar.calendars = [];
        }
        if (this.settings.calendar.calendars.length === 0 && this.settings.calendar.icalUrl) {
          this.settings.calendar.calendars.push({
            id: 'cal_default',
            name: 'メインカレンダー',
            icalUrl: this.settings.calendar.icalUrl,
            enabled: true
          });
        }
        if (this.settings.calendar.remindEnabled === undefined) {
          this.settings.calendar.remindEnabled = (parseInt(this.settings.calendar.remindMinutesBefore, 10) || 0) > 0;
        }

        // DND スケジュール配列の確認
        if (!Array.isArray(this.settings.dnd.schedules)) {
          this.settings.dnd.schedules = [...DEFAULT_SETTINGS.dnd.schedules];
        }
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
    if (updates.dnd) {
      this.settings.dnd = {
        ...this.settings.dnd,
        ...updates.dnd
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
