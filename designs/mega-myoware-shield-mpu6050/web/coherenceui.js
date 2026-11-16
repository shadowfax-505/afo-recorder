// Coherence panel for a recording that holds raw 2 kHz EMG (see coherence.js).
import { COH_DEFAULTS, analyzeRawCoherence, phaseWindows } from './coherence.js';

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const el = (tag, props = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'class') e.className = v;
    else if (k in e) e[k] = v;
    else e.setAttribute(k, v);
  }
  e.append(...kids.filter((k) => k !== null && k !== undefined));
  return e;
};

const PHASES = [
  ['swing', 'Swing (toe-off to next heel strike)'],
  ['stance', 'Stance (heel strike to toe-off)'],
  ['stride', 'Whole strides'],
  ['all', 'Whole recording (bench checks, standing, holding a contraction)'],
  ['zoom', 'The part shown in the charts'],
];

export const COH_SETTINGS = { x: -1, y: -1, phase: 'swing', lo: COH_DEFAULTS.band[0], hi: COH_DEFAULTS.band[1], rectify: true, mainsHz: 50 };

export class CoherencePanel {
  // opts: {idPrefix, settings, onChange(settings), getContext() -> {raw, rawMeta, strides, zoom:[t0,t1], muscles}}
  constructor(host, opts) {
    this.opts = opts;
    this.settings = { ...COH_SETTINGS, ...(opts.settings || {}) };
    this.result = null;
    const id = opts.idPrefix || 'coh';
    this.selX = el('select', { id: `${id}-x` });
    this.selY = el('select', { id: `${id}-y` });
    this.selPhase = el('select', { id: `${id}-phase` }, ...PHASES.map(([v, t]) => el('option', { value: v }, t)));
    this.lo = el('input', { id: `${id}-lo`, type: 'number', min: 1, max: 500, step: 1 });
    this.hi = el('input', { id: `${id}-hi`, type: 'number', min: 2, max: 1000, step: 1 });
    this.rect = el('input', { id: `${id}-rect`, type: 'checkbox' });
    this.mains = el('select', { id: `${id}-mains` }, el('option', { value: '50' }, '50 Hz, left out'), el('option', { value: '60' }, '60 Hz, left out'), el('option', { value: '0' }, 'Keep all bins'));
    this.csv = el('button', { id: `${id}-csv` }, 'Coherence CSV');
    this.warn = el('ul', { class: 'notice gait-warn', hidden: true });
    this.table = el('table', { class: 'gait-table coh-table' });
    this.cSpec = el('canvas', {});
    this.cLag = el('canvas', {});
    this.root = el(
      'section',
      { class: 'gait coh', 'aria-label': 'EMG coherence' },
      el(
        'div',
        { class: 'gait-head' },
        el('h2', {}, 'Coherence between two EMG sites (raw 2 kHz)'),
        el(
          'p',
          { class: 'hint' },
          'How strongly two raw EMG channels share a rhythm at each frequency (0 = none, 1 = identical). For two sites on the tibialis anterior, 15–55 Hz coherence in swing is read as common drive from the brain to that muscle. Values under the dashed line are what unrelated signals give by chance. Run the bench checks first: cross-talk, mains and shared electronics noise also produce coherence.',
        ),
      ),
      el(
        'div',
        { class: 'toolbar' },
        el('label', { class: 'field' }, 'Channel 1', this.selX),
        el('label', { class: 'field' }, 'Channel 2', this.selY),
        el('label', { class: 'field' }, 'Part of the walk', this.selPhase),
        el('label', { class: 'field' }, 'Band from (Hz)', this.lo),
        el('label', { class: 'field' }, 'to (Hz)', this.hi),
        el('label', { class: 'field' }, 'Mains', this.mains),
        el('label', { class: 'field check' }, el('span', {}, 'Rectify'), this.rect),
        el('div', { class: 'group push' }, this.csv),
      ),
      this.warn,
      el('div', { class: 'table-scroll' }, this.table),
      el(
        'div',
        { class: 'charts gait-charts coh-charts' },
        el('figure', { class: 'chart' }, el('figcaption', {}, el('h3', {}, 'Coherence by frequency'), el('span', { class: 'unit' }, 'shaded: band · dashed: 95 % chance limit')), el('div', { class: 'plot' }, this.cSpec)),
        el('figure', { class: 'chart' }, el('figcaption', {}, el('h3', {}, 'Time lag of the shared part'), el('span', { class: 'unit' }, 'channel 2 after channel 1 → positive ms')), el('div', { class: 'plot' }, this.cLag)),
      ),
    );
    host.replaceChildren(this.root);
    for (const c of [this.selX, this.selY, this.selPhase, this.lo, this.hi, this.rect, this.mains]) c.addEventListener('change', () => this.changed());
    this.csv.addEventListener('click', () => this.opts.onCsv && this.result && !this.result.error && this.opts.onCsv(this.toCsv()));
  }

