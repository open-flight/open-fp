// M1 bench bring-up: one load cell on one ADS1220 (L1: CS D3, DRDY D2).
// Wiring and test procedure: docs/bench-single-cell.md.
//
// Output lines, read with `arduino-app-cli monitor` (tools/bench/single_cell.py parses them):
//   R,<ok 0|1>,<reg0>,<reg1>,<reg2>,<reg3>   register readback after configure (hex)
//   S,<ms>,<n>,<mean>,<std>,<min>,<max>      stats over each 100 ms window of 1000 SPS samples
//   E,<message>                              a problem to fix
// Send 'r' on the monitor to reset and re-check the ADC.
#include <Arduino_RouterBridge.h>
#include <SPI.h>
#include "ads1220.h"

constexpr uint8_t CS_PIN = 3;     // L1
constexpr uint8_t DRDY_PIN = 2;   // L1 DRDY
// Every other chip-select from the full pin map: held high so any board already wired stays off the bus.
constexpr uint8_t OTHER_CS[] = {4, 5, 6, 7, 8, 9, A2};
constexpr uint32_t WINDOW_MS = 100;
constexpr uint32_t NO_DRDY_MS = 500;

int64_t sum = 0;
double sumsq = 0;
int32_t vmin = INT32_MAX, vmax = INT32_MIN;
uint32_t n = 0, windowStart = 0, lastDrdy = 0;

void report(const char *line) { Monitor.println(line); }

void checkAdc() {
  uint8_t rb[4];
  bool ok = ads1220::configure(CS_PIN, rb);
  char buf[48];
  snprintf(buf, sizeof buf, "R,%d,%02X,%02X,%02X,%02X", ok ? 1 : 0, rb[0], rb[1], rb[2], rb[3]);
  report(buf);
  if (!ok) report("E,register readback mismatch: check CS (D3), SCLK (D13), DIN (D11), DOUT (D12), 3V3 and GND");
  ads1220::command(CS_PIN, ads1220::CMD_START);
  lastDrdy = millis();
}

void setup() {
  pinMode(CS_PIN, OUTPUT);
  digitalWrite(CS_PIN, HIGH);  // deselect everything before SPI starts
  for (uint8_t cs : OTHER_CS) {
    pinMode(cs, OUTPUT);
    digitalWrite(cs, HIGH);
  }
  pinMode(DRDY_PIN, INPUT_PULLUP);  // reads high (never ready) if DRDY isn't connected
  Monitor.begin();
  SPI.begin();
  delay(50);
  report("# ads1220_single: L1 on CS D3, DRDY D2, 1000 SPS, gain 128");
  checkAdc();
  windowStart = millis();
}

void loop() {
  if (Monitor.available() && Monitor.read() == 'r') checkAdc();

  uint32_t now = millis();
  if (digitalRead(DRDY_PIN) == LOW) {
    int32_t v = ads1220::read(CS_PIN);
    sum += v;
    sumsq += (double)v * v;
    if (v < vmin) vmin = v;
    if (v > vmax) vmax = v;
    n++;
    lastDrdy = now;
  } else if (now - lastDrdy > NO_DRDY_MS) {
    report("E,no DRDY for 500 ms: check DRDY -> D2, power, and that the readback line says 1");
    lastDrdy = now;
  }

  if (now - windowStart >= WINDOW_MS) {
    if (n > 0) {
      double mean = (double)sum / n;
      double var = sumsq / n - mean * mean;
      char buf[80];
      // Integers only: the Zephyr libc used here may not format floats.
      snprintf(buf, sizeof buf, "S,%lu,%lu,%ld,%ld,%ld,%ld", (unsigned long)now, (unsigned long)n,
               (long)(mean >= 0 ? mean + 0.5 : mean - 0.5), (long)(var > 0 ? sqrt(var) + 0.5 : 0),
               (long)vmin, (long)vmax);
      report(buf);
    }
    sum = 0;
    sumsq = 0;
    vmin = INT32_MAX;
    vmax = INT32_MIN;
    n = 0;
    windowStart = now;
  }
}
