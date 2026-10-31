// Wi-Fi transport: a WebSocket to the ESP32 bridge (../firmware/esp32_wifi_bridge),
// which passes bytes both ways to the Mega's Serial2. Same interface as
// SerialTransport, so the rest of the app does not care which link it is.
//
// Browsers block ws:// from an https:// page (mixed content), so use the app
// from http://localhost (or open it from the file server on your computer),
// not from the GitHub Pages copy, when connecting over Wi-Fi.

export const DEFAULT_HOST = 'afo-mega.local';

export function wsUrl(host) {
  const h = String(host || DEFAULT_HOST).trim().replace(/^wss?:\/\//, '').replace(/^https?:\/\//, '').replace(/\/.*$/, '');
  return `ws://${h}/ws`;
}

export class WifiTransport {
  constructor({ host = DEFAULT_HOST, timeoutMs = 6000, WebSocketImpl = globalThis.WebSocket } = {}) {
    this.host = host;
    this.url = wsUrl(host);
    this.timeoutMs = timeoutMs;
    this.WS = WebSocketImpl;
    this.onBytes = () => {};
    this.onClose = () => {};
    this.label = 'Wi-Fi';
    this.detail = `Wi-Fi ${this.url}`;
    this.baud = 500000; // Mega Serial2 to ESP32; the info frame reports the real value
    this.ws = null;
    this.closing = false;
  }

  open() {
    if (globalThis.location && location.protocol === 'https:')
      return Promise.reject(
        new Error('This page was opened over https, and browsers do not allow it to reach the ESP32 (ws://). Open the app from http://localhost on your computer instead.'),
      );
    return new Promise((resolve, reject) => {
      let settled = false;
      const ws = new this.WS(this.url);
      ws.binaryType = 'arraybuffer';
      const timer = setTimeout(() => {
        if (settled) return;
        settled = true;
        try {
          ws.close();
        } catch {}
        reject(new Error(`No answer from ${this.host}. Check that the ESP32 is powered, that this computer is on the same Wi-Fi (or joined to the AFO-MEGA network), and try its IP address instead of the name.`));
      }, this.timeoutMs);
      ws.onopen = () => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        this.ws = ws;
        resolve();
      };
      ws.onerror = () => {};
      ws.onclose = (ev) => {
        clearTimeout(timer);
        if (!settled) {
          settled = true;
          reject(new Error(`Could not open ${this.url}${ev && ev.code ? ` (code ${ev.code})` : ''}. Check the ESP32's address.`));
          return;
        }
        if (!this.closing) this.onClose(new Error('The Wi-Fi link closed (ESP32 restarted, out of range, or another device took the connection).'));
      };
      ws.onmessage = (ev) => {
        const d = ev.data;
        if (d instanceof ArrayBuffer) this.onBytes(new Uint8Array(d));
        else if (typeof d === 'string') this.onBytes(new TextEncoder().encode(d));
      };
    });
  }

  write(text) {
    if (this.ws && this.ws.readyState === 1) this.ws.send(new TextEncoder().encode(text));
    return Promise.resolve();
  }

  async close() {
    this.closing = true;
    try {
      await this.write('x\n');
    } catch {}
    try {
      if (this.ws) this.ws.close();
    } catch {}
  }
}