  set hidden(v) {
    this.root.hidden = v;
  }

  // Fills the channel pickers for the raw channel mask and runs the analysis.
  setChannels(mask, muscles = {}) {
    const chans = [];
    for (let ch = 0; ch < 6; ch++) if (mask & (1 << ch)) chans.push(ch);
    this.chans = chans;
    this.muscles = muscles;
    const name = (ch) => `A${ch}${muscles[ch] ? ` · ${muscles[ch]}` : ''}`;
    for (const sel of [this.selX, this.selY]) sel.replaceChildren(...chans.map((ch) => el('option', { value: String(ch) }, name(ch))));
    const s = this.settings;
    if (!chans.includes(s.x)) s.x = chans[0] ?? -1;
    if (!chans.includes(s.y) || s.y === s.x) s.y = chans.find((c) => c !== s.x) ?? -1;
    this.selX.value = String(s.x);
    this.selY.value = String(s.y);
    this.selPhase.value = s.phase;
    this.lo.value = s.lo;
    this.hi.value = s.hi;
    this.rect.checked = s.rectify;
    this.mains.value = String(s.mainsHz);
    this.run();
  }

  changed() {
    const s = this.settings;
    s.x = Number(this.selX.value);
    s.y = Number(this.selY.value);
    s.phase = this.selPhase.value;
    s.lo = Math.max(1, Number(this.lo.value) || COH_DEFAULTS.band[0]);
    s.hi = Math.max(s.lo + 1, Number(this.hi.value) || COH_DEFAULTS.band[1]);
    s.rectify = this.rect.checked;
    s.mainsHz = Number(this.mains.value);
    if (this.opts.onChange) this.opts.onChange({ ...s });
    this.run();
  }

  run() {
    const s = this.settings;
    const ctx = this.opts.getContext();
    let res;
    if (!ctx || !ctx.raw || !ctx.raw.n) res = { error: 'This recording has no raw 2 kHz EMG. Tick "Raw 2 kHz EMG" on the Live tab before recording (ESP32 firmware 1.3 or later, over Wi-Fi).' };
    else if (s.x < 0 || s.y < 0 || s.x === s.y) res = { error: 'Coherence needs two different raw EMG channels. Switch on a second EMG jack before recording.' };
    else {
      let windows = null;
      if (s.phase === 'zoom') windows = [ctx.zoom];
      else if (s.phase !== 'all') {
        windows = phaseWindows(ctx.strides, s.phase);
        if (!windows.length) res = { error: 'No strides were found, so there is no swing or stance to analyse. Pick "Whole recording", or check the gait analysis above.' };
      }
      if (!res) res = analyzeRawCoherence(ctx.raw, ctx.rawMeta, s.x, s.y, { windows, band: [s.lo, s.hi], rectify: s.rectify, mainsHz: s.mainsHz });
    }
    this.result = res;
    this.render();
  }

