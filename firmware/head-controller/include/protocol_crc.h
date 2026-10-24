#pragma once

#include <cstddef>
#include <cstdint>

namespace project_mirror {
inline uint32_t crc32(const char *payload, size_t length) {
  uint32_t crc = 0xFFFFFFFFU;
  for (size_t index = 0; index < length; ++index) {
    crc ^= static_cast<uint8_t>(payload[index]);
    for (uint8_t bit = 0; bit < 8; ++bit) {
      crc = (crc >> 1U) ^ ((crc & 1U) != 0U ? 0xEDB88320U : 0U);
    }
  }
  return ~crc;
}
}  // namespace project_mirror
