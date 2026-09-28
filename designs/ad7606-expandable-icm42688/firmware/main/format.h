#pragma once
#include <stdint.h>
#include <stddef.h>
#define AFO_HEADER_BYTES 4096
#define AFO_RECORD_BYTES 64
#define AFO_RECORD_MAGIC 0x31524641u /* little endian AFR1 */
enum { REC_EMG=1, REC_FOOT=2, REC_SHANK=3, REC_STATUS=4, REC_END=5, REC_EMG_B=6 };
enum { FLAG_GAP=1, FLAG_TIMING_UNCERTAIN=2, FLAG_INVALID=4 };
typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint8_t type, flags;
    uint16_t payload_len;
    uint32_t sequence;
    uint64_t timestamp_us;
    uint8_t payload[40];
    uint32_t crc;
} afo_record_t;
typedef struct __attribute__((packed)) {
    int32_t codes[4]; /* Only active_mask channels are valid; disabled values zero. */
    uint16_t adc_status, adc_crc;
    uint32_t read_duration_us, elapsed_slots;
    uint8_t active_mask, reserved[3];
    uint64_t read_start_us;
} emg_payload_t;
typedef struct __attribute__((packed)) {
    uint8_t fifo_packet[16];
    uint64_t read_start_us, read_end_us, irq_anchor_us;
} imu_payload_t;
typedef struct __attribute__((packed)) {
    uint32_t timer_missed, queue_dropped, imu_errors, fifo_overflows, adc_errors;
    uint32_t emg_records, foot_records, shank_records, battery_mv, queue_high_water;
} status_payload_t;
_Static_assert(sizeof(afo_record_t)==64, "record layout");
_Static_assert(sizeof(emg_payload_t)==40, "Rev B EMG layout");
_Static_assert(sizeof(imu_payload_t)==40, "IMU layout");
_Static_assert(sizeof(status_payload_t)==40, "status layout");
uint32_t afo_crc32(const void *data, size_t len);
void afo_format_init(void);
void afo_record_init(afo_record_t *r, uint8_t type, uint8_t flags,
                     uint32_t seq, uint64_t time, const void *payload, size_t len);
int afo_header(void *buffer, const char *json);
