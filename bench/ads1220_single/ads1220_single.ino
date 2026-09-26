// M1 bench bring-up: one load cell on one ADS1220 (L1: CS D3, DRDY D2).
// Wiring and test procedure: docs/bench-single-cell.md.
//
// Output lines, read with `arduino-app-cli monitor` (tools/bench/single_cell.py parses them):
//   R,<ok 0|1>,<reg0>,<reg1>,<reg2>,<reg3>   register readback after configure (hex)
//   S,<ms>,<n>,<mean>,<std>,<min>,<max>,<drdy>  stats over each 100 ms window: n samples
//                                            captured, and drdy conversions signalled by the ADC
//                                            (counted by interrupt; n < drdy while Monitor I/O blocks)
//   M,<differential|single-ended>             measurement mode
//   V,<name>,<millivolts>                    voltage check ('v'), measured by the ADC itself
//   X,<i>,<b2><b1><b0>,<value>                raw dump ('x'): 32 consecutive conversions, bytes in hex
//   E,<message>                              a problem to fix
// Keys on the monitor: 'r' reset and re-check the ADC; 'd' differential AIN0-AIN1, gain 128
// (the real configuration, needs R1/R2); 's' single-ended AIN0-GND, gain 1 (works before
// R1/R2 are fitted: tests wiring and response, not accuracy); 'v' voltage check: AVDD, AIN0 and
// AIN1 against the ADC's internal 2.048 V reference, and the external reference on REFP0/REFN0.
#include <Arduino_RouterBridge.h>
#include <SPI.h>
#include "ads1220.h"

constexpr uint8_t CS_PIN = 3;     // L1
constexpr uint8_t DRDY_PIN = 2;   // L1 DRDY
// Every other chip-select from the full pin map: held high so any board already wired stays off the bus.
constexpr uint8_t OTHER_CS[] = {4, 5, 6, 7, 8, 9, A2};
constexpr uint32_t WINDOW_MS = 100;
constexpr uint32_t NO_DRDY_MS = 500;
constexpr uint32_t KEY_POLL_MS = 200;  // each Monitor call is a blocking RPC to Linux (~13 ms)

int64_t sum = 0;
double sumsq = 0;
int32_t vmin = INT32_MAX, vmax = INT32_MIN;
uint32_t n = 0, windowStart = 0, lastDrdy = 0, lastKeyPoll = 0;
volatile uint32_t drdyCount = 0;
void onDrdy() { drdyCount++; }  // ISR: count only, never touch SPI or Monitor here
const uint8_t *cfg = ads1220::CFG;

void report(const char *line) { Monitor.println(line); }

void checkAdc() {
  report(cfg == ads1220::CFG ? "M,differential" : "M,single-ended");
  uint8_t rb[4];
  bool ok = ads1220::configure(CS_PIN, cfg, rb);
  char buf[48];
  snprintf(buf, sizeof buf, "R,%d,%02X,%02X,%02X,%02X", ok ? 1 : 0, rb[0], rb[1], rb[2], rb[3]);
  report(buf);
  if (!ok) report("E,register readback mismatch: check CS (D3), SCLK (D13), DIN (D11), DOUT (D12), 3V3 and GND");
  ads1220::command(CS_PIN, ads1220::CMD_START);
  lastDrdy = millis();
}

// Average `count` conversions with the current config (after discarding a few). Returns false on timeout.
bool average(int count, double &out) {
  double sumv = 0;
  int got = 0;
  uint32_t start = millis();
  while (got < count + 4) {
    if (millis() - start > 500) return false;
    if (digitalRead(DRDY_PIN) == LOW) {
      int32_t v = ads1220::read(CS_PIN);
      if (got >= 4) sumv += v;
      got++;
    }
  }
  out = sumv / count;
  return true;
}

// Configure one measurement (register 0 and 2), start it, and average it.
bool measure(uint8_t reg0, uint8_t reg2, double &counts) {
  const uint8_t regs[4] = {reg0, 0xC4, reg2, 0x00};
  uint8_t rb[4];
  if (!ads1220::configure(CS_PIN, regs, rb)) return false;
  ads1220::command(CS_PIN, ads1220::CMD_START);
  return average(64, counts);
}

void reportMv(const char *name, double mv, bool saturated) {
  char buf[64];
  if (saturated) snprintf(buf, sizeof buf, "V,%s,>%ld", name, (long)mv);
  else snprintf(buf, sizeof buf, "V,%s,%ld", name, (long)(mv + 0.5));
  report(buf);
}

