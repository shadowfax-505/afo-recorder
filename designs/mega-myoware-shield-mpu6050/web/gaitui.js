// The gait analysis panel: leg assignment and walk distance controls, headline
// tiles, a parameter table per leg, the shank angular velocity with detected
// events, and (for recordings) a per-stride table.
import { StripChart } from './chart.js';
import { strideFromWalk } from './gait.js';

const LEG_COLOR = { right: '--series-1', left: '--series-2' };
const SIDES = [
  ['right', 'Right shank'],
  ['left', 'Left shank'],
  ['off', 'Not on a leg'],
];

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

const ok = (v) => Number.isFinite(v);
function ms(x, d = 2, unit = '') {
  if (!x || !ok(x.mean)) return '–';
  return x.n > 1 && ok(x.sd) ? `${x.mean.toFixed(d)} ± ${x.sd.toFixed(d)}${unit}` : `${x.mean.toFixed(d)}${unit}`;
}
const num = (v, d = 2, unit = '') => (ok(v) ? `${v.toFixed(d)}${unit}` : '–');

// Rows: [label, note, per-leg formatter, combined formatter]
const ROWS = [
  ['Strides analysed', 'complete heel strike to heel strike', (s) => String(s.strides), (c) => String(c.strides)],
  ['Stride time (s)', 'Eq. 1: HS(i+1) − HS(i)', (s) => ms(s.strideT, 3), (c) => ms(c.strideT, 3)],
  ['Stance time (s)', 'Eq. 2: TO(i) − HS(i)', (s) => ms(s.stanceT, 3), (c) => ms(c.stanceT, 3)],
  ['Swing time (s)', 'Eq. 3: HS(i+1) − TO(i)', (s) => ms(s.swingT, 3), (c) => ms(c.swingT, 3)],
  ['Stance (% of stride)', '', (s) => ms(s.stancePct, 1), (c) => ms(c.stancePct, 1)],
  ['Swing (% of stride)', '', (s) => ms(s.swingPct, 1), (c) => ms(c.swingPct, 1)],
  ['Step time (s)', 'HS to the other leg’s HS; needs both legs', () => '', (c) => ms(c.stepT, 3)],
  ['Double support (% of stride)', 'both feet down; needs both legs', () => '', (c) => ms(c.doubleSupportPct, 1)],
  ['Cadence (steps/min)', 'from step time, or 2 × strides/min with one leg', (s) => num(2 * s.cadenceStrides, 1), (c) => num(c.cadenceSteps, 1)],
  ['Cadence (strides/min)', 'the paper’s definition', (s) => num(s.cadenceStrides, 1), (c) => num(c.cadenceStrides, 1)],
  ['Stride time variability (CV %)', '', (s) => num(s.strideCv, 1), () => ''],
  ['Stride length, sensor (m)', 'de-drifted integration at the ankle; estimate', (s) => ms(s.length, 2), (c) => ms(c.sensorLength, 2)],
  ['Stride velocity, sensor (m/s)', 'sensor stride length ÷ stride time; estimate', (s) => ms(s.speed, 2), (c) => ms(c.sensorSpeed, 2)],
  ['Stride length, person-scaled (m)', 'sensor estimate scaled so it averages to the person’s measured stride', (s) => ms(s.personLength, 2), (c) => ms(c.personLength, 2)],
  ['Stride velocity, person-scaled (m/s)', 'person-scaled stride length ÷ stride time', (s) => ms(s.personSpeed, 2), (c) => ms(c.personSpeed, 2)],
  ['Person’s measured stride length (m)', 'entered or measured for this person', () => '', (c) => num(c.personStrideM, 2)],
  ['Mean stride length, Eq. 4 (m)', 'walk distance ÷ strides; enter the distance', () => '', (c) => num(c.meanStrideLength, 2)],
  ['Gait speed (m/s)', 'walk distance ÷ walking time; enter the distance', () => '', (c) => num(c.gaitSpeed, 2)],
  ['Walking time (s)', 'first to last heel strike', () => '', (c) => num(c.walkTimeS, 1)],
  ['Symmetry index, stance / swing (%)', '0 = symmetric; needs both legs', () => '', (c) => (c.symmetry && ok(c.symmetry.stanceT) ? `${num(c.symmetry.stanceT, 1)} / ${num(c.symmetry.swingT, 1)}` : '–')],
];

