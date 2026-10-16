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
    whisperVolume: 10,
    topMuteDuration: 'indefinite', // 'indefinite' | '30' | '60' | '120' | '1440'
    aiSummaryEnabled: true,
    aiSummaryThreshold: 2,
    aiSummaryCustomPrompt: ''
  },
  ai: {
    enabled: true,
    provider: 'gemini', // 'gemini' | 'openai'
    geminiApiKey: process.env.GEMINI_API_KEY || process.env.AI_API_KEY || '',
    openaiApiKey: process.env.OPENAI_API_KEY || '',
    geminiModel: 'gemini-3.8-flash',
    openaiModel: 'gpt-4o-mini',
    summarizeDndQueue: true,
    summaryThreshold: 2,
    summarizeDailyCalendar: true,
    dailyCalendarPrompt: '',
    customPrompt: ''
  },
  chime: 'dingdong', // 'none' | 'dingdong' | 'bell' | 'announce' | 'alert'
  deduplication: {
    enabled: true,
    cooldownSeconds: 30
  },
  deviceGroups: {
    '1F': ['リビング', 'キッチン', '和室', 'トイレ1F'],
    '2F': ['寝室', '書斎', '部屋', 'トイレ2F'],
    'LDK': ['リビング', 'キッチン']
  },
  autoVolume: {
    enabled: true,
    rules: [
      { id: 'day', name: '日中 (07:00〜21:00)', startTime: '07:00', endTime: '21:00', volume: 50 },
      { id: 'evening', name: '夜間 (21:00〜23:00)', startTime: '21:00', endTime: '23:00', volume: 25 },
      { id: 'night', name: '深夜 (23:00〜07:00)', startTime: '23:00', endTime: '07:00', volume: 10 }
    ]
  },
  ipAliases: {}, // { "192.168.1.50": "ラズパイ", ... }
  onvif: {
    enabled: true,
    defaultUsername: 'admin',
    defaultPassword: '',
    registeredDevices: []
  },
  disaster: {
    enabled: true,
    targetScope: 'all', // 'all' (家中すべて) | 'default' (標準スピーカー) | 'specific' (個別選択)
    targetDevices: ['ALL'],
    area: {
      prefCode: '130000', // 東京都
      prefName: '東京都',
      cityCode: '1310100', // 千代田区 (任意: 空文字なら都道府県全域)
      cityName: '千代田区'
    },
    earthquake: {
      enabled: true,
      eewEnabled: true,
      eewUrgent: true,
      eewVolume: 80,
      reportEnabled: true,
      minScale: 30, // 30: 震度3以上 (10: 震度1, 20: 震度2, 30: 震度3, 40: 震度4, 45: 震度5弱...)
      reportUrgent: false,
      targetScope: 'local' // 'local' (自地域のみ) | 'all' (全国)
    },
    weatherWarning: {
      enabled: true,
      level: 'warning', // 'special' (特別警報) | 'warning' (警報以上) | 'advisory' (注意報含む)
      notifyClear: true, // 解除時も通知
      urgent: false,
      checkIntervalMinutes: 5
    },
    dailyWeather: {
      enabled: true,
      includeAdvice: true // 傘・気温アドバイスを含める
    }
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
          chime: parsed.chime !== undefined ? parsed.chime : DEFAULT_SETTINGS.chime,
          deduplication: {
            ...DEFAULT_SETTINGS.deduplication,
            ...(parsed.deduplication || {})
          },
          deviceGroups: parsed.deviceGroups || { ...DEFAULT_SETTINGS.deviceGroups },
          autoVolume: {
            ...DEFAULT_SETTINGS.autoVolume,
            ...(parsed.autoVolume || {})
          },
          onvif: {
            ...DEFAULT_SETTINGS.onvif,
            ...(parsed.onvif || {})
          },
          ipAliases: parsed.ipAliases || {},
          calendar: {
            ...DEFAULT_SETTINGS.calendar,
            ...(parsed.calendar || {})
          },
          dnd: {
            ...DEFAULT_SETTINGS.dnd,
            ...(parsed.dnd || {})
          },
          ai: {
            ...DEFAULT_SETTINGS.ai,
            ...(parsed.ai || {})
          }
        };

        // API Key が保存されていない場合は環境変数をフォールバック
        if (!this.settings.ai.geminiApiKey && (process.env.GEMINI_API_KEY || process.env.AI_API_KEY)) {
          this.settings.ai.geminiApiKey = process.env.GEMINI_API_KEY || process.env.AI_API_KEY;
        }
        if (!this.settings.ai.openaiApiKey && process.env.OPENAI_API_KEY) {
          this.settings.ai.openaiApiKey = process.env.OPENAI_API_KEY;
        }

        // 廃止・提供終了済みモデルの自動マイグレーション
        const retiredGemini = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.5-flash-8b', 'gemini-1.0-pro', 'gemini-pro', 'gemini-3.7-flash'];
        if (retiredGemini.includes(this.settings.ai.geminiModel)) {
          console.warn(`[Settings] 以前設定されていたモデル "${this.settings.ai.geminiModel}" は提供終了したため、最新の "gemini-3.8-flash" に自動更新しました`);
          this.settings.ai.geminiModel = 'gemini-3.8-flash';
          this.save();
        }

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
        if (!this.settings.dnd.topMuteDuration) {
          this.settings.dnd.topMuteDuration = DEFAULT_SETTINGS.dnd.topMuteDuration;
        }

        if (this.settings.disaster) {
          if (!this.settings.disaster.targetScope) {
            this.settings.disaster.targetScope = DEFAULT_SETTINGS.disaster.targetScope;
          }
          if (!Array.isArray(this.settings.disaster.targetDevices)) {
            this.settings.disaster.targetDevices = [...DEFAULT_SETTINGS.disaster.targetDevices];
          }
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
    if (updates.ipAliases !== undefined) {
      this.settings.ipAliases = updates.ipAliases && typeof updates.ipAliases === 'object' ? updates.ipAliases : {};
    }
    if (updates.chime !== undefined) {
      this.settings.chime = updates.chime;
    }
    if (updates.deduplication) {
      this.settings.deduplication = {
        ...this.settings.deduplication,
        ...updates.deduplication
      };
    }
    if (updates.deviceGroups !== undefined) {
      this.settings.deviceGroups = updates.deviceGroups && typeof updates.deviceGroups === 'object' ? updates.deviceGroups : {};
    }
    if (updates.autoVolume) {
      this.settings.autoVolume = {
        ...this.settings.autoVolume,
        ...updates.autoVolume
      };
    }
    if (updates.onvif) {
      this.settings.onvif = {
        ...this.settings.onvif,
        ...updates.onvif,
        registeredDevices: Array.isArray(updates.onvif.registeredDevices)
          ? updates.onvif.registeredDevices
          : (this.settings.onvif.registeredDevices || [])
      };
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
    if (updates.ai) {
      this.settings.ai = {
        ...this.settings.ai,
        ...updates.ai
      };
    }
    if (updates.disaster) {
      this.settings.disaster = {
        ...this.settings.disaster,
        ...updates.disaster,
        area: {
          ...((this.settings.disaster && this.settings.disaster.area) || {}),
          ...((updates.disaster && updates.disaster.area) || {})
        },
        earthquake: {
          ...((this.settings.disaster && this.settings.disaster.earthquake) || {}),
          ...((updates.disaster && updates.disaster.earthquake) || {})
        },
        weatherWarning: {
          ...((this.settings.disaster && this.settings.disaster.weatherWarning) || {}),
          ...((updates.disaster && updates.disaster.weatherWarning) || {})
        },
        dailyWeather: {
          ...((this.settings.disaster && this.settings.disaster.dailyWeather) || {}),
          ...((updates.disaster && updates.disaster.dailyWeather) || {})
        }
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

  getDisasterSettings() {
    return this.settings.disaster || DEFAULT_SETTINGS.disaster;
  }
}

module.exports = new SettingsManager();
