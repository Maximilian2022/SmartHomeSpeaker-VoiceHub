/**
 * Disaster & Weather Alert Manager (disaster.js)
 * - P2P地震情報 API / WebSocket (緊急地震速報 EEW & 震度速報)
 * - 気象庁 防災情報 API (気象警報・注意報 差分監視)
 * - 気象庁 天気予報 API (毎朝のAI予定サマリー用 天気・気温・降水確率)
 */

const fs = require('fs');
const path = require('path');
const settingsManager = require('./settings');

// 47都道府県マスター (気象庁 offices コード & 接頭辞)
const PREFECTURE_MASTER = [
  { code: '016000', name: '北海道 (石狩・空知・後志)', prefix: '01' },
  { code: '020000', name: '青森県', prefix: '02' },
  { code: '030000', name: '岩手県', prefix: '03' },
  { code: '040000', name: '宮城県', prefix: '04' },
  { code: '050000', name: '秋田県', prefix: '05' },
  { code: '060000', name: '山形県', prefix: '06' },
  { code: '070000', name: '福島県', prefix: '07' },
  { code: '080000', name: '茨城県', prefix: '08' },
  { code: '090000', name: '栃木県', prefix: '09' },
  { code: '100000', name: '群馬県', prefix: '10' },
  { code: '110000', name: '埼玉県', prefix: '11' },
  { code: '120000', name: '千葉県', prefix: '12' },
  { code: '130000', name: '東京都', prefix: '13' },
  { code: '140000', name: '神奈川県', prefix: '14' },
  { code: '150000', name: '新潟県', prefix: '15' },
  { code: '160000', name: '富山県', prefix: '16' },
  { code: '170000', name: '石川県', prefix: '17' },
  { code: '180000', name: '福井県', prefix: '18' },
  { code: '190000', name: '山梨県', prefix: '19' },
  { code: '200000', name: '長野県', prefix: '20' },
  { code: '210000', name: '岐阜県', prefix: '21' },
  { code: '220000', name: '静岡県', prefix: '22' },
  { code: '230000', name: '愛知県', prefix: '23' },
  { code: '240000', name: '三重県', prefix: '24' },
  { code: '250000', name: '滋賀県', prefix: '25' },
  { code: '260000', name: '京都府', prefix: '26' },
  { code: '270000', name: '大阪府', prefix: '27' },
  { code: '280000', name: '兵庫県', prefix: '28' },
  { code: '290000', name: '奈良県', prefix: '29' },
  { code: '300000', name: '和歌山県', prefix: '30' },
  { code: '310000', name: '鳥取県', prefix: '31' },
  { code: '320000', name: '島根県', prefix: '32' },
  { code: '330000', name: '岡山県', prefix: '33' },
  { code: '340000', name: '広島県', prefix: '34' },
  { code: '350000', name: '山口県', prefix: '35' },
  { code: '360000', name: '徳島県', prefix: '36' },
  { code: '370000', name: '香川県', prefix: '37' },
  { code: '380000', name: '愛媛県', prefix: '38' },
  { code: '390000', name: '高知県', prefix: '39' },
  { code: '400000', name: '福岡県', prefix: '40' },
  { code: '410000', name: '佐賀県', prefix: '41' },
  { code: '420000', name: '長崎県', prefix: '42' },
  { code: '430000', name: '熊本県', prefix: '43' },
  { code: '440000', name: '大分県', prefix: '44' },
  { code: '450000', name: '宮崎県', prefix: '45' },
  { code: '460100', name: '鹿児島県', prefix: '46' },
  { code: '471000', name: '沖縄県 (本島)', prefix: '47' }
];

// 震度コードのテキスト変換
const SCALE_MAP = {
  10: '震度1',
  20: '震度2',
  30: '震度3',
  40: '震度4',
  45: '震度5弱',
  50: '震度5強',
  55: '震度6弱',
  60: '震度6強',
  70: '震度7'
};

class DisasterManager {
  constructor() {
    this.ws = null;
    this.wsReconnectTimer = null;
    this.wsPingTimer = null;
    this.warningPollTimer = null;
    this.lastProcessedEarthquakeId = null;
    this.activeEewEvents = new Map(); // eventId -> { notifiedAt: number, matchedAreaName: string }
    this.lastKnownWarnings = new Set(); // 直近検知した警報名のセット
    this.areaDataCache = null; // 気象庁 area.json のキャッシュ
    this.speechExecutor = null; // 音声発話関数 (text, targets, options)
    this.isWsConnected = false;
  }

