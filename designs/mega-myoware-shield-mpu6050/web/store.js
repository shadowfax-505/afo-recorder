// Recordings live in this browser's IndexedDB. Each recording has one row in
// "recordings" and its samples in "chunks", written every couple of seconds so
// a closed tab or a crash keeps everything up to the last chunk.
//
// Chunk columns (all typed arrays, n rows):
//   t      Float64  seconds since the recording started (board clock)
//   seq    Uint32   unwrapped sample counter, gaps = samples lost on the link
//   flags  Uint8    bit0/bit1 = IMU A/B read failed
//   emg    Uint16   n x 6, ADC counts for A0..A5 (0 where not enabled)
//   imu    Int16    n x 12, raw LSB: IMU A ax ay az gx gy gz, then IMU B

const DB_NAME = 'mega-myoware-recorder';
const DB_VERSION = 1;
export const EMG_COLS = 6;
export const IMU_COLS = 12;

let dbPromise = null;

function req(r) {
  return new Promise((resolve, reject) => {
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}

function done(tx) {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error('transaction aborted'));
  });
}

export function openDb() {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const r = indexedDB.open(DB_NAME, DB_VERSION);
      r.onupgradeneeded = () => {
        const db = r.result;
        if (!db.objectStoreNames.contains('recordings')) db.createObjectStore('recordings', { keyPath: 'id', autoIncrement: true });
        if (!db.objectStoreNames.contains('chunks')) db.createObjectStore('chunks', { keyPath: ['recId', 'idx'] });
      };
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    });
  }
  return dbPromise;
}

export async function listRecordings() {
  const db = await openDb();
  const rows = await req(db.transaction('recordings').objectStore('recordings').getAll());
  return rows.sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
}

export async function getRecording(id) {
  const db = await openDb();
  return req(db.transaction('recordings').objectStore('recordings').get(id));
}

export async function putRecording(meta) {
  const db = await openDb();
  const tx = db.transaction('recordings', 'readwrite');
  const id = await req(tx.objectStore('recordings').put(meta));
  await done(tx);
  return id;
}

export async function putChunk(recId, idx, chunk) {
  const db = await openDb();
  const tx = db.transaction('chunks', 'readwrite');
  tx.objectStore('chunks').put({ recId, idx, ...chunk });
  await done(tx);
}

export async function deleteRecording(id) {
  const db = await openDb();
  const tx = db.transaction(['recordings', 'chunks'], 'readwrite');
  tx.objectStore('recordings').delete(id);
  tx.objectStore('chunks').delete(IDBKeyRange.bound([id, 0], [id, Infinity]));
  await done(tx);
}

// Loads every chunk of a recording into one set of contiguous arrays.
export async function loadSamples(id) {
  const db = await openDb();
  const chunks = await req(
    db.transaction('chunks').objectStore('chunks').getAll(IDBKeyRange.bound([id, 0], [id, Infinity])),
  );
  chunks.sort((a, b) => a.idx - b.idx);
  return joinChunks(chunks);
}

export function joinChunks(chunks) {
  const n = chunks.reduce((s, c) => s + c.n, 0);
  const out = {
    n,
    t: new Float64Array(n),
    seq: new Uint32Array(n),
    flags: new Uint8Array(n),
    emg: new Uint16Array(n * EMG_COLS),
    imu: new Int16Array(n * IMU_COLS),
  };
  let o = 0;
  for (const c of chunks) {
    out.t.set(c.t.subarray(0, c.n), o);
    out.seq.set(c.seq.subarray(0, c.n), o);
    out.flags.set(c.flags.subarray(0, c.n), o);
    out.emg.set(c.emg.subarray(0, c.n * EMG_COLS), o * EMG_COLS);
    out.imu.set(c.imu.subarray(0, c.n * IMU_COLS), o * IMU_COLS);
    o += c.n;
  }
  return out;
}

export class ChunkBuilder {
  constructor(capacity = 1024) {
    this.capacity = capacity;
    this.reset();
  }

  reset() {
    const c = this.capacity;
    this.n = 0;
    this.t = new Float64Array(c);
    this.seq = new Uint32Array(c);
    this.flags = new Uint8Array(c);
    this.emg = new Uint16Array(c * EMG_COLS);
    this.imu = new Int16Array(c * IMU_COLS);
  }

  get full() {
    return this.n >= this.capacity;
  }

  add(t, seq, s) {
    const i = this.n++;
    this.t[i] = t;
    this.seq[i] = seq;
    this.flags[i] = s.flags;
    for (let ch = 0; ch < EMG_COLS; ch++) this.emg[i * EMG_COLS + ch] = s.emg[ch] ?? 0;
    for (let k = 0; k < 2; k++)
      for (let a = 0; a < 6; a++) this.imu[i * IMU_COLS + k * 6 + a] = s.imu[k] ? s.imu[k][a] : 0;
  }

  // Hands back the filled rows and starts a fresh chunk.
  take() {
    const n = this.n;
    const chunk = {
      n,
      t: this.t.slice(0, n),
      seq: this.seq.slice(0, n),
      flags: this.flags.slice(0, n),
      emg: this.emg.slice(0, n * EMG_COLS),
      imu: this.imu.slice(0, n * IMU_COLS),
    };
    this.n = 0;
    return chunk;
  }
}