  render() {
    const r = this.result;
    const warnings = r.error ? [r.error] : r.warnings;
    this.warn.hidden = !warnings.length;
    this.warn.replaceChildren(...warnings.map((w) => el('li', {}, w)));
    this.csv.disabled = !!r.error;
    if (r.error) {
      this.table.replaceChildren();
      for (const c of [this.cSpec, this.cLag]) c.getContext('2d').clearRect(0, 0, c.width, c.height);
      return;
    }
    const b = r.band;
    const row = (name, value, note) => el('tr', {}, el('th', { scope: 'row' }, name), el('td', {}, value), el('td', { class: 'hint' }, note || ''));
    const chance = b.bins ? Math.max(1, Math.round(0.05 * b.bins)) : 0;
    this.table.replaceChildren(
      el('thead', {}, el('tr', {}, el('th', {}, 'Result'), el('th', {}, 'Value'), el('th', {}, 'How to read it'))),
      el(
        'tbody',
        {},
        row('Segments averaged', `${r.L}`, `${(r.segLen / r.fs * 1000).toFixed(0)} ms each, ${(r.fs / r.segLen).toFixed(1)} Hz resolution${r.windows ? `, from ${r.windows} windows` : ''}`),
        row('95 % chance limit', r.cl95.toFixed(4), 'Unrelated signals stay below this at 95 % of frequencies'),
        row(`Mean coherence ${b.lo}–${b.hi} Hz`, Number.isFinite(b.mean) ? b.mean.toFixed(4) : '–', b.mean > r.cl95 ? 'Above the chance limit' : 'Not above the chance limit'),
        row('Peak in band', Number.isFinite(b.peak) ? `${b.peak.toFixed(3)} at ${b.peakHz.toFixed(1)} Hz` : '–', ''),
        row('Bins above the limit', `${b.above} of ${b.bins}`, `About ${chance} expected by chance${b.mainsBins ? `; ${b.mainsBins} bins around mains left out` : ''}`),
        row('Area above the limit', `${b.area.toFixed(3)} Hz`, 'Coherence above the limit, summed over the band'),
        ...(r.options.mainsHz > 0 ? [row(`Coherence at mains (${r.options.mainsHz} Hz)`, r.mainsPeak.toFixed(3), 'High here means both channels pick up the same mains hum')] : []),
        row('Lag of the shared part', Number.isFinite(r.cumulant.peak.lagMs) ? `${r.cumulant.peak.lagMs.toFixed(1)} ms (size ${r.cumulant.peak.value.toFixed(3)})` : '–', Math.abs(r.cumulant.peak.value) > 4 * r.cumulant.limit ? 'A sharp peak at exactly 0 ms with coherence at all frequencies points to cross-talk or shared electronics noise' : 'No clear shared part in time'),
        row('Signal size after filtering', `${r.rms.x.toFixed(1)} / ${r.rms.y.toFixed(1)} counts RMS`, 'Channel 1 / channel 2, 12-bit ADC counts'),
      ),
    );
    this.draw();
  }

  draw() {
    const r = this.result;
    if (!r || r.error || this.root.hidden) return;
    const fmax = Math.min(r.fs / 2, Math.max(100, r.band.hi * 1.6));
    const ymax = Math.max(0.1, r.cl95 * 2, ...Array.from(r.coh).filter((_, k) => r.f[k] >= 2 && r.f[k] <= fmax)) * 1.1;
    plot(this.cSpec, {
      x: r.f,
      y: r.coh,
      xmin: 0,
      xmax: fmax,
      ymin: 0,
      ymax: Math.min(1, ymax),
      xlabel: 'Hz',
      hline: r.cl95,
      shade: [r.band.lo, r.band.hi],
    });
    const lim = Math.max(4 * r.cumulant.limit, ...Array.from(r.cumulant.q, Math.abs)) * 1.15;
    plot(this.cLag, { x: r.cumulant.lagMs, y: r.cumulant.q, xmin: r.cumulant.lagMs[0], xmax: -r.cumulant.lagMs[0], ymin: -lim, ymax: lim, xlabel: 'ms', hline: r.cumulant.limit, hline2: -r.cumulant.limit, vline: 0 });
  }

