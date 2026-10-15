const https = require('https');
const http = require('http');
const { URL } = require('url');
const settingsManager = require('./settings');

/**
 * iCal 日付文字列を Date オブジェクトに変換
 * @param {string} dateStr 例: 20261015T023000Z, 20261015T113000, 20261015
 */
function parseIcalDate(dateStr) {
  if (!dateStr) return null;
  const clean = dateStr.trim();

  // 終日予定 (YYYYMMDD)
  if (/^\d{8}$/.test(clean)) {
    const y = parseInt(clean.slice(0, 4), 10);
    const m = parseInt(clean.slice(4, 6), 10) - 1;
    const d = parseInt(clean.slice(6, 8), 10);
    return new Date(y, m, d, 0, 0, 0);
  }

  // UTC 日時 (YYYYMMDDTHHMMSSZ)
  if (/^\d{8}T\d{6}Z$/.test(clean)) {
    const y = parseInt(clean.slice(0, 4), 10);
    const m = parseInt(clean.slice(4, 6), 10) - 1;
    const d = parseInt(clean.slice(6, 8), 10);
    const h = parseInt(clean.slice(9, 11), 10);
    const min = parseInt(clean.slice(11, 13), 10);
    const s = parseInt(clean.slice(13, 15), 10);
    return new Date(Date.UTC(y, m, d, h, min, s));
  }

  // ローカル日時 (YYYYMMDDTHHMMSS)
  if (/^\d{8}T\d{6}$/.test(clean)) {
    const y = parseInt(clean.slice(0, 4), 10);
    const m = parseInt(clean.slice(4, 6), 10) - 1;
    const d = parseInt(clean.slice(6, 8), 10);
    const h = parseInt(clean.slice(9, 11), 10);
    const min = parseInt(clean.slice(11, 13), 10);
    const s = parseInt(clean.slice(13, 15), 10);
    return new Date(y, m, d, h, min, s);
  }

  return new Date(clean);
}

/**
 * URL からテキストデータを取得 (リダイレクト追従)
 */
function fetchUrl(targetUrl, maxRedirects = 5) {
  return new Promise((resolve, reject) => {
    if (maxRedirects <= 0) return reject(new Error('リダイレクト回数が上限を超えました'));

    const parsed = new URL(targetUrl);
    const client = parsed.protocol === 'https:' ? https : http;

    const req = client.get(targetUrl, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        const redirectUrl = new URL(res.headers.location, targetUrl).href;
        return resolve(fetchUrl(redirectUrl, maxRedirects - 1));
      }

      if (res.statusCode !== 200) {
        return reject(new Error(`HTTPエラー: ${res.statusCode}`));
      }

      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => resolve(data));
    });

    req.on('error', reject);
    req.setTimeout(15000, () => {
      req.destroy();
      reject(new Error('カレンダー取得タイムアウト (15秒)'));
    });
  });
}

/**
 * ICS プレーンテキストをパースしてイベント配列を生成
 */
function parseIcsEvents(icsText) {
  const events = [];
  // 改行コード正規化とアンフォールディング（複数行折り返しの結合）
  const unfolded = icsText.replace(/\r\n[ \t]/g, '').replace(/\r/g, '');
  const lines = unfolded.split('\n');

  let current = null;

  for (let line of lines) {
    line = line.trim();
    if (!line) continue;

    if (line === 'BEGIN:VEVENT') {
      current = {};
      continue;
    }

    if (line === 'END:VEVENT' && current) {
      if (current.summary && current.start) {
        events.push(current);
      }
      current = null;
      continue;
    }

    if (!current) continue;

    // キーと値の分離
    const colonIdx = line.indexOf(':');
    if (colonIdx === -1) continue;

    const keyPart = line.slice(0, colonIdx);
    const value = line.slice(colonIdx + 1);

    const [keyName, ...params] = keyPart.split(';');

    if (keyName === 'SUMMARY') {
      current.summary = value.replace(/\\,/g, ',').replace(/\\;/g, ';').replace(/\\n/g, ' ');
    } else if (keyName === 'DTSTART') {
      current.start = parseIcalDate(value);
      current.isAllDay = !value.includes('T');
    } else if (keyName === 'DTEND') {
      current.end = parseIcalDate(value);
    } else if (keyName === 'LOCATION') {
      current.location = value.replace(/\\,/g, ',').replace(/\\;/g, ';');
    } else if (keyName === 'UID') {
      current.uid = value;
    }
  }

  return events;
}

class CalendarManager {
  constructor() {
    this.eventsCache = [];
    this.lastFetched = null;
    this.notifiedReminders = new Set(); // UID_StartTime_Minutes の通知済みフラグ
    this.notifiedSummaries = new Set(); // CalID_YYYY-MM-DD の通知済みフラグ
    this.lastDailySummaryDate = null; // YYYY-MM-DD
    this.executor = null;

    // 1分ごとにチェック
    setInterval(() => this.tick(), 60 * 1000).unref();
    // 15分ごとにカレンダーをバックグラウンド再取得
    setInterval(() => this.syncEvents(), 15 * 60 * 1000).unref();
  }

