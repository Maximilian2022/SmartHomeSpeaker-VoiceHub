// ==========================================================================
// Google Home & Alexa Speaker - Frontend Logic (app.js)
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
    cacheStatusText: document.getElementById('cacheStatusText'),
    defaultDeviceText: document.getElementById('defaultDeviceText'),
    // タブ
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabPanes: document.querySelectorAll('.tab-pane'),
    // 即時発言
    sayTextInput: document.getElementById('sayTextInput'),
    saySpeakersContainer: document.getElementById('saySpeakersContainer'),
    btnSelectAllSpeakers: document.getElementById('btnSelectAllSpeakers'),
    btnClearSpeakers: document.getElementById('btnClearSpeakers'),
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
    schedFrequencyRadios: document.querySelectorAll('input[name="schedFrequency"]'),
    schedWeekdaysWrapper: document.getElementById('schedWeekdaysWrapper'),
    schedWeekdayChecks: document.querySelectorAll('input[name="schedDay"]'),
    schedTime: document.getElementById('schedTime'),
    schedVoice: document.getElementById('schedVoice'),
    schedSpeakersContainer: document.getElementById('schedSpeakersContainer'),
    // デバイス
    devicesGrid: document.getElementById('devicesGrid'),
    btnRefreshDevices: document.getElementById('btnRefreshDevices'),
    // Webhookガイド & Tunnel
    apiEndpointUrl: document.getElementById('apiEndpointUrl'),
    tunnelDomainBanner: document.getElementById('tunnelDomainBanner'),
    tunnelDomainBadge: document.getElementById('tunnelDomainBadge'),
    tunnelEndpointBox: document.getElementById('tunnelEndpointBox'),
    apiTunnelEndpointUrl: document.getElementById('apiTunnelEndpointUrl'),
    tunnelCurlSection: document.getElementById('tunnelCurlSection'),
    curlTunnelExample: document.getElementById('curlTunnelExample'),
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

      // キャッシュ容量表示
      if (data.cacheStats) {
        el.cacheStatusText.textContent = `Cache: ${data.cacheStats.totalMB} MB / ${data.cacheStats.maxMB} MB`;
      }

      // Cloudflare Tunnel 情報の反映
      if (data.tunnelDomain) {
        el.tunnelDomainBanner.style.display = 'block';
        el.tunnelDomainBadge.textContent = data.tunnelDomain;
        el.tunnelEndpointBox.style.display = 'flex';
        el.apiTunnelEndpointUrl.textContent = `https://${data.tunnelDomain}/api/say`;
        el.tunnelCurlSection.style.display = 'block';
        el.curlTunnelExample.textContent = `curl -X POST https://${data.tunnelDomain}/api/say \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer your-secret-token" \\\n  -d '{\n    "text": "外出先からの通知です。",\n    "devices": ["部屋"]\n  }'`;
      }
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

      renderSpeakersCheckboxes(el.saySpeakersContainer, 'saySpeaker', ['192.168.11.97']);
      renderSpeakersCheckboxes(el.schedSpeakersContainer, 'schedSpeaker', ['default']);
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

  // 複数スピーカー選択チェックボックスの描画
  function renderSpeakersCheckboxes(container, nameAttr, selectedValues = []) {
    const defaultIp = (state.serverInfo && state.serverInfo.defaultDeviceIp) || '192.168.11.97';
    let html = '';

    // スケジュール用: デフォルト選択肢
    if (nameAttr === 'schedSpeaker') {
      const isDefChecked = selectedValues.includes('default') ? 'checked' : '';
      html += `
        <label class="speaker-chip ${isDefChecked ? 'checked' : ''}">
          <input type="checkbox" name="${nameAttr}" value="default" ${isDefChecked}>
          <span class="speaker-chip-name">デフォルト (部屋)</span>
          <span class="speaker-chip-badge">標準</span>
        </label>
      `;
    }

    state.devices.forEach(dev => {
      const isChecked = selectedValues.includes(dev.ip) ? 'checked' : '';
      const isDefault = dev.ip === defaultIp;
      const isAlexa = dev.type === 'alexa' || dev.ip.startsWith('alexa:');

      html += `
        <label class="speaker-chip ${isAlexa ? 'alexa-chip' : ''} ${isChecked ? 'checked' : ''}">
          <input type="checkbox" name="${nameAttr}" value="${dev.ip}" ${isChecked}>
          <span class="speaker-chip-name">${escapeHtml(dev.name)}</span>
          ${isDefault ? '<span class="speaker-chip-badge">★</span>' : ''}
          ${isAlexa ? '<span class="speaker-chip-badge" style="color:var(--alexa-color);">Echo</span>' : ''}
        </label>
      `;
    });

    container.innerHTML = html;

    // チェック状態変化でスタイル反映
    container.querySelectorAll('input[type="checkbox"]').forEach(chk => {
      chk.addEventListener('change', (e) => {
        const parent = e.target.closest('.speaker-chip');
        if (e.target.checked) {
          parent.classList.add('checked');
        } else {
          parent.classList.remove('checked');
        }
      });
    });
  }

  function getSelectedSpeakers(container) {
    const checked = container.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checked).map(c => c.value);
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

      // 送信先スピーカー名一覧の生成
      const targets = sched.deviceIps || (sched.deviceIp ? [sched.deviceIp] : ['default']);
      const devNames = targets.map(t => {
        if (t === 'default') return '部屋 (デフォルト)';
        const found = state.devices.find(d => d.ip === t);
        return found ? found.name : t;
      }).join(', ');

      rowsHtml += `
        <tr>
          <td>
            <label class="switch">
              <input type="checkbox" class="schedule-toggle" data-id="${sched.id}" ${checked}>
              <span class="slider"></span>
            </label>
          </td>
          <td><strong>${escapeHtml(sched.name)}</strong></td>
          <td><span class="badge-tech" style="font-size:0.82rem; text-transform:none;">${escapeHtml(sched.readableFrequency || sched.cron)}</span></td>
          <td><span style="font-size:0.85rem; color:var(--text-muted);">${escapeHtml(devNames)}</span></td>
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
      const isAlexa = dev.type === 'alexa' || dev.ip.startsWith('alexa:');

      cardsHtml += `
        <div class="device-card ${isDef ? 'default-dev' : ''} ${isAlexa ? 'alexa-dev' : ''}">
          <div class="device-card-header">
            <span class="device-card-title">${escapeHtml(dev.name)}</span>
            ${isDef ? '<span class="device-tag">デフォルト</span>' : ''}
            ${isAlexa ? '<span class="device-tag alexa">Alexa Echo</span>' : ''}
          </div>
          <div class="device-card-info">
            <span><strong>識別子/IP:</strong> ${escapeHtml(dev.ip)}</span>
            <span><strong>モデル:</strong> ${escapeHtml(dev.model || 'Smart Speaker')}</span>
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

    // 全室選択 / クリア
    el.btnSelectAllSpeakers.addEventListener('click', () => {
      el.saySpeakersContainer.querySelectorAll('input[type="checkbox"]').forEach(c => {
        c.checked = true;
        c.closest('.speaker-chip').classList.add('checked');
      });
    });

    el.btnClearSpeakers.addEventListener('click', () => {
      el.saySpeakersContainer.querySelectorAll('input[type="checkbox"]').forEach(c => {
        c.checked = false;
        c.closest('.speaker-chip').classList.remove('checked');
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

    // スピーカーで発言 (複数選択対応)
    el.btnSpeakDirect.addEventListener('click', async () => {
      const text = el.sayTextInput.value.trim();
      if (!text) {
        showToast('テキストを入力してください', 'error');
        return;
      }

      const selectedSpeakers = getSelectedSpeakers(el.saySpeakersContainer);
      if (!selectedSpeakers.length) {
        showToast('送信先スピーカーを1台以上選択してください', 'error');
        return;
      }

      el.btnSpeakDirect.disabled = true;
      el.btnSpeakDirect.textContent = 'スピーカーへ送信中...';

      try {
        const voice = el.sayVoiceSelect.value;
        const rate = (parseInt(el.sayRateRange.value) >= 0 ? '+' : '') + el.sayRateRange.value + '%';
        const pitch = (parseInt(el.sayPitchRange.value) >= 0 ? '+' : '') + el.sayPitchRange.value + 'Hz';

        const res = await fetch('/api/say', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, devices: selectedSpeakers, voice, rate, pitch })
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.error || '送信失敗');
        }

        const data = await res.json();
        const successCount = data.results?.filter(r => r.status === 'success').length || 0;
        showToast(`${selectedSpeakers.length} 台のスピーカーへ送信完了 (${successCount} 台成功)！`, 'success');

        // 履歴に追加
        state.history.unshift({
          text,
          status: 'success',
          timestamp: new Date().toISOString()
        });
        renderHistoryList();
        // キャッシュ統計の再取得
        loadServerStatus();
      } catch (err) {
        showToast(`発声エラー: ${err.message}`, 'error');
      } finally {
        el.btnSpeakDirect.disabled = false;
        el.btnSpeakDirect.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg> スピーカーで発言`;
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
          body: JSON.stringify({ text, devices: [ip] })
        });
        if (!res.ok) throw new Error('送信失敗');
        showToast(`${name} にテスト音声を送信しました！`, 'success');
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

    // スケジュール頻度ラジオ変更 (曜日指定表示切り替え)
    el.schedFrequencyRadios.forEach(radio => {
      radio.addEventListener('change', (e) => {
        if (e.target.value === 'custom_days') {
          el.schedWeekdaysWrapper.style.display = 'block';
        } else {
          el.schedWeekdaysWrapper.style.display = 'none';
        }
      });
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
      el.schedTime.value = '07:00';
      el.schedWeekdaysWrapper.style.display = 'none';
      renderSpeakersCheckboxes(el.schedSpeakersContainer, 'schedSpeaker', ['default']);
      el.scheduleModal.style.display = 'flex';
    });

    el.btnCloseModal.addEventListener('click', () => { el.scheduleModal.style.display = 'none'; });
    el.btnCancelModal.addEventListener('click', () => { el.scheduleModal.style.display = 'none'; });

    // スケジュール保存
    el.scheduleForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const freqRadio = document.querySelector('input[name="schedFrequency"]:checked');
      const frequency = freqRadio ? freqRadio.value : 'daily';

      // 選択された曜日
      const weekdays = [];
      if (frequency === 'custom_days') {
        el.schedWeekdayChecks.forEach(c => {
          if (c.checked) weekdays.push(parseInt(c.value, 10));
        });
        if (!weekdays.length) {
          showToast('曜日を1つ以上選択してください', 'error');
          return;
        }
      }

      const selectedSpeakers = getSelectedSpeakers(el.schedSpeakersContainer);
      if (!selectedSpeakers.length) {
        showToast('送信先スピーカーを1つ以上選択してください', 'error');
        return;
      }

      const payload = {
        name: el.schedName.value.trim(),
        text: el.schedText.value.trim(),
        frequency,
        time: el.schedTime.value,
        weekdays,
        deviceIps: selectedSpeakers,
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