export class GaitPanel {
  // opts: {live: bool, settings: {sides:{A,B}, distanceM, windowS, person, personStrideM},
  //        profiles: {list() -> [{name, strideM}], save(name, strideM)}, onChange(settings), onZoom}
  constructor(host, opts) {
    this.opts = opts;
    this.settings = structuredClone(opts.settings);
    this.result = null;
    this.root = el('section', { class: 'gait', 'aria-label': 'Gait analysis' });
    host.replaceChildren(this.root);

    const head = el(
      'div',
      { class: 'gait-head' },
      el('h2', {}, 'Gait analysis'),
      el(
        'p',
        { class: 'hint' },
        'Wear one IMU on each shank just above the outer ankle bone, stand still for 2 s, then walk. Events come from the shank’s angular velocity: toe-off (TO) is the dip before the swing peak, heel strike (HS) the dip after it.',
      ),
    );

    const sideSelect = (name) => {
      const s = el('select', { id: `${opts.idPrefix}-side-${name}` }, ...SIDES.map(([v, l]) => el('option', { value: v }, l)));
      s.value = this.settings.sides[name];
      s.addEventListener('change', () => {
        this.settings.sides[name] = s.value;
        this.changed();
      });
      return el('label', { class: 'field' }, `IMU ${name} (${name === 'A' ? '0x68' : '0x69'}) is on`, s);
    };
    const dist = el('input', { type: 'number', min: '0', step: '0.1', inputMode: 'decimal', placeholder: 'e.g. 10', id: `${opts.idPrefix}-distance` });
    dist.value = this.settings.distanceM || '';
    dist.addEventListener('change', () => {
      this.settings.distanceM = Math.max(0, Number(dist.value) || 0);
      this.changed();
    });
    const controls = el('div', { class: 'toolbar gait-controls' }, sideSelect('A'), sideSelect('B'), el('label', { class: 'field' }, 'Walk distance (m)', dist));
    if (opts.live) {
      const win = el(
        'select',
        { id: `${opts.idPrefix}-window` },
        ...[
          [10, 'Last 10 s'],
          [20, 'Last 20 s'],
          [30, 'Last 30 s'],
          [60, 'Last 60 s'],
          [0, 'Since Record was pressed'],
        ].map(([v, l]) => el('option', { value: String(v) }, l)),
      );
      win.value = String(this.settings.windowS ?? 20);
      win.addEventListener('change', () => {
        this.settings.windowS = Number(win.value);
        this.changed();
      });
      controls.append(el('label', { class: 'field' }, 'Analyse', win));
    }
    controls.append(el('p', { class: 'hint grow' }, 'The walk distance is the measured length walked in this stretch (for example 10 m in a 10 m walk test). It gives Eq. 4’s mean stride length and the gait speed.'));
    const person = this.buildPerson(opts);

    this.warn = el('ul', { class: 'notice gait-warn', hidden: true });
    this.tiles = el('div', { class: 'tiles gait-tiles' });
    this.table = el('table', { class: 'gait-table' });
    const tableWrap = el('div', { class: 'table-scroll' }, this.table);
    this.chartHost = el('div', { class: 'charts gait-charts' });
    this.chart = new StripChart(this.chartHost, {
      title: 'Shank sagittal angular velocity with events',
      unit: '°/s · ● HS · ■ TO',
      series: [],
      minSpan: 50,
      onZoom: opts.onZoom || null,
    });
    this.chart.el.classList.add('wide');
    this.root.append(head, controls, person, this.warn, this.tiles, tableWrap, this.chartHost);
    if (!opts.live) {
      this.strideBody = el('tbody');
      this.strideCsv = el('button', { type: 'button', id: `${opts.idPrefix}-csv` }, 'Export gait CSV');
      this.root.append(
        el(
          'details',
          { class: 'strides' },
          el('summary', {}, 'Every stride'),
          el('div', { class: 'actions' }, this.strideCsv),
          el(
            'div',
            { class: 'table-scroll' },
            el(
              'table',
              {},
              el('thead', {}, el('tr', {}, ...['Leg', '#', 'HS (s)', 'TO (s)', 'Stride (s)', 'Stance (s)', 'Swing (s)', 'Stance %', 'Length (m)', 'Velocity (m/s)', 'Person-scaled (m)'].map((h) => el('th', { class: h === 'Leg' ? '' : 'num' }, h)))),
              this.strideBody,
            ),
          ),
        ),
      );
    }
  }

