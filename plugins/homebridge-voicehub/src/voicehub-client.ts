/**
 * VoiceHub REST API クライアント
 * Node.js 18+ ネイティブ fetch を使用したゼロ依存実装
 */

export interface VoiceHubDevice {
  id: string;
  name: string;
  rawName?: string;
  ip: string;
  rawIp?: string;
  mac?: string;
  model?: string;
  type: string;
  isDefault?: boolean;
}

export interface VoiceHubDevicesResponse {
  devices: VoiceHubDevice[];
  defaultIp?: string;
}

export interface VoiceHubDndStatus {
  enabled: boolean;
  isActive: boolean;
  active?: boolean;
  reason?: string | null;
  until?: number | null;
  queuedCount: number;
}

export interface VoiceHubSayResult {
  success: boolean;
  message?: string;
  targets?: string[];
  audioUrl?: string;
}

export class VoiceHubClient {
  private baseUrl: string;
  private token?: string;
  private timeoutMs: number;

  constructor(host: string, token?: string, timeoutMs: number = 8000) {
    // 末尾のスラッシュを除去して正規化
    let url = (host || 'http://localhost:8080').trim();
    if (url.endsWith('/')) {
      url = url.slice(0, -1);
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = `http://${url}`;
    }
    this.baseUrl = url;
    this.token = token?.trim() || undefined;
    this.timeoutMs = timeoutMs;
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'User-Agent': 'Homebridge-VoiceHub/1.0.0',
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
      headers['X-Webhook-Token'] = this.token;
    }
    return headers;
  }

  private getUrl(path: string): string {
    const base = `${this.baseUrl}${path.startsWith('/') ? path : '/' + path}`;
    if (this.token) {
      const sep = base.includes('?') ? '&' : '?';
      return `${base}${sep}token=${encodeURIComponent(this.token)}`;
    }
    return base;
  }

  /**
   * 登録済みスピーカー・デバイス一覧を取得
   */
  async getDevices(): Promise<VoiceHubDevice[]> {
    const url = this.getUrl('/api/devices');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const res = await fetch(url, {
        method: 'GET',
        headers: this.getHeaders(),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status} ${res.statusText}`);
      }

      const data = await res.json() as any;
      if (Array.isArray(data)) {
        return data as VoiceHubDevice[];
      }
      if (data && Array.isArray(data.devices)) {
        return data.devices as VoiceHubDevice[];
      }
      return [];
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * 指定スピーカーへテキストを発話
   */
  async say(text: string, target?: string, volume?: number): Promise<VoiceHubSayResult> {
    const url = this.getUrl('/api/say');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    const body: Record<string, any> = { text };
    if (target && target.trim().length > 0 && target !== 'ALL') {
      body.target = target.trim();
    }
    if (typeof volume === 'number' && volume >= 0 && volume <= 100) {
      body.volume = volume;
    }

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status} ${res.statusText}`);
      }

      return await res.json() as VoiceHubSayResult;
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * DND (おやすみ・会議モード) 状態を取得
   */
  async getDndStatus(): Promise<VoiceHubDndStatus> {
    const url = this.getUrl('/api/dnd/status');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const res = await fetch(url, {
        method: 'GET',
        headers: this.getHeaders(),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status} ${res.statusText}`);
      }

      const data = await res.json() as any;
      return {
        enabled: Boolean(data.enabled),
        isActive: Boolean(data.isActive ?? data.active),
        reason: data.reason || null,
        until: data.until || null,
        queuedCount: Number(data.queuedCount || data.queueCount || 0),
      };
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * DND (おやすみ・会議モード) を設定
   */
  async setDnd(active: boolean, reason?: string, durationMinutes?: number): Promise<boolean> {
    const path = active ? '/api/dnd/mute' : '/api/dnd/unmute';
    const url = this.getUrl(path);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    const body: Record<string, any> = {};
    if (active) {
      body.reason = reason || 'HomeKit操作';
      if (typeof durationMinutes === 'number' && durationMinutes > 0) {
        body.durationMinutes = durationMinutes;
      }
    }

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status} ${res.statusText}`);
      }

      const data = await res.json() as any;
      return Boolean(data.success);
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * DND をトグル切り替え
   */
  async toggleDnd(): Promise<boolean> {
    const url = this.getUrl('/api/dnd/toggle');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: this.getHeaders(),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status} ${res.statusText}`);
      }

      const data = await res.json() as any;
      return Boolean(data.success);
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * サーバー疎通確認
   */
  async ping(): Promise<boolean> {
    try {
      const url = this.getUrl('/api/status');
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 3000);
      const res = await fetch(url, { method: 'GET', signal: controller.signal });
      clearTimeout(timer);
      return res.ok;
    } catch {
      return false;
    }
  }
}
