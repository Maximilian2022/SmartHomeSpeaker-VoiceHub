const fs = require('fs');
const path = require('path');

const DATA_DIR = path.resolve(__dirname, '../data');
const HISTORY_FILE = path.join(DATA_DIR, 'history.json');
const MAX_HISTORY_ENTRIES = 100;

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

class HistoryManager {
  constructor() {
    this.history = [];
    this.loadHistory();
  }

  loadHistory() {
    try {
      if (fs.existsSync(HISTORY_FILE)) {
        const raw = fs.readFileSync(HISTORY_FILE, 'utf8');
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          this.history = parsed.slice(0, MAX_HISTORY_ENTRIES);
        }
      }
    } catch (err) {
      console.warn('[History] 履歴読み込み失敗、初期化します:', err.message);
      this.history = [];
    }
  }

  saveHistory() {
    try {
      fs.writeFileSync(HISTORY_FILE, JSON.stringify(this.history, null, 2), 'utf8');
    } catch (err) {
      console.error('[History] 履歴保存エラー:', err.message);
    }
  }

  /**
   * 発話履歴に新規レコードを追加 (最大100件を保持)
   * @param {Object} entry
   */
  addEntry(entry) {
    if (!entry || !entry.text) return null;

    const id = `hist_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const timestamp = entry.timestamp || new Date().toISOString();

    const record = {
      id,
      timestamp,
      text: String(entry.text),
      source: entry.source || 'api',
      sourceLabel: entry.sourceLabel || this.deriveSourceLabel(entry.source),
      clientName: entry.clientName || '',
      clientIp: entry.clientIp || '',
      wasQueued: !!entry.wasQueued,
      targets: Array.isArray(entry.targets) ? entry.targets : (entry.targets ? [entry.targets] : ['デフォルト']),
      voice: entry.voice || 'ja-JP-NanamiNeural',
      rate: entry.rate || '0',
      pitch: entry.pitch || '0',
      volume: entry.volume || '',
      volumeLevel: entry.volumeLevel,
      status: entry.status || 'success', // 'success' | 'partial' | 'error' | 'suppressed'
      statusMessage: entry.statusMessage || '',
      urgent: !!entry.urgent,
      results: Array.isArray(entry.results) ? entry.results : []
    };

    this.history.unshift(record);

    if (this.history.length > MAX_HISTORY_ENTRIES) {
      this.history = this.history.slice(0, MAX_HISTORY_ENTRIES);
    }

    this.saveHistory();
    return record;
  }

  deriveSourceLabel(source) {
    switch (source) {
      case 'web_ui':
        return 'Web UI (即時発言)';
      case 'quick_test':
        return 'Web UI (テスト)';
      case 'schedule':
        return '定期スケジュール';
      case 'calendar':
        return 'カレンダー連携';
      case 'tunnel_webhook':
        return 'Cloudflare Tunnel (外部)';
      case 'dnd_queue':
        return 'DND保留再生';
      case 'api':
      default:
        return '外部 API / Webhook';
    }
  }

  getHistory(limit = MAX_HISTORY_ENTRIES) {
    const lim = Math.min(Math.max(1, parseInt(limit, 10) || MAX_HISTORY_ENTRIES), MAX_HISTORY_ENTRIES);
    return this.history.slice(0, lim);
  }

  getEntryById(id) {
    return this.history.find(h => h.id === id) || null;
  }

  clearHistory() {
    this.history = [];
    this.saveHistory();
    return true;
  }
}

module.exports = new HistoryManager();
