const settingsManager = require('./settings');
const calendarManager = require('./calendar');

class DndManager {
  constructor() {
    this.history = []; // 直近50件のDND履歴 [{ id, timestamp, text, target, reason, action }]
    this.queue = [];   // 保留キュー [{ id, text, options, target, timestamp, reason }]
    this.wasDndActive = false;
    this.speakerExecutor = null; // server.js からインジェクト

    // 1分ごとにDND終了検知 & キュー処理
    setInterval(() => this.tick(), 60 * 1000).unref();
  }

  setSpeakerExecutor(fn) {
    this.speakerExecutor = fn;
  }

  /**
   * 現在時刻における DND 状態をチェック
   * @param {string} targetDeviceId スピーカー識別子
   * @param {Object} options urgent, bypassDnd など
   * @returns {{ isDnd: boolean, urgent?: boolean, reason?: string, action?: string, whisperVolume?: number, until?: string }}
   */
  checkDndStatus(targetDeviceId, options = {}) {
    // 1. 緊急バイパス判定 (urgent: true または bypassDnd: true)
    if (options.urgent || options.bypassDnd) {
      return { isDnd: false, urgent: true };
    }

    const dndConfig = settingsManager.get().dnd || {};
    if (!dndConfig.enabled) {
      return { isDnd: false };
    }

    // 2. 対象スピーカーのスコープ判定
    if (dndConfig.targetScope === 'specific' && Array.isArray(dndConfig.targetDevices) && dndConfig.targetDevices.length > 0) {
      const isTarget = dndConfig.targetDevices.includes(targetDeviceId) || 
                       dndConfig.targetDevices.includes('all');
      if (!isTarget) {
        return { isDnd: false, reason: '対象外スピーカー' };
      }
    }

    const now = new Date();
    const action = dndConfig.action || 'skip';
    const whisperVolume = parseInt(dndConfig.whisperVolume || '10', 10);

    // 3. ワンタップ即時 DND (手動設定)
    if (dndConfig.manualUntil) {
      const untilDate = new Date(dndConfig.manualUntil);
      if (untilDate.getTime() > now.getTime()) {
        return {
          isDnd: true,
          reason: dndConfig.manualReason || '手動サイレント (即時)',
          until: dndConfig.manualUntil,
          action,
          whisperVolume
        };
      } else {
        // 期限切れならクリア
        dndConfig.manualUntil = null;
        dndConfig.manualReason = '';
        settingsManager.update({ dnd: { manualUntil: null, manualReason: '' } });
      }
    }

    // 4. カレンダー進行中予定連動 DND
    if (dndConfig.calendarEnabled && Array.isArray(calendarManager.eventsCache)) {
      const keywords = (dndConfig.calendarKeywords || '')
        .split(',')
        .map(k => k.trim().toLowerCase())
        .filter(Boolean);

      const ongoingEvent = calendarManager.eventsCache.find(ev => {
        if (ev.isAllDay) return false; // 終日予定は除外
        if (!ev.start || !ev.end) return false;
        if (ev.start <= now && now < ev.end) {
          if (keywords.length === 0) return true;
          const summary = (ev.summary || '').toLowerCase();
          const desc = (ev.description || '').toLowerCase();
          return keywords.some(k => summary.includes(k) || desc.includes(k));
        }
        return false;
      });

      if (ongoingEvent) {
        return {
          isDnd: true,
          reason: `カレンダー予定中: ${ongoingEvent.summary || '予定あり'}`,
          until: ongoingEvent.end ? ongoingEvent.end.toISOString() : undefined,
          action,
          whisperVolume
        };
      }
    }

    // 5. 定時スケジュール DND (曜日 & 時間帯)
    if (dndConfig.scheduleEnabled && Array.isArray(dndConfig.schedules)) {
      const currentDay = String(now.getDay()); // '0' = 日曜, '1' = 月曜...
      const currentH = String(now.getHours()).padStart(2, '0');
      const currentM = String(now.getMinutes()).padStart(2, '0');
      const currentTimeStr = `${currentH}:${currentM}`;

      for (const sched of dndConfig.schedules) {
        if (!sched.enabled) continue;
        const days = Array.isArray(sched.days) ? sched.days : [];
        if (!days.includes(currentDay)) continue;

        const start = sched.startTime || '00:00';
        const end = sched.endTime || '23:59';

        let isMatch = false;
        if (start <= end) {
          // 同一日の範囲 (例: 09:00 〜 18:00)
          isMatch = (currentTimeStr >= start && currentTimeStr < end);
        } else {
          // 日跨ぎの範囲 (例: 23:00 〜 07:00)
          isMatch = (currentTimeStr >= start || currentTimeStr < end);
        }

        if (isMatch) {
          return {
            isDnd: true,
            reason: `定時サイレント: ${sched.name || '指定時間帯'}`,
            action,
            whisperVolume
          };
        }
      }
    }

    return { isDnd: false };
  }