  setSpeechExecutor(executor) {
    this.speechExecutor = executor;
  }

  async speak(text, options = {}) {
    const settings = settingsManager.getDisasterSettings();
    let targets = ['ALL'];
    if (settings.targetScope === 'default') {
      targets = ['default'];
    } else if (settings.targetScope === 'specific') {
      const devs = Array.isArray(settings.targetDevices) ? settings.targetDevices.filter(Boolean) : [];
      targets = devs.length > 0 ? devs : ['ALL'];
    } else {
      targets = ['ALL']; // デフォルトは家中すべてのスピーカー (推奨)
    }

    if (typeof this.speechExecutor === 'function') {
      try {
        await this.speechExecutor(text, targets, options);
      } catch (err) {
        console.error('[Disaster Speech Error]:', err.message);
      }
    } else {
      console.warn('[Disaster] 発話エグゼキュータが未登録です:', text);
    }
  }

  // ================= 1. 初期化・ライフサイクル =================
  async init() {
    console.log('[Disaster] 防災・気象マネージャーを初期化します...');
    await this.loadAreaMaster();
    this.startP2PQuakeWebSocket();
    this.startWarningMonitoring();
  }

  // ================= 2. エリアマスターデータの管理 =================
  async loadAreaMaster() {
    try {
      const res = await fetch('https://www.jma.go.jp/bosai/common/const/area.json', {
        headers: { 'User-Agent': 'SmartHomeSpeaker-VoiceHub/2.0' }
      });
      if (res.ok) {
        this.areaDataCache = await res.json();
        console.log('[Disaster] 気象庁エリアマスターデータを読み込みました');
      }
    } catch (err) {
      console.warn('[Disaster] エリアマスター取得エラー (オフライン動作継続):', err.message);
    }
  }

  getPrefectures() {
    return PREFECTURE_MASTER;
  }

  getCitiesForPrefecture(prefCode) {
    if (!this.areaDataCache || !this.areaDataCache.class20s) {
      return [];
    }
    const targetPref = PREFECTURE_MASTER.find(p => p.code === prefCode);
    const prefix = targetPref ? targetPref.prefix : prefCode.slice(0, 2);

    const cities = [];
    for (const [code, info] of Object.entries(this.areaDataCache.class20s)) {
      if (code.startsWith(prefix)) {
        cities.push({
          code,
          name: info.name,
          kana: info.kana || ''
        });
      }
    }
    return cities.sort((a, b) => a.code.localeCompare(b.code));
  }

  // ================= 3. P2P地震情報 WebSocket 連携 =================
  startP2PQuakeWebSocket() {
    const disasterSettings = settingsManager.getDisasterSettings();
    if (!disasterSettings.enabled || !disasterSettings.earthquake?.enabled) {
      console.log('[Disaster] 地震アラートが無効のため WebSocket 接続を待機します');
      return;
    }

    if (this.ws) {
      try { this.ws.close(); } catch (e) {}
      this.ws = null;
    }

    try {
      console.log('[Disaster] P2P地震情報 WebSocket (wss://api.p2pquake.net/v2/ws) に接続中...');
      this.ws = new WebSocket('wss://api.p2pquake.net/v2/ws');

      this.ws.onopen = () => {
        console.log('[Disaster] P2P地震情報 WebSocket に接続完了');
        this.isWsConnected = true;
        if (this.wsReconnectTimer) {
          clearTimeout(this.wsReconnectTimer);
          this.wsReconnectTimer = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleP2PQuakeMessage(data);
        } catch (err) {
          console.error('[Disaster] WebSocket メッセージパースエラー:', err.message);
        }
      };

      this.ws.onclose = () => {
        this.isWsConnected = false;
        console.warn('[Disaster] P2P地震情報 WebSocket が切断されました。15秒後に再接続します...');
        this.scheduleWsReconnect();
      };

      this.ws.onerror = (err) => {
        this.isWsConnected = false;
        console.warn('[Disaster] P2P地震情報 WebSocket エラー:', err.message || err);
      };
    } catch (err) {
      console.error('[Disaster] WebSocket 初期化失敗:', err.message);
      this.scheduleWsReconnect();
    }
  }

