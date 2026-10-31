// Run: node --test designs/mega-myoware-shield-mpu6050/host/tests/wifi.test.mjs
// The Wi-Fi transport (web/wifi.js) against a fake WebSocket that behaves like
// the ESP32 bridge: bytes from the app go to the "Mega", bytes back arrive as
// binary messages in arbitrary chunks.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { WifiTransport, wsUrl } from '../../web/wifi.js';

class FakeWS {
  static last = null;
  constructor(url) {
    this.url = url;
    this.readyState = 0;
    this.sent = [];
    FakeWS.last = this;
    setTimeout(() => {
      if (FakeWS.refuse) {
        this.readyState = 3;
        this.onclose?.({ code: 1006 });
      } else {
        this.readyState = 1;
        this.onopen?.();
      }
    }, 5);
  }
  send(b) {
    this.sent.push(new TextDecoder().decode(b));
  }
  close() {
    this.readyState = 3;
    this.onclose?.({ code: 1000 });
  }
}

test('addresses', () => {
  assert.equal(wsUrl('afo-mega.local'), 'ws://afo-mega.local/ws');
  assert.equal(wsUrl(' http://192.168.4.1/ '), 'ws://192.168.4.1/ws');
  assert.equal(wsUrl(''), 'ws://afo-mega.local/ws');
});

test('opens, passes bytes both ways, stops the board on close', async () => {
  FakeWS.refuse = false;
  const t = new WifiTransport({ host: '192.168.4.1', WebSocketImpl: FakeWS });
  const got = [];
  t.onBytes = (b) => got.push(...b);
  let closedWith = null;
  t.onClose = (e) => (closedWith = e);
  await t.open();
  const ws = FakeWS.last;
  assert.equal(ws.url, 'ws://192.168.4.1/ws');
  assert.equal(ws.binaryType, 'arraybuffer');
  await t.write('?\n');
  await t.write('s\n');
  assert.deepEqual(ws.sent, ['?\n', 's\n']);
  ws.onmessage({ data: new Uint8Array([0xa5, 0x5a, 1]).buffer });
  ws.onmessage({ data: new Uint8Array([2, 3]).buffer });
  assert.deepEqual(got, [0xa5, 0x5a, 1, 2, 3]);
  // an unexpected drop is reported
  ws.onclose({ code: 1006 });
  assert.match(closedWith.message, /Wi-Fi link closed/);
  // a deliberate close sends x first and reports nothing
  const t2 = new WifiTransport({ WebSocketImpl: FakeWS });
  let closed2 = false;
  t2.onClose = () => (closed2 = true);
  await t2.open();
  await t2.close();
  assert.deepEqual(FakeWS.last.sent, ['x\n']);
  assert.equal(closed2, false);
});

test('a refused or silent bridge gives a clear error', async () => {
  FakeWS.refuse = true;
  await assert.rejects(new WifiTransport({ WebSocketImpl: FakeWS }).open(), /Could not open ws:\/\/afo-mega.local\/ws/);
  class Silent {
    constructor() {
      this.readyState = 0;
    }
    close() {}
  }
  await assert.rejects(new WifiTransport({ WebSocketImpl: Silent, timeoutMs: 30 }).open(), /No answer from afo-mega.local/);
});
