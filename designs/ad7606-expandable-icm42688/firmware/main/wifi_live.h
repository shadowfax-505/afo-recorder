#pragma once
#include "format.h"
#include "esp_err.h"
// Call before battery_init() (ADC) and wifi_live_init(): loads or creates the
// per-device access-point password in NVS.
esp_err_t wifi_live_prepare_credentials(void);
esp_err_t wifi_live_init(void);
void wifi_live_begin(const char *metadata);
void wifi_live_offer(const afo_record_t *record);
