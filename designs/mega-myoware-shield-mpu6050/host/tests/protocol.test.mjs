// Run: node --test designs/mega-myoware-shield-mpu6050/host/tests/
// Checks the web app's decoder against frames built by the firmware's own
// frame.h (compiled natively with g++), plus stream splitting, corruption,
// and counter wrap-around.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { FrameParser, SampleClock, encodeData, crc8 } from '../../web/protocol.js';
import { joinChunks, ChunkBuilder } from '../../web/store.js';

const here = dirname(fileURLToPath(import.meta.url));
const hex = (s) => Uint8Array.from(s.match(/../g).map((h) => parseInt(h, 16)));

function firmwareFrames() {
  const exe = join(mkdtempSync(join(tmpdir(), 'frame-')), 'frame_dump');
  execFileSync('g++', ['-std=c++11', '-Wall', '-Wextra', '-Werror', '-o', exe, join(here, 'frame_dump.cpp')]);
  return execFileSync(exe, { encoding: 'utf8' }).trim().split('\n').map(hex);
}

function expected(m) {
  const masks = [[0x01, 0x03], [0x3f, 0x03], [0x00, 0x01], [0x05, 0x02], [0x01, 0x00], [0x3f, 0x00]];
  const [emgMask, imuMask] = masks[m];
  return {
    seq: (65530 + m * 3) & 0xffff,
    tUs: (4294967000 + m * 250) >>> 0,
    emgMask,
    imuMask,
    flags: m & 3,
    emg: [0, 1, 2, 3, 4, 5].map((ch) => (emgMask & (1 << ch) ? ch * 200 + m : null)),
    imu: [0, 1].map((k) =>
      imuMask & (1 << k) ? [0, 1, 2, 3, 4, 5].map((a) => (a % 2 ? -1 : 1) * (k * 10000 + a * 1111 + m)) : null,
    ),
  };
}

function parseAll(bytes, splits = [bytes.length]) {
  const samples = [];
  const infos = [];
  const texts = [];
  const p = new FrameParser({ onSample: (s) => samples.push(s), onInfo: (i) => infos.push(i), onText: (t) => texts.push(t) });
  let o = 0;
  for (const n of splits) {
    p.push(bytes.subarray(o, o + n));
    o += n;
  }
  if (o < bytes.length) p.push(bytes.subarray(o));
  return { samples, infos, texts, stats: p.stats };
}

const concat = (parts) => {
  const out = new Uint8Array(parts.reduce((a, p) => a + p.length, 0));
  let o = 0;
  for (const p of parts) {
    out.set(p, o);
    o += p.length;
  }
  return out;
};

test('decodes frames produced by the firmware encoder', () => {
  const frames = firmwareFrames();
  const { samples, infos, stats } = parseAll(concat(frames));
  assert.equal(stats.crcErrors, 0);
  assert.equal(samples.length, frames.length - 1);
  samples.forEach((s, m) => assert.deepEqual(s, expected(m)));
  assert.deepEqual(infos, [{ fw: 'test', rate: 20 }]);
});

test('web encoder matches the firmware encoder byte for byte', () => {
  const frames = firmwareFrames();
  for (let m = 0; m < frames.length - 1; m++) {
    const e = expected(m);
    const s = { ...e, emg: e.emg.map((v) => v ?? 0), imu: e.imu.map((v) => v ?? [0, 0, 0, 0, 0, 0]) };
    assert.deepEqual(encodeData(s), frames[m]);
  }
});

test('survives banners, byte-by-byte delivery and corrupted frames', () => {
  const frames = firmwareFrames();
  const banner = new TextEncoder().encode('# mega-myoware-1.0 ready. imu_mask=3.\r\n');
  const bad = frames[1].slice();
  bad[10] ^= 0x40; // corrupt payload, CRC no longer matches
  const stream = concat([banner, frames[0], bad, Uint8Array.of(0xa5, 0x00, 0x13), frames[2], frames[6]]);
  const ones = new Array(stream.length).fill(1);
  const { samples, infos, texts, stats } = parseAll(stream, ones);
  assert.deepEqual(texts, ['# mega-myoware-1.0 ready. imu_mask=3.']);
  assert.equal(stats.crcErrors, 1);
  assert.deepEqual(samples.map((s) => s.seq), [expected(0).seq, expected(2).seq]);
  assert.equal(infos.length, 1);
});

test('crc8 matches CRC-8/SMBUS check value', () => {
  assert.equal(crc8(new TextEncoder().encode('123456789')), 0xf4);
});

test('clock unwraps seq and micros and counts lost samples', () => {
  const c = new SampleClock();
  const pts = [
    [65534, 4294966000],
    [65535, 4294967000],
    [2, 2704], // seq wrapped and skipped 0 and 1; micros wrapped
    [3, 3704],
  ].map(([seq, tUs]) => c.step({ seq, tUs }));
  assert.deepEqual(pts.map((p) => p.seq), [0, 1, 4, 5]);
  assert.deepEqual(pts.map((p) => p.us), [0, 1000, 4000, 5000]);
  assert.equal(c.lost, 2);
  // streaming restarted: seq jumps back to 0, timeline keeps going forward
  const r = c.step({ seq: 0, tUs: 4704 });
  assert.equal(r.seq, 6);
  assert.equal(r.us, 6000);
  assert.equal(c.lost, 2);
});

test('chunks join back in order', () => {
  const b = new ChunkBuilder(3);
  const chunks = [];
  for (let i = 0; i < 7; i++) {
    b.add(i / 100, i, { flags: i & 1, emg: [i, null, null, null, null, i * 2], imu: [[i, -i, 0, 0, 0, 1], null] });
    if (b.full) chunks.push({ idx: chunks.length, ...b.take() });
  }
  chunks.push({ idx: chunks.length, ...b.take() });
  const d = joinChunks(chunks);
  assert.equal(d.n, 7);
  assert.deepEqual(Array.from(d.seq), [0, 1, 2, 3, 4, 5, 6]);
  assert.equal(d.emg[6 * 6 + 5], 12);
  assert.equal(d.imu[5 * 12 + 1], -5);
  assert.equal(d.imu[5 * 12 + 6], 0);
});
