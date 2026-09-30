// Independent native checks of the current Wokwi chip source, not MCU or WASM execution.
#include "../chips/wokwi-api.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned levels[32], pin_count, attribute_count, attributes[16], timer_count;
static pin_watch_config_t watchers[32];
static timer_config_t timer_configurations[8];
static unsigned timer_duration[8], timer_starts[8];
static bool timer_active[8];
static spi_config_t spi_configuration;
static uint8_t *spi_bytes;
static uint32_t spi_count;

pin_t pin_init(const char *name, uint32_t mode) {
    (void)name; assert(pin_count < 32); pin_t pin = pin_count++;
    levels[pin] = mode == INPUT_PULLUP || mode == OUTPUT_HIGH; return pin;
}
uint32_t pin_read(pin_t pin) { assert(pin >= 0 && pin < 32); return levels[pin]; }
void pin_write(pin_t pin, uint32_t value) { assert(pin >= 0 && pin < 32); levels[pin] = value; }
bool pin_watch(pin_t pin, const pin_watch_config_t *configuration) {
    watchers[pin] = *configuration; return true;
}
spi_dev_t spi_init(const spi_config_t *configuration) { spi_configuration = *configuration; return 1; }
void spi_start(spi_dev_t spi, uint8_t *bytes, uint32_t count) {
    assert(spi == 1); spi_bytes = bytes; spi_count = count;
}
void spi_stop(spi_dev_t spi) { assert(spi == 1); spi_bytes = NULL; spi_count = 0; }
uint32_t attr_init(const char *name, uint32_t value) {
    (void)name; assert(attribute_count < 16); attributes[attribute_count] = value; return attribute_count++;
}
uint32_t attr_read(uint32_t attribute) { assert(attribute < attribute_count); return attributes[attribute]; }
timer_t timer_init(const timer_config_t *configuration) {
    assert(timer_count < 8); timer_configurations[timer_count] = *configuration; return timer_count++;
}
void timer_start(timer_t timer, uint32_t microseconds, bool repeat) {
    assert(timer < timer_count && !repeat); timer_duration[timer] = microseconds;
    timer_active[timer] = true; timer_starts[timer]++;
}
void timer_stop(timer_t timer) { assert(timer < timer_count); timer_active[timer] = false; }

#include "../chips/ad7606.chip.c"

static void drive(pin_t pin, unsigned value) {
    if (levels[pin] == value) return;
    levels[pin] = value; assert(watchers[pin].pin_change);
    watchers[pin].pin_change(watchers[pin].user_data, pin, value);
}
static void pulse(chip_t *chip) { drive(chip->conv, 0); drive(chip->conv, 1); drive(chip->conv, 0); }
static void expire(chip_t *chip) {
    assert(timer_active[chip->timer]); timer_active[chip->timer] = false;
    timer_configurations[chip->timer].callback(timer_configurations[chip->timer].user_data);
}
static void reset_model(chip_t *chip) {
    drive(chip->cs, 1); drive(chip->conv, 0); drive(chip->reset, 0); drive(chip->reset, 1); drive(chip->reset, 0);
    attributes[chip->fault] = 0; attributes[chip->waveform] = 0;
    assert(!pin_read(chip->busy) && !timer_active[chip->timer] && chip->sample == 0);
}
static void read_words(chip_t *chip, int16_t words[8]) {
    drive(chip->cs, 1); drive(chip->cs, 0); assert(spi_count == 16 && spi_bytes);
    for (unsigned i = 0; i < 8; i++) words[i] = (int16_t)(((uint16_t)spi_bytes[2 * i] << 8) | spi_bytes[2 * i + 1]);
    drive(chip->cs, 1); assert(spi_bytes == NULL && spi_count == 0);
}

