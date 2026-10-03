// Native event-replay harness only. Not shipped as a Wokwi sensor model.
#pragma once
#include <stdint.h>
#include <stdbool.h>
typedef uint32_t pin_t;
typedef uint32_t timer_t;
#define INPUT 0
#define BOTH 0
typedef struct { void (*callback)(void *); void *user_data; } timer_config_t;
typedef struct { uint32_t edge; void (*pin_change)(void *, pin_t, uint32_t); void *user_data; } pin_watch_config_t;
uint64_t get_sim_nanos(void);
pin_t pin_init(const char *, uint32_t);
uint32_t pin_read(pin_t);
bool pin_watch(pin_t, pin_watch_config_t *);
timer_t timer_init(timer_config_t *);
void timer_start(timer_t, uint32_t, bool);
