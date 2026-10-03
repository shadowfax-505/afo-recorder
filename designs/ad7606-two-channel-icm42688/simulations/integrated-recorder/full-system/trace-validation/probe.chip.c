// Observes simulator pins. No output drivers, pull-ups or sensor callbacks.
// Project-authored instrument: this is not a manufacturer validation model.
#ifdef PROBE_HOST_TEST
#include "probe_test_api.h"
#else
#include "wokwi-api.h"
#endif
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { CONVST, BUSY, CS, SCLK, DOUTA, FOOT_IRQ, SHANK_IRQ, FOOT_CS, RESET, N_PINS };
static const char *names[N_PINS] = {
  "CONVST", "BUSY", "CS", "SCLK", "DOUTA", "FOOT_IRQ", "SHANK_IRQ", "FOOT_CS", "RESET"
};
static const int16_t known[8] = {6554, 13107, -1234, 2345, -32768, 32767, 0, 1111};

typedef struct { uint64_t count, lo, hi, sum; } metric_t;
typedef struct {
  uint64_t trigger, busy_end, start, end, previous_fall;
  unsigned number, falls, rises;
  bool active, prime;
  uint16_t words[8];
} frame_t;
typedef struct {
  pin_t pins[N_PINS];
  uint32_t levels[N_PINS];
  timer_t idle;
  uint64_t first_trigger, last_trigger, conv_start, busy_start, last_busy_end;
  uint64_t irq_start[2], irq_previous[2], irq_times[2][2048];
  unsigned irq_count[2], triggers, reads, primes, pending, reported;
  unsigned bad_clocks, bad_words, busy_reads, missing_busy, overlaps;
  unsigned idle_errors, reset_prime_errors, watch_errors, late_triggers;
  metric_t periods, conv_width, busy_width, clock_period, irq_period[2], irq_width[2];
  frame_t frame, last_frames[2];
} probe_t;

static void observe(metric_t *m, uint64_t value) {
  if (!m->count || value < m->lo) m->lo = value;
  if (!m->count || value > m->hi) m->hi = value;
  m->sum += value; m->count++;
}

static void show_frame(const frame_t *f) {
  printf("PROBE_FRAME,{\"number\":%u,\"trigger_ns\":%" PRIu64
    ",\"busy_end_ns\":%" PRIu64 ",\"cs_start_ns\":%" PRIu64
    ",\"cs_end_ns\":%" PRIu64 ",\"falls\":%u,\"rises\":%u,\"words\":[",
    f->number, f->trigger, f->busy_end, f->start, f->end, f->falls, f->rises);
  for (unsigned i = 0; i < 8; i++) printf("%s%d", i ? "," : "", (int16_t)f->words[i]);
  printf("]}\n");
}

static unsigned window_irqs(const probe_t *s, unsigned identity) {
  unsigned n = 0;
  for (unsigned i = 0; i < s->irq_count[identity] && i < 2048; i++) {
    uint64_t t = s->irq_times[identity][i];
    if (t >= s->first_trigger && t <= s->last_trigger) n++;
  }
  return n;
}

static void show_metric(const char *name, const metric_t *m) {
  printf(",\"%s\":{\"count\":%" PRIu64 ",\"min\":%" PRIu64
    ",\"max\":%" PRIu64 ",\"sum\":%" PRIu64 "}", name, m->count, m->lo, m->hi, m->sum);
}

static void report(void *data) {
  probe_t *s = data;
  if (s->reported) return;
  s->reported = 1;
  if (s->reads > 3) show_frame(&s->last_frames[(s->reads - 2) % 2]);
  if (s->reads == 3) show_frame(&s->last_frames[(s->reads - 1) % 2]);
  if (s->reads > 3) show_frame(&s->last_frames[(s->reads - 1) % 2]);
  printf("PROBE_SUMMARY,{\"version\":1,\"hardware_measured\":false,\"drives_outputs\":false,"
    "\"idle_report_us\":2000,\"report_ns\":%" PRIu64 ",\"first_trigger_ns\":%" PRIu64
    ",\"last_trigger_ns\":%" PRIu64 ",\"triggers\":%u,\"reads\":%u,\"priming_reads\":%u,"
    "\"pending\":%u,\"partial_frame\":%s,\"bad_clocks\":%u,\"bad_words\":%u,"
    "\"read_while_busy\":%u,\"missing_busy\":%u,\"overlapping_conversions\":%u,"
    "\"wrong_idle_clock\":%u,\"prime_outside_reset\":%u,\"watch_failures\":%u,"
    "\"foot_irq_total\":%u,\"shank_irq_total\":%u,\"foot_irq_window\":%u,\"shank_irq_window\":%u",
    get_sim_nanos(), s->first_trigger, s->last_trigger, s->triggers, s->reads, s->primes,
    s->pending, s->frame.active ? "true" : "false", s->bad_clocks, s->bad_words,
    s->busy_reads, s->missing_busy, s->overlaps, s->idle_errors, s->reset_prime_errors,
    s->watch_errors, s->irq_count[0], s->irq_count[1], window_irqs(s, 0), window_irqs(s, 1));
  show_metric("trigger_period_ns", &s->periods);
  show_metric("convst_width_ns", &s->conv_width);
  show_metric("busy_width_ns", &s->busy_width);
  show_metric("falling_clock_period_ns", &s->clock_period);
  show_metric("foot_irq_period_ns", &s->irq_period[0]);
  show_metric("shank_irq_period_ns", &s->irq_period[1]);
  show_metric("foot_irq_width_ns", &s->irq_width[0]);
  show_metric("shank_irq_width_ns", &s->irq_width[1]);
  printf("}\n");
}

