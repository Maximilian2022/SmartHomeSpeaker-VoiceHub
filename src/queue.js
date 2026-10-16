const fs = require('fs');
const path = require('path');

const DATA_DIR = path.resolve(__dirname, '../data');
const PENDING_WEBHOOKS_FILE = path.join(DATA_DIR, 'pending_webhooks.json');

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

/**
 * 通常時および不慮のダウン・再起動に備えた永続化 Webhook 再生キューマネージャー
 * - Webhook 受信時に即時ディスク保存 (WAL: Write-Ahead Log)
 * - 複数 Webhook の同時衝突・音声切断を防止する順次再生
 * - サーバー再起動やクラッシュ時に未再生 Webhook を自動復旧・再生
 */
class WebhookQueueManager {
  constructor() {
    this.queue = [];
    this.isProcessing = false;
    this.executor = null;
    this.load();
  }

  load() {
    try {
      if (fs.existsSync(PENDING_WEBHOOKS_FILE)) {
        const raw = fs.readFileSync(PENDING_WEBHOOKS_FILE, 'utf8');
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          const now = Date.now();
          const valid = [];
          for (const item of parsed) {
            if (!item || !item.text) continue;
            const ts = item.receivedAt ? new Date(item.receivedAt).getTime() : 0;
            // 24時間以内の未処理項目のみを保持
            if (now - ts < 24 * 60 * 60 * 1000) {
              valid.push(item);
            } else {
              console.log(`[WebhookQueue] 24時間以上経過した古い未再生Webhookを破棄しました: "${String(item.text).slice(0, 30)}..."`);
            }
          }
          this.queue = valid;
          if (this.queue.length > 0) {
            console.log(`[WebhookQueue] 前回のセッションで未処理だった Webhook ${this.queue.length} 件を復元しました`);
          }
        }
      }
    } catch (err) {
      console.warn('[WebhookQueue] 保留Webhookの読み込みエラー:', err.message);
      this.queue = [];
    }
  }

  save() {
    try {
      fs.writeFileSync(PENDING_WEBHOOKS_FILE, JSON.stringify(this.queue, null, 2), 'utf8');
    } catch (err) {
      console.error('[WebhookQueue] 保留Webhookの保存エラー:', err.message);
    }
  }

  setExecutor(fn) {
    this.executor = fn;
    // 起動時に復元された未処理項目があれば、5秒後に順次再生を開始
    if (this.queue.length > 0) {
      console.log(`[WebhookQueue] 起動時復旧: 復元された ${this.queue.length} 件の未再生Webhookを5秒後に再生再開します`);
      setTimeout(() => {
        this.processQueue();
      }, 5000);
    }
  }

  /**
   * Webhookリクエストをキューに追加して即時永続化
   * @param {{ text: string, targets: Array, options: Object }} item
   * @returns {string} jobId
   */
  enqueue(item) {
    const job = {
      id: 'wh_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5),
      text: item.text,
      targets: item.targets || [],
      options: item.options || {},
      receivedAt: new Date().toISOString(),
      retryCount: 0
    };

    this.queue.push(job);
    this.save();
    console.log(`[WebhookQueue] Webhookを永続化キューに追加しました (未処理: ${this.queue.length}件): "${String(item.text).slice(0, 30)}..."`);

    // ワーカーループをキック
    this.processQueue();
    return job.id;
  }

  /**
   * キューを順次処理 (1件ずつ前の音声が完全に再生完了するのを待機)
   */
  async processQueue() {
    if (this.isProcessing || !this.executor || this.queue.length === 0) {
      return;
    }

    this.isProcessing = true;

    try {
      while (this.queue.length > 0) {
        const currentJob = this.queue[0];
        console.log(`[WebhookQueue] 再生処理開始 (残り ${this.queue.length} 件): "${String(currentJob.text).slice(0, 30)}..."`);

        try {
          const res = await this.executor(currentJob.text, currentJob.targets, {
            ...(currentJob.options || {}),
            webhookJobId: currentJob.id
          });

          // 完了を待機 (実際の音声秒数または推定秒数 + 1.2秒のインターバル)
          let waitSec = 2.5;
          if (res?.duration && res.duration > 0) {
            waitSec = res.duration + 1.2;
          } else if (res?.queued) {
            // DNDキューに引き渡された場合は即座に次へ
            waitSec = 0.2;
          } else if (res?.dndSuppressed) {
            waitSec = 0.2;
          } else {
            waitSec = Math.max(2.5, (String(currentJob.text).length / 4.8) + 1.5);
          }

          if (waitSec > 0) {
            await new Promise(resolve => setTimeout(resolve, Math.ceil(waitSec * 1000)));
          }
        } catch (err) {
          console.error(`[WebhookQueue] Webhook [${currentJob.id}] 再生エラー:`, err.message);
          await new Promise(resolve => setTimeout(resolve, 2000));
        }

        // 処理完了した項目をキューから取り除いて即座にファイル更新
        this.queue.shift();
        this.save();
        console.log(`[WebhookQueue] Webhook [${currentJob.id}] の処理完了・永続化更新 (残り: ${this.queue.length}件)`);
      }
    } finally {
      this.isProcessing = false;
    }
  }

  getQueue() {
    return this.queue;
  }

  clearQueue() {
    this.queue = [];
    this.save();
    return true;
  }
}

module.exports = new WebhookQueueManager();
