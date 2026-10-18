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
    // 認証
    loginOverlay: document.getElementById('loginOverlay'),
    loginForm: document.getElementById('loginForm'),
    loginPassword: document.getElementById('loginPassword'),
    loginErrorMsg: document.getElementById('loginErrorMsg'),
    loginSubmitBtn: document.getElementById('loginSubmitBtn'),
    headerLogoutBtn: document.getElementById('headerLogoutBtn'),
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

  // 認証関連ヘルパー
  function showLoginOverlay() {
    if (!el.loginOverlay) return;
    el.loginOverlay.style.display = 'flex';
    if (el.loginErrorMsg) el.loginErrorMsg.style.display = 'none';
    if (el.loginPassword) {
      el.loginPassword.value = '';
      setTimeout(() => el.loginPassword.focus(), 100);
    }
  }

  function hideLoginOverlay() {
    if (el.loginOverlay) el.loginOverlay.style.display = 'none';
  }

  async function checkAuthStatus() {
    try {
      const res = await fetch('/api/auth/status');
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('[Auth] ステータス取得エラー:', e.message);
    }
    return { authRequired: false, authenticated: true };
  }

  // ================= 1. 初期データ読み込み =================
  async function init() {
    setupEventListeners();
    setupWebhookBuilder();
    setupCalendarHandlers();
    setupDndHandlers();
    setupSettingsHandlers();
    setupAiHandlers();
    setupDisasterHandlers();
    setupOnvifSettings();
    setupMqttSettings();
    setupMcpSettings();



    // 認証ステータスの確認 (ADMIN_PASSWORD 設定時)
    const auth = await checkAuthStatus();
    if (auth.authRequired) {
      if (!auth.authenticated) {
        showLoginOverlay();
        return;
      }
      if (el.headerLogoutBtn) el.headerLogoutBtn.style.display = 'inline-flex';
    }

    await loadInitialData();

    // DND ステータスを定期ポーリング (15秒ごと)
    setInterval(loadDndStatus, 15000);
  }

  async function loadInitialData() {
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
      loadAiSettings(),
      loadDisasterSettings()
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
      updateDefaultDeviceDisplay();
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
      if (type === 'dlna') return 7;   // DLNA
      if (type === 'onvif') return 8;  // ONVIF
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
  // 全スピーカーセレクター（Say, Sched, Cal, DND, Disaster, Webhookビルダー）の一括再描画
  function renderAllSpeakerSelectors() {
    const curSay = getSelectedSpeakers(el.saySpeakersContainer);
    renderSpeakersCheckboxes(el.saySpeakersContainer, 'saySpeaker', curSay.length ? curSay : (state.serverInfo?.defaultDeviceIp ? [state.serverInfo.defaultDeviceIp] : []));

    const curSched = getSelectedSpeakers(el.schedSpeakersContainer);
    renderSpeakersCheckboxes(el.schedSpeakersContainer, 'schedSpeaker', curSched.length ? curSched : ['default']);

    renderCalendarSpeakers();
    renderDndSpeakers();
    renderDisasterSpeakers();
    renderBuilderSpeakers();
    renderBuilderCustomGroupChips();
    if (typeof renderMqttSpeakerOptions === 'function') renderMqttSpeakerOptions();
    if (typeof window.renderMcpSpeakerOptions === 'function') window.renderMcpSpeakerOptions();
    updateBuilderCode();
  }

  function updateDefaultDeviceDisplay() {
    if (!el.defaultDeviceText) return;
    const defIp = state.serverInfo?.defaultDeviceIp || '';
    const defName = state.serverInfo?.defaultDeviceName || '';

    if (defName && defName !== defIp) {
      el.defaultDeviceText.textContent = `デフォルト: ${defName}`;
      el.defaultDeviceText.title = `標準スピーカー: ${defName} (${defIp})`;
      return;
    }

    if (defIp) {
      const found = (state.devices || []).find(d => d.ip === defIp || d.host === defIp || d.id === defIp);
      if (found && found.name) {
        const dName = formatSpeakerDisplayName(found.name);
        el.defaultDeviceText.textContent = `デフォルト: ${dName}`;
        el.defaultDeviceText.title = `標準スピーカー: ${dName} (${defIp})`;
      } else {
        el.defaultDeviceText.textContent = `デフォルト: ${defIp}`;
      }
    } else {
      el.defaultDeviceText.textContent = 'デフォルト未設定';
    }
  }

  // デバイス一覧取得 & 画面反映
  async function loadDevices() {
    try {
      const res = await fetch('/api/devices');
      if (!res.ok) throw new Error('デバイス取得失敗');
      const data = await res.json();
      state.devices = sortDevicesList(data.devices || []);

      renderDevicesGrid();
      renderAllSpeakerSelectors();
      updateDefaultDeviceDisplay();
      if (typeof renderScheduleTable === 'function') renderScheduleTable();
      if (typeof renderDeviceGroups === 'function') renderDeviceGroups();
      if (typeof renderFullHistory === 'function') renderFullHistory();
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
      state.history = Array.isArray(data) ? data : (data.history || []);

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

  // IP/ID/短縮名から最適な日本語表示デバイス名を取得する共通解決関数
  function getDeviceDisplayName(target) {
    if (!target) return '';
    const t = String(target).trim();
    if (t === 'default') return 'デフォルト (標準)';

    // 1. 完全一致 (ip, host, id, name)
    let found = (state.devices || []).find(d => d.ip === t || d.host === t || d.id === t || d.name === t);

    // 2. ポートなしIP/プレフィックス除去での一致
    if (!found) {
      const cleanIp = t.includes(':') && !t.startsWith('alexa:') && !t.startsWith('homepod:') && !t.startsWith('onvif:')
        ? t.split(':')[0]
        : t;
      found = (state.devices || []).find(d => d.host === cleanIp || (d.ip && d.ip.split(':')[0] === cleanIp));
    }

    // 3. 名前 (小文字一致)
    if (!found) {
      found = (state.devices || []).find(d => d.name && d.name.toLowerCase() === t.toLowerCase());
    }

    if (found && found.name) {
      return formatSpeakerDisplayName(found.name);
    }

    // 4. IPエイリアス設定にあればエイリアス名
    if (state.settings?.ipAliases && state.settings.ipAliases[t]) {
      return state.settings.ipAliases[t];
    }

    // 5. 特殊グループマクロ名
    if (t.toUpperCase() === 'ALL') return 'ALL (全スピーカー)';
    if (t.toUpperCase() === 'GH:ALL') return 'GH:ALL (Google全台)';
    if (t.toUpperCase() === 'AL:ALL') return 'AL:ALL (Alexa全台)';
    if (t.toUpperCase() === 'HP:ALL') return 'HP:ALL (HomePod全台)';
    if (t.toUpperCase() === 'CAM:ALL') return 'CAM:ALL (カメラ全台)';

    return formatSpeakerDisplayName(t);
  }

  // 汎用マクロボタン群の描画とクリックイベント紐付け
  function renderMacroButtonsFor(macroContainer, targetGrid, nameAttr, onChangeCallback) {
    if (!macroContainer || !targetGrid) return;
    const hasGoogle = state.devices.some(d => d.type === 'google');
    const hasAlexa = state.devices.some(d => d.type === 'alexa' || d.ip.startsWith('alexa:'));
    const hasHomePod = state.devices.some(d => d.type === 'homepod' || d.ip.startsWith('homepod:'));
    const hasOnvif = state.devices.some(d => d.type === 'onvif');
    const groups = state.settings?.deviceGroups || {};
    const groupNames = Object.keys(groups);

    let html = `
      <button type="button" class="btn-chip btn-macro" data-macro="ALL" title="全スピーカーを選択">⚡ ALL (全台)</button>
    `;
    if (hasGoogle) {
      html += `<button type="button" class="btn-chip btn-macro" data-macro="GH:ALL" title="Google Home全台を選択">⚡ GH:ALL (Google全台)</button>`;
    }
    if (hasAlexa) {
      html += `<button type="button" class="btn-chip btn-macro" data-macro="AL:ALL" title="Alexa全台を選択">⚡ AL:ALL (Alexa全台)</button>`;
    }
    if (hasHomePod) {
      html += `<button type="button" class="btn-chip btn-macro" data-macro="HP:ALL" title="HomePod全台を選択">⚡ HP:ALL (HomePod全台)</button>`;
    }
    if (hasOnvif) {
      html += `<button type="button" class="btn-chip btn-macro" data-macro="CAM:ALL" title="ONVIFカメラ全台を選択">⚡ CAM:ALL (カメラ全台)</button>`;
    }
    // カスタム部屋グループボタン (グループ編集モーダル内では非表示)
    if (nameAttr !== 'groupSpeaker') {
      groupNames.forEach(grp => {
        html += `
          <button type="button" class="btn-chip btn-macro btn-custom-group" data-macro="${escapeHtml(grp)}" title="登録グループ [${escapeHtml(grp)}] を選択">
            ⚡ ${escapeHtml(grp)}
          </button>
        `;
      });
    }
    // クリアボタン
    html += `<button type="button" class="btn-chip text-danger btn-clear-macro">クリア</button>`;

    macroContainer.innerHTML = html;

    // イベントリスナー紐付け
    macroContainer.querySelectorAll('.btn-macro').forEach(btn => {
      btn.addEventListener('click', () => {
        const macro = btn.getAttribute('data-macro');
        const isAlreadyActive = btn.classList.contains('active');

        macroContainer.querySelectorAll('.btn-macro').forEach(b => b.classList.remove('active'));

        if (!isAlreadyActive) {
          btn.classList.add('active');

          targetGrid.querySelectorAll('input[type="checkbox"]').forEach(c => {
            const type = c.getAttribute('data-type');
            const devName = (c.closest('.speaker-chip')?.textContent || '').toLowerCase();
            const devIp = (c.value || '').toLowerCase();
            let match = false;

            if (macro === 'ALL') {
              match = (c.value !== 'default'); // ALL選択時は個別スピーカー全ON
            } else if (macro === 'GH:ALL') {
              match = (type === 'google');
            } else if (macro === 'AL:ALL') {
              match = (type === 'alexa');
            } else if (macro === 'HP:ALL') {
              match = (type === 'homepod');
            } else if (macro === 'CAM:ALL') {
              match = (type === 'onvif');
            } else if (groups[macro]) {
              const members = (groups[macro] || []).map(m => String(m).toLowerCase());
              match = members.some(m => m === devIp || m === c.value || devName.includes(m) || devIp.includes(m));
            }

            c.checked = match;
            c.closest('.speaker-chip')?.classList.toggle('checked', match);
          });
        } else {
          // すでに active だった場合はクリア
          targetGrid.querySelectorAll('input[type="checkbox"]').forEach(c => {
            c.checked = false;
            c.closest('.speaker-chip')?.classList.remove('checked');
          });
        }

        if (typeof onChangeCallback === 'function') {
          onChangeCallback();
        }
      });
    });

    macroContainer.querySelector('.btn-clear-macro')?.addEventListener('click', () => {
      macroContainer.querySelectorAll('.btn-macro').forEach(b => b.classList.remove('active'));
      targetGrid.querySelectorAll('input[type="checkbox"]').forEach(c => {
        c.checked = false;
        c.closest('.speaker-chip')?.classList.remove('checked');
      });
      if (typeof onChangeCallback === 'function') {
        onChangeCallback();
      }
    });
  }

  // 複数スピーカー選択チェックボックス＆マクロボタン群の描画
  function renderSpeakersCheckboxes(container, nameAttr, selectedValues = [], options = {}) {
    if (!container) return;
    const defaultIp = (state.serverInfo && state.serverInfo.defaultDeviceIp) || (state.devices[0]?.ip || '');
    let html = '';

    // スケジュール/カレンダー用: デフォルト選択肢
    if (nameAttr === 'schedSpeaker' || options.includeDefault) {
      const isDefChecked = selectedValues.includes('default') ? 'checked' : '';
      html += `
        <label class="speaker-chip ${isDefChecked ? 'checked' : ''}">
          <input type="checkbox" name="${nameAttr}" value="default" data-type="default" ${isDefChecked}>
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
      const isOnvif = dev.type === 'onvif' || dev.ip.startsWith('onvif:');
      const isDlna = dev.type === 'dlna' || dev.ip.startsWith('dlna:');
      const devType = isAlexa ? 'alexa' : (isHomePod ? 'homepod' : (isDlna ? 'dlna' : (isOnvif ? 'onvif' : 'google')));
      const chipClass = isAlexa ? 'alexa-chip' : (isHomePod ? 'homepod-chip' : (isDlna ? 'dlna-chip' : (isOnvif ? 'onvif-chip' : 'google-chip')));
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
        } else if (isDlna) {
          badgeHtml += '<span class="speaker-chip-badge dlna-badge">🎵 DLNA</span>';
        } else if (isOnvif) {
          badgeHtml += '<span class="speaker-chip-badge onvif-badge">📷 ONVIF</span>';
        } else {
          badgeHtml += '<span class="speaker-chip-badge google-badge">Google Home</span>';
        }
      }

      html += `
        <label class="speaker-chip ${chipClass} ${isChecked ? 'checked' : ''}" title="${escapeHtml(displayName)} (${escapeHtml(dev.model || dev.type)})">
          <input type="checkbox" name="${nameAttr}" value="${dev.ip}" data-type="${devType}" ${isChecked}>
          <span class="speaker-chip-name">${escapeHtml(displayName)}</span>
          <span class="speaker-chip-badges">${badgeHtml}</span>
        </label>
      `;
    });

    container.innerHTML = html;

    // マクロボタン群コンテナの特定 & 描画
    const macroMap = {
      saySpeaker: 'sayMacroButtons',
      schedSpeaker: 'schedMacroButtons',
      calSpeaker: 'calMacroButtons',
      modalCalSpeaker: 'modalCalMacroButtons',
      dndSpeaker: 'dndMacroButtons',
      disasterSpeaker: 'disasterMacroButtons',
      groupSpeaker: 'groupMacroButtons'
    };
    const macroContainerId = options.macroContainerId || macroMap[nameAttr];
    const macroContainer = macroContainerId ? document.getElementById(macroContainerId) : null;

    if (macroContainer) {
      renderMacroButtonsFor(macroContainer, container, nameAttr, options.onChange);
    }

    // チェック状態変化でスタイル反映 & マクロボタン連動
    container.querySelectorAll('input[type="checkbox"]').forEach(chk => {
      chk.addEventListener('change', (e) => {
        const parent = e.target.closest('.speaker-chip');
        if (e.target.checked) {
          parent.classList.add('checked');
        } else {
          parent.classList.remove('checked');
        }
        // 手動チェック変更でマクロボタンのアクティブ解除
        if (macroContainer) {
          macroContainer.querySelectorAll('.btn-macro').forEach(b => b.classList.remove('active'));
        }
        if (typeof options.onChange === 'function') {
          options.onChange(e);
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

  // 防災・緊急速報用スピーカーチェックボックスの描画
  function renderDisasterSpeakers(selectedList = []) {
    const container = document.getElementById('disasterSpeakersContainer');
    if (!container) return;
    renderSpeakersCheckboxes(container, 'disasterSpeaker', selectedList);
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
      const devNames = targets.map(t => getDeviceDisplayName(t)).join(', ');

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
      const targetsHtml = targetsList.map(t => {
        const dName = getDeviceDisplayName(t);
        return `<span class="speaker-tag" title="${escapeHtml(t)}">${escapeHtml(dName)}</span>`;
      }).join(' ');

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
    // ログインフォーム送信
    if (el.loginForm) {
      el.loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const password = el.loginPassword ? el.loginPassword.value.trim() : '';
        if (!password) return;

        if (el.loginSubmitBtn) {
          el.loginSubmitBtn.disabled = true;
          el.loginSubmitBtn.textContent = '認証中...';
        }
        if (el.loginErrorMsg) el.loginErrorMsg.style.display = 'none';

        try {
          const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
          });
          const data = await res.json();
          if (res.ok && data.success) {
            hideLoginOverlay();
            if (el.headerLogoutBtn) el.headerLogoutBtn.style.display = 'inline-flex';
            if (typeof showToast === 'function') {
              showToast('ログインしました', 'success');
            }
            await loadInitialData();
          } else {
            if (el.loginErrorMsg) {
              el.loginErrorMsg.textContent = data.error || 'パスワードが正しくありません';
              el.loginErrorMsg.style.display = 'block';
            }
          }
        } catch (err) {
          if (el.loginErrorMsg) {
            el.loginErrorMsg.textContent = '通信エラー: ' + err.message;
            el.loginErrorMsg.style.display = 'block';
          }
        } finally {
          if (el.loginSubmitBtn) {
            el.loginSubmitBtn.disabled = false;
            el.loginSubmitBtn.textContent = 'ログイン';
          }
        }
      });
    }

    // ログアウトボタン
    if (el.headerLogoutBtn) {
      el.headerLogoutBtn.addEventListener('click', async () => {
        if (confirm('ログアウトしますか？')) {
          try {
            await fetch('/api/auth/logout', { method: 'POST' });
          } catch (e) {}
          window.location.reload();
        }
      });
    }

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
          loadDisasterSettings();
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
            if (subtabId === 'subtab-settings-disaster') {
              loadDisasterSettings();
            } else if (subtabId === 'subtab-settings-mqtt') {
              if (typeof updateMqttStatus === 'function') updateMqttStatus();
            } else if (subtabId === 'subtab-settings-mcp') {
              if (typeof updateMcpConfigSnippets === 'function') updateMcpConfigSnippets();
              if (typeof updateMcpStatus === 'function') updateMcpStatus();
            }


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

    // 全室選択 / クリア（レガシー参照の安全対策）
    el.btnSelectAllSpeakers?.addEventListener('click', () => {
      el.saySpeakersContainer?.querySelectorAll('input[type="checkbox"]').forEach(c => {
        c.checked = true;
        c.closest('.speaker-chip')?.classList.add('checked');
      });
    });

    el.btnClearSpeakers?.addEventListener('click', () => {
      el.saySpeakersContainer?.querySelectorAll('input[type="checkbox"]').forEach(c => {
        c.checked = false;
        c.closest('.speaker-chip')?.classList.remove('checked');
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
            state.serverInfo.defaultDeviceName = name;
          }
          updateDefaultDeviceDisplay();

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

    // 全デバイス一括再スキャン (Google Home / Alexa / HomePod / ONVIF)
    el.btnRefreshDevices?.addEventListener('click', async () => {
      const origHtml = el.btnRefreshDevices.innerHTML;
      el.btnRefreshDevices.disabled = true;
      el.btnRefreshDevices.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" class="spin"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
        スキャン中...
      `;
      showToast('全スマートスピーカー＆カメラを一括再スキャンしています...');
      try {
        const res = await fetch('/api/devices/rescan-all', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          state.devices = sortDevicesList(data.devices || []);
          renderDevicesGrid();
          renderAllSpeakerSelectors();
          showToast(`全デバイス一括再スキャン完了: 計 ${state.devices.length} 台を検出・同期しました`, 'success');
        } else {
          throw new Error(data.error || '再スキャン失敗');
        }
      } catch (err) {
        console.error('一括再スキャンエラー:', err);
        showToast('再スキャンエラー: ' + err.message, 'error');
        await loadDevices();
      } finally {
        el.btnRefreshDevices.disabled = false;
        el.btnRefreshDevices.innerHTML = origHtml;
      }
    });

    // 接続デバイスタブ内の外部連携・ONVIF設定へのクイック移動リンク
    document.getElementById('linkGoToIntegrations')?.addEventListener('click', (e) => {
      e.preventDefault();
      document.getElementById('btnTabSettings')?.click();
      document.getElementById('btnSubtabSettingsIntegrations')?.click();
    });
    document.getElementById('linkGoToOnvif')?.addEventListener('click', (e) => {
      e.preventDefault();
      document.getElementById('btnTabSettings')?.click();
      document.getElementById('btnSubtabSettingsOnvif')?.click();
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
      const isOnvif = dev.type === 'onvif';
      const devType = isAlexa ? 'alexa' : (isHomePod ? 'homepod' : (isOnvif ? 'onvif' : 'google'));
      const chipClass = isAlexa ? 'alexa-chip' : (isHomePod ? 'homepod-chip' : (isOnvif ? 'onvif-chip' : 'google-chip'));
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
      } else if (isOnvif) {
        badgeHtml += '<span class="speaker-chip-badge onvif-badge">📷 ONVIF</span>';
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
            else if (macro === 'CAM:ALL') match = (type === 'onvif');
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
        let reasonShort = s.reason ? s.reason.replace('カレンダー予定中: ', '📅').replace('定時サイレント: ', '⏰').replace(/手動サイレント.*/, '🔇手動ミュート') : '🔇ミュート中';
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
        toggleText.textContent = 'ミュート解除';
        toggleBtn.title = '現在ミュート中 (クリックでミュート解除)';
      } else {
        toggleBtn.classList.remove('is-muted');
        toggleIcon.textContent = '🔇';
        toggleText.textContent = 'ミュート';
        const topDur = state.dndConfig?.topMuteDuration || 'indefinite';
        const durLabel = (topDur === 'indefinite') ? '手動解除までずっと' : (topDur === '1440' ? '1日間' : (topDur === '120' ? '2時間' : (topDur === '30' ? '30分間' : '1時間')));
        toggleBtn.title = `ワンタップで即時ミュート (${durLabel})`;
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
        topMuteDuration: document.querySelector('input[name="dndTopMuteDuration"]:checked')?.value || 'indefinite',
        aiSummaryEnabled: document.getElementById('dndAiSummaryEnabled')?.checked !== false,
        aiSummaryThreshold: parseInt(document.getElementById('dndAiSummaryThreshold')?.value || '2', 10),
        manualUntil: dnd.manualUntil !== undefined ? dnd.manualUntil : null,
        manualReason: dnd.manualReason || '',
        manualUnmutedUntil: dnd.manualUnmutedUntil !== undefined ? dnd.manualUnmutedUntil : null
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
          const durationSetting = state.dndConfig?.topMuteDuration || 'indefinite';
          let minutes = -1;
          let label = '手動解除までずっと';
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
    if (str === null || str === undefined) return '';
    return String(str)
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
      // 5. カスタム部屋グループの描画
      renderDeviceGroups();

      // 6. IPエイリアスの描画
      renderIpAliases();

      // 7. Webhookビルダーのマクロチップ & 各種スピーカーセレクターも再描画
      renderAllSpeakerSelectors();

      // 8. ONVIF デフォルト認証情報の入力欄反映 & 登録済みテーブル描画
      const onvifConfig = data.onvif || {};
      const onvifUserEl = document.getElementById('onvifDefaultUser');
      const onvifPassEl = document.getElementById('onvifDefaultPass');
      if (onvifUserEl && onvifConfig.defaultUsername) {
        onvifUserEl.value = onvifConfig.defaultUsername;
      }
      if (onvifPassEl && onvifConfig.defaultPassword) {
        onvifPassEl.value = onvifConfig.defaultPassword;
      }
      renderRegisteredOnvifTable();

      // 9. MQTT 設定のフォーム反映
      if (typeof window.populateMqttSettings === 'function') {
        window.populateMqttSettings(data.mqtt);
      }

      // 10. 履歴一覧がすでに描画されている場合、エイリアス設定でIPタグを更新 (エイリアス登録済みIPは非リンク化)
      if (state.historyItems && state.historyItems.length > 0) {
        renderFullHistory();
      }

      // 11. Homebridge 連携案内カードのパラメータ動的反映
      const hbHostEl = document.getElementById('homebridgeHostDisplay');
      if (hbHostEl) {
        hbHostEl.textContent = `${window.location.protocol}//${window.location.hostname}:${window.location.port || (window.location.protocol === 'https:' ? '443' : '80')}`;
      }
      const hbTokenEl = document.getElementById('homebridgeTokenDisplay');
      if (hbTokenEl) {
        if (data.webhookToken) {
          hbTokenEl.textContent = `${data.webhookToken.slice(0, 6)}...${data.webhookToken.slice(-4)}`;
          hbTokenEl.title = data.webhookToken;
        } else {
          hbTokenEl.textContent = 'なし (未設定)';
        }
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
      const memberChips = (members || []).map(m => {
        const dName = getDeviceDisplayName(m);
        return `<span class="group-member-chip" title="${escapeHtml(m)}">${escapeHtml(dName)}</span>`;
      }).join(' ');
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
        renderAllSpeakerSelectors();
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
        renderSpeakersCheckboxes(groupCheckboxesContainer, 'groupSpeaker', []);
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
      renderAllSpeakerSelectors();

      if (groupModal) groupModal.style.display = 'none';
      showToast(`カスタムグループ「${name}」を保存しました`, 'success');
    });

    // 6. Homebridge プラグイン解説書モーダル関連
    const hbModal = document.getElementById('modalHomebridgeManual');
    document.getElementById('btnOpenHomebridgeManual')?.addEventListener('click', () => {
      if (hbModal) hbModal.style.display = 'flex';
    });
    document.getElementById('btnCloseHomebridgeManualModal')?.addEventListener('click', () => {
      if (hbModal) hbModal.style.display = 'none';
    });
    document.getElementById('btnCloseHomebridgeManualModalFooter')?.addEventListener('click', () => {
      if (hbModal) hbModal.style.display = 'none';
    });
    hbModal?.addEventListener('click', (e) => {
      if (e.target === hbModal) hbModal.style.display = 'none';
    });

    // Homebridge インストールコマンドコピー
    document.getElementById('btnCopyInstallCmd')?.addEventListener('click', () => {
      navigator.clipboard.writeText('npm install -g homebridge-voicehub').then(() => {
        showToast('インストールコマンドをコピーしました', 'success');
      }).catch(() => {
        showToast('コピーに失敗しました', 'error');
      });
    });

    // Homebridge 設定 JSON コピー
    document.getElementById('btnCopyHomebridgeJson')?.addEventListener('click', () => {
      const pre = document.getElementById('preHomebridgeConfigJson');
      if (pre) {
        navigator.clipboard.writeText(pre.textContent).then(() => {
          showToast('Homebridge 設定 JSON をコピーしました', 'success');
        }).catch(() => {
          showToast('コピーに失敗しました', 'error');
        });
      }
    });
  }

  // ================= ONVIF カメラスピーカー設定 =================
  let discoveredOnvifDevices = [];

  function renderDiscoveredOnvifTable() {
    const tbody = document.getElementById('onvifDiscoveredTableBody');
    if (!tbody) return;

    if (!discoveredOnvifDevices.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center loading-cell">「ONVIF / DLNA 自動スキャン」を押すと、宅内のカメラおよびDLNAスピーカーを自動検出します</td></tr>`;
      return;
    }

    const registered = state.settings?.onvif?.registeredDevices || [];

    tbody.innerHTML = discoveredOnvifDevices.map(dev => {
      const isReg = registered.some(r => r.ip === dev.ip);
      const isDlna = (dev.category === 'dlna' || dev.type === 'dlna');
      const isSupported = isDlna || !!(dev.isProfileT || dev.hasProfileT || dev.supportsAudio);
      const rowStyle = !isSupported ? 'opacity: 0.55;' : '';

      let typeBadge = '';
      if (isDlna) {
        typeBadge = `<span class="speaker-chip-badge dlna-badge">🎵 DLNA</span>`;
      } else {
        typeBadge = `<span class="speaker-chip-badge onvif-badge">📷 ONVIF</span>`;
      }

      let profileBadge = '';
      if (isDlna) {
        profileBadge = `<span class="speaker-chip-badge" style="background:rgba(6,182,212,0.2);color:#22d3ee;border:1px solid rgba(6,182,212,0.4);font-weight:600;">🎵 UPnP AVTransport</span>`;
      } else if (isSupported) {
        profileBadge = `<span class="speaker-chip-badge" style="background:rgba(16,185,129,0.2);color:#34d399;border:1px solid rgba(16,185,129,0.4);font-weight:600;">📷 Profile T (双方向音声対応)</span>`;
      } else {
        profileBadge = `<span class="speaker-chip-badge" style="background:rgba(255,255,255,0.06);color:var(--text-muted);border:1px solid rgba(255,255,255,0.12);">Profile S (スピーカー非対応)</span>`;
      }

      let authStatus = '';
      if (isDlna) {
        authStatus = `<span style="color:#22d3ee;font-size:0.8rem;">✓ 認証不要 (UPnP)</span>`;
      } else if (dev.status === 'ok') {
        authStatus = `<span style="color:#34d399;font-size:0.8rem;">✓ 認証・通信確認済</span>`;
      } else if (dev.status === 'unauthorized') {
        authStatus = `<span style="color:#fbbf24;font-size:0.8rem;">要認証 (Profile T対応)</span>`;
      } else {
        authStatus = `<span style="color:var(--text-muted);font-size:0.8rem;">通信確認済</span>`;
      }

      let actionHtml = '';
      if (isReg) {
        actionHtml = `<button type="button" class="btn-chip" disabled style="opacity:0.6;">✓ 登録済み</button>`;
      } else if (!isSupported) {
        actionHtml = `<span style="font-size:0.8rem;color:var(--text-muted);background:rgba(255,255,255,0.04);padding:3px 8px;border-radius:4px;">非対応</span>`;
      } else {
        actionHtml = `<button type="button" class="btn btn-primary btn-sm btn-open-onvif-modal" data-ip="${escapeHtml(dev.ip)}">＋ 連携登録</button>`;
      }

      const primaryName = dev.friendlyName || dev.name || (isDlna ? 'DLNA Speaker' : 'ONVIF Camera');
      const subInfo = (dev.model && dev.model !== primaryName)
        ? `${escapeHtml(dev.model)}`
        : (isDlna ? 'MediaRenderer' : 'Camera');

      const icon = isDlna ? '🎵' : '📷';

      return `
        <tr style="${rowStyle}">
          <td>${typeBadge}</td>
          <td>
            <strong>${icon} ${escapeHtml(primaryName)}</strong>
            <div style="font-size:0.75rem;color:var(--text-muted);">${subInfo} ${dev.serialNumber ? '(' + escapeHtml(dev.serialNumber) + ')' : ''}</div>
          </td>
          <td><code>${escapeHtml(dev.ip)}:${dev.port || 80}</code></td>
          <td>${profileBadge}</td>
          <td>${authStatus}</td>
          <td>${actionHtml}</td>
        </tr>
      `;
    }).join('');

    tbody.querySelectorAll('.btn-open-onvif-modal').forEach(btn => {
      btn.addEventListener('click', () => {
        const ip = btn.getAttribute('data-ip');
        const dev = discoveredOnvifDevices.find(d => d.ip === ip);
        if (dev) openOnvifRegisterModal(dev);
      });
    });
  }

  let activeOnvifDeviceToRegister = null;

  function openOnvifRegisterModal(dev) {
    activeOnvifDeviceToRegister = dev;
    const modal = document.getElementById('modalOnvifRegister');
    if (!modal) return;

    const titleEl = document.getElementById('modalOnvifTitle');
    const alertEl = document.getElementById('modalOnvifAlert');
    const authBlock = document.getElementById('onvifAuthBlock');
    const nameInput = document.getElementById('onvifRegName');
    const ipInput = document.getElementById('onvifRegIp');
    const modelInput = document.getElementById('onvifRegModel');
    const userInput = document.getElementById('onvifRegUser');
    const passInput = document.getElementById('onvifRegPass');

    const isDlna = (dev.category === 'dlna' || dev.type === 'dlna');
    const defaultName = dev.friendlyName || dev.name || (dev.model ? `${dev.model}_${dev.ip.split('.').pop()}` : (isDlna ? 'DLNAスピーカー' : '防犯カメラ'));

    if (titleEl) {
      titleEl.textContent = isDlna ? '🎵 DLNAスピーカー連携登録' : '📷 カメラスピーカー連携登録';
    }
    if (alertEl) {
      alertEl.textContent = isDlna
        ? 'この DLNA / UPnP MediaRenderer スピーカーを音声案内スピーカーとして登録します。登録後は各アナウンスや部屋グループ選択で通常のスマートスピーカーと同様に利用できます。'
        : 'このカメラを音声案内スピーカーとして登録します。登録後は各アナウンスや部屋グループ選択で通常のスマートスピーカーと同様に利用できます。';
    }
    if (authBlock) {
      authBlock.style.display = isDlna ? 'none' : 'block';
    }

    if (nameInput) nameInput.value = defaultName;
    if (ipInput) ipInput.value = `${dev.ip}:${dev.port || (isDlna ? 80 : 8000)}`;
    if (modelInput) modelInput.value = isDlna ? `${dev.model || 'DLNA'} (UPnP AVTransport)` : `${dev.model || 'ONVIF'} (Profile T 双方向音声)`;
    if (userInput) {
      userInput.value = '';
      userInput.placeholder = isDlna ? '不要 (DLNA)' : 'ユーザー名 (空欄でデフォルト)';
      userInput.disabled = isDlna;
    }
    if (passInput) {
      passInput.value = '';
      passInput.placeholder = isDlna ? '不要 (DLNA)' : 'パスワード (空欄でデフォルト)';
      passInput.disabled = isDlna;
    }

    modal.style.display = 'flex';
    setTimeout(() => nameInput?.focus(), 50);
  }

  function closeOnvifRegisterModal() {
    const modal = document.getElementById('modalOnvifRegister');
    if (modal) modal.style.display = 'none';
    activeOnvifDeviceToRegister = null;
  }

  function setupOnvifRegisterModal() {
    const modal = document.getElementById('modalOnvifRegister');
    const btnClose = document.getElementById('btnCloseOnvifModal');
    const btnCancel = document.getElementById('btnCancelOnvifModal');
    const btnSubmit = document.getElementById('btnSubmitOnvifModal');

    if (!modal) return;

    [btnClose, btnCancel].forEach(b => {
      b?.addEventListener('click', closeOnvifRegisterModal);
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeOnvifRegisterModal();
    });

    btnSubmit?.addEventListener('click', async () => {
      if (!activeOnvifDeviceToRegister) return;
      const dev = activeOnvifDeviceToRegister;
      const nameInput = document.getElementById('onvifRegName');
      const userInput = document.getElementById('onvifRegUser');
      const passInput = document.getElementById('onvifRegPass');

      const name = nameInput?.value.trim();
      if (!name) {
        showToast('スピーカー表示名を入力してください', 'warning');
        nameInput?.focus();
        return;
      }

      const isDlna = (dev.category === 'dlna' || dev.type === 'dlna');
      const defaultUser = document.getElementById('onvifDefaultUser')?.value.trim() || 'admin';
      const defaultPass = document.getElementById('onvifDefaultPass')?.value || '';

      const username = isDlna ? '' : (userInput?.value.trim() || defaultUser);
      const password = isDlna ? '' : (passInput?.value || defaultPass);

      try {
        btnSubmit.disabled = true;
        btnSubmit.textContent = '登録中...';

        const res = await fetch('/api/onvif/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            device: {
              ip: dev.ip,
              name,
              username,
              password,
              port: dev.port || (isDlna ? 80 : 8000),
              model: dev.model || (isDlna ? 'DLNA MediaRenderer' : 'ONVIF Camera'),
              controlUrl: dev.controlUrl || '',
              renderingControlUrl: dev.renderingControlUrl || '',
              type: isDlna ? 'dlna' : 'onvif'
            }
          })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '登録失敗');

        if (!state.settings) state.settings = {};
        if (!state.settings.onvif) state.settings.onvif = {};
        state.settings.onvif.registeredDevices = data.registeredDevices;

        showToast(`「${name}」を${isDlna ? 'DLNA' : 'カメラ'}スピーカーとして登録しました`, 'success');
        closeOnvifRegisterModal();
        await loadDevices();
        renderRegisteredOnvifTable();
        renderDiscoveredOnvifTable();
      } catch (err) {
        showToast('登録エラー: ' + err.message, 'error');
      } finally {
        btnSubmit.disabled = false;
        btnSubmit.textContent = 'この内容で登録する';
      }
    });
  }

  function renderRegisteredOnvifTable() {
    const tbody = document.getElementById('onvifRegisteredTableBody');
    if (!tbody) return;

    const list = state.settings?.onvif?.registeredDevices || [];
    if (!list.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center loading-cell">登録済みのスピーカーはありません</td></tr>`;
      return;
    }

    tbody.innerHTML = list.map(dev => {
      const isDlna = (dev.type === 'dlna');
      const icon = isDlna ? '🎵' : '📷';
      const typeBadge = isDlna
        ? `<span class="speaker-chip-badge dlna-badge">🎵 DLNA</span>`
        : `<span class="speaker-chip-badge onvif-badge">📷 ONVIF</span>`;
      const connUrl = isDlna
        ? (dev.controlUrl || 'UPnP AVTransport')
        : (dev.rtspUrl || 'RTSP Backchannel');
      const authUser = isDlna
        ? `<span style="color:var(--text-muted);font-size:0.8rem;">不要 (UPnP)</span>`
        : escapeHtml(dev.username || 'admin');

      return `
        <tr>
          <td>${typeBadge}</td>
          <td><strong>${icon} ${escapeHtml(dev.name)}</strong></td>
          <td><code>${escapeHtml(dev.ip)}</code></td>
          <td><code style="font-size:0.75rem;word-break:break-all;">${escapeHtml(connUrl)}</code></td>
          <td>${authUser}</td>
          <td style="white-space:nowrap;">
            <button type="button" class="btn btn-secondary btn-sm btn-test-onvif" data-ip="${escapeHtml(dev.ip)}" style="margin-right:6px;">
              🔊 テスト発話
            </button>
            <button type="button" class="btn-chip text-danger btn-delete-onvif" data-ip="${escapeHtml(dev.ip)}" title="連携解除">
              解除
            </button>
          </td>
        </tr>
      `;
    }).join('');

    // テスト発話
    tbody.querySelectorAll('.btn-test-onvif').forEach(btn => {
      btn.addEventListener('click', async () => {
        const ip = btn.getAttribute('data-ip');
        const dev = list.find(d => d.ip === ip);
        if (!dev) return;

        const origText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '再生中...';
        showToast(`「${dev.name}」へテスト音声を送信しています...`);

        try {
          const res = await fetch('/api/onvif/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dev)
          });
          const data = await res.json();
          if (!res.ok || !data.success) throw new Error(data.error || '再生失敗');
          showToast(`「${dev.name}」のスピーカーからテスト音声を再生しました`, 'success');
        } catch (err) {
          showToast('テスト発話エラー: ' + err.message, 'error');
        } finally {
          btn.disabled = false;
          btn.innerHTML = origText;
        }
      });
    });

    // 登録解除
    tbody.querySelectorAll('.btn-delete-onvif').forEach(btn => {
      btn.addEventListener('click', async () => {
        const ip = btn.getAttribute('data-ip');
        const dev = list.find(d => d.ip === ip);
        const name = dev?.name || ip;
        const isDlna = (dev?.type === 'dlna');
        if (!confirm(`「${name}」の${isDlna ? 'DLNA' : 'カメラ'}スピーカー連携を解除しますか？`)) return;

        try {
          const res = await fetch('/api/onvif/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device: { ip }, delete: true })
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || '解除失敗');

          if (state.settings?.onvif) {
            state.settings.onvif.registeredDevices = data.registeredDevices;
          }
          showToast(`「${name}」の連携を解除しました`, 'success');
          await loadDevices();
          renderRegisteredOnvifTable();
          renderDiscoveredOnvifTable();
        } catch (err) {
          showToast('解除エラー: ' + err.message, 'error');
        }
      });
    });
  }

  function setupOnvifSettings() {
    const btnScan = document.getElementById('btnScanOnvif');
    const btnSaveAuth = document.getElementById('btnSaveOnvifDefaultAuth');
    const inputUser = document.getElementById('onvifDefaultUser');
    const inputPass = document.getElementById('onvifDefaultPass');
    const authSavedMsg = document.getElementById('onvifAuthSavedMsg');
    const btnManualAdd = document.getElementById('btnManualAddDevice');

    const onvifConfig = state.settings?.onvif || {};
    setupOnvifRegisterModal();
    if (inputUser && onvifConfig.defaultUsername) {
      inputUser.value = onvifConfig.defaultUsername;
    }
    if (inputPass && onvifConfig.defaultPassword) {
      inputPass.value = onvifConfig.defaultPassword;
    }

    btnSaveAuth?.addEventListener('click', async () => {
      const user = inputUser?.value.trim() || 'admin';
      const pass = inputPass?.value || '';

      const updated = {
        ...state.settings,
        onvif: {
          ...(state.settings?.onvif || {}),
          enabled: true,
          defaultUsername: user,
          defaultPassword: pass
        }
      };

      try {
        const res = await fetch('/api/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updated)
        });
        if (!res.ok) throw new Error('保存に失敗しました');
        state.settings = updated;
        if (authSavedMsg) {
          authSavedMsg.style.display = 'inline';
          setTimeout(() => { authSavedMsg.style.display = 'none'; }, 3000);
        }
        showToast('ONVIF デフォルト認証情報を保存しました', 'success');
      } catch (e) {
        showToast('保存エラー: ' + e.message, 'error');
      }
    });

    // 手動デバイス追加（IP直接登録）
    btnManualAdd?.addEventListener('click', async () => {
      const type = document.getElementById('manualDevType')?.value || 'dlna';
      const name = document.getElementById('manualDevName')?.value.trim();
      const ip = document.getElementById('manualDevIp')?.value.trim();
      let port = parseInt(document.getElementById('manualDevPort')?.value, 10);
      if (isNaN(port) || port <= 0) {
        port = (type === 'dlna' ? 80 : 8000);
      }

      if (!name) {
        showToast('スピーカー表示名を入力してください', 'warning');
        document.getElementById('manualDevName')?.focus();
        return;
      }
      if (!ip) {
        showToast('IP アドレスを入力してください', 'warning');
        document.getElementById('manualDevIp')?.focus();
        return;
      }

      const defaultUser = inputUser?.value.trim() || 'admin';
      const defaultPass = inputPass?.value || '';

      const devPayload = {
        ip,
        name,
        port,
        type,
        model: type === 'dlna' ? 'DLNA MediaRenderer (手動登録)' : 'ONVIF Camera (手動登録)',
        username: type === 'dlna' ? '' : defaultUser,
        password: type === 'dlna' ? '' : defaultPass,
        controlUrl: type === 'dlna' ? `http://${ip}:${port}/upnp/control/rendertr1` : '',
        enabled: true
      };

      const origText = btnManualAdd.textContent;
      btnManualAdd.disabled = true;
      btnManualAdd.textContent = '登録中...';
      try {
        const res = await fetch('/api/onvif/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ device: devPayload })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '登録失敗');

        if (!state.settings) state.settings = {};
        if (!state.settings.onvif) state.settings.onvif = {};
        state.settings.onvif.registeredDevices = data.registeredDevices;

        showToast(`「${name}」を${type === 'dlna' ? 'DLNA' : 'カメラ'}スピーカーとして手動登録しました`, 'success');
        document.getElementById('manualDevName').value = '';
        document.getElementById('manualDevIp').value = '';
        document.getElementById('manualDevPort').value = '';
        await loadDevices();
        renderRegisteredOnvifTable();
        renderDiscoveredOnvifTable();
      } catch (err) {
        showToast('手動登録エラー: ' + err.message, 'error');
      } finally {
        btnManualAdd.disabled = false;
        btnManualAdd.textContent = origText;
      }
    });

    btnScan?.addEventListener('click', async () => {
      const origHtml = btnScan.innerHTML;
      btnScan.disabled = true;
      btnScan.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" class="spin"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
        スキャン中...
      `;
      showToast('宅内の ONVIF カメラおよび DLNA スピーカーをスキャンしています...');

      const tbody = document.getElementById('onvifDiscoveredTableBody');
      const scanCount = document.getElementById('onvifScanCount');
      if (tbody) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center loading-cell">ネットワーク内のデバイスを検出中 (数秒かかります)...</td></tr>';
      }

      try {
        const user = inputUser?.value.trim() || 'admin';
        const pass = inputPass?.value || '';
        const res = await fetch('/api/onvif/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: user, password: pass })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'スキャンに失敗しました');

        discoveredOnvifDevices = Array.isArray(data) ? data : (data.devices || []);
        if (scanCount) {
          scanCount.textContent = `${discoveredOnvifDevices.length} 台検出`;
        }
        renderDiscoveredOnvifTable();
        showToast(`ONVIF / DLNA デバイスを ${discoveredOnvifDevices.length} 台検出しました`, 'success');
      } catch (err) {
        console.error('ONVIF/DLNA スキャンエラー:', err);
        showToast('ONVIF/DLNA スキャンエラー: ' + err.message, 'error');
        if (tbody) {
          tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">スキャンに失敗しました: ${escapeHtml(err.message)}</td></tr>`;
        }
      } finally {
        btnScan.disabled = false;
        btnScan.innerHTML = origHtml;
      }
    });

    renderRegisteredOnvifTable();
  }

  // ================= 8.5. MQTT 連携設定 (Node-RED / n8n メッセージ読み上げ) =================
  // ================= 8.5. MQTT 連携設定 (マルチブローカー対応) =================
  let currentMqttBrokers = [];

  function getMqttSpeakerOptionsHtml() {
    const devs = state.devices || [];
    const optionsHtml = [
      '<option value="">全体デフォルトスピーカーに従う</option>',
      '<optgroup label="全室マクロ">',
      '  <option value="ALL">全スピーカー一斉 (ALL)</option>',
      '  <option value="GH:ALL">Google Cast 全台 (GH:ALL)</option>',
      '  <option value="AL:ALL">Alexa 全台 (AL:ALL)</option>',
      '  <option value="HP:ALL">HomePod 全台 (HP:ALL)</option>',
      '  <option value="DLNA:ALL">DLNA 全台 (DLNA:ALL)</option>',
      '</optgroup>',
      '<optgroup label="個別スピーカー">'
    ];

    devs.forEach(d => {
      const dName = getDeviceDisplayName(d.name || d.ip);
      const val = d.name || d.ip;
      optionsHtml.push(`  <option value="${escapeHtml(val)}">${escapeHtml(dName)} (${escapeHtml(d.type || 'device')})</option>`);
    });
    optionsHtml.push('</optgroup>');

    const groups = state.deviceGroups || {};
    const groupEntries = Object.entries(groups);
    if (groupEntries.length > 0) {
      optionsHtml.push('<optgroup label="カスタムグループ">');
      groupEntries.forEach(([gName]) => {
        optionsHtml.push(`  <option value="${escapeHtml(gName)}">🏠 ${escapeHtml(gName)}</option>`);
      });
      optionsHtml.push('</optgroup>');
    }

    return optionsHtml.join('\n');
  }

  function renderMqttSpeakerOptions() {
    const htmlString = getMqttSpeakerOptionsHtml();
    const selTest = document.getElementById('selectMqttTestTarget');
    if (selTest) {
      const curTestVal = selTest.value;
      selTest.innerHTML = htmlString;
      selTest.value = curTestVal;
    }
    document.querySelectorAll('.broker-select-target').forEach(sel => {
      const curVal = sel.value;
      sel.innerHTML = htmlString;
      sel.value = curVal;
    });
  }

  async function updateMqttStatus() {
    const dot = document.getElementById('mqttStatusDot');
    const text = document.getElementById('mqttStatusText');
    const detail = document.getElementById('mqttStatusDetail');
    if (!dot || !text) return;

    try {
      const res = await fetch('/api/mqtt/status');
      if (!res.ok) throw new Error('ステータス取得失敗');
      const data = await res.json();

      if (!data.enabled) {
        dot.style.background = '#64748b'; // gray
        text.textContent = '無効 (未稼働)';
        text.style.color = 'var(--text-muted)';
        if (detail) detail.textContent = 'スイッチをONにして保存すると、設定したMQTTブローカーへ接続を開始します';
      } else if (data.connected) {
        dot.style.background = '#10b981'; // green
        text.textContent = `接続中 (${data.connectedCount} / ${data.totalBrokers || 1} 台のブローカー)`;
        text.style.color = '#34d399';
        if (detail) {
          detail.textContent = `受信合計: ${data.receivedCount} 件${data.lastMessageAt ? ' (最新: ' + data.lastMessageAt + ')' : ''}`;
        }
      } else {
        dot.style.background = '#ef4444'; // red
        text.textContent = `切断 / 接続待機 (${data.connectedCount} / ${data.totalBrokers || 0} 台接続)`;
        text.style.color = '#f87171';
        if (detail) detail.textContent = data.lastError || 'ブローカーに接続できません。設定やネットワークを確認してください';
      }

      // 各ブローカーカードのステータスバッジ & 統計情報の個別更新
      if (Array.isArray(data.brokers)) {
        data.brokers.forEach(ws => {
          const pill = document.getElementById(`mqttBrokerPill_${ws.id}`);
          if (pill) {
            pill.className = 'mqtt-broker-status-pill ' + (!ws.enabled ? 'disabled' : (ws.connected ? 'connected' : 'disconnected'));
            pill.textContent = !ws.enabled ? '⚪ 無効' : (ws.connected ? '🟢 接続中' : '🔴 切断');
          }
          const stats = document.getElementById(`mqttBrokerStats_${ws.id}`);
          if (stats) {
            let statsHtml = `受信: <strong>${ws.receivedCount || 0}</strong> 件 | トピック: <code>${escapeHtml(ws.baseTopic || 'voicehub')}/say</code>`;
            if (ws.lastMessageAt) statsHtml += ` | 最新: ${escapeHtml(ws.lastMessageAt)}`;
            if (ws.lastError) statsHtml += `<div style="color: #f87171; margin-top: 4px;">⚠️ ${escapeHtml(ws.lastError)}</div>`;
            stats.innerHTML = statsHtml;
          }
        });

        // テスト送信先ブローカー選択セレクトボックスの更新
        const selBroker = document.getElementById('selectMqttTestBroker');
        if (selBroker) {
          const currentVal = selBroker.value;
          let opts = '<option value="">🌐 すべての接続中ブローカーに配信</option>';
          data.brokers.forEach(b => {
            const statusLabel = !b.enabled ? '無効' : (b.connected ? '接続中' : '切断');
            opts += `<option value="${escapeHtml(b.id)}">${escapeHtml(b.name || b.broker)} (${escapeHtml(b.broker)}:${b.port}) [${statusLabel}]</option>`;
          });
          selBroker.innerHTML = opts;
          selBroker.value = currentVal;
        }
      }
    } catch (e) {
      dot.style.background = '#f59e0b';
      text.textContent = '通信エラー';
      if (detail) detail.textContent = e.message;
    }
  }

  function setupMqttSettings() {
    const checkEnabled = document.getElementById('settingMqttEnabled');
    const container = document.getElementById('mqttBrokersContainer');
    const btnAddBroker = document.getElementById('btnAddMqttBroker');
    const btnSave = document.getElementById('btnSaveMqttSettings');
    const btnReconnect = document.getElementById('btnReconnectMqtt');
    const btnTest = document.getElementById('btnSendMqttTest');

    function renderBrokersList() {
      if (!container) return;
      if (currentMqttBrokers.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; padding: 36px 20px; color: var(--text-muted); background: rgba(255,255,255,0.02); border: 1px dashed rgba(255,255,255,0.1); border-radius: var(--radius-md);">
            <div style="font-size: 2.2rem; margin-bottom: 8px;">📡</div>
            <div style="font-weight: 600; font-size: 1rem; color: var(--text-color); margin-bottom: 4px;">登録された MQTT ブローカーはありません</div>
            <div style="font-size: 0.85rem;">「＋ 新しい MQTT ブローカーを追加」ボタンから Home Assistant や Node-RED などのブローカーを追加してください</div>
          </div>
        `;
        return;
      }

      const speakerOptionsHtml = getMqttSpeakerOptionsHtml();

      container.innerHTML = currentMqttBrokers.map((b, idx) => {
        const isCollapsed = Boolean(b._collapsed);
        const hostDisplay = b.broker ? `${b.broker}:${b.port || 1883}` : 'ホスト未設定';
        return `
          <div class="mqtt-broker-card ${isCollapsed ? 'collapsed' : ''} ${b.enabled === false ? 'disabled' : ''}" data-broker-id="${escapeHtml(b.id)}">
            <div class="mqtt-broker-card-header" data-action="toggle-collapse">
              <div class="mqtt-broker-header-left">
                <span class="collapse-icon" style="font-size: 0.75rem; color: var(--text-muted); width: 14px;">${isCollapsed ? '▶' : '▼'}</span>
                <div>
                  <div class="mqtt-broker-title">${escapeHtml(b.name || `ブローカー #${idx + 1}`)}</div>
                  <div class="mqtt-broker-subtitle">${escapeHtml(hostDisplay)}</div>
                </div>
              </div>
              <div class="mqtt-broker-header-right" onclick="event.stopPropagation();">
                <span id="mqttBrokerPill_${escapeHtml(b.id)}" class="mqtt-broker-status-pill ${b.enabled === false ? 'disabled' : 'disconnected'}">
                  ${b.enabled === false ? '⚪ 無効' : '🔴 未接続'}
                </span>
                <label class="switch" title="このブローカーを有効化">
                  <input type="checkbox" class="broker-toggle-enabled" ${b.enabled !== false ? 'checked' : ''}>
                  <span class="slider round"></span>
                </label>
                <button type="button" class="btn-icon-danger btn-delete-broker" title="このブローカー設定を削除">
                  🗑️
                </button>
              </div>
            </div>

            <div class="mqtt-broker-card-body">
              <div class="form-group" style="margin-bottom: 12px;">
                <label class="form-label" style="font-size: 0.85rem;">ブローカー表示名 *</label>
                <input type="text" class="form-input broker-input-name" placeholder="例: Home Assistant Mosquitto" value="${escapeHtml(b.name || '')}">
              </div>

              <div class="two-col-layout" style="gap: 12px; margin-bottom: 12px;">
                <div class="form-group" style="margin: 0;">
                  <label class="form-label" style="font-size: 0.85rem;">ブローカー IP / ホスト名 *</label>
                  <input type="text" class="form-input broker-input-host" placeholder="例: 192.168.11.248 または localhost" value="${escapeHtml(b.broker || '')}">
                </div>
                <div class="form-group" style="margin: 0;">
                  <label class="form-label" style="font-size: 0.85rem;">ポート番号 *</label>
                  <input type="number" class="form-input broker-input-port" placeholder="1883" value="${escapeHtml(b.port || 1883)}">
                </div>
              </div>

              <div class="two-col-layout" style="gap: 12px; margin-bottom: 12px;">
                <div class="form-group" style="margin: 0;">
                  <label class="form-label" style="font-size: 0.85rem;">ユーザー名 (任意)</label>
                  <input type="text" class="form-input broker-input-user" placeholder="空欄時は認証なし" value="${escapeHtml(b.username || '')}">
                </div>
                <div class="form-group" style="margin: 0;">
                  <label class="form-label" style="font-size: 0.85rem;">パスワード (任意)</label>
                  <input type="password" class="form-input broker-input-pass" placeholder="空欄時はパスワードなし" value="${escapeHtml(b.password || '')}">
                </div>
              </div>

              <div class="two-col-layout" style="gap: 12px; margin-bottom: 12px;">
                <div class="form-group" style="margin: 0;">
                  <label class="form-label" style="font-size: 0.85rem;">ベーストピック *</label>
                  <input type="text" class="form-input broker-input-basetopic" placeholder="voicehub" value="${escapeHtml(b.baseTopic || 'voicehub')}">
                  <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 3px;">購読: <code>${escapeHtml(b.baseTopic || 'voicehub')}/say</code>, <code>${escapeHtml(b.baseTopic || 'voicehub')}/say/#</code></div>
                </div>
                <div class="form-group" style="margin: 0;">
                  <label class="form-label" style="font-size: 0.85rem;">クライアント ID</label>
                  <input type="text" class="form-input broker-input-clientid" placeholder="voice-hub" value="${escapeHtml(b.clientId || 'voice-hub')}">
                </div>
              </div>

              <div class="form-group" style="margin-bottom: 12px;">
                <label class="form-label" style="font-size: 0.85rem;">デフォルト読み上げ先スピーカー</label>
                <select class="form-input broker-select-target">
                  ${speakerOptionsHtml}
                </select>
                <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 3px;">トピックやメッセージ内でスピーカー指定が無い場合に使用されます</div>
              </div>

              <div class="form-group flex-between" style="padding: 8px 0; border-top: 1px solid rgba(255,255,255,0.05);">
                <div>
                  <div style="font-weight: 500; font-size: 0.85rem;">イベント通知の自動発行 (Publish)</div>
                  <small style="color: var(--text-muted);">発話完了時に <code>${escapeHtml(b.baseTopic || 'voicehub')}/events/say</code> へ結果を通知</small>
                </div>
                <label class="switch">
                  <input type="checkbox" class="broker-check-publishevents" ${b.publishEvents !== false ? 'checked' : ''}>
                  <span class="slider round"></span>
                </label>
              </div>

              <div class="form-group flex-between" style="padding: 8px 0; border-top: 1px solid rgba(255,255,255,0.05);">
                <div>
                  <div style="font-weight: 500; font-size: 0.85rem;">MQTTS (TLS/SSL 暗号化通信)</div>
                  <small style="color: var(--text-muted);">ポート8883等の暗号化接続</small>
                </div>
                <label class="switch">
                  <input type="checkbox" class="broker-check-tls" ${b.tls ? 'checked' : ''}>
                  <span class="slider round"></span>
                </label>
              </div>

              <div class="form-group flex-between" style="padding: 8px 0; border-top: 1px solid rgba(255,255,255,0.05);">
                <div>
                  <div style="font-weight: 500; font-size: 0.85rem;">🏠 Home Assistant 自動検出 (MQTT Discovery)</div>
                  <small style="color: var(--text-muted);">このブローカー経由で HA にエンティティを自動登録</small>
                </div>
                <label class="switch">
                  <input type="checkbox" class="broker-check-hadiscovery" ${b.haDiscoveryEnabled !== false ? 'checked' : ''}>
                  <span class="slider round"></span>
                </label>
              </div>

              <div class="broker-ha-options" style="padding: 10px 12px; background: rgba(0,0,0,0.25); border-radius: 6px; margin-bottom: 12px; border: 1px solid rgba(255,255,255,0.05); ${b.haDiscoveryEnabled === false ? 'display: none;' : ''}">
                <div class="form-group" style="margin: 0 0 8px 0;">
                  <label class="form-label" style="font-size: 0.75rem;">HA Discovery プレフィックス</label>
                  <input type="text" class="form-input broker-input-haprefix" placeholder="homeassistant" value="${escapeHtml(b.haDiscoveryPrefix || 'homeassistant')}" style="font-size: 0.8rem; padding: 6px 10px;">
                </div>
                <div style="display: flex; gap: 8px; justify-content: flex-end;">
                  <button type="button" class="btn btn-secondary btn-sm btn-broker-resend-ha" style="font-size: 0.75rem;">
                    🔄 Discovery 再送信
                  </button>
                  <button type="button" class="btn btn-secondary btn-sm btn-broker-clear-ha" style="font-size: 0.75rem; color: #f87171;">
                    🗑️ HA 解除
                  </button>
                </div>
              </div>

              <!-- 統計情報フッター -->
              <div id="mqttBrokerStats_${escapeHtml(b.id)}" style="font-size: 0.78rem; color: var(--text-muted); background: rgba(255,255,255,0.02); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.04);">
                受信: 0 件 | トピック: <code>${escapeHtml(b.baseTopic || 'voicehub')}/say</code>
              </div>
            </div>
          </div>
        `;
      }).join('');

      // 各カードへの初期値とイベントバインド
      currentMqttBrokers.forEach(b => {
        const card = container.querySelector(`[data-broker-id="${b.id}"]`);
        if (!card) return;

        // デフォルトスピーカー選択肢の反映
        const selTarget = card.querySelector('.broker-select-target');
        if (selTarget && b.defaultTarget) {
          selTarget.value = b.defaultTarget;
        }

        // 開閉
        const header = card.querySelector('.mqtt-broker-card-header');
        header?.addEventListener('click', (e) => {
          if (e.target.closest('.switch') || e.target.closest('.btn-delete-broker')) return;
          b._collapsed = !b._collapsed;
          card.classList.toggle('collapsed', b._collapsed);
          const icon = card.querySelector('.collapse-icon');
          if (icon) icon.textContent = b._collapsed ? '▶' : '▼';
        });

        // 有効/無効トグル
        const toggleEnabled = card.querySelector('.broker-toggle-enabled');
        toggleEnabled?.addEventListener('change', () => {
          b.enabled = toggleEnabled.checked;
          card.classList.toggle('disabled', !b.enabled);
        });

        // 削除ボタン
        const btnDelete = card.querySelector('.btn-delete-broker');
        btnDelete?.addEventListener('click', () => {
          if (!confirm(`MQTTブローカー「${b.name || b.broker || '無題'}」を削除しますか？`)) return;
          currentMqttBrokers = currentMqttBrokers.filter(item => item.id !== b.id);
          renderBrokersList();
        });

        // 各種入力フィールドバインド
        const inputName = card.querySelector('.broker-input-name');
        inputName?.addEventListener('input', () => {
          b.name = inputName.value.trim();
          const title = card.querySelector('.mqtt-broker-title');
          if (title) title.textContent = b.name || 'ブローカー';
        });

        const inputHost = card.querySelector('.broker-input-host');
        inputHost?.addEventListener('input', () => {
          b.broker = inputHost.value.trim();
          const sub = card.querySelector('.mqtt-broker-subtitle');
          if (sub) sub.textContent = b.broker ? `${b.broker}:${b.port || 1883}` : 'ホスト未設定';
        });

        const inputPort = card.querySelector('.broker-input-port');
        inputPort?.addEventListener('input', () => {
          b.port = parseInt(inputPort.value || '1883', 10);
          const sub = card.querySelector('.mqtt-broker-subtitle');
          if (sub) sub.textContent = b.broker ? `${b.broker}:${b.port || 1883}` : 'ホスト未設定';
        });

        const inputUser = card.querySelector('.broker-input-user');
        inputUser?.addEventListener('input', () => { b.username = inputUser.value.trim(); });

        const inputPass = card.querySelector('.broker-input-pass');
        inputPass?.addEventListener('input', () => { b.password = inputPass.value; });

        const inputBaseTopic = card.querySelector('.broker-input-basetopic');
        inputBaseTopic?.addEventListener('input', () => { b.baseTopic = inputBaseTopic.value.trim() || 'voicehub'; });

        const inputClientId = card.querySelector('.broker-input-clientid');
        inputClientId?.addEventListener('input', () => { b.clientId = inputClientId.value.trim() || 'voice-hub'; });

        selTarget?.addEventListener('change', () => { b.defaultTarget = selTarget.value; });

        const checkPublish = card.querySelector('.broker-check-publishevents');
        checkPublish?.addEventListener('change', () => { b.publishEvents = checkPublish.checked; });

        const checkTls = card.querySelector('.broker-check-tls');
        checkTls?.addEventListener('change', () => { b.tls = checkTls.checked; });

        const checkHa = card.querySelector('.broker-check-hadiscovery');
        const haOpts = card.querySelector('.broker-ha-options');
        checkHa?.addEventListener('change', () => {
          b.haDiscoveryEnabled = checkHa.checked;
          if (haOpts) haOpts.style.display = b.haDiscoveryEnabled ? 'block' : 'none';
        });

        const inputHaPrefix = card.querySelector('.broker-input-haprefix');
        inputHaPrefix?.addEventListener('input', () => { b.haDiscoveryPrefix = inputHaPrefix.value.trim() || 'homeassistant'; });

        // 個別 HA Discovery 再送
        const btnResendHa = card.querySelector('.btn-broker-resend-ha');
        btnResendHa?.addEventListener('click', async () => {
          const orig = btnResendHa.textContent;
          btnResendHa.disabled = true;
          btnResendHa.textContent = '🔄 送信中...';
          try {
            const res = await fetch('/api/mqtt/ha-discovery', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ clear: false, brokerId: b.id })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Discovery 送信に失敗しました');
            showToast(`[${b.name}] HA Discovery トピック (${data.count} 件) を発行しました！`, 'success');
          } catch (err) {
            showToast('HA Discovery エラー: ' + err.message, 'error');
          } finally {
            btnResendHa.disabled = false;
            btnResendHa.textContent = orig;
          }
        });

        // 個別 HA Discovery 解除
        const btnClearHa = card.querySelector('.btn-broker-clear-ha');
        btnClearHa?.addEventListener('click', async () => {
          if (!confirm(`Home Assistant から「${b.name}」の登録エンティティを解除しますか？`)) return;
          const orig = btnClearHa.textContent;
          btnClearHa.disabled = true;
          btnClearHa.textContent = '🗑️ 削除中...';
          try {
            const res = await fetch('/api/mqtt/ha-discovery', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ clear: true, brokerId: b.id })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Discovery 解除に失敗しました');
            showToast(`[${b.name}] HA から Discovery エンティティを解除しました`, 'success');
          } catch (err) {
            showToast('HA Discovery 解除エラー: ' + err.message, 'error');
          } finally {
            btnClearHa.disabled = false;
            btnClearHa.textContent = orig;
          }
        });
      });
    }

    // 初期化・設定データ流し込み
    window.populateMqttSettings = (mqttData) => {
      const m = mqttData || state.settings?.mqtt || {};
      if (checkEnabled) checkEnabled.checked = Boolean(m.enabled);
      if (Array.isArray(m.brokers) && m.brokers.length > 0) {
        currentMqttBrokers = JSON.parse(JSON.stringify(m.brokers));
      } else if (m.broker) {
        currentMqttBrokers = [{
          id: 'default',
          name: 'メインブローカー',
          enabled: m.enabled !== false,
          broker: m.broker || '',
          port: m.port || 1883,
          username: m.username || '',
          password: m.password || '',
          clientId: m.clientId || 'voice-hub',
          baseTopic: m.baseTopic || 'voicehub',
          defaultTarget: m.defaultTarget || '',
          publishEvents: m.publishEvents !== false,
          tls: Boolean(m.tls),
          haDiscoveryEnabled: m.haDiscoveryEnabled !== false,
          haDiscoveryPrefix: m.haDiscoveryPrefix || 'homeassistant'
        }];
      } else {
        currentMqttBrokers = [];
      }
      renderBrokersList();
      updateMqttStatus();
    };

    // 新規ブローカー追加ボタン
    btnAddBroker?.addEventListener('click', () => {
      const newIdx = currentMqttBrokers.length + 1;
      const newId = 'broker_' + Date.now();
      currentMqttBrokers.push({
        id: newId,
        name: `ブローカー #${newIdx}`,
        enabled: true,
        broker: '',
        port: 1883,
        username: '',
        password: '',
        clientId: `voice-hub-${Math.floor(Math.random() * 1000)}`,
        baseTopic: 'voicehub',
        defaultTarget: '',
        publishEvents: true,
        tls: false,
        haDiscoveryEnabled: true,
        haDiscoveryPrefix: 'homeassistant',
        _collapsed: false
      });
      renderBrokersList();
      const newCard = container?.querySelector(`[data-broker-id="${newId}"]`);
      newCard?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });

    // 全体保存ボタン
    btnSave?.addEventListener('click', async () => {
      const origText = btnSave.textContent;
      btnSave.disabled = true;
      btnSave.textContent = '💾 保存中...';

      const brokersToSave = currentMqttBrokers.map(b => {
        const copy = { ...b };
        delete copy._collapsed;
        return copy;
      });

      const mqttPayload = {
        enabled: checkEnabled?.checked || false,
        brokers: brokersToSave
      };

      try {
        const res = await fetch('/api/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mqtt: mqttPayload })
        });
        if (!res.ok) throw new Error('MQTT設定保存に失敗しました');
        const updated = await res.json();
        if (state.settings) state.settings.mqtt = updated.mqtt || mqttPayload;

        // クライアント再起動
        await fetch('/api/mqtt/restart', { method: 'POST' });
        showToast('MQTT 設定を保存し、ブローカー接続を更新しました', 'success');
        setTimeout(updateMqttStatus, 1000);
      } catch (err) {
        showToast('エラー: ' + err.message, 'error');
      } finally {
        btnSave.disabled = false;
        btnSave.textContent = origText;
      }
    });

    // 全再接続ボタン
    btnReconnect?.addEventListener('click', async () => {
      btnReconnect.disabled = true;
      btnReconnect.textContent = '🔄 接続中...';
      try {
        await fetch('/api/mqtt/restart', { method: 'POST' });
        showToast('MQTT クライアントを再起動しました');
        setTimeout(updateMqttStatus, 1500);
      } catch (err) {
        showToast('再接続エラー: ' + err.message, 'error');
      } finally {
        btnReconnect.disabled = false;
        btnReconnect.textContent = '🔄 全再接続';
      }
    });

    // テスト送信ボタン
    btnTest?.addEventListener('click', async () => {
      const inputTestText = document.getElementById('inputMqttTestText');
      const selectTestTarget = document.getElementById('selectMqttTestTarget');
      const selectTestBroker = document.getElementById('selectMqttTestBroker');
      const text = inputTestText?.value.trim();
      const target = selectTestTarget?.value || null;
      const brokerId = selectTestBroker?.value || null;

      if (!text) {
        showToast('テスト発話テキストを入力してください', 'warning');
        return;
      }

      const origText = btnTest.textContent;
      btnTest.disabled = true;
      btnTest.textContent = '📤 送信中...';

      try {
        const res = await fetch('/api/mqtt/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, target, brokerId })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.error || 'テスト送信に失敗しました');

        const pubCount = data.publishedTo ? data.publishedTo.length : 1;
        showToast(`${pubCount} 件のブローカーにPublishしました！まもなくスピーカーから発声されます`, 'success');
        setTimeout(updateMqttStatus, 1000);
      } catch (err) {
        showToast('MQTTテストエラー: ' + err.message, 'error');
      } finally {
        btnTest.disabled = false;
        btnTest.textContent = origText;
      }
    });

    // 定期ポーリング（設定タブ表示時のみ）
    setInterval(() => {
      const mqttTab = document.getElementById('subtab-settings-mqtt');
      if (mqttTab && mqttTab.classList.contains('active')) {
        updateMqttStatus();
      }
    }, 10000);

    renderMqttSpeakerOptions();
  }

  // ================= 8.6. MCP 連携設定 (Claude Desktop / Cursor / Cline) =================
  let mcpConnectionMode = 'local'; // 'local' | 'internet'

  function updateMcpConfigSnippets() {
    const preClaude = document.getElementById('preClaudeConfig');
    const preCursor = document.getElementById('preCursorConfig');
    if (!preClaude && !preCursor) return;

    const token = state.settings?.webhookToken || '';
    const host = location.host || '127.0.0.1:8080';
    const proto = location.protocol || 'http:';

    let sseUrl = '';
    if (mcpConnectionMode === 'local') {
      sseUrl = `${proto}//${host}/mcp/sse`;
    } else {
      let tunnelDomain = state.serverStatus?.tunnelDomain;
      if (!tunnelDomain) {
        const isIp = /^[0-9.]+(:[0-9]+)?$/.test(host);
        tunnelDomain = isIp ? 'your-tunnel-domain.com' : host;
      }
      sseUrl = `https://${tunnelDomain}/mcp/sse${token ? '?token=' + encodeURIComponent(token) : ''}`;
    }



    // Claude Desktop 設定
    const claudeJson = {
      mcpServers: {
        voicehub: {
          url: sseUrl
        }
      }
    };
    if (preClaude) {
      preClaude.textContent = JSON.stringify(claudeJson, null, 2);
    }

    // Cursor / Cline 設定
    const cursorJson = {
      name: "voicehub",
      type: "sse",
      url: sseUrl
    };
    if (preCursor) {
      preCursor.textContent = JSON.stringify(cursorJson, null, 2);
    }
  }

  async function updateMcpStatus() {
    const statsEl = document.getElementById('mcpCallStats');
    if (!statsEl) return;
    try {
      const res = await fetch('/api/mcp/status');
      if (res.ok) {
        const data = await res.json();
        statsEl.textContent = `セッション: ${data.activeSessions || 0} | 呼出: ${data.totalCalls || 0} 回${data.lastCallAt ? ' (最終: ' + data.lastCallAt.slice(11) + ')' : ''}`;
      }
    } catch (e) {
      // ignore
    }
  }

  function setupMcpSettings() {
    const btnLocal = document.getElementById('btnMcpModeLocal');
    const btnInternet = document.getElementById('btnMcpModeInternet');
    const btnCopyClaude = document.getElementById('btnCopyClaudeConfig');
    const btnCopyCursor = document.getElementById('btnCopyCursorConfig');
    const selectSimTool = document.getElementById('selectMcpSimTool');
    const btnExecuteSim = document.getElementById('btnExecuteMcpSim');
    const preSimResult = document.getElementById('preMcpSimResult');
    const selSimTarget = document.getElementById('mcpSimSpeakTarget');

    // モード切り替え
    btnLocal?.addEventListener('click', () => {
      mcpConnectionMode = 'local';
      btnLocal.classList.add('active');
      btnInternet?.classList.remove('active');
      updateMcpConfigSnippets();
    });

    btnInternet?.addEventListener('click', () => {
      mcpConnectionMode = 'internet';
      btnInternet.classList.add('active');
      btnLocal?.classList.remove('active');
      updateMcpConfigSnippets();
    });

    // コピーボタン
    btnCopyClaude?.addEventListener('click', () => {
      const text = document.getElementById('preClaudeConfig')?.textContent || '';
      navigator.clipboard.writeText(text).then(() => {
        showToast('Claude Desktop 設定 JSON をクリップボードにコピーしました！', 'success');
      });
    });

    btnCopyCursor?.addEventListener('click', () => {
      const text = document.getElementById('preCursorConfig')?.textContent || '';
      navigator.clipboard.writeText(text).then(() => {
        showToast('Cursor / Cline 設定 JSON をクリップボードにコピーしました！', 'success');
      });
    });

    // シミュレーター: ツール選択切り替え
    selectSimTool?.addEventListener('change', (e) => {
      const val = e.target.value;
      const argsSpeak = document.getElementById('mcpSimArgsSpeak');
      const argsDnd = document.getElementById('mcpSimArgsDnd');
      if (argsSpeak) argsSpeak.style.display = (val === 'speak') ? 'block' : 'none';
      if (argsDnd) argsDnd.style.display = (val === 'set_dnd') ? 'block' : 'none';
    });

    // シミュレーター: ツール実行
    btnExecuteSim?.addEventListener('click', async () => {
      const tool = selectSimTool?.value || 'speak';
      const origText = btnExecuteSim.textContent;
      btnExecuteSim.disabled = true;
      btnExecuteSim.textContent = '実行中...';

      let args = {};
      if (tool === 'speak') {
        const text = document.getElementById('mcpSimSpeakText')?.value.trim() || 'テスト発話です';
        const target = document.getElementById('mcpSimSpeakTarget')?.value || '';
        args = { text, target };
      } else if (tool === 'set_dnd') {
        const enabled = document.getElementById('mcpSimDndEnabled')?.checked !== false;
        const reason = document.getElementById('mcpSimDndReason')?.value || 'MCPテスト';
        args = { enabled, reason };
      }

      try {
        const res = await fetch('/api/mcp/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tool, arguments: args })
        });
        const data = await res.json();
        if (preSimResult) {
          preSimResult.textContent = JSON.stringify(data, null, 2);
        }
        showToast(`MCP ツール [${tool}] を実行しました`, 'success');
        updateMcpStatus();
      } catch (err) {
        if (preSimResult) preSimResult.textContent = 'エラー: ' + err.message;
        showToast('MCP実行エラー: ' + err.message, 'error');
      } finally {
        btnExecuteSim.disabled = false;
        btnExecuteSim.textContent = origText;
      }
    });

    // スピーカー一覧の反映
    window.renderMcpSpeakerOptions = () => {
      if (!selSimTarget) return;
      const cur = selSimTarget.value;
      const devs = state.devices || [];
      const opts = ['<option value="">デフォルトスピーカー</option>', '<option value="ALL">全スピーカー一斉 (ALL)</option>'];
      devs.forEach(d => {
        opts.push(`<option value="${escapeHtml(d.name || d.ip)}">${escapeHtml(getDeviceDisplayName(d.name || d.ip))}</option>`);
      });
      selSimTarget.innerHTML = opts.join('\n');
      selSimTarget.value = cur;
    };

    updateMcpConfigSnippets();
    updateMcpStatus();
    window.renderMcpSpeakerOptions();
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

      let rawModels = data.models || data[provider] || [];
      const models = rawModels.map(m => typeof m === 'string' ? { id: m, name: m } : m);
      const defaultModel = provider === 'gemini' ? 'gemini-2.5-flash' : 'gpt-4o-mini';
      let currentSelected = selectEl.value || data.currentModel || defaultModel;
      if (typeof currentSelected === 'string' && (currentSelected.includes('1.5') || currentSelected.includes('1.0') || currentSelected.includes('2.0'))) {
        currentSelected = defaultModel;
      }


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
      if (geminiModelSelect) {
        let targetModel = ai.geminiModel || 'gemini-2.5-flash';
        if (targetModel.includes('3.8') || targetModel.includes('3.5') || targetModel.includes('argon')) {
          targetModel = 'gemini-2.5-flash';
        }
        if (Array.from(geminiModelSelect.options).some(o => o.value === targetModel)) {
          geminiModelSelect.value = targetModel;
        } else {
          geminiModelSelect.value = 'gemini-2.5-flash';
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

  // ================= 8. 防災・緊急速報 & 天気設定 =================
  let disasterPrefectures = [];

  async function loadDisasterSettings() {
    try {
      const [settingsRes, statusRes] = await Promise.all([
        fetch('/api/disaster/settings'),
        fetch('/api/disaster/status')
      ]);

      if (!settingsRes.ok) return;
      const data = await settingsRes.json();
      const status = statusRes.ok ? await statusRes.json() : {};

      // ステータスバッジ
      const badge = document.getElementById('disasterStatusBadge');
      const statusText = document.getElementById('disasterStatusText');
      if (statusText) {
        if (status.wsConnected) {
          statusText.textContent = 'P2P地震速報: 接続中 (リアルタイム監視)';
          if (badge) badge.style.borderColor = 'rgba(16, 185, 129, 0.4)';
        } else {
          statusText.textContent = 'P2P地震速報: 再接続待機中';
          if (badge) badge.style.borderColor = 'rgba(245, 158, 11, 0.4)';
        }
      }

      // マスター有効/無効
      const elDisasterEnabled = document.getElementById('settingDisasterEnabled');
      if (elDisasterEnabled) elDisasterEnabled.checked = data.enabled !== false;

      // 通知先スピーカー設定
      const targetScope = data.targetScope || 'all';
      const targetRadio = document.querySelector(`input[name="disasterTargetScope"][value="${targetScope}"]`);
      if (targetRadio) targetRadio.checked = true;
      const spkWrapper = document.getElementById('disasterSpeakersWrapper');
      if (spkWrapper) spkWrapper.style.display = targetScope === 'specific' ? 'block' : 'none';
      renderDisasterSpeakers(data.targetDevices || []);

      // 都道府県・市区町村ドロップダウン読み込み
      await loadDisasterAreas(data.area?.prefCode, data.area?.cityCode);

      // 朝の予定まとめ
      const elDailyWeatherEnabled = document.getElementById('settingDailyWeatherEnabled');
      if (elDailyWeatherEnabled) elDailyWeatherEnabled.checked = data.dailyWeather?.enabled !== false;
      const elDailyWeatherAdvice = document.getElementById('settingDailyWeatherAdvice');
      if (elDailyWeatherAdvice) elDailyWeatherAdvice.checked = data.dailyWeather?.includeAdvice !== false;

      // EEW
      const elEewEnabled = document.getElementById('settingEewEnabled');
      if (elEewEnabled) elEewEnabled.checked = data.earthquake?.eewEnabled !== false;
      const elEewUrgent = document.getElementById('settingEewUrgent');
      if (elEewUrgent) elEewUrgent.checked = data.earthquake?.eewUrgent !== false;
      const elEewVolume = document.getElementById('settingEewVolume');
      const elEewVolumeDisplay = document.getElementById('eewVolumeDisplay');
      if (elEewVolume) {
        elEewVolume.value = data.earthquake?.eewVolume || 80;
        if (elEewVolumeDisplay) elEewVolumeDisplay.textContent = `${elEewVolume.value}%`;
      }

      // 震度速報
      const elQuakeReportEnabled = document.getElementById('settingQuakeReportEnabled');
      if (elQuakeReportEnabled) elQuakeReportEnabled.checked = data.earthquake?.reportEnabled !== false;
      const elQuakeMinScale = document.getElementById('settingQuakeMinScale');
      if (elQuakeMinScale) elQuakeMinScale.value = String(data.earthquake?.minScale || 30);
      const elQuakeTargetScope = document.getElementById('settingQuakeTargetScope');
      if (elQuakeTargetScope) elQuakeTargetScope.value = data.earthquake?.targetScope || 'local';
      const elQuakeReportUrgent = document.getElementById('settingQuakeReportUrgent');
      if (elQuakeReportUrgent) elQuakeReportUrgent.checked = !!data.earthquake?.reportUrgent;

      // 気象警報
      const elWeatherWarningEnabled = document.getElementById('settingWeatherWarningEnabled');
      if (elWeatherWarningEnabled) elWeatherWarningEnabled.checked = data.weatherWarning?.enabled !== false;
      const elWeatherWarningLevel = document.getElementById('settingWeatherWarningLevel');
      if (elWeatherWarningLevel) elWeatherWarningLevel.value = data.weatherWarning?.level || 'warning';
      const elWeatherWarningNotifyClear = document.getElementById('settingWeatherWarningNotifyClear');
      if (elWeatherWarningNotifyClear) elWeatherWarningNotifyClear.checked = data.weatherWarning?.notifyClear !== false;
      const elWeatherWarningUrgent = document.getElementById('settingWeatherWarningUrgent');
      if (elWeatherWarningUrgent) elWeatherWarningUrgent.checked = !!data.weatherWarning?.urgent;

      // 天気予報プレビューの更新
      updateWeatherPreview();
    } catch (err) {
      console.warn('[Disaster] 設定読み込みエラー:', err.message);
    }
  }

  async function loadDisasterAreas(selectedPrefCode = '130000', selectedCityCode = '') {
    const prefSelect = document.getElementById('settingDisasterPref');
    if (!prefSelect) return;

    try {
      if (disasterPrefectures.length === 0) {
        const res = await fetch('/api/disaster/areas');
        if (res.ok) {
          const data = await res.json();
          disasterPrefectures = data.prefectures || [];
        }
      }

      prefSelect.innerHTML = '';
      for (const p of disasterPrefectures) {
        const opt = document.createElement('option');
        opt.value = p.code;
        opt.textContent = p.name;
        if (p.code === selectedPrefCode) opt.selected = true;
        prefSelect.appendChild(opt);
      }

      const currentPref = prefSelect.value || selectedPrefCode || '130000';
      await loadCitiesDropdown(currentPref, selectedCityCode);
    } catch (err) {
      console.warn('[Disaster] エリア一覧取得エラー:', err.message);
    }
  }

  async function loadCitiesDropdown(prefCode, selectedCityCode = '') {
    const citySelect = document.getElementById('settingDisasterCity');
    if (!citySelect) return;

    citySelect.innerHTML = '<option value="">都道府県全域 (指定なし)</option>';
    if (!prefCode) return;

    try {
      const res = await fetch(`/api/disaster/areas?prefCode=${prefCode}`);
      if (res.ok) {
        const data = await res.json();
        const cities = data.cities || [];
        for (const c of cities) {
          const opt = document.createElement('option');
          opt.value = c.code;
          opt.textContent = `${c.name}${c.kana ? ` (${c.kana})` : ''}`;
          if (c.code === selectedCityCode) opt.selected = true;
          citySelect.appendChild(opt);
        }
      }
    } catch (err) {
      console.warn('[Disaster] 市区町村取得エラー:', err.message);
    }
  }

  async function updateWeatherPreview() {
    const box = document.getElementById('weatherPreviewContent');
    if (!box) return;
    box.textContent = '気象庁から最新の天気予報を取得中...';

    try {
      const res = await fetch('/api/disaster/weather');
      const data = await res.json();
      if (res.ok && data && data.weather) {
        box.replaceChildren();
        const line1 = document.createElement('div');
        line1.style.fontWeight = '600';
        line1.style.color = '#38bdf8';
        line1.textContent = `📍 ${data.areaName}: ${data.weather}`;

        const line2 = document.createElement('div');
        line2.style.fontSize = '0.85rem';
        line2.style.marginTop = '4px';
        line2.style.color = 'var(--text-muted)';
        const tempPart = (data.tempMax || data.tempMin) ? `気温: ${data.tempMax || '--'} / ${data.tempMin || '--'}` : '';
        const popPart = data.pop ? `降水確率: ${data.pop}` : '';
        line2.textContent = [tempPart, popPart].filter(Boolean).join(' | ');

        box.appendChild(line1);
        box.appendChild(line2);

        if (data.advice) {
          const line3 = document.createElement('div');
          line3.style.fontSize = '0.82rem';
          line3.style.marginTop = '4px';
          line3.style.color = '#fbbf24';
          line3.textContent = `💡 ${data.advice}`;
          box.appendChild(line3);
        }
      } else {
        box.textContent = '天気予報データの取得に失敗しました';
      }
    } catch (err) {
      box.textContent = '通信エラー: ' + err.message;
    }
  }

  function setupDisasterHandlers() {
    // 都道府県切り替え連動
    const prefSelect = document.getElementById('settingDisasterPref');
    prefSelect?.addEventListener('change', async (e) => {
      await loadCitiesDropdown(e.target.value);
      updateWeatherPreview();
    });

    // 市区町村切り替え連動
    const citySelect = document.getElementById('settingDisasterCity');
    citySelect?.addEventListener('change', () => {
      updateWeatherPreview();
    });

    // 天気予報更新ボタン
    document.getElementById('btnRefreshWeatherPreview')?.addEventListener('click', () => {
      updateWeatherPreview();
    });

    // EEW 音量スライダー
    const eewVol = document.getElementById('settingEewVolume');
    const eewVolDisplay = document.getElementById('eewVolumeDisplay');
    eewVol?.addEventListener('input', (e) => {
      if (eewVolDisplay) eewVolDisplay.textContent = `${e.target.value}%`;
    });

    // 通知先スピーカーのスコープラジオ切り替え
    document.querySelectorAll('input[name="disasterTargetScope"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        const spkWrapper = document.getElementById('disasterSpeakersWrapper');
        if (spkWrapper) {
          spkWrapper.style.display = e.target.value === 'specific' ? 'block' : 'none';
        }
      });
    });

    // 保存ボタン
    document.getElementById('btnSaveDisasterSettings')?.addEventListener('click', async () => {
      const btn = document.getElementById('btnSaveDisasterSettings');
      if (btn) {
        btn.disabled = true;
        btn.textContent = '保存中...';
      }

      try {
        const prefCode = document.getElementById('settingDisasterPref')?.value || '130000';
        const prefOpt = document.getElementById('settingDisasterPref')?.selectedOptions?.[0];
        const prefName = prefOpt ? prefOpt.textContent : '東京都';

        const cityCode = document.getElementById('settingDisasterCity')?.value || '';
        const cityOpt = document.getElementById('settingDisasterCity')?.selectedOptions?.[0];
        let cityName = '';
        if (cityCode && cityOpt) {
          cityName = cityOpt.textContent.split(' ')[0];
        }

        const targetScope = document.querySelector('input[name="disasterTargetScope"]:checked')?.value || 'all';
        const targetDevices = getSelectedSpeakers(document.getElementById('disasterSpeakersContainer'));

        const payload = {
          enabled: document.getElementById('settingDisasterEnabled')?.checked !== false,
          targetScope,
          targetDevices,
          area: {
            prefCode,
            prefName,
            cityCode,
            cityName
          },
          earthquake: {
            enabled: document.getElementById('settingQuakeReportEnabled')?.checked !== false || document.getElementById('settingEewEnabled')?.checked !== false,
            eewEnabled: document.getElementById('settingEewEnabled')?.checked !== false,
            eewUrgent: document.getElementById('settingEewUrgent')?.checked !== false,
            eewVolume: parseInt(document.getElementById('settingEewVolume')?.value || 80, 10),
            reportEnabled: document.getElementById('settingQuakeReportEnabled')?.checked !== false,
            minScale: parseInt(document.getElementById('settingQuakeMinScale')?.value || 30, 10),
            targetScope: document.getElementById('settingQuakeTargetScope')?.value || 'local',
            reportUrgent: !!document.getElementById('settingQuakeReportUrgent')?.checked
          },
          weatherWarning: {
            enabled: document.getElementById('settingWeatherWarningEnabled')?.checked !== false,
            level: document.getElementById('settingWeatherWarningLevel')?.value || 'warning',
            notifyClear: document.getElementById('settingWeatherWarningNotifyClear')?.checked !== false,
            urgent: !!document.getElementById('settingWeatherWarningUrgent')?.checked
          },
          dailyWeather: {
            enabled: document.getElementById('settingDailyWeatherEnabled')?.checked !== false,
            includeAdvice: document.getElementById('settingDailyWeatherAdvice')?.checked !== false
          }
        };

        const res = await fetch('/api/disaster/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          showToast('防災・気象設定を保存しました', 'success');
          updateWeatherPreview();
        } else {
          const errData = await res.json();
          throw new Error(errData.error || '保存に失敗しました');
        }
      } catch (err) {
        showToast('保存エラー: ' + err.message, 'error');
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.textContent = '💾 防災・気象設定を保存';
        }
      }
    });

    // テスト発話ハンドラー
    async function triggerDisasterTest(type, label) {
      showToast(`${label}を発報しています...`, 'info');
      try {
        const res = await fetch('/api/disaster/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          showToast(`${label}を発声しました: 「${data.text}」`, 'success');
        } else {
          throw new Error(data.error || 'テスト発声に失敗しました');
        }
      } catch (err) {
        showToast(`テスト発声エラー: ${err.message}`, 'error');
      }
    }

    document.getElementById('btnTestEew')?.addEventListener('click', () => triggerDisasterTest('eew', '緊急地震速報 (EEW) テスト'));
    document.getElementById('btnTestEewCancel')?.addEventListener('click', () => triggerDisasterTest('eew_cancel', '緊急地震速報 取消テスト'));
    document.getElementById('btnTestQuake')?.addEventListener('click', () => triggerDisasterTest('quake', '震度速報テスト'));
    document.getElementById('btnTestWarning')?.addEventListener('click', () => triggerDisasterTest('warning', '気象警報テスト'));
    document.getElementById('btnTestWeatherSummary')?.addEventListener('click', () => triggerDisasterTest('weather', '朝の天気サマリーテスト'));
  }

  // 起動実行
  init();
});
