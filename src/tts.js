const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { EdgeTTS } = require('node-edge-tts');

const VOICE_DIR = path.resolve(__dirname, '../public/voice');

// フォルダが存在しない場合は作成
if (!fs.existsSync(VOICE_DIR)) {
  fs.mkdirSync(VOICE_DIR, { recursive: true });
}

// サポートする日本語ボイス
const SUPPORTED_VOICES = [
  { id: 'ja-JP-NanamiNeural', name: '七海 (Nanami) - 女性・標準', gender: 'Female' },
  { id: 'ja-JP-KeitaNeural', name: '圭太 (Keita) - 男性・標準', gender: 'Male' },
  { id: 'ja-JP-AoiNeural', name: '碧 (Aoi) - 女性・落ち着いた声', gender: 'Female' },
  { id: 'ja-JP-DaichiNeural', name: '大地 (Daichi) - 男性・落ち着いた声', gender: 'Male' },
  { id: 'ja-JP-MayuNeural', name: '真夕 (Mayu) - 女性・明るい声', gender: 'Female' },
  { id: 'ja-JP-NaokiNeural', name: '直樹 (Naoki) - 男性・アナウンス調', gender: 'Male' },
  { id: 'ja-JP-ShioriNeural', name: '詩織 (Shiori) - 女性・アナウンス調', gender: 'Female' }
];

// キャッシュサイズ上限: 1GB (1024 * 1024 * 1024 bytes)
const MAX_CACHE_SIZE_BYTES = parseInt(process.env.MAX_CACHE_SIZE_MB || '1024', 10) * 1024 * 1024;
// クリーンアップ時の目標サイズ (900MB)
const TARGET_CACHE_SIZE_BYTES = Math.floor(MAX_CACHE_SIZE_BYTES * 0.9);

class TTSManager {
  constructor() {
    this.defaultVoice = process.env.DEFAULT_VOICE || 'ja-JP-NanamiNeural';
    // 起動時と1時間ごとに容量制限チェック
    this.enforceLRUCacheLimit();
    setInterval(() => this.enforceLRUCacheLimit(), 60 * 60 * 1000);
  }

  getVoices() {
    return SUPPORTED_VOICES;
  }

  /**
   * テキストからMP3音声を生成（キャッシュがあれば再利用してmtime更新）
   * @param {string} text 読み上げテキスト
   * @param {Object} options voice, rate, pitch, volume
   * @returns {Promise<{ filename: string, filepath: string, urlPath: string }>}
   */
  async generateSpeech(text, options = {}) {
    if (!text || !text.trim()) {
      throw new Error('読み上げるテキストが空です');
    }

    const cleanText = text.trim();
    const voice = options.voice || this.defaultVoice;
    const rate = options.rate || '+0%';
    const pitch = options.pitch || '+0Hz';
    const volume = options.volume || '+0%';

    // キャッシュ用ハッシュキー生成
    const hash = crypto
      .createHash('md5')
      .update(`${cleanText}_${voice}_${rate}_${pitch}_${volume}`)
      .digest('hex');

    const filename = `speech_${hash}.mp3`;
    const filepath = path.join(VOICE_DIR, filename);

    // キャッシュが存在しサイズが0でなければ再利用（LRU: アクセス時刻を更新）
    if (fs.existsSync(filepath)) {
      try {
        const stats = fs.statSync(filepath);
        if (stats.size > 0) {
          const now = new Date();
          fs.utimesSync(filepath, now, now); // アクセス時刻・更新時刻をタッチ
          return {
            filename,
            filepath,
            urlPath: `/voice/${filename}`
          };
        }
      } catch (e) {
        // stat 失敗時は再生成へ
      }
    }

    // 生成（最大2回リトライ）
    let lastError = null;
    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        const tts = new EdgeTTS({
          voice,
          lang: voice.startsWith('ja') ? 'ja-JP' : 'en-US',
          rate: (rate === '+0%' || rate === '0%') ? 'default' : rate,
          pitch: (pitch === '+0Hz' || pitch === '0Hz') ? 'default' : pitch,
          volume: (volume === '+0%' || volume === '0%') ? 'default' : volume,
          timeout: 15000
        });

        await tts.ttsPromise(cleanText, filepath);

        if (fs.existsSync(filepath) && fs.statSync(filepath).size > 0) {
          // 生成後に容量チェック
          this.enforceLRUCacheLimit();
          return {
            filename,
            filepath,
            urlPath: `/voice/${filename}`
          };
        }
      } catch (err) {
        lastError = err;
        console.warn(`Edge TTS 生成リトライ (${attempt}/2):`, err?.message || err);
        if (fs.existsSync(filepath)) {
          try { fs.unlinkSync(filepath); } catch (e) {}
        }
        await new Promise(r => setTimeout(r, 600));
      }
    }

    const errMsg = lastError?.message || lastError || '不明なエラー';
    console.error(`Edge TTS 生成エラー: ${errMsg}`);
    throw new Error(`音声生成に失敗しました: ${errMsg}`);
  }

  /**
   * LRU キャッシュ容量管理 (上限1GBを超えたら古いファイルから削除)
   */
  enforceLRUCacheLimit() {
    try {
      const files = fs.readdirSync(VOICE_DIR);
      const fileStats = [];
      let totalSize = 0;

      for (const file of files) {
        if (!file.endsWith('.mp3')) continue;
        const filePath = path.join(VOICE_DIR, file);
        try {
          const stat = fs.statSync(filePath);
          fileStats.push({
            path: filePath,
            size: stat.size,
            mtime: stat.mtimeMs
          });
          totalSize += stat.size;
        } catch (e) {}
      }

      // 上限 (1GB) を超えている場合、古い順にソートして削除
      if (totalSize > MAX_CACHE_SIZE_BYTES) {
        console.log(`[Cache] キャッシュ容量が上限を超過 (${(totalSize / 1024 / 1024).toFixed(2)} MB / ${(MAX_CACHE_SIZE_BYTES / 1024 / 1024).toFixed(0)} MB)。古いファイルを整理します...`);
        // 最も古い（mtimeが小さい）順
        fileStats.sort((a, b) => a.mtime - b.mtime);

        for (const item of fileStats) {
          try {
            fs.unlinkSync(item.path);
            totalSize -= item.size;
            if (totalSize <= TARGET_CACHE_SIZE_BYTES) {
              break;
            }
          } catch (e) {}
        }
        console.log(`[Cache] キャッシュ整理完了。現在容量: ${(totalSize / 1024 / 1024).toFixed(2)} MB`);
      }
    } catch (err) {
      console.warn('[Cache] LRUキャッシュ容量管理中に警告:', err.message);
    }
  }

  /**
   * 現在のキャッシュ統計を取得
   */
  getCacheStats() {
    try {
      const files = fs.readdirSync(VOICE_DIR);
      let count = 0;
      let totalBytes = 0;
      for (const file of files) {
        if (!file.endsWith('.mp3')) continue;
        const stat = fs.statSync(path.join(VOICE_DIR, file));
        count++;
        totalBytes += stat.size;
      }
      return {
        count,
        totalBytes,
        totalMB: (totalBytes / 1024 / 1024).toFixed(2),
        maxMB: (MAX_CACHE_SIZE_BYTES / 1024 / 1024).toFixed(0)
      };
    } catch (e) {
      return { count: 0, totalBytes: 0, totalMB: '0', maxMB: '1024' };
    }
  }
}

module.exports = new TTSManager();
