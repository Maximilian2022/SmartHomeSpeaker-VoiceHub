import { Service, PlatformAccessory, CharacteristicValue } from 'homebridge';
import { VoiceHubPlatform } from '../platform';

export interface PresetConfig {
  name: string;
  text: string;
  target?: string;
  volume?: number;
}

/**
 * プリセット発話ステートレススイッチアクセサリ
 * 押下すると発話を実行し、1秒後に自動でOFFに戻るプッシュボタン仕様
 */
export class PresetSwitchAccessory {
  private service: Service;
  private isProcessing: boolean = false;

  constructor(
    private readonly platform: VoiceHubPlatform,
    private readonly accessory: PlatformAccessory,
    private readonly preset: PresetConfig,
  ) {
    // アクセサリ情報設定
    this.accessory.getService(this.platform.Service.AccessoryInformation)!
      .setCharacteristic(this.platform.Characteristic.Manufacturer, 'VoiceHub')
      .setCharacteristic(this.platform.Characteristic.Model, 'Preset Speech Switch')
      .setCharacteristic(this.platform.Characteristic.SerialNumber, `VH-PRESET-${accessory.UUID.slice(0, 8)}`);

    // スイッチサービス
    this.service = this.accessory.getService(this.platform.Service.Switch)
      || this.accessory.addService(this.platform.Service.Switch);

    this.service.setCharacteristic(this.platform.Characteristic.Name, this.preset.name);

    // ハンドラ
    this.service.getCharacteristic(this.platform.Characteristic.On)
      .onSet(this.setOn.bind(this))
      .onGet(this.getOn.bind(this));
  }

  async setOn(value: CharacteristicValue) {
    const targetState = Boolean(value);

    // OFF へのリセット時は何もしない
    if (!targetState) {
      return;
    }

    if (this.isProcessing) {
      this.platform.log.warn(`[Preset:${this.preset.name}] 直前の発話処理中のためスキップします`);
      return;
    }

    this.isProcessing = true;
    this.platform.log.info(`[Preset:${this.preset.name}] 発話開始: "${this.preset.text}" (対象: ${this.preset.target || 'ALL'})`);

    try {
      const res = await this.platform.client.say(
        this.preset.text,
        this.preset.target,
        this.preset.volume,
      );

      this.platform.log.info(`[Preset:${this.preset.name}] 発話成功: ${res.message || '送信完了'}`);
    } catch (err: any) {
      this.platform.log.error(`[Preset:${this.preset.name}] 発話エラー: ${err.message || err}`);
    } finally {
      // 1秒後にスイッチを自動で OFF に戻す（プッシュボタン動作）
      setTimeout(() => {
        this.service.updateCharacteristic(this.platform.Characteristic.On, false);
        this.isProcessing = false;
      }, 1000);
    }
  }

  async getOn(): Promise<CharacteristicValue> {
    // 常に OFF (プッシュボタン)
    return false;
  }
}
