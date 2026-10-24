#include <cstring>

#include <unity.h>

#include "protocol_crc.h"

namespace {
void assertCrc(const char *payload, uint32_t expected) {
  TEST_ASSERT_EQUAL_HEX32(expected, project_mirror::crc32(payload, std::strlen(payload)));
}

void testPoseGoldenVector() { assertCrc("1,42,12500,-4000", 0x91F71A45U); }

void testStopGoldenVector() { assertCrc("1,stop,43", 0x79595F22U); }

void testTrackingTelemetryGoldenVector() {
  assertCrc("1,telemetry,42,12500,-4000,tracking,pose,1", 0x844925C8U);
}

void testTimeoutTelemetryGoldenVector() {
  assertCrc("1,telemetry,44,12500,-4000,neutral,heartbeat_timeout,0", 0xD19F41A0U);
}
}  // namespace

int main(int, char **) {
  UNITY_BEGIN();
  RUN_TEST(testPoseGoldenVector);
  RUN_TEST(testStopGoldenVector);
  RUN_TEST(testTrackingTelemetryGoldenVector);
  RUN_TEST(testTimeoutTelemetryGoldenVector);
  return UNITY_END();
}
