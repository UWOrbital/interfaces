#include "data_pack_utils.h"

#include <stdint.h>
#include <stddef.h>
#include <string.h>

void packUint8(uint8_t value, uint8_t* buffer, uint32_t* offset) {
  buffer[*offset] = value;
  (*offset)++;
}

void packUint16(uint16_t value, uint8_t* buffer, uint32_t* offset) {
  buffer[*offset] = (uint8_t)(value >> 8);
  buffer[*offset + 1] = (uint8_t)value;
  (*offset) += 2;
}

void packUint32(uint32_t value, uint8_t* buffer, uint32_t* offset) {
  buffer[*offset] = (uint8_t)(value >> 24);
  buffer[*offset + 1] = (uint8_t)(value >> 16);
  buffer[*offset + 2] = (uint8_t)(value >> 8);
  buffer[*offset + 3] = (uint8_t)value;
  (*offset) += 4;
}

void packInt8(int8_t value, uint8_t* buffer, uint32_t* offset) {
  uint8_t tmp;
  memcpy(&tmp, &value, sizeof(tmp));
  packUint8(tmp, buffer, offset);
}

void packInt16(int16_t value, uint8_t* buffer, uint32_t* offset) {
  uint16_t tmp;
  memcpy(&tmp, &value, sizeof(tmp));
  packUint16(tmp, buffer, offset);
}

void packInt32(int32_t value, uint8_t* buffer, uint32_t* offset) {
  uint32_t tmp;
  memcpy(&tmp, &value, sizeof(tmp));
  packUint32(tmp, buffer, offset);
}

void packFloat(float value, uint8_t* buffer, uint32_t* offset) {
  _Static_assert(sizeof(float) == sizeof(uint32_t), "float is not 32 bits");

  uint32_t tmp;
  memcpy(&tmp, &value, sizeof(tmp));
  packUint32(tmp, buffer, offset);
}

obc_gs_error_code_t packUint16LE(uint8_t* buf, uint16_t val) {
  if (buf == NULL) {
    return OBC_GS_ERR_CODE_INVALID_ARG;
  }

  buf[0] = (uint8_t)((val >> 0) & 0xFFU);
  buf[1] = (uint8_t)((val >> 8) & 0xFFU);
  return OBC_GS_ERR_CODE_SUCCESS;
}

obc_gs_error_code_t packUint32LE(uint8_t* buf, uint32_t val) {
  if (buf == NULL) {
    return OBC_GS_ERR_CODE_INVALID_ARG;
  }

  buf[0] = (uint8_t)((val >> 0) & 0xFFU);
  buf[1] = (uint8_t)((val >> 8) & 0xFFU);
  buf[2] = (uint8_t)((val >> 16) & 0xFFU);
  buf[3] = (uint8_t)((val >> 24) & 0xFFU);
  return OBC_GS_ERR_CODE_SUCCESS;
}
