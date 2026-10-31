// Web Serial transport (Chrome / Edge on desktop). The picker lists USB
// serial ports, the COM port Windows creates for a paired HC-05, and, on
// recent Chrome, paired Bluetooth serial (SPP) devices directly.

const SPP_UUID = '00001101-0000-1000-8000-00805f9b34fb';

export const serialSupported = () => 'serial' in navigator;

export class SerialTransport {
  constructor({ baud = 115200 } = {}) {
    this.baud = baud;
    this.onBytes = () => {};
    this.onClose = () => {};
    this.port = null;
    this.reader = null;
    this.closing = false;
    this.label = 'Serial';
  }

  async open() {
    this.port = await navigator.serial.requestPort({ allowedBluetoothServiceClassIds: [SPP_UUID] });
    await this.port.open({ baudRate: this.baud, bufferSize: 1 << 16 });
    const info = this.port.getInfo();
    this.label = info.bluetoothServiceClassId ? 'Bluetooth' : info.usbVendorId ? 'USB' : 'Serial port';
    const hex = (v) => (v === undefined ? '?' : v.toString(16).padStart(4, '0'));
    this.detail = info.usbVendorId ? `USB ${hex(info.usbVendorId)}:${hex(info.usbProductId)}` : this.label;
    this.loopDone = this.readLoop();
  }

  async readLoop() {
    try {
      while (this.port.readable && !this.closing) {
        this.reader = this.port.readable.getReader();
        try {
          for (;;) {
            const { value, done } = await this.reader.read();
            if (done) break;
            if (value) this.onBytes(value);
          }
        } catch (e) {
          // A framing/parity/buffer error is recoverable: get a new reader.
          if (this.closing) break;
          if (e && e.name !== 'BufferOverrunError' && e.name !== 'FramingError' && e.name !== 'ParityError' && e.name !== 'BreakError') throw e;
        } finally {
          this.reader.releaseLock();
          this.reader = null;
        }
      }
    } catch (e) {
      console.warn('serial read ended', e);
    }
    if (!this.closing) this.onClose(new Error('The serial port closed (cable unplugged or Bluetooth out of range).'));
  }

  // Writes are queued: Chrome throws if a second writer is taken while a
  // write is still pending, which used to drop the 's' that starts the stream.
  write(text) {
    const p = (this.writeChain || Promise.resolve()).then(() => this.writeNow(text));
    this.writeChain = p.catch(() => {});
    return p;
  }

  async writeNow(text) {
    if (!this.port || !this.port.writable) return;
    const w = this.port.writable.getWriter();
    try {
      await w.write(new TextEncoder().encode(text));
    } finally {
      w.releaseLock();
    }
  }

  async close() {
    this.closing = true;
    try {
      await this.write('x\n');
    } catch {}
    try {
      if (this.reader) await this.reader.cancel();
      await this.loopDone;
    } catch {}
    try {
      await this.port.close();
    } catch {}
  }
}