  /**
   * 現在の全体 DND 状態を取得 (GUI 表示用)
   */
  getGlobalStatus() {
    const dndConfig = settingsManager.get().dnd || {};
    const check = this.checkDndStatus('dummy_check');
    const now = new Date();

    // 進行中のカレンダー予定があれば情報付与
    let activeCalendarEvent = null;
    if (Array.isArray(calendarManager.eventsCache)) {
      const keywords = (dndConfig.calendarKeywords || '')
        .split(',')
        .map(k => k.trim().toLowerCase())
        .filter(Boolean);

      const found = calendarManager.eventsCache.find(ev => {
        if (ev.isAllDay || !ev.start || !ev.end) return false;
        if (ev.start <= now && now < ev.end) {
          if (keywords.length === 0) return true;
          const summary = (ev.summary || '').toLowerCase();
          return keywords.some(k => summary.includes(k));
        }
        return false;
      });
      if (found) {
        activeCalendarEvent = {
          summary: found.summary,
          start: found.start,
          end: found.end
        };
      }
    }

    return {
      enabled: !!dndConfig.enabled,
      isActive: check.isDnd,
      reason: check.reason || null,
      until: check.until || null,
      action: dndConfig.action || 'skip',
      whisperVolume: dndConfig.whisperVolume || 10,
      activeCalendarEvent,
      queuedCount: this.queue.length
    };
  }

  /**
   * ワンタップ即時 DND の設定 / 解除
   * @param {number} minutes 分数 (0 で即時解除)
   * @param {string} reason 理由
   */
  setQuickDnd(minutes, reason = '手動サイレント') {
    if (!minutes || minutes <= 0) {
      settingsManager.update({
        dnd: {
          manualUntil: null,
          manualReason: ''
        }
      });
      console.log('[DND] 手動サイレントを解除しました');
      this.checkAndFlushQueue();
      return { success: true, active: false };
    }

    const until = new Date(Date.now() + minutes * 60 * 1000).toISOString();
    settingsManager.update({
      dnd: {
        manualUntil: until,
        manualReason: reason
      }
    });
    console.log(`[DND] 手動サイレントを ${minutes} 分間有効化しました (解除予定: ${until})`);
    return { success: true, active: true, until };
  }

  /**
   * ミュート履歴に記録
   */
  logEvent(item) {
    const entry = {
      id: 'dnd_log_' + Date.now() + '_' + Math.random().toString(36).substr(2, 4),
      timestamp: new Date().toISOString(),
      text: item.text || '',
      targetDevice: item.targetDevice || 'default',
      reason: item.reason || 'サイレント発動中',
      action: item.action || 'skip',
      handledAs: item.handledAs || 'スキップ'
    };

    this.history.unshift(entry);
    if (this.history.length > 50) {
      this.history.pop();
    }
  }

  getHistory() {
    return this.history;
  }

  clearHistory() {
    this.history = [];
    return true;
  }

  /**
   * 保留キューに追加 (action === 'queue')
   */
  enqueue(item) {
    this.queue.push({
      id: 'queue_' + Date.now(),
      timestamp: new Date().toISOString(),
      ...item
    });
    console.log(`[DND] 発話を保留キューに追加しました (現在 ${this.queue.length} 件): "${item.text.slice(0, 30)}..."`);
  }

  getQueue() {
    return this.queue;
  }

  clearQueue() {
    this.queue = [];
  }

  /**
   * 1分ごとの定期処理: 状態変化を監視し、DND終了時にキューを消化
   */
  tick() {
    const status = this.getGlobalStatus();
    if (this.wasDndActive && !status.isActive) {
      console.log('[DND] サイレント状態が終了しました。保留キューを確認します...');
      this.checkAndFlushQueue();
    }
    this.wasDndActive = status.isActive;
  }

  /**
   * キューに溜まっている発話を順次再生
   */
  async checkAndFlushQueue() {
    if (this.queue.length === 0 || !this.speakerExecutor) return;

    const items = [...this.queue];
    this.queue = [];

    console.log(`[DND] 保留されていた ${items.length} 件の通知を再生します`);

    // 冒頭アナウンス
    try {
      await this.speakerExecutor({
        text: `会議・おやすみモードが終了しました。保留されていた通知が ${items.length} 件あります。`,
        targetDevice: items[0].targetDevice
      });
      await new Promise(r => setTimeout(r, 1500));
    } catch (e) {}

    // 各アイテムを再生
    for (const item of items) {
      try {
        await this.speakerExecutor({
          text: item.text,
          targetDevice: item.targetDevice,
          options: item.options
        });
        await new Promise(r => setTimeout(r, 1200));
      } catch (err) {
        console.error('[DND] 保留通知の再生エラー:', err.message);
      }
    }
  }
}

module.exports = new DndManager();
