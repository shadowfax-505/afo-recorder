// Synthetic digital edges for testing the instrument itself, not recorder evidence.
#define PROBE_HOST_TEST
#include "probe.chip.c"

typedef struct { uint64_t time; unsigned pin, value, order; } event_t;
#define N_FRAMES 128
static event_t events[65000];
static unsigned event_count, pin_count;
static uint64_t virtual_now;
static unsigned values[N_PINS];
static pin_watch_config_t watchers[N_PINS];
static timer_config_t report_timer;

uint64_t get_sim_nanos(void) { return virtual_now; }
pin_t pin_init(const char *name, uint32_t mode) {
  (void)name; if (mode != INPUT) abort();
  return pin_count++;
}
uint32_t pin_read(pin_t pin) { return values[pin]; }
bool pin_watch(pin_t pin, pin_watch_config_t *watch) { watchers[pin] = *watch; return true; }
timer_t timer_init(timer_config_t *timer) { report_timer = *timer; return 1; }
void timer_start(timer_t timer, uint32_t micros, bool repeat) {
  if (timer != 1 || micros != 2000 || repeat) abort();
}
static void add(uint64_t time, unsigned pin, unsigned value) {
  if (event_count >= sizeof(events) / sizeof(events[0])) abort();
  events[event_count] = (event_t){time, pin, value, event_count}; event_count++;
}
static int order(const void *a, const void *b) {
  const event_t *x = a, *y = b;
  if (x->time != y->time) return x->time < y->time ? -1 : 1;
  return x->order < y->order ? -1 : x->order != y->order;
}

static void adc_read(uint64_t trigger, bool prime, const char *fault, unsigned frame) {
  const int16_t golden[8] = {6554, 13107, -1234, 2345, -32768, 32767, 0, 1111};
  uint64_t start = trigger + 5000;
  if (!prime) {
    // Reverse same-time callback order in one case to test model/observer ordering.
    if (!strcmp(fault, "busy-first")) add(trigger, BUSY, 1);
    add(trigger, CONVST, 1);
    if (strcmp(fault, "busy-first") && strcmp(fault, "missing-busy")) add(trigger, BUSY, 1);
    add(trigger + 1000, CONVST, 0);
    if (strcmp(fault, "missing-busy")) add(trigger + (!strcmp(fault, "read-busy") ? 50000 : 4000), BUSY, 0);
  }
  if (!strcmp(fault, "wrong-idle") && !prime && frame == 1) add(start - 1, SCLK, 0);
  add(start, CS, 0);
  unsigned bits = (!strcmp(fault, "short-clock") && frame == 1 && !prime) ? 127 : 128;
  unsigned period = (!strcmp(fault, "slow-clock") && !prime) ? 250 : 125;
  for (unsigned bit = 0; bit < bits; bit++) {
    unsigned word = bit / 16;
    if (!strcmp(fault, "swapped-words") && !prime && word < 2) word = 1 - word;
    unsigned v = ((uint16_t)golden[word] >> (15 - bit % 16)) & 1;
    add(start + 90 + period * bit, DOUTA, v);
    add(start + 100 + period * bit, SCLK, 0);
    add(start + 162 + period * bit, SCLK, 1);
  }
  if (strcmp(fault, "partial-frame") || prime || frame != N_FRAMES) add(start + period * 128 + 200, CS, 1);
}

int main(int argc, char **argv) {
  const char *fault = argc > 1 ? argv[1] : "normal";
  values[CS] = values[SCLK] = values[RESET] = 1;
  if (!strcmp(fault, "prime-reset")) values[RESET] = 0;
  chip_init();
  adc_read(100000, true, fault, 0); add(200000, RESET, 0);
  if (strcmp(fault, "missing-prime")) {
    add(300000, RESET, !strcmp(fault, "prime-reset") ? 0 : 1);
    adc_read(310000, true, fault, 0); add(350000, RESET, 0);
  }
  unsigned period = !strcmp(fault, "slow-trigger") ? 140000 : 125000;
  for (unsigned i = 0; i < N_FRAMES; i++) adc_read(10000000 + (uint64_t)i * period, false, fault, i + 1);
  uint64_t last = 10000000 + (N_FRAMES - 1) * period;
  for (unsigned identity = 0; identity < 2; identity++) {
    if (!strcmp(fault, "missing-foot-irq") && !identity) continue;
    for (uint64_t t = 12500000 + identity * 500000; t < last; t += 5000000) {
      add(t, FOOT_IRQ + identity, 1); add(t + 10000, FOOT_IRQ + identity, 0);
    }
  }
  qsort(events, event_count, sizeof(event_t), order);
  for (unsigned i = 0; i < event_count; i++) {
    const event_t *e = &events[i]; virtual_now = e->time;
    if (values[e->pin] == e->value) continue;
    values[e->pin] = e->value;
    watchers[e->pin].pin_change(watchers[e->pin].user_data, e->pin, e->value);
  }
  virtual_now = last + 2000000;
  report_timer.callback(report_timer.user_data);
  if (!strcmp(fault, "late-trigger")) {
    virtual_now += 125000; values[CONVST] = 1;
    watchers[CONVST].pin_change(watchers[CONVST].user_data, CONVST, 1);
  }
  return 0;
}
