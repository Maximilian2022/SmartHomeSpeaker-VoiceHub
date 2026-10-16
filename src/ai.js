const settingsManager = require('./settings');

/**
 * AI API 連携モジュール (Google Gemini / OpenAI)
 * DND保留通知の要約、朝の予定まとめアナウンス、モデル動的一覧取得を担当
 */
class AiManager {
  constructor() {
    this.defaultGeminiModel = 'gemini-3.8-flash';
    this.defaultOpenAiModel = 'gpt-4o-mini';
    this.modelCache = {
      gemini: { models: null, timestamp: 0 },
      openai: { models: null, timestamp: 0 }
    };
  }

  /**
   * 有効な API キーを取得 (設定ファイル > 環境変数の優先順位)
   */
  getApiKey(provider = 'gemini') {
    const aiConfig = settingsManager.get().ai || {};
    if (provider === 'gemini') {
      return (aiConfig.geminiApiKey || '').trim() ||
             (process.env.GEMINI_API_KEY || '').trim() ||
             (process.env.AI_API_KEY || '').trim() || '';
    } else if (provider === 'openai') {
      return (aiConfig.openaiApiKey || '').trim() ||
             (process.env.OPENAI_API_KEY || '').trim() || '';
    }
    return '';
  }

  /**
   * 現在利用可能か判定
   */
  isAvailable() {
    const aiConfig = settingsManager.get().ai || {};
    if (aiConfig.enabled === false) return false;
    const provider = aiConfig.provider || 'gemini';
    return !!this.getApiKey(provider);
  }

  /**
   * APIキーの一部をマスク (末尾4文字とプレフィックスのみ表示)
   */
  maskKey(key) {
    if (!key || typeof key !== 'string') return '';
    const trimmed = key.trim();
    if (trimmed.length <= 8) return '****';
    const prefix = trimmed.slice(0, 4);
    const suffix = trimmed.slice(-4);
    return `${prefix}...${suffix}`;
  }