  // Each person's stride length is their own: enter it, measure it with a
  // counted walk, or (on a recording with a walk distance) take Eq. 4's result.
  buildPerson(opts) {
    const p = opts.idPrefix;
    const profiles = opts.profiles || { list: () => [], save: () => {} };
    const list = el('datalist', { id: `${p}-people` });
    const fillList = () => list.replaceChildren(...profiles.list().map((x) => el('option', { value: x.name }, `${x.strideM.toFixed(2)} m`)));
    fillList();
    const name = el('input', { type: 'text', id: `${p}-person`, placeholder: 'e.g. Rafi', autocomplete: 'off' });
    name.setAttribute('list', list.id);
    name.value = this.settings.person || '';
    const stride = el('input', { type: 'number', min: '0', step: '0.01', inputMode: 'decimal', placeholder: 'e.g. 1.10', id: `${p}-stride` });
    stride.value = this.settings.personStrideM || '';
    const setStride = (v, save = true) => {
      this.settings.personStrideM = v > 0 ? Math.round(v * 1000) / 1000 : 0;
      stride.value = this.settings.personStrideM || '';
      if (save && this.settings.person && this.settings.personStrideM) {
        profiles.save(this.settings.person, this.settings.personStrideM);
        fillList();
      }
      this.changed();
    };
    this.setPersonStride = setStride;
    name.addEventListener('change', () => {
      this.settings.person = name.value.trim();
      const found = profiles.list().find((x) => x.name === this.settings.person);
      if (found) setStride(found.strideM, false);
      else if (this.settings.person && this.settings.personStrideM) setStride(this.settings.personStrideM);
      else this.changed();
    });
    stride.addEventListener('change', () => setStride(Math.max(0, Number(stride.value) || 0)));

    // counted-walk helper
    const dist = el('input', { type: 'number', min: '0', step: '0.1', inputMode: 'decimal', value: '10', id: `${p}-m-dist` });
    const steps = el('input', { type: 'number', min: '0', step: '1', inputMode: 'numeric', placeholder: 'e.g. 18', id: `${p}-m-steps` });
    const out = el('strong', { id: `${p}-m-out` }, '–');
    const use = el('button', { type: 'button', id: `${p}-m-use`, disabled: true }, 'Use this stride length');
    const calc = () => {
      const v = strideFromWalk(Number(dist.value), Number(steps.value));
      out.textContent = Number.isFinite(v) ? `${v.toFixed(2)} m per stride` : '–';
      use.disabled = !Number.isFinite(v);
      return v;
    };
    dist.addEventListener('input', calc);
    steps.addEventListener('input', calc);
    use.addEventListener('click', () => setStride(calc()));
    const measure = el(
      'details',
      { class: 'measure' },
      el('summary', {}, 'Measure it'),
      el('p', { class: 'hint' }, 'Mark a straight distance on the floor (10 m is easy), have the person walk it at their normal pace from a standing start, and count every step, left and right. One stride is two steps, so stride length = 2 × distance ÷ steps.'),
      el('div', { class: 'toolbar' }, el('label', { class: 'field' }, 'Distance walked (m)', dist), el('label', { class: 'field' }, 'Steps counted', steps), el('div', { class: 'field' }, 'Stride length', out), use),
    );
    this.eq4Btn = el('button', { type: 'button', id: `${p}-use-eq4`, hidden: true }, 'Save this recording’s Eq. 4 stride length for the person');
    this.eq4Btn.addEventListener('click', () => {
      const c = this.result && this.result.combined;
      if (c && Number.isFinite(c.meanStrideLength)) setStride(c.meanStrideLength);
    });
    return el(
      'div',
      { class: 'person' },
      el(
        'div',
        { class: 'toolbar' },
        el('label', { class: 'field' }, 'Person', name, list),
        el('label', { class: 'field' }, 'Their stride length (m)', stride),
        el('p', { class: 'hint grow' }, 'Stride length differs from person to person. Enter it once (or measure it below) and it is kept for that name in this browser. It sets the stride length and gait speed when no walk distance is given, and scales the sensor’s stride-by-stride estimate.'),
        this.eq4Btn,
      ),
      measure,
    );
  }

  changed() {
    if (this.opts.onChange) this.opts.onChange(structuredClone(this.settings));
  }

  set hidden(v) {
    this.root.hidden = v;
  }

