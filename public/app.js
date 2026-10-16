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
    history: [],
    historyFilter: 'all',
    historySearch: ''
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
    // サブタブ (スケジュール・カレンダー)
    subTabBtns: document.querySelectorAll('.sub-tab-btn'),
    subTabPanes: document.querySelectorAll('.sub-tab-pane'),
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
    sayVolumeRange: document.getElementById('sayVolumeRange'),
    sayVolumeDisplay: document.getElementById('sayVolumeDisplay'),
    btnPreviewAudio: document.getElementById('btnPreviewAudio'),
    btnSpeakDirect: document.getElementById('btnSpeakDirect'),
    audioPreviewWrapper: document.getElementById('audioPreviewWrapper'),
    audioPreviewPlayer: document.getElementById('audioPreviewPlayer'),
    presetBtns: document.querySelectorAll('.preset-btn'),
    btnGoToHistoryTab: document.getElementById('btnGoToHistoryTab'),
    // 発言履歴 (過去100件)
    tabHistoryCount: document.getElementById('tabHistoryCount'),
    historyCounterBadge: document.getElementById('historyCounterBadge'),
    fullHistoryContainer: document.getElementById('fullHistoryContainer'),
    historyFilterGroup: document.getElementById('historyFilterGroup'),
    historySearchInput: document.getElementById('historySearchInput'),
    btnReloadHistory: document.getElementById('btnReloadHistory'),
    btnClearFullHistory: document.getElementById('btnClearFullHistory'),
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
    schedVolumeRange: document.getElementById('schedVolumeRange'),
    schedVolumeDisplay: document.getElementById('schedVolumeDisplay'),
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
    setupDndHandlers();
    setupSettingsHandlers();
    setupAiHandlers();
    await loadServerStatus();
    await Promise.all([
      loadDevices(),
      loadVoices(),
      loadSchedules(),
      loadHistory(),
      loadAlexaStatus(),
      loadCalendarSettings(),
      loadCalendarEvents(),
      loadDndStatus(),
      loadDndSettings(),
      loadDndHistory(),
      loadSettings(),
      loadAiSettings()
    ]);

    // DND ステータスを定期ポーリング (15秒ごと)
    setInterval(loadDndStatus, 15000);
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

  // デバイスのカテゴリ優先度判定:
  // 1: Group GH (Google Home グループ)
  // 2: Group Alexa (Alexa グループ)
  // 3: Group Homepod (HomePod グループ)
  // 4: GH (単体 Google Home)
  // 5: Alexa (単体 Alexa)
  // 6: Homepod (単体 HomePod)
  function getDeviceCategoryOrder(dev) {
    const type = (dev.type || 'google').toLowerCase();
    const name = (dev.name || '').toLowerCase();
    const model = (dev.model || '').toLowerCase();
    const ip = (dev.ip || '').toLowerCase();

    const isGroup = !!dev.isGroup ||
      ip.endsWith(':all') ||
      model.includes('group') ||
      model.includes('グループ') ||
      name.includes('全室') ||
      name.includes('グループ');

    if (isGroup) {
      if (type === 'google') return 1; // Group GH
      if (type === 'alexa') return 2;  // Group Alexa
      if (type === 'homepod') return 3;// Group HomePod
      return 1;
    } else {
      if (type === 'google') return 4; // GH
      if (type === 'alexa') return 5;  // Alexa
      if (type === 'homepod') return 6;// HomePod
      return 4;
    }
  }

  function sortDevicesList(devices) {
    const defaultIp = (state.serverInfo && state.serverInfo.defaultDeviceIp) || '';
    return [...devices].sort((a, b) => {
      const orderA = getDeviceCategoryOrder(a);
      const orderB = getDeviceCategoryOrder(b);
      if (orderA !== orderB) return orderA - orderB;
      const isDefA = a.ip === defaultIp || a.isDefault;
      const isDefB = b.ip === defaultIp || b.isDefault;
      if (isDefA && !isDefB) return -1;
      if (!isDefA && isDefB) return 1;
      return (a.name || '').localeCompare(b.name || '', 'ja');
    });
  }

  // デバイス一覧
  async function loadDevices() {
    try {
      const res = await fetch('/api/devices');
      if (!res.ok) throw new Error('デバイス取得失敗');
      const data = await res.json();
      state.devices = sortDevicesList(data.devices || []);

      const initialSelected = state.serverInfo?.defaultDeviceIp
        ? [state.serverInfo.defaultDeviceIp]
        : (state.devices[0] ? [state.devices[0].ip] : []);

      renderSpeakersCheckboxes(el.saySpeakersContainer, 'saySpeaker', initialSelected);
      renderSpeakersCheckboxes(el.schedSpeakersContainer, 'schedSpeaker', ['default']);
      renderCalendarSpeakers();
      renderDndSpeakers();
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

      renderScheduleTable();
    } catch (err) {
      showToast('スケジュールの取得に失敗しました', 'error');
    }
  }

  // 発言履歴一覧の取得 (直近100件)
  async function loadHistory() {
    try {
      const res = await fetch('/api/history?limit=100');
      if (!res.ok) throw new Error('発言履歴取得失敗');
      const data = await res.json();
      state.history = data.history || [];

      renderFullHistory();
      updateHistoryBadges();
    } catch (err) {
      console.warn('発言履歴の取得に失敗:', err.message);
    }
  }

  function updateHistoryBadges() {
    const count = (state.history || []).length;
    if (el.tabHistoryCount) el.tabHistoryCount.textContent = count;
    if (el.historyCounterBadge) el.historyCounterBadge.textContent = `${count} / 100 件`;
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
      const catOrder = getDeviceCategoryOrder(dev);
      const isGroup = catOrder <= 3;
      const isDefault = dev.ip === defaultIp;
      const isAlexa = dev.type === 'alexa' || dev.ip.startsWith('alexa:');
      const isHomePod = dev.type === 'homepod' || dev.ip.startsWith('homepod:');
      const chipClass = isAlexa ? 'alexa-chip' : (isHomePod ? 'homepod-chip' : 'google-chip');
      const displayName = formatSpeakerDisplayName(dev.name);

      let badgeHtml = '';
      if (isDefault) {
        badgeHtml += '<span class="speaker-chip-badge default-badge" title="標準スピーカー">★</span>';
      }
      if (isGroup) {
        if (isAlexa) {
          badgeHtml += '<span class="speaker-chip-badge" style="background:rgba(16,185,129,0.2);color:#34d399;border:1px solid rgba(16,185,129,0.4);font-weight:600;">👥 Echo Group</span>';
        } else if (isHomePod) {
          badgeHtml += '<span class="speaker-chip-badge" style="background:rgba(236,72,153,0.2);color:#f472b6;border:1px solid rgba(236,72,153,0.4);font-weight:600;">👥 HomePod Group</span>';
        } else {
          badgeHtml += '<span class="speaker-chip-badge" style="background:rgba(66,133,244,0.2);color:#93c5fd;border:1px solid rgba(66,133,244,0.4);font-weight:600;">👥 Cast Group</span>';
        }
      } else {
        if (isAlexa) {
          badgeHtml += '<span class="speaker-chip-badge alexa-badge">Echo</span>';
        } else if (isHomePod) {
          badgeHtml += '<span class="speaker-chip-badge homepod-badge">HomePod</span>';
        } else {
          badgeHtml += '<span class="speaker-chip-badge google-badge">Google Home</span>';
        }
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
      const volBadge = sched.volumeLevel 
        ? `<span class="badge-tech" style="font-size:0.68rem; padding:1px 6px; color:#34d399; border-color:rgba(52,211,153,0.3); margin-left:6px;" title="個別音量: ${Math.round(parseFloat(sched.volumeLevel) * 100)}%">🔉 ${Math.round(parseFloat(sched.volumeLevel) * 100)}%</span>` 
        : '';

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
          <td><span style="font-size:0.85rem; color:var(--text-muted);">${escapeHtml(devNames)}</span>${volBadge}</td>
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
      const catOrder = getDeviceCategoryOrder(dev);
      const isGroup = catOrder <= 3;
      const isAlexa = dev.type === 'alexa' || dev.ip.startsWith('alexa:');
      const isHomePod = dev.type === 'homepod' || dev.ip.startsWith('homepod:');
      const displayName = formatSpeakerDisplayName(dev.name);

      let groupBadge = '';
      if (isGroup) {
        if (isAlexa) {
          groupBadge = '<span class="device-tag alexa" style="background:rgba(16,185,129,0.22);color:#34d399;border:1px solid rgba(16,185,129,0.4);font-size:0.7rem;padding:2px 6px;font-weight:600;">👥 Echo グループ</span>';
        } else if (isHomePod) {
          groupBadge = '<span class="device-tag homepod" style="background:rgba(236,72,153,0.22);color:#f472b6;border:1px solid rgba(236,72,153,0.4);font-size:0.7rem;padding:2px 6px;font-weight:600;">👥 HomePod グループ</span>';
        } else {
          groupBadge = '<span class="device-tag google" style="background:rgba(66,133,244,0.22);color:#93c5fd;border:1px solid rgba(66,133,244,0.4);font-size:0.7rem;padding:2px 6px;font-weight:600;">👥 Cast グループ</span>';
        }
      }

      cardsHtml += `
        <div class="device-card ${isDef ? 'default-dev' : ''} ${isAlexa ? 'alexa-dev' : ''} ${isHomePod ? 'homepod-dev' : ''}" style="${isDef ? 'border-color: rgba(245, 158, 11, 0.4); box-shadow: 0 0 15px rgba(245, 158, 11, 0.1);' : ''}">
          <div class="device-card-header" style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
            <div style="min-width:0;flex:1;">
              <span class="device-card-title" style="font-size:1.05rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;">${escapeHtml(displayName)}</span>
            </div>
            <div style="display:flex;gap:4px;flex-shrink:0;align-items:center;">
              ${isDef ? '<span class="device-tag default" style="background:rgba(245,158,11,0.15);color:#fbbf24;border:1px solid rgba(245,158,11,0.3);font-size:0.7rem;padding:2px 6px;">★ 標準</span>' : ''}
              ${isGroup ? groupBadge : `
                ${!isAlexa && !isHomePod ? '<span class="device-tag google" style="background:rgba(66,133,244,0.15);color:#8ab4f8;border:1px solid rgba(66,133,244,0.3);font-size:0.7rem;padding:2px 6px;">Google Home</span>' : ''}
                ${isAlexa ? '<span class="device-tag alexa" style="font-size:0.7rem;padding:2px 6px;">Echo</span>' : ''}
                ${isHomePod ? '<span class="device-tag homepod" style="font-size:0.7rem;padding:2px 6px;">HomePod</span>' : ''}
              `}
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

  function renderFullHistory() {
    if (!el.fullHistoryContainer) return;

    let items = state.history || [];

    // フィルター適用
    if (state.historyFilter && state.historyFilter !== 'all') {
      items = items.filter(item => {
        if (state.historyFilter === 'api') {
          return item.source === 'api' || item.source === 'tunnel_webhook';
        }
        return item.source === state.historyFilter;
      });
    }

    // 検索語句適用
    if (state.historySearch) {
      const q = state.historySearch.toLowerCase();
      items = items.filter(item => {
        const textMatch = (item.text || '').toLowerCase().includes(q);
        const sourceMatch = (item.sourceLabel || '').toLowerCase().includes(q);
        const targetsMatch = Array.isArray(item.targets) 
          ? item.targets.some(t => String(t).toLowerCase().includes(q))
          : false;
        return textMatch || sourceMatch || targetsMatch;
      });
    }

    if (!items.length) {
      el.fullHistoryContainer.innerHTML = `<div class="empty-msg">条件に一致する発言履歴はありません</div>`;
      return;
    }

    let html = '';
    items.forEach(item => {
      // 日時フォーマット (YYYY/MM/DD HH:mm:ss)
      const date = item.timestamp ? new Date(item.timestamp) : new Date();
      const timeStr = date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });

      // 相対時間
      const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
      let relativeTime = '';
      if (diffSec < 60) relativeTime = `${Math.max(1, diffSec)}秒前`;
      else if (diffSec < 3600) relativeTime = `${Math.floor(diffSec / 60)}分前`;
      else if (diffSec < 86400) relativeTime = `${Math.floor(diffSec / 3600)}時間前`;
      else relativeTime = `${Math.floor(diffSec / 86400)}日前`;

      // 送信元バッジ (通信経路)
      const sourceClass = `source-${item.source || 'api'}`;
      const sourceText = escapeHtml(item.sourceLabel || item.source || '不明');

      // IPエイリアスの登録判定 (登録済みエイリアス名を取得)
      const ipAliasName = (item.clientIp && state.ipAliases && state.ipAliases[item.clientIp]) ||
                          (item.clientIp && state.settings?.ipAliases && state.settings.ipAliases[item.clientIp]) ||
                          item.ipAlias ||
                          '';

      // 送信元クライアント（From）バッジ: Discord, IFTTT, Slack等の独立表示
      let effectiveClientName = item.clientName || '';
      if (!effectiveClientName && ipAliasName) {
        effectiveClientName = ipAliasName;
      }

      let clientBadgeHtml = '';
      if (effectiveClientName && effectiveClientName !== item.clientIp) {
        let icon = '🤖';
        const cLower = effectiveClientName.toLowerCase();
        if (cLower.includes('discord')) icon = '🎮';
        else if (cLower.includes('ifttt')) icon = '⚡';
        else if (cLower.includes('slack')) icon = '💬';
        else if (cLower.includes('line')) icon = '🟢';
        else if (cLower.includes('home assistant') || cLower.includes('ha')) icon = '🏠';
        else if (effectiveClientName === 'Web UI') icon = '🖥️';
        else icon = '👤';

        clientBadgeHtml = `<span class="history-from-badge" title="送信元クライアント: ${escapeHtml(effectiveClientName)}">${icon} From: <strong>${escapeHtml(effectiveClientName)}</strong></span>`;
      }

      // ステータスバッジ
      let statusBadgeHtml = '';
      let statusClass = 'status-success';
      if (item.status === 'suppressed') {
        statusClass = 'status-suppressed';
        statusBadgeHtml = `<span class="history-status-badge status-suppressed">🌙 DNDサイレント</span>`;
      } else if (item.status === 'queued') {
        statusClass = 'status-dnd-queued';
        statusBadgeHtml = `<span class="history-status-badge status-dnd-queued">🕒 DND保留中</span>`;
      } else if (item.status === 'error') {
        statusClass = 'status-error';
        statusBadgeHtml = `<span class="history-status-badge status-error">❌ 送信失敗</span>`;
      } else if (item.status === 'partial') {
        statusClass = 'status-partial';
        statusBadgeHtml = `<span class="history-status-badge status-partial">⚠️ 一部送信</span>`;
      } else {
        statusBadgeHtml = `<span class="history-status-badge status-success">✓ 送信成功</span>`;
      }

      // DND保留再生バッジ (右上の送信成功の左に配置)
      const dndQueuedBadgeHtml = item.wasQueued
        ? `<span class="history-status-badge status-dnd-queued" title="DND (おやすみ・会議モード) 中に保留され、解除後に自動再生されました">🕒 DND保留再生</span>`
        : '';

      // 送信元IPタグ
      // 【ユーザー要望】エイリアス登録済みの場合はLink(ボタン)化せず、通常の非リンクタグとして表示する！
      // 未登録のIPのみエイリアス登録画面へのジャンプボタンとする。
      let clientIpTag = '';
      if (item.clientIp) {
        const isAliased = !!ipAliasName || (effectiveClientName && effectiveClientName !== item.clientIp && effectiveClientName !== 'Web UI');
        if (isAliased) {
          // エイリアス登録済みの場合はリンク化しない (通常のテキストタグ)
          const aliasTooltip = ipAliasName ? ` (エイリアス: ${escapeHtml(ipAliasName)})` : '';
          clientIpTag = `<span class="history-ip-tag" title="送信元 IP: ${escapeHtml(item.clientIp)}${aliasTooltip}">IP: ${escapeHtml(item.clientIp)}</span>`;
        } else {
          // 未登録IPのみクリック可能な登録ボタン化
          clientIpTag = `<button type="button" class="history-ip-tag btn-ip-alias-jump" data-ip="${escapeHtml(item.clientIp)}" title="未登録のIPです。クリックして「${escapeHtml(item.clientIp)}」の表示名エイリアスを登録">
            <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 2px;"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
            IP: ${escapeHtml(item.clientIp)}
          </button>`;
        }
      }

      // 送信先スピーカー表示
      const targetsList = Array.isArray(item.targets) ? item.targets : (item.targets ? [item.targets] : ['デフォルト']);
      const targetsHtml = targetsList.map(t => `<span class="speaker-tag">${escapeHtml(formatSpeakerDisplayName(t))}</span>`).join(' ');

      // 音声オプション
      const voiceName = (item.voice || '').replace('ja-JP-', '').replace('Neural', '') || '七海';
      const speechOptions = `${voiceName}${item.urgent ? ' | 🚨緊急' : ''}`;

      html += `
        <div class="history-card-item ${statusClass}" data-id="${escapeHtml(item.id || '')}">
          <div class="history-card-top">
            <div class="history-meta-group">
              <span class="source-badge ${sourceClass}" title="${item.clientIp ? `送信元 IP: ${escapeHtml(item.clientIp)}` : ''}">
                <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>
                ${sourceText}
              </span>
              ${clientBadgeHtml}
              ${clientIpTag}
              <span class="history-time" title="${timeStr}">${relativeTime} (${timeStr})</span>
            </div>
            <div class="history-status-group" style="display: flex; align-items: center; gap: 6px;">
              ${dndQueuedBadgeHtml}
              ${statusBadgeHtml}
            </div>
          </div>

          <div class="history-card-body">
            ${escapeHtml(item.text)}
          </div>

          <div class="history-card-footer">
            <div class="history-targets-info">
              <span>送信先:</span>
              ${targetsHtml}
              <span style="color: var(--text-muted); margin-left: 6px;">[${escapeHtml(speechOptions)}]</span>
            </div>
            <div class="history-actions">
              <button type="button" class="btn-history-action btn-copy-hist" data-text="${escapeHtml(item.text)}" title="発言内容をコピー">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
                コピー
              </button>
              <button type="button" class="btn-history-action btn-preview-hist" data-text="${escapeHtml(item.text)}" data-voice="${escapeHtml(item.voice || '')}" title="ブラウザで試聴">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                試聴
              </button>
              <button type="button" class="btn-history-action btn-repeat" data-text="${escapeHtml(item.text)}" data-voice="${escapeHtml(item.voice || '')}" data-targets='${escapeHtml(JSON.stringify(targetsList))}' title="このテキストで再発言">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
                再発言
              </button>
            </div>
          </div>
        </div>
      `;
    });

    el.fullHistoryContainer.innerHTML = html;

    // 未登録IPボタンのクリックリスナー (設定画面へ遷移＆IP自動セット)
    el.fullHistoryContainer.querySelectorAll('.btn-ip-alias-jump').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const ip = btn.getAttribute('data-ip');
        if (!ip) return;

        // 各種設定タブへ切り替え & 機能拡張サブタブを開く
        document.getElementById('btnTabSettings')?.click();
        document.getElementById('btnSubtabSettingsFeatures')?.click();

        // エイリアス登録欄へ値をセットしてスクロール＆フォーカス
        setTimeout(() => {
          const inputIp = document.getElementById('inputNewAliasIp');
          const inputName = document.getElementById('inputNewAliasName');
          if (inputIp) {
            inputIp.value = ip;
            inputIp.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
          if (inputName) {
            inputName.focus();
          }
        }, 150);

        showToast(`IP「${ip}」のエイリアス登録欄を開きました`, 'info');
      });
    });
  }

  function renderHistoryList() {
    renderFullHistory();
  }

  // ================= 3. イベントリスナー =================
  function setupEventListeners() {
    // メインタブ切り替え
    el.tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        el.tabBtns.forEach(b => b.classList.remove('active'));
        el.tabPanes.forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const targetId = btn.getAttribute('data-tab');
        document.getElementById(targetId)?.classList.add('active');

        // 発言履歴タブを開いた時は最新の履歴を再取得
        if (targetId === 'tab-history') {
          loadHistory();
        } else if (targetId === 'tab-settings') {
          loadSettings();
          loadDndStatus();
          loadTunnelStatus();
        }
      });
    });

    // サブタブ切り替え (親タブ単位で独立して動作)
    document.querySelectorAll('.sub-tab-nav').forEach(nav => {
      const container = nav.closest('.tab-pane') || nav.parentElement;
      const btns = nav.querySelectorAll('.sub-tab-btn');
      btns.forEach(btn => {
        btn.addEventListener('click', () => {
          btns.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const subtabId = btn.getAttribute('data-subtab');
          if (container) {
            container.querySelectorAll('.sub-tab-pane').forEach(p => p.classList.remove('active'));
          }
          if (subtabId) {
            document.getElementById(subtabId)?.classList.add('active');
          }
        });
      });
    });

    // 即時発言画面から発言履歴タブへのクイック遷移
    el.btnGoToHistoryTab?.addEventListener('click', () => {
      document.getElementById('btnTabHistory')?.click();
    });

    // ヘッダーの DND チップクリックで 設定 > DND サブタブへ移動
    document.getElementById('headerDndChip')?.addEventListener('click', () => {
      document.getElementById('btnTabSettings')?.click();
      document.getElementById('btnSubtabSettingsDnd')?.click();
    });

    // 互換性ハンドラー: 他の場所から旧ボタンIDが呼ばれた場合に対応
    document.getElementById('btnTabDnd')?.addEventListener('click', () => {
      document.getElementById('btnTabSettings')?.click();
      document.getElementById('btnSubtabSettingsDnd')?.click();
    });
    document.getElementById('btnTabWebhook')?.addEventListener('click', () => {
      document.getElementById('btnTabSettings')?.click();
      document.getElementById('btnSubtabSettingsWebhook')?.click();
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

    // 音量スライダー (即時発言)
    el.sayVolumeRange?.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      if (el.sayVolumeDisplay) {
        el.sayVolumeDisplay.textContent = val === 0 ? '端末音量を維持' : `${val}%`;
      }
    });

    // スライダー値表示 (スケジュールモーダル)
    el.schedVolumeRange?.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      if (el.schedVolumeDisplay) {
        el.schedVolumeDisplay.textContent = val === 0 ? '全体設定に従う' : `${val}%`;
      }
    });

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
        const volVal = parseInt(el.sayVolumeRange?.value || '0', 10);
        el.audioPreviewPlayer.volume = volVal > 0 ? (volVal / 100) : 1.0;
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
        const urgent = document.getElementById('sayUrgentCheck')?.checked || false;
        const volVal = parseInt(el.sayVolumeRange?.value || '0', 10);

        const payload = {
          text,
          devices: selectedSpeakers,
          voice,
          rate,
          pitch,
          urgent,
          bypassDnd: urgent
        };
        if (volVal > 0) {
          payload.volumeLevel = volVal / 100;
        }

        const res = await fetch('/api/say', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.error || '送信失敗');
        }

        const data = await res.json();
        if (data.dndSuppressed) {
          showToast('【DND発動中】おやすみ・会議モード中のため発話を抑制しました', 'info');
          loadDndHistory();
        } else {
          const successCount = data.results?.filter(r => r.status === 'success').length || 0;
          showToast(`${selectedSpeakers.length} 台のスピーカーへ送信完了 (${successCount} 台成功)！`, 'success');
        }

        // 最新の発言履歴を取得同期
        loadHistory();
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
            body: JSON.stringify({
              text,
              devices: [ip],
              source: 'quick_test',
              sourceLabel: `テスト発声 (${name})`
            })
          });
          if (!res.ok) throw new Error('送信失敗');
          showToast(`${name} にテスト音声を送信しました！`, 'success');
          loadHistory();
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

        // 音量の反映
        const volVal = sched.volumeLevel ? Math.round(parseFloat(sched.volumeLevel) * 100) : 0;
        if (el.schedVolumeRange) el.schedVolumeRange.value = volVal;
        if (el.schedVolumeDisplay) el.schedVolumeDisplay.textContent = volVal > 0 ? `${volVal}%` : '全体設定に従う';

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

    // 履歴 送信元フィルター
    document.querySelectorAll('.history-filter-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.history-filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        state.historyFilter = pill.getAttribute('data-filter') || 'all';
        renderFullHistory();
      });
    });

    // 履歴 リアルタイム検索
    el.historySearchInput?.addEventListener('input', (e) => {
      state.historySearch = e.target.value.trim();
      renderFullHistory();
    });

    // 履歴 手動再読み込み
    el.btnReloadHistory?.addEventListener('click', async () => {
      await loadHistory();
      showToast('発言履歴を最新に更新しました', 'info');
    });

    // 履歴 全件クリア
    el.btnClearFullHistory?.addEventListener('click', async () => {
      if (confirm('過去100件の発言履歴をすべて消去しますか？')) {
        try {
          const res = await fetch('/api/history', { method: 'DELETE' });
          if (!res.ok) throw new Error('クリア処理に失敗しました');
          state.history = [];
          renderFullHistory();
          updateHistoryBadges();
          showToast('発言履歴をすべてクリアしました', 'success');
        } catch (err) {
          showToast('履歴クリア失敗: ' + err.message, 'error');
        }
      }
    });

    // 履歴カード内アクション (イベント委譲: コピー、試聴、再発言)
    el.fullHistoryContainer?.addEventListener('click', async (e) => {
      // 1. コピーボタン
      const copyBtn = e.target.closest('.btn-copy-hist');
      if (copyBtn) {
        const text = copyBtn.getAttribute('data-text') || '';
        try {
          await navigator.clipboard.writeText(text);
          showToast('発言テキストをクリップボードにコピーしました', 'success');
        } catch (err) {
          showToast('コピーに失敗しました', 'error');
        }
        return;
      }

      // 2. 試聴ボタン
      const previewBtn = e.target.closest('.btn-preview-hist');
      if (previewBtn) {
        const text = previewBtn.getAttribute('data-text') || '';
        const voice = previewBtn.getAttribute('data-voice') || '';
        playHistoryPreview(text, voice, previewBtn);
        return;
      }

      // 3. 再発言ボタン
      const repeatBtn = e.target.closest('.btn-repeat');
      if (repeatBtn) {
        const text = repeatBtn.getAttribute('data-text') || '';
        const voice = repeatBtn.getAttribute('data-voice') || '';
        let targets = [];
        try {
          targets = JSON.parse(repeatBtn.getAttribute('data-targets') || '[]');
        } catch (_) {}

        // 即時発言タブへ切り替え
        document.getElementById('btnTabSay')?.click();

        // フォームへ反映
        if (el.sayTextInput) {
          el.sayTextInput.value = text;
          el.sayTextInput.focus();
        }
        if (voice && el.sayVoiceSelect) {
          el.sayVoiceSelect.value = voice;
        }

        // スピーカー選択の復元
        if (Array.isArray(targets) && targets.length && el.saySpeakersContainer) {
          const checkboxes = el.saySpeakersContainer.querySelectorAll('input[type="checkbox"]');
          let matchedAny = false;
          checkboxes.forEach(cb => {
            const devName = cb.getAttribute('data-name') || '';
            const devIp = cb.value;
            const isMatch = targets.some(t => t === devIp || t === devName || (t && devName && devName.includes(t)));
            if (isMatch) {
              cb.checked = true;
              cb.closest('.speaker-chip')?.classList.add('checked');
              matchedAny = true;
            } else {
              cb.checked = false;
              cb.closest('.speaker-chip')?.classList.remove('checked');
            }
          });
          if (!matchedAny) {
            checkboxes.forEach(cb => {
              cb.checked = true;
              cb.closest('.speaker-chip')?.classList.add('checked');
            });
          }
        }

        showToast('発言内容を即時発言フォームにセットしました', 'info');
        return;
      }
    });

    // モーダル操作
    el.btnOpenNewScheduleModal.addEventListener('click', () => {
      document.getElementById('schedEditId').value = '';
      document.getElementById('modalTitle').textContent = '新規スケジュール登録';
      el.scheduleForm.reset();
      el.schedTime.value = '07:00';
      if (el.schedVolumeRange) el.schedVolumeRange.value = 0;
      if (el.schedVolumeDisplay) el.schedVolumeDisplay.textContent = '全体設定に従う';
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

      const volVal = parseInt(el.schedVolumeRange?.value || '0', 10);
      const volumeLevel = volVal > 0 ? (volVal / 100).toString() : '';
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
        volumeLevel,
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
  let builderMacroTarget = null; // 'ALL' | 'GH:ALL' | 'AL:ALL' | 'HP:ALL' | null

  function clearMacroButtons() {
    builderMacroTarget = null;
    document.querySelectorAll('.btn-macro').forEach(b => b.classList.remove('active'));
  }

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
        // 個別チェック操作されたらマクロ指定は解除
        clearMacroButtons();
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
    const fromVal = document.getElementById('builderFrom')?.value.trim() || '';

    // 送信先デバイス: 短縮マクロ指定がある場合はそれを優先 (URL/コマンドが短縮される)
    let devices = [];
    if (builderMacroTarget) {
      devices = [builderMacroTarget];
    } else {
      const checkedBoxes = Array.from(document.querySelectorAll('#builderSpeakersGrid input[type="checkbox"]:checked'));
      devices = checkedBoxes.map(c => c.value);
    }

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
    const chime = document.getElementById('builderChime')?.value;

    const defaultDevName = state.devices[0]?.name || 'default';
    const payloadObj = {
      text,
      devices: devices.length > 0 ? devices : [defaultDevName]
    };
    if (fromVal) payloadObj.from = fromVal;
    if (voice) payloadObj.voice = voice;
    if (rate) payloadObj.rate = rate;
    if (volumeLevel) payloadObj.volumeLevel = parseFloat(volumeLevel);
    if (chime) payloadObj.chime = chime;

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
      if (fromVal) params.set('from', fromVal);
      if (chime) params.set('chime', chime);
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

  // ビルダー内のカスタム部屋グループチップを描画
  function renderBuilderCustomGroupChips() {
    const container = document.getElementById('builderCustomGroupChips');
    if (!container) return;

    const groups = state.settings?.deviceGroups || {};
    const groupNames = Object.keys(groups);
    if (!groupNames.length) {
      container.innerHTML = '';
      return;
    }

    container.innerHTML = groupNames.map(grp => `
      <button type="button" class="btn-chip btn-macro btn-custom-group" data-macro="${escapeHtml(grp)}" title="登録グループ [${escapeHtml(grp)}] へ一括送信 (devices: [&quot;${escapeHtml(grp)}&quot;])">
        ⚡ ${escapeHtml(grp)}
      </button>
    `).join('');

    // クリックイベントの紐付け
    container.querySelectorAll('.btn-custom-group').forEach(btn => {
      btn.addEventListener('click', () => {
        const macro = btn.getAttribute('data-macro');
        const isAlreadyActive = (builderMacroTarget === macro);

        clearMacroButtons();

        if (!isAlreadyActive) {
          btn.classList.add('active');
          builderMacroTarget = macro;

          const memberNames = (groups[macro] || []).map(m => String(m).toLowerCase());
          document.querySelectorAll('#builderSpeakersGrid input[type="checkbox"]').forEach(c => {
            const devName = (c.closest('.speaker-chip')?.textContent || '').toLowerCase();
            const devIp = c.value.toLowerCase();
            const match = memberNames.some(m => devName.includes(m) || devIp.includes(m));
            c.checked = match;
            c.closest('.speaker-chip')?.classList.toggle('checked', match);
          });
        }
        updateBuilderCode();
      });
    });
  }

  function setupWebhookBuilder() {
    // フォーム入力変更リスナー
    const textInput = document.getElementById('builderText');
    const fromInput = document.getElementById('builderFrom');
    const voiceSelect = document.getElementById('builderVoice');
    const rateSelect = document.getElementById('builderRate');
    const volSelect = document.getElementById('builderVolumeLevel');
    const chimeSelect = document.getElementById('builderChime');
    const urlRadios = document.querySelectorAll('input[name="builderUrlType"]');

    if (textInput) textInput.addEventListener('input', updateBuilderCode);
    if (fromInput) fromInput.addEventListener('input', updateBuilderCode);
    if (voiceSelect) voiceSelect.addEventListener('change', updateBuilderCode);
    if (rateSelect) rateSelect.addEventListener('change', updateBuilderCode);
    if (volSelect) volSelect.addEventListener('change', updateBuilderCode);
    if (chimeSelect) chimeSelect.addEventListener('change', updateBuilderCode);
    urlRadios.forEach(r => r.addEventListener('change', updateBuilderCode));

    // 短縮マクロボタン (ALL, GH:ALL, AL:ALL, HP:ALL)
    document.querySelectorAll('.btn-macro').forEach(btn => {
      btn.addEventListener('click', () => {
        const macro = btn.getAttribute('data-macro');
        const isAlreadyActive = (builderMacroTarget === macro);

        clearMacroButtons();

        if (!isAlreadyActive) {
          btn.classList.add('active');
          builderMacroTarget = macro;

          // 下のスピーカーチップも種別に応じて視覚的に選択
          document.querySelectorAll('#builderSpeakersGrid input[type="checkbox"]').forEach(c => {
            const type = c.getAttribute('data-type');
            let match = false;
            if (macro === 'ALL') match = true;
            else if (macro === 'GH:ALL') match = (type === 'google');
            else if (macro === 'AL:ALL') match = (type === 'alexa');
            else if (macro === 'HP:ALL') match = (type === 'homepod');
            c.checked = match;
            c.closest('.speaker-chip')?.classList.toggle('checked', match);
          });
        }
        updateBuilderCode();
      });
    });

    // スピーカークリアボタン
    document.getElementById('btnBuilderClear')?.addEventListener('click', () => {
      clearMacroButtons();
      document.querySelectorAll('#builderSpeakersGrid input[type="checkbox"]').forEach(c => {
        c.checked = false;
        c.closest('.speaker-chip')?.classList.remove('checked');
      });
      updateBuilderCode();
    });

    // タブ切り替え
    document.querySelectorAll('.pill-btn').forEach(btn => {
      btn.addEventListener('click', () => {
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

  // 登録カレンダー一覧の描画 (個別設定バッジ & 編集モーダル対応)
  function renderCalendarList() {
    const container = document.getElementById('calendarListContainer');
    if (!container) return;

    const list = state.calendarData?.calendars || [];
    if (list.length === 0) {
      container.innerHTML = `
        <div style="padding: 14px; background: rgba(255,255,255,0.02); border: 1px dashed var(--card-border); border-radius: var(--radius-sm); text-align: center; color: var(--text-muted); font-size: 0.85rem;">
          登録されたカレンダーはありません。「＋ カレンダーを追加」ボタンから Google カレンダーの iCal URL を登録してください。
        </div>
      `;
      return;
    }

    let html = '';
    list.forEach((c, idx) => {
      const isChecked = c.enabled !== false ? 'checked' : '';

      // 個別設定バッジ一覧
      const badges = [];
      if (c.remindEnabled !== false) {
        badges.push(`<span class="badge-tech" style="font-size:0.68rem; padding:1px 6px;">🔔 ${c.remindMinutesBefore || 10}分前</span>`);
      } else {
        badges.push(`<span class="badge-tech" style="font-size:0.68rem; padding:1px 6px; opacity:0.6;">🔔 リマインドOFF</span>`);
      }

      if (c.dailySummaryEnabled !== false) {
        badges.push(`<span class="badge-tech" style="font-size:0.68rem; padding:1px 6px; color:#fbbf24; border-color:rgba(245,158,11,0.3);">☀️ ${c.dailySummaryTime || '07:30'}</span>`);
      } else {
        badges.push(`<span class="badge-tech" style="font-size:0.68rem; padding:1px 6px; opacity:0.6;">☀️ 朝まとめOFF</span>`);
      }

      if (Array.isArray(c.targetDevices) && c.targetDevices.length > 0) {
        badges.push(`<span class="badge-tech" style="font-size:0.68rem; padding:1px 6px; color:#60a5fa; border-color:rgba(59,130,246,0.3);">🔊 個別スピーカー(${c.targetDevices.length})</span>`);
      }

      if (c.voice) {
        const shortVoice = c.voice.replace('ja-JP-', '').replace('Neural', '');
        badges.push(`<span class="badge-tech" style="font-size:0.68rem; padding:1px 6px;">🗣️ ${shortVoice}</span>`);
      }

      if (c.volumeLevel) {
        badges.push(`<span class="badge-tech" style="font-size:0.68rem; padding:1px 6px; color:#34d399; border-color:rgba(52,211,153,0.3);">🔉 ${Math.round(parseFloat(c.volumeLevel) * 100)}%</span>`);
      }

      html += `
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; background: rgba(255,255,255,0.03); border: 1px solid var(--card-border); border-radius: var(--radius-sm); transition: all 0.2s ease;">
          <div style="min-width: 0; flex: 1;">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <span style="font-size: 0.92rem; font-weight: 600; color: var(--text-main);">${escapeHtml(c.name || `カレンダー ${idx + 1}`)}</span>
              ${c.enabled !== false ? '<span style="font-size: 0.68rem; padding: 1px 6px; border-radius: 999px; background: rgba(99,102,241,0.15); color: #818cf8; border: 1px solid rgba(99,102,241,0.3);">同期中</span>' : '<span style="font-size: 0.68rem; padding: 1px 6px; border-radius: 999px; background: rgba(255,255,255,0.08); color: var(--text-muted);">停止中</span>'}
              <div style="display: inline-flex; gap: 4px; flex-wrap: wrap;">
                ${badges.join(' ')}
              </div>
            </div>
            <div style="font-size: 0.78rem; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 450px; margin-top: 4px;" title="${escapeHtml(c.icalUrl)}">
              ${escapeHtml(c.icalUrl)}
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; flex-shrink: 0;">
            <button type="button" class="btn btn-secondary btn-sm btn-edit-cal" data-id="${c.id}" style="font-size: 0.8rem; padding: 5px 10px;" title="このカレンダーの通知先・ボイス・リマインドを個別設定">
              ⚙️ 個別設定
            </button>
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

    // 個別設定編集ボタン
    container.querySelectorAll('.btn-edit-cal').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        openCalendarModal(id);
      });
    });

    // カレンダー個別ON/OFFトグル
    container.querySelectorAll('.cal-toggle-item').forEach(chk => {
      chk.addEventListener('change', async (e) => {
        const id = e.target.getAttribute('data-id');
        const found = state.calendarData.calendars.find(c => c.id === id);
        if (found) {
          found.enabled = e.target.checked;
          renderCalendarList();
          await saveCurrentCalendarConfig(true);
          showToast(`「${found.name}」の有効状態を更新しました`, 'success');
        }
      });
    });

    // カレンダー削除
    container.querySelectorAll('.btn-delete-cal').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = btn.getAttribute('data-id');
        const found = state.calendarData.calendars.find(c => c.id === id);
        const name = found ? found.name : 'カレンダー';
        if (confirm(`「${name}」を連携リストから削除してもよろしいですか？`)) {
          state.calendarData.calendars = state.calendarData.calendars.filter(c => c.id !== id);
          renderCalendarList();
          const ok = await saveCurrentCalendarConfig(true);
          if (ok) {
            showToast(`「${name}」を削除しました`, 'success');
          }
        }
      });
    });
  }

  // 共通カレンダー設定保存関数 (全体設定 & 各カレンダーの個別設定を保持)
  async function saveCurrentCalendarConfig(shouldSync = false) {
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
      if (shouldSync) {
        await loadCalendarEvents();
      }
      return true;
    } catch (err) {
      showToast('設定保存エラー: ' + err.message, 'error');
      return false;
    }
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

    // カレンダー追加ボタン (モーダルを開く)
    const btnShowAddCalForm = document.getElementById('btnShowAddCalForm');
    const addCalInlineForm = document.getElementById('addCalInlineForm');
    const btnCancelAddCal = document.getElementById('btnCancelAddCal');
    const btnAddCalConfirm = document.getElementById('btnAddCalConfirm');

    if (btnShowAddCalForm) {
      btnShowAddCalForm.addEventListener('click', () => {
        openCalendarModal(null);
      });
    }

    if (btnCancelAddCal && addCalInlineForm) {
      btnCancelAddCal.addEventListener('click', () => {
        addCalInlineForm.style.display = 'none';
        document.getElementById('newCalName').value = '';
        document.getElementById('newCalUrl').value = '';
      });
    }

    // カレンダー追加の確定 (インライン簡易追加)
    if (btnAddCalConfirm) {
      btnAddCalConfirm.addEventListener('click', async () => {
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

        if (url.includes('/public/basic.ics')) {
          const proceed = confirm('【ご注意】入力されたURLはGoogleカレンダーの「公開用」URLです。\nカレンダーを一般公開していない場合、同期時に 404 エラーとなります。\n\n非公開カレンダーの場合は、Google カレンダー設定の「非公開 URL の iCal」をコピーしてください。\n\nこのまま登録を続行しますか？');
          if (!proceed) return;
        }

        if (!state.calendarData) state.calendarData = { calendars: [] };
        if (!state.calendarData.calendars) state.calendarData.calendars = [];

        state.calendarData.calendars.push({
          id: 'cal_' + Date.now(),
          name,
          icalUrl: url,
          enabled: true,
          remindEnabled: true,
          remindMinutesBefore: 10,
          dailySummaryEnabled: true,
          dailySummaryTime: '07:30',
          targetDevices: [],
          voice: 'ja-JP-NanamiNeural',
          rate: '+0%',
          pitch: '+0Hz',
          volumeLevel: ''
        });

        renderCalendarList();
        if (addCalInlineForm) addCalInlineForm.style.display = 'none';
        nameInput.value = '';
        urlInput.value = '';

        showToast(`「${name}」を登録して同期しています...`, 'info');
        const ok = await saveCalendarConfigInternal(true);
        if (ok) {
          showToast(`「${name}」を追加し、予定を同期しました！`, 'success');
        }
      });
    }

    // ================= カレンダー個別設定モーダル操作 =================
    window.openCalendarModal = function(calId = null) {
      const modal = document.getElementById('calendarModal');
      if (!modal) return;

      const isEdit = !!calId;
      const found = isEdit ? (state.calendarData?.calendars || []).find(c => c.id === calId) : null;

      document.getElementById('editCalId').value = isEdit ? calId : '';
      document.getElementById('calendarModalTitle').textContent = isEdit ? `「${found?.name || 'カレンダー'}」の個別設定` : '新規カレンダー登録';
      document.getElementById('modalCalName').value = found ? (found.name || '') : '';
      document.getElementById('modalCalUrl').value = found ? (found.icalUrl || '') : '';

      // 直前リマインド
      const remindCheck = document.getElementById('modalCalRemindEnabled');
      if (remindCheck) remindCheck.checked = found ? (found.remindEnabled !== false) : true;
      const remindMin = document.getElementById('modalCalRemindMinutes');
      if (remindMin) remindMin.value = String(found ? (found.remindMinutesBefore || 10) : 10);

      // 朝まとめ
      const dailyCheck = document.getElementById('modalCalDailySummaryEnabled');
      if (dailyCheck) dailyCheck.checked = found ? (found.dailySummaryEnabled !== false) : true;
      const dailyTime = document.getElementById('modalCalDailySummaryTime');
      if (dailyTime) dailyTime.value = found ? (found.dailySummaryTime || '07:30') : '07:30';

      // スピーカー個別選択
      const spkContainer = document.getElementById('modalCalSpeakersContainer');
      if (spkContainer) {
        const selected = found?.targetDevices || [];
        renderSpeakersCheckboxes(spkContainer, 'modalCalSpeaker', selected);
      }

      // 音声オプション
      const voiceSelect = document.getElementById('modalCalVoice');
      if (voiceSelect) voiceSelect.value = found?.voice || 'ja-JP-NanamiNeural';

      // 音量
      const volRange = document.getElementById('modalCalVolumeRange');
      const volDisplay = document.getElementById('modalCalVolumeDisplay');
      const volVal = found?.volumeLevel ? Math.round(parseFloat(found.volumeLevel) * 100) : 0;
      if (volRange) volRange.value = volVal;
      if (volDisplay) volDisplay.textContent = volVal > 0 ? `${volVal}%` : '全体設定に従う';

      // 話速
      const rateRange = document.getElementById('modalCalRateRange');
      const rateDisplay = document.getElementById('modalCalRateDisplay');
      const rateVal = parseInt(found?.rate || '0', 10);
      if (rateRange) rateRange.value = rateVal;
      if (rateDisplay) rateDisplay.textContent = rateVal === 0 ? '標準 (0%)' : (rateVal > 0 ? `+${rateVal}%` : `${rateVal}%`);

      // 音高
      const pitchRange = document.getElementById('modalCalPitchRange');
      const pitchDisplay = document.getElementById('modalCalPitchDisplay');
      const pitchVal = parseInt(found?.pitch || '0', 10);
      if (pitchRange) pitchRange.value = pitchVal;
      if (pitchDisplay) pitchDisplay.textContent = pitchVal === 0 ? '標準 (0Hz)' : (pitchVal > 0 ? `+${pitchVal}Hz` : `${pitchVal}Hz`);

      modal.style.display = 'flex';
    };

    window.closeCalendarModal = function() {
      const modal = document.getElementById('calendarModal');
      if (modal) modal.style.display = 'none';
    };

    document.getElementById('btnCloseCalModal')?.addEventListener('click', closeCalendarModal);
    document.getElementById('btnCancelCalModal')?.addEventListener('click', closeCalendarModal);

    // スライダーイベント (モーダル内)
    document.getElementById('modalCalVolumeRange')?.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      const disp = document.getElementById('modalCalVolumeDisplay');
      if (disp) disp.textContent = val === 0 ? '全体設定に従う' : `${val}%`;
    });
    document.getElementById('modalCalRateRange')?.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      const disp = document.getElementById('modalCalRateDisplay');
      if (disp) disp.textContent = val === 0 ? '標準 (0%)' : (val > 0 ? `+${val}%` : `${val}%`);
    });
    document.getElementById('modalCalPitchRange')?.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      const disp = document.getElementById('modalCalPitchDisplay');
      if (disp) disp.textContent = val === 0 ? '標準 (0Hz)' : (val > 0 ? `+${val}Hz` : `${val}Hz`);
    });

    // モーダル保存確定
    document.getElementById('calendarModalForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const editId = document.getElementById('editCalId')?.value;
      const name = document.getElementById('modalCalName')?.value.trim() || 'カレンダー';
      const url = document.getElementById('modalCalUrl')?.value.trim() || '';

      if (!url) {
        showToast('iCal URL を入力してください', 'error');
        return;
      }

      if (url.includes('/public/basic.ics')) {
        const proceed = confirm('【ご注意】入力されたURLはGoogleカレンダーの「公開用」URLです。\nカレンダーを一般公開していない場合、同期時に 404 エラーとなります。\n\n非公開カレンダーの場合は、Google カレンダー設定の「非公開 URL の iCal」をコピーしてください。\n\nこのまま登録を続行しますか？');
        if (!proceed) return;
      }

      const remindEnabled = document.getElementById('modalCalRemindEnabled')?.checked !== false;
      const remindMinutesBefore = parseInt(document.getElementById('modalCalRemindMinutes')?.value || '10', 10);
      const dailySummaryEnabled = document.getElementById('modalCalDailySummaryEnabled')?.checked !== false;
      const dailySummaryTime = document.getElementById('modalCalDailySummaryTime')?.value || '07:30';

      const spk = getSelectedSpeakers(document.getElementById('modalCalSpeakersContainer'));
      const voice = document.getElementById('modalCalVoice')?.value || 'ja-JP-NanamiNeural';
      const rateVal = parseInt(document.getElementById('modalCalRateRange')?.value || '0', 10);
      const rate = (rateVal >= 0 ? '+' : '') + rateVal + '%';
      const pitchVal = parseInt(document.getElementById('modalCalPitchRange')?.value || '0', 10);
      const pitch = (pitchVal >= 0 ? '+' : '') + pitchVal + 'Hz';
      const volVal = parseInt(document.getElementById('modalCalVolumeRange')?.value || '0', 10);
      const volumeLevel = volVal > 0 ? (volVal / 100).toString() : '';

      if (!state.calendarData) state.calendarData = { calendars: [] };
      if (!state.calendarData.calendars) state.calendarData.calendars = [];

      if (editId) {
        const found = state.calendarData.calendars.find(c => c.id === editId);
        if (found) {
          found.name = name;
          found.icalUrl = url;
          found.remindEnabled = remindEnabled;
          found.remindMinutesBefore = remindMinutesBefore;
          found.dailySummaryEnabled = dailySummaryEnabled;
          found.dailySummaryTime = dailySummaryTime;
          found.targetDevices = spk;
          found.voice = voice;
          found.rate = rate;
          found.pitch = pitch;
          found.volumeLevel = volumeLevel;
        }
      } else {
        state.calendarData.calendars.push({
          id: 'cal_' + Date.now(),
          name,
          icalUrl: url,
          enabled: true,
          remindEnabled,
          remindMinutesBefore,
          dailySummaryEnabled,
          dailySummaryTime,
          targetDevices: spk,
          voice,
          rate,
          pitch,
          volumeLevel
        });
      }

      closeCalendarModal();
      renderCalendarList();

      showToast(`カレンダー「${name}」を保存して同期しています...`, 'info');
      const ok = await saveCalendarConfigInternal(true);
      if (ok) {
        showToast(`カレンダー「${name}」の個別設定を保存しました！`, 'success');
      }
    });

    // 内部保存ヘルパー
    async function saveCalendarConfigInternal(shouldSync = false) {
      const calSpeakers = getSelectedSpeakers(document.getElementById('calSpeakersContainer'));
      const calendars = state.calendarData?.calendars || [];

      const payload = {
        calendar: {
          enabled: document.getElementById('calEnabled')?.checked || false,
          calendars,
          icalUrl: calendars[0]?.icalUrl || '',
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
        if (shouldSync) {
          await loadCalendarEvents();
        }
        return true;
      } catch (err) {
        showToast('設定保存エラー: ' + err.message, 'error');
        return false;
      }
    }

    // カレンダー設定保存
    const calForm = document.getElementById('calendarSettingsForm');
    if (calForm) {
      calForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const ok = await saveCalendarConfigInternal(true);
        if (ok) {
          showToast('Google カレンダー連携設定を保存しました！', 'success');
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

  // ================= 5.5 おやすみ・会議モード (DND) =================
  async function loadDndStatus() {
    try {
      const res = await fetch('/api/dnd/status');
      if (!res.ok) return;
      const data = await res.json();
      state.dndStatus = data;
      renderDndStatus();
    } catch (e) {
      console.warn('DNDステータス取得失敗:', e);
    }
  }

  function renderDndStatus() {
    const s = state.dndStatus || {};
    const headerChip = document.getElementById('headerDndChip');
    const headerText = document.getElementById('headerDndText');
    const banner = document.getElementById('dndStatusBanner');
    const dot = document.getElementById('dndStatusDot');
    const title = document.getElementById('dndStatusTitle');
    const subtitle = document.getElementById('dndStatusSubtitle');
    const queueBadge = document.getElementById('dndQueueBadge');
    const queueCount = document.getElementById('dndQueueCount');
    const btnCancel = document.getElementById('btnCancelQuickDnd');
    const activeCalBox = document.getElementById('dndActiveCalendarBox');

    // 1. ヘッダー表示
    if (headerText) {
      if (s.isActive) {
        let reasonShort = s.reason ? s.reason.replace('カレンダー予定中: ', '📅').replace('定時サイレント: ', '⏰').replace('手動サイレント (即時)', '🔇手動') : '🔇発動中';
        if (reasonShort.length > 14) reasonShort = reasonShort.slice(0, 14) + '...';
        headerText.textContent = `DND: ${reasonShort}`;
        if (headerChip) {
          headerChip.style.borderColor = 'rgba(239, 68, 68, 0.5)';
          headerChip.style.color = '#f87171';
        }
      } else {
        headerText.textContent = s.enabled ? 'DND: 監視中' : 'DND: 無効';
        if (headerChip) {
          headerChip.style.borderColor = '';
          headerChip.style.color = '';
        }
      }
    }

    // 1.5. ヘッダーのミュート/アンミュート切り替えボタン更新
    const toggleBtn = document.getElementById('headerDndToggleBtn');
    const toggleIcon = document.getElementById('headerDndToggleIcon');
    const toggleText = document.getElementById('headerDndToggleText');
    if (toggleBtn && toggleIcon && toggleText) {
      if (s.isActive) {
        toggleBtn.classList.add('is-muted');
        toggleIcon.textContent = '🔊';
        toggleText.textContent = 'アンミュート';
        toggleBtn.title = 'クリックでミュートを解除 (通常モードへ復帰)';
      } else {
        toggleBtn.classList.remove('is-muted');
        toggleIcon.textContent = '🔇';
        toggleText.textContent = 'ミュート';
        const topDur = state.dndConfig?.topMuteDuration || '60';
        const durLabel = (topDur === 'indefinite') ? '手動解除までずっと' : (topDur === '1440' ? '1日間' : (topDur === '120' ? '2時間' : (topDur === '30' ? '30分間' : '1時間')));
        toggleBtn.title = `ワンタップで即時ミュート (${durLabel}サイレント)`;
      }
    }

    // 2. バナー表示
    if (banner && title && subtitle) {
      if (s.isActive) {
        banner.style.background = 'rgba(239, 68, 68, 0.12)';
        banner.style.borderColor = 'rgba(239, 68, 68, 0.35)';
        if (dot) {
          dot.style.background = '#ef4444';
          dot.style.boxShadow = '0 0 10px #ef4444';
        }
        title.innerHTML = `🔇 サイレント発動中: <span style="color:#f87171;">${escapeHtml(s.reason || 'DNDアクティブ')}</span>`;
        let subText = `現在スピーカーは【${s.action === 'whisper' ? `囁き音量 (${s.whisperVolume || 10}%)` : s.action === 'queue' ? '保留キュー' : '完全スキップ'}】に設定されています。`;
        if (s.until) {
          if (s.until === 'indefinite') {
            subText += ` 解除予定: 手動で解除するまでずっと (無期限)`;
          } else {
            const uDate = new Date(s.until);
            subText += ` 解除予定: ${uDate.toLocaleTimeString()}`;
          }
        }
        subtitle.textContent = subText;
        if (btnCancel) btnCancel.style.display = 'inline-block';
      } else {
        banner.style.background = 'rgba(16, 185, 129, 0.1)';
        banner.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        if (dot) {
          dot.style.background = '#10b981';
          dot.style.boxShadow = '0 0 10px #10b981';
        }
        title.textContent = s.enabled ? '🟢 現在は通常モードです' : '⚪ DND機能は全体無効です';
        subtitle.textContent = s.enabled 
          ? '通知やアナウンスは通常音量でスピーカーから再生されます（予定や時間帯に合わせて自動切替）'
          : 'スイッチをONにすると、定時やカレンダー連携での静音化が有効になります';
        if (btnCancel) btnCancel.style.display = 'none';
      }
    }

    // 3. 保留キュー件数
    if (queueBadge && queueCount) {
      if (s.queuedCount > 0) {
        queueBadge.style.display = 'inline-block';
        queueCount.textContent = s.queuedCount;
      } else {
        queueBadge.style.display = 'none';
      }
    }

    // 4. カレンダー進行中予定プレビュー
    if (activeCalBox) {
      if (s.activeCalendarEvent) {
        const ev = s.activeCalendarEvent;
        const sTime = ev.start ? new Date(ev.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
        const eTime = ev.end ? new Date(ev.end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
        activeCalBox.innerHTML = `
          <div style="display:flex; align-items:center; gap:8px; color:#f87171;">
            <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#ef4444;"></span>
            <strong>進行中の予定を検知中:</strong> ${escapeHtml(ev.summary || '予定あり')} (${sTime} 〜 ${eTime})
          </div>
        `;
      } else {
        activeCalBox.innerHTML = '現在進行中の会議・カレンダー予定はありません';
      }
    }
  }

  function updateDndActionRadioHighlight() {
    document.querySelectorAll('.dnd-action-radio-box').forEach(box => {
      const inp = box.querySelector('input[type="radio"]');
      if (inp && inp.checked) {
        box.classList.add('selected');
      } else {
        box.classList.remove('selected');
      }
    });
  }

  async function loadDndSettings() {
    try {
      const res = await fetch('/api/settings');
      if (!res.ok) return;
      const data = await res.json();
      const dnd = data.dnd || {};
      state.dndConfig = dnd;

      // マスター
      const masterEl = document.getElementById('dndMasterEnabled');
      if (masterEl) masterEl.checked = dnd.enabled !== false;

      // カレンダー
      const calEl = document.getElementById('dndCalendarEnabled');
      if (calEl) calEl.checked = !!dnd.calendarEnabled;
      const kwEl = document.getElementById('dndCalendarKeywords');
      if (kwEl) kwEl.value = dnd.calendarKeywords || '';

      const calMode = dnd.calendarMode || 'keywords';
      const calModeRadio = document.querySelector(`input[name="dndCalendarMode"][value="${calMode}"]`);
      if (calModeRadio) calModeRadio.checked = true;
      const kwWrapper = document.getElementById('dndCalendarKeywordsWrapper');
      if (kwWrapper) kwWrapper.style.display = (calMode === 'all') ? 'none' : 'block';

      const calAllDayEl = document.getElementById('dndCalendarIncludeAllDay');
      if (calAllDayEl) calAllDayEl.checked = !!dnd.calendarIncludeAllDay;

      // スケジュール
      const schedEl = document.getElementById('dndScheduleEnabled');
      if (schedEl) schedEl.checked = !!dnd.scheduleEnabled;
      renderDndSchedules();

      // アクションラジオ
      const actionRadio = document.querySelector(`input[name="dndAction"][value="${dnd.action || 'skip'}"]`);
      if (actionRadio) {
        actionRadio.checked = true;
        updateDndActionRadioHighlight();
      }
      const whisperWrapper = document.getElementById('dndWhisperWrapper');
      if (whisperWrapper) whisperWrapper.style.display = (dnd.action === 'whisper') ? 'block' : 'none';
      const whisperVolEl = document.getElementById('dndWhisperVolume');
      const whisperDispEl = document.getElementById('dndWhisperDisplay');
      if (whisperVolEl) whisperVolEl.value = dnd.whisperVolume || 10;
      if (whisperDispEl) whisperDispEl.textContent = `${dnd.whisperVolume || 10}%`;

      // スコープラジオ
      const scopeRadio = document.querySelector(`input[name="dndTargetScope"][value="${dnd.targetScope || 'all'}"]`);
      if (scopeRadio) scopeRadio.checked = true;
      const spkWrapper = document.getElementById('dndSpeakersWrapper');
      if (spkWrapper) spkWrapper.style.display = (dnd.targetScope === 'specific') ? 'block' : 'none';
      renderDndSpeakers(dnd.targetDevices || []);

      // Topメニューのミュートボタン動作
      const topMuteDur = dnd.topMuteDuration || '60';
      const topMuteRadio = document.querySelector(`input[name="dndTopMuteDuration"][value="${topMuteDur}"]`);
      if (topMuteRadio) topMuteRadio.checked = true;

      // 保留通知のAI自動要約
      const aiSummaryCheck = document.getElementById('dndAiSummaryEnabled');
      if (aiSummaryCheck) aiSummaryCheck.checked = dnd.aiSummaryEnabled !== false;
      const aiSummaryThres = document.getElementById('dndAiSummaryThreshold');
      if (aiSummaryThres) aiSummaryThres.value = String(dnd.aiSummaryThreshold || 2);

      // AI要約ラッパーの表示制御 (action === 'queue' のときに表示)
      const queueAiWrapper = document.getElementById('dndQueueAiWrapper');
      if (queueAiWrapper) queueAiWrapper.style.display = (dnd.action === 'queue') ? 'block' : 'none';
      updateDndAiBadge();
    } catch (e) {
      console.warn('DND設定取得失敗:', e);
    }
  }

  function renderDndSchedules() {
    const container = document.getElementById('dndScheduleList');
    if (!container) return;
    const list = state.dndConfig?.schedules || [];

    if (!list.length) {
      container.innerHTML = `<div class="empty-msg" style="padding:10px 0;">登録された定時ルールはありません</div>`;
      return;
    }

    const WEEKDAYS_MAP = { '0': '日', '1': '月', '2': '火', '3': '水', '4': '木', '5': '金', '6': '土' };

    let html = '';
    list.forEach(item => {
      const checked = item.enabled !== false ? 'checked' : '';
      const daysStr = (item.days || []).map(d => WEEKDAYS_MAP[d] || d).join('・') || '全日';

      html += `
        <div class="calendar-item dnd-sched-item">
          <div style="display:flex; align-items:center; gap:12px; min-width:0; flex:1;">
            <label class="switch">
              <input type="checkbox" class="dnd-sched-toggle" data-id="${escapeHtml(item.id)}" ${checked}>
              <span class="slider"></span>
            </label>
            <div>
              <strong style="font-size:0.92rem;">${escapeHtml(item.name || '定時サイレント')}</strong>
              <div style="font-size:0.8rem; color:var(--text-muted); margin-top:2px;">
                毎週 ${escapeHtml(daysStr)} ｜ ${escapeHtml(item.startTime || '00:00')} 〜 ${escapeHtml(item.endTime || '23:59')}
              </div>
            </div>
          </div>
          <div class="dnd-sched-actions">
            <button type="button" class="btn-icon-sm btn-edit-dnd-sched" data-id="${escapeHtml(item.id)}" title="編集">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
            <button type="button" class="btn-icon-sm btn-danger btn-delete-dnd-sched" data-id="${escapeHtml(item.id)}" title="削除">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // トグル切り替え
    container.querySelectorAll('.dnd-sched-toggle').forEach(chk => {
      chk.addEventListener('change', async (e) => {
        const id = e.target.getAttribute('data-id');
        const found = state.dndConfig.schedules.find(s => s.id === id);
        if (found) {
          found.enabled = e.target.checked;
          await saveDndSettingsInternal();
          showToast(`「${found.name}」の有効状態を更新しました`, 'success');
          loadDndStatus();
        }
      });
    });

    // 編集
    container.querySelectorAll('.btn-edit-dnd-sched').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        const found = state.dndConfig.schedules.find(s => s.id === id);
        if (!found) return;

        const formEl = document.getElementById('addDndSchedInlineForm');
        if (!formEl) return;

        document.getElementById('editDndSchedId').value = found.id;
        document.getElementById('newDndSchedName').value = found.name || '';
        document.getElementById('newDndStartTime').value = found.startTime || '09:00';
        document.getElementById('newDndEndTime').value = found.endTime || '18:00';

        const days = Array.isArray(found.days) ? found.days.map(String) : [];
        document.querySelectorAll('input[name="newDndDay"]').forEach(chk => {
          chk.checked = days.includes(chk.value);
        });

        const titleEl = document.getElementById('dndSchedFormTitle');
        if (titleEl) titleEl.textContent = '定時サイレントルールの編集';
        const confirmBtn = document.getElementById('btnAddDndSchedConfirm');
        if (confirmBtn) confirmBtn.textContent = 'ルールを更新';

        formEl.style.display = 'block';
        formEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    });

    // 削除
    container.querySelectorAll('.btn-delete-dnd-sched').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = btn.getAttribute('data-id');
        const found = state.dndConfig.schedules.find(s => s.id === id);
        const name = found ? found.name : 'ルール';
        if (confirm(`「${name}」を削除してもよろしいですか？`)) {
          state.dndConfig.schedules = state.dndConfig.schedules.filter(s => s.id !== id);
          renderDndSchedules();
          await saveDndSettingsInternal();
          showToast(`「${name}」を削除しました`, 'success');
          loadDndStatus();
        }
      });
    });
  }

  function renderDndSpeakers(selectedList) {
    const container = document.getElementById('dndSpeakersContainer');
    if (!container) return;
    const current = selectedList || state.dndConfig?.targetDevices || [];
    renderSpeakersCheckboxes(container, 'dndSpeaker', current);
  }

  async function loadDndHistory() {
    try {
      const res = await fetch('/api/dnd/history');
      if (!res.ok) return;
      const data = await res.json();
      state.dndHistory = data;
      renderDndHistory();
    } catch (e) {
      console.warn('DND履歴取得失敗:', e);
    }
  }

  function renderDndHistory() {
    const container = document.getElementById('dndHistoryList');
    if (!container) return;
    const list = state.dndHistory || [];

    if (!list.length) {
      container.innerHTML = `<li class="empty-msg">サイレント履歴はまだありません</li>`;
      return;
    }

    let html = '';
    list.forEach(item => {
      const t = new Date(item.timestamp).toLocaleTimeString();
      let actionBadge = `<span style="font-size:0.75rem; padding:2px 8px; border-radius:999px; background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.3);">${escapeHtml(item.handledAs || 'スキップ')}</span>`;
      if (item.action === 'whisper') {
        actionBadge = `<span style="font-size:0.75rem; padding:2px 8px; border-radius:999px; background:rgba(245,158,11,0.15); color:#fbbf24; border:1px solid rgba(245,158,11,0.3);">${escapeHtml(item.handledAs || '極小音量')}</span>`;
      } else if (item.action === 'queue') {
        actionBadge = `<span style="font-size:0.75rem; padding:2px 8px; border-radius:999px; background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3);">${escapeHtml(item.handledAs || '保留キュー')}</span>`;
      }

      html += `
        <li class="history-item" style="padding:10px 12px; border-bottom:1px solid rgba(255,255,255,0.05); display:flex; flex-direction:column; gap:4px;">
          <div style="display:flex; align-items:center; justify-content:space-between; gap:8px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:0.8rem; color:var(--text-muted); font-family:var(--font-mono);">${t}</span>
              ${actionBadge}
              <span style="font-size:0.75rem; color:var(--text-muted); background:rgba(255,255,255,0.05); padding:1px 6px; border-radius:4px;">理由: ${escapeHtml(item.reason || '')}</span>
            </div>
            <span style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml(item.targetDevice || '全室')}</span>
          </div>
          <div style="font-size:0.9rem; color:var(--text-color); margin-top:2px;">${escapeHtml(item.text || '')}</div>
        </li>
      `;
    });

    container.innerHTML = html;
  }

  async function saveDndSettingsInternal() {
    const spk = getSelectedSpeakers(document.getElementById('dndSpeakersContainer'));
    const dnd = state.dndConfig || {};

    const payload = {
      dnd: {
        enabled: document.getElementById('dndMasterEnabled')?.checked !== false,
        calendarEnabled: document.getElementById('dndCalendarEnabled')?.checked || false,
        calendarMode: document.querySelector('input[name="dndCalendarMode"]:checked')?.value || 'keywords',
        calendarKeywords: document.getElementById('dndCalendarKeywords')?.value || '',
        calendarIncludeAllDay: document.getElementById('dndCalendarIncludeAllDay')?.checked || false,
        scheduleEnabled: document.getElementById('dndScheduleEnabled')?.checked || false,
        schedules: dnd.schedules || [],
        action: document.querySelector('input[name="dndAction"]:checked')?.value || 'skip',
        whisperVolume: parseInt(document.getElementById('dndWhisperVolume')?.value || '10', 10),
        targetScope: document.querySelector('input[name="dndTargetScope"]:checked')?.value || 'all',
        targetDevices: spk,
        topMuteDuration: document.querySelector('input[name="dndTopMuteDuration"]:checked')?.value || '60',
        aiSummaryEnabled: document.getElementById('dndAiSummaryEnabled')?.checked !== false,
        aiSummaryThreshold: parseInt(document.getElementById('dndAiSummaryThreshold')?.value || '2', 10)
      }
    };

    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('保存失敗');
      const updated = await res.json();
      state.dndConfig = updated.dnd || payload.dnd;
      return true;
    } catch (err) {
      showToast('DND設定保存エラー: ' + err.message, 'error');
      return false;
    }
  }

  function setupDndHandlers() {
    // マスター切り替え
    document.getElementById('dndMasterEnabled')?.addEventListener('change', async () => {
      await saveDndSettingsInternal();
      showToast('おやすみ・会議モードの全体設定を更新しました', 'success');
      loadDndStatus();
    });

    // カレンダー連動トグル
    document.getElementById('dndCalendarEnabled')?.addEventListener('change', async () => {
      await saveDndSettingsInternal();
      showToast('カレンダー予定連動の有効状態を更新しました', 'success');
      loadDndStatus();
    });

    // カレンダーモードラジオ (キーワードのみ vs 全予定)
    document.querySelectorAll('input[name="dndCalendarMode"]').forEach(radio => {
      radio.addEventListener('change', async (e) => {
        const kwWrapper = document.getElementById('dndCalendarKeywordsWrapper');
        if (kwWrapper) {
          kwWrapper.style.display = (e.target.value === 'all') ? 'none' : 'block';
        }
        await saveDndSettingsInternal();
        showToast(`カレンダーサイレント対象: ${e.target.value === 'all' ? 'すべての予定' : 'キーワード一致のみ'} に変更しました`, 'info');
        loadDndStatus();
      });
    });

    // 終日予定を含めるトグル
    document.getElementById('dndCalendarIncludeAllDay')?.addEventListener('change', async (e) => {
      await saveDndSettingsInternal();
      showToast(`終日予定のサイレント対象: ${e.target.checked ? '含む' : '除外 (推奨)'} に設定しました`, 'info');
      loadDndStatus();
    });

    // 定時スケジュールトグル
    document.getElementById('dndScheduleEnabled')?.addEventListener('change', async () => {
      await saveDndSettingsInternal();
      showToast('定時スケジュールの有効状態を更新しました', 'success');
      loadDndStatus();
    });

    // ワンタップ即時ミュートボタン
    document.querySelectorAll('.btn-quick-dnd').forEach(btn => {
      btn.addEventListener('click', async () => {
        const val = btn.getAttribute('data-minutes');
        let minutes = 30;
        let reason = '';
        let label = '';
        if (val === 'today') {
          const now = new Date();
          const endOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
          minutes = Math.max(1, Math.round((endOfDay.getTime() - now.getTime()) / 60000));
          reason = 'ワンタップ即時サイレント (本日中)';
          label = '本日終了まで';
        } else if (val === 'indefinite') {
          minutes = -1;
          reason = 'ワンタップ即時サイレント (手動解除までずっと)';
          label = '手動解除までずっと';
        } else {
          minutes = parseInt(val, 10) || 30;
          reason = `ワンタップ即時サイレント (${minutes}分)`;
          label = `${minutes}分間`;
        }

        try {
          const res = await fetch('/api/dnd/quick', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ minutes, reason })
          });
          if (!res.ok) throw new Error('設定失敗');
          showToast(`【サイレント発動】${label}ミュートを開始しました`, 'success');
          await loadDndStatus();
        } catch (e) {
          showToast('即時ミュート設定エラー: ' + e.message, 'error');
        }
      });
    });

    // サイレント即時解除
    document.getElementById('btnCancelQuickDnd')?.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/dnd/quick', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ minutes: 0 })
        });
        if (!res.ok) throw new Error('解除失敗');
        showToast('サイレントを解除し、通常モードに復帰しました', 'success');
        await loadDndStatus();
      } catch (e) {
        showToast('サイレント解除エラー: ' + e.message, 'error');
      }
    });

    // ヘッダーのミュート/アンミュート即時トグルボタン
    document.getElementById('headerDndToggleBtn')?.addEventListener('click', async () => {
      const isCurrentlyActive = !!state.dndStatus?.isActive;
      try {
        if (isCurrentlyActive) {
          // アンミュート実行
          const res = await fetch('/api/dnd/quick', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ minutes: 0 })
          });
          if (!res.ok) throw new Error('解除失敗');
          showToast('ミュートを解除し、通常モードに復帰しました', 'success');
        } else {
          // 設定された期間でミュート実行
          const durationSetting = state.dndConfig?.topMuteDuration || '60';
          let minutes = 60;
          let label = '1時間';
          if (durationSetting === 'indefinite') {
            minutes = -1;
            label = '手動解除までずっと';
          } else {
            minutes = parseInt(durationSetting, 10) || 60;
            if (minutes === 30) label = '30分間';
            else if (minutes === 60) label = '1時間';
            else if (minutes === 120) label = '2時間';
            else if (minutes === 1440) label = '1日間 (24時間)';
            else label = `${minutes}分間`;
          }

          const res = await fetch('/api/dnd/quick', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              minutes,
              reason: `手動サイレント (Topメニュー即時ミュート: ${label})`
            })
          });
          if (!res.ok) throw new Error('設定失敗');
          showToast(`【サイレント発動】${label}ミュートを開始しました (再クリックで即時解除)`, 'success');
        }
        await loadDndStatus();
      } catch (e) {
        showToast('ミュート切り替えエラー: ' + e.message, 'error');
      }
    });

    // Topメニューミュート挙動ラジオ切り替え
    document.querySelectorAll('input[name="dndTopMuteDuration"]').forEach(r => {
      r.addEventListener('change', async (e) => {
        await saveDndSettingsInternal();
        const labelMap = {
          '30': '30分 (30m)',
          '60': '1時間 (1h)',
          '120': '2時間 (2h)',
          '1440': '1日 (1d)',
          'indefinite': '手動で解除するまでずっと'
        };
        showToast(`Topメニューのミュート動作を「${labelMap[e.target.value] || e.target.value}」に更新しました`, 'success');
        renderDndStatus();
      });
    });

    // 保留AI要約トグル
    document.getElementById('dndAiSummaryEnabled')?.addEventListener('change', async () => {
      await saveDndSettingsInternal();
      showToast('保留通知のAI要約設定を更新しました', 'success');
    });

    document.getElementById('dndAiSummaryThreshold')?.addEventListener('change', async () => {
      await saveDndSettingsInternal();
      showToast('AI要約の発動件数を更新しました', 'success');
    });

    // DNDタブからAI設定タブへのクイックリンク
    document.getElementById('btnGoToAiTabFromDnd')?.addEventListener('click', () => {
      document.getElementById('btnTabSettings')?.click();
      document.getElementById('btnSubtabSettingsAi')?.click();
    });

    // 定時サイレント追加インラインフォーム開閉
    const btnShowAdd = document.getElementById('btnShowAddDndSched');
    const formEl = document.getElementById('addDndSchedInlineForm');
    const btnCancelAdd = document.getElementById('btnCancelAddDndSched');
    const btnConfirmAdd = document.getElementById('btnAddDndSchedConfirm');

    if (btnShowAdd && formEl) {
      btnShowAdd.addEventListener('click', () => {
        document.getElementById('editDndSchedId').value = '';
        const titleEl = document.getElementById('dndSchedFormTitle');
        if (titleEl) titleEl.textContent = '新規定時ルール';
        if (btnConfirmAdd) btnConfirmAdd.textContent = 'ルールを保存';
        const nameInput = document.getElementById('newDndSchedName');
        if (nameInput) nameInput.value = '';

        formEl.style.display = formEl.style.display === 'none' ? 'block' : 'none';
        if (formEl.style.display === 'block') {
          nameInput?.focus();
        }
      });
    }

    if (btnCancelAdd && formEl) {
      btnCancelAdd.addEventListener('click', () => {
        document.getElementById('editDndSchedId').value = '';
        formEl.style.display = 'none';
      });
    }

    // 定時サイレント追加／編集の確定
    if (btnConfirmAdd) {
      btnConfirmAdd.addEventListener('click', async () => {
        const editId = document.getElementById('editDndSchedId')?.value;
        const name = document.getElementById('newDndSchedName')?.value.trim() || '定時サイレント';
        const sTime = document.getElementById('newDndStartTime')?.value || '09:00';
        const eTime = document.getElementById('newDndEndTime')?.value || '18:00';
        const days = Array.from(document.querySelectorAll('input[name="newDndDay"]:checked')).map(c => c.value);

        if (!days.length) {
          showToast('適用する曜日を1日以上選択してください', 'error');
          return;
        }

        if (!state.dndConfig) state.dndConfig = { schedules: [] };
        if (!state.dndConfig.schedules) state.dndConfig.schedules = [];

        if (editId) {
          const existing = state.dndConfig.schedules.find(s => s.id === editId);
          if (existing) {
            existing.name = name;
            existing.days = days;
            existing.startTime = sTime;
            existing.endTime = eTime;
          }
        } else {
          state.dndConfig.schedules.push({
            id: 'dnd_sched_' + Date.now(),
            name,
            days,
            startTime: sTime,
            endTime: eTime,
            enabled: true
          });
        }

        renderDndSchedules();
        formEl.style.display = 'none';
        document.getElementById('editDndSchedId').value = '';
        document.getElementById('newDndSchedName').value = '';

        const ok = await saveDndSettingsInternal();
        if (ok) {
          showToast(editId ? `定時ルール「${name}」を更新しました！` : `定時ルール「${name}」を追加・保存しました！`, 'success');
          loadDndStatus();
        }
      });
    }

    // アクションラジオ切り替え (囁き音量スライダー連動 & 保留AI設定連動 & ハイライト)
    document.querySelectorAll('input[name="dndAction"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        updateDndActionRadioHighlight();
        const whisperWrapper = document.getElementById('dndWhisperWrapper');
        if (whisperWrapper) {
          whisperWrapper.style.display = (e.target.value === 'whisper') ? 'block' : 'none';
        }
        const queueAiWrapper = document.getElementById('dndQueueAiWrapper');
        if (queueAiWrapper) {
          queueAiWrapper.style.display = (e.target.value === 'queue') ? 'block' : 'none';
        }
      });
    });

    // 囁き音量スライダー値表示
    const whisperVol = document.getElementById('dndWhisperVolume');
    const whisperDisp = document.getElementById('dndWhisperDisplay');
    if (whisperVol && whisperDisp) {
      whisperVol.addEventListener('input', (e) => {
        whisperDisp.textContent = `${e.target.value}%`;
      });
    }

    // 囁き音量テスト再生ボタン
    document.getElementById('btnTestWhisperVolume')?.addEventListener('click', async () => {
      const vol = parseInt(document.getElementById('dndWhisperVolume')?.value || '10', 10);
      const testBtn = document.getElementById('btnTestWhisperVolume');
      testBtn.disabled = true;
      testBtn.textContent = '🔊 再生中...';

      try {
        const res = await fetch('/api/say', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: `これは囁き音量のテストです。現在の音量は${vol}%です。`,
            volumeLevel: vol / 100,
            bypassDnd: true
          })
        });
        if (!res.ok) throw new Error('テスト再生に失敗しました');
        showToast(`囁き音量 (${vol}%) でテスト音声をスピーカーへ送信しました！`, 'success');
      } catch (err) {
        showToast('音量テストエラー: ' + err.message, 'error');
      } finally {
        testBtn.disabled = false;
        testBtn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg> 🔊 音量テスト`;
      }
    });

    // スコープラジオ切り替え (スピーカー一覧連動)
    document.querySelectorAll('input[name="dndTargetScope"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        const spkWrapper = document.getElementById('dndSpeakersWrapper');
        if (spkWrapper) {
          spkWrapper.style.display = (e.target.value === 'specific') ? 'block' : 'none';
        }
      });
    });

    // DND設定フォーム保存
    document.getElementById('dndSettingsForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const ok = await saveDndSettingsInternal();
      if (ok) {
        showToast('おやすみ・会議モード (DND) 設定を保存しました！', 'success');
        loadDndStatus();
      }
    });

    // 履歴クリア
    document.getElementById('btnClearDndHistory')?.addEventListener('click', async () => {
      if (confirm('サイレント履歴をクリアしてもよろしいですか？')) {
        try {
          await fetch('/api/dnd/history', { method: 'DELETE' });
          state.dndHistory = [];
          renderDndHistory();
          showToast('サイレント履歴をクリアしました', 'success');
        } catch (e) {
          showToast('履歴クリア失敗: ' + e.message, 'error');
        }
      }
    });
  }

  // ================= 6. ユーティリティ =================
  async function playHistoryPreview(text, voice, btn) {
    if (!text) return;
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-pulse"></span> 再生中...`;

    try {
      const params = new URLSearchParams({
        text,
        voice: voice || el.sayVoiceSelect?.value || 'ja-JP-NanamiNeural',
        rate: '+0%',
        pitch: '+0Hz'
      });
      const audioUrl = `/api/preview?${params.toString()}`;

      if (el.audioPreviewPlayer) {
        el.audioPreviewPlayer.src = audioUrl;
        el.audioPreviewWrapper.style.display = 'block';
        await el.audioPreviewPlayer.play();
        showToast('試聴音声を再生しました');
      }
    } catch (err) {
      showToast('試聴の再生に失敗しました: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }

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

  // ================= 8. 拡張・システム設定 (チャイム、重複ブロック、カスタムグループ、自動音量、IPエイリアス) =================
  async function loadSettings() {
    try {
      const res = await fetch('/api/settings');
      if (!res.ok) throw new Error('設定取得失敗');
      const data = await res.json();
      state.settings = data;
      state.ipAliases = data.ipAliases || {};
      state.deviceGroups = data.deviceGroups || {};

      // 1. チャイム設定
      const chimeSelect = document.getElementById('settingDefaultChime');
      if (chimeSelect && data.chime !== undefined) {
        chimeSelect.value = data.chime;
      }

      // 2. 重複通知ブロック
      const dedupeCheck = document.getElementById('settingDedupeEnabled');
      const dedupeInput = document.getElementById('settingDedupeCooldown');
      if (dedupeCheck) dedupeCheck.checked = data.deduplication?.enabled !== false;
      if (dedupeInput) dedupeInput.value = data.deduplication?.cooldownSeconds || 30;

      // 3. 自動音量カーブ
      const autoVolCheck = document.getElementById('settingAutoVolEnabled');
      if (autoVolCheck) autoVolCheck.checked = data.autoVolume?.enabled !== false;

      const rules = data.autoVolume?.rules || [];
      const dayRule = rules.find(r => r.id === 'day') || { volume: 50 };
      const eveningRule = rules.find(r => r.id === 'evening') || { volume: 25 };
      const nightRule = rules.find(r => r.id === 'night') || { volume: 10 };

      const rangeDay = document.getElementById('rangeAutoVolDay');
      const labelDay = document.getElementById('labelAutoVolDay');
      const rangeEve = document.getElementById('rangeAutoVolEvening');
      const labelEve = document.getElementById('labelAutoVolEvening');
      const rangeNight = document.getElementById('rangeAutoVolNight');
      const labelNight = document.getElementById('labelAutoVolNight');

      if (rangeDay) rangeDay.value = dayRule.volume;
      if (labelDay) labelDay.textContent = `${dayRule.volume}%`;
      if (rangeEve) rangeEve.value = eveningRule.volume;
      if (labelEve) labelEve.textContent = `${eveningRule.volume}%`;
      if (rangeNight) rangeNight.value = nightRule.volume;
      if (labelNight) labelNight.textContent = `${nightRule.volume}%`;

      // 4. 同調エンジン (Sync Engine)
      const syncEngine = data.syncEngine || {};
      const syncCheck = document.getElementById('settingSyncEnabled');
      const syncPreferNative = document.getElementById('settingSyncPreferNative');
      const syncDynamicAdjust = document.getElementById('settingSyncDynamicAdjust');
      const rangeGoogleDelay = document.getElementById('rangeSyncGoogleDelay');
      const labelGoogleDelay = document.getElementById('labelSyncGoogleDelay');
      const rangeHomepodDelay = document.getElementById('rangeSyncHomepodDelay');
      const labelHomepodDelay = document.getElementById('labelSyncHomepodDelay');

      if (syncCheck) syncCheck.checked = syncEngine.enabled !== false;
      if (syncPreferNative) syncPreferNative.checked = syncEngine.preferNativeGroups !== false;
      if (syncDynamicAdjust) syncDynamicAdjust.checked = syncEngine.dynamicAutoAdjust !== false;

      const gDelay = syncEngine.googleDelayMs !== undefined ? syncEngine.googleDelayMs : 1100;
      const hpDelay = syncEngine.homepodDelayMs !== undefined ? syncEngine.homepodDelayMs : 650;

      if (rangeGoogleDelay) rangeGoogleDelay.value = gDelay;
      if (labelGoogleDelay) labelGoogleDelay.textContent = `${gDelay} ms`;
      if (rangeHomepodDelay) rangeHomepodDelay.value = hpDelay;
      if (labelHomepodDelay) labelHomepodDelay.textContent = `${hpDelay} ms`;

      // RTT 統計表示
      const stats = syncEngine.stats || {};
      const statGoogle = document.getElementById('statGoogleRtt');
      const statHp = document.getElementById('statHomepodRtt');
      const statAlexa = document.getElementById('statAlexaRtt');
      if (statGoogle) statGoogle.textContent = `${stats.googleAvgRttMs || 420}ms`;
      if (statHp) statHp.textContent = `${stats.homepodAvgRttMs || 850}ms`;
      if (statAlexa) statAlexa.textContent = `${stats.alexaAvgRttMs || 1600}ms`;

      // 5. カスタム部屋グループの描画
      renderDeviceGroups();

      // 6. IPエイリアスの描画
      renderIpAliases();

      // 6. Webhookビルダーのマクロチップも再描画
      renderBuilderCustomGroupChips();

      // 7. 履歴一覧がすでに描画されている場合、エイリアス設定でIPタグを更新 (エイリアス登録済みIPは非リンク化)
      if (state.historyItems && state.historyItems.length > 0) {
        renderFullHistory();
      }
    } catch (e) {
      console.warn('システム設定読み込みエラー:', e.message);
    }
  }

  // カスタム部屋グループ一覧描画
  function renderDeviceGroups() {
    const container = document.getElementById('deviceGroupsContainer');
    if (!container) return;

    const groups = state.deviceGroups || {};
    const entries = Object.entries(groups);

    if (entries.length === 0) {
      container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; padding: 8px 0;">登録済みのカスタムグループはありません（「＋ 新規グループ」から作成できます）。</div>';
      return;
    }

    container.innerHTML = entries.map(([name, members]) => {
      const memberChips = (members || []).map(m => `<span class="group-member-chip">${escapeHtml(m)}</span>`).join(' ');
      return `
        <div class="group-card-item">
          <div>
            <div class="group-name-tag">
              <span>🏠</span> <strong>${escapeHtml(name)}</strong>
              <small style="color: var(--text-muted); font-weight: normal; margin-left: 6px;">(${members?.length || 0} 台)</small>
            </div>
            <div class="group-members-list">
              ${memberChips || '<span style="color: var(--text-muted); font-size: 0.75rem;">所属スピーカーなし</span>'}
            </div>
          </div>
          <button type="button" class="btn-chip text-danger btn-delete-group" data-name="${escapeHtml(name)}" title="グループ削除" style="padding: 4px 10px;">
            削除
          </button>
        </div>
      `;
    }).join('');

    container.querySelectorAll('.btn-delete-group').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const name = e.target.getAttribute('data-name');
        if (!confirm(`カスタムグループ「${name}」を削除しますか？`)) return;

        delete state.deviceGroups[name];
        await saveAllSettings({ silent: true });
        renderDeviceGroups();
        renderBuilderCustomGroupChips();
        showToast(`グループ「${name}」を削除しました`, 'success');
      });
    });
  }

  // IPエイリアス一覧描画
  function renderIpAliases() {
    const container = document.getElementById('ipAliasesContainer');
    if (!container) return;

    const aliases = state.ipAliases || {};
    const entries = Object.entries(aliases);

    if (entries.length === 0) {
      container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; padding: 6px 0;">登録済みの IP エイリアスはありません。</div>';
      return;
    }

    container.innerHTML = entries.map(([ip, name]) => `
      <div class="ip-alias-item">
        <div>
          <code>${escapeHtml(ip)}</code>
          <strong style="margin-left: 8px; color: #ffffff;">${escapeHtml(name)}</strong>
        </div>
        <button type="button" class="btn-chip text-danger btn-delete-alias" data-ip="${escapeHtml(ip)}" title="削除" style="padding: 2px 8px; font-size: 0.75rem;">
          削除
        </button>
      </div>
    `).join('');

    container.querySelectorAll('.btn-delete-alias').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const ip = e.target.getAttribute('data-ip');
        if (!confirm(`IP「${ip}」のエイリアスを削除しますか？`)) return;

        delete state.ipAliases[ip];
        if (state.settings && state.settings.ipAliases) {
          delete state.settings.ipAliases[ip];
        }
        await saveAllSettings({ silent: true });
        renderIpAliases();
        if (state.historyItems && state.historyItems.length > 0) {
          renderFullHistory();
        }
        showToast('IP エイリアスを削除しました', 'success');
      });
    });
  }

  // 全システム設定の保存
  async function saveAllSettings(options = {}) {
    try {
      const chime = document.getElementById('settingDefaultChime')?.value || 'dingdong';
      const dedupeEnabled = document.getElementById('settingDedupeEnabled')?.checked !== false;
      const dedupeCooldown = parseInt(document.getElementById('settingDedupeCooldown')?.value || '30', 10);

      const autoVolEnabled = document.getElementById('settingAutoVolEnabled')?.checked !== false;
      const volDay = parseInt(document.getElementById('rangeAutoVolDay')?.value || '50', 10);
      const volEvening = parseInt(document.getElementById('rangeAutoVolEvening')?.value || '25', 10);
      const volNight = parseInt(document.getElementById('rangeAutoVolNight')?.value || '10', 10);

      // 同調エンジン (Sync Engine) の設定
      const syncEnabled = document.getElementById('settingSyncEnabled')?.checked !== false;
      const syncPreferNative = document.getElementById('settingSyncPreferNative')?.checked !== false;
      const syncDynamicAdjust = document.getElementById('settingSyncDynamicAdjust')?.checked !== false;
      const googleDelayMs = parseInt(document.getElementById('rangeSyncGoogleDelay')?.value || '1100', 10);
      const homepodDelayMs = parseInt(document.getElementById('rangeSyncHomepodDelay')?.value || '650', 10);

      const payload = {
        chime,
        deduplication: {
          enabled: dedupeEnabled,
          cooldownSeconds: dedupeCooldown
        },
        autoVolume: {
          enabled: autoVolEnabled,
          rules: [
            { id: 'day', name: '日中 (07:00〜21:00)', startTime: '07:00', endTime: '21:00', volume: volDay },
            { id: 'evening', name: '夜間 (21:00〜23:00)', startTime: '21:00', endTime: '23:00', volume: volEvening },
            { id: 'night', name: '深夜 (23:00〜07:00)', startTime: '23:00', endTime: '07:00', volume: volNight }
          ]
        },
        syncEngine: {
          enabled: syncEnabled,
          preferNativeGroups: syncPreferNative,
          dynamicAutoAdjust: syncDynamicAdjust,
          alexaDelayMs: 0,
          homepodDelayMs,
          googleDelayMs
        },
        deviceGroups: state.deviceGroups || {},
        ipAliases: state.ipAliases || {}
      };

      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('設定保存失敗');
      const updated = await res.json();
      state.settings = updated;

      if (!options.silent) {
        showToast('システム設定を保存しました', 'success');
      }
      renderBuilderCustomGroupChips();
      return true;
    } catch (e) {
      showToast('設定保存エラー: ' + e.message, 'error');
      return false;
    }
  }

  function setupSettingsHandlers() {
    // 1. チャイム試聴ボタン
    document.getElementById('btnPreviewChime')?.addEventListener('click', () => {
      const chime = document.getElementById('settingDefaultChime')?.value || 'dingdong';
      if (chime === 'none') {
        showToast('「チャイムなし」が選択されています', 'info');
        return;
      }
      const audio = new Audio(`/sound/${chime}.mp3`);
      audio.play().catch(e => {
        showToast('チャイム試聴再生エラー: ' + e.message, 'error');
      });
    });

    // 2. 自動音量スライダー値のリアルタイム表示
    const rangeDay = document.getElementById('rangeAutoVolDay');
    const labelDay = document.getElementById('labelAutoVolDay');
    const rangeEve = document.getElementById('rangeAutoVolEvening');
    const labelEve = document.getElementById('labelAutoVolEvening');
    const rangeNight = document.getElementById('rangeAutoVolNight');
    const labelNight = document.getElementById('labelAutoVolNight');

    rangeDay?.addEventListener('input', (e) => {
      if (labelDay) labelDay.textContent = `${e.target.value}%`;
    });
    rangeEve?.addEventListener('input', (e) => {
      if (labelEve) labelEve.textContent = `${e.target.value}%`;
    });
    rangeNight?.addEventListener('input', (e) => {
      if (labelNight) labelNight.textContent = `${e.target.value}%`;
    });

    // 3. 同調遅延スライダー値のリアルタイム表示
    const rangeGoogleDelay = document.getElementById('rangeSyncGoogleDelay');
    const labelGoogleDelay = document.getElementById('labelSyncGoogleDelay');
    const rangeHomepodDelay = document.getElementById('rangeSyncHomepodDelay');
    const labelHomepodDelay = document.getElementById('labelSyncHomepodDelay');

    rangeGoogleDelay?.addEventListener('input', (e) => {
      if (labelGoogleDelay) labelGoogleDelay.textContent = `${e.target.value} ms`;
    });
    rangeHomepodDelay?.addEventListener('input', (e) => {
      if (labelHomepodDelay) labelHomepodDelay.textContent = `${e.target.value} ms`;
    });

    // 4. 同調テスト再生ボタン
    document.getElementById('btnSyncTestPlay')?.addEventListener('click', async () => {
      const btn = document.getElementById('btnSyncTestPlay');
      const originalHtml = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span>⏳</span> <span>同調テスト中...</span>';
      showToast('同調テスト再生を実行中...（各スピーカーの実測RTTを学習中）', 'info');

      try {
        const res = await fetch('/api/settings/sync-test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: 'ポーン♪ マルチスピーカー同調テストです。',
            targets: ['ALL']
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '同調テストに失敗しました');

        showToast('同調テスト再生が完了しました！', 'success');

        // 最新の syncEngine 設定と RTT 統計を画面に即時反映
        if (data.syncEngine) {
          if (state.settings) state.settings.syncEngine = data.syncEngine;
          const se = data.syncEngine;
          const rangeG = document.getElementById('rangeSyncGoogleDelay');
          const labelG = document.getElementById('labelSyncGoogleDelay');
          const rangeHp = document.getElementById('rangeSyncHomepodDelay');
          const labelHp = document.getElementById('labelSyncHomepodDelay');
          if (rangeG && se.googleDelayMs !== undefined) {
            rangeG.value = se.googleDelayMs;
            if (labelG) labelG.textContent = `${se.googleDelayMs} ms`;
          }
          if (rangeHp && se.homepodDelayMs !== undefined) {
            rangeHp.value = se.homepodDelayMs;
            if (labelHp) labelHp.textContent = `${se.homepodDelayMs} ms`;
          }
          const st = se.stats || {};
          const statG = document.getElementById('statGoogleRtt');
          const statH = document.getElementById('statHomepodRtt');
          const statA = document.getElementById('statAlexaRtt');
          if (statG && st.googleAvgRttMs) statG.textContent = `${st.googleAvgRttMs}ms`;
          if (statH && st.homepodAvgRttMs) statH.textContent = `${st.homepodAvgRttMs}ms`;
          if (statA && st.alexaAvgRttMs) statA.textContent = `${st.alexaAvgRttMs}ms`;
        }
      } catch (err) {
        showToast('同調テストエラー: ' + err.message, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
      }
    });

    // 5. 全設定保存ボタン
    document.getElementById('btnSaveAllSettings')?.addEventListener('click', async () => {
      await saveAllSettings();
    });

    // 4. IPエイリアス追加ボタン
    document.getElementById('btnAddIpAlias')?.addEventListener('click', async () => {
      const inputIp = document.getElementById('inputNewAliasIp');
      const inputName = document.getElementById('inputNewAliasName');
      const ip = (inputIp?.value || '').trim();
      const name = (inputName?.value || '').trim();

      if (!ip || !name) {
        showToast('IPアドレスと表示名の両方を入力してください', 'warning');
        return;
      }

      state.ipAliases = state.ipAliases || {};
      state.ipAliases[ip] = name;
      if (state.settings) {
        state.settings.ipAliases = state.ipAliases;
      }
      await saveAllSettings({ silent: true });
      renderIpAliases();
      if (state.historyItems && state.historyItems.length > 0) {
        renderFullHistory();
      }

      if (inputIp) inputIp.value = '';
      if (inputName) inputName.value = '';
      showToast(`IP「${ip}」を「${name}」として登録しました`, 'success');
    });

    // 5. カスタムグループモーダル関連
    const groupModal = document.getElementById('modalDeviceGroup');
    const inputGroupName = document.getElementById('inputGroupName');
    const groupCheckboxesContainer = document.getElementById('groupSpeakerCheckboxes');

    // モーダルを開く
    document.getElementById('btnOpenNewGroupModal')?.addEventListener('click', () => {
      if (inputGroupName) inputGroupName.value = '';
      if (groupCheckboxesContainer) {
        const devs = state.devices || [];
        if (!devs.length) {
          groupCheckboxesContainer.innerHTML = '<span class="text-sub">利用可能なスピーカーがありません</span>';
        } else {
          groupCheckboxesContainer.innerHTML = devs.map(d => `
            <label class="speaker-chip" style="cursor: pointer;">
              <input type="checkbox" value="${escapeHtml(d.name || d.ip)}" style="margin-right: 6px;">
              <span>${escapeHtml(d.name || d.ip)}</span>
            </label>
          `).join('');

          groupCheckboxesContainer.querySelectorAll('input[type="checkbox"]').forEach(c => {
            c.addEventListener('change', (e) => {
              e.target.closest('.speaker-chip')?.classList.toggle('checked', e.target.checked);
            });
          });
        }
      }
      if (groupModal) groupModal.style.display = 'flex';
    });

    // モーダルを閉じる
    document.getElementById('btnCloseGroupModal')?.addEventListener('click', () => {
      if (groupModal) groupModal.style.display = 'none';
    });
    document.getElementById('btnCancelGroupModal')?.addEventListener('click', () => {
      if (groupModal) groupModal.style.display = 'none';
    });

    // グループ保存
    document.getElementById('btnSaveGroupModal')?.addEventListener('click', async () => {
      const name = (inputGroupName?.value || '').trim();
      if (!name) {
        showToast('グループ名を入力してください', 'warning');
        return;
      }

      const checked = Array.from(groupCheckboxesContainer?.querySelectorAll('input[type="checkbox"]:checked') || [])
        .map(c => c.value);

      if (!checked.length) {
        showToast('所属させるスピーカーを1台以上選択してください', 'warning');
        return;
      }

      state.deviceGroups = state.deviceGroups || {};
      state.deviceGroups[name] = checked;

      await saveAllSettings({ silent: true });
      renderDeviceGroups();
      renderBuilderCustomGroupChips();

      if (groupModal) groupModal.style.display = 'none';
      showToast(`カスタムグループ「${name}」を保存しました`, 'success');
    });
  }

  // ================= 9. AI 連携設定 (Google Gemini / OpenAI) =================
  async function loadAiModels(provider = 'gemini', forceRefresh = false, keyOverride = null) {
    const selectEl = document.getElementById(provider === 'gemini' ? 'selectGeminiModel' : 'selectOpenAiModel');
    const alertEl = document.getElementById(provider === 'gemini' ? 'geminiModelAlert' : 'openaiModelAlert');
    const refreshBtn = document.getElementById(provider === 'gemini' ? 'btnRefreshGeminiModels' : 'btnRefreshOpenAiModels');

    if (!selectEl) return;

    if (refreshBtn) {
      refreshBtn.disabled = true;
      refreshBtn.textContent = '🔄 取得中...';
    }

    try {
      const apiKey = keyOverride || (provider === 'gemini'
        ? document.getElementById('inputGeminiApiKey')?.value?.trim()
        : document.getElementById('inputOpenAiApiKey')?.value?.trim());

      const params = new URLSearchParams({ provider });
      if (forceRefresh) params.set('forceRefresh', 'true');
      if (apiKey) params.set('apiKey', apiKey);

      const res = await fetch(`/api/ai/models?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const models = data.models || [];
      const currentSelected = selectEl.value || data.currentModel || (provider === 'gemini' ? 'gemini-3.8-flash' : 'gpt-4o-mini');

      selectEl.replaceChildren();

      models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.name || m.id;
        if (m.id === currentSelected || m.id === data.currentModel) {
          opt.selected = true;
        }
        selectEl.appendChild(opt);
      });

      // 以前の選択モデルが提供終了している場合のアラート表示
      if (data.isCurrentModelEnded || data.notice) {
        if (alertEl) {
          alertEl.style.display = 'block';
          alertEl.textContent = `⚠️ ${data.notice || `以前選択されていたモデルは終了したため、最新の「${data.currentModel}」に自動切り替えされました。`}`;
        }
        selectEl.value = data.currentModel;
      } else {
        if (alertEl) {
          alertEl.style.display = 'none';
          alertEl.textContent = '';
        }
      }
    } catch (err) {
      console.warn(`[AI] ${provider} モデル一覧取得エラー:`, err.message);
    } finally {
      if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.textContent = '🔄 最新モデル再取得';
      }
    }
  }

  async function loadAiSettings() {
    try {
      const [statusRes, settingsRes] = await Promise.all([
        fetch('/api/ai/status'),
        fetch('/api/settings')
      ]);
      if (!statusRes.ok) return;
      const aiStatus = await statusRes.json();
      state.aiStatus = aiStatus;
      const settings = settingsRes.ok ? await settingsRes.json() : {};
      const ai = settings.ai || {};

      // マスター有効/無効
      const masterCheck = document.getElementById('aiMasterEnabled');
      if (masterCheck) masterCheck.checked = ai.enabled !== false;

      // プロバイダ
      const currentProvider = ai.provider || aiStatus.provider || 'gemini';
      const providerRadio = document.querySelector(`input[name="aiProvider"][value="${currentProvider}"]`);
      if (providerRadio) providerRadio.checked = true;

      const geminiCard = document.getElementById('geminiConfigCard');
      const openaiCard = document.getElementById('openaiConfigCard');
      if (geminiCard) geminiCard.style.display = (currentProvider === 'gemini') ? 'block' : 'none';
      if (openaiCard) openaiCard.style.display = (currentProvider === 'openai') ? 'block' : 'none';

      // Gemini 設定
      const geminiInput = document.getElementById('inputGeminiApiKey');
      const geminiBadge = document.getElementById('geminiSourceBadge');
      if (geminiInput) {
        geminiInput.value = ai.geminiApiKey || '';
        if (aiStatus.gemini?.source === 'env') {
          geminiInput.placeholder = `環境変数 (.env) で設定中: ${aiStatus.gemini.keyMasked}`;
        } else if (aiStatus.gemini?.keyMasked) {
          geminiInput.placeholder = `保存済み: ${aiStatus.gemini.keyMasked}`;
        } else {
          geminiInput.placeholder = 'AIzaSy... (API Key を入力)';
        }
      }
      if (geminiBadge) {
        if (aiStatus.gemini?.source === 'env') {
          geminiBadge.textContent = '環境変数 (.env)';
          geminiBadge.style.color = '#10b981';
        } else if (aiStatus.gemini?.source === 'settings') {
          geminiBadge.textContent = '保存済み (Web設定)';
          geminiBadge.style.color = '#60a5fa';
        } else {
          geminiBadge.textContent = '未設定';
          geminiBadge.style.color = 'var(--text-muted)';
        }
      }

      // OpenAI 設定
      const openaiInput = document.getElementById('inputOpenAiApiKey');
      const openaiBadge = document.getElementById('openaiSourceBadge');
      if (openaiInput) {
        openaiInput.value = ai.openaiApiKey || '';
        if (aiStatus.openai?.source === 'env') {
          openaiInput.placeholder = `環境変数 (.env) で設定中: ${aiStatus.openai.keyMasked}`;
        } else if (aiStatus.openai?.keyMasked) {
          openaiInput.placeholder = `保存済み: ${aiStatus.openai.keyMasked}`;
        } else {
          openaiInput.placeholder = 'sk-... (API Key を入力)';
        }
      }
      if (openaiBadge) {
        if (aiStatus.openai?.source === 'env') {
          openaiBadge.textContent = '環境変数 (.env)';
          openaiBadge.style.color = '#10b981';
        } else if (aiStatus.openai?.source === 'settings') {
          openaiBadge.textContent = '保存済み (Web設定)';
          openaiBadge.style.color = '#60a5fa';
        } else {
          openaiBadge.textContent = '未設定';
          openaiBadge.style.color = 'var(--text-muted)';
        }
      }

      // モデル動的一覧の取得
      await Promise.all([
        loadAiModels('gemini'),
        loadAiModels('openai')
      ]);

      const geminiModelSelect = document.getElementById('selectGeminiModel');
      if (geminiModelSelect && ai.geminiModel) {
        // もし退役モデルだった場合は loadAiModels 内で既に自己修復済み
        if (Array.from(geminiModelSelect.options).some(o => o.value === ai.geminiModel)) {
          geminiModelSelect.value = ai.geminiModel;
        }
      }

      const openaiModelSelect = document.getElementById('selectOpenAiModel');
      if (openaiModelSelect && ai.openaiModel) {
        if (Array.from(openaiModelSelect.options).some(o => o.value === ai.openaiModel)) {
          openaiModelSelect.value = ai.openaiModel;
        }
      }

      // DND 保留要約オプション
      const summarizeQueueCheck = document.getElementById('aiSummarizeDndQueue');
      if (summarizeQueueCheck) summarizeQueueCheck.checked = ai.summarizeDndQueue !== false;

      const thresholdSelect = document.getElementById('aiSummaryThresholdSelect');
      if (thresholdSelect) thresholdSelect.value = String(ai.summaryThreshold || 2);

      const customPromptInput = document.getElementById('aiCustomPrompt');
      if (customPromptInput) customPromptInput.value = ai.customPrompt || '';

      // 朝の予定まとめ (デイリーサマリー) AI連携
      const summarizeCalendarCheck = document.getElementById('aiSummarizeDailyCalendar');
      if (summarizeCalendarCheck) summarizeCalendarCheck.checked = ai.summarizeDailyCalendar !== false;

      const dailyPromptInput = document.getElementById('aiDailyCalendarPrompt');
      if (dailyPromptInput) dailyPromptInput.value = ai.dailyCalendarPrompt || '';

      // バナー更新
      renderAiBanner();
      updateDndAiBadge();
    } catch (e) {
      console.warn('AI設定取得失敗:', e);
    }
  }

  function renderAiBanner() {
    const s = state.aiStatus || {};
    const banner = document.getElementById('aiStatusBanner');
    const dot = document.getElementById('aiStatusDot');
    const title = document.getElementById('aiStatusTitle');
    const subtitle = document.getElementById('aiStatusSubtitle');
    const badge = document.getElementById('aiActiveProviderBadge');

    const provider = s.provider || 'gemini';
    const hasKey = (provider === 'gemini') ? s.gemini?.hasKey : s.openai?.hasKey;
    const isMasterOn = s.enabled !== false;

    if (badge) {
      badge.textContent = provider === 'gemini' ? 'Google Gemini' : 'OpenAI';
    }

    if (!isMasterOn) {
      if (dot) {
        dot.style.background = '#94a3b8';
        dot.style.boxShadow = 'none';
      }
      if (title) title.textContent = 'AI 連携機能: 無効';
      if (subtitle) subtitle.textContent = 'スイッチをONにするとAIによるDND保留通知の要約が有効になります';
      if (banner) {
        banner.style.background = 'rgba(255, 255, 255, 0.03)';
        banner.style.borderColor = 'rgba(255, 255, 255, 0.1)';
      }
    } else if (hasKey) {
      if (dot) {
        dot.style.background = '#10b981';
        dot.style.boxShadow = '0 0 10px #10b981';
      }
      if (title) title.textContent = `🟢 AI 連携機能: 稼働中 (${provider === 'gemini' ? 'Gemini' : 'OpenAI'})`;
      if (subtitle) subtitle.textContent = 'API Key が正常に設定されています。DND解除時に複数通知を自動要約して1回で発話します。';
      if (banner) {
        banner.style.background = 'rgba(16, 185, 129, 0.1)';
        banner.style.borderColor = 'rgba(16, 185, 129, 0.3)';
      }
    } else {
      if (dot) {
        dot.style.background = '#f59e0b';
        dot.style.boxShadow = '0 0 8px #f59e0b';
      }
      if (title) title.textContent = '🟡 AI 連携機能: API Key 未設定';
      if (subtitle) subtitle.textContent = 'API Key を入力して保存するか、.my.env に設定すると自動要約が有効になります';
      if (banner) {
        banner.style.background = 'rgba(245, 158, 11, 0.1)';
        banner.style.borderColor = 'rgba(245, 158, 11, 0.3)';
      }
    }
  }

  function updateDndAiBadge() {
    const s = state.aiStatus || {};
    const badge = document.getElementById('dndAiBadgeStatus');
    if (!badge) return;
    const provider = s.provider || 'gemini';
    const hasKey = (provider === 'gemini') ? s.gemini?.hasKey : s.openai?.hasKey;
    if (s.enabled !== false && hasKey) {
      badge.textContent = `AI要約利用可 (${provider === 'gemini' ? 'Gemini' : 'OpenAI'})`;
      badge.style.color = '#10b981';
      badge.style.borderColor = 'rgba(16, 185, 129, 0.4)';
    } else {
      badge.textContent = 'API Key未設定 (個別読上)';
      badge.style.color = 'var(--text-muted)';
      badge.style.borderColor = 'rgba(255, 255, 255, 0.1)';
    }
  }

  function setupAiHandlers() {
    // プロバイダラジオ切り替え
    document.querySelectorAll('input[name="aiProvider"]').forEach(r => {
      r.addEventListener('change', (e) => {
        const geminiCard = document.getElementById('geminiConfigCard');
        const openaiCard = document.getElementById('openaiConfigCard');
        if (geminiCard) geminiCard.style.display = (e.target.value === 'gemini') ? 'block' : 'none';
        if (openaiCard) openaiCard.style.display = (e.target.value === 'openai') ? 'block' : 'none';
        if (state.aiStatus) state.aiStatus.provider = e.target.value;
        renderAiBanner();
        updateDndAiBadge();
      });
    });

    // 最新モデル再取得ボタン
    document.getElementById('btnRefreshGeminiModels')?.addEventListener('click', () => {
      loadAiModels('gemini', true);
    });

    document.getElementById('btnRefreshOpenAiModels')?.addEventListener('click', () => {
      loadAiModels('openai', true);
    });

    // キー可視性トグル
    document.getElementById('btnToggleGeminiKeyVisibility')?.addEventListener('click', () => {
      const inp = document.getElementById('inputGeminiApiKey');
      if (inp) {
        inp.type = inp.type === 'password' ? 'text' : 'password';
      }
    });

    document.getElementById('btnToggleOpenAiKeyVisibility')?.addEventListener('click', () => {
      const inp = document.getElementById('inputOpenAiApiKey');
      if (inp) {
        inp.type = inp.type === 'password' ? 'text' : 'password';
      }
    });

    // AI設定保存ボタン
    document.getElementById('btnSaveAiSettings')?.addEventListener('click', async () => {
      try {
        const enabled = document.getElementById('aiMasterEnabled')?.checked !== false;
        const provider = document.querySelector('input[name="aiProvider"]:checked')?.value || 'gemini';
        const geminiApiKey = document.getElementById('inputGeminiApiKey')?.value?.trim() || '';
        const selectGeminiModel = document.getElementById('selectGeminiModel')?.value || 'gemini-3.8-flash';
        const openaiApiKey = document.getElementById('inputOpenAiApiKey')?.value?.trim() || '';
        const selectOpenAiModel = document.getElementById('selectOpenAiModel')?.value || 'gpt-4o-mini';
        const summarizeDndQueue = document.getElementById('aiSummarizeDndQueue')?.checked !== false;
        const summaryThreshold = parseInt(document.getElementById('aiSummaryThresholdSelect')?.value || '2', 10);
        const customPrompt = document.getElementById('aiCustomPrompt')?.value?.trim() || '';
        const summarizeDailyCalendar = document.getElementById('aiSummarizeDailyCalendar')?.checked !== false;
        const dailyCalendarPrompt = document.getElementById('aiDailyCalendarPrompt')?.value?.trim() || '';

        const payload = {
          ai: {
            enabled,
            provider,
            geminiApiKey,
            geminiModel: selectGeminiModel,
            openaiApiKey,
            openaiModel: selectOpenAiModel,
            summarizeDndQueue,
            summaryThreshold,
            customPrompt,
            summarizeDailyCalendar,
            dailyCalendarPrompt
          }
        };

        const res = await fetch('/api/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error('保存失敗');
        showToast('AI API Key および 連携設定を保存しました', 'success');
        await loadAiSettings();
        await loadDndSettings();
      } catch (e) {
        showToast('AI設定保存エラー: ' + e.message, 'error');
      }
    });

    // マスター切り替え
    document.getElementById('aiMasterEnabled')?.addEventListener('change', async (e) => {
      try {
        const res = await fetch('/api/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ai: { enabled: e.target.checked } })
        });
        if (!res.ok) throw new Error('更新失敗');
        showToast(`AI連携を ${e.target.checked ? '有効化' : '無効化'} しました`, 'info');
        await loadAiSettings();
      } catch (err) {
        showToast('設定更新エラー: ' + err.message, 'error');
      }
    });

    // 接続テストボタン
    document.getElementById('btnTestAiConnection')?.addEventListener('click', async () => {
      const resultBox = document.getElementById('aiTestResultBox');
      const provider = document.querySelector('input[name="aiProvider"]:checked')?.value || 'gemini';
      const typedKey = (provider === 'gemini')
        ? document.getElementById('inputGeminiApiKey')?.value?.trim()
        : document.getElementById('inputOpenAiApiKey')?.value?.trim();
      const model = (provider === 'gemini')
        ? document.getElementById('selectGeminiModel')?.value
        : document.getElementById('selectOpenAiModel')?.value;

      if (resultBox) {
        resultBox.style.display = 'block';
        resultBox.style.background = 'rgba(99, 102, 241, 0.08)';
        resultBox.style.border = '1px solid rgba(99, 102, 241, 0.3)';
        resultBox.style.color = 'var(--text-color)';
        resultBox.textContent = `⏳ ${provider === 'gemini' ? 'Google Gemini' : 'OpenAI'} API と通信中...`;
      }

      try {
        const res = await fetch('/api/ai/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider,
            apiKey: typedKey || undefined,
            model
          })
        });

        const data = await res.json();
        if (data.success) {
          if (resultBox) {
            resultBox.style.background = 'rgba(16, 185, 129, 0.12)';
            resultBox.style.border = '1px solid rgba(16, 185, 129, 0.4)';
            resultBox.style.color = '#34d399';
            resultBox.replaceChildren();
            const strong = document.createElement('strong');
            strong.textContent = `✅ 接続成功！ (${data.provider === 'gemini' ? 'Gemini' : 'OpenAI'} / ${data.model})`;
            resultBox.appendChild(strong);

            if (data.notice) {
              const noticeP = document.createElement('div');
              noticeP.style.marginTop = '6px';
              noticeP.style.color = '#fbbf24';
              noticeP.style.fontWeight = '500';
              noticeP.textContent = `⚠️ ${data.notice}`;
              resultBox.appendChild(noticeP);
            }

            const p = document.createElement('div');
            p.style.marginTop = '4px';
            p.textContent = `AIからの応答: 「${data.reply}」`;
            resultBox.appendChild(p);
          }
          showToast('API Key 接続テストに成功しました！', 'success');
        } else {
          if (resultBox) {
            resultBox.style.background = 'rgba(239, 68, 68, 0.12)';
            resultBox.style.border = '1px solid rgba(239, 68, 68, 0.4)';
            resultBox.style.color = '#f87171';
            resultBox.replaceChildren();
            const strong = document.createElement('strong');
            strong.textContent = '❌ 接続失敗';
            const p = document.createElement('div');
            p.style.marginTop = '4px';
            p.textContent = data.error || '通信エラーが発生しました';
            resultBox.appendChild(strong);
            resultBox.appendChild(p);
          }
          showToast('接続テストに失敗しました: ' + (data.error || '不明なエラー'), 'error');
        }
      } catch (e) {
        if (resultBox) {
          resultBox.style.background = 'rgba(239, 68, 68, 0.12)';
          resultBox.style.border = '1px solid rgba(239, 68, 68, 0.4)';
          resultBox.style.color = '#f87171';
          resultBox.textContent = `❌ エラー: ${e.message}`;
        }
        showToast('接続テスト失敗: ' + e.message, 'error');
      }
    });

    // 朝の予定まとめテスト試聴ボタン
    document.getElementById('btnTestAiCalendarSummary')?.addEventListener('click', async () => {
      const resultBox = document.getElementById('aiTestResultBox');
      const dailyPrompt = document.getElementById('aiDailyCalendarPrompt')?.value?.trim();

      if (resultBox) {
        resultBox.style.display = 'block';
        resultBox.style.background = 'rgba(99, 102, 241, 0.08)';
        resultBox.style.border = '1px solid rgba(99, 102, 241, 0.3)';
        resultBox.style.color = 'var(--text-color)';
        resultBox.textContent = '⏳ サンプル予定3件（朝会・レビュー・用事）をもとに朝のアナウンス文章をAI生成中...';
      }

      try {
        const res = await fetch('/api/ai/calendar-test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ promptHint: dailyPrompt })
        });

        const data = await res.json();
        if (data.success && data.summary) {
          if (resultBox) {
            resultBox.style.background = 'rgba(59, 130, 246, 0.1)';
            resultBox.style.border = '1px solid rgba(59, 130, 246, 0.3)';
            resultBox.style.color = '#93c5fd';
            resultBox.replaceChildren();
            const strong = document.createElement('strong');
            strong.textContent = '🎙️ 朝の予定まとめ AIアナウンス生成結果 (音声をプレビュー中):';
            const p = document.createElement('div');
            p.style.marginTop = '4px';
            p.textContent = data.summary;
            resultBox.appendChild(strong);
            resultBox.appendChild(p);
          }
          // プレビュー再生
          const audio = new Audio(`/api/preview?text=${encodeURIComponent(data.summary)}`);
          audio.play().catch(err => console.warn('オーディオ再生ブロック:', err));
          showToast('朝の予定まとめテスト音声をブラウザで再生開始しました', 'success');
        } else {
          throw new Error(data.error || '予定まとめの生成に失敗しました');
        }
      } catch (err) {
        if (resultBox) {
          resultBox.style.background = 'rgba(239, 68, 68, 0.12)';
          resultBox.style.border = '1px solid rgba(239, 68, 68, 0.4)';
          resultBox.style.color = '#f87171';
          resultBox.textContent = `❌ 朝の予定まとめテスト失敗: ${err.message}`;
        }
        showToast('朝の予定まとめテストエラー: ' + err.message, 'error');
      }
    });

    // 要約テスト試聴ボタン
    document.getElementById('btnTestAiSummarize')?.addEventListener('click', async () => {
      const resultBox = document.getElementById('aiTestResultBox');
      const customPrompt = document.getElementById('aiCustomPrompt')?.value?.trim();

      if (resultBox) {
        resultBox.style.display = 'block';
        resultBox.style.background = 'rgba(99, 102, 241, 0.08)';
        resultBox.style.border = '1px solid rgba(99, 102, 241, 0.3)';
        resultBox.style.color = 'var(--text-color)';
        resultBox.textContent = '⏳ サンプル通知3件（宅配便・給湯器・室温）をAI要約中...';
      }

      try {
        const res = await fetch('/api/ai/summarize-test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ promptHint: customPrompt })
        });

        const data = await res.json();
        if (data.success && data.summary) {
          const speechText = `会議・おやすみモードが終了しました。保留されていた 3 件の通知をAIが要約してお知らせします。${data.summary}`;
          if (resultBox) {
            resultBox.style.background = 'rgba(59, 130, 246, 0.1)';
            resultBox.style.border = '1px solid rgba(59, 130, 246, 0.3)';
            resultBox.style.color = '#93c5fd';
            resultBox.replaceChildren();
            const strong = document.createElement('strong');
            strong.textContent = '📢 AI要約テスト結果 (プレビュー音声を再生中):';
            const p = document.createElement('div');
            p.style.marginTop = '4px';
            p.textContent = speechText;
            resultBox.appendChild(strong);
            resultBox.appendChild(p);
          }
          // プレビュー再生
          const audio = new Audio(`/api/preview?text=${encodeURIComponent(speechText)}`);
          audio.play().catch(err => console.warn('オーディオ再生ブロック:', err));
          showToast('要約テスト音声をブラウザで再生開始しました', 'success');
        } else {
          throw new Error(data.error || '要約の生成に失敗しました');
        }
      } catch (err) {
        if (resultBox) {
          resultBox.style.background = 'rgba(239, 68, 68, 0.12)';
          resultBox.style.border = '1px solid rgba(239, 68, 68, 0.4)';
          resultBox.style.color = '#f87171';
          resultBox.textContent = `❌ 要約テスト失敗: ${err.message}`;
        }
        showToast('要約テストエラー: ' + err.message, 'error');
      }
    });
  }

  // 起動実行
  init();
});
