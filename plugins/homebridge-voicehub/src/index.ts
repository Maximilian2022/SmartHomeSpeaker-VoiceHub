import { API } from 'homebridge';
import { PLATFORM_NAME } from './settings';
import { VoiceHubPlatform } from './platform';

/**
 * Homebridge プラグインのエントリーポイント
 */
export = (api: API) => {
  api.registerPlatform(PLATFORM_NAME, VoiceHubPlatform);
};
