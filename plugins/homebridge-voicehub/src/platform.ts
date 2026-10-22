import {
  API,
  DynamicPlatformPlugin,
  Logger,
  PlatformAccessory,
  PlatformConfig,
  Service,
  Characteristic,
} from 'homebridge';

import { PLATFORM_NAME, PLUGIN_NAME } from './settings';
import { VoiceHubClient, VoiceHubDevice } from './voicehub-client';
import { DndSwitchAccessory } from './accessories/dnd-switch';
import { PresetSwitchAccessory, PresetConfig } from './accessories/preset-switch';
import { SpeakerAccessory } from './accessories/speaker';

export interface VoiceHubPlatformConfig extends PlatformConfig {
  host?: string;
  webhookToken?: string;
  enableDndSwitch?: boolean;
  autoDiscoverSpeakers?: boolean;
  discoverGoogleHome?: boolean;
  discoverAlexa?: boolean;
  discoverHomepod?: boolean;
  discoverOnvif?: boolean;
  discoverDlna?: boolean;
  volumeAsLightbulb?: boolean;
  pollInterval?: number;
  presets?: PresetConfig[];
}

export class VoiceHubPlatform implements DynamicPlatformPlugin {
  public readonly Service: typeof Service;
  public readonly Characteristic: typeof Characteristic;

  // キャッシュアクセサリ一覧
  public readonly accessories: PlatformAccessory[] = [];

  // API クライアント
  public readonly client: VoiceHubClient;
  public readonly config: VoiceHubPlatformConfig;

  private dndAccessoryInstance?: DndSwitchAccessory;
  private pollTimer?: NodeJS.Timeout;

  constructor(
    public readonly log: Logger,
    config: PlatformConfig,
    public readonly api: API,
  ) {
    this.Service = this.api.hap.Service;
    this.Characteristic = this.api.hap.Characteristic;
    this.config = config as VoiceHubPlatformConfig;

    const host = this.config.host || 'http://127.0.0.1:8080';
    const token = this.config.webhookToken || undefined;
    this.client = new VoiceHubClient(host, token);

    this.log.info(`[VoiceHubPlatform] Initialized / 初期化完了 (Host: ${host}, Token: ${token ? 'Configured / 設定あり' : 'None / なし'})`);

    // Homebridge 起動完了イベントでデバイス検出を実行
    this.api.on('didFinishLaunching', () => {
      this.log.info('[VoiceHubPlatform] didFinishLaunching: Starting device discovery & sync / デバイス検出と同期を開始します');
      this.discoverDevices();
      this.startPolling();
    });
  }

  /**
   * Homebridge キャッシュからの復元ハンドラ
   */
  configureAccessory(accessory: PlatformAccessory) {
    this.log.info(`[VoiceHubPlatform] Restoring cached accessory / キャッシュアクセサリ復元: ${accessory.displayName}`);
    this.accessories.push(accessory);
  }

  /**
   * デバイスのカテゴリが config で有効化されているかを判定
   */
  public isDeviceCategoryEnabled(device: VoiceHubDevice): boolean {
    const dtype = (device.type || '').toLowerCase().trim();
    const id = (device.id || '').toLowerCase().trim();
    const ip = (device.ip || '').toLowerCase().trim();
    const model = (device.model || '').toLowerCase().trim();

    // 1. Alexa
    if (dtype === 'alexa' || id.startsWith('alexa_') || ip.startsWith('alexa:') || model.includes('echo') || model.includes('alexa')) {
      return this.config.discoverAlexa !== false;
    }

    // 2. HomePod
    if (dtype === 'homepod' || id.startsWith('homepod_') || ip.startsWith('homepod:') || model.includes('homepod')) {
      return this.config.discoverHomepod !== false;
    }

    // 3. ONVIF / Tapo
    if (dtype === 'onvif' || dtype === 'tapo' || id.startsWith('onvif_') || id.startsWith('tapo_') || ip.startsWith('onvif:') || ip.startsWith('tapo:')) {
      return this.config.discoverOnvif !== false;
    }

    // 4. DLNA
    if (dtype === 'dlna' || id.startsWith('dlna_') || ip.startsWith('dlna:')) {
      return this.config.discoverDlna !== false;
    }

    // 5. Google Home / Google Cast
    if (dtype === 'google' || dtype === 'cast' || id.startsWith('dev_') || id.startsWith('group_') || model.includes('google') || model.includes('cast')) {
      return this.config.discoverGoogleHome !== false;
    }

    // その他未分類スピーカーは Google Home 設定に連動 (デフォルト許可)
    return this.config.discoverGoogleHome !== false;
  }

