#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <cmath>

#include "protocol_crc.h"

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
int32_t lastYawMilliDegrees = 0;
int32_t lastPitchMilliDegrees = 0;
bool armed = false;
bool discardingFrame = false;
bool stopLatched = true;
const char *lastMode = "stopped";
const char *lastReason = "startup";

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
  return project_mirror::crc32(payload.c_str(), payload.length());
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

bool controlChecksumMatches(const char *operation, uint32_t sequence, const char *provided) {
  if (operation == nullptr || provided == nullptr || strlen(provided) != 8) {
    return false;
  }
  for (size_t index = 0; index < 8; ++index) {
    const char value = provided[index];
    if (!((value >= '0' && value <= '9') || (value >= 'A' && value <= 'F'))) {
      return false;
    }
  }

  const String payload = "1," + String(operation) + "," + String(sequence);
  char expected[9];
  snprintf(expected, sizeof(expected), "%08lX", static_cast<unsigned long>(crc32(payload)));
  return strcmp(provided, expected) == 0;
}

void publishTelemetry(int32_t yawMilliDegrees, int32_t pitchMilliDegrees, const char *mode,
                      const char *reason) {
  lastMode = mode;
  lastReason = reason;
  const String payload = "1,telemetry," + String(lastSequence) + "," +
                         String(yawMilliDegrees) + "," + String(pitchMilliDegrees) + "," +
                         String(mode) + "," + String(reason) + "," + (armed ? "1" : "0");
  char checksum[9];
  snprintf(checksum, sizeof(checksum), "%08lX",
           static_cast<unsigned long>(crc32(payload)));

  JsonDocument response;
  response["v"] = 1;
  response["seq"] = lastSequence;
  response["yaw_mdeg"] = yawMilliDegrees;
  response["pitch_mdeg"] = pitchMilliDegrees;
  response["mode"] = mode;
  response["reason"] = reason;
  response["armed"] = armed;
  response["crc32"] = checksum;
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
  if (!versionValue.is<int>() || versionValue.as<int>() != 1 ||
      !sequenceValue.is<uint32_t>()) {
    return;
  }

  const uint32_t sequence = sequenceValue.as<uint32_t>();

  if (object["op"].is<const char *>()) {
    const JsonVariantConst operationValue = object["op"];
    const JsonVariantConst checksumValue = object["crc32"];
    if (object.size() != 4 || !operationValue.is<const char *>() ||
        !checksumValue.is<const char *>()) {
      return;
    }
    const char *operation = operationValue.as<const char *>();
    if ((strcmp(operation, "stop") != 0 && strcmp(operation, "arm") != 0 &&
         strcmp(operation, "status") != 0) ||
        !controlChecksumMatches(operation, sequence, checksumValue.as<const char *>())) {
      return;
    }

    if (strcmp(operation, "status") == 0) {
      if (sequence == 0) {
        publishTelemetry(lastYawMilliDegrees, lastPitchMilliDegrees, lastMode, lastReason);
      }
      return;
    }
    if (sequence <= lastSequence) {
      return;
    }

    lastSequence = sequence;
    lastCommandAtMs = millis();
    if (strcmp(operation, "stop") == 0) {
      stopLatched = true;
      disarm();
      publishTelemetry(lastYawMilliDegrees, lastPitchMilliDegrees, "stopped",
                       "operator_stop");
    } else {
      stopLatched = false;
      publishTelemetry(lastYawMilliDegrees, lastPitchMilliDegrees, "neutral", "operator_arm");
    }
    return;
  }

  if (sequence <= lastSequence) {
    return;
  }

  const JsonVariantConst yawValue = object["yaw_mdeg"];
  const JsonVariantConst pitchValue = object["pitch_mdeg"];
  const JsonVariantConst checksumValue = object["crc32"];
  if (object.size() != 5 || !yawValue.is<int32_t>() || !pitchValue.is<int32_t>() ||
      !checksumValue.is<const char *>() || stopLatched) {
    return;
  }

  const int32_t yawMilliDegrees = yawValue.as<int32_t>();
  const int32_t pitchMilliDegrees = pitchValue.as<int32_t>();
  if (yawMilliDegrees < -55000 || yawMilliDegrees > 55000 || pitchMilliDegrees < -25000 ||
      pitchMilliDegrees > 25000 ||
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
  lastYawMilliDegrees = yawMilliDegrees;
  lastPitchMilliDegrees = pitchMilliDegrees;
  lastCommandAtMs = millis();
  publishTelemetry(yawMilliDegrees, pitchMilliDegrees, "tracking", "pose");
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
    publishTelemetry(lastYawMilliDegrees, lastPitchMilliDegrees, "neutral",
                     "heartbeat_timeout");
  }
}
