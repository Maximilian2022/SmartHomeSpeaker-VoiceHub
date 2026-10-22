import { Service, PlatformAccessory, CharacteristicValue } from 'homebridge';
import { VoiceHubPlatform } from '../platform';

export type DisasterSensorType = 'eew' | 'warning' | 'rain';

/**
 * スマートホーム防災連動トリガー（仮想モーションセンサー）アクセサリ
 * Apple Home (HomeKit) のオートメーション（照明点灯、家電制御等）のトリガーとして動作
 */
export class DisasterSensorAccessory {
  private service: Service;
  private isDetected: boolean = false;

  constructor(
    private readonly platform: VoiceHubPlatform,
    private readonly accessory: PlatformAccessory,
    public readonly sensorType: DisasterSensorType,
  ) {
    const configMap: Record<DisasterSensorType, { model: string; serial: string; defaultName: string }> = {
      eew: {
        model: 'Disaster Sensor - EEW',
        serial: 'VH-DISASTER-EEW',
        defaultName: 'EEW Alert / 緊急地震速報 (EEW)',
      },
      warning: {
        model: 'Disaster Sensor - Warning',
        serial: 'VH-DISASTER-WARN',
        defaultName: 'Weather Warning / 気象警報',
      },
      rain: {
        model: 'Disaster Sensor - Rain',
        serial: 'VH-DISASTER-RAIN',
        defaultName: 'Rain Approaching / 雨雲接近',
      },
    };

    const conf = configMap[sensorType];

    // アクセサリ情報設定
    this.accessory.getService(this.platform.Service.AccessoryInformation)!
      .setCharacteristic(this.platform.Characteristic.Manufacturer, 'VoiceHub')
      .setCharacteristic(this.platform.Characteristic.Model, conf.model)
      .setCharacteristic(this.platform.Characteristic.SerialNumber, conf.serial);

    // 仮想モーションセンサーサービス取得または新規登録
    this.service = this.accessory.getService(this.platform.Service.MotionSensor)
      || this.accessory.addService(this.platform.Service.MotionSensor);

    this.service.setCharacteristic(
      this.platform.Characteristic.Name,
      this.accessory.displayName || conf.defaultName,
    );

    // ハンドラ登録
    this.service.getCharacteristic(this.platform.Characteristic.MotionDetected)
      .onGet(this.getMotionDetected.bind(this));
  }

  async getMotionDetected(): Promise<CharacteristicValue> {
    return this.isDetected;
  }

  /**
   * 外部状態変更時の検知フラグ更新
   */
  public updateState(detected: boolean) {
    if (this.isDetected !== detected) {
      this.isDetected = detected;
      this.service.updateCharacteristic(this.platform.Characteristic.MotionDetected, detected);
      this.platform.log.info(
        `[DisasterSensor] ${this.sensorType.toUpperCase()} trigger state updated / 防災トリガー状態更新: ${detected ? 'DETECTED (ON)' : 'CLEAR (OFF)'}`,
      );
    }
  }
}
