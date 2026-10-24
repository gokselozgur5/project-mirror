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

Servo yawServo;
Servo pitchServo;
String inputLine;
uint32_t lastCommandAtMs = 0;
uint32_t lastSequence = 0;
bool armed = false;

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

void publishTelemetry(float yaw, float pitch) {
  JsonDocument response;
  response["v"] = 1;
  response["seq"] = lastSequence;
  response["yaw"] = yaw;
  response["pitch"] = pitch;
  response["armed"] = armed;
  serializeJson(response, Serial);
  Serial.println();
}

void handleCommand(const String &line) {
  JsonDocument command;
  if (deserializeJson(command, line) != DeserializationError::Ok) {
    return;
  }
  if (command["v"] != 1 || !command["seq"].is<uint32_t>() ||
      !command["yaw"].is<float>() || !command["pitch"].is<float>()) {
    return;
  }

  const uint32_t sequence = command["seq"];
  const float requestedYaw = command["yaw"];
  const float requestedPitch = command["pitch"];
  if (sequence <= lastSequence || !std::isfinite(requestedYaw) ||
      !std::isfinite(requestedPitch)) {
    return;
  }

  const float yaw = clampValue(requestedYaw, kYawMinDeg, kYawMaxDeg);
  const float pitch = clampValue(requestedPitch, kPitchMinDeg, kPitchMaxDeg);
  armIfNeeded();
  yawServo.write(poseToServo(yaw, kYawMinDeg, kYawMaxDeg));
  pitchServo.write(poseToServo(pitch, kPitchMinDeg, kPitchMaxDeg));
  lastSequence = sequence;
  lastCommandAtMs = millis();
  publishTelemetry(yaw, pitch);
}
}  // namespace

void setup() {
  Serial.begin(115200);
  inputLine.reserve(256);
  disarm();
}

void loop() {
  while (Serial.available() > 0) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\n') {
      handleCommand(inputLine);
      inputLine = "";
    } else if (inputLine.length() < 255) {
      inputLine += value;
    } else {
      inputLine = "";
    }
  }

  if (armed && millis() - lastCommandAtMs > kHeartbeatTimeoutMs) {
    disarm();
  }
}