  /**
   * VoiceHub からデバイス・設定を取得して HomeKit アクセサリと同期
   */
  async discoverDevices() {
    const activeUUIDs = new Set<string>();

    // 1. DND（おやすみ・会議モード）スイッチの登録
    if (this.config.enableDndSwitch !== false) {
      const dndUuid = this.api.hap.uuid.generate('voicehub-dnd-switch');
      activeUUIDs.add(dndUuid);

      const existingAcc = this.accessories.find(a => a.UUID === dndUuid);
      if (existingAcc) {
        this.log.info(`[VoiceHubPlatform] Reconfiguring existing DND switch / 既存の DND スイッチを再構成: ${existingAcc.displayName}`);
        this.dndAccessoryInstance = new DndSwitchAccessory(this, existingAcc);
      } else {
        this.log.info('[VoiceHubPlatform] Registering new DND switch / 新規 DND スイッチを登録します');
        const accessory = new this.api.platformAccessory('DND Mode / 会議・おやすみモード', dndUuid);
        this.dndAccessoryInstance = new DndSwitchAccessory(this, accessory);
        this.api.registerPlatformAccessories(PLUGIN_NAME, PLATFORM_NAME, [accessory]);
        this.accessories.push(accessory);
      }
    }

    // 2. プリセット発話スイッチの登録
    const presets = Array.isArray(this.config.presets)
      ? this.config.presets
      : [
          { name: 'Dinner / ご飯できたよ', text: 'ご飯ができました。リビングに集まってください。 / Dinner is ready. Please come to the dining room.', target: 'ALL', volume: 70 },
          { name: 'Bath / お風呂が沸いたよ', text: 'お風呂が沸き上がりました。 / The bath is ready.', target: 'ALL', volume: 60 }
        ];

    for (const preset of presets) {
      if (!preset.name || !preset.text) continue;
      const presetUuid = this.api.hap.uuid.generate(`voicehub-preset-${preset.name}`);
      activeUUIDs.add(presetUuid);

      const existingAcc = this.accessories.find(a => a.UUID === presetUuid);
      if (existingAcc) {
        this.log.info(`[VoiceHubPlatform] Reconfiguring preset switch / プリセットスイッチ再構成: ${preset.name}`);
        new PresetSwitchAccessory(this, existingAcc, preset);
      } else {
        this.log.info(`[VoiceHubPlatform] Registering new preset switch / 新規プリセットスイッチを登録: ${preset.name}`);
        const accessory = new this.api.platformAccessory(preset.name, presetUuid);
        new PresetSwitchAccessory(this, accessory, preset);
        this.api.registerPlatformAccessories(PLUGIN_NAME, PLATFORM_NAME, [accessory]);
        this.accessories.push(accessory);
      }
    }

    // 3. スピーカーの自動検出とアクセサリ登録
    if (this.config.autoDiscoverSpeakers !== false) {
      try {
        const devices = await this.client.getDevices();
        this.log.info(`[VoiceHubPlatform] Discovered ${devices.length} speaker(s) from VoiceHub / VoiceHub から ${devices.length} 台のスピーカー情報を取得しました`);

        for (const device of devices) {
          // カテゴリ判定による登録フィルタリング
          if (!this.isDeviceCategoryEnabled(device)) {
            this.log.info(`[VoiceHubPlatform] Speaker registration skipped (category disabled) / スピーカー登録スキップ (カテゴリ無効): ${device.name} (${device.type || 'unknown'})`);
            continue;
          }

          // IP / ID を元に UUID を生成
          const deviceUuid = this.api.hap.uuid.generate(`voicehub-speaker-${device.id}`);
          activeUUIDs.add(deviceUuid);

          const existingAcc = this.accessories.find(a => a.UUID === deviceUuid);
          if (existingAcc) {
            this.log.debug(`[VoiceHubPlatform] Reconfiguring existing speaker / 既存スピーカーを再構成: ${device.name}`);
            new SpeakerAccessory(this, existingAcc, device);
          } else {
            this.log.info(`[VoiceHubPlatform] Registering new speaker / 新規スピーカーを登録: ${device.name} (${device.type})`);
            const accessory = new this.api.platformAccessory(device.name, deviceUuid);
            new SpeakerAccessory(this, accessory, device);
            this.api.registerPlatformAccessories(PLUGIN_NAME, PLATFORM_NAME, [accessory]);
            this.accessories.push(accessory);
          }
        }
      } catch (err: any) {
        this.log.error(`[VoiceHubPlatform] Speaker auto-discovery failed / スピーカー自動検出に失敗しました: ${err.message || err}`);
      }
    }

    // 4. 不要になった古いキャッシュアクセサリの削除クリーンアップ (カテゴリ無効化時の即時解除含む)
    const obsoleteAccessories = this.accessories.filter(a => !activeUUIDs.has(a.UUID));
    if (obsoleteAccessories.length > 0) {
      this.log.info(`[VoiceHubPlatform] Unregistering ${obsoleteAccessories.length} obsolete accessory(ies) / 不要になった ${obsoleteAccessories.length} 個のアクセサリを登録解除します`);
      this.api.unregisterPlatformAccessories(PLUGIN_NAME, PLATFORM_NAME, obsoleteAccessories);
      for (const obs of obsoleteAccessories) {
        const idx = this.accessories.indexOf(obs);
        if (idx >= 0) this.accessories.splice(idx, 1);
      }
    }
  }

  /**
   * DND 状態の定期ポーリング同期
   */
  private startPolling() {
    const intervalSec = Math.max(10, this.config.pollInterval || 30);
    this.pollTimer = setInterval(async () => {
      if (!this.dndAccessoryInstance) return;
      try {
        const status = await this.client.getDndStatus();
        this.dndAccessoryInstance.updateState(status.isActive);
      } catch {
        // バックグラウンドポーリングエラーはログレベルdebug
      }
    }, intervalSec * 1000);
  }
}