static void change(void *data, pin_t pin, uint32_t value) {
  probe_t *s = data;
  unsigned index = 0;
  while (index < N_PINS && s->pins[index] != pin) index++;
  if (index == N_PINS || s->levels[index] == value) return;
  s->levels[index] = value;
  uint64_t now = get_sim_nanos();
  if (s->reported) {
    if (index == CONVST && value) {
      s->late_triggers++;
      printf("PROBE_LATE_TRIGGER,%" PRIu64 "\n", now);
    }
    return;
  }
  if (index == CONVST && value) {
    if (s->pending || s->frame.active) s->overlaps++;
    if (s->triggers) observe(&s->periods, now - s->last_trigger);
    else {
      s->first_trigger = now;
      printf("PROBE_INITIAL,{\"time_ns\":%" PRIu64 ",\"levels\":[", now);
      for (unsigned i = 0; i < N_PINS; i++) printf("%s%u", i ? "," : "", pin_read(s->pins[i]));
      printf("]}\n");
    }
    s->triggers++; s->pending = s->triggers;
    s->last_trigger = s->conv_start = now;
    timer_start(s->idle, 2000, false);
  }
  if (s->triggers && s->triggers <= 2) {
    printf("PROBE_EDGE,%" PRIu64 ",%s,%u\n", now, names[index], value);
  }
  if (index == CONVST && !value && s->triggers) {
    observe(&s->conv_width, now - s->conv_start);
    if (!pin_read(s->pins[BUSY])) s->missing_busy++;
  }
  if (index == BUSY) {
    if (value) s->busy_start = now;
    else if (s->busy_start) {
      observe(&s->busy_width, now - s->busy_start);
      s->last_busy_end = now; s->busy_start = 0;
    }
  }
  if (index == CS && !value) {
    if (s->frame.active) s->overlaps++;
    memset(&s->frame, 0, sizeof(s->frame));
    frame_t *f = &s->frame;
    f->active = true; f->prime = !s->triggers;
    f->number = s->pending; f->start = now;
    f->trigger = s->last_trigger; f->busy_end = s->last_busy_end;
    if (!pin_read(s->pins[SCLK])) s->idle_errors++;
    if (f->prime) {
      if (!pin_read(s->pins[RESET])) s->reset_prime_errors++;
    } else {
      if (pin_read(s->pins[BUSY])) s->busy_reads++;
      if (!s->pending || s->last_busy_end < s->last_trigger) s->missing_busy++;
    }
  }
  if (index == SCLK && s->frame.active) {
    frame_t *f = &s->frame;
    if (value) f->rises++;
    else {
      if (!f->prime && f->falls) observe(&s->clock_period, now - f->previous_fall);
      f->previous_fall = now;
      if (f->falls < 128) {
        unsigned word = f->falls / 16;
        f->words[word] = (uint16_t)((f->words[word] << 1) | pin_read(s->pins[DOUTA]));
      }
      f->falls++;
    }
  }
  if (index == CS && value && s->frame.active) {
    frame_t *f = &s->frame; f->end = now;
    if (f->falls != 128 || f->rises != 128) s->bad_clocks++;
    if (f->prime) s->primes++;
    else {
      for (unsigned i = 0; i < 8; i++) {
        if ((int16_t)f->words[i] != known[i]) { s->bad_words++; break; }
      }
      s->reads++; s->pending = 0;
      s->last_frames[(s->reads - 1) % 2] = *f;
      if (s->reads <= 2) show_frame(f);
    }
    f->active = false;
  }
  if (index == FOOT_IRQ || index == SHANK_IRQ) {
    unsigned identity = index - FOOT_IRQ;
    if (value) {
      unsigned n = s->irq_count[identity];
      if (n < 2048) s->irq_times[identity][n] = now;
      if (n) observe(&s->irq_period[identity], now - s->irq_previous[identity]);
      s->irq_previous[identity] = s->irq_start[identity] = now;
      s->irq_count[identity]++;
    } else if (s->irq_start[identity]) {
      observe(&s->irq_width[identity], now - s->irq_start[identity]);
      s->irq_start[identity] = 0;
    }
  }
}

void chip_init(void) {
  probe_t *s = calloc(1, sizeof(*s));
  timer_config_t timer = {.callback = report, .user_data = s};
  s->idle = timer_init(&timer);
  pin_watch_config_t watch = {.edge = BOTH, .pin_change = change, .user_data = s};
  for (unsigned i = 0; i < N_PINS; i++) {
    s->pins[i] = pin_init(names[i], INPUT);
    s->levels[i] = pin_read(s->pins[i]);
    if (!pin_watch(s->pins[i], &watch)) s->watch_errors++;
  }
  printf("PROBE_INIT,{\"version\":1,\"pins\":9,\"drives_outputs\":false,\"watch_failures\":%u}\n", s->watch_errors);
}
