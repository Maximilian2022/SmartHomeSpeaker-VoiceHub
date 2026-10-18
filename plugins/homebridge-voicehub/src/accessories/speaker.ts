import { Service, PlatformAccessory, CharacteristicValue } from 'homebridge';
import { VoiceHubPlatform } from '../platform';
import { VoiceHubDevice } from '../voicehub-client';

/**
 * 個別スピーカーアクセサリ
 * HomeKit 上で音量スライダー操作（Lightbulb の Brightness または Speaker）を可能にする
 */
export class SpeakerAccessory {
  private service: Service;
  private currentVolume: number = 60;
  private isMuted: boolean = false;

  constructor(
    private readonly platform: VoiceHubPlatform,
    private readonly accessory: PlatformAccessory,
    private readonly device: VoiceHubDevice,
  ) {
    // アクセサリ情報設定
    this.accessory.getService(this.platform.Service.AccessoryInformation)!
      .setCharacteristic(this.platform.Characteristic.Manufacturer, 'VoiceHub')
      .setCharacteristic(this.platform.Characteristic.Model, device.model || device.type || 'Smart Speaker')
      .setCharacteristic(this.platform.Characteristic.SerialNumber, device.id);

    const asLightbulb = this.platform.config.volumeAsLightbulb !== false;

    if (asLightbulb) {
      // HomeKit ホームアプリのタイルで直感的に音量パーセントを操作できるよう Lightbulb サービスを使用
      this.service = this.accessory.getService(this.platform.Service.Lightbulb)
        || this.accessory.addService(this.platform.Service.Lightbulb);

      this.service.setCharacteristic(this.platform.Characteristic.Name, device.name);

      this.service.getCharacteristic(this.platform.Characteristic.On)
        .onSet(this.setOn.bind(this))
        .onGet(this.getOn.bind(this));

      this.service.getCharacteristic(this.platform.Characteristic.Brightness)
        .onSet(this.setBrightness.bind(this))
        .onGet(this.getBrightness.bind(this));
    } else {
      // 標準 Speaker サービス
      this.service = this.accessory.getService(this.platform.Service.Speaker)
        || this.accessory.addService(this.platform.Service.Speaker);

      this.service.setCharacteristic(this.platform.Characteristic.Name, device.name);

      this.service.getCharacteristic(this.platform.Characteristic.Mute)
        .onSet(this.setMute.bind(this))
        .onGet(this.getMute.bind(this));

      this.service.getCharacteristic(this.platform.Characteristic.Volume)
        .onSet(this.setVolume.bind(this))
        .onGet(this.getVolume.bind(this));
    }
  }

  // --- Lightbulb 方式 (音量スライダー) ---
  async setOn(value: CharacteristicValue) {
    this.isMuted = !Boolean(value);
    this.platform.log.debug(`[Speaker:${this.device.name}] 電源/ミュート切り替え: ${!this.isMuted}`);
  }

  async getOn(): Promise<CharacteristicValue> {
    return !this.isMuted;
  }

  async setBrightness(value: CharacteristicValue) {
    const vol = Number(value);
    this.currentVolume = Math.min(100, Math.max(0, vol));
    this.platform.log.info(`[Speaker:${this.device.name}] 音量変更: ${this.currentVolume}%`);
  }

  async getBrightness(): Promise<CharacteristicValue> {
    return this.currentVolume;
  }

  // --- Speaker 方式 ---
  async setMute(value: CharacteristicValue) {
    this.isMuted = Boolean(value);
    this.platform.log.debug(`[Speaker:${this.device.name}] ミュート: ${this.isMuted}`);
  }

  async getMute(): Promise<CharacteristicValue> {
    return this.isMuted;
  }

  async setVolume(value: CharacteristicValue) {
    this.currentVolume = Number(value);
    this.platform.log.info(`[Speaker:${this.device.name}] 音量変更: ${this.currentVolume}%`);
  }

  async getVolume(): Promise<CharacteristicValue> {
    return this.currentVolume;
  }
}