  setExecutor(fn) {
    this.executor = fn;
  }

  async syncEvents() {
    const config = settingsManager.get().calendar;
    if (!config || !config.enabled) {
      this.eventsCache = [];
      return [];
    }

    // カレンダーリストの取得 (複数対応、後方互換対応)
    let cals = Array.isArray(config.calendars) ? config.calendars.filter(c => c.enabled !== false && c.icalUrl) : [];
    if (cals.length === 0 && config.icalUrl) {
      cals = [{ id: 'cal_default', name: 'メインカレンダー', icalUrl: config.icalUrl, enabled: true }];
    }

    if (cals.length === 0) {
      this.eventsCache = [];
      return [];
    }

    try {
      console.log(`[Calendar] ${cals.length} 件のカレンダーから同期を開始します...`);
      const results = await Promise.allSettled(
        cals.map(async (cal) => {
          const icsText = await fetchUrl(cal.icalUrl);
          const evs = parseIcsEvents(icsText);
          return evs.map(e => ({
            ...e,
            calendarId: cal.id,
            calendarName: cal.name || 'カレンダー'
          }));
        })
      );

      const allEvents = [];
      results.forEach((r, idx) => {
        if (r.status === 'fulfilled') {
          allEvents.push(...r.value);
        } else {
          console.warn(`[Calendar] "${cals[idx].name}" の取得失敗:`, r.reason?.message);
        }
      });

      // 日付順ソート
      allEvents.sort((a, b) => (a.start && b.start ? a.start - b.start : 0));
      this.eventsCache = allEvents;
      this.lastFetched = new Date().toISOString();
      console.log(`[Calendar] 同期完了: 合計 ${allEvents.length} 件の予定を取得`);
      return allEvents;
    } catch (err) {
      console.error('[Calendar] 同期全体エラー:', err.message);
      return this.eventsCache;
    }
  }

  /**
   * 今日の予定一覧を取得
   */
  getTodayEvents() {
    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    const endOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);

