// M2 bench bring-up: every ADS1220 on the shared bus (one carrier or both).
// Wiring: docs/harness.md. Guided test: tools/bench/multi_cell.py.
//
// On start (and on 'r', 'd', 's') it configures all 8 chip-selects and reports which answer.
// Boards that read back their registers are "present" and are read on every tick. A tick is
// L1's DRDY (the only DRDY wired); if L1 isn't present, a 1 ms timer paces instead. The other
// boards run on their own oscillators, so now and then one is read twice before its next
// conversion: a few repeated values are normal, a channel that repeats almost every time is stuck.
//
// Output lines, read with `arduino-app-cli monitor`:
//   M,<differential|single-ended>                 measurement mode
//   R,<ch>,<ok 0|1>,<reg0>,<reg1>,<reg2>,<reg3>   readback per channel (hex), all 8 channels
//   S,<ms>,<ticks>,<drdy>,<ch>:<n>:<mean>:<std>:<min>:<max>:<rep>,...
//                                                 one line per 250 ms window: ticks the loop caught,
//                                                 L1 DRDY pulses counted by interrupt (0 if L1 absent),
//                                                 then each present channel; rep = reads equal to the
//                                                 previous read of that channel
//   V,<ch>,<AVDD|AIN0|AIN1|REF>,<millivolts>       voltage check ('v'), measured by each ADC itself
//   X,<ch>,<i>,<b2><b1><b0>,<value>               raw dump ('x'): 16 consecutive reads per channel
//   E,<message>                                   a problem to fix
// Keys: 'r' re-check; 'd' differential AIN0-AIN1, gain 128 (needs R1/R2); 's' single-ended
// AIN0-GND, gain 1 (works before R1/R2); 'v' voltage check; 'x' raw dump.
#include <Arduino_RouterBridge.h>
#include <SPI.h>
#include "ads1220.h"

constexpr uint8_t NCH = 8;
const char *const NAMES[NCH] = {"L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4"};
const uint8_t CS[NCH] = {3, 4, 5, 6, 7, 8, 9, A2};  // docs/harness.md; never D10 (SPI NSS)
constexpr uint8_t DRDY_PIN = 2;                      // L1's DRDY only
constexpr uint32_t WINDOW_MS = 250;
constexpr uint32_t KEY_POLL_MS = 200;  // each Monitor call is a blocking RPC to Linux (~13 ms)
constexpr uint32_t TIMER_TICK_US = 1000;

struct Acc {
  int64_t sum;
  double sumsq;
  int32_t vmin, vmax, last;
  uint32_t n, rep;
};

bool present[NCH];
Acc acc[NCH];
uint32_t ticks = 0, windowStart = 0, lastKeyPoll = 0, lastTimerTick = 0;
volatile uint32_t drdyCount = 0;
void onDrdy() { drdyCount++; }  // ISR: count only, never touch SPI or Monitor here
const uint8_t *cfg = ads1220::CFG;

void report(const char *line) { Monitor.println(line); }

void resetAcc() {
  for (auto &a : acc) {
    a.sum = 0;
    a.sumsq = 0;
    a.vmin = INT32_MAX;
    a.vmax = INT32_MIN;
    a.n = 0;
    a.rep = 0;
  }
  ticks = 0;
}

void checkAll() {
  report(cfg == ads1220::CFG ? "M,differential" : "M,single-ended");
  char buf[48];
  for (uint8_t i = 0; i < NCH; i++) {
    uint8_t rb[4];
    present[i] = ads1220::configure(CS[i], cfg, rb);
    snprintf(buf, sizeof buf, "R,%s,%d,%02X,%02X,%02X,%02X", NAMES[i], present[i] ? 1 : 0, rb[0], rb[1],
             rb[2], rb[3]);
    report(buf);
  }
  for (uint8_t i = 0; i < NCH; i++)
    if (present[i]) ads1220::command(CS[i], ads1220::CMD_START);
  for (auto &a : acc) a.last = INT32_MIN;
  resetAcc();
  noInterrupts();
  drdyCount = 0;
  interrupts();
  windowStart = millis();
}

