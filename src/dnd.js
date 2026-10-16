const fs = require('fs');
const path = require('path');
const settingsManager = require('./settings');
const calendarManager = require('./calendar');
const aiManager = require('./ai');

const DATA_DIR = path.resolve(__dirname, '../data');
const DND_QUEUE_FILE = path.join(DATA_DIR, 'dnd_queue.json');

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

class DndManager {
  constructor() {
    this.history = []; // 直近50件のDND履歴 [{ id, timestamp, text, target, reason, action }]
    this.queue = [];   // 保留キュー [{ id, text, options, target, timestamp, reason }]
    this.wasDndActive = false;
    this.speakerExecutor = null; // server.js からインジェクト

    // 保存されていた保留キューを復元
    this.loadQueue();

    // 1分ごとにDND終了検知 & キュー処理
    setInterval(() => this.tick(), 60 * 1000).unref();
  }

  loadQueue() {
    try {
      if (fs.existsSync(DND_QUEUE_FILE)) {
        const raw = fs.readFileSync(DND_QUEUE_FILE, 'utf8');
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          const now = Date.now();
          // 24時間以内の有効な保留項目のみを復元
          this.queue = parsed.filter(item => {
            if (!item || !item.text) return false;
            const ts = item.timestamp ? new Date(item.timestamp).getTime() : 0;
            return (now - ts) < 24 * 60 * 60 * 1000;
          });
          if (this.queue.length > 0) {
            console.log(`[DND] 保存されていた保留キュー ${this.queue.length} 件をファイルから復元しました`);
          }
        }
      }
    } catch (err) {
      console.warn('[DND] 保留キュー読み込みエラー:', err.message);
      this.queue = [];
    }
  }

  saveQueue() {
    try {
      fs.writeFileSync(DND_QUEUE_FILE, JSON.stringify(this.queue, null, 2), 'utf8');
    } catch (err) {
      console.error('[DND] 保留キュー保存エラー:', err.message);
    }
  }

  setSpeakerExecutor(fn) {
    this.speakerExecutor = fn;
  }

  /**
   * サーバー起動時・再起動時の保留キュー確認と自動消化
   */
  checkStartupQueue() {
    if (this.queue.length === 0 || !this.speakerExecutor) return;
    const status = this.getGlobalStatus();
    if (!status.isActive) {
      console.log(`[DND] 起動時復元: サイレントが終了しているため、保留されていた ${this.queue.length} 件の通知を5秒後に再生します`);
      setTimeout(() => {
        this.checkAndFlushQueue();
      }, 5000);
    } else {
      console.log(`[DND] 起動時復元: 現在もサイレント中 (${status.reason}) のため保留キュー (${this.queue.length}件) を保持します`);
    }
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

    // 2. 対象スピーカーのスコープ判定 (全体ステータス問い合わせ dummy_check や global の場合はスキップ)
    const isGlobalQuery = !targetDeviceId || targetDeviceId === 'dummy_check' || targetDeviceId === 'global' || targetDeviceId === 'all';
    if (!isGlobalQuery && dndConfig.targetScope === 'specific' && Array.isArray(dndConfig.targetDevices) && dndConfig.targetDevices.length > 0) {
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
      if (dndConfig.manualUntil === 'indefinite') {
        return {
          isDnd: true,
          reason: dndConfig.manualReason || '手動サイレント (手動解除まで)',
          until: 'indefinite',
          action,
          whisperVolume
        };
      }
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

    // 3.5. 手動アンミュートによる一時解除オーバーライド (カレンダーや定時DNDも一時解除)
    if (dndConfig.manualUnmutedUntil) {
      const unmutedDate = new Date(dndConfig.manualUnmutedUntil);
      if (unmutedDate.getTime() > now.getTime()) {
        return { isDnd: false, reason: '手動アンミュート中' };
      } else {
        dndConfig.manualUnmutedUntil = null;
        settingsManager.update({ dnd: { manualUnmutedUntil: null } });
      }
    }

    // 4. カレンダー進行中予定連動 DND
    if (dndConfig.calendarEnabled && Array.isArray(calendarManager.eventsCache)) {
      const isAllMode = dndConfig.calendarMode === 'all';
      const includeAllDay = !!dndConfig.calendarIncludeAllDay;
      const keywords = (dndConfig.calendarKeywords || '')
        .split(',')
        .map(k => k.trim().toLowerCase())
        .filter(Boolean);

      const ongoingEvent = calendarManager.eventsCache.find(ev => {
        if (ev.isAllDay) {
          if (!includeAllDay || !ev.start) return false;
          const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
          const todayEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);
          const evStart = new Date(ev.start);
          const evEnd = ev.end ? new Date(ev.end) : new Date(evStart.getTime() + 24 * 60 * 60 * 1000);
          if (todayEnd < evStart || todayStart >= evEnd) return false;
        } else {
          if (!ev.start || !ev.end) return false;
          if (ev.start > now || now >= ev.end) return false;
        }

        if (isAllMode) return true;
        if (keywords.length === 0) return true;

        const summary = (ev.summary || '').toLowerCase();
        const desc = (ev.description || '').toLowerCase();
        return keywords.some(k => summary.includes(k) || desc.includes(k));
      });

      if (ongoingEvent) {
        return {
          isDnd: true,
          reason: `カレンダー予定中: ${ongoingEvent.summary || '予定あり'}${ongoingEvent.isAllDay ? ' (終日)' : ''}`,
          until: ongoingEvent.isAllDay ? undefined : (ongoingEvent.end ? ongoingEvent.end.toISOString() : undefined),
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
      const isAllMode = dndConfig.calendarMode === 'all';
      const includeAllDay = !!dndConfig.calendarIncludeAllDay;
      const keywords = (dndConfig.calendarKeywords || '')
        .split(',')
        .map(k => k.trim().toLowerCase())
        .filter(Boolean);

      const found = calendarManager.eventsCache.find(ev => {
        if (ev.isAllDay) {
          if (!includeAllDay || !ev.start) return false;
          const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
          const todayEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);
          const evStart = new Date(ev.start);
          const evEnd = ev.end ? new Date(ev.end) : new Date(evStart.getTime() + 24 * 60 * 60 * 1000);
          if (todayEnd < evStart || todayStart >= evEnd) return false;
        } else {
          if (!ev.start || !ev.end) return false;
          if (ev.start > now || now >= ev.end) return false;
        }

        if (isAllMode) return true;
        if (keywords.length === 0) return true;

        const summary = (ev.summary || '').toLowerCase();
        return keywords.some(k => summary.includes(k));
      });
      if (found) {
        activeCalendarEvent = {
          summary: found.summary,
          start: found.start,
          end: found.end,
          isAllDay: found.isAllDay
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
    if (minutes === 0 || (typeof minutes === 'number' && minutes === 0)) {
      // 60分間のアンミュートオーバーライドを設定（カレンダーや定時サイレントも確実に解除）
      const unmutedUntil = new Date(Date.now() + 60 * 60 * 1000).toISOString();
      settingsManager.update({
        dnd: {
          manualUntil: null,
          manualReason: '',
          manualUnmutedUntil: unmutedUntil
        }
      });
      console.log('[DND] 手動サイレントを解除 (アンミュート) しました');
      this.checkAndFlushQueue();
      return { success: true, active: false };
    }

    if (minutes === 'indefinite' || minutes === -1 || minutes === '-1') {
      settingsManager.update({
        dnd: {
          manualUntil: 'indefinite',
          manualReason: reason || '手動サイレント (手動解除まで)',
          manualUnmutedUntil: null
        }
      });
      console.log('[DND] 手動サイレントを「手動解除までずっと」有効化しました');
      return { success: true, active: true, until: 'indefinite' };
    }

    const minsNum = parseInt(minutes, 10) || 30;
    const until = new Date(Date.now() + minsNum * 60 * 1000).toISOString();
    settingsManager.update({
      dnd: {
        manualUntil: until,
        manualReason: reason,
        manualUnmutedUntil: null
      }
    });
    console.log(`[DND] 手動サイレントを ${minsNum} 分間有効化しました (解除予定: ${until})`);
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
      id: 'queue_' + Date.now() + '_' + Math.random().toString(36).substr(2, 4),
      timestamp: new Date().toISOString(),
      ...item
    });
    this.saveQueue();
    console.log(`[DND] 発話を保留キューに追加・永続化しました (現在 ${this.queue.length} 件): "${item.text.slice(0, 30)}..."`);
  }

  getQueue() {
    return this.queue;
  }

  clearQueue() {
    this.queue = [];
    this.saveQueue();
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
   * キューに溜まっている発話を順次再生 (前の通知が完全に再生終了するまで待機)
   */
  async checkAndFlushQueue() {
    if (this.queue.length === 0 || !this.speakerExecutor) return;

    const items = [...this.queue];
    this.queue = [];
    this.saveQueue();

    console.log(`[DND] 保留されていた ${items.length} 件の通知の再生処理を開始します`);

    const dndConfig = settingsManager.get().dnd || {};
    const aiConfig = settingsManager.get().ai || {};
    const aiSummaryEnabled = dndConfig.aiSummaryEnabled !== false && aiConfig.summarizeDndQueue !== false && aiManager.isAvailable();
    const threshold = parseInt(dndConfig.aiSummaryThreshold || aiConfig.summaryThreshold || '2', 10);

    // AI要約条件を満たした場合 (指定件数以上たまった時)
    if (aiSummaryEnabled && items.length >= threshold) {
      try {
        console.log(`[DND] 保留通知 ${items.length} 件を AI (${aiConfig.provider || 'Gemini'}) で要約します...`);
        const summary = await aiManager.summarizeNotifications(items, {
          promptHint: dndConfig.aiSummaryCustomPrompt || aiConfig.customPrompt
        });

        if (summary && summary.trim().length > 0) {
          const firstTargets = items[0].targetDevices || (items[0].targetDevice ? [items[0].targetDevice] : []);
          const announceText = `会議・おやすみモードが終了しました。保留されていた ${items.length} 件の通知をAIが要約してお知らせします。${summary.trim()}`;
          console.log(`[DND] AI要約アナウンスを再生: "${announceText}"`);

          const announceRes = await this.speakerExecutor({
            text: announceText,
            targetDevices: firstTargets,
            options: {
              source: 'dnd_ai_summary',
              sourceLabel: 'DND保留通知 (AI要約)',
              clientName: 'AIアシスタント'
            }
          });

          const announceDuration = (announceRes?.duration && announceRes.duration > 0)
            ? announceRes.duration
            : Math.max(5.0, (announceText.length / 4.8) + 2.0);
          const waitMs = Math.ceil((announceDuration + 1.5) * 1000);
          await new Promise(r => setTimeout(r, waitMs));
          console.log('[DND] AI要約アナウンスの再生が完了しました');
          return;
        }
      } catch (aiErr) {
        console.warn('[DND] AI要約に失敗したため、通常の個別読み上げにフォールバックします:', aiErr.message);
      }
    }

    // 冒頭アナウンス
    try {
      const firstTargets = items[0].targetDevices || (items[0].targetDevice ? [items[0].targetDevice] : []);
      const announceText = `会議・おやすみモードが終了しました。保留されていた通知が ${items.length} 件あります。`;
      const announceRes = await this.speakerExecutor({
        text: announceText,
        targetDevices: firstTargets,
        options: {
          source: 'dnd_queue',
          sourceLabel: 'DND保留アナウンス',
          clientName: 'DNDシステム'
        }
      });
      // 冒頭アナウンスの実際の音声秒数 (または文字数推定) + 1.5秒の余白を確実に待機！
      const announceDuration = (announceRes?.duration && announceRes.duration > 0)
        ? announceRes.duration
        : Math.max(4.5, (announceText.length / 4.8) + 2.0);
      const waitMs = Math.ceil((announceDuration + 1.5) * 1000);
      console.log(`[DND] 冒頭アナウンス再生中... (${(announceDuration).toFixed(1)}秒 + 1.5秒待機)`);
      await new Promise(r => setTimeout(r, waitMs));
    } catch (e) {
      console.warn('[DND] 冒頭アナウンス失敗:', e.message);
    }

    // 各アイテムを順番に再生（前の音声が完全に終わりきるまで待つ）
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      try {
        console.log(`[DND] 保留通知 [${i + 1}/${items.length}] 再生中: "${String(item.text).slice(0, 30)}..."`);
        const itemRes = await this.speakerExecutor(item);

        // 音声の実際の秒数 (または文字数推定) + 1.8秒のインターバルを確実に待機！
        const itemDuration = (itemRes?.duration && itemRes.duration > 0)
          ? itemRes.duration
          : Math.max(3.0, (String(item.text).length / 4.8) + 2.5);
        const waitMs = Math.ceil((itemDuration + 1.8) * 1000);
        console.log(`[DND] 通知 [${i + 1}/${items.length}] 再生待機中... (${(itemDuration).toFixed(1)}秒 + 1.8秒間隔)`);
        await new Promise(r => setTimeout(r, waitMs));
      } catch (err) {
        console.error(`[DND] 保留通知 [${i + 1}/${items.length}] 再生エラー:`, err.message);
        await new Promise(r => setTimeout(r, 2000));
      }
    }
    console.log('[DND] 保留キューの全件再生が完了しました');
  }
}

module.exports = new DndManager();