    return this.eventsCache.filter(ev => {
      if (!ev.start) return false;
      return ev.start >= startOfDay && ev.start <= endOfDay;
    });
  }

  /**
   * 今後24時間の予定一覧を取得
   */
  getUpcomingEvents() {
    const now = new Date();
    const limit = new Date(now.getTime() + 24 * 60 * 60 * 1000);

    return this.eventsCache.filter(ev => {
      if (!ev.start) return false;
      return ev.start >= now && ev.start <= limit;
    });
  }

  /**
   * 1分ごとの定期処理 (カレンダーごとの個別設定に対応)
   */
  async tick() {
    const config = settingsManager.get().calendar;
    if (!config || !config.enabled) return;

    const now = new Date();
    const nowTime = now.getTime();
    const currentH = String(now.getHours()).padStart(2, '0');
    const currentM = String(now.getMinutes()).padStart(2, '0');
    const currentTimeStr = `${currentH}:${currentM}`;
    const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

    const cals = Array.isArray(config.calendars) ? config.calendars : [];
    const calMap = new Map();
    for (const c of cals) {
      if (c && c.id) calMap.set(c.id, c);
    }

    // 1. 直前リマインド判定 (カレンダー個別の設定に対応)
    if (this.executor) {
      for (const ev of this.eventsCache) {
        if (!ev.start || ev.isAllDay) continue;

        const cal = (ev.calendarId ? calMap.get(ev.calendarId) : null) || {};
        if (cal.enabled === false) continue;

        // リマインド有効フラグ (個別設定優先、未定義時は全体設定)
        const isRemindOn = cal.remindEnabled !== undefined ? !!cal.remindEnabled : (config.remindEnabled !== false);
        if (!isRemindOn) continue;

        const remindMinutes = parseInt(cal.remindMinutesBefore !== undefined ? cal.remindMinutesBefore : (config.remindMinutesBefore || '10'), 10);
        if (remindMinutes <= 0) continue;

        const diffMinutes = (ev.start.getTime() - nowTime) / (60 * 1000);
        if (diffMinutes >= remindMinutes - 0.5 && diffMinutes < remindMinutes + 0.5) {
          const reminderKey = `${ev.uid || ev.summary}_${ev.start.getTime()}_${remindMinutes}_remind`;
          if (!this.notifiedReminders.has(reminderKey)) {
            this.notifiedReminders.add(reminderKey);
            const timeStr = `${ev.start.getHours()}時${ev.start.getMinutes() === 0 ? '' : ev.start.getMinutes() + '分'}`;
            const message = `まもなく、${timeStr}から「${ev.summary}」の時間です。`;
            console.log(`[Calendar Reminder] (${cal.name || 'カレンダー'}) 発声: ${message}`);
            this.speakMessage(message, cal, config);
          }
        }
      }
    }

    // 2. 朝のデイリーサマリー判定 (カレンダー個別の放送時刻 & 有効フラグに対応)
    if (this.executor) {
      if (cals.length > 0) {
        for (const cal of cals) {
          if (cal.enabled === false) continue;
          const isDailyOn = cal.dailySummaryEnabled !== undefined ? !!cal.dailySummaryEnabled : !!config.dailySummaryEnabled;
          const summaryTime = cal.dailySummaryTime || config.dailySummaryTime || '07:30';
          const sumKey = `${cal.id}_${todayStr}`;

          if (isDailyOn && summaryTime === currentTimeStr && !this.notifiedSummaries.has(sumKey)) {
            this.notifiedSummaries.add(sumKey);
            console.log(`[Calendar Daily Summary] カレンダー「${cal.name || 'カレンダー'}」の朝の予定まとめ読み上げ実行 (${currentTimeStr})`);
            await this.speakDailySummaryForCalendar(cal, config);
          }
        }
      } else if (config.dailySummaryEnabled && config.dailySummaryTime === currentTimeStr && this.lastDailySummaryDate !== todayStr) {
        this.lastDailySummaryDate = todayStr;
        console.log(`[Calendar Daily Summary] 朝の予定まとめ読み上げ実行 (${currentTimeStr})`);
        await this.speakDailySummary(config);
      }
    }

    // 古い通知済みフラグの整理
    if (this.notifiedReminders.size > 300) {
      this.notifiedReminders.clear();
    }
    if (this.notifiedSummaries.size > 100) {
      this.notifiedSummaries.clear();
    }
  }

  /**
   * 特定カレンダーの予定サマリー発声
   */
  async speakDailySummaryForCalendar(cal, globalConfig = {}) {
    const todayEvents = this.getTodayEvents().filter(ev => ev.calendarId === cal.id);
    let message = '';
    const calLabel = cal.name ? `${cal.name}の` : '';

    if (todayEvents.length === 0) {
      message = `おはようございます。${calLabel}本日の予定は登録されていません。良い一日を！`;
    } else {
      message = `おはようございます。${calLabel}本日の予定は ${todayEvents.length} 件あります。`;
      for (const ev of todayEvents) {
        if (ev.isAllDay) {
          message += ` 終日、${ev.summary}。`;
        } else {
          const h = ev.start.getHours();
          const m = ev.start.getMinutes();
          const timeStr = `${h}時${m === 0 ? '' : m + '分'}`;
          message += ` ${timeStr}から、${ev.summary}。`;
        }
      }
      message += ' 今日も一日がんばりましょう！';
    }

    return await this.speakMessage(message, cal, globalConfig);
  }

  /**
   * 全体本日の予定サマリー発声 (テスト・手動実行・互換用)
   */
  async speakDailySummary(configOverride = null) {
    const config = configOverride || settingsManager.get().calendar;
    // 最新を取得
    await this.syncEvents();
    const todayEvents = this.getTodayEvents();

    let message = '';
    if (todayEvents.length === 0) {
      message = 'おはようございます。本日の予定は登録されていません。良い一日を！';
    } else {
      message = `おはようございます。本日の予定は ${todayEvents.length} 件あります。`;
      for (const ev of todayEvents) {
        if (ev.isAllDay) {
          message += ` 終日、${ev.summary}。`;
        } else {
          const h = ev.start.getHours();
          const m = ev.start.getMinutes();
          const timeStr = `${h}時${m === 0 ? '' : m + '分'}`;
          message += ` ${timeStr}から、${ev.summary}。`;
        }
      }
      message += ' 今日も一日がんばりましょう！';
    }

    return await this.speakMessage(message, {}, config);
  }

  /**
   * メッセージをターゲットスピーカーへ発声 (個別設定を最優先、全体設定へフォールバック)
   */
  async speakMessage(text, calConfig = {}, globalConfig = {}) {
    if (!this.executor) return null;

    // スピーカーの決定 (カレンダー個別 > 全体設定 > デフォルト)
    let targets = calConfig.targetDevices;
    if (!Array.isArray(targets) || targets.length === 0) {
      targets = globalConfig.targetDevices || ['default'];
    }

    // 音声オプションの決定
    const voice = calConfig.voice || globalConfig.voice || 'ja-JP-NanamiNeural';
    const rate = calConfig.rate || globalConfig.rate || '+0%';
    const pitch = calConfig.pitch || globalConfig.pitch || '+0Hz';
    const volStr = calConfig.volumeLevel !== undefined && calConfig.volumeLevel !== '' ? calConfig.volumeLevel : globalConfig.volumeLevel;
    const volumeLevel = volStr ? parseFloat(volStr) : undefined;

    return await this.executor(text, {
      deviceIps: targets.map(d => (d === 'default' ? undefined : d)).filter(Boolean),
      voice,
      rate,
      pitch,
      volumeLevel
    });
  }
}

module.exports = new CalendarManager();
