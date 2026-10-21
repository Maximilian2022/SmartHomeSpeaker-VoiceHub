// ==========================================================================
// Voice Hub - Lightweight i18n Internationalization Engine (i18n.js)
// ==========================================================================

(() => {
  'use strict';

  // サポート言語一覧（言語追加時はこの配列に1行足すだけで自動反映）
  const SUPPORTED_LANGUAGES = [
    { code: 'ja', label: '日本語' },
    { code: 'en', label: 'English' }
  ];

  // 最終フォールバック言語（未翻訳キーや未対応ロケール時の世界標準フォールバック）
  const DEFAULT_FALLBACK_LANG = 'en';

  // メモリ内辞書キャッシュ
  const dictionaries = {};

  // 現在のアクティブ言語
  let currentLang = DEFAULT_FALLBACK_LANG;

  /**
   * ブラウザロケールおよび保存設定から最適な初期言語を動的判定
   * 1. ユーザー手動選択値 (localStorage: voicehub_lang)
   * 2. ブラウザ優先言語 (navigator.languages / navigator.language)
   * 3. 最終フォールバック (en: 英語)
   */
  function detectInitialLanguage() {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const urlLang = urlParams.get('lang') || urlParams.get('lng');
      if (urlLang && SUPPORTED_LANGUAGES.some(l => l.code === urlLang)) {
        try { localStorage.setItem('voicehub_lang', urlLang); } catch (_) {}
        return urlLang;
      }
    } catch (_) {}

    try {
      const saved = localStorage.getItem('voicehub_lang');
      if (saved && SUPPORTED_LANGUAGES.some(l => l.code === saved)) {
        return saved;
      }
    } catch (_) {}

    const browserLangs = (navigator.languages && navigator.languages.length)
      ? navigator.languages
      : [navigator.language || navigator.userLanguage || ''];

    const supportedCodes = SUPPORTED_LANGUAGES.map(l => l.code);

    for (const bLang of browserLangs) {
      if (!bLang) continue;
      const clean = String(bLang).toLowerCase();
      const primary = clean.split('-')[0];

      // 完全一致（例: 'en'）または 第一言語コード一致（例: 'ja-JP' -> 'ja'）
      const match = supportedCodes.find(code => code === clean || code === primary);
      if (match) {
        return match;
      }
    }

    return DEFAULT_FALLBACK_LANG;
  }

  /**
   * 指定言語の辞書JSONを非同期ロード（キャッシュ付き）
   */
  async function loadDictionary(lang) {
    if (dictionaries[lang]) {
      return dictionaries[lang];
    }
    try {
      const res = await fetch(`/locales/${encodeURIComponent(lang)}.json?v=1.0`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status} while fetching /locales/${lang}.json`);
      }
      const data = await res.json();
      dictionaries[lang] = data;
      return data;
    } catch (err) {
      console.warn(`[i18n] Failed to load locale "${lang}":`, err);
      dictionaries[lang] = {};
      return dictionaries[lang];
    }
  }

  /**
   * ネストされたオブジェクトからキーを安全に取得
   */
  function getNestedValue(obj, keyPath) {
    if (!obj || typeof obj !== 'object') return undefined;
    const parts = keyPath.split('.');
    let curr = obj;
    for (const part of parts) {
      if (curr == null || typeof curr !== 'object') return undefined;
      curr = curr[part];
    }
    return curr;
  }

  /**
   * プレースホルダー {name} を params で置換
   */
  function interpolate(text, params) {
    if (!params || typeof params !== 'object') return text;
    return String(text).replace(/\{([a-zA-Z0-9_-]+)\}/g, (match, paramKey) => {
      return params[paramKey] !== undefined ? String(params[paramKey]) : match;
    });
  }

  /**
   * 翻訳文字列を取得する関数
   * @param {string} key - 'tabs.say' や 'header.connecting' などのドット区切りキー
   * @param {Object} [params] - '{size: "12MB"}' などの置換パラメータ
   * @param {string} [defaultValue] - 見つからない場合のデフォルト値
   */
  function t(key, params, defaultValue) {
    if (!key) return '';

    // 1. 現在のアクティブ言語の辞書から探索
    let val = getNestedValue(dictionaries[currentLang], key);

    // 2. なければ最終フォールバック言語 (en) から探索
    if (val === undefined && currentLang !== DEFAULT_FALLBACK_LANG) {
      val = getNestedValue(dictionaries[DEFAULT_FALLBACK_LANG], key);
    }

    // 3. なければ ja 辞書から探索 (初期フォールバック)
    if (val === undefined && currentLang !== 'ja' && DEFAULT_FALLBACK_LANG !== 'ja') {
      val = getNestedValue(dictionaries['ja'], key);
    }

    // 4. なければ引数のデフォルト値、最終的にキー名自体
    if (val === undefined) {
      val = defaultValue !== undefined ? defaultValue : key;
    }

    return interpolate(val, params);
  }

  /**
   * DOM内の i18n 属性を走査してテキスト・属性を一括適用
   */
  function applyTranslations(root = document) {
    // 1. data-i18n (テキストまたはHTML置換)
    const elements = root.querySelectorAll('[data-i18n]');
    elements.forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (!key) return;

      const isHtml = el.getAttribute('data-i18n-html') === 'true';
      const translation = t(key);

      // 子要素（例: svgアイコン）を直接持っている場合の安全策:
      // 子要素にsvgや子タグが存在し、data-i18n-target="text-node" が指定されている場合、テキストノードのみ更新
      const textNodeTarget = el.getAttribute('data-i18n-target') === 'text-node';
      if (textNodeTarget) {
        let updated = false;
        for (const child of el.childNodes) {
          if (child.nodeType === Node.TEXT_NODE && child.textContent.trim().length > 0) {
            child.textContent = translation;
            updated = true;
            break;
          }
        }
        if (!updated) {
          el.appendChild(document.createTextNode(translation));
        }
      } else if (isHtml) {
        el.innerHTML = translation;
      } else {
        el.textContent = translation;
      }
    });

    // 2. data-i18n-placeholder (プレースホルダー置換)
    const placeholders = root.querySelectorAll('[data-i18n-placeholder]');
    placeholders.forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (key) {
        el.placeholder = t(key);
      }
    });

    // 3. data-i18n-title (ツールチップ置換)
    const titles = root.querySelectorAll('[data-i18n-title]');
    titles.forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      if (key) {
        el.title = t(key);
      }
    });

    // 4. data-i18n-aria-label (アクセシビリティラベル置換)
    const arias = root.querySelectorAll('[data-i18n-aria-label]');
    arias.forEach(el => {
      const key = el.getAttribute('data-i18n-aria-label');
      if (key) {
        el.setAttribute('aria-label', t(key));
      }
    });
  }

  /**
   * 言語切替を実行
   * @param {string} newLang - 切り替え先言語コード ('ja' | 'en')
   */
  async function setLanguage(newLang) {
    if (!SUPPORTED_LANGUAGES.some(l => l.code === newLang)) {
      console.warn(`[i18n] Unsupported language: ${newLang}`);
      return;
    }

    // 辞書ロード
    await loadDictionary(newLang);
    currentLang = newLang;

    // localStorageに保存
    try {
      localStorage.setItem('voicehub_lang', newLang);
    } catch (_) {}

    // HTML lang属性更新
    document.documentElement.lang = newLang;

    // DOMへの一括適用
    applyTranslations(document);

    // ドロップダウンの選択値を同期
    const selectEl = document.getElementById('headerLanguageSelect');
    if (selectEl && selectEl.value !== newLang) {
      selectEl.value = newLang;
    }

    // カスタムイベントを発火（app.js 側の動的コンポーネント再描画用）
    window.dispatchEvent(new CustomEvent('voicehub:language-changed', {
      detail: { lang: newLang, t }
    }));
  }

  /**
   * ヘッダーの言語ドロップダウンを動的に描画・イベント登録
   */
  function renderLanguageSelector(selectEl) {
    if (!selectEl) return;

    selectEl.innerHTML = SUPPORTED_LANGUAGES.map(lang => {
      return `<option value="${lang.code}">${lang.label}</option>`;
    }).join('');

    selectEl.value = currentLang;

    // 変更イベント
    selectEl.addEventListener('change', (e) => {
      setLanguage(e.target.value);
    });
  }

  /**
   * 初期化
   */
  async function init() {
    currentLang = detectInitialLanguage();

    // 最終フォールバック言語（en）と現在言語をロード
    const promises = [loadDictionary(currentLang)];
    if (currentLang !== DEFAULT_FALLBACK_LANG) {
      promises.push(loadDictionary(DEFAULT_FALLBACK_LANG));
    }
    await Promise.all(promises);

    // HTML lang 属性更新
    document.documentElement.lang = currentLang;

    // ヘッダーセレクトボックスの動的初期化
    const selectEl = document.getElementById('headerLanguageSelect');
    if (selectEl) {
      renderLanguageSelector(selectEl);
    }

    // 初回DOM翻訳適用
    applyTranslations(document);

    console.log(`[i18n] Initialized with language: ${currentLang}`);
  }

  // グローバル公開
  window.i18n = {
    SUPPORTED_LANGUAGES,
    DEFAULT_FALLBACK_LANG,
    detectInitialLanguage,
    loadDictionary,
    t,
    applyTranslations,
    setLanguage,
    getLanguage: () => currentLang,
    renderLanguageSelector,
    init
  };

  // 簡略記法 window.t も提供
  window.t = (key, params, defaultValue) => t(key, params, defaultValue);

  // DOMContentLoaded または 即時実行
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
