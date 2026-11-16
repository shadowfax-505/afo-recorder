// Run: node --test designs/mega-myoware-shield-mpu6050/host/tests/emgraw.test.mjs   # needs g++
// The raw 2 kHz EMG stream: frames built by the firmware's emgraw.h (compiled
// natively) decoded by the web app, with a ring overrun in the middle, and the
// app-side index unwrapping and storage.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync, execFileSync } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { FrameParser, RawClock, SampleClock, decodeRaw, encodeData, encodeRaw, popcount } from '../../web/protocol.js';
import { RawBuilder } from '../../web/store.js';

const here = dirname(fileURLToPath(import.meta.url));
const hex = (s) => Uint8Array.from(s.match(/../g).map((h) => parseInt(h, 16)));

function firmware(mask) {
  const exe = join(mkdtempSync(join(tmpdir(), 'emgraw-')), 'emgraw_dump');
  execFileSync('g++', ['-std=c++11', '-Wall', '-Wextra', '-Werror', '-o', exe, join(here, 'emgraw_dump.cpp')]);
  const r = spawnSync(exe, [String(mask)], { encoding: 'utf8' });
  return { frames: r.stdout.trim().split('\n').map(hex), overruns: Number(r.stderr.trim()) };
}

for (const mask of [0x03, 0x3f, 0x20]) {
  test(`firmware raw frames decode in the app (mask 0x${mask.toString(16)})`, () => {
    const { frames, overruns } = firmware(mask);
    const got = [];
    const p = new FrameParser({ onRaw: (r) => got.push(r) });
    for (const f of frames) p.push(f);
    assert.equal(p.stats.crcErrors + p.stats.badFrames, 0);
    assert.equal(got.length, frames.length);
    const pc = popcount(mask);
    const chans = [0, 1, 2, 3, 4, 5].filter((ch) => mask & (1 << ch));
    const clock = new RawClock();
    const seen = [];
    for (const r of got) {
      assert.equal(r.mask, mask);
      assert.ok(r.n * pc * 2 + 10 <= 255);
      const first = clock.step(r);
      for (let i = 0; i < r.n; i++) {
        const idx = first + i;
        seen.push(idx);
        chans.forEach((ch, k) => assert.equal(r.rows[i * pc + k], 100 * ch + (idx % 100), `sample ${idx} A${ch}`));
      }
    }
    // samples 24..199 waited in a 128-row ring: the oldest 48 were overwritten
    assert.equal(overruns, 48);
    assert.equal(clock.lost, 48);
    assert.equal(clock.received, 300 - 48);
    assert.equal(seen[0], 0);
    assert.equal(seen[seen.length - 1], 299);
    assert.ok(!seen.includes(24) && !seen.includes(71) && seen.includes(72));
    // t_us is the drain time (wraps at 2^32)
    assert.equal(got[0].tUs, (4294967000 + 7 * 500) >>> 0);
    assert.equal(got[got.length - 1].tUs, (4294967000 + 300 * 500) >>> 0);
  });
}

test('raw frames survive between data frames, split anywhere', () => {
  const d = (seq) => encodeData({ seq, tUs: 1000 + seq * 4000, emgMask: 1, imuMask: 0, flags: 0, emg: [seq, 0, 0, 0, 0, 0], imu: [null, null] });
  const e = (i) => encodeRaw({ idx0: i * 8, tUs: 1000 + i * 4000 + 50, mask: 0x05, rows: Uint16Array.from({ length: 16 }, (_, k) => i * 100 + k) });
  const parts = [];
  for (let i = 0; i < 5; i++) parts.push(d(i), e(i));
  const bytes = Uint8Array.from(parts.flatMap((p) => [...p]));
  for (const step of [1, 7, bytes.length]) {
    const order = [];
    const p = new FrameParser({ onSample: (s) => order.push(`D${s.seq}`), onRaw: (r) => order.push(`E${r.idx0}`) });
    for (let o = 0; o < bytes.length; o += step) p.push(bytes.subarray(o, o + step));
    assert.deepEqual(order, ['D0', 'E0', 'D1', 'E8', 'D2', 'E16', 'D3', 'E24', 'D4', 'E32']);
  }
  assert.equal(decodeRaw(new Uint8Array(9)), null);
  assert.equal(decodeRaw(e(0).subarray(4, 4 + 10 + 30)), null); // length does not match n
});

test('index unwrap across 2^32 and a board restart', () => {
  const c = new RawClock();
  const f = (idx0, n = 8) => ({ idx0: idx0 >>> 0, n });
  assert.equal(c.step(f(4294967288)), 0);
  assert.equal(c.step(f(0)), 8); // wrapped, no loss
  assert.equal(c.step(f(16)), 24); // 8 lost
  assert.equal(c.lost, 8);
  assert.equal(c.step(f(0)), 32); // restart: counts on without a gap
  assert.equal(c.restarts, 1);
  assert.equal(c.lost, 8);
});

test('frame time stamps land on the data-frame clock', () => {
  const c = new SampleClock();
  assert.equal(c.at(5), null);
  c.step({ seq: 0, tUs: 4294967000 });
  c.step({ seq: 1, tUs: (4294967000 + 4000) >>> 0 }); // wrapped
  assert.equal(c.at((4294967000 + 4100) >>> 0), 4100);
  assert.equal(c.at((4294967000 + 3900) >>> 0), 3900);
});

test('raw builder stores six columns per sample', () => {
  const b = new RawBuilder(4);
  b.add(10, 0x05, Uint16Array.from([7, 9, 11, 13]), 0);
  b.add(11, 0x05, Uint16Array.from([7, 9, 11, 13]), 2);
  const c = b.take();
  assert.equal(c.n, 2);
  assert.deepEqual([...c.si], [10, 11]);
  assert.deepEqual([...c.v], [7, 0, 9, 0, 0, 0, 11, 0, 13, 0, 0, 0]);
  assert.equal(b.n, 0);
});