// Voltage check with the ADC's internal 2.048 V reference (gain 1, PGA bypassed):
// register 0 = MUX << 4 | 0x01; MUX 1101 = (AVDD-AVSS)/4, 1000 = AIN0-AVSS, 1001 = AIN1-AVSS.
// Raw dump: 32 consecutive conversions exactly as read over SPI (diagnoses stuck or
// correlated bytes). Output is sent after capture so the RPCs don't disturb the timing.
void rawDump() {
  uint32_t raw[32];
  int got = 0;
  uint32_t start = millis();
  while (got < 32 && millis() - start < 500) {
    if (digitalRead(DRDY_PIN) == LOW) {
      SPI.beginTransaction(ads1220::SPI_CFG);
      digitalWrite(CS_PIN, LOW);
      SPI.transfer(ads1220::CMD_RDATA);
      uint32_t v = (uint32_t)SPI.transfer(0) << 16;
      v |= (uint32_t)SPI.transfer(0) << 8;
      v |= SPI.transfer(0);
      digitalWrite(CS_PIN, HIGH);
      SPI.endTransaction();
      raw[got++] = v;
      while (digitalRead(DRDY_PIN) == LOW && millis() - start < 500) {}  // wait for DRDY to clear
    }
  }
  char buf[48];
  for (int i = 0; i < got; i++) {
    int32_t sv = (raw[i] & 0x800000) ? (int32_t)(raw[i] | 0xFF000000) : (int32_t)raw[i];
    snprintf(buf, sizeof buf, "X,%d,%06lX,%ld", i, (unsigned long)raw[i], (long)sv);
    report(buf);
  }
  if (got < 32) report("E,raw dump: fewer than 32 conversions (DRDY?)");
}

void voltageCheck() {
  constexpr double FS = 8388608.0, VREF_INT_MV = 2048.0, SAT = 8388000.0;
  double c = 0, avddMv = 0;
  if (measure(0xD1, 0x00, c)) {
    avddMv = 4 * c * VREF_INT_MV / FS;
    reportMv("AVDD", avddMv, false);
  } else report("E,voltage check: no conversions (DRDY?)");
  if (measure(0x81, 0x00, c)) reportMv("AIN0", c >= SAT ? VREF_INT_MV : c * VREF_INT_MV / FS, c >= SAT);
  if (measure(0x91, 0x00, c)) reportMv("AIN1", c >= SAT ? VREF_INT_MV : c * VREF_INT_MV / FS, c >= SAT);
  // External reference: measure AVDD/4 against REFP0-REFN0. Saturation means the reference is
  // smaller than AVDD/4, i.e. REFP0/REFN0 aren't connected.
  if (avddMv > 0 && measure(0xD1, 0x40, c)) {
    if (c >= SAT) report("V,REF,<AVDD/4: REFP0/REFN0 not connected?");
    else reportMv("REF", (avddMv / 4) * FS / c, false);
  }
  checkAdc();  // back to the selected mode
}

void setup() {
  pinMode(CS_PIN, OUTPUT);
  digitalWrite(CS_PIN, HIGH);  // deselect everything before SPI starts
  for (uint8_t cs : OTHER_CS) {
    pinMode(cs, OUTPUT);
    digitalWrite(cs, HIGH);
  }
  pinMode(DRDY_PIN, INPUT_PULLUP);  // reads high (never ready) if DRDY isn't connected
  attachInterrupt(digitalPinToInterrupt(DRDY_PIN), onDrdy, FALLING);
  Monitor.begin();
  SPI.begin();
  delay(50);
  report("# ads1220_single: L1 on CS D3, DRDY D2, 1000 SPS ('s' single-ended, 'd' differential)");
  checkAdc();
  windowStart = millis();
}

void loop() {
  uint32_t now = millis();
  if (now - lastKeyPoll >= KEY_POLL_MS) {
    lastKeyPoll = now;
    if (Monitor.available()) {
      int c = Monitor.read();
      if (c == 'd') cfg = ads1220::CFG;
      if (c == 's') cfg = ads1220::CFG_SINGLE_ENDED;
      if (c == 'r' || c == 'd' || c == 's') checkAdc();
      if (c == 'v') voltageCheck();
      if (c == 'x') rawDump();
      now = millis();
    }
  }
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
      noInterrupts();
      uint32_t drdy = drdyCount;
      drdyCount = 0;
      interrupts();
      snprintf(buf, sizeof buf, "S,%lu,%lu,%ld,%ld,%ld,%ld,%lu", (unsigned long)now, (unsigned long)n,
               (long)(mean >= 0 ? mean + 0.5 : mean - 0.5), (long)(var > 0 ? sqrt(var) + 0.5 : 0),
               (long)vmin, (long)vmax, (unsigned long)drdy);
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
