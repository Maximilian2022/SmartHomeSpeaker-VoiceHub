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
    schedRateRange: document.getElementById('schedRateRange'),
    schedRateValueDisplay: document.getElementById('schedRateValueDisplay'),
    schedPitchRange: document.getElementById('schedPitchRange'),
    schedPitchValueDisplay: document.getElementById('schedPitchValueDisplay'),
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
    // Alexa 連携
    alexaStatusBadge: document.getElementById('alexaStatusBadge'),
    alexaStateUnlinked: document.getElementById('alexaStateUnlinked'),
    alexaStateWaiting: document.getElementById('alexaStateWaiting'),
    alexaStateLinked: document.getElementById('alexaStateLinked'),
    btnStartAlexaAuth: document.getElementById('btnStartAlexaAuth'),
    btnCancelAlexaAuth: document.getElementById('btnCancelAlexaAuth'),
    alexaLoginLink: document.getElementById('alexaLoginLink'),
    alexaLoginUrlText: document.getElementById('alexaLoginUrlText'),
    btnRefreshAlexaDevices: document.getElementById('btnRefreshAlexaDevices'),
    btnLogoutAlexa: document.getElementById('btnLogoutAlexa'),
    inputAlexaToken: document.getElementById('inputAlexaToken'),
    btnSaveAlexaToken: document.getElementById('btnSaveAlexaToken'),
    // トースト
    toastContainer: document.getElementById('toastContainer')
  };

  let alexaPollTimer = null;

  // ================= 1. 初期データ読み込み =================
  async function init() {
    setupEventListeners();
    setupWebhookBuilder();
    setupCalendarHandlers();
    await loadServerStatus();
    await Promise.all([
      loadDevices(),
      loadVoices(),
      loadSchedules(),
      loadAlexaStatus(),
      loadCalendarSettings(),
      loadCalendarEvents()
    ]);
  }

  // サーバー状態
  async function loadServerStatus() {
    try {
      const res = await fetch('/api/status');
      if (!res.ok) throw new Error('ステータス取得失敗');
      const data = await res.json();
      state.serverInfo = data;

      if (el.serverStatusText) el.serverStatusText.textContent = `稼働中 (${data.serverIp}:${data.port})`;
      if (el.defaultDeviceText) el.defaultDeviceText.textContent = data.defaultDeviceIp ? `デフォルト: ${data.defaultDeviceIp}` : 'デフォルト未設定';
      if (el.apiEndpointUrl) el.apiEndpointUrl.textContent = `http://${data.serverIp}:${data.port}/api/say`;

      // キャッシュ容量表示
      if (data.cacheStats && el.cacheStatusText) {
        el.cacheStatusText.textContent = `Cache: ${data.cacheStats.totalMB} MB / ${data.cacheStats.maxMB} MB`;
      }

      // Webhook Token の反映
      const tokenInput = document.getElementById('txtWebhookTokenVal');
      if (tokenInput && data.webhookToken) {
        tokenInput.value = data.webhookToken;
      }

      // Cloudflare Tunnel 情報の反映
      if (data.tunnelDomain) {
        if (el.tunnelDomainBanner) el.tunnelDomainBanner.style.display = 'block';
        if (el.tunnelDomainBadge) el.tunnelDomainBadge.textContent = data.tunnelDomain;
        if (el.tunnelEndpointBox) el.tunnelEndpointBox.style.display = 'flex';
        if (el.apiTunnelEndpointUrl) el.apiTunnelEndpointUrl.textContent = `https://${data.tunnelDomain}/api/say`;

        const radioTunnelWrapper = document.getElementById('builderRadioTunnelWrapper');
        if (radioTunnelWrapper) radioTunnelWrapper.style.display = 'inline-flex';
        const tunnelLabel = document.getElementById('builderTunnelUrlLabel');
        if (tunnelLabel) tunnelLabel.textContent = `https://${data.tunnelDomain}/api/say`;
      }

      // HomePod 台数の反映
      const hpBadge = document.getElementById('homepodStatusBadge');
      if (hpBadge && data.homepodCount !== undefined) {
        hpBadge.textContent = `${data.homepodCount > 0 ? data.homepodCount - 1 : 0} 台認識済み`;
      }

      updateBuilderCode();
    } catch (err) {
      if (el.serverStatusText) el.serverStatusText.textContent = '接続エラー';
      if (el.serverStatusChip) el.serverStatusChip.style.borderColor = 'var(--danger)';
    }
  }

  // デバイス一覧
  async function loadDevices() {
    try {
      const res = await fetch('/api/devices');
      if (!res.ok) throw new Error('デバイス取得失敗');
      const data = await res.json();
      state.devices = data.devices || [];

      const initialSelected = state.serverInfo?.defaultDeviceIp
        ? [state.serverInfo.defaultDeviceIp]
        : (state.devices[0] ? [state.devices[0].ip] : []);

      renderSpeakersCheckboxes(el.saySpeakersContainer, 'saySpeaker', initialSelected);
      renderSpeakersCheckboxes(el.schedSpeakersContainer, 'schedSpeaker', ['default']);
      renderCalendarSpeakers();
      renderDevicesGrid();
      renderBuilderSpeakers();
      updateBuilderCode();
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

  // スピーカー表示名の整形（重複する Alexa: や HomePod: プレフィックスの除去）
  function formatSpeakerDisplayName(name) {
    if (!name) return '';
    return name
      .replace(/^(Alexa:\s*|HomePod:\s*)/i, '')
      .replace(/^Alexa\s*\((全室\s*Echo)\)/i, '$1')
      .replace(/^HomePod\s*\((全室\s*HomePod)\)/i, '$1');
  }

  // 複数スピーカー選択チェックボックスの描画
  function renderSpeakersCheckboxes(container, nameAttr, selectedValues = []) {
    const defaultIp = (state.serverInfo && state.serverInfo.defaultDeviceIp) || (state.devices[0]?.ip || '');
    let html = '';

    // スケジュール用: デフォルト選択肢
    if (nameAttr === 'schedSpeaker') {
      const isDefChecked = selectedValues.includes('default') ? 'checked' : '';
      html += `
        <label class="speaker-chip ${isDefChecked ? 'checked' : ''}">
          <input type="checkbox" name="${nameAttr}" value="default" ${isDefChecked}>
          <span class="speaker-chip-name">デフォルト (標準)</span>
          <span class="speaker-chip-badges">
            <span class="speaker-chip-badge default-badge">標準</span>
          </span>
        </label>
      `;
    }

    state.devices.forEach(dev => {
      const isChecked = selectedValues.includes(dev.ip) ? 'checked' : '';
      const isDefault = dev.ip === defaultIp;
      const isAlexa = dev.type === 'alexa' || dev.ip.startsWith('alexa:');
      const isHomePod = dev.type === 'homepod' || dev.ip.startsWith('homepod:');
      const chipClass = isAlexa ? 'alexa-chip' : (isHomePod ? 'homepod-chip' : 'google-chip');
      const displayName = formatSpeakerDisplayName(dev.name);

      let badgeHtml = '';
      if (isDefault) {
        badgeHtml += '<span class="speaker-chip-badge default-badge" title="標準スピーカー">★</span>';
      }
      if (isAlexa) {
        badgeHtml += '<span class="speaker-chip-badge alexa-badge">Echo</span>';
      } else if (isHomePod) {
        badgeHtml += '<span class="speaker-chip-badge homepod-badge">HomePod</span>';
      } else {
        badgeHtml += '<span class="speaker-chip-badge google-badge">Google Home</span>';
      }

      html += `
        <label class="speaker-chip ${chipClass} ${isChecked ? 'checked' : ''}" title="${escapeHtml(displayName)} (${escapeHtml(dev.model || dev.type)})">
          <input type="checkbox" name="${nameAttr}" value="${dev.ip}" ${isChecked}>
          <span class="speaker-chip-name">${escapeHtml(displayName)}</span>
          <span class="speaker-chip-badges">${badgeHtml}</span>
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

  // カレンダー用スピーカーチェックボックスの描画
  function renderCalendarSpeakers(selectedList = ['default']) {
    const container = document.getElementById('calSpeakersContainer');
    if (!container) return;
    renderSpeakersCheckboxes(container, 'calSpeaker', selectedList);
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

    const calVoice = document.getElementById('calVoice');
    if (calVoice) {
      calVoice.innerHTML = optionsHtml;
    }

    const bVoice = document.getElementById('builderVoice');
    if (bVoice) {
      bVoice.innerHTML = '<option value="">デフォルト (Nanami - 女性)</option>' + optionsHtml;
    }
  }

  // cron式から人間が直感的に理解できる自然な日本語を解析
  function formatHumanReadableCron(sched) {
    if (!sched) return '未設定';

    const WEEKDAY_NAMES_MAP = {
      '0': '日', '1': '月', '2': '火', '3': '水', '4': '木', '5': '金', '6': '土', '7': '日'
    };

    // 1. frequency と time が指定されている場合
    if (sched.frequency && sched.time) {
      const time = sched.time;
      switch (sched.frequency) {
        case 'daily':
          return `毎日 ${time}`;
        case 'weekdays':
          return `平日 (月〜金) ${time}`;
        case 'weekends':
          return `土日 ${time}`;
        case 'custom_days':
          if (Array.isArray(sched.weekdays) && sched.weekdays.length) {
            const names = sched.weekdays.map(d => WEEKDAY_NAMES_MAP[d] || d).join('・');
            return `毎週 ${names} ${time}`;
          }
          return `指定曜日 ${time}`;
      }
    }

    // 2. 既に自然な日本語になっている場合はそれを使用 (古い raw 形式は除外)
    if (sched.readableFrequency && !sched.readableFrequency.includes('(') && !sched.readableFrequency.includes('*')) {
      return sched.readableFrequency;
    }

    // 3. cron 式から自然な日本語を自動解析
    const cron = (sched.cron || '').trim();
    if (cron) {
      const parts = cron.split(/\s+/);
      if (parts.length === 5) {
        const [m, h, dom, mon, dow] = parts;

        if (/^\d+$/.test(m) && /^\d+$/.test(h)) {
          const timeStr = `${h.padStart(2, '0')}:${m.padStart(2, '0')}`;

          if (dom === '*' && mon === '*') {
            if (dow === '*') return `毎日 ${timeStr}`;
            if (dow === '1-5' || dow === '1,2,3,4,5') return `平日 (月〜金) ${timeStr}`;
            if (dow === '0,6' || dow === '6,0') return `土日 ${timeStr}`;
            const days = dow.split(',').map(d => WEEKDAY_NAMES_MAP[d.trim()] || d).filter(Boolean);
            if (days.length) return `毎週 ${days.join('・')} ${timeStr}`;
          }
        }

        if (m.startsWith('*/') && h === '*' && dom === '*' && mon === '*' && dow === '*') {
          return `${m.slice(2)}分ごと`;
        }
        if (m === '0' && h === '*' && dom === '*' && mon === '*' && dow === '*') {
          return `毎時 00分`;
        }
      }
      return cron;
    }

    return sched.readableFrequency || sched.time || '未設定';
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
        if (t === 'default') return 'デフォルト (標準)';
        const found = state.devices.find(d => d.ip === t);
        return found ? formatSpeakerDisplayName(found.name) : t;
      }).join(', ');

      const freqText = formatHumanReadableCron(sched);

      rowsHtml += `
        <tr>
          <td>
            <label class="switch">
              <input type="checkbox" class="schedule-toggle" data-id="${sched.id}" ${checked}>
              <span class="slider"></span>
            </label>
          </td>
          <td><strong>${escapeHtml(sched.name)}</strong></td>
          <td>
            <span class="sched-freq-badge" title="cron: ${escapeHtml(sched.cron || '')}">
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              ${escapeHtml(freqText)}
            </span>
          </td>
          <td><span style="font-size:0.85rem; color:var(--text-muted);">${escapeHtml(devNames)}</span></td>
          <td>${escapeHtml(sched.text)}</td>
          <td>
            <div class="table-actions">
              <button type="button" class="btn-icon btn-edit-sched" data-id="${sched.id}" title="編集">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
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
    const defaultIp = (state.serverInfo && state.serverInfo.defaultDeviceIp) || (state.devices[0]?.ip || '');

    let cardsHtml = '';
    state.devices.forEach(dev => {
      const isDef = dev.ip === defaultIp;
      const isAlexa = dev.type === 'alexa' || dev.ip.startsWith('alexa:');
      const isHomePod = dev.type === 'homepod' || dev.ip.startsWith('homepod:');
      const displayName = formatSpeakerDisplayName(dev.name);

      cardsHtml += `
        <div class="device-card ${isDef ? 'default-dev' : ''} ${isAlexa ? 'alexa-dev' : ''} ${isHomePod ? 'homepod-dev' : ''}" style="${isDef ? 'border-color: rgba(245, 158, 11, 0.4); box-shadow: 0 0 15px rgba(245, 158, 11, 0.1);' : ''}">
          <div class="device-card-header" style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
            <div style="min-width:0;flex:1;">
              <span class="device-card-title" style="font-size:1.05rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;">${escapeHtml(displayName)}</span>
            </div>
            <div style="display:flex;gap:4px;flex-shrink:0;align-items:center;">
              ${isDef ? '<span class="device-tag default" style="background:rgba(245,158,11,0.15);color:#fbbf24;border:1px solid rgba(245,158,11,0.3);font-size:0.7rem;padding:2px 6px;">★ 標準</span>' : ''}
              ${!isAlexa && !isHomePod ? '<span class="device-tag google" style="background:rgba(66,133,244,0.15);color:#8ab4f8;border:1px solid rgba(66,133,244,0.3);font-size:0.7rem;padding:2px 6px;">Google Home</span>' : ''}
              ${isAlexa ? '<span class="device-tag alexa" style="font-size:0.7rem;padding:2px 6px;">Echo</span>' : ''}
              ${isHomePod ? '<span class="device-tag homepod" style="font-size:0.7rem;padding:2px 6px;">HomePod</span>' : ''}
            </div>
          </div>
          <div class="device-card-info" style="margin-top:8px;">
            <span><strong>識別子/IP:</strong> ${escapeHtml(dev.ip)}</span>
            <span><strong>モデル:</strong> ${escapeHtml(dev.model || 'Smart Speaker')}</span>
          </div>
          <div class="device-card-actions" style="display:flex;flex-direction:column;gap:8px;margin-top:14px;">
            <button type="button" class="btn btn-secondary btn-sm btn-quick-ping" data-ip="${dev.ip}" data-name="${escapeHtml(displayName)}" style="width:100%;justify-content:center;">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              テスト発声
            </button>
            ${isDef ? `
              <div style="display:flex;align-items:center;justify-content:center;gap:6px;width:100%;color:#fbbf24;font-size:0.82rem;font-weight:600;padding:7px 12px;border-radius:var(--radius-sm);background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);box-sizing:border-box;">
                ★ デフォルト (標準) 端末
              </div>
            ` : `
              <button type="button" class="btn btn-outline-gold btn-sm btn-set-default" data-ip="${dev.ip}" data-name="${escapeHtml(displayName)}" title="このスピーカーをデフォルト端末に設定します" style="width:100%;justify-content:center;">
                ★ デフォルトに設定
              </button>
            `}
          </div>
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

    // スライダー値表示 (即時発言)
    el.sayRateRange.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      el.rateValueDisplay.textContent = val === 0 ? '標準 (0%)' : (val > 0 ? `+${val}%` : `${val}%`);
    });

    el.sayPitchRange.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      el.pitchValueDisplay.textContent = val === 0 ? '標準 (0Hz)' : (val > 0 ? `+${val}Hz` : `${val}Hz`);
    });

    // スライダー値表示 (スケジュールモーダル)
    el.schedRateRange?.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      if (el.schedRateValueDisplay) {
        el.schedRateValueDisplay.textContent = val === 0 ? '標準 (0%)' : (val > 0 ? `+${val}%` : `${val}%`);
      }
    });

    el.schedPitchRange?.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      if (el.schedPitchValueDisplay) {
        el.schedPitchValueDisplay.textContent = val === 0 ? '標準 (0Hz)' : (val > 0 ? `+${val}Hz` : `${val}Hz`);
      }
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
      // 1. テスト発声ボタン
      const pingBtn = e.target.closest('.btn-quick-ping');
      if (pingBtn) {
        const ip = pingBtn.getAttribute('data-ip');
        const name = pingBtn.getAttribute('data-name');
        const text = `${name}のテストです。音声通知は正常に動作しています。`;

        pingBtn.disabled = true;
        pingBtn.textContent = '送信中...';

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
          pingBtn.disabled = false;
          pingBtn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> テスト発声`;
        }
        return;
      }

      // 2. デフォルトに設定ボタン
      const defBtn = e.target.closest('.btn-set-default');
      if (defBtn) {
        const ip = defBtn.getAttribute('data-ip');
        const name = defBtn.getAttribute('data-name');

        defBtn.disabled = true;
        defBtn.textContent = '設定中...';

        try {
          const res = await fetch('/api/devices/default', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip })
          });
          if (!res.ok) throw new Error('デフォルト設定に失敗しました');
          const data = await res.json();

          if (state.serverInfo) {
            state.serverInfo.defaultDeviceIp = data.defaultDeviceIp;
          }

          // 即時発言の初期選択や表示を更新
          if (el.defaultDeviceText) {
            el.defaultDeviceText.textContent = `デフォルト: ${name} (${data.defaultDeviceIp})`;
          }

          // 全UIを再描画
          renderSpeakersCheckboxes(el.saySpeakersContainer, 'saySpeaker', [data.defaultDeviceIp]);
          renderDevicesGrid();
          renderBuilderSpeakers();
          const calContainer = document.getElementById('calSpeakersContainer');
          if (calContainer) renderCalendarSpeakers(['default']);

          showToast(`デフォルトスピーカーを「${name}」に変更しました！`, 'success');
        } catch (err) {
          showToast(`デフォルト設定エラー: ${err.message}`, 'error');
          defBtn.disabled = false;
          defBtn.textContent = '★ デフォルトに設定';
        }
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
      // 編集ボタン
      const editBtn = e.target.closest('.btn-edit-sched');
      if (editBtn) {
        const id = editBtn.getAttribute('data-id');
        const sched = state.schedules.find(s => s.id === id);
        if (!sched) return;

        document.getElementById('schedEditId').value = sched.id;
        document.getElementById('modalTitle').textContent = 'スケジュール編集';
        el.schedName.value = sched.name || '';
        el.schedText.value = sched.text || '';
        el.schedTime.value = sched.time || '07:00';
        el.schedVoice.value = sched.voice || 'ja-JP-NanamiNeural';

        const freq = sched.frequency || 'daily';
        el.schedFrequencyRadios.forEach(r => {
          r.checked = r.value === freq;
        });

        if (freq === 'custom_days') {
          el.schedWeekdaysWrapper.style.display = 'block';
          const wDays = sched.weekdays || [];
          el.schedWeekdayChecks.forEach(c => {
            c.checked = wDays.includes(parseInt(c.value, 10));
          });
        } else {
          el.schedWeekdaysWrapper.style.display = 'none';
        }

        const targets = sched.deviceIps || (sched.deviceIp ? [sched.deviceIp] : ['default']);
        renderSpeakersCheckboxes(el.schedSpeakersContainer, 'schedSpeaker', targets);

        // 話速と音高の反映
        let rateVal = 0;
        if (sched.rate) {
          rateVal = parseInt(sched.rate, 10) || 0;
        }
        if (el.schedRateRange) el.schedRateRange.value = rateVal;
        if (el.schedRateValueDisplay) {
          el.schedRateValueDisplay.textContent = rateVal === 0 ? '標準 (0%)' : (rateVal > 0 ? `+${rateVal}%` : `${rateVal}%`);
        }

        let pitchVal = 0;
        if (sched.pitch) {
          pitchVal = parseInt(sched.pitch, 10) || 0;
        }
        if (el.schedPitchRange) el.schedPitchRange.value = pitchVal;
        if (el.schedPitchValueDisplay) {
          el.schedPitchValueDisplay.textContent = pitchVal === 0 ? '標準 (0Hz)' : (pitchVal > 0 ? `+${pitchVal}Hz` : `${pitchVal}Hz`);
        }

        el.scheduleModal.style.display = 'flex';
        return;
      }

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

    // 履歴クリア
    document.getElementById('btnClearHistory')?.addEventListener('click', () => {
      state.history = [];
      renderHistoryList();
      showToast('発言履歴をクリアしました');
    });

    // モーダル操作
    el.btnOpenNewScheduleModal.addEventListener('click', () => {
      document.getElementById('schedEditId').value = '';
      document.getElementById('modalTitle').textContent = '新規スケジュール登録';
      el.scheduleForm.reset();
      el.schedTime.value = '07:00';
      if (el.schedRateRange) el.schedRateRange.value = 0;
      if (el.schedRateValueDisplay) el.schedRateValueDisplay.textContent = '標準 (0%)';
      if (el.schedPitchRange) el.schedPitchRange.value = 0;
      if (el.schedPitchValueDisplay) el.schedPitchValueDisplay.textContent = '標準 (0Hz)';
      el.schedWeekdaysWrapper.style.display = 'none';
      renderSpeakersCheckboxes(el.schedSpeakersContainer, 'schedSpeaker', ['default']);
      el.scheduleModal.style.display = 'flex';
    });

    el.btnCloseModal.addEventListener('click', () => { el.scheduleModal.style.display = 'none'; });
    el.btnCancelModal.addEventListener('click', () => { el.scheduleModal.style.display = 'none'; });

    // スケジュール保存 (新規作成または更新)
    el.scheduleForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const editId = document.getElementById('schedEditId')?.value;
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

      const rateVal = parseInt(el.schedRateRange?.value || '0', 10);
      const pitchVal = parseInt(el.schedPitchRange?.value || '0', 10);
      const rate = (rateVal >= 0 ? '+' : '') + rateVal + '%';
      const pitch = (pitchVal >= 0 ? '+' : '') + pitchVal + 'Hz';

      const payload = {
        name: el.schedName.value.trim(),
        text: el.schedText.value.trim(),
        frequency,
        time: el.schedTime.value,
        weekdays,
        deviceIps: selectedSpeakers,
        voice: el.schedVoice.value,
        rate,
        pitch,
        enabled: true
      };

      try {
        const url = editId ? `/api/schedules/${editId}` : '/api/schedules';
        const method = editId ? 'PUT' : 'POST';

        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.error || '保存失敗');
        }

        showToast(editId ? 'スケジュールを更新しました！' : '新規スケジュールを登録しました！', 'success');
        el.scheduleModal.style.display = 'none';
        await loadSchedules();
      } catch (err) {
        showToast(`保存エラー: ${err.message}`, 'error');
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

    // Alexa 認証開始ボタン
    if (el.btnStartAlexaAuth) {
      el.btnStartAlexaAuth.addEventListener('click', async () => {
        try {
          el.btnStartAlexaAuth.disabled = true;
          el.btnStartAlexaAuth.textContent = '起動中...';

          const res = await fetch('/api/alexa/auth/start', { method: 'POST' });
          if (!res.ok) throw new Error('プロキシサーバーの起動に失敗しました');
          const data = await res.json();

          showToast('Amazon ログインページを開きました。ログインを完了してください。', 'info');
          if (data.loginUrl) {
            window.open(data.loginUrl, '_blank');
          }
          await loadAlexaStatus();
        } catch (err) {
          showToast('エラー: ' + err.message, 'error');
        } finally {
          el.btnStartAlexaAuth.disabled = false;
          el.btnStartAlexaAuth.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" x2="3" y1="12" y2="12"/></svg>
            Amazon ログインを開始して Alexa と連携
          `;
        }
      });
    }

    // Alexa 認証キャンセルボタン
    if (el.btnCancelAlexaAuth) {
      el.btnCancelAlexaAuth.addEventListener('click', async () => {
        try {
          await fetch('/api/alexa/auth/stop', { method: 'POST' });
          stopAlexaPolling();
          await loadAlexaStatus();
          showToast('Alexa 認証をキャンセルしました', 'info');
        } catch (err) {
          showToast('キャンセル失敗: ' + err.message, 'error');
        }
      });
    }

    // Alexa デバイス再取得ボタン
    if (el.btnRefreshAlexaDevices) {
      el.btnRefreshAlexaDevices.addEventListener('click', async () => {
        await loadDevices();
        showToast('Alexa デバイス一覧を再取得しました', 'success');
      });
    }

    // Alexa 連携解除ボタン
    if (el.btnLogoutAlexa) {
      el.btnLogoutAlexa.addEventListener('click', async () => {
        if (!window.confirm('Amazon Alexa との連携を解除しますか？')) return;
        try {
          await fetch('/api/alexa/logout', { method: 'POST' });
          await loadDevices();
          await loadAlexaStatus();
          showToast('Alexa 連携を解除しました', 'info');
        } catch (err) {
          showToast('連携解除失敗: ' + err.message, 'error');
        }
      });
    }

    // 手動トークン保存ボタン
    if (el.btnSaveAlexaToken) {
      el.btnSaveAlexaToken.addEventListener('click', async () => {
        const token = (el.inputAlexaToken.value || '').trim();
        if (!token) {
          return showToast('リフレッシュトークンを入力してください', 'error');
        }
        try {
          el.btnSaveAlexaToken.disabled = true;
          const res = await fetch('/api/alexa/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token })
          });
          if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.error || '保存失敗');
          }
          el.inputAlexaToken.value = '';
          await loadDevices();
          await loadAlexaStatus();
          showToast('🎉 リフレッシュトークンを保存し、Alexa デバイスを読み込みました！', 'success');
        } catch (err) {
          showToast('エラー: ' + err.message, 'error');
        } finally {
          el.btnSaveAlexaToken.disabled = false;
        }
      });
    }
  }

  // ================= Alexa 認証ステータス管理 =================
  async function loadAlexaStatus() {
    try {
      const res = await fetch('/api/alexa/status');
      if (!res.ok) return;
      const data = await res.json();

      if (data.proxyRunning) {
        el.alexaStatusBadge.textContent = '認証待機中...';
        el.alexaStatusBadge.style.color = '#facc15';
        el.alexaStatusBadge.style.borderColor = 'rgba(234, 179, 8, 0.4)';
        el.alexaStateUnlinked.style.display = 'none';
        el.alexaStateWaiting.style.display = 'block';
        el.alexaStateLinked.style.display = 'none';

        if (data.proxyUrl) {
          el.alexaLoginLink.href = data.proxyUrl;
          el.alexaLoginUrlText.textContent = data.proxyUrl;
        }

        startAlexaPolling();
      } else if (data.configured) {
        el.alexaStatusBadge.textContent = '連携完了';
        el.alexaStatusBadge.style.color = '#10b981';
        el.alexaStatusBadge.style.borderColor = 'rgba(16, 185, 129, 0.4)';
        el.alexaStateUnlinked.style.display = 'none';
        el.alexaStateWaiting.style.display = 'none';
        el.alexaStateLinked.style.display = 'block';

        stopAlexaPolling();
      } else {
        el.alexaStatusBadge.textContent = '未連携';
        el.alexaStatusBadge.style.color = 'var(--text-muted)';
        el.alexaStatusBadge.style.borderColor = 'var(--card-border)';
        el.alexaStateUnlinked.style.display = 'block';
        el.alexaStateWaiting.style.display = 'none';
        el.alexaStateLinked.style.display = 'none';

        stopAlexaPolling();
      }
    } catch (err) {
      console.warn('Alexa ステータス取得エラー:', err);
    }
  }

  function startAlexaPolling() {
    if (alexaPollTimer) return;
    alexaPollTimer = setInterval(async () => {
      try {
        const res = await fetch('/api/alexa/status');
        if (!res.ok) return;
        const data = await res.json();

        if (data.configured) {
          stopAlexaPolling();
          await loadAlexaStatus();
          await loadDevices();
          showToast('🎉 Amazon Alexa 認証が完了しました！Echo デバイスを認識しました。', 'success');
        } else if (!data.proxyRunning) {
          stopAlexaPolling();
          await loadAlexaStatus();
        }
      } catch (e) {}
    }, 2500);
  }

  function stopAlexaPolling() {
    if (alexaPollTimer) {
      clearInterval(alexaPollTimer);
      alexaPollTimer = null;
    }
  }

  // ================= 4. Webhook ビルダー機能 =================
  let builderSelectedTab = 'curl-post';

  function renderBuilderSpeakers() {
    const grid = document.getElementById('builderSpeakersGrid');
    if (!grid) return;

    if (!state.devices || state.devices.length === 0) {
      grid.innerHTML = '<span class="loading-text">スピーカーが見つかりません</span>';
      return;
    }

    let html = '';
    state.devices.forEach(dev => {
      const isAlexa = dev.type === 'alexa' || dev.ip.startsWith('alexa:');
      const isHomePod = dev.type === 'homepod' || dev.ip.startsWith('homepod:');
      const devType = isAlexa ? 'alexa' : (isHomePod ? 'homepod' : 'google');
      const chipClass = isAlexa ? 'alexa-chip' : (isHomePod ? 'homepod-chip' : 'google-chip');
      const displayName = formatSpeakerDisplayName(dev.name);

      // 初期値: デフォルトまたは最初のスピーカーを選択
      const isChecked = dev.isDefault || (!state.devices.some(d => d.isDefault) && state.devices[0]?.ip === dev.ip);

      let badgeHtml = '';
      if (dev.isDefault) {
        badgeHtml += '<span class="speaker-chip-badge default-badge" title="標準スピーカー">★</span>';
      }
      if (isAlexa) {
        badgeHtml += '<span class="speaker-chip-badge alexa-badge">Echo</span>';
      } else if (isHomePod) {
        badgeHtml += '<span class="speaker-chip-badge homepod-badge">HomePod</span>';
      } else {
        badgeHtml += '<span class="speaker-chip-badge google-badge">Google Home</span>';
      }

      html += `
        <label class="speaker-chip ${chipClass} ${isChecked ? 'checked' : ''}" title="${escapeHtml(displayName)} (${escapeHtml(dev.model || dev.type)})">
          <input type="checkbox" name="builderSpeaker" value="${dev.ip}" data-type="${devType}" ${isChecked ? 'checked' : ''}>
          <span class="speaker-chip-name">${escapeHtml(displayName)}</span>
          <span class="speaker-chip-badges">${badgeHtml}</span>
        </label>
      `;
    });

    grid.innerHTML = html;

    grid.querySelectorAll('input[type="checkbox"]').forEach(chk => {
      chk.addEventListener('change', (e) => {
        const parent = e.target.closest('.speaker-chip');
        if (e.target.checked) {
          parent.classList.add('checked');
        } else {
          parent.classList.remove('checked');
        }
        updateBuilderCode();
      });
    });
  }

  function updateBuilderCode() {
    const text = document.getElementById('builderText')?.value || 'ご飯ができましたよ！みんな集まってください。';
    const checkedBoxes = Array.from(document.querySelectorAll('#builderSpeakersGrid input[type="checkbox"]:checked'));
    const devices = checkedBoxes.map(c => c.value);

    const isTunnel = document.querySelector('input[name="builderUrlType"]:checked')?.value === 'tunnel';
    const tunnelDomain = state.serverInfo?.tunnelDomain;
    const localHost = state.serverInfo?.serverIp || window.location.hostname || 'localhost';
    const localPort = state.serverInfo?.port || window.location.port || 8080;
    const baseUrl = (isTunnel && tunnelDomain)
      ? `https://${tunnelDomain}`
      : `http://${localHost}:${localPort}`;
    const token = document.getElementById('txtWebhookTokenVal')?.value || state.serverInfo?.webhookToken || '';

    const voice = document.getElementById('builderVoice')?.value;
    const rate = document.getElementById('builderRate')?.value;
    const volumeLevel = document.getElementById('builderVolumeLevel')?.value;

    const defaultDevName = state.devices[0]?.name || 'default';
    const payloadObj = {
      text,
      devices: devices.length > 0 ? devices : [defaultDevName]
    };
    if (voice) payloadObj.voice = voice;
    if (rate) payloadObj.rate = rate;
    if (volumeLevel) payloadObj.volumeLevel = parseFloat(volumeLevel);

    const codeEl = document.getElementById('builderGeneratedCode');
    if (!codeEl) return;

    if (builderSelectedTab === 'curl-post') {
      let cmd = `curl -X POST ${baseUrl}/api/say \\\n  -H "Content-Type: application/json" \\\n`;
      if (token) {
        cmd += `  -H "Authorization: Bearer ${token}" \\\n`;
      }
      cmd += `  -d '${JSON.stringify(payloadObj, null, 2)}'`;
      codeEl.textContent = cmd;
    } else if (builderSelectedTab === 'curl-get') {
      const params = new URLSearchParams();
      params.set('text', text);
      if (devices.length > 0) {
        params.set('devices', devices.join(','));
      }
      if (voice) params.set('voice', voice);
      if (rate) params.set('rate', rate);
      if (token) params.set('token', token);
      codeEl.textContent = `curl "${baseUrl}/api/say?${params.toString()}"`;
    } else if (builderSelectedTab === 'json-body') {
      codeEl.textContent = JSON.stringify(payloadObj, null, 2);
    } else if (builderSelectedTab === 'ifttt') {
      let iftttGuide = `【IFTTT "Make a web request" (Webhooks) 設定】\n`;
      iftttGuide += `1. URL:\n   ${baseUrl}/api/say\n\n`;
      iftttGuide += `2. Method:\n   POST\n\n`;
      iftttGuide += `3. Content Type:\n   application/json\n\n`;
      if (token) {
        iftttGuide += `4. Additional Headers:\n   Authorization: Bearer ${token}\n\n`;
      }
      iftttGuide += `5. Body (JSON):\n${JSON.stringify(payloadObj, null, 2)}`;
      codeEl.textContent = iftttGuide;
    }
  }

  function setupWebhookBuilder() {
    // フォーム入力変更リスナー
    const textInput = document.getElementById('builderText');
    const voiceSelect = document.getElementById('builderVoice');
    const rateSelect = document.getElementById('builderRate');
    const volSelect = document.getElementById('builderVolumeLevel');
    const urlRadios = document.querySelectorAll('input[name="builderUrlType"]');

    if (textInput) textInput.addEventListener('input', updateBuilderCode);
    if (voiceSelect) voiceSelect.addEventListener('change', updateBuilderCode);
    if (rateSelect) rateSelect.addEventListener('change', updateBuilderCode);
    if (volSelect) volSelect.addEventListener('change', updateBuilderCode);
    urlRadios.forEach(r => r.addEventListener('change', updateBuilderCode));

    // スピーカー一括選択ボタン
    document.getElementById('btnBuilderSelectAll')?.addEventListener('click', () => {
      document.querySelectorAll('#builderSpeakersGrid input[type="checkbox"]').forEach(c => {
        c.checked = true;
        c.closest('.speaker-chip')?.classList.add('checked');
      });
      updateBuilderCode();
    });
    document.getElementById('btnBuilderSelectGoogle')?.addEventListener('click', () => {
      document.querySelectorAll('#builderSpeakersGrid input[type="checkbox"]').forEach(c => {
        const isMatch = c.getAttribute('data-type') === 'google';
        c.checked = isMatch;
        c.closest('.speaker-chip')?.classList.toggle('checked', isMatch);
      });
      updateBuilderCode();
    });
    document.getElementById('btnBuilderSelectAlexa')?.addEventListener('click', () => {
      document.querySelectorAll('#builderSpeakersGrid input[type="checkbox"]').forEach(c => {
        const isMatch = c.getAttribute('data-type') === 'alexa';
        c.checked = isMatch;
        c.closest('.speaker-chip')?.classList.toggle('checked', isMatch);
      });
      updateBuilderCode();
    });
    document.getElementById('btnBuilderSelectHomePod')?.addEventListener('click', () => {
      document.querySelectorAll('#builderSpeakersGrid input[type="checkbox"]').forEach(c => {
        const isMatch = c.getAttribute('data-type') === 'homepod';
        c.checked = isMatch;
        c.closest('.speaker-chip')?.classList.toggle('checked', isMatch);
      });
      updateBuilderCode();
    });
    document.getElementById('btnBuilderClear')?.addEventListener('click', () => {
      document.querySelectorAll('#builderSpeakersGrid input[type="checkbox"]').forEach(c => {
        c.checked = false;
        c.closest('.speaker-chip')?.classList.remove('checked');
      });
      updateBuilderCode();
    });

    // タブ切り替え
    document.querySelectorAll('.pill-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        builderSelectedTab = btn.getAttribute('data-output-tab');
        updateBuilderCode();
      });
    });

    // トークン表示トグル
    const tokenInput = document.getElementById('txtWebhookTokenVal');
    const btnToggle = document.getElementById('btnToggleTokenVisibility');
    if (btnToggle && tokenInput) {
      btnToggle.addEventListener('click', () => {
        if (tokenInput.type === 'password') {
          tokenInput.type = 'text';
          btnToggle.textContent = '🙈';
        } else {
          tokenInput.type = 'password';
          btnToggle.textContent = '👁️';
        }
      });
    }

    // トークンコピーボタン
    document.getElementById('btnCopyWebhookToken')?.addEventListener('click', () => {
      if (tokenInput && tokenInput.value) {
        navigator.clipboard.writeText(tokenInput.value).then(() => {
          showToast('Webhook 認証トークンをコピーしました！', 'success');
        });
      }
    });

    // トークン保存ボタン
    document.getElementById('btnSaveWebhookToken')?.addEventListener('click', async () => {
      const token = tokenInput ? tokenInput.value.trim() : '';
      try {
        const res = await fetch('/api/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ webhookToken: token })
        });
        if (!res.ok) throw new Error('保存失敗');
        if (state.serverInfo) state.serverInfo.webhookToken = token;
        updateBuilderCode();
        showToast('Webhook 認証トークンを保存しました！', 'success');
      } catch (e) {
        showToast('トークン保存エラー: ' + e.message, 'error');
      }
    });

    // ビルダーコードコピーボタン
    document.getElementById('btnCopyBuilderCode')?.addEventListener('click', () => {
      const codeEl = document.getElementById('builderGeneratedCode');
      if (codeEl) {
        navigator.clipboard.writeText(codeEl.textContent).then(() => {
          showToast('設定/コードをクリップボードにコピーしました！', 'success');
        });
      }
    });

    // その場でテスト送信
    document.getElementById('btnTestWebhookNow')?.addEventListener('click', async () => {
      const text = document.getElementById('builderText')?.value || '';
      if (!text.trim()) {
        return showToast('発言内容を入力してください', 'warning');
      }

      const checked = Array.from(document.querySelectorAll('#builderSpeakersGrid input[type="checkbox"]:checked')).map(c => c.value);
      if (checked.length === 0) {
        return showToast('少なくとも1つのスピーカーを選択してください', 'warning');
      }

      const payload = {
        text,
        devices: checked
      };
      const voice = document.getElementById('builderVoice')?.value;
      if (voice) payload.voice = voice;
      const rate = document.getElementById('builderRate')?.value;
      if (rate) payload.rate = rate;
      const volumeLevel = document.getElementById('builderVolumeLevel')?.value;
      if (volumeLevel) payload.volumeLevel = parseFloat(volumeLevel);

      const statusEl = document.getElementById('testWebhookStatus');
      if (statusEl) {
        statusEl.style.display = 'block';
        statusEl.textContent = 'スピーカーへテスト送信中...';
        statusEl.style.color = '#38bdf8';
      }

      try {
        const res = await fetch('/api/say', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.success) {
          if (statusEl) {
            statusEl.textContent = `✅ テスト送信成功！(${checked.length}台のスピーカーで発話)`;
            statusEl.style.color = 'var(--success)';
          }
          showToast('スピーカーへ発言リクエストを送信しました！', 'success');
        } else {
          throw new Error(data.error || '送信失敗');
        }
      } catch (err) {
        if (statusEl) {
          statusEl.textContent = `❌ エラー: ${err.message}`;
          statusEl.style.color = 'var(--danger)';
        }
        showToast('送信エラー: ' + err.message, 'error');
      }
    });

    // HomePod 再スキャンボタン
    document.getElementById('btnRescanHomePod')?.addEventListener('click', async () => {
      const btn = document.getElementById('btnRescanHomePod');
      btn.disabled = true;
      showToast('HomePod を再スキャンしています...');
      try {
        const res = await fetch('/api/homepod/scan', { method: 'POST' });
        const data = await res.json();
        showToast(`HomePod 再スキャン完了: ${data.count || 0} 台認識`, 'success');
        await loadDevices();
        await loadServerStatus();
      } catch (e) {
        showToast('HomePod スキャンエラー: ' + e.message, 'error');
      } finally {
        btn.disabled = false;
      }
    });
  }

  // ================= 5. Google カレンダー連携 =================
  // カレンダー設定の読み込み
  async function loadCalendarSettings() {
    try {
      const res = await fetch('/api/settings');
      if (!res.ok) return;
      const data = await res.json();
      const cal = data.calendar || {};

      state.calendarData = {
        calendars: Array.isArray(cal.calendars) ? [...cal.calendars] : []
      };

      // 既存の単一 icalUrl からのフォールバック
      if (state.calendarData.calendars.length === 0 && cal.icalUrl) {
        state.calendarData.calendars.push({
          id: 'cal_default',
          name: 'メインカレンダー',
          icalUrl: cal.icalUrl,
          enabled: true
        });
      }

      renderCalendarList();

      const calEnabled = document.getElementById('calEnabled');
      const calEnabledLabel = document.getElementById('calEnabledLabel');
      if (calEnabled) {
        calEnabled.checked = !!cal.enabled;
        if (calEnabledLabel) calEnabledLabel.textContent = cal.enabled ? '有効' : '無効';
      }

      // 直前リマインドの独立スイッチ
      const calRemindEnabled = document.getElementById('calRemindEnabled');
      const calRemindTimingWrapper = document.getElementById('calRemindTimingWrapper');
      if (calRemindEnabled) {
        calRemindEnabled.checked = cal.remindEnabled !== false;
        if (calRemindTimingWrapper) {
          calRemindTimingWrapper.style.opacity = calRemindEnabled.checked ? '1' : '0.4';
          calRemindTimingWrapper.style.pointerEvents = calRemindEnabled.checked ? 'auto' : 'none';
        }
      }

      const calRemindMinutes = document.getElementById('calRemindMinutes');
      if (calRemindMinutes && cal.remindMinutesBefore !== undefined) {
        calRemindMinutes.value = String(cal.remindMinutesBefore);
      }

      // 朝の予定まとめの独立スイッチ
      const calDailySummaryEnabled = document.getElementById('calDailySummaryEnabled');
      const calDailyTimingWrapper = document.getElementById('calDailyTimingWrapper');
      if (calDailySummaryEnabled) {
        calDailySummaryEnabled.checked = cal.dailySummaryEnabled !== false;
        if (calDailyTimingWrapper) {
          calDailyTimingWrapper.style.opacity = calDailySummaryEnabled.checked ? '1' : '0.4';
          calDailyTimingWrapper.style.pointerEvents = calDailySummaryEnabled.checked ? 'auto' : 'none';
        }
      }

      const calDailySummaryTime = document.getElementById('calDailySummaryTime');
      if (calDailySummaryTime && cal.dailySummaryTime) {
        calDailySummaryTime.value = cal.dailySummaryTime;
      }

      const calVoice = document.getElementById('calVoice');
      if (calVoice && cal.voice) calVoice.value = cal.voice;

      renderCalendarSpeakers(cal.targetDevices || ['default']);
    } catch (e) {
      console.warn('カレンダー設定取得エラー:', e);
    }
  }

  // 登録カレンダー一覧の描画
  function renderCalendarList() {
    const container = document.getElementById('calendarListContainer');
    if (!container) return;

    const list = state.calendarData?.calendars || [];
    if (list.length === 0) {
      container.innerHTML = `
        <div style="padding: 12px; background: rgba(255,255,255,0.02); border: 1px dashed var(--card-border); border-radius: var(--radius-sm); text-align: center; color: var(--text-muted); font-size: 0.85rem;">
          登録されたカレンダーはありません。「＋ カレンダーを追加」ボタンから Google カレンダーの iCal URL を登録してください。
        </div>
      `;
      return;
    }

    let html = '';
    list.forEach((c, idx) => {
      const isChecked = c.enabled !== false ? 'checked' : '';
      html += `
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 14px; background: rgba(255,255,255,0.03); border: 1px solid var(--card-border); border-radius: var(--radius-sm);">
          <div style="min-width: 0; flex: 1;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 0.9rem; font-weight: 600; color: var(--text-main);">${escapeHtml(c.name || `カレンダー ${idx + 1}`)}</span>
              ${c.enabled !== false ? '<span style="font-size: 0.68rem; padding: 1px 6px; border-radius: 999px; background: rgba(99,102,241,0.15); color: #818cf8;">同期中</span>' : '<span style="font-size: 0.68rem; padding: 1px 6px; border-radius: 999px; background: rgba(255,255,255,0.08); color: var(--text-muted);">停止中</span>'}
            </div>
            <div style="font-size: 0.78rem; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 380px;" title="${escapeHtml(c.icalUrl)}">
              ${escapeHtml(c.icalUrl)}
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 12px; flex-shrink: 0;">
            <label class="switch" style="width: 36px; height: 20px;">
              <input type="checkbox" class="cal-toggle-item" data-id="${c.id}" ${isChecked}>
              <span class="slider round"></span>
            </label>
            <button type="button" class="btn-icon danger btn-delete-cal" data-id="${c.id}" title="このカレンダーを削除" style="width: 28px; height: 28px;">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // カレンダー個別ON/OFFトグル
    container.querySelectorAll('.cal-toggle-item').forEach(chk => {
      chk.addEventListener('change', (e) => {
        const id = e.target.getAttribute('data-id');
        const found = state.calendarData.calendars.find(c => c.id === id);
        if (found) {
          found.enabled = e.target.checked;
          renderCalendarList();
        }
      });
    });

    // カレンダー削除
    container.querySelectorAll('.btn-delete-cal').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = btn.getAttribute('data-id');
        const found = state.calendarData.calendars.find(c => c.id === id);
        const name = found ? found.name : 'カレンダー';
        if (confirm(`「${name}」を連携リストから削除してもよろしいですか？`)) {
          state.calendarData.calendars = state.calendarData.calendars.filter(c => c.id !== id);
          renderCalendarList();
          showToast(`「${name}」を削除しました（保存ボタンを押すと確定します）`, 'info');
        }
      });
    });
  }

  async function loadCalendarEvents() {
    try {
      const res = await fetch('/api/calendar/events');
      if (!res.ok) return;
      const data = await res.json();
      renderCalendarEvents(data.today || [], data.lastFetched);
    } catch (e) {
      console.warn('カレンダーイベント取得エラー:', e);
    }
  }

  function renderCalendarEvents(events, lastFetched) {
    const listEl = document.getElementById('calEventsList');
    const badgeEl = document.getElementById('calLastSyncBadge');
    if (!listEl) return;

    if (badgeEl && lastFetched) {
      const timeStr = new Date(lastFetched).toLocaleTimeString();
      badgeEl.textContent = `最終同期: ${timeStr}`;
    }

    if (!events || events.length === 0) {
      listEl.innerHTML = `<li class="empty-msg">本日の予定はありません</li>`;
      return;
    }

    let html = '';
    events.forEach(ev => {
      const isAllDay = !!ev.isAllDay;
      let timeText = '終日';
      if (!isAllDay && ev.start) {
        const s = new Date(ev.start);
        const h = String(s.getHours()).padStart(2, '0');
        const m = String(s.getMinutes()).padStart(2, '0');
        timeText = `${h}:${m}`;
      }

      html += `
        <li class="cal-event-item ${isAllDay ? 'allday' : ''}">
          <div class="cal-event-header">
            <span class="cal-event-time">${timeText}</span>
            ${ev.calendarName ? `<span style="font-size:0.7rem; color:var(--text-muted); background:rgba(255,255,255,0.06); padding:1px 6px; border-radius:999px;">${escapeHtml(ev.calendarName)}</span>` : ''}
          </div>
          <div class="cal-event-summary">${escapeHtml(ev.summary || '（無題）')}</div>
          ${ev.location ? `<div class="cal-event-location">📍 ${escapeHtml(ev.location)}</div>` : ''}
        </li>
      `;
    });

    listEl.innerHTML = html;
  }

  function setupCalendarHandlers() {
    // 全体有効/無効スイッチ
    const calEnabled = document.getElementById('calEnabled');
    const calEnabledLabel = document.getElementById('calEnabledLabel');
    if (calEnabled) {
      calEnabled.addEventListener('change', () => {
        if (calEnabledLabel) calEnabledLabel.textContent = calEnabled.checked ? '有効' : '無効';
      });
    }

    // 直前リマインドスイッチ連動
    const calRemindEnabled = document.getElementById('calRemindEnabled');
    const calRemindTimingWrapper = document.getElementById('calRemindTimingWrapper');
    if (calRemindEnabled && calRemindTimingWrapper) {
      calRemindEnabled.addEventListener('change', () => {
        calRemindTimingWrapper.style.opacity = calRemindEnabled.checked ? '1' : '0.4';
        calRemindTimingWrapper.style.pointerEvents = calRemindEnabled.checked ? 'auto' : 'none';
      });
    }

    // 朝まとめスイッチ連動
    const calDailySummaryEnabled = document.getElementById('calDailySummaryEnabled');
    const calDailyTimingWrapper = document.getElementById('calDailyTimingWrapper');
    if (calDailySummaryEnabled && calDailyTimingWrapper) {
      calDailySummaryEnabled.addEventListener('change', () => {
        calDailyTimingWrapper.style.opacity = calDailySummaryEnabled.checked ? '1' : '0.4';
        calDailyTimingWrapper.style.pointerEvents = calDailySummaryEnabled.checked ? 'auto' : 'none';
      });
    }

    // カレンダー追加フォームの開閉
    const btnShowAddCalForm = document.getElementById('btnShowAddCalForm');
    const addCalInlineForm = document.getElementById('addCalInlineForm');
    const btnCancelAddCal = document.getElementById('btnCancelAddCal');
    const btnAddCalConfirm = document.getElementById('btnAddCalConfirm');

    if (btnShowAddCalForm && addCalInlineForm) {
      btnShowAddCalForm.addEventListener('click', () => {
        addCalInlineForm.style.display = addCalInlineForm.style.display === 'none' ? 'block' : 'none';
        if (addCalInlineForm.style.display === 'block') {
          document.getElementById('newCalName')?.focus();
        }
      });
    }

    if (btnCancelAddCal && addCalInlineForm) {
      btnCancelAddCal.addEventListener('click', () => {
        addCalInlineForm.style.display = 'none';
        document.getElementById('newCalName').value = '';
        document.getElementById('newCalUrl').value = '';
      });
    }

    // カレンダー追加の確定
    if (btnAddCalConfirm) {
      btnAddCalConfirm.addEventListener('click', () => {
        const nameInput = document.getElementById('newCalName');
        const urlInput = document.getElementById('newCalUrl');
        const name = nameInput?.value.trim() || 'カレンダー';
        const url = urlInput?.value.trim() || '';

        if (!url) {
          showToast('Google カレンダーの iCal URL を入力してください', 'error');
          urlInput?.focus();
          return;
        }

        if (!url.startsWith('http://') && !url.startsWith('https://')) {
          showToast('URLは http:// または https:// から始まる必要があります', 'error');
          urlInput?.focus();
          return;
        }

        if (!state.calendarData) state.calendarData = { calendars: [] };
        if (!state.calendarData.calendars) state.calendarData.calendars = [];

        state.calendarData.calendars.push({
          id: 'cal_' + Date.now(),
          name,
          icalUrl: url,
          enabled: true
        });

        renderCalendarList();
        addCalInlineForm.style.display = 'none';
        nameInput.value = '';
        urlInput.value = '';
        showToast(`「${name}」を追加しました！「設定を保存」ボタンを押すと確定します`, 'success');
      });
    }

    // カレンダー設定保存
    const calForm = document.getElementById('calendarSettingsForm');
    if (calForm) {
      calForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const calSpeakers = getSelectedSpeakers(document.getElementById('calSpeakersContainer'));
        const calendars = state.calendarData?.calendars || [];

        const payload = {
          calendar: {
            enabled: document.getElementById('calEnabled')?.checked || false,
            calendars,
            icalUrl: calendars[0]?.icalUrl || '', // 互換性維持用
            remindEnabled: document.getElementById('calRemindEnabled')?.checked !== false,
            remindMinutesBefore: parseInt(document.getElementById('calRemindMinutes')?.value || '10', 10),
            dailySummaryEnabled: document.getElementById('calDailySummaryEnabled')?.checked !== false,
            dailySummaryTime: document.getElementById('calDailySummaryTime')?.value || '07:30',
            targetDevices: calSpeakers.length ? calSpeakers : ['default'],
            voice: document.getElementById('calVoice')?.value || 'ja-JP-NanamiNeural'
          }
        };

        try {
          const res = await fetch('/api/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          if (!res.ok) throw new Error('保存失敗');
          showToast('Google カレンダー連携設定を保存しました！', 'success');
          await loadCalendarEvents();
        } catch (err) {
          showToast('設定保存エラー: ' + err.message, 'error');
        }
      });
    }

    // 手動同期ボタン
    document.getElementById('btnSyncCalendar')?.addEventListener('click', async () => {
      const btn = document.getElementById('btnSyncCalendar');
      btn.disabled = true;
      showToast('Google カレンダーと同期しています...');
      try {
        const res = await fetch('/api/calendar/sync', { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
          showToast(`カレンダー同期完了: 合計 ${data.count || 0} 件の予定を取得`, 'success');
          await loadCalendarEvents();
        } else {
          throw new Error(data.error || '同期失敗');
        }
      } catch (err) {
        showToast('同期エラー: ' + err.message, 'error');
      } finally {
        btn.disabled = false;
      }
    });

    // 朝のまとめ読み上げテスト
    document.getElementById('btnTestDailySummary')?.addEventListener('click', async () => {
      const btn = document.getElementById('btnTestDailySummary');
      btn.disabled = true;
      showToast('朝の予定サマリーをスピーカーへ送信中...');
      try {
        const res = await fetch('/api/calendar/summary', { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.success) {
          showToast('朝の予定まとめアナウンスを実行しました！', 'success');
        } else {
          throw new Error(data.error || '実行失敗');
        }
      } catch (err) {
        showToast('テスト発声エラー: ' + err.message, 'error');
      } finally {
        btn.disabled = false;
      }
    });
  }

  // ================= 6. ユーティリティ =================
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
