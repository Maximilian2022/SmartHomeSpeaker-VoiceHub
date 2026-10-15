const fs = require('fs');
const path = require('path');
const cron = require('node-cron');

const DATA_DIR = path.resolve(__dirname, '../data');
const SCHEDULE_FILE = path.join(DATA_DIR, 'schedules.json');

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// 曜日番号から日本語へのマップ
const WEEKDAY_NAMES = ['日', '月', '火', '水', '木', '金', '土'];

/**
 * GUI設定から cron 式を生成
 */
function buildCronExpression({ frequency, time, weekdays }) {
  const [hourStr, minStr] = (time || '07:00').split(':');
  const minute = parseInt(minStr, 10) || 0;
  const hour = parseInt(hourStr, 10) || 7;

  switch (frequency) {
    case 'daily': // 毎日
      return `${minute} ${hour} * * *`;
    case 'weekdays': // 平日 (月〜金)
      return `${minute} ${hour} * * 1-5`;
    case 'weekends': // 土日
      return `${minute} ${hour} * * 0,6`;
    case 'custom_days': // 指定曜日
      const days = Array.isArray(weekdays) && weekdays.length ? weekdays.sort().join(',') : '*';
      return `${minute} ${hour} * * ${days}`;
    default:
      return `${minute} ${hour} * * *`;
  }
}

const WEEKDAY_NAMES_MAP = {
  '0': '日', '1': '月', '2': '火', '3': '水', '4': '木', '5': '金', '6': '土', '7': '日'
};

/**
 * 人間が読みやすいスケジュール表記を生成（cron式から自然な日本語を自動解析）
 */
function formatHumanReadable(sched) {
  // 1. frequency と time が指定されている場合
  if (sched.frequency && sched.time) {
    const time = sched.time;
    switch (sched.frequency) {
      case 'daily':
        return `毎日 ${time}`;
      case 'weekdays':
        return `平日 (月〜金) ${time}`;
      case 'weekends':
        return `土日 ${time}`;
      case 'custom_days':
        if (Array.isArray(sched.weekdays) && sched.weekdays.length) {
          const names = sched.weekdays.map(d => WEEKDAY_NAMES_MAP[d] || d).join('・');
          return `毎週 ${names} ${time}`;
        }
        return `指定曜日 ${time}`;
    }
  }

  // 2. cron 式から自然な日本語を自動解析
  const cron = (sched.cron || '').trim();
  if (cron) {
    const parts = cron.split(/\s+/);
    if (parts.length === 5) {
      const [m, h, dom, mon, dow] = parts;

      // 分と時が具体的な数値の場合 (例: 0 7, 30 7)
      if (/^\d+$/.test(m) && /^\d+$/.test(h)) {
        const timeStr = `${h.padStart(2, '0')}:${m.padStart(2, '0')}`;

        if (dom === '*' && mon === '*') {
          if (dow === '*') {
            return `毎日 ${timeStr}`;
          }
          if (dow === '1-5' || dow === '1,2,3,4,5') {
            return `平日 (月〜金) ${timeStr}`;
          }
          if (dow === '0,6' || dow === '6,0') {
            return `土日 ${timeStr}`;
          }
          // 指定曜日 (例: 2,5 や 1,3,5)
          const days = dow.split(',').map(d => WEEKDAY_NAMES_MAP[d.trim()] || d).filter(Boolean);
          if (days.length) {
            return `毎週 ${days.join('・')} ${timeStr}`;
          }
        }
      }

      // 毎時・間隔指定の解析
      if (m.startsWith('*/') && h === '*' && dom === '*' && mon === '*' && dow === '*') {
        return `${m.slice(2)}分ごと`;
      }
      if (m === '0' && h === '*' && dom === '*' && mon === '*' && dow === '*') {
        return `毎時 00分`;
      }
    }
    return cron;
  }

  return sched.time || '未設定';
}

// 初期サンプルスケジュール
const INITIAL_SCHEDULES = [
  {
    id: 'sample_morning',
    name: '毎朝のおはようアナウンス',
    enabled: false,
    frequency: 'daily',
    time: '07:00',
    cron: '0 7 * * *',
    readableFrequency: '毎日 07:00',
    text: 'おはようございます。今日も一日がんばりましょう！',
    deviceIps: ['default'],
    voice: 'ja-JP-NanamiNeural',
    createdAt: new Date().toISOString()
  },
  {
    id: 'sample_garbage',
    name: 'ゴミ出しリマインダー (火・金)',
    enabled: false,
    frequency: 'custom_days',
    weekdays: [2, 5],
    time: '07:30',
    cron: '30 7 * * 2,5',
    readableFrequency: '毎週 火・金曜日 07:30',
    text: 'おはようございます。今日はゴミ出しの日です。準備を忘れずに！',
    deviceIps: ['default'],
    voice: 'ja-JP-KeitaNeural',
    createdAt: new Date().toISOString()
  }
];

