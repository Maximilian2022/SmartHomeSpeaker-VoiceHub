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

class TTSManager {
  constructor() {
    this.defaultVoice = process.env.DEFAULT_VOICE || 'ja-JP-NanamiNeural';
    this.cleanOldFiles();
    // 1時間ごとに古いキャッシュを整理
    setInterval(() => this.cleanOldFiles(), 60 * 60 * 1000);
  }

  getVoices() {
    return SUPPORTED_VOICES;
  }

  /**
   * テキストからMP3音声を生成（キャッシュがあれば再利用）
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

    // キャッシュが存在しサイズが0でなければ再利用
    if (fs.existsSync(filepath)) {
      const stats = fs.statSync(filepath);
      if (stats.size > 0) {
        return {
          filename,
          filepath,
          urlPath: `/voice/${filename}`
        };
      }
    }

    try {
      const tts = new EdgeTTS({
        voice,
        rate,
        pitch,
        volume
      });

      await tts.ttsPromise(cleanText, filepath);

      return {
        filename,
        filepath,
        urlPath: `/voice/${filename}`
      };
    } catch (err) {
      console.error(`Edge TTS 生成エラー: ${err.message}`);
      throw new Error(`音声生成に失敗しました: ${err.message}`);
    }
  }

  /**
   * 24時間以上経過した一時音声ファイルを削除
   */
  cleanOldFiles() {
    try {
      const now = Date.now();
      const maxAgeMs = 24 * 60 * 60 * 1000; // 24時間

      const files = fs.readdirSync(VOICE_DIR);
      for (const file of files) {
        if (!file.endsWith('.mp3')) continue;
        const filePath = path.join(VOICE_DIR, file);
        try {
          const stat = fs.statSync(filePath);
          if (now - stat.mtimeMs > maxAgeMs) {
            fs.unlinkSync(filePath);
          }
        } catch (e) {
          // ignore
        }
      }
    } catch (err) {
      console.warn('古い音声ファイルのクリーンアップ中に警告:', err.message);
    }
  }
}

module.exports = new TTSManager();