  scheduleWsReconnect() {
    if (this.wsReconnectTimer) return;
    this.wsReconnectTimer = setTimeout(() => {
      this.wsReconnectTimer = null;
      this.startP2PQuakeWebSocket();
    }, 15000);
  }

  handleP2PQuakeMessage(msg) {
    if (!msg || !msg.code) return;
    const settings = settingsManager.getDisasterSettings();
    if (!settings.enabled || !settings.earthquake?.enabled) return;

    // Code 556: 緊急地震速報 (EEW)
    if (msg.code === 556 && settings.earthquake.eewEnabled) {
      this.handleEewMessage(msg, settings);
    }
    // Code 551: 地震情報 (震度速報)
    else if (msg.code === 551 && settings.earthquake.reportEnabled) {
      this.handleQuakeReportMessage(msg, settings);
    }
  }

  // 緊急地震速報 (EEW) 処理
  handleEewMessage(msg, settings) {
    const eqConfig = settings.earthquake || {};
    const userArea = settings.area || {};
    const eventId = msg.issue?.eventId || msg.id || `${msg.earthquake?.originTime}_${msg.earthquake?.hypocenter?.name}`;
    const isCancelled = !!msg.cancelled || !!msg.earthquake?.cancelled;

    // 定期的に古い EEW イベント (1時間以上前) をクリーンアップ
    const now = Date.now();
    for (const [id, data] of this.activeEewEvents.entries()) {
      if (now - data.notifiedAt > 60 * 60 * 1000) {
        this.activeEewEvents.delete(id);
      }
    }

    const existing = this.activeEewEvents.get(eventId);

    // すでに取り消し済みの地震イベントに対する遅延電文は破棄
    if (existing && existing.status === 'cancelled') {
      console.log(`[Disaster] 取消完了済みの緊急地震速報に対する遅延電文のためスキップ: eventId=${eventId}`);
      return;
    }

    // 1. 取消報の処理 (最優先判定)
    if (isCancelled) {
      console.log(`[Disaster] 緊急地震速報 (取消報) を受信しました: eventId=${eventId}`);
      const wasNotified = existing && existing.status === 'notified';
      this.activeEewEvents.set(eventId, { notifiedAt: now, status: 'cancelled' });

      // 自地域で実際に速報を発報していた場合 (または全地域対象設定)、取り消しをアナウンス
      if (wasNotified || eqConfig.targetScope === 'all') {
        console.warn(`[Disaster EEW CANCEL] 緊急地震速報の取消報を発報: eventId=${eventId}`);
        const cancelText = '先ほどの緊急地震速報は取り消されました。誤報、または観測値の修正によるものです。';
        this.speak(cancelText, {
          urgent: eqConfig.eewUrgent !== false,
          volumeLevel: eqConfig.eewVolume || 80
        });
      } else {
        console.log(`[Disaster] 未発報地域または未発報イベントに対する取消報のため発声をスキップ: eventId=${eventId}`);
      }
      return;
    }

    // 2. 通常報・更新報の処理 (同一地震の第2報以降の不要な連呼を防止)
    if (existing && existing.status === 'notified') {
      console.log(`[Disaster] 緊急地震速報の続報 (serial: ${msg.issue?.serial || 'update'}) を受信しましたが発報済みのためスキップ: eventId=${eventId}`);
      return;
    }

    const eewAreas = msg.areas || [];

    // 地域一致チェック (local の場合は自都道府県が含まれるか、all の場合は全国)
    let shouldNotify = false;
    let matchedAreaName = '';

    if (eqConfig.targetScope === 'all' || eewAreas.length === 0) {
      shouldNotify = true;
      matchedAreaName = '各地';
    } else {
      const targetPrefName = userArea.prefName || '';
      const matched = eewAreas.find(a => {
        const areaName = a.name || a.pref || '';
        return targetPrefName && (areaName.includes(targetPrefName) || targetPrefName.includes(areaName));
      });
      if (matched) {
        shouldNotify = true;
        matchedAreaName = userArea.cityName ? `${userArea.prefName}${userArea.cityName}` : userArea.prefName;
      }
    }

    if (!shouldNotify) {
      console.log(`[Disaster] 緊急地震速報を受信しましたが対象外地域のためスキップ: eventId=${eventId}, 対象=${eewAreas.map(a => a.name || a.pref).join(', ')}`);
      return;
    }

    // 発報状態を記録 (続報の重複防止および取消報検知用)
    this.activeEewEvents.set(eventId, {
      notifiedAt: now,
      status: 'notified',
      matchedAreaName
    });

    console.warn(`[Disaster EEW ALERT] 緊急地震速報発報: eventId=${eventId}, 地域=${matchedAreaName}`);
    const text = `緊急地震速報です。強い揺れに警戒してください。身を守る行動を取ってください。`;

    this.speak(text, {
      urgent: eqConfig.eewUrgent !== false,
      volumeLevel: eqConfig.eewVolume || 80
    });
  }