  render(result) {
    this.result = result;
    const c = result && result.combined;
    const legs = result ? result.legs : {};
    const names = Object.keys(legs);

    // warnings: shared ones plus each leg's own
    const warnings = [...(result ? result.warnings : [])];
    for (const k of names) for (const w of legs[k].warnings) warnings.push(`${label(k)}: ${w}`);
    if (!names.length && result && result.fs > 0) warnings.push('Set which shank each IMU is on. IMUs that are missing or set to “Not on a leg” are skipped.');
    this.warn.replaceChildren(...[...new Set(warnings)].map((w) => el('li', {}, w)));
    this.warn.hidden = !warnings.length;

    // headline tiles: stride length and speed from the best source available
    const SRC = { eq4: ['Eq. 4', 'distance ÷ time'], person: ['person’s stride', 'person’s stride ÷ stride time'], sensor: ['sensor estimate', 'sensor estimate'] };
    const lenSrc = c && c.strideLength.source ? SRC[c.strideLength.source][0] : 'enter a distance or stride';
    const spdSrc = c && c.speed.source ? SRC[c.speed.source][1] : 'enter a distance or stride';
    const tiles = [
      ['Cadence', c ? num(c.cadenceSteps, 0) : '–', 'steps per minute'],
      ['Gait speed', c ? num(c.speed.value, 2) : '–', `m/s · ${spdSrc}`],
      ['Mean stride length', c ? num(c.strideLength.value, 2) : '–', `m · ${lenSrc}`],
      ['Stride time', c ? num(c.strideT.mean, 2) : '–', 's'],
      ['Stance / swing', c && ok(c.stancePct.mean) ? `${c.stancePct.mean.toFixed(0)} / ${c.swingPct.mean.toFixed(0)}` : '–', '% of stride'],
      ['Double support', c ? num(c.doubleSupportPct.mean, 0) : '–', '% of stride'],
    ];
    this.tiles.replaceChildren(...tiles.map(([l, v, s]) => el('div', { class: 'tile' }, el('span', { class: 'label' }, l), el('strong', {}, v), el('small', {}, s))));
    this.eq4Btn.hidden = !(c && ok(c.meanStrideLength) && this.settings.person);

    // parameter table
    const cols = names.map((k) => [label(k), c.perLeg[k]]);
    const head = el('tr', {}, el('th', {}, 'Parameter'), ...cols.map(([l]) => el('th', { class: 'num' }, l)), el('th', { class: 'num' }, names.length > 1 ? 'Both legs' : 'All strides'));
    const body = ROWS.map(([lab, note, perLeg, both]) =>
      el(
        'tr',
        {},
        el('th', { scope: 'row' }, lab, note ? el('small', {}, note) : null),
        ...cols.map(([, s]) => el('td', { class: 'num' }, perLeg(s) || '')),
        el('td', { class: 'num' }, c ? both(c) || '' : '–'),
      ),
    );
    this.table.replaceChildren(el('thead', {}, head), el('tbody', {}, ...body));

    // chart
    const T = result && result.t;
    const series = names.map((k, i) => ({ key: i, label: label(k), color: LEG_COLOR[legs[k].side] || '--series-3' }));
    this.chart.setSeries(series);
    this.chart.markers = names.flatMap((k) => {
      const color = LEG_COLOR[legs[k].side] || '--series-3';
      return legs[k].strides.flatMap((s, i, a) => [
        { t: s.hs, color },
        { t: s.to, color, dashed: true },
        ...(i === a.length - 1 ? [{ t: s.hsNext, color }] : []),
      ]);
    });
    this.src = T ? { n: T.length, t: (i) => T[i], v: (key, i) => legs[names[key]].w[i] } : { n: 0, t: () => 0, v: () => NaN };
    this.chart.el.hidden = !names.length;
    this.draw();

    if (this.strideBody) {
      const rows = [];
      for (const k of names)
        legs[k].strides.forEach((s, i) =>
          rows.push(
            el(
              'tr',
              {},
              el('td', {}, label(k)),
              ...[i + 1, s.hs.toFixed(3), s.to.toFixed(3), s.strideT.toFixed(3), s.stanceT.toFixed(3), s.swingT.toFixed(3), s.stancePct.toFixed(1), num(s.length, 2), num(s.speed, 2), num(s.personLength, 2)].map((v) => el('td', { class: 'num' }, String(v))),
            ),
          ),
        );
      this.strideBody.replaceChildren(...rows);
    }
  }

  // t0/t1: visible range; defaults to the analysed stretch
  draw(t0, t1) {
    if (this.chart.el.hidden || !this.src || !this.src.n) return;
    const a = t0 ?? this.src.t(0);
    const b = t1 ?? this.src.t(this.src.n - 1);
    this.chart.draw(this.src, a, Math.max(b, a + 0.001), 3.5 / (this.result.fs || 100));
  }
}

function label(k) {
  const [side, imu] = k.split('-');
  const s = side === 'right' ? 'Right' : side === 'left' ? 'Left' : side;
  return imu ? `${s} (IMU ${imu})` : s;
}
