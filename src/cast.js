const { Client, DefaultMediaReceiver } = require('castv2-client');

class CastManager {
  /**
   * 指定した Google Cast デバイスで音声 URL を再生
   * @param {string} host Google Home / Nest の IP アドレス
   * @param {string} mediaUrl サーバー上の音声ファイル URL (例: http://192.168.11.244:8080/voice/xxx.mp3)
   * @param {Object} options volume, contentType
   * @returns {Promise<string>}
   */
  playMedia(host, mediaUrl, options = {}) {
    return new Promise((resolve, reject) => {
      let isSettled = false;
      const client = new Client();

      // 12秒タイムアウト設定
      const timer = setTimeout(() => {
        if (!isSettled) {
          isSettled = true;
          try { client.close(); } catch (e) {}
          reject(new Error(`Google Cast 接続タイムアウト (${host})`));
        }
      }, 12000);

      const cleanupAndResolve = (result) => {
        if (!isSettled) {
          isSettled = true;
          clearTimeout(timer);
          try { client.close(); } catch (e) {}
          resolve(result);
        }
      };

      const cleanupAndReject = (err) => {
        if (!isSettled) {
          isSettled = true;
          clearTimeout(timer);
          try { client.close(); } catch (e) {}
          reject(err);
        }
      };

      client.on('error', (err) => {
        console.error(`[Cast Error] ${host}:`, err.message);
        cleanupAndReject(new Error(`Cast クライアントエラー: ${err.message}`));
      });

      client.connect(host, () => {
        // 音量指定がある場合は音量をセット
        if (typeof options.volumeLevel === 'number') {
          const level = Math.max(0.0, Math.min(1.0, options.volumeLevel));
          client.setVolume({ level }, (volErr) => {
            if (volErr) console.warn('音量設定に失敗:', volErr);
            this._launchAndPlay(client, mediaUrl, options, cleanupAndResolve, cleanupAndReject);
          });
        } else {
          this._launchAndPlay(client, mediaUrl, options, cleanupAndResolve, cleanupAndReject);
        }
      });
    });
  }

  _launchAndPlay(client, mediaUrl, options, resolve, reject) {
    client.launch(DefaultMediaReceiver, (launchErr, player) => {
      if (launchErr) {
        return reject(new Error(`DefaultMediaReceiver 起動失敗: ${launchErr.message}`));
      }

      const media = {
        contentId: mediaUrl,
        contentType: options.contentType || 'audio/mp3',
        streamType: 'BUFFERED'
      };

      player.load(media, { autoplay: true }, (loadErr, status) => {
        if (loadErr) {
          return reject(new Error(`メディア読み込み失敗: ${loadErr.message}`));
        }

        // status イベントの監視
        player.on('status', (playerStatus) => {
          if (playerStatus.playerState === 'IDLE' && playerStatus.idleReason === 'FINISHED') {
            resolve('Playback finished');
          }
        });

        // 再生リクエスト完了時点で一旦通知（Google Homeがストリームを開始した）
        setTimeout(() => {
          resolve('Playback started');
        }, 1500);
      });
    });
  }
}

module.exports = new CastManager();
