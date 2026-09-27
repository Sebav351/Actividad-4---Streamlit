#include <Arduino.h>

namespace {
constexpr uint8_t ledPins[] = {25, 26, 27};
constexpr uint8_t ledChannels[] = {0, 1, 2};
constexpr uint32_t pwmFrequency = 5000;
constexpr uint8_t pwmResolution = 8;
constexpr uint32_t sequenceIntervalMs = 170;
constexpr uint8_t sequenceSteps = 12;

String inputLine;
bool discardUntilNewline = false;
uint8_t activeSequence = 0;
uint8_t currentStep = 0;
uint32_t lastSequenceStep = 0;

void setBrightness(uint8_t percent) {
  activeSequence = 0;
  const uint32_t duty = (static_cast<uint32_t>(percent) * 255U + 50U) / 100U;
  for (const uint8_t channel : ledChannels) {
    ledcWrite(channel, duty);
  }
}

void startSequence(uint8_t sequence) {
  activeSequence = sequence;
  currentStep = 0;
  lastSequenceStep = millis() - sequenceIntervalMs;
  for (const uint8_t channel : ledChannels) {
    ledcWrite(channel, 0);
  }
}

void processCommand(String command) {
  command.trim();
  command.toUpperCase();

  if (command == "PWM:30") {
    setBrightness(30);
  } else if (command == "PWM:70") {
    setBrightness(70);
  } else if (command == "PWM:100") {
    setBrightness(100);
  } else if (command == "SEQ:1") {
    startSequence(1);
  } else if (command == "SEQ:2") {
    startSequence(2);
  }
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    const char incoming = static_cast<char>(Serial.read());
    if (incoming == '\n') {
      if (!discardUntilNewline) {
        processCommand(inputLine);
      }
      inputLine = "";
      discardUntilNewline = false;
    } else if (incoming != '\r' && !discardUntilNewline) {
      if (inputLine.length() < 40) {
        inputLine += incoming;
      } else {
        inputLine = "";
        discardUntilNewline = true;
      }
    }
  }
}

void updateSequence() {
  if (activeSequence == 0 || millis() - lastSequenceStep < sequenceIntervalMs) {
    return;
  }

  lastSequenceStep = millis();
  for (uint8_t index = 0; index < 3; ++index) {
    const uint8_t litIndex = activeSequence == 1
        ? currentStep % 3
        : 2 - (currentStep % 3);
    ledcWrite(ledChannels[index], index == litIndex ? 255 : 0);
  }

  ++currentStep;
  if (currentStep >= sequenceSteps) {
    activeSequence = 0;
    for (const uint8_t channel : ledChannels) {
      ledcWrite(channel, 0);
    }
  }
}
}  // namespace

void setup() {
  Serial.begin(115200);
  inputLine.reserve(40);

  for (uint8_t index = 0; index < 3; ++index) {
    ledcSetup(ledChannels[index], pwmFrequency, pwmResolution);
    ledcAttachPin(ledPins[index], ledChannels[index]);
    ledcWrite(ledChannels[index], 0);
  }

  Serial.println("ESP32 DevKit V1 lista; protocolo PWM/SEQ a 115200 baudios.");
}

void loop() {
  readSerialCommands();
  updateSequence();
}