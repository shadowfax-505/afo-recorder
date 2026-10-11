#pragma once
#include "variant.h"
#define ADC_CONVST 11

// Revision B ESP32-S3-WROOM-1-N8R8. Onboard LEDs, active high.
#define ADC_DRDY 8
#define ADC_RESET 9
#define USB_PRESENT_PIN 21
#ifndef EMG_CHANNEL_COUNT
#define EMG_CHANNEL_COUNT 2
#endif
#if EMG_CHANNEL_COUNT != 2
#error "This hardware has exactly two EMG inputs"
#endif
#define ADS_CLOCK_REG ((EMG_CHANNEL_COUNT == 2 ? 0x0300 : 0x0f00) | 0x000a)
#define ADS_MODE_REG 0x0111
#define ADC_SCK 12
#define ADC_MISO 13
#define ADC_MOSI 11
#define ADC_CS 10
#define IMU_SCL 6
#define IMU_RESERVED 5
#define IMU_SDA 4
#define FOOT_AD0 7
#define SHANK_AD0 15
#define FOOT_INT 16
#define SHANK_INT 17
#define SD_CLK 39
#ifndef AFO_BREADBOARD
#define AFO_BREADBOARD 0
#endif
#if AFO_BREADBOARD
#define SD_CMD 47
#define AFO_SD_METADATA "\"sd_cmd_gpio\":47,\"sd_clk_gpio\":39,\"sd_d0_gpio\":40,"
#else
#define SD_CMD 38
#define AFO_SD_METADATA "\"sd_cmd_gpio\":38,\"sd_clk_gpio\":39,\"sd_d0_gpio\":40,"
#endif
#define SD_D0 40
#define BUTTON_PIN 18
#define LED_RECORD 41
#define LED_ERROR 42
#define LED_BATTERY 2
#define BATTERY_PIN 1  // ADC1 channel 0; 100k/100k divider from protected 1S pack.
#define EMG_HZ 8000
#define IMU_HZ 200
#ifndef IMU_COUNT
#define IMU_COUNT 2
#endif
#define ENABLE_IMUS (IMU_COUNT > 0)
#ifndef HARDWARE_VARIANT
#define HARDWARE_VARIANT "pcb"
#endif
#define ADC_REFERENCE_MV (AFO_AD7606 ? 5000 : 1200) // Nominal signed full-scale, not measured.
#define ADC_REFERENCE_MEASURED 0 // Set to 1 only after measuring and entering the rail voltage.
#define BATTERY_DIVIDER 2.0f
#define BATTERY_WARN_MV 3500
#define BATTERY_STOP_MV 3300
#define MIN_FREE_BYTES (64ULL * 1024 * 1024)
#define MAX_SESSION_US (2ULL * 60 * 60 * 1000000)
// 20,480 x 64-byte records in PSRAM: about 2.44 s at 8,000 EMG + 400 IMU records/s.
// The SD specification permits write-busy periods up to 250 ms (SDHC) or
// 500 ms (SDXC); the older 2,048-entry internal queue held only 0.244 s.
#define RECORD_QUEUE_LENGTH 20480
#define SD_MOUNT "/sdcard"

// Laptop preview uses a private access point. Change this bench password before deployment.
#ifndef ENABLE_WIFI_LIVE
#define ENABLE_WIFI_LIVE 1
#endif
#define WIFI_LIVE_SSID "AFO-Recorder-B"
// No password is compiled in: each recorder generates a random one on first boot,
// keeps it in NVS and prints it on the USB console at every boot.
#define WIFI_LIVE_PASSWORD_CHARS 16
// Largest metadata JSON sent to the laptop; host/live_protocol.py MAX_PAYLOAD
// must match. MPU-6050 session metadata is about 1,360-1,430 bytes, above the
// previous 1,280-byte limit (which disabled the live preview); the 1,832-byte
// metadata datagram is IP-fragmented on Wi-Fi and resent every second.
#define WIFI_LIVE_METADATA_MAX 1800
#define WIFI_LIVE_PORT 3333