int main(void) {
    chip_init(); chip_t *chip = spi_configuration.user_data; assert(chip);
    assert(spi_configuration.mode == 2 && spi_configuration.mosi == NO_PIN);
    puts("PASS custom chip initializes the single-output SPI mode-2 interface");

    reset_model(chip); pulse(chip);
    assert(pin_read(chip->busy) && timer_duration[chip->timer] == 4); expire(chip); assert(!pin_read(chip->busy));
    puts("PASS normal conversion asserts BUSY and its 4us completion clears it");

    int16_t words[8]; read_words(chip, words);
    const int16_t expected[8] = {6554, 13107, -1234, 2345, -32768, 32767, 0, 1111};
    assert(memcmp(words, expected, sizeof(words)) == 0);
    puts("PASS all eight signed serial words preserve byte order and channel identity");

    reset_model(chip); attributes[chip->waveform] = 1; pulse(chip); assert(chip->sample == 1);
    unsigned starts = timer_starts[chip->timer]; pulse(chip);
    assert(chip->sample == 1 && timer_starts[chip->timer] == starts); expire(chip);
    read_words(chip, words); assert(words[0] == emg_stimulus[0][0] && words[1] == emg_stimulus[1][0]);
    puts("PASS a second trigger while BUSY is high cannot advance the waveform");

    reset_model(chip); attributes[chip->waveform] = 1; attributes[chip->fault] = 4;
    starts = timer_starts[chip->timer]; pulse(chip);
    assert(!pin_read(chip->busy) && chip->sample == 1 && timer_starts[chip->timer] == starts + 1);
    assert(timer_active[chip->timer] && timer_duration[chip->timer] == 4);
    read_words(chip, words); assert(words[0] == emg_stimulus[0][0] && words[1] == emg_stimulus[1][0]); expire(chip);
    puts("PASS stuck-low BUSY fault still advances converter data without an observable BUSY pulse");

    reset_model(chip); attributes[chip->waveform] = 1; pulse(chip); expire(chip); read_words(chip, words);
    int16_t previous[8]; memcpy(previous, words, sizeof(words)); attributes[chip->fault] = 5;
    starts = timer_starts[chip->timer]; pulse(chip); read_words(chip, words);
    assert(!pin_read(chip->busy) && !timer_active[chip->timer] && timer_starts[chip->timer] == starts);
    assert(chip->sample == 1 && memcmp(words, previous, sizeof(words)) == 0);
    puts("PASS ignored CONVST leaves BUSY low and retains plausible stale waveform words");

    attributes[chip->fault] = 0; pulse(chip); expire(chip); read_words(chip, words);
    assert(chip->sample == 2 && words[0] == emg_stimulus[0][1] && words[1] == emg_stimulus[1][1]);
    puts("PASS removing ignored-trigger fault permits the next ordered waveform sample");

    reset_model(chip); attributes[chip->waveform] = 1;
    pulse(chip); expire(chip); read_words(chip, words);
    assert(chip->sample == 1 && words[0] == emg_stimulus[0][0] && words[1] == emg_stimulus[1][0]);
    puts("PASS RESET stops the completion timer and restarts waveform indexing");

    for (unsigned i = 1; i <= STIMULUS_SAMPLES; i++) {
        pulse(chip); expire(chip); read_words(chip, words);
        assert(words[0] == emg_stimulus[0][i % STIMULUS_SAMPLES]);
        assert(words[1] == emg_stimulus[1][i % STIMULUS_SAMPLES]);
        for (unsigned channel = 2; channel < 8; channel++) assert(words[channel] == 0);
    }
    puts("PASS full stimulus table and rollover retain two-channel order and zero unused model inputs");

    reset_model(chip); attributes[chip->fault] = 1; pulse(chip);
    assert(pin_read(chip->busy) && !timer_active[chip->timer]); pulse(chip);
    assert(pin_read(chip->busy) && !timer_active[chip->timer]);
    puts("PASS stuck-high BUSY fault has no scheduled completion");

    reset_model(chip); attributes[chip->fault] = 2; pulse(chip);
    assert(pin_read(chip->busy) && timer_active[chip->timer] && timer_duration[chip->timer] == 250); expire(chip);
    assert(!pin_read(chip->busy)); puts("PASS delayed conversion schedules exactly 250us BUSY");

    reset_model(chip); attributes[chip->fault] = 3; read_words(chip, words);
    for (unsigned i = 0; i < 8; i++) assert(words[i] == -1);
    puts("PASS wrong serial-mode model returns plausible signed minus-one codes");
    free(chip); return 0;
}
