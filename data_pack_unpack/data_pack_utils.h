#pragma once

#include "obc_gs_errors.h"

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Packs an unsigned 8-bit integer into a buffer at the given offset.
 *
 * @param value   The value to pack.
 * @param buffer  The buffer to pack the value into.
 * @param offset  A pointer to the offset within the buffer to pack the value at.
 */
void packUint8(uint8_t value, uint8_t* buffer, uint32_t* offset);

/**
 * Packs an unsigned 16-bit integer into a buffer at the given offset.
 *
 * @param value   The value to pack.
 * @param buffer  The buffer to pack the value into.
 * @param offset  A pointer to the offset within the buffer to pack the value at.
 */
void packUint16(uint16_t value, uint8_t* buffer, uint32_t* offset);

/**
 * Packs an unsigned 32-bit integer into a buffer at the given offset.
 *
 * @param value   The value to pack.
 * @param buffer  The buffer to pack the value into.
 * @param offset  A pointer to the offset within the buffer to pack the value at.
 */
void packUint32(uint32_t value, uint8_t* buffer, uint32_t* offset);

/**
 * Packs a signed 8-bit integer into a buffer at the given offset.
 *
 * @param value   The value to pack.
 * @param buffer  The buffer to pack the value into.
 * @param offset  A pointer to the offset within the buffer to pack the value at.
 */
void packInt8(int8_t value, uint8_t* buffer, uint32_t* offset);

/**
 * Packs a signed 16-bit integer into a buffer at the given offset.
 *
 * @param value   The value to pack.
 * @param buffer  The buffer to pack the value into.
 * @param offset  A pointer to the offset within the buffer to pack the value at.
 */
void packInt16(int16_t value, uint8_t* buffer, uint32_t* offset);

/**
 * Packs a signed 32-bit integer into a buffer at the given offset.
 *
 * @param value   The value to pack.
 * @param buffer  The buffer to pack the value into.
 * @param offset  A pointer to the offset within the buffer to pack the value at.
 */
void packInt32(int32_t value, uint8_t* buffer, uint32_t* offset);

/**
 * Packs a floating point value into a buffer at the given offset.
 *
 * @param value   The value to pack.
 * @param buffer  The buffer to pack the value into.
 * @param offset  A pointer to the offset within the buffer to pack the value at.
 */
void packFloat(float value, uint8_t* buffer, uint32_t* offset);

/**
 * Pack a 16-bit unsigned integer in little-endian byte order.
 * The caller must provide a buffer with at least 2 bytes.
 * @return OBC_GS_ERR_CODE_INVALID_ARG if any pointer is NULL; otherwise SUCCESS.
 */
obc_gs_error_code_t packUint16LE(uint8_t* buf, uint16_t val);

/**
 * Pack a 32-bit unsigned integer in little-endian byte order.
 * The caller must provide a buffer with at least 4 bytes.
 * @return OBC_GS_ERR_CODE_INVALID_ARG if any pointer is NULL; otherwise SUCCESS.
 */
obc_gs_error_code_t packUint32LE(uint8_t* buf, uint32_t val);

#ifdef __cplusplus
}
#endif
