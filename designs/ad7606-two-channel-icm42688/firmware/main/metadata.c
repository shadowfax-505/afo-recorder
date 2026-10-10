#include <stdio.h>
#include "board.h"
#include "metadata.h"
#define AFO_STRINGIFY_(x) #x
#define AFO_STRINGIFY(x) AFO_STRINGIFY_(x)
int afo_session_metadata(char *out, size_t capacity, const char *trial_name) {
    return snprintf(out,capacity,
      "{" AFO_ADC_METADATA AFO_SD_METADATA
      "\"firmware\":\"" AFO_FIRMWARE_ID "\",\"hardware_variant\":\"" HARDWARE_VARIANT "\","
      "\"synthetic\":false,\"trial_id\":\"%s\",\"clock\":\"esp_timer_boot_us\","
      "\"emg_hz\":8000,\"imu_hz\":200,\"imu_enabled\":true,"
      "\"active_channel_count\":%d,\"emg_channels\":%s,"
      "\"calibration_state\":\"uncalibrated\",\"simultaneous\":true,"
      "\"accel_range_g\":16,\"gyro_range_dps\":2000,\"imu_timestamp_tick_us\":1,"
      "\"imu_timing_calibrated\":false,\"imu_locations\":[\"foot\",\"shank\"],"
      "\"imu_time\":\"fifo_delta_first_irq\","
      "\"placement_verified\":false,\"record_bytes\":64,\"usb_recording_inhibit\":true,"
      "\"record_queue_entries\":" AFO_STRINGIFY(RECORD_QUEUE_LENGTH) ","
      "\"analog_filter\":\"two cascaded 3.3k/47nF low-pass sections, each unity buffered; 100R series output, 1nF to ground; single-ended ADC\","
      "\"unplugged_input_bias_mv\":1500,\"unplugged_input_bias_ohm\":1000000,"
      "\"clock_or_filter_delay_correction\":\"none\",\"notes\":\"Engineering prototype; physical validation pending\"}",
      trial_name,EMG_CHANNEL_COUNT,
      EMG_CHANNEL_COUNT==2?"[\"EMG1\",\"EMG2\"]":"[\"EMG1\",\"EMG2\",\"EMG3\",\"EMG4\"]");
}