// Wait for the next tick: L1's DRDY if L1 is present, else the 1 ms timer.
bool tickReady() {
  if (present[0]) return digitalRead(DRDY_PIN) == LOW;
  uint32_t now = micros();
  if (now - lastTimerTick >= TIMER_TICK_US) {
    lastTimerTick = now;
    return true;
  }
  return false;
}

// Average `count` reads of one board, paced by time (only L1 has a DRDY wire).
bool average(uint8_t cs, int count, double &out) {
  delay(6);  // first conversions after START
  double s = 0;
  for (int i = 0; i < count; i++) {
    delayMicroseconds(1100);
    s += ads1220::read(cs);
  }
  out = s / count;
  return true;
}

bool measure(uint8_t cs, uint8_t reg0, uint8_t reg2, double &counts) {
  const uint8_t regs[4] = {reg0, 0xC4, reg2, 0x00};
  uint8_t rb[4];
  if (!ads1220::configure(cs, regs, rb)) return false;
  ads1220::command(cs, ads1220::CMD_START);
  return average(cs, 48, counts);
}

void reportMv(const char *ch, const char *name, double mv, bool saturated) {
  char buf[64];
  if (saturated) snprintf(buf, sizeof buf, "V,%s,%s,>%ld", ch, name, (long)mv);
  else snprintf(buf, sizeof buf, "V,%s,%s,%ld", ch, name, (long)(mv + 0.5));
  report(buf);
}

// Same method as bench/ads1220_single: the internal 2.048 V reference, gain 1, PGA bypassed.
void voltageCheck() {
  constexpr double FS = 8388608.0, VREF_INT_MV = 2048.0, SAT = 8388000.0;
  char buf[64];
  for (uint8_t i = 0; i < NCH; i++) {
    if (!present[i]) continue;
    double c = 0, avddMv = 0;
    if (!measure(CS[i], 0xD1, 0x00, c)) {
      snprintf(buf, sizeof buf, "E,%s voltage check: readback failed", NAMES[i]);
      report(buf);
      continue;
    }
    avddMv = 4 * c * VREF_INT_MV / FS;
    reportMv(NAMES[i], "AVDD", avddMv, false);
    if (measure(CS[i], 0x81, 0x00, c)) reportMv(NAMES[i], "AIN0", c >= SAT ? VREF_INT_MV : c * VREF_INT_MV / FS, c >= SAT);
    if (measure(CS[i], 0x91, 0x00, c)) reportMv(NAMES[i], "AIN1", c >= SAT ? VREF_INT_MV : c * VREF_INT_MV / FS, c >= SAT);
    if (avddMv > 0 && measure(CS[i], 0xD1, 0x40, c)) {
      if (c >= SAT) {
        snprintf(buf, sizeof buf, "V,%s,REF,<AVDD/4: REFP0/REFN0 not connected?", NAMES[i]);
        report(buf);
      } else reportMv(NAMES[i], "REF", (avddMv / 4) * FS / c, false);
    }
  }
  checkAll();  // back to the selected mode on every board
}