class SchedulerManager {
  constructor() {
    this.schedules = [];
    this.cronTasks = new Map();
    this.history = [];
    this.executor = null;

    this.loadSchedules();
  }

  setExecutor(fn) {
    this.executor = fn;
    this.rescheduleAll();
  }

  loadSchedules() {
    try {
      if (fs.existsSync(SCHEDULE_FILE)) {
        const raw = fs.readFileSync(SCHEDULE_FILE, 'utf8');
        this.schedules = JSON.parse(raw);
        // 既存データの正規化
        this.schedules.forEach(s => {
          if (!s.deviceIps && s.deviceIp) s.deviceIps = [s.deviceIp];
          if (!s.readableFrequency) s.readableFrequency = formatHumanReadable(s);
        });
      } else {
        this.schedules = INITIAL_SCHEDULES;
        this.saveSchedules();
      }
    } catch (err) {
      console.error('スケジュール読み込み失敗:', err.message);
      this.schedules = INITIAL_SCHEDULES;
    }
  }

  saveSchedules() {
    try {
      fs.writeFileSync(SCHEDULE_FILE, JSON.stringify(this.schedules, null, 2), 'utf8');
    } catch (err) {
      console.error('スケジュール保存失敗:', err.message);
    }
  }

  rescheduleAll() {
    for (const [id, task] of this.cronTasks.entries()) {
      task.stop();
    }
    this.cronTasks.clear();

    if (!this.executor) return;

    for (const sched of this.schedules) {
      if (sched.enabled && cron.validate(sched.cron)) {
        this.startCronTask(sched);
      }
    }
  }

  startCronTask(sched) {
    if (this.cronTasks.has(sched.id)) {
      this.cronTasks.get(sched.id).stop();
    }

    try {
      const task = cron.schedule(
        sched.cron,
        async () => {
          console.log(`[Scheduler] 実行中: "${sched.name}" (${sched.text})`);
          sched.lastRun = new Date().toISOString();
          this.saveSchedules();

          const targets = sched.deviceIps || (sched.deviceIp ? [sched.deviceIp] : ['default']);

          try {
            if (this.executor) {
              const volStr = sched.volumeLevel !== undefined && sched.volumeLevel !== '' ? sched.volumeLevel : undefined;
              const volumeLevel = volStr ? parseFloat(volStr) : undefined;
              await this.executor(sched.text, {
                deviceIps: targets.map(d => (d === 'default' ? undefined : d)).filter(Boolean),
                voice: sched.voice,
                rate: sched.rate,
                pitch: sched.pitch,
                volumeLevel,
                source: 'schedule',
                sourceLabel: `スケジュール (${sched.name})`
              });
            }
            this.addHistory({
              scheduleId: sched.id,
              name: sched.name,
              text: sched.text,
              status: 'success',
              timestamp: new Date().toISOString()
            });
          } catch (err) {
            console.error(`[Scheduler] 実行失敗 "${sched.name}":`, err.message);
            this.addHistory({
              scheduleId: sched.id,
              name: sched.name,
              text: sched.text,
              status: 'error',
              error: err.message,
              timestamp: new Date().toISOString()
            });
          }
        },
        {
          timezone: process.env.TZ || 'Asia/Tokyo'
        }
      );

      this.cronTasks.set(sched.id, task);
    } catch (err) {
      console.error(`Cron スケジュール登録失敗 "${sched.name}":`, err.message);
    }
  }

  addHistory(item) {
    this.history.unshift(item);
    if (this.history.length > 50) this.history.pop();
  }

  getSchedules() {
    return this.schedules.map(s => ({
      ...s,
      readableFrequency: formatHumanReadable(s)
    }));
  }

  getHistory() {
    return this.history;
  }