  toCsv() {
    const r = this.result;
    const s = this.settings;
    const lines = [
      `# coherence A${s.x} vs A${s.y}; part ${s.phase}; ${r.L} segments of ${r.segLen} samples at ${r.fs} Hz; rectified ${s.rectify}; high-pass ${r.options.hpHz} Hz`,
      `# 95 % chance limit ${r.cl95.toFixed(6)}; band ${r.band.lo}-${r.band.hi} Hz mean ${r.band.mean.toFixed(6)}, peak ${r.band.peak.toFixed(6)} at ${r.band.peakHz.toFixed(2)} Hz, ${r.band.above} of ${r.band.bins} bins above the limit`,
      'frequency_hz,coherence,phase_rad,psd_ch1,psd_ch2',
    ];
    for (let k = 0; k < r.f.length; k++) lines.push([r.f[k].toFixed(3), r.coh[k].toFixed(6), r.phase[k].toFixed(4), r.psd.x[k].toExponential(4), r.psd.y[k].toExponential(4)].join(','));
    lines.push('', 'lag_ms,cumulant');
    for (let i = 0; i < r.cumulant.q.length; i++) lines.push(`${r.cumulant.lagMs[i].toFixed(2)},${r.cumulant.q[i].toFixed(6)}`);
    return lines.join('\n') + '\n';
  }
}

function plot(canvas, { x, y, xmin, xmax, ymin, ymax, xlabel, hline, hline2, vline, shade }) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || 600;
  const h = canvas.clientHeight || 200;
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  const g = canvas.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  const L = 46;
  const R = 10;
  const T = 8;
  const B = 24;
  const X = (v) => L + ((v - xmin) / (xmax - xmin)) * (w - L - R);
  const Y = (v) => h - B - ((v - ymin) / (ymax - ymin)) * (h - T - B);
  g.font = '11px system-ui, sans-serif';
  if (shade) {
    g.fillStyle = css('--select');
    g.fillRect(X(Math.max(xmin, shade[0])), T, X(Math.min(xmax, shade[1])) - X(Math.max(xmin, shade[0])), h - T - B);
  }
  g.strokeStyle = css('--grid');
  g.fillStyle = css('--text-muted');
  g.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const v = ymin + ((ymax - ymin) * i) / 4;
    g.beginPath();
    g.moveTo(L, Y(v));
    g.lineTo(w - R, Y(v));
    g.stroke();
    g.textAlign = 'right';
    g.fillText(Math.abs(v) < 1e-9 ? '0' : v.toFixed(Math.abs(ymax - ymin) < 0.2 ? 3 : 2), L - 6, Y(v) + 4);
  }
  for (let i = 0; i <= 5; i++) {
    const v = xmin + ((xmax - xmin) * i) / 5;
    g.textAlign = 'center';
    g.fillText(`${Math.round(v)}${i === 5 ? ` ${xlabel}` : ''}`, Math.min(X(v), w - R - 14), h - 7);
  }
  g.setLineDash([5, 4]);
  g.strokeStyle = css('--text-secondary');
  for (const v of [hline, hline2])
    if (Number.isFinite(v) && v >= ymin && v <= ymax) {
      g.beginPath();
      g.moveTo(L, Y(v));
      g.lineTo(w - R, Y(v));
      g.stroke();
    }
  g.setLineDash([]);
  if (Number.isFinite(vline)) {
    g.strokeStyle = css('--axis');
    g.beginPath();
    g.moveTo(X(vline), T);
    g.lineTo(X(vline), h - B);
    g.stroke();
  }
  g.strokeStyle = css('--accent');
  g.lineWidth = 1.6;
  g.beginPath();
  let pen = false;
  for (let i = 0; i < x.length; i++) {
    if (x[i] < xmin || x[i] > xmax) continue;
    const py = Y(Math.max(ymin, Math.min(ymax, y[i])));
    if (pen) g.lineTo(X(x[i]), py);
    else g.moveTo(X(x[i]), py);
    pen = true;
  }
  g.stroke();
}
