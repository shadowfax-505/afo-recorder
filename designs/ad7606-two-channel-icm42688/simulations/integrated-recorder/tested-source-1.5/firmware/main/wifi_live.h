#pragma once
#include "format.h"
#include "esp_err.h"
esp_err_t wifi_live_init(void);
void wifi_live_begin(const char *metadata);
void wifi_live_offer(const afo_record_t *record);