  // 地震情報 (震度速報) 処理
  handleQuakeReportMessage(msg, settings) {
    const eq = msg.earthquake;
    if (!eq) return;

    // 重複発報防止
    const eventKey = `${eq.time}_${eq.hypocenter?.name}_${eq.maxScale}`;
    if (this.lastProcessedEarthquakeId === eventKey) return;
    this.lastProcessedEarthquakeId = eventKey;

    const eqConfig = settings.earthquake || {};
    const userArea = settings.area || {};
    const minScale = parseInt(eqConfig.minScale || 30, 10); // デフォルト震度3

    const points = msg.points || [];
    const maxScale = eq.maxScale || 0;

    let targetHit = false;
    let localScale = maxScale;
    let localAreaName = '';

    if (eqConfig.targetScope === 'all') {
      if (maxScale >= minScale) {
        targetHit = true;
        localAreaName = '各地';
        localScale = maxScale;
      }
    } else {
      // 自地域 (都道府県 または 市区町村) の観測点を検索
      const prefName = userArea.prefName || '';
      const cityName = userArea.cityName || '';

      let bestMatch = null;
      for (const p of points) {
        if (p.pref && prefName && (p.pref.includes(prefName) || prefName.includes(p.pref))) {
          if (cityName && p.addr && (p.addr.includes(cityName) || cityName.includes(p.addr))) {
            bestMatch = p;
            break;
          }
          if (!bestMatch || (p.scale > bestMatch.scale)) {
            bestMatch = p;
          }
        }
      }

      if (bestMatch && bestMatch.scale >= minScale) {
        targetHit = true;
        localScale = bestMatch.scale;
        localAreaName = cityName ? `${prefName}${cityName}` : prefName;
      }
    }

    if (!targetHit) {
      console.log(`[Disaster] 震度速報を受信しましたが閾値未満のためスキップ: 最大震度=${SCALE_MAP[maxScale] || maxScale}, 設定閾値=${SCALE_MAP[minScale] || minScale}`);
      return;
    }

    const scaleText = SCALE_MAP[localScale] || `震度${localScale / 10}`;
    const hypocenter = eq.hypocenter?.name || '不明';
    const magnitude = eq.hypocenter?.magnitude ? `マグニチュード${eq.hypocenter.magnitude}` : '';
    const tsunami = eq.domesticTsunami === 'Warning' ? '津波に注意してください。' : '';

    const text = `地震情報です。${localAreaName}で${scaleText}の揺れを観測しました。震源は${hypocenter}、${magnitude}です。${tsunami}`;

    console.warn(`[Disaster Quake ALERT] 地震情報発話: ${text}`);
    this.speak(text, {
      urgent: !!eqConfig.reportUrgent
    });
  }

  // ================= 4. 気象庁 気象警報・注意報 差分監視 =================
  startWarningMonitoring() {
    // 5分ごとに警報を定期チェック
    if (this.warningPollTimer) clearInterval(this.warningPollTimer);
    this.warningPollTimer = setInterval(() => {
      this.checkWeatherWarnings().catch(err => {
        console.warn('[Disaster] 気象警報ポーリングエラー:', err.message);
      });
    }, 5 * 60 * 1000);

    // 起動10秒後に初回チェック
    setTimeout(() => {
      this.checkWeatherWarnings(true).catch(e => {});
    }, 10000);
  }

