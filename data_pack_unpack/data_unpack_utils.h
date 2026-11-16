#pragma once

#include "obc_gs_errors.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

uint8_t unpackUint8(const uint8_t* buffer, uint32_t* offset);

uint16_t unpackUint16(const uint8_t* buffer, uint32_t* offset);

uint32_t unpackUint32(const uint8_t* buffer, uint32_t* offset);

int8_t unpackInt8(const uint8_t* buffer, uint32_t* offset);

int16_t unpackInt16(const uint8_t* buffer, uint32_t* offset);

int32_t unpackInt32(const uint8_t* buffer, uint32_t* offset);

float unpackFloat(const uint8_t* buffer, uint32_t* offset);

/**
 * Unpack a 16-bit unsigned integer in little-endian byte order.
 * The caller must provide a buffer with at least 2 bytes.
 * @return OBC_GS_ERR_CODE_INVALID_ARG if any pointer is NULL; otherwise SUCCESS.
 */
obc_gs_error_code_t unpackUint16LE(const uint8_t* buf, uint16_t* val);

/**
 * Unpack a 32-bit unsigned integer in little-endian byte order.
 * The caller must provide a buffer with at least 4 bytes.
 * @return OBC_GS_ERR_CODE_INVALID_ARG if any pointer is NULL; otherwise SUCCESS.
 */
obc_gs_error_code_t unpackUint32LE(const uint8_t* buf, uint32_t* val);

#ifdef __cplusplus
}
#endif
