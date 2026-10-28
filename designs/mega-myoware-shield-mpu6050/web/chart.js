// Canvas strip chart: one y-axis, thin lines, a legend, a hover crosshair
// with a tooltip, and optional drag-to-zoom. Works on any source exposing
// {n, t(i), v(key, i)} with t ascending, so the live ring buffer and a loaded
// recording share the same drawing code.

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function lowerBound(src, t) {
  let lo = 0;
  let hi = src.n;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (src.t(mid) < t) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

function niceStep(span, target) {
  const raw = span / Math.max(1, target);
  const mag = 10 ** Math.floor(Math.log10(raw));
  const f = raw / mag;
  return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * mag;
}

function fmt(v, step) {
  const d = step >= 1 ? 0 : Math.min(4, Math.ceil(-Math.log10(step)));
  return v.toFixed(d);
}

const fmtValue = (v, unit) => (Number.isNaN(v) ? '–' : v.toFixed(unit === 'counts' ? 0 : 3));

export class StripChart {
  constructor(host, { title, unit, series, minSpan = 1, fixed = null, onZoom = null }) {
    this.title = title;
    this.unit = unit;
    this.series = series; // [{key, label, color: '--series-1'}]
    this.minSpan = minSpan;
    this.fixed = fixed; // [min, max] or null for auto
    this.onZoom = onZoom;
    this.hoverX = null;
    this.drag = null;
    this.last = null;

    this.el = document.createElement('figure');
    this.el.className = 'chart';
    const head = document.createElement('figcaption');
    const h = document.createElement('h3');
    h.textContent = title;
    const u = document.createElement('span');
    u.className = 'unit';
    u.textContent = unit;
    h.append(' ', u);
    this.legend = document.createElement('div');
    this.legend.className = 'legend';
    head.append(h, this.legend);
    this.wrap = document.createElement('div');
    this.wrap.className = 'plot';
    this.canvas = document.createElement('canvas');
    this.tip = document.createElement('div');
    this.tip.className = 'tip';
    this.tip.hidden = true;
    this.wrap.append(this.canvas, this.tip);
    this.el.append(head, this.wrap);
    host.append(this.el);
    this.setSeries(series);

    this.canvas.addEventListener('pointermove', (e) => {
      const r = this.canvas.getBoundingClientRect();
      this.hoverX = e.clientX - r.left;
      if (this.drag) this.drag.x1 = this.hoverX;
      this.redraw();
    });
    this.canvas.addEventListener('pointerleave', () => {
      this.hoverX = null;
      this.tip.hidden = true;
      this.redraw();
    });
    if (onZoom) {
      this.canvas.classList.add('zoomable');
      this.canvas.addEventListener('pointerdown', (e) => {
        const r = this.canvas.getBoundingClientRect();
        this.drag = { x0: e.clientX - r.left, x1: e.clientX - r.left };
        this.canvas.setPointerCapture(e.pointerId);
      });
      this.canvas.addEventListener('pointerup', () => {
        const d = this.drag;
        this.drag = null;
        if (!d || !this.last || Math.abs(d.x1 - d.x0) < 6) return this.redraw();
        const { tMin, tMax, plot } = this.last;
        const toT = (x) => tMin + ((x - plot.x) / plot.w) * (tMax - tMin);
        const a = toT(Math.max(plot.x, Math.min(d.x0, d.x1)));
        const b = toT(Math.min(plot.x + plot.w, Math.max(d.x0, d.x1)));
        if (b > a) this.onZoom(a, b);
      });
      this.canvas.addEventListener('dblclick', () => this.onZoom(null, null));
    }
  }

  setSeries(series) {
    this.series = series;
    this.legend.replaceChildren(
      ...series.map((s) => {
        const item = document.createElement('span');
        const sw = document.createElement('i');
        sw.style.background = `var(${s.color})`;
        item.append(sw, s.label);
        return item;
      }),
    );
    this.legend.hidden = series.length < 2;
  }

  set hidden(v) {
    this.el.hidden = v;
  }

  redraw() {
    if (this.last) this.draw(this.last.src, this.last.tMin, this.last.tMax, this.last.gapS);
  }

  draw(src, tMin, tMax, gapS = Infinity) {
    const c = this.canvas;
    const dpr = window.devicePixelRatio || 1;
    const W = c.clientWidth;
    const H = c.clientHeight;
    if (!W || !H) return;
    if (c.width !== Math.round(W * dpr) || c.height !== Math.round(H * dpr)) {
      c.width = Math.round(W * dpr);
      c.height = Math.round(H * dpr);
    }
    const g = c.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, W, H);
    const plot = { x: 52, y: 8, w: W - 52 - 10, h: H - 8 - 22 };
    this.last = { src, tMin, tMax, gapS, plot };
    if (tMax <= tMin) tMax = tMin + 1;

    const i0 = Math.max(0, lowerBound(src, tMin) - 1);
    const i1 = Math.min(src.n, lowerBound(src, tMax) + 1);

    // y range
    let lo = Infinity;
    let hi = -Infinity;
    if (this.fixed) [lo, hi] = this.fixed;
    else {
      for (const s of this.series)
        for (let i = i0; i < i1; i++) {
          const v = src.v(s.key, i);
          if (v < lo) lo = v;
          if (v > hi) hi = v;
        }
      if (!isFinite(lo)) [lo, hi] = [-this.minSpan / 2, this.minSpan / 2];
      if (hi - lo < this.minSpan) {
        const mid = (hi + lo) / 2;
        lo = mid - this.minSpan / 2;
        hi = mid + this.minSpan / 2;
      }
      const pad = (hi - lo) * 0.08;
      lo -= pad;
      hi += pad;
    }
    const X = (t) => plot.x + ((t - tMin) / (tMax - tMin)) * plot.w;
    const Y = (v) => plot.y + plot.h - ((v - lo) / (hi - lo)) * plot.h;

    // grid and axes
    g.font = '11px system-ui, -apple-system, "Segoe UI", sans-serif';
    g.textBaseline = 'middle';
    g.lineWidth = 1;
    const yStep = niceStep(hi - lo, Math.max(2, Math.floor(plot.h / 34)));
    g.fillStyle = css('--text-muted');
    g.textAlign = 'right';
    for (let v = Math.ceil(lo / yStep) * yStep; v <= hi; v += yStep) {
      const y = Math.round(Y(v)) + 0.5;
      g.strokeStyle = Math.abs(v) < yStep / 1e6 ? css('--axis') : css('--grid');
      g.beginPath();
      g.moveTo(plot.x, y);
      g.lineTo(plot.x + plot.w, y);
      g.stroke();
      g.fillText(fmt(v, yStep), plot.x - 6, y);
    }
    const tStep = niceStep(tMax - tMin, Math.max(2, Math.floor(plot.w / 90)));
    g.textAlign = 'center';
    g.textBaseline = 'top';
    for (let t = Math.ceil(tMin / tStep) * tStep; t <= tMax; t += tStep) {
      g.fillText(`${fmt(t, tStep)} s`, X(t), plot.y + plot.h + 6);
    }
    g.strokeStyle = css('--axis');
    g.beginPath();
    g.moveTo(plot.x, plot.y + plot.h + 0.5);
    g.lineTo(plot.x + plot.w, plot.y + plot.h + 0.5);
    g.stroke();

    // lines
    g.save();
    g.beginPath();
    g.rect(plot.x, plot.y, plot.w, plot.h);
    g.clip();
    g.lineWidth = 1.5;
    g.lineJoin = 'round';
    const dense = i1 - i0 > plot.w * 2;
    for (const s of this.series) {
      g.strokeStyle = css(s.color);
      g.beginPath();
      if (dense) {
        // min/max per pixel column
        let col = -1;
        let mn = 0;
        let mx = 0;
        let prevT = -Infinity;
        let penUp = true;
        const flush = () => {
          if (col < 0) return;
          g.lineTo(col, Y(mn));
          g.lineTo(col, Y(mx));
        };
        for (let i = i0; i < i1; i++) {
          const t = src.t(i);
          const v = src.v(s.key, i);
          if (Number.isNaN(v)) {
            flush();
            col = -1;
            penUp = true;
            continue;
          }
          const x = Math.floor(X(t));
          if (penUp || t - prevT > gapS) {
            flush();
            col = -1;
            g.moveTo(x, Y(v));
            penUp = false;
          }
          prevT = t;
          if (x !== col) {
            flush();
            col = x;
            mn = mx = v;
          } else {
            if (v < mn) mn = v;
            if (v > mx) mx = v;
          }
        }
        flush();
      } else {
        let prevT = -Infinity;
        let penUp = true;
        for (let i = i0; i < i1; i++) {
          const t = src.t(i);
          const v = src.v(s.key, i);
          if (Number.isNaN(v)) {
            penUp = true; // channel was off for this sample
            continue;
          }
          if (penUp || t - prevT > gapS) g.moveTo(X(t), Y(v));
          else g.lineTo(X(t), Y(v));
          penUp = false;
          prevT = t;
        }
      }
      g.stroke();
    }
    g.restore();

    // drag selection
    if (this.drag) {
      g.fillStyle = css('--select');
      const a = Math.min(this.drag.x0, this.drag.x1);
      g.fillRect(a, plot.y, Math.abs(this.drag.x1 - this.drag.x0), plot.h);
    }

    // hover crosshair + tooltip
    const hx = this.hoverX;
    if (hx === null || hx < plot.x || hx > plot.x + plot.w || i1 <= i0) {
      this.tip.hidden = true;
      return;
    }
    const tq = tMin + ((hx - plot.x) / plot.w) * (tMax - tMin);
    let k = lowerBound(src, tq);
    if (k >= src.n) k = src.n - 1;
    if (k > 0 && Math.abs(src.t(k - 1) - tq) < Math.abs(src.t(k) - tq)) k--;
    const x = Math.round(X(src.t(k))) + 0.5;
    g.strokeStyle = css('--axis');
    g.beginPath();
    g.moveTo(x, plot.y);
    g.lineTo(x, plot.y + plot.h);
    g.stroke();
    for (const s of this.series) {
      if (Number.isNaN(src.v(s.key, k))) continue;
      g.fillStyle = css(s.color);
      g.strokeStyle = css('--surface-1');
      g.lineWidth = 2;
      g.beginPath();
      g.arc(x, Y(src.v(s.key, k)), 4, 0, Math.PI * 2);
      g.fill();
      g.stroke();
    }
    const rows = this.series
      .map((s) => `<div><i style="background:var(${s.color})"></i>${s.label}<b>${fmtValue(src.v(s.key, k), this.unit)}</b></div>`)
      .join('');
    this.tip.innerHTML = `<div class="tip-t">${src.t(k).toFixed(3)} s</div>${rows}`;
    this.tip.hidden = false;
    const tw = this.tip.offsetWidth;
    this.tip.style.left = `${x + 12 + tw > W ? x - 12 - tw : x + 12}px`;
    this.tip.style.top = `${plot.y + 4}px`;
  }
}