  async checkWeatherWarnings(isInitial = false) {
    const settings = settingsManager.getDisasterSettings();
    if (!settings.enabled || !settings.weatherWarning?.enabled) return;

    const area = settings.area || {};
    const prefCode = area.prefCode || '130000';
    const cityCode = area.cityCode || '';
    const cityName = area.cityName || area.prefName || '';

    try {
      const url = `https://www.jma.go.jp/bosai/warning/data/warning/${prefCode}.json`;
      const res = await fetch(url, {
        headers: { 'User-Agent': 'SmartHomeSpeaker-VoiceHub/2.0' }
      });
      if (!res.ok) return;

      const data = await res.json();
      const areas = data.areaTypes?.[1]?.areas || data.areaTypes?.[0]?.areas || [];

      // 対象市区町村 (未指定なら全体)
      let targetArea = null;
      if (cityCode) {
        targetArea = areas.find(a => a.code === cityCode);
      }
      if (!targetArea && areas.length > 0) {
        targetArea = areas[0];
      }
      if (!targetArea || !targetArea.warnings) return;

      // 有効な警報・注意報の抽出
      const currentWarnings = new Set();
      const warningConfig = settings.weatherWarning;
      const targetLevel = warningConfig.level || 'warning'; // 'special' | 'warning' | 'advisory'

      for (const w of targetArea.warnings) {
        const status = w.status || '';
        const name = w.name || '';
        if (status === '発表警報・注意報はなし' || !name) continue;

        // レベル判定
        const isSpecial = name.includes('特別警報');
        const isWarning = name.includes('警報') && !name.includes('注意報');
        const isAdvisory = name.includes('注意報');

        if (targetLevel === 'special' && isSpecial) {
          currentWarnings.add(name);
        } else if (targetLevel === 'warning' && (isSpecial || isWarning)) {
          currentWarnings.add(name);
        } else if (targetLevel === 'advisory' && (isSpecial || isWarning || isAdvisory)) {
          currentWarnings.add(name);
        }
      }

      // 初回起動時は基準セットを作成するのみ (差分発話はしない)
      if (isInitial) {
        this.lastKnownWarnings = currentWarnings;
        console.log(`[Disaster] 気象警報初期状態を記録: ${Array.from(currentWarnings).join(', ') || 'なし'}`);
        return;
      }

      // 差分検知
      const newlyIssued = [];
      const newlyCleared = [];

      for (const w of currentWarnings) {
        if (!this.lastKnownWarnings.has(w)) newlyIssued.push(w);
      }
      for (const w of this.lastKnownWarnings) {
        if (!currentWarnings.has(w)) newlyCleared.push(w);
      }

      this.lastKnownWarnings = currentWarnings;

      // 新規発表時のアナウンス
      if (newlyIssued.length > 0) {
        const text = `気象情報です。${cityName}に${newlyIssued.join('、')}が発表されました。今後の気象情報にご注意ください。`;
        console.warn(`[Disaster Warning ALERT] 警報発表: ${text}`);
        this.speak(text, {
          urgent: !!warningConfig.urgent
        });
      }

      // 解除時のアナウンス
      if (newlyCleared.length > 0 && warningConfig.notifyClear) {
        const text = `気象情報の更新です。${cityName}の${newlyCleared.join('、')}は解除されました。`;
        console.log(`[Disaster Warning Clear] 警報解除: ${text}`);
        this.speak(text, {
          urgent: false
        });
      }
    } catch (err) {
      console.warn('[Disaster] 気象警報取得エラー:', err.message);
    }
  }