  /**
   * 最新の推奨デフォルトモデル一覧 (フォールバック用)
   */
  getFallbackModels(provider = 'gemini') {
    if (provider === 'gemini') {
      return [
        { id: 'gemini-3.8-flash', name: 'Gemini 3.8 Flash (最新主力・高速・推奨)', description: '最新世代の高性能Flashモデル。要約・アナウンスに最適' },
        { id: 'gemini-3.5-flash-lite', name: 'Gemini 3.5 Flash-Lite (超高速・低遅延)', description: '最も低遅延かつ高効率な軽量モデル' },
        { id: 'gemini-4-argon', name: 'Gemini 4 Argon (最高峰推論)', description: '高度な推論と高品質な文章生成を行うフラグシップ' },
        { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash (安定版)', description: '安定稼働実績の長いFlashモデル' },
        { id: 'gemini-2.5-flash-lite', name: 'Gemini 2.5 Flash-Lite', description: '2.5世代の軽量高効率モデル' }
      ];
    } else {
      return [
        { id: 'gpt-4o-mini', name: 'GPT-4o mini (高速・経済的・推奨)', description: '低価格で高速な万能モデル' },
        { id: 'gpt-4o', name: 'GPT-4o (フラグシップ)', description: '高性能なマルチモーダル対応フラグシップ' },
        { id: 'o3-mini', name: 'o3-mini (高速推論)', description: '最新の推論特化型モデル' },
        { id: 'o1', name: 'o1 (高度な推論)', description: '深い思考と論理的推論を行うモデル' }
      ];
    }
  }

  /**
   * Google Gemini の利用可能モデル一覧を動的取得
   * - generateContent 対応の標準 Gemini モデル (gemini-*)
   * - エージェント/PC操作/長時間研究 (antigravity, agent, computer-use, deep-research) を除外
   * - 音声・配信・画像・埋め込み (tts, live, omni, transcribe, audio, image, imagen, embedding, aqa, custom-tools) を除外
   * - 退役・古い世代 (1.5, 1.0, 2.0, 3.7) を除外
   * - 最新順 (バージョン番号降順) でソート
   */
  async fetchGeminiModels(apiKey) {
    const key = apiKey || this.getApiKey('gemini');
    if (!key) return this.getFallbackModels('gemini');

    const url = `https://generativelanguage.googleapis.com/v1beta/models?key=${encodeURIComponent(key)}`;
    const res = await fetch(url);
    if (!res.ok) {
      console.warn(`[AI] Gemini models 取得失敗 (HTTP ${res.status}), フォールバックリストを使用`);
      return this.getFallbackModels('gemini');
    }

    const data = await res.json();
    const list = data.models || [];

    // 全IDセット (プレビュー版の重複排除用)
    const allRawIds = new Set(list.map(m => (m.name || '').replace(/^models\//, '').toLowerCase()));

    const filtered = list.filter(m => {
      if (!m.supportedGenerationMethods?.includes('generateContent')) return false;

      const rawId = (m.name || '').replace(/^models\//, '').toLowerCase();
      const displayName = (m.displayName || '').toLowerCase();

      // 1. 必ず gemini- で始まるモデルのみを対象
      // (antigravity-* などの開発環境向けエージェントや deep-research-* 等の研究エージェントを完全排除)
      if (!rawId.startsWith('gemini-')) return false;

      // 2. 特殊用途・非会話モデルを除外 (PC操作、自律エージェント、ストリーミング配信、画像、音声、埋め込み、ツールベンチマーク、エッジ小型モデル)
      const excludeKeywords = [
        'antigravity',
        'agent',
        'computer-use',
        'deep-research',
        'research',
        'omni',
        'custom-tools',
        'customtools',
        'tool',
        'robot',
        'nano',
        'banana',
        'tts',
        'live',
        'transcribe',
        'audio',
        'image',
        'imagen',
        'embedding',
        'aqa'
      ];

      for (const kw of excludeKeywords) {
        if (rawId.includes(kw) || displayName.includes(kw)) {
          return false;
        }
      }

      // 3. 旧世代 (2025年以前・レガシー) を除外
      if (rawId.startsWith('gemini-1.5') || rawId.startsWith('gemini-1.0') || rawId.startsWith('gemini-2.0') || rawId.startsWith('gemini-3.7')) {
        return false;
      }

      // 4. 正式版が存在する場合の重複プレビュー版 (例: gemini-3.1-flash-lite がある場合の gemini-3.1-flash-lite-preview) を除外
      if (rawId.endsWith('-preview')) {
        const base = rawId.replace(/-preview$/, '');
        if (allRawIds.has(base)) return false;
      }

      return true;
    });

    // 最新順 (バージョン番号降順: 4 > 3.8 > 3.5 > 2.5) でソート
    const parseVersion = (id) => {
      const match = id.match(/gemini-(\d+)(?:\.(\d+))?/i);
      if (!match) return 0;
      const major = parseInt(match[1], 10) || 0;
      const minor = parseInt(match[2], 10) || 0;
      return major * 100 + minor;
    };

    filtered.sort((a, b) => {
      const idA = a.name.replace(/^models\//, '').toLowerCase();
      const idB = b.name.replace(/^models\//, '').toLowerCase();
      const vA = parseVersion(idA);
      const vB = parseVersion(idB);
      if (vB !== vA) return vB - vA;

      // 同世代内では Flash を優先
      const isFlashA = idA.includes('flash');
      const isFlashB = idB.includes('flash');
      if (isFlashA && !isFlashB) return -1;
      if (!isFlashA && isFlashB) return 1;

      return idA.localeCompare(idB);
    });

    const results = filtered.map(m => {
      const id = m.name.replace(/^models\//, '');
      let label = m.displayName || id;
      if (id === 'gemini-3.8-flash') label += ' (最新主力・推奨)';
      else if (id === 'gemini-3.5-flash-lite') label += ' (超高速・軽量)';
      else if (id === 'gemini-4-argon') label += ' (最高峰推論)';
      else if (id === 'gemini-2.5-flash') label += ' (安定版)';
      return {
        id,
        name: label,
        description: m.description || ''
      };
    });

    return results.length > 0 ? results : this.getFallbackModels('gemini');
  }

  /**
   * OpenAI の利用可能モデル一覧を動的取得
   * - チャット生成向け (gpt-, o1, o3)
   * - 音声特化 (realtime, audio, tts, whisper)、画像 (dall-e)、埋め込みを除外
   * - エージェント/PC操作/長時間研究 (agent, computer-use, deep-research, operator) を除外
   * - 最新順 (created タイムスタンプ降順) でソート
   */
  async fetchOpenAiModels(apiKey) {
    const key = apiKey || this.getApiKey('openai');
    if (!key) return this.getFallbackModels('openai');

    const url = 'https://api.openai.com/v1/models';
    const res = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${key}`
      }
    });

    if (!res.ok) {
      console.warn(`[AI] OpenAI models 取得失敗 (HTTP ${res.status}), フォールバックリストを使用`);
      return this.getFallbackModels('openai');
    }

    const data = await res.json();
    const list = data.data || [];

    const filtered = list.filter(m => {
      const id = (m.id || '').toLowerCase();
      if (!id.startsWith('gpt-') && !id.startsWith('o1') && !id.startsWith('o3') && !id.startsWith('chatgpt-')) {
        return false;
      }
      if (id.includes('realtime') || id.includes('audio') || id.includes('tts') || id.includes('whisper')) return false;
      if (id.includes('dall-e') || id.includes('embedding') || id.includes('moderation') || id.includes('vision-preview')) return false;
      if (id.includes('instruct') || id.includes('search')) return false;
      if (id.includes('agent') || id.includes('computer-use') || id.includes('deep-research') || id.includes('operator')) return false;

      return true;
    });

    // 最新順 (created タイムスタンプ降順) でソート
    filtered.sort((a, b) => (b.created || 0) - (a.created || 0));

    const results = filtered.map(m => {
      let label = m.id;
      if (m.id === 'gpt-4o-mini') label = 'GPT-4o mini (高速・経済的・推奨)';
      else if (m.id === 'gpt-4o') label = 'GPT-4o (フラグシップ)';
      else if (m.id === 'o3-mini') label = 'o3-mini (高速推論)';
      else if (m.id === 'o1') label = 'o1 (高度な推論)';
      return {
        id: m.id,
        name: label,
        created: m.created
      };
    });

    return results.length > 0 ? results : this.getFallbackModels('openai');
  }

  /**
   * キャッシュ対応の利用可能モデル一覧取得
   * - 選択中のモデルが終了（退役）しているかの検証と自己修復
   */
  async getAvailableModels(provider = 'gemini', options = {}) {
    const now = Date.now();
    const cache = this.modelCache[provider];
    const key = options.apiKey || this.getApiKey(provider);
    const aiConfig = settingsManager.get().ai || {};
    const defaultModel = provider === 'openai' ? this.defaultOpenAiModel : this.defaultGeminiModel;
    const currentModel = provider === 'openai' ? (aiConfig.openaiModel || defaultModel) : (aiConfig.geminiModel || defaultModel);

    let models = [];
    let isLive = false;
    let fetchError = null;

    if (!options.forceRefresh && cache?.models && (now - cache.timestamp < 10 * 60 * 1000)) {
      models = cache.models;
      isLive = true;
    } else if (!key) {
      models = this.getFallbackModels(provider);
      isLive = false;
    } else {
      try {
        if (provider === 'openai') {
          models = await this.fetchOpenAiModels(key);
        } else {
          models = await this.fetchGeminiModels(key);
        }
        this.modelCache[provider] = { models, timestamp: now };
        isLive = true;
      } catch (err) {
        console.warn(`[AI] ${provider} モデル動的取得エラー:`, err.message);
        models = this.getFallbackModels(provider);
        isLive = false;
        fetchError = err.message;
      }
    }

    // 選択されていたモデルが提供終了しているか検証
    const retiredList = provider === 'gemini'
      ? ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.5-flash-8b', 'gemini-1.0-pro', 'gemini-pro', 'gemini-3.7-flash']
      : ['gpt-3.5-turbo-instruct', 'gpt-4-0314', 'gpt-4-0613'];

    const isKnownRetired = retiredList.includes(currentModel);
    const isInModelList = models.some(m => m.id === currentModel);
    const isCurrentModelEnded = isKnownRetired || (!isInModelList && models.length > 0);

    let activeModel = currentModel;
    let notice = null;

    if (isCurrentModelEnded) {
      console.warn(`[AI] 現在設定されているモデル "${currentModel}" は提供終了または一覧に見つかりません。最新推奨モデル "${defaultModel}" に自動更新します`);
      if (provider === 'gemini') {
        settingsManager.update({ ai: { geminiModel: defaultModel } });
      } else {
        settingsManager.update({ ai: { openaiModel: defaultModel } });
      }
      activeModel = defaultModel;
      notice = `以前設定されていたモデル「${currentModel}」は提供終了したため、最新の「${defaultModel}」に自動更新されました。`;
    }

    return {
      provider,
      models,
      isLive,
      currentModel: activeModel,
      previousModel: isCurrentModelEnded ? currentModel : null,
      isCurrentModelEnded,
      defaultModel,
      notice,
      error: fetchError
    };
  }

  /**
   * UI表示用のステータス情報取得 (安全のため生キーは返さない)
   */
  getStatus() {
    const aiConfig = settingsManager.get().ai || {};
    const dndConfig = settingsManager.get().dnd || {};

    const geminiKey = this.getApiKey('gemini');
    const openaiKey = this.getApiKey('openai');

    let geminiSource = 'none';
    if (aiConfig.geminiApiKey) geminiSource = 'settings';
    else if (process.env.GEMINI_API_KEY || process.env.AI_API_KEY) geminiSource = 'env';

    let openAiSource = 'none';
    if (aiConfig.openaiApiKey) openAiSource = 'settings';
    else if (process.env.OPENAI_API_KEY) openAiSource = 'env';

    return {
      enabled: aiConfig.enabled !== false,
      provider: aiConfig.provider || 'gemini',
      gemini: {
        hasKey: !!geminiKey,
        keyMasked: this.maskKey(geminiKey),
        source: geminiSource,
        model: aiConfig.geminiModel || this.defaultGeminiModel
      },
      openai: {
        hasKey: !!openaiKey,
        keyMasked: this.maskKey(openaiKey),
        source: openAiSource,
        model: aiConfig.openaiModel || this.defaultOpenAiModel
      },
      dndSummary: {
        enabled: dndConfig.aiSummaryEnabled !== false && aiConfig.summarizeDndQueue !== false,
        threshold: parseInt(dndConfig.aiSummaryThreshold || aiConfig.summaryThreshold || '2', 10),
        customPrompt: dndConfig.aiSummaryCustomPrompt || aiConfig.customPrompt || ''
      },
      calendarSummary: {
        enabled: aiConfig.summarizeDailyCalendar !== false,
        promptHint: aiConfig.dailyCalendarPrompt || ''
      }
    };
  }

  /**
   * Google Gemini API 呼び出し
   * ※指定モデルが提供終了 (404/not found) の場合、最新デフォルトモデルへ自動フォールバック＆設定自己修復
   */
  async callGemini(prompt, options = {}) {
    const apiKey = options.apiKey || this.getApiKey('gemini');
    if (!apiKey) {
      throw new Error('Google Gemini API Key が設定されていません。拡張・システム設定または .my.env に設定してください。');
    }

    const aiConfig = settingsManager.get().ai || {};
    let model = options.model || aiConfig.geminiModel || this.defaultGeminiModel;

    // 既知の退役モデルが指定されている場合は即座に最新推奨モデルに切り替え
    const retired = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.5-flash-8b', 'gemini-1.0-pro', 'gemini-pro', 'gemini-3.7-flash'];
    if (retired.includes(model)) {
      console.warn(`[AI] 指定されたモデル "${model}" は提供終了しています。最新の "${this.defaultGeminiModel}" に自動切り替えます`);
      model = this.defaultGeminiModel;
      settingsManager.update({ ai: { geminiModel: this.defaultGeminiModel } });
    }

    const makeRequest = async (targetModel) => {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(targetModel)}:generateContent?key=${encodeURIComponent(apiKey)}`;
      const payload = {
        contents: [
          {
            parts: [
              { text: prompt }
            ]
          }
        ],
        generationConfig: {
          temperature: options.temperature ?? 0.3,
          maxOutputTokens: options.maxTokens ?? 300
        }
      };

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        let errorMsg = `HTTP ${res.status} ${res.statusText}`;
        let retryAfter = null;
        const retryHeader = res.headers.get('retry-after');
        if (retryHeader) {
          const parsed = parseFloat(retryHeader);
          if (!isNaN(parsed)) retryAfter = parsed;
        }

        try {
          const errJson = await res.json();
          if (errJson.error && errJson.error.message) {
            errorMsg = errJson.error.message;
            const match = errorMsg.match(/retry after\s+([0-9.]+)\s*s/i);
            if (match && !retryAfter) {
              retryAfter = parseFloat(match[1]);
            }
          }
        } catch (_) {}
        const err = new Error(errorMsg);
        err.status = res.status;
        err.isRateLimit = (res.status === 429) || errorMsg.includes('RESOURCE_EXHAUSTED') || errorMsg.toLowerCase().includes('quota');
        err.retryAfter = retryAfter;
        throw err;
      }

      return await res.json();
    };

    let data;
    try {
      data = await makeRequest(model);
    } catch (err) {
      // 404 Not Found やモデル終了エラーの場合、最新モデルへ自動フォールバック！
      if (err.status === 404 || err.message.toLowerCase().includes('not found') || err.message.toLowerCase().includes('deprecated')) {
        console.warn(`[AI] モデル "${model}" の呼び出しに失敗しました (${err.message})。最新の推奨モデル "${this.defaultGeminiModel}" に自動フォールバックします`);
        try {
          data = await makeRequest(this.defaultGeminiModel);
          // 設定を自動修復
          settingsManager.update({ ai: { geminiModel: this.defaultGeminiModel } });
        } catch (retryErr) {
          throw new Error(`Gemini API エラー (フォールバック後も失敗): ${retryErr.message}`);
        }
      } else {
        throw new Error(`Gemini API エラー: ${err.message}`);
      }
    }

    const candidate = data.candidates?.[0];
    const textPart = candidate?.content?.parts?.[0]?.text;

    if (!textPart) {
      throw new Error('Gemini API から応答テキストを取得できませんでした');
    }

    return textPart.trim();
  }

  /**
   * OpenAI API 呼び出し
   * ※指定モデル終了時の自動フォールバック対応
   */
  async callOpenAi(prompt, options = {}) {
    const apiKey = options.apiKey || this.getApiKey('openai');
    if (!apiKey) {
      throw new Error('OpenAI API Key が設定されていません。拡張・システム設定または .my.env に設定してください。');
    }

    const aiConfig = settingsManager.get().ai || {};
    let model = options.model || aiConfig.openaiModel || this.defaultOpenAiModel;

    const makeRequest = async (targetModel) => {
      const url = 'https://api.openai.com/v1/chat/completions';
      const payload = {
        model: targetModel,
        messages: [
          {
            role: 'system',
            content: 'あなたは家庭用スマートスピーカーのAIアシスタントです。音声合成で読み上げやすいよう、マークダウンや記号を使わず簡潔な日本語の話し言葉で返答してください。'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: options.temperature ?? 0.3,
        max_tokens: options.maxTokens ?? 300
      };

      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        let errorMsg = `HTTP ${res.status} ${res.statusText}`;
        let retryAfter = null;
        const retryHeader = res.headers.get('retry-after');
        if (retryHeader) {
          const parsed = parseFloat(retryHeader);
          if (!isNaN(parsed)) retryAfter = parsed;
        }

        try {
          const errJson = await res.json();
          if (errJson.error && errJson.error.message) {
            errorMsg = errJson.error.message;
            const match = errorMsg.match(/retry after\s+([0-9.]+)\s*s/i);
            if (match && !retryAfter) {
              retryAfter = parseFloat(match[1]);
            }
          }
        } catch (_) {}
        const err = new Error(errorMsg);
        err.status = res.status;
        err.isRateLimit = (res.status === 429) || errorMsg.toLowerCase().includes('rate_limit') || errorMsg.toLowerCase().includes('quota');
        err.retryAfter = retryAfter;
        throw err;
      }

      return await res.json();
    };

    let data;
    try {
      data = await makeRequest(model);
    } catch (err) {
      if (err.status === 404 || err.message.toLowerCase().includes('model_not_found') || err.message.toLowerCase().includes('does not exist')) {
        console.warn(`[AI] OpenAIモデル "${model}" が利用不可のため、最新の "${this.defaultOpenAiModel}" に自動フォールバックします`);
        try {
          data = await makeRequest(this.defaultOpenAiModel);
          settingsManager.update({ ai: { openaiModel: this.defaultOpenAiModel } });
        } catch (retryErr) {
          throw new Error(`OpenAI API エラー (フォールバック後も失敗): ${retryErr.message}`);
        }
      } else {
        throw new Error(`OpenAI API エラー: ${err.message}`);
      }
    }

    const text = data.choices?.[0]?.message?.content;
    if (!text) {
      throw new Error('OpenAI API から応答テキストを取得できませんでした');
    }

    return text.trim();
  }

  /**
   * 設定されたプロバイダ（または指定プロバイダ）で生成実行
   * ※レート制限や障害発生時の Retry-After 制御および自動フェイルオーバー対応
   */
  async generateText(prompt, options = {}) {
    const aiConfig = settingsManager.get().ai || {};
    const primaryProvider = options.provider || aiConfig.provider || 'gemini';
    const secondaryProvider = primaryProvider === 'gemini' ? 'openai' : 'gemini';

    const hasSecondary = !options.provider && !!this.getApiKey(secondaryProvider);

    try {
      if (primaryProvider === 'openai') {
        return await this.callOpenAi(prompt, options);
      }
      return await this.callGemini(prompt, options);
    } catch (primaryErr) {
      // 1. エラーまたはレート制限時、セカンダリ（もう一方のプロバイダ）が設定されている場合は即時フェイルオーバー
      // （スマートスピーカーの応答遅延を最小限にするため、Retry-After で数十秒待機せず即座に予備プロバイダへ切り替えます）
      if (hasSecondary) {
        const retryInfo = primaryErr.retryAfter ? ` (Retry-After: ${primaryErr.retryAfter}秒)` : '';
        console.warn(`[AI] メインの ${primaryProvider} でエラーまたは制限が発生しました (${primaryErr.message}${retryInfo})。待機遅延を避けるため、予備プロバイダ (${secondaryProvider}) へ即時フェイルオーバーします`);
        try {
          if (secondaryProvider === 'openai') {
            return await this.callOpenAi(prompt, options);
          } else {
            return await this.callGemini(prompt, options);
          }
        } catch (secondaryErr) {
          throw new Error(`AI生成エラー (両プロバイダ失敗): [${primaryProvider}] ${primaryErr.message} / [${secondaryProvider}] ${secondaryErr.message}`);
        }
      }

      // 2. セカンダリがない場合で、かつ Retry-After が短時間（3秒以下）の場合は1回だけ待機して再試行
      if (primaryErr.isRateLimit && primaryErr.retryAfter && primaryErr.retryAfter <= 3 && !options.isRetry) {
        console.warn(`[AI] ${primaryProvider} がレート制限中ですが、Retry-After が短いため ${primaryErr.retryAfter}秒 待機して再試行します...`);
        await new Promise(r => setTimeout(r, Math.ceil(primaryErr.retryAfter * 1000) + 200));
        return await this.generateText(prompt, { ...options, isRetry: true });
      }

      // 3. Retry-After が長い場合 (4秒以上) やリトライ後も失敗した場合:
      // スピーカー発声を数十秒も停止・待たせることはできないため、エラーをスローして通常の標準読み上げ（DND個別読み上げ / 定型予定アナウンス）へ安全にフォールバックさせる
      throw primaryErr;
    }
  }

  /**
   * 接続テスト (API Key が正しく通信できるか検証)
   */
  async testConnection(params = {}) {
    const provider = params.provider || 'gemini';
    const apiKey = params.apiKey || this.getApiKey(provider);
    const model = params.model;

    if (!apiKey) {
      return {
        success: false,
        error: `${provider === 'gemini' ? 'Google Gemini' : 'OpenAI'} API Key が入力されていません`
      };
    }

    const testPrompt = 'こんにちは！接続テストです。日本語で「API接続に成功しました」とだけ簡潔に返答してください。';

    try {
      let reply = '';
      if (provider === 'openai') {
        reply = await this.callOpenAi(testPrompt, { apiKey, model, maxTokens: 40 });
      } else {
        reply = await this.callGemini(testPrompt, { apiKey, model, maxTokens: 40 });
      }

      reply = reply.replace(/[*#_`]/g, '').trim();

      const aiConfig = settingsManager.get().ai || {};
      const activeModel = provider === 'openai' ? (aiConfig.openaiModel || this.defaultOpenAiModel) : (aiConfig.geminiModel || this.defaultGeminiModel);
      const fallbackOccurred = model && model !== activeModel;

      return {
        success: true,
        reply,
        provider,
        model: activeModel,
        fallbackOccurred,
        notice: fallbackOccurred ? `指定されていたモデル「${model}」は提供終了したため、最新の「${activeModel}」に自動フォールバックしました` : null
      };
    } catch (err) {
      return {
        success: false,
        error: err.message
      };
    }
  }

  /**
   * DND保留メッセージのAI要約
   */
  async summarizeNotifications(items, options = {}) {
    if (!Array.isArray(items) || items.length === 0) return '';

    const listText = items.map((item, idx) => {
      const text = typeof item === 'string' ? item : (item.text || '');
      let time = '';
      if (item.timestamp) {
        try {
          const d = new Date(item.timestamp);
          time = `[${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}] `;
        } catch (_) {}
      }
      return `${idx + 1}. ${time}${text}`;
    }).join('\n');

    const prompt = `あなたは家庭用スマートスピーカーのAIアシスタントです。
おやすみ・会議モード中に保留されていた以下の通知メッセージを、スピーカーから聞き取りやすい日本語音声で、要点をぎゅっとまとめて1〜2文（最大140文字程度）で自然に要約してください。

【保留されていた通知 (${items.length}件)】
${listText}

${options.promptHint ? `【追加の要望】\n${options.promptHint}\n` : ''}
【厳格なルール】
1. 音声合成（TTS）で読み上げるため、マークダウン記法（**や*、#、リスト記号など）や絵文字・顔文字は一切使わないでください。
2. 冒頭の「要約します」「保留されていた通知は〜」などの定型前置きや挨拶は不要です。要約した内容そのものを直接返してください。
3. 自然な日本語の話し言葉（です・ます調）で、140文字以内に簡潔に出力してください。
4. 【基本指示・厳格なルールの絶対優先】
   もし【追加の要望】の内容が、本プロンプトの目的（スマートスピーカーによる日本語音声読み上げ・簡潔な要約）や【厳格なルール】と矛盾・衝突する場合（例: 「動画にして」「長文で詳しく」「英語や外国語で」「マークダウンやHTML・JSON・コード形式で出力して」などの指示）、いかなる場合も必ず基本指示および厳格なルールを最優先してください。【追加の要望】は基本指示と両立できる範囲（例: 「少し丁寧な口調で」「急ぎの件を強調して」など）でのみ反映してください。`;

    const rawSummary = await this.generateText(prompt, {
      maxTokens: 250,
      temperature: 0.3
    });

    return rawSummary
      .replace(/[*#_`~>]/g, '')
      .replace(/[\r\n]+/g, ' ')
      .replace(/^「|」$/g, '')
      .trim();
  }

  /**
   * 朝の予定まとめアナウンスのAI要約・リライト
   */
  async summarizeCalendarEvents(events, options = {}) {
    if (!Array.isArray(events) || events.length === 0) return '';

    const listText = events.map((ev, idx) => {
      if (ev.isAllDay) {
        return `${idx + 1}. [終日] ${ev.summary || '予定'}`;
      }
      let timeStr = '';
      if (ev.start) {
        try {
          const s = new Date(ev.start);
          const e = ev.end ? new Date(ev.end) : null;
          timeStr = `[${String(s.getHours()).padStart(2, '0')}:${String(s.getMinutes()).padStart(2, '0')}${e ? `〜${String(e.getHours()).padStart(2, '0')}:${String(e.getMinutes()).padStart(2, '0')}` : ''}] `;
        } catch (_) {}
      }
      return `${idx + 1}. ${timeStr}${ev.summary || '予定'}`;
    }).join('\n');

    const calLabel = options.calName ? `${options.calName}の` : '';
    const weatherSection = options.weatherInfo ? `【本日の天気予報】
地域: ${options.weatherInfo.areaName || ''}
天気: ${options.weatherInfo.weather || ''}
予想気温: ${options.weatherInfo.tempMax ? `最高${options.weatherInfo.tempMax}` : ''} ${options.weatherInfo.tempMin ? `最低${options.weatherInfo.tempMin}` : ''}
降水確率: ${options.weatherInfo.pop || '0%'}
${options.weatherInfo.advice ? `アドバイス: ${options.weatherInfo.advice}` : ''}
` : '';

    const prompt = `あなたは家庭用スマートスピーカーのAIアシスタントです。
ユーザーの本日のカレンダー予定リスト${options.weatherInfo ? 'および天気予報' : ''}をもとに、朝のスマートスピーカーから流れる爽やかで聞き取りやすい「本日の予定まとめアナウンス」を作成してください。

${weatherSection}【${calLabel}本日の予定 (${events.length}件)】
${listText}

${options.promptHint ? `【追加の要望・プロンプト指示】\n${options.promptHint}\n` : ''}
【厳格なルール】
1. 朝の爽やかな挨拶（「おはようございます！」など）から開始し、${options.weatherInfo ? 'まず本日の天気・気温（必要に応じて傘や服装のアドバイス）を1文で簡潔に伝え、続けて' : ''}本日の予定の件数と主な内容を分かりやすく整理してください。
2. 最後に前向きな応援の言葉（「今日も充実した一日にしましょう！」など）で締めくくってください。
3. 音声合成（TTS）で読み上げるため、マークダウン記法（**や*、#、箇条書き記号など）や絵文字・顔文字は一切使わないでください。
4. 自然な日本語の話し言葉（です・ます調）で、140〜190文字程度にまとめてください。
5. 【基本指示・厳格なルールの絶対優先】
   もし【追加の要望・プロンプト指示】の内容が、本プロンプトの目的（朝のスマートスピーカーによる日本語音声予定アナウンス）や【厳格なルール】と矛盾・衝突する場合（例: 「動画にして」「長文で詳しく」「英語や外国語で」「マークダウンやHTML・JSON・コード形式で出力して」などの指示）、いかなる場合も必ず基本指示および厳格なルールを最優先してください。【追加の要望】は基本指示と両立できる範囲（例: 「語尾を明るく」「移動時間を意識させて」など）でのみ反映してください。`;

    const rawSummary = await this.generateText(prompt, {
      maxTokens: 250,
      temperature: 0.4
    });

    return rawSummary
      .replace(/[*#_`~>]/g, '')
      .replace(/[\r\n]+/g, ' ')
      .replace(/^「|」$/g, '')
      .trim();
  }
}

module.exports = new AiManager();