  addSchedule(data) {
    if (!data.name || !data.text) {
      throw new Error('スケジュール名と発言メッセージは必須です');
    }

    // cron 式の決定 (直接cronが渡された場合はそれを使用、なければGUI設定から生成)
    let cronExpr = data.cron;
    if (!cronExpr) {
      cronExpr = buildCronExpression({
        frequency: data.frequency || 'daily',
        time: data.time || '07:00',
        weekdays: data.weekdays || []
      });
    }

    if (!cron.validate(cronExpr)) {
      throw new Error('無効なスケジュール設定です');
    }

    // 複数デバイス対応
    let deviceIps = data.deviceIps;
    if (!deviceIps && data.deviceIp) deviceIps = [data.deviceIp];
    if (!deviceIps || !deviceIps.length) deviceIps = ['default'];

    const newSched = {
      id: `sched_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
      name: data.name,
      enabled: data.enabled !== false,
      frequency: data.frequency || 'daily',
      time: data.time || '07:00',
      weekdays: data.weekdays || [],
      cron: cronExpr,
      readableFrequency: formatHumanReadable({
        frequency: data.frequency || 'daily',
        time: data.time || '07:00',
        weekdays: data.weekdays || []
      }),
      text: data.text,
      deviceIps,
      voice: data.voice || 'ja-JP-NanamiNeural',
      rate: data.rate || '+0%',
      pitch: data.pitch || '+0Hz',
      volumeLevel: (data.volumeLevel !== undefined && data.volumeLevel !== '') ? String(data.volumeLevel) : undefined,
      createdAt: new Date().toISOString()
    };

    this.schedules.push(newSched);
    this.saveSchedules();

    if (newSched.enabled) {
      this.startCronTask(newSched);
    }
    return newSched;
  }

  updateSchedule(id, updates) {
    const index = this.schedules.findIndex(s => s.id === id);
    if (index === -1) {
      throw new Error('指定されたスケジュールが見つかりません');
    }

    let cronExpr = updates.cron;
    if (!cronExpr && (updates.frequency || updates.time || updates.weekdays)) {
      cronExpr = buildCronExpression({
        frequency: updates.frequency || this.schedules[index].frequency || 'daily',
        time: updates.time || this.schedules[index].time || '07:00',
        weekdays: updates.weekdays !== undefined ? updates.weekdays : this.schedules[index].weekdays
      });
    }

    if (cronExpr && !cron.validate(cronExpr)) {
      throw new Error('無効なスケジュール設定です');
    }

    const updated = {
      ...this.schedules[index],
      ...updates,
      id
    };

    if (updates.volumeLevel !== undefined) {
      updated.volumeLevel = updates.volumeLevel !== '' ? String(updates.volumeLevel) : undefined;
    }

    if (cronExpr) updated.cron = cronExpr;
    updated.readableFrequency = formatHumanReadable(updated);

    this.schedules[index] = updated;
    this.saveSchedules();

    if (this.cronTasks.has(id)) {
      this.cronTasks.get(id).stop();
      this.cronTasks.delete(id);
    }
    if (updated.enabled) {
      this.startCronTask(updated);
    }

    return updated;
  }

  deleteSchedule(id) {
    const index = this.schedules.findIndex(s => s.id === id);
    if (index === -1) {
      throw new Error('指定されたスケジュールが見つかりません');
    }

    if (this.cronTasks.has(id)) {
      this.cronTasks.get(id).stop();
      this.cronTasks.delete(id);
    }

    const removed = this.schedules.splice(index, 1)[0];
    this.saveSchedules();
    return removed;
  }

  toggleSchedule(id) {
    const sched = this.schedules.find(s => s.id === id);
    if (!sched) throw new Error('指定されたスケジュールが見つかりません');
    return this.updateSchedule(id, { enabled: !sched.enabled });
  }

  async runScheduleNow(id) {
    const sched = this.schedules.find(s => s.id === id);
    if (!sched) throw new Error('指定されたスケジュールが見つかりません');

    if (!this.executor) throw new Error('実行エンジンが初期化されていません');
    const targets = sched.deviceIps || (sched.deviceIp ? [sched.deviceIp] : ['default']);

    const volStr = sched.volumeLevel !== undefined && sched.volumeLevel !== '' ? sched.volumeLevel : undefined;
    const volumeLevel = volStr ? parseFloat(volStr) : undefined;

    return await this.executor(sched.text, {
      deviceIps: targets.map(d => (d === 'default' ? undefined : d)).filter(Boolean),
      voice: sched.voice,
      rate: sched.rate,
      pitch: sched.pitch,
      volumeLevel,
      source: 'schedule',
      sourceLabel: `スケジュール (${sched.name} テスト)`
    });
  }
}

module.exports = new SchedulerManager();