  // ================= 5. 気象庁 天気予報取得 (毎朝のサマリー連携) =================
  async getTodayWeather() {
    const settings = settingsManager.getDisasterSettings();
    const area = settings.area || {};
    const prefCode = area.prefCode || '130000';
    const cityName = area.cityName || area.prefName || '現在地';

    try {
      const url = `https://www.jma.go.jp/bosai/forecast/data/forecast/${prefCode}.json`;
      const res = await fetch(url, {
        headers: { 'User-Agent': 'SmartHomeSpeaker-VoiceHub/2.0' }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      if (!Array.isArray(data) || data.length === 0) throw new Error('データ形式が不正です');

      const timeSeries = data[0].timeSeries || [];
      const weatherArea = timeSeries[0]?.areas?.[0] || {};
      const popArea = timeSeries[1]?.areas?.[0] || {};

      // 天気テロップ
      const weathers = weatherArea.weathers || [];
      const todayWeather = weathers[0] ? weathers[0].replace(/\s+/g, ' ') : '晴れ';

      // 降水確率 (当日の最大確率)
      const pops = popArea.pops || [];
      const maxPop = pops.length > 0 ? Math.max(...pops.map(p => parseInt(p, 10) || 0)) : 0;

      // 気温 (最高・最低気温)
      let tempMax = null;
      let tempMin = null;
      const tempArea = timeSeries[2]?.areas?.[0] || data[1]?.timeSeries?.[1]?.areas?.[0];
      if (tempArea && tempArea.temps) {
        const temps = tempArea.temps.map(t => parseInt(t, 10)).filter(t => !isNaN(t));
        if (temps.length >= 2) {
          tempMin = Math.min(...temps);
          tempMax = Math.max(...temps);
        } else if (temps.length === 1) {
          tempMax = temps[0];
        }
      }

      // 天気アドバイス生成
      let advice = '';
      if (maxPop >= 50) {
        advice = '傘を必ずお持ちください。';
      } else if (maxPop >= 30) {
        advice = '折りたたみ傘があると安心です。';
      } else if (tempMax && tempMax >= 30) {
        advice = '熱中症対策を万全にしてください。';
      } else if (tempMin && tempMin <= 5) {
        advice = '防寒対策をしっかりしてお出かけください。';
      }

      return {
        areaName: cityName,
        weather: todayWeather,
        pop: `${maxPop}%`,
        maxPopValue: maxPop,
        tempMax: tempMax !== null ? `${tempMax}度` : null,
        tempMin: tempMin !== null ? `${tempMin}度` : null,
        advice,
        summaryText: `今日の${cityName}の天気は${todayWeather}${tempMax !== null ? `、最高気温は${tempMax}度` : ''}、降水確率は${maxPop}%です。${advice ? advice : ''}`
      };
    } catch (err) {
      console.warn('[Disaster] 天気予報取得エラー:', err.message);
      return null;
    }
  }

  // ================= 6. テスト発話機能 =================
  async testEew() {
    const settings = settingsManager.getDisasterSettings();
    const cityName = settings.area?.cityName || settings.area?.prefName || '各地';
    const text = `緊急地震速報のテストです。強い揺れに警戒してください。これは訓練放送です。`;
    await this.speak(text, {
      urgent: settings.earthquake?.eewUrgent !== false,
      volumeLevel: settings.earthquake?.eewVolume || 80
    });
    return { success: true, text };
  }

  async testEewCancel() {
    const settings = settingsManager.getDisasterSettings();
    const text = `緊急地震速報の取消テストです。先ほどの緊急地震速報は取り消されました。誤報、または観測値の修正によるものです。これは訓練放送です。`;
    await this.speak(text, {
      urgent: settings.earthquake?.eewUrgent !== false,
      volumeLevel: settings.earthquake?.eewVolume || 80
    });
    return { success: true, text };
  }

  async testQuake() {
    const settings = settingsManager.getDisasterSettings();
    const cityName = settings.area?.cityName || settings.area?.prefName || '東京地方';
    const minScale = settings.earthquake?.minScale || 30;
    const scaleText = SCALE_MAP[minScale] || '震度3';
    const text = `地震情報のテストです。${cityName}で${scaleText}の揺れを観測しました。震源地はテスト湾、マグニチュードは5.0です。この地震による津波の心配はありません。`;
    await this.speak(text, {
      urgent: !!settings.earthquake?.reportUrgent
    });
    return { success: true, text };
  }

  async testWarning() {
    const settings = settingsManager.getDisasterSettings();
    const cityName = settings.area?.cityName || settings.area?.prefName || '地域';
    const text = `気象警報のテストです。${cityName}に大雨警報、および洪水警報が発表されました。これはテスト放送です。`;
    await this.speak(text, {
      urgent: !!settings.weatherWarning?.urgent
    });
    return { success: true, text };
  }

  async testWeatherSummary() {
    const weather = await this.getTodayWeather();
    const summaryText = weather?.summaryText || '本日の天気予報の取得に失敗しました。';
    await this.speak(summaryText, { urgent: false });
    return { success: true, text: summaryText };
  }

  getStatus() {
    return {
      wsConnected: this.isWsConnected,
      lastProcessedEarthquakeId: this.lastProcessedEarthquakeId,
      currentActiveWarnings: Array.from(this.lastKnownWarnings)
    };
  }
}

module.exports = new DisasterManager();
