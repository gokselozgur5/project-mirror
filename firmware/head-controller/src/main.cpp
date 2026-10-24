#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <cmath>

namespace {
constexpr int kYawPin = 5;
constexpr int kPitchPin = 6;
constexpr float kYawMinDeg = -55.0F;
constexpr float kYawMaxDeg = 55.0F;
constexpr float kPitchMinDeg = -25.0F;
constexpr float kPitchMaxDeg = 25.0F;
constexpr uint32_t kHeartbeatTimeoutMs = 500;
constexpr int kServoMinUs = 700;
constexpr int kServoMaxUs = 2300;
constexpr size_t kMaxFrameBytes = 160;

Servo yawServo;
Servo pitchServo;
String inputLine;
uint32_t lastCommandAtMs = 0;
uint32_t lastSequence = 0;
bool armed = false;
bool discardingFrame = false;

float clampValue(float value, float lower, float upper) {
  return std::max(lower, std::min(upper, value));
}

int poseToServo(float degrees, float lower, float upper) {
  const float normalized = (degrees - lower) / (upper - lower);
  return static_cast<int>(std::round(normalized * 180.0F));
}

void disarm() {
  yawServo.detach();
  pitchServo.detach();
  armed = false;
}

void armIfNeeded() {
  if (armed) {
    return;
  }
  yawServo.attach(kYawPin, kServoMinUs, kServoMaxUs);
  pitchServo.attach(kPitchPin, kServoMinUs, kServoMaxUs);
  armed = true;
}

uint32_t crc32(const String &payload) {
  uint32_t crc = 0xFFFFFFFFU;
  for (size_t index = 0; index < payload.length(); ++index) {
    crc ^= static_cast<uint8_t>(payload[index]);
    for (uint8_t bit = 0; bit < 8; ++bit) {
      crc = (crc >> 1U) ^ ((crc & 1U) != 0U ? 0xEDB88320U : 0U);
    }
  }
  return ~crc;
}

bool checksumMatches(uint32_t sequence, int32_t yawMilliDegrees,
                     int32_t pitchMilliDegrees, const char *provided) {
  if (provided == nullptr || strlen(provided) != 8) {
    return false;
  }
  for (size_t index = 0; index < 8; ++index) {
    const char value = provided[index];
    if (!((value >= '0' && value <= '9') || (value >= 'A' && value <= 'F'))) {
      return false;
    }
  }

  const String payload = "1," + String(sequence) + "," + String(yawMilliDegrees) +
                         "," + String(pitchMilliDegrees);
  char expected[9];
  snprintf(expected, sizeof(expected), "%08lX", static_cast<unsigned long>(crc32(payload)));
  return strcmp(provided, expected) == 0;
}

void publishTelemetry(int32_t yawMilliDegrees, int32_t pitchMilliDegrees) {
  JsonDocument response;
  response["v"] = 1;
  response["seq"] = lastSequence;
  response["yaw_mdeg"] = yawMilliDegrees;
  response["pitch_mdeg"] = pitchMilliDegrees;
  response["armed"] = armed;
  serializeJson(response, Serial);
  Serial.println();
}

void handleCommand(const String &line) {
  JsonDocument command;
  if (deserializeJson(command, line) != DeserializationError::Ok) {
    return;
  }
  const JsonObjectConst object = command.as<JsonObjectConst>();
  const JsonVariantConst versionValue = object["v"];
  const JsonVariantConst sequenceValue = object["seq"];
  const JsonVariantConst yawValue = object["yaw_mdeg"];
  const JsonVariantConst pitchValue = object["pitch_mdeg"];
  const JsonVariantConst checksumValue = object["crc32"];
  if (object.size() != 5 || !versionValue.is<int>() || versionValue.as<int>() != 1 ||
      !sequenceValue.is<uint32_t>() || !yawValue.is<int32_t>() ||
      !pitchValue.is<int32_t>() || !checksumValue.is<const char *>()) {
    return;
  }

  const uint32_t sequence = sequenceValue.as<uint32_t>();
  const int32_t yawMilliDegrees = yawValue.as<int32_t>();
  const int32_t pitchMilliDegrees = pitchValue.as<int32_t>();
  if (sequence <= lastSequence || yawMilliDegrees < -55000 || yawMilliDegrees > 55000 ||
      pitchMilliDegrees < -25000 || pitchMilliDegrees > 25000 ||
      !checksumMatches(sequence, yawMilliDegrees, pitchMilliDegrees,
                       checksumValue.as<const char *>())) {
    return;
  }

  const float yaw = clampValue(static_cast<float>(yawMilliDegrees) / 1000.0F, kYawMinDeg,
                               kYawMaxDeg);
  const float pitch = clampValue(static_cast<float>(pitchMilliDegrees) / 1000.0F,
                                 kPitchMinDeg, kPitchMaxDeg);
  armIfNeeded();
  yawServo.write(poseToServo(yaw, kYawMinDeg, kYawMaxDeg));
  pitchServo.write(poseToServo(pitch, kPitchMinDeg, kPitchMaxDeg));
  lastSequence = sequence;
  lastCommandAtMs = millis();
  publishTelemetry(yawMilliDegrees, pitchMilliDegrees);
}
}  // namespace

void setup() {
  Serial.begin(115200);
  inputLine.reserve(kMaxFrameBytes);
  disarm();
}

void loop() {
  while (Serial.available() > 0) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\n') {
      if (!discardingFrame && !inputLine.isEmpty()) {
        handleCommand(inputLine);
      }
      inputLine = "";
      discardingFrame = false;
    } else if (!discardingFrame && inputLine.length() < kMaxFrameBytes - 1) {
      inputLine += value;
    } else {
      inputLine = "";
      discardingFrame = true;
    }
  }

  if (armed && millis() - lastCommandAtMs > kHeartbeatTimeoutMs) {
    disarm();
  }
}
