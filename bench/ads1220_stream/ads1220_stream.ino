// Live stream of all 8 ADS1220s as 200 Hz frames, for tools/bench/live_plates.py (the app's UI
// on real plates before the production firmware exists). Wiring: docs/harness.md.
//
// Every board is read on each tick (L1's DRDY, ~1 kHz; a 1 ms timer if L1 is missing) and the
// reads are averaged into 5 ms frames, the rate app/python/open_fp expects. A frame with no
// fresh read (the loop was blocked printing) repeats the previous one. Ten frames go out per line:
//   B,<seq>,<t_first_us>,<period_us>,<flags>,<hex>   hex = 10 frames x 8 channels x 6 hex digits
//                                                     (24-bit two's complement, L1..R4 per frame)
//   R,<ch>,<ok 0|1>,<reg0>,<reg1>,<reg2>,<reg3>       readback, on start and on 'r'
// flags as in protocol.py: 0x01 = no read from any board for 50 ms, 0x02 = a board at full scale.
// Keys: 'r' re-check every board (the stream pauses for a moment).
#include <Arduino_RouterBridge.h>
#include <SPI.h>
#include "ads1220.h"

constexpr uint8_t NCH = 8;
const char *const NAMES[NCH] = {"L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4"};
const uint8_t CS[NCH] = {3, 4, 5, 6, 7, 8, 9, A2};  // docs/harness.md; never D10 (SPI NSS)
constexpr uint8_t DRDY_PIN = 2;                      // L1's DRDY only
constexpr uint32_t PERIOD_US = 5000;                 // 200 Hz frames
constexpr uint8_t FRAMES_PER_LINE = 10;              // 20 lines/s: each Monitor call blocks ~13 ms
constexpr uint8_t STALE_FRAMES = 10;                 // 50 ms without a read sets FLAG_NO_READS
constexpr uint32_t KEY_POLL_MS = 200;
constexpr uint32_t TIMER_TICK_US = 1000;
constexpr int32_t SATURATED = 8388000;
constexpr uint8_t FLAG_NO_READS = 0x01, FLAG_SATURATION = 0x02;

bool present[NCH];
int64_t sum[NCH];
uint16_t reads = 0;          // ticks in the current frame (every present board is read per tick)
uint8_t staleFrames = 0;
int32_t held[NCH];           // last frame, repeated when a frame has no reads
int32_t frames[FRAMES_PER_LINE][NCH];
uint8_t nFrames = 0, flags = 0;
uint32_t seq = 0, tFirst = 0, frameStart = 0, lastKeyPoll = 0, lastTimerTick = 0;

void checkAll() {
  char buf[48];
  for (uint8_t i = 0; i < NCH; i++) {
    uint8_t rb[4];
    present[i] = ads1220::configure(CS[i], ads1220::CFG, rb);
    snprintf(buf, sizeof buf, "R,%s,%d,%02X,%02X,%02X,%02X", NAMES[i], present[i] ? 1 : 0, rb[0], rb[1],
             rb[2], rb[3]);
    Monitor.println(buf);
  }
  for (uint8_t i = 0; i < NCH; i++)
    if (present[i]) ads1220::command(CS[i], ads1220::CMD_START);
  // restart the stream: a new batch from now, so frame times stay true
  nFrames = 0;
  reads = 0;
  flags = 0;
  for (uint8_t i = 0; i < NCH; i++) sum[i] = 0;
  frameStart = micros();
}

bool tickReady() {
  if (present[0]) return digitalRead(DRDY_PIN) == LOW;
  uint32_t now = micros();
  if (now - lastTimerTick >= TIMER_TICK_US) {
    lastTimerTick = now;
    return true;
  }
  return false;
}

void sendLine() {
  static char line[48 + FRAMES_PER_LINE * NCH * 6];
  int len = snprintf(line, sizeof line, "B,%lu,%lu,%lu,%u,", (unsigned long)seq, (unsigned long)tFirst,
                     (unsigned long)PERIOD_US, (unsigned)flags);
  static const char HEX_DIGITS[] = "0123456789ABCDEF";
  for (uint8_t f = 0; f < nFrames; f++)
    for (uint8_t i = 0; i < NCH; i++) {
      uint32_t v = (uint32_t)frames[f][i] & 0xFFFFFF;
      for (int s = 20; s >= 0; s -= 4) line[len++] = HEX_DIGITS[(v >> s) & 0xF];
    }
  line[len] = '\0';
  Monitor.println(line);  // blocks the loop; the frames it covers repeat the last value
  seq++;
  nFrames = 0;
  flags = 0;
}

// Close the frame that started at frameStart.
void closeFrame() {
  if (reads == 0) {
    if (staleFrames < 255) staleFrames++;
  } else {
    staleFrames = 0;
  }
  for (uint8_t i = 0; i < NCH; i++) {
    if (reads > 0) {
      int64_t s = sum[i];
      held[i] = present[i] ? (int32_t)((s >= 0 ? s + reads / 2 : s - reads / 2) / reads) : 0;
    }
    if (held[i] >= SATURATED || held[i] <= -SATURATED) flags |= FLAG_SATURATION;
    frames[nFrames][i] = held[i];
    sum[i] = 0;
  }
  if (staleFrames >= STALE_FRAMES) flags |= FLAG_NO_READS;
  if (nFrames == 0) tFirst = frameStart;
  nFrames++;
  reads = 0;
  frameStart += PERIOD_US;
  if (nFrames == FRAMES_PER_LINE) sendLine();
}

void setup() {
  for (uint8_t cs : CS) {
    pinMode(cs, OUTPUT);
    digitalWrite(cs, HIGH);  // deselect everything before SPI starts
  }
  pinMode(DRDY_PIN, INPUT_PULLUP);
  Monitor.begin();
  SPI.begin();
  delay(50);
  Monitor.println("# ads1220_stream: 8 boards as 200 Hz frames, 10 per line");
  for (uint8_t i = 0; i < NCH; i++) held[i] = 0;
  checkAll();
}

void loop() {
  uint32_t now = millis();
  if (now - lastKeyPoll >= KEY_POLL_MS) {
    lastKeyPoll = now;
    if (Monitor.available() && Monitor.read() == 'r') checkAll();
  }
  if (tickReady()) {
    for (uint8_t i = 0; i < NCH; i++)
      if (present[i]) sum[i] += ads1220::read(CS[i]);
    reads++;
  }
  // Close every frame whose 5 ms is over, including ones the Monitor call blocked.
  while ((uint32_t)(micros() - frameStart) >= PERIOD_US) closeFrame();
}