// 16 consecutive reads of every present board, paced by the normal tick, printed afterwards
// so the Monitor RPCs don't disturb the timing.
void rawDump() {
  constexpr int N = 16;
  static uint32_t raw[NCH][N];
  int got = 0;
  uint32_t start = millis();
  while (got < N && millis() - start < 500) {
    if (!tickReady()) continue;
    for (uint8_t i = 0; i < NCH; i++) {
      if (!present[i]) continue;
      SPI.beginTransaction(ads1220::SPI_CFG);
      digitalWrite(CS[i], LOW);
      SPI.transfer(ads1220::CMD_RDATA);
      uint32_t v = (uint32_t)SPI.transfer(0) << 16;
      v |= (uint32_t)SPI.transfer(0) << 8;
      v |= SPI.transfer(0);
      digitalWrite(CS[i], HIGH);
      SPI.endTransaction();
      raw[i][got] = v;
    }
    got++;
    if (present[0])
      while (digitalRead(DRDY_PIN) == LOW && millis() - start < 500) {}  // wait for DRDY to clear
  }
  char buf[48];
  for (uint8_t i = 0; i < NCH; i++) {
    if (!present[i]) continue;
    for (int k = 0; k < got; k++) {
      int32_t sv = (raw[i][k] & 0x800000) ? (int32_t)(raw[i][k] | 0xFF000000) : (int32_t)raw[i][k];
      snprintf(buf, sizeof buf, "X,%s,%d,%06lX,%ld", NAMES[i], k, (unsigned long)raw[i][k], (long)sv);
      report(buf);
    }
  }
  if (got < N) report("E,raw dump: fewer than 16 ticks (DRDY?)");
}

void sendWindow(uint32_t now) {
  noInterrupts();
  uint32_t drdy = drdyCount;
  drdyCount = 0;
  interrupts();
  static char line[640];
  int len = snprintf(line, sizeof line, "S,%lu,%lu,%lu", (unsigned long)now, (unsigned long)ticks,
                     (unsigned long)drdy);
  for (uint8_t i = 0; i < NCH; i++) {
    const Acc &a = acc[i];
    if (!present[i] || a.n == 0) continue;
    double mean = (double)a.sum / a.n;
    double var = a.sumsq / a.n - mean * mean;
    // Integers only: the Zephyr libc used here may not format floats.
    len += snprintf(line + len, sizeof line - len, ",%s:%lu:%ld:%ld:%ld:%ld:%lu", NAMES[i],
                    (unsigned long)a.n, (long)(mean >= 0 ? mean + 0.5 : mean - 0.5),
                    (long)(var > 0 ? sqrt(var) + 0.5 : 0), (long)a.vmin, (long)a.vmax, (unsigned long)a.rep);
  }
  report(line);  // one line per window: each Monitor call blocks the loop
}

void setup() {
  for (uint8_t cs : CS) {
    pinMode(cs, OUTPUT);
    digitalWrite(cs, HIGH);  // deselect everything before SPI starts
  }
  pinMode(DRDY_PIN, INPUT_PULLUP);  // reads high (never ready) if DRDY isn't connected
  attachInterrupt(digitalPinToInterrupt(DRDY_PIN), onDrdy, FALLING);
  Monitor.begin();
  SPI.begin();
  delay(50);
  report("# ads1220_all: 8 chip-selects (L1-L4 D3-D6, R1-R3 D7-D9, R4 A2), paced by L1 DRDY on D2");
  checkAll();
}

void loop() {
  uint32_t now = millis();
  if (now - lastKeyPoll >= KEY_POLL_MS) {
    lastKeyPoll = now;
    if (Monitor.available()) {
      int c = Monitor.read();
      if (c == 'd') cfg = ads1220::CFG;
      if (c == 's') cfg = ads1220::CFG_SINGLE_ENDED;
      if (c == 'r' || c == 'd' || c == 's') checkAll();
      if (c == 'v') voltageCheck();
      if (c == 'x') rawDump();
      now = millis();
    }
  }
  if (tickReady()) {
    for (uint8_t i = 0; i < NCH; i++) {
      if (!present[i]) continue;
      int32_t v = ads1220::read(CS[i]);
      Acc &a = acc[i];
      a.sum += v;
      a.sumsq += (double)v * v;
      if (v < a.vmin) a.vmin = v;
      if (v > a.vmax) a.vmax = v;
      if (v == a.last) a.rep++;
      a.last = v;
      a.n++;
    }
    ticks++;
  }
  if (now - windowStart >= WINDOW_MS) {
    sendWindow(now);
    resetAcc();
    windowStart = millis();
  }
}
