// SPI bus diagnostic for the ADC carrier: bit-bangs the bus (no SPI peripheral) and checks who
// drives MISO. Every 3 s, one block of lines:
//   P,A4,<pu>,<pd>                           control pin with nothing on it: must read 1,0
//   I,<idle_pullup>,<idle_pulldown>          MISO with every CS high: 1,0 = floating (good)
//   C,<ch>,<pu>,<pd>,<r0>,<r1>,<r2>,<r3>,<r0'>,<r1'>,<r2'>,<r3'>
//       with that CS low: MISO level under pull-up/pull-down (same = a chip drives it), then the
//       4 config registers read with the pull-up and again with the pull-down (equal = real data)
// Wiring: docs/harness.md. Flash: tools/bench/flash.sh bench/spi_diag
#include <Arduino_RouterBridge.h>

constexpr uint8_t SCK_PIN = 13, MOSI_PIN = 11, MISO_PIN = 12;
const char *const NAMES[8] = {"L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4"};
const uint8_t CS[8] = {3, 4, 5, 6, 7, 8, 9, A2};

// SPI mode 1: the ADS1220 shifts out on the rising edge and samples on the falling edge.
uint8_t xfer(uint8_t out) {
  uint8_t in = 0;
  for (int b = 7; b >= 0; b--) {
    digitalWrite(SCK_PIN, HIGH);
    digitalWrite(MOSI_PIN, (out >> b) & 1);
    delayMicroseconds(5);
    digitalWrite(SCK_PIN, LOW);
    in = (in << 1) | digitalRead(MISO_PIN);
    delayMicroseconds(5);
  }
  return in;
}

int level(uint8_t mode) {
  pinMode(MISO_PIN, mode);
  delayMicroseconds(200);
  return digitalRead(MISO_PIN);
}

void readRegs(uint8_t cs, uint8_t *r) {
  digitalWrite(cs, LOW);
  delayMicroseconds(5);
  xfer(0x23);  // RREG, registers 0-3
  for (int i = 0; i < 4; i++) r[i] = xfer(0x00);
  digitalWrite(cs, HIGH);
  delayMicroseconds(5);
}

void setup() {
  for (uint8_t cs : CS) {
    pinMode(cs, OUTPUT);
    digitalWrite(cs, HIGH);
  }
  pinMode(SCK_PIN, OUTPUT);
  digitalWrite(SCK_PIN, LOW);
  pinMode(MOSI_PIN, OUTPUT);
  digitalWrite(MOSI_PIN, LOW);
  Monitor.begin();
  delay(50);
  for (uint8_t cs : CS) {  // reset every chip so the readback is the power-on default
    digitalWrite(cs, LOW);
    xfer(0x06);
    digitalWrite(cs, HIGH);
  }
  delay(5);
}

void loop() {
  static char line[160];
  // control: an unconnected pin must read 1,0, or the pull-down isn't working on this core
  pinMode(A4, INPUT_PULLUP);
  delayMicroseconds(200);
  int cpu = digitalRead(A4);
  pinMode(A4, INPUT_PULLDOWN);
  delayMicroseconds(200);
  snprintf(line, sizeof line, "P,A4,%d,%d", cpu, digitalRead(A4));
  Monitor.println(line);
  snprintf(line, sizeof line, "I,%d,%d", level(INPUT_PULLUP), level(INPUT_PULLDOWN));
  Monitor.println(line);
  for (uint8_t i = 0; i < 8; i++) {
    digitalWrite(CS[i], LOW);
    delayMicroseconds(20);
    int pu = level(INPUT_PULLUP), pd = level(INPUT_PULLDOWN);
    digitalWrite(CS[i], HIGH);
    uint8_t a[4], b[4];
    pinMode(MISO_PIN, INPUT_PULLUP);
    readRegs(CS[i], a);
    pinMode(MISO_PIN, INPUT_PULLDOWN);
    readRegs(CS[i], b);
    snprintf(line, sizeof line, "C,%s,%d,%d,%02X,%02X,%02X,%02X,%02X,%02X,%02X,%02X", NAMES[i], pu, pd,
             a[0], a[1], a[2], a[3], b[0], b[1], b[2], b[3]);
    Monitor.println(line);
  }
  delay(3000);
}
