const fs = require('fs');
const path = require('path');
const cron = require('node-cron');

const DATA_DIR = path.resolve(__dirname, '../data');
const SCHEDULE_FILE = path.join(DATA_DIR, 'schedules.json');

// データディレクトリの作成
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// サンプルの初期スケジュール（ファイルが空の時用）
const INITIAL_SCHEDULES = [
  {
    id: 'sample_morning',
    name: '毎朝のおはようアナウンス',
    enabled: false,
    cron: '0 7 * * *',
    description: '毎朝 7:00 にアナウンス',
    text: 'おはようございます。今日も一日がんばりましょう！',
    deviceIp: 'default',
    voice: 'ja-JP-NanamiNeural',
    createdAt: new Date().toISOString()
  },
  {
    id: 'sample_garbage',
    name: 'ゴミ出しリマインダー (火・金)',
    enabled: false,
    cron: '30 7 * * 2,5',
    description: '毎週火・金 7:30 にアナウンス',
    text: 'おはようございます。今日はゴミ出しの日です。準備を忘れずに！',
    deviceIp: 'default',
    voice: 'ja-JP-KeitaNeural',
    createdAt: new Date().toISOString()
  }
];

class SchedulerManager {
  constructor() {
    this.schedules = [];
    this.cronTasks = new Map();
    this.history = [];
    this.executor = null; // (text, options) => Promise<any>

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
    // 既存の cron タスクをすべて停止
    for (const [id, task] of this.cronTasks.entries()) {
      task.stop();
    }
    this.cronTasks.clear();

    if (!this.executor) return;

    // 有効なスケジュールを登録
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

          try {
            if (this.executor) {
              await this.executor(sched.text, {
                deviceIp: sched.deviceIp === 'default' ? undefined : sched.deviceIp,
                voice: sched.voice
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
    if (this.history.length > 50) {
      this.history.pop();
    }
  }

  getSchedules() {
    return this.schedules;
  }

  getHistory() {
    return this.history;
  }

  addSchedule(data) {
    if (!data.name || !data.text || !data.cron) {
      throw new Error('スケジュール名、テキスト、cron式は必須です');
    }
    if (!cron.validate(data.cron)) {
      throw new Error('無効な cron 式です');
    }

    const newSched = {
      id: `sched_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
      name: data.name,
      description: data.description || '',
      enabled: data.enabled !== false,
      cron: data.cron,
      text: data.text,
      deviceIp: data.deviceIp || 'default',
      voice: data.voice || 'ja-JP-NanamiNeural',
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

    if (updates.cron && !cron.validate(updates.cron)) {
      throw new Error('無効な cron 式です');
    }

    const updated = {
      ...this.schedules[index],
      ...updates,
      id // idは不変
    };

    this.schedules[index] = updated;
    this.saveSchedules();

    // cron再登録
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
    return await this.executor(sched.text, {
      deviceIp: sched.deviceIp === 'default' ? undefined : sched.deviceIp,
      voice: sched.voice
    });
  }
}

module.exports = new SchedulerManager();
