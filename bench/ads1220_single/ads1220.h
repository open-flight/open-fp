// ADS1220 24-bit ADC driver: one board per chip-select pin on a shared SPI bus.
// Register values and commands: docs/PROJECT_INIT.md §8.2.
#pragma once
#include <Arduino.h>
#include <SPI.h>
#include <string.h>

namespace ads1220 {
constexpr uint8_t CMD_RESET = 0x06, CMD_START = 0x08, CMD_RDATA = 0x10;
constexpr uint8_t CMD_WREG_ALL = 0x43, CMD_RREG_ALL = 0x23;  // registers 0..3
// AIN0/AIN1, gain 128, PGA on | 1000 SPS normal, continuous | external ref REFP0/REFN0 | DRDY pin only
constexpr uint8_t CFG[4] = {0x0E, 0xC4, 0x40, 0x00};
// Bench only: AIN0 vs AVSS, gain 1, PGA bypassed (register 0 = MUX 1000, gain 000, bypass 1).
// Measures the cell's centre tap against ground, so it works before R1/R2 complete the bridge.
constexpr uint8_t CFG_SINGLE_ENDED[4] = {0x81, 0xC4, 0x40, 0x00};
static const SPISettings SPI_CFG(2000000, MSBFIRST, SPI_MODE1);

inline void command(uint8_t cs, uint8_t c) {
  SPI.beginTransaction(SPI_CFG);
  digitalWrite(cs, LOW);
  SPI.transfer(c);
  digitalWrite(cs, HIGH);
  SPI.endTransaction();
}

// Reset, write `cfg`, read it back into `rb`. Returns true if the readback matches.
inline bool configure(uint8_t cs, const uint8_t cfg[4], uint8_t rb[4]) {
  command(cs, CMD_RESET);
  delay(2);
  SPI.beginTransaction(SPI_CFG);
  digitalWrite(cs, LOW);
  SPI.transfer(CMD_WREG_ALL);
  for (int i = 0; i < 4; i++) SPI.transfer(cfg[i]);
  digitalWrite(cs, HIGH);
  SPI.endTransaction();
  SPI.beginTransaction(SPI_CFG);
  digitalWrite(cs, LOW);
  SPI.transfer(CMD_RREG_ALL);
  for (int i = 0; i < 4; i++) rb[i] = SPI.transfer(0x00);
  digitalWrite(cs, HIGH);
  SPI.endTransaction();
  return memcmp(rb, cfg, 4) == 0;
}

inline int32_t read(uint8_t cs) {
  SPI.beginTransaction(SPI_CFG);
  digitalWrite(cs, LOW);
  SPI.transfer(CMD_RDATA);
  uint32_t v = (uint32_t)SPI.transfer(0) << 16;
  v |= (uint32_t)SPI.transfer(0) << 8;
  v |= SPI.transfer(0);
  digitalWrite(cs, HIGH);
  SPI.endTransaction();
  if (v & 0x800000) v |= 0xFF000000;  // sign-extend 24 -> 32 bits
  return (int32_t)v;
}
}  // namespace ads1220
