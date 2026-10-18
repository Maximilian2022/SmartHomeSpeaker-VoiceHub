import { Service, PlatformAccessory, CharacteristicValue } from 'homebridge';
import { VoiceHubPlatform } from '../platform';

/**
 * DND（おやすみ・会議モード）スイッチアクセサリ
 */
export class DndSwitchAccessory {
  private service: Service;
  private isDndActive: boolean = false;

  constructor(
    private readonly platform: VoiceHubPlatform,
    private readonly accessory: PlatformAccessory,
  ) {
    // アクセサリ情報設定
    this.accessory.getService(this.platform.Service.AccessoryInformation)!
      .setCharacteristic(this.platform.Characteristic.Manufacturer, 'VoiceHub')
      .setCharacteristic(this.platform.Characteristic.Model, 'DND Switch')
      .setCharacteristic(this.platform.Characteristic.SerialNumber, 'VH-DND-01');

    // スイッチサービス取得または新規登録
    this.service = this.accessory.getService(this.platform.Service.Switch)
      || this.accessory.addService(this.platform.Service.Switch);

    this.service.setCharacteristic(this.platform.Characteristic.Name, accessory.displayName || '会議・おやすみモード (DND)');

    // ハンドラ登録
    this.service.getCharacteristic(this.platform.Characteristic.On)
      .onSet(this.setOn.bind(this))
      .onGet(this.getOn.bind(this));

    // 初回同期と定期同期
    this.syncState();
  }

  async setOn(value: CharacteristicValue) {
    const targetState = Boolean(value);
    this.platform.log.info(`[DND] HomeKit からの操作: ${targetState ? 'ON (ミュート開始)' : 'OFF (ミュート解除)'}`);

    try {
      await this.platform.client.setDnd(targetState, 'HomeKit 操作');
      this.isDndActive = targetState;
    } catch (err: any) {
      this.platform.log.error(`[DND] 操作失敗: ${err.message || err}`);
      throw new this.platform.api.hap.HapStatusError(this.platform.api.hap.HAPStatus.SERVICE_COMMUNICATION_FAILURE);
    }
  }

  async getOn(): Promise<CharacteristicValue> {
    try {
      const status = await this.platform.client.getDndStatus();
      this.isDndActive = status.isActive;
      return this.isDndActive;
    } catch (err: any) {
      this.platform.log.warn(`[DND] 状態取得失敗: ${err.message || err}`);
      return this.isDndActive;
    }
  }

  /**
   * 外部変更検知時の値アップデート
   */
  public updateState(isActive: boolean) {
    if (this.isDndActive !== isActive) {
      this.isDndActive = isActive;
      this.service.updateCharacteristic(this.platform.Characteristic.On, isActive);
      this.platform.log.info(`[DND] 外部変更を検知し状態を同期しました: ${isActive ? 'ON' : 'OFF'}`);
    }
  }

  private async syncState() {
    try {
      const status = await this.platform.client.getDndStatus();
      this.updateState(status.isActive);
    } catch {
      // 初期化時のサイレント無視
    }
  }
}
