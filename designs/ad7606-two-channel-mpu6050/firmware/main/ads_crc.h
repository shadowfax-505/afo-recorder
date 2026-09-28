#pragma once
#include <stdint.h>
#include <stddef.h>
uint16_t ads_crc16(const uint8_t *data,size_t length);
/* 0=valid, 1=CRC failure, 2=unexpected status; all six 24-bit words required. */
int ads_decode24(const uint8_t frame[18],int32_t codes[4],uint16_t *status,uint16_t *crc);
