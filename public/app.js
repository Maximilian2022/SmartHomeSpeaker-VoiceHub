// ==========================================================================
// Google Home Speaker - Frontend Logic (app.js)
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  // 状態保持
  const state = {
    serverInfo: null,
    devices: [],
    voices: [],
    schedules: [],
    history: []
  };

  // DOM要素
  const el = {
    // ステータス
    serverStatusChip: document.getElementById('serverStatusChip'),
    serverStatusText: document.getElementById('serverStatusText'),
    defaultDeviceChip: document.getElementById('defaultDeviceChip'),
    defaultDeviceText: document.getElementById('defaultDeviceText'),
    // タブ
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabPanes: document.querySelectorAll('.tab-pane'),
    // 即時発言
    sayTextInput: document.getElementById('sayTextInput'),
    sayDeviceSelect: document.getElementById('sayDeviceSelect'),
    sayVoiceSelect: document.getElementById('sayVoiceSelect'),
    sayRateRange: document.getElementById('sayRateRange'),
    rateValueDisplay: document.getElementById('rateValueDisplay'),
    sayPitchRange: document.getElementById('sayPitchRange'),
    pitchValueDisplay: document.getElementById('pitchValueDisplay'),
    btnPreviewAudio: document.getElementById('btnPreviewAudio'),
    btnSpeakDirect: document.getElementById('btnSpeakDirect'),
    audioPreviewWrapper: document.getElementById('audioPreviewWrapper'),
    audioPreviewPlayer: document.getElementById('audioPreviewPlayer'),
    recentHistoryList: document.getElementById('recentHistoryList'),
    presetBtns: document.querySelectorAll('.preset-btn'),
    // スケジュール
    scheduleTableBody: document.getElementById('scheduleTableBody'),
    btnOpenNewScheduleModal: document.getElementById('btnOpenNewScheduleModal'),
    scheduleModal: document.getElementById('scheduleModal'),
    btnCloseModal: document.getElementById('btnCloseModal'),
    btnCancelModal: document.getElementById('btnCancelModal'),
    scheduleForm: document.getElementById('scheduleForm'),
    schedName: document.getElementById('schedName'),
    schedText: document.getElementById('schedText'),
    schedPreset: document.getElementById('schedPreset'),
    schedCron: document.getElementById('schedCron'),
    schedDevice: document.getElementById('schedDevice'),
    schedVoice: document.getElementById('schedVoice'),
    // デバイス
    devicesGrid: document.getElementById('devicesGrid'),
    btnRefreshDevices: document.getElementById('btnRefreshDevices'),
    // Webhookガイド
    apiEndpointUrl: document.getElementById('apiEndpointUrl'),
    copyBtns: document.querySelectorAll('.btn-copy'),
    // トースト
    toastContainer: document.getElementById('toastContainer')
  };

  // ================= 1. 初期データ読み込み =================
  async function init() {
    setupEventListeners();
    await loadServerStatus();
    await Promise.all([
      loadDevices(),
      loadVoices(),
      loadSchedules()
    ]);
  }

  // サーバー状態
  async function loadServerStatus() {
    try {
      const res = await fetch('/api/status');
      if (!res.ok) throw new Error('ステータス取得失敗');
      const data = await res.json();
      state.serverInfo = data;

      el.serverStatusText.textContent = `稼働中 (${data.serverIp}:${data.port})`;
      el.defaultDeviceText.textContent = `デフォルト: 部屋 (${data.defaultDeviceIp})`;
      el.apiEndpointUrl.textContent = `http://${data.serverIp}:${data.port}/api/say`;
    } catch (err) {
      el.serverStatusText.textContent = '接続エラー';
      el.serverStatusChip.style.borderColor = 'var(--danger)';
    }
  }

  // デバイス一覧
  async function loadDevices() {
    try {
      const res = await fetch('/api/devices');
      if (!res.ok) throw new Error('デバイス取得失敗');
      const data = await res.json();
      state.devices = data.devices || [];

      renderDeviceSelects();
      renderDevicesGrid();
    } catch (err) {
      showToast('デバイス情報の取得に失敗しました', 'error');
    }
  }

  // ボイス一覧
  async function loadVoices() {
    try {
      const res = await fetch('/api/voices');
      if (!res.ok) throw new Error('ボイス取得失敗');
      const data = await res.json();
      state.voices = data.voices || [];

      renderVoiceSelects();
    } catch (err) {
      console.warn('ボイス一覧取得失敗:', err);
    }
  }

  // スケジュール一覧
  async function loadSchedules() {
    try {
      const res = await fetch('/api/schedules');
      if (!res.ok) throw new Error('スケジュール取得失敗');
      const data = await res.json();
      state.schedules = data.schedules || [];
      state.history = data.history || [];

      renderScheduleTable();
      renderHistoryList();
    } catch (err) {
      showToast('スケジュールの取得に失敗しました', 'error');
    }
  }

  // ================= 2. レンダリング =================
  function renderDeviceSelects() {
    // 即時発言用とモーダル用のセレクトを更新
    const defaultIp = (state.serverInfo && state.serverInfo.defaultDeviceIp) || '192.168.11.97';

    let optionsHtml = '';
    state.devices.forEach(dev => {
      const isSelected = dev.ip === defaultIp ? 'selected' : '';
      optionsHtml += `<option value="${dev.ip}" ${isSelected}>${dev.name} (${dev.ip}) ${dev.ip === defaultIp ? '★デフォルト' : ''}</option>`;
    });

    el.sayDeviceSelect.innerHTML = optionsHtml;
    el.schedDevice.innerHTML = `<option value="default">デフォルト (部屋: ${defaultIp})</option>` + optionsHtml;
  }

  function renderVoiceSelects() {
    let optionsHtml = '';
    state.voices.forEach(v => {
      const isSelected = v.id === 'ja-JP-NanamiNeural' ? 'selected' : '';
      optionsHtml += `<option value="${v.id}" ${isSelected}>${v.name}</option>`;
    });

    el.sayVoiceSelect.innerHTML = optionsHtml;
    el.schedVoice.innerHTML = optionsHtml;
  }

  function renderScheduleTable() {
    if (!state.schedules.length) {
      el.scheduleTableBody.innerHTML = `<tr><td colspan="6" class="text-center empty-msg">登録されたスケジュールはありません</td></tr>`;
      return;
    }

    let rowsHtml = '';
    state.schedules.forEach(sched => {
      const checked = sched.enabled ? 'checked' : '';
      const devName = sched.deviceIp === 'default' ? '部屋 (デフォルト)' : (state.devices.find(d => d.ip === sched.deviceIp)?.name || sched.deviceIp);

      rowsHtml += `
        <tr>
          <td>
            <label class="switch">
              <input type="checkbox" class="schedule-toggle" data-id="${sched.id}" ${checked}>
              <span class="slider"></span>
            </label>
          </td>
          <td><strong>${escapeHtml(sched.name)}</strong></td>
          <td><code>${escapeHtml(sched.cron)}</code></td>
          <td>${escapeHtml(devName)}</td>
          <td>${escapeHtml(sched.text)}</td>
          <td>
            <div class="table-actions">
              <button type="button" class="btn-icon btn-run-sched" data-id="${sched.id}" title="今すぐ実行">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              </button>
              <button type="button" class="btn-icon danger btn-delete-sched" data-id="${sched.id}" title="削除">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          </td>
        </tr>
      `;
    });

    el.scheduleTableBody.innerHTML = rowsHtml;
  }

  function renderDevicesGrid() {
    const defaultIp = (state.serverInfo && state.serverInfo.defaultDeviceIp) || '192.168.11.97';

    let cardsHtml = '';
    state.devices.forEach(dev => {
      const isDef = dev.ip === defaultIp;
      cardsHtml += `
        <div class="device-card ${isDef ? 'default-dev' : ''}">
          <div class="device-card-header">
            <span class="device-card-title">${escapeHtml(dev.name)}</span>
            ${isDef ? '<span class="device-tag">デフォルト</span>' : ''}
          </div>
          <div class="device-card-info">
            <span><strong>IP:</strong> ${escapeHtml(dev.ip)}</span>
            <span><strong>モデル:</strong> ${escapeHtml(dev.model || 'Google Cast')}</span>
          </div>
          <button type="button" class="btn btn-secondary btn-sm btn-quick-ping" data-ip="${dev.ip}" data-name="${dev.name}" style="margin-top: 6px;">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            テスト発声
          </button>
        </div>
      `;
    });

    el.devicesGrid.innerHTML = cardsHtml;
  }

  function renderHistoryList() {
    if (!state.history.length) {
      el.recentHistoryList.innerHTML = `<li class="empty-msg">履歴はまだありません</li>`;
      return;
    }

    let itemsHtml = '';
    state.history.slice(0, 15).forEach(item => {
      const timeStr = item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : '';
      const isSuccess = item.status === 'success';

      itemsHtml += `
        <li class="history-item">
          <div class="history-header">
            <span>${timeStr}</span>
            <span style="color: ${isSuccess ? 'var(--success)' : 'var(--danger)'}">${isSuccess ? '成功' : '失敗'}</span>
          </div>
          <div class="history-text">${escapeHtml(item.text)}</div>
        </li>
      `;
    });

    el.recentHistoryList.innerHTML = itemsHtml;
  }

  // ================= 3. イベントリスナー =================
  function setupEventListeners() {
    // タブ切り替え
    el.tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        el.tabBtns.forEach(b => b.classList.remove('active'));
        el.tabPanes.forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const targetId = btn.getAttribute('data-tab');
        document.getElementById(targetId)?.classList.add('active');
      });
    });

    // クイックプリセットクリック
    el.presetBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        el.sayTextInput.value = btn.getAttribute('data-text');
        el.sayTextInput.focus();
      });
    });

    // スライダー値表示
    el.sayRateRange.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      el.rateValueDisplay.textContent = val === 0 ? '標準 (0%)' : (val > 0 ? `+${val}%` : `${val}%`);
    });

    el.sayPitchRange.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      el.pitchValueDisplay.textContent = val === 0 ? '標準 (0Hz)' : (val > 0 ? `+${val}Hz` : `${val}Hz`);
    });

    // ブラウザ試聴プレビュー
    el.btnPreviewAudio.addEventListener('click', async () => {
      const text = el.sayTextInput.value.trim();
      if (!text) {
        showToast('テキストを入力してください', 'error');
        return;
      }

      el.btnPreviewAudio.disabled = true;
      el.btnPreviewAudio.textContent = '音声生成中...';

      try {
        const voice = el.sayVoiceSelect.value;
        const rate = (parseInt(el.sayRateRange.value) >= 0 ? '+' : '') + el.sayRateRange.value + '%';
        const pitch = (parseInt(el.sayPitchRange.value) >= 0 ? '+' : '') + el.sayPitchRange.value + 'Hz';

        const params = new URLSearchParams({ text, voice, rate, pitch });
        const audioUrl = `/api/preview?${params.toString()}`;

        el.audioPreviewPlayer.src = audioUrl;
        el.audioPreviewWrapper.style.display = 'block';
        await el.audioPreviewPlayer.play();
        showToast('試聴音声を再生しました');
      } catch (err) {
        showToast('試聴の生成に失敗しました: ' + err.message, 'error');
      } finally {
        el.btnPreviewAudio.disabled = false;
        el.btnPreviewAudio.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> ブラウザで試聴`;
      }
    });

    // Google Home で発言
    el.btnSpeakDirect.addEventListener('click', async () => {
      const text = el.sayTextInput.value.trim();
      if (!text) {
        showToast('テキストを入力してください', 'error');
        return;
      }

      el.btnSpeakDirect.disabled = true;
      el.btnSpeakDirect.textContent = 'Google Homeへ送信中...';

      try {
        const deviceIp = el.sayDeviceSelect.value;
        const voice = el.sayVoiceSelect.value;
        const rate = (parseInt(el.sayRateRange.value) >= 0 ? '+' : '') + el.sayRateRange.value + '%';
        const pitch = (parseInt(el.sayPitchRange.value) >= 0 ? '+' : '') + el.sayPitchRange.value + 'Hz';

        const res = await fetch('/api/say', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, deviceIp, voice, rate, pitch })
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.error || '送信失敗');
        }

        const data = await res.json();
        showToast(`Google Home (${data.deviceIp}) で再生を開始しました！`, 'success');

        // 履歴に追加
        state.history.unshift({
          text,
          status: 'success',
          timestamp: new Date().toISOString()
        });
        renderHistoryList();
      } catch (err) {
        showToast(`発声エラー: ${err.message}`, 'error');
      } finally {
        el.btnSpeakDirect.disabled = false;
        el.btnSpeakDirect.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg> Google Homeで発言`;
      }
    });

    // デバイス一覧内クイックテストボタン (イベント委譲)
    el.devicesGrid.addEventListener('click', async (e) => {
      const btn = e.target.closest('.btn-quick-ping');
      if (!btn) return;

      const ip = btn.getAttribute('data-ip');
      const name = btn.getAttribute('data-name');
      const text = `${name}のテストです。音声通知は正常に動作しています。`;

      btn.disabled = true;
      btn.textContent = '送信中...';

      try {
        const res = await fetch('/api/say', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, deviceIp: ip })
        });
        if (!res.ok) throw new Error('送信失敗');
        showToast(`${name} (${ip}) にテスト音声を送信しました！`, 'success');
      } catch (err) {
        showToast(`送信エラー: ${err.message}`, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> テスト発声`;
      }
    });

    // デバイス再スキャン
    el.btnRefreshDevices.addEventListener('click', async () => {
      el.btnRefreshDevices.disabled = true;
      showToast('デバイスを再スキャンしています...');
      await loadDevices();
      el.btnRefreshDevices.disabled = false;
      showToast('デバイスリストを更新しました', 'success');
    });

    // スケジュール テーブル内操作 (イベント委譲)
    el.scheduleTableBody.addEventListener('change', async (e) => {
      const toggle = e.target.closest('.schedule-toggle');
      if (!toggle) return;
      const id = toggle.getAttribute('data-id');

      try {
        const res = await fetch(`/api/schedules/${id}/toggle`, { method: 'POST' });
        if (!res.ok) throw new Error('トグル失敗');
        const updated = await res.json();
        showToast(`「${updated.name}」を${updated.enabled ? '有効' : '無効'}にしました`);
      } catch (err) {
        showToast('状態の更新に失敗しました', 'error');
        toggle.checked = !toggle.checked;
      }
    });

    el.scheduleTableBody.addEventListener('click', async (e) => {
      const runBtn = e.target.closest('.btn-run-sched');
      if (runBtn) {
        const id = runBtn.getAttribute('data-id');
        runBtn.disabled = true;
        try {
          const res = await fetch(`/api/schedules/${id}/run`, { method: 'POST' });
          if (!res.ok) throw new Error('実行失敗');
          showToast('スケジュールを即時実行しました！', 'success');
          await loadSchedules();
        } catch (err) {
          showToast('実行エラー: ' + err.message, 'error');
        } finally {
          runBtn.disabled = false;
        }
        return;
      }

      const delBtn = e.target.closest('.btn-delete-sched');
      if (delBtn) {
        const id = delBtn.getAttribute('data-id');
        if (!confirm('このスケジュールを削除してよろしいですか？')) return;

        try {
          const res = await fetch(`/api/schedules/${id}`, { method: 'DELETE' });
          if (!res.ok) throw new Error('削除失敗');
          showToast('スケジュールを削除しました', 'success');
          await loadSchedules();
        } catch (err) {
          showToast('削除エラー: ' + err.message, 'error');
        }
      }
    });

    // モーダル操作
    el.btnOpenNewScheduleModal.addEventListener('click', () => {
      el.scheduleForm.reset();
      el.schedCron.value = '0 7 * * *';
      el.scheduleModal.style.display = 'flex';
    });

    el.btnCloseModal.addEventListener('click', () => { el.scheduleModal.style.display = 'none'; });
    el.btnCancelModal.addEventListener('click', () => { el.scheduleModal.style.display = 'none'; });

    // プリセット変更で Cron 入力
    el.schedPreset.addEventListener('change', (e) => {
      if (e.target.value !== 'custom') {
        el.schedCron.value = e.target.value;
      }
    });

    // スケジュール保存
    el.scheduleForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const payload = {
        name: el.schedName.value.trim(),
        text: el.schedText.value.trim(),
        cron: el.schedCron.value.trim(),
        deviceIp: el.schedDevice.value,
        voice: el.schedVoice.value,
        enabled: true
      };

      try {
        const res = await fetch('/api/schedules', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.error || '保存失敗');
        }

        showToast('新規スケジュールを登録しました！', 'success');
        el.scheduleModal.style.display = 'none';
        await loadSchedules();
      } catch (err) {
        showToast('登録エラー: ' + err.message, 'error');
      }
    });

    // コピーボタン
    el.copyBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-copy-target');
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
          navigator.clipboard.writeText(targetEl.textContent.trim());
          btn.textContent = 'コピー完了!';
          setTimeout(() => { btn.textContent = 'コピー'; }, 2000);
        }
      });
    });
  }

  // ================= 4. ユーティリティ =================
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${escapeHtml(message)}</span>`;
    el.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // 起動実行
  init();
});
