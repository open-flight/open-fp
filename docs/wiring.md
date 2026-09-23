# Wiring

The full spec is in [`PROJECT_INIT.md` §7](PROJECT_INIT.md#7-electrical). This page records the wiring as it is actually built.

## UNO Q pin map

| Signal | UNO Q pin | Connects to |
|---|---|---|
| SCK | D13 | SCLK on all 8 ADS1220 |
| MOSI | D11 | DIN on all 8 |
| MISO | D12 | DOUT/DRDY on all 8 (tri-stated when CS high) |
| DRDY (pace) | D2 | **DRDY of L1 only**; never tie DRDY pins together |
| CS L1–L4 | D3, D4, D5, D6 | CS of L1, L2, L3, L4 |
| CS R1–R4 | D7, D8, D9, D10 | CS of R1, R2, R3, R4 |
| 3V3 | 3V3 | AVDD, DVDD, REFP0 on all 8; top of every bridge |
| GND | GND | AVSS/DGND, REFN0 on all 8; bottom of every bridge |

## Load cell wire identification (§6.3)

Measure the resistance between each pair of wires. The pair that reads about 2 kΩ is excitation (E+/E−). The remaining wire is the signal (S). Go by the meter reading, not the wire colors.

JST-XH plug pinout: 1 E+, 2 E−, 3 S, 4 unused.

| Ch | ID | E+ color | E− color | S color | Sign (config) | Notes |
|---|---|---|---|---|---|---|
| 0 | L1 | | | | | |
| 1 | L2 | | | | | |
| 2 | L3 | | | | | |
| 3 | L4 | | | | | |
| 4 | R1 | | | | | |
| 5 | R2 | | | | | |
| 6 | R3 | | | | | |
| 7 | R4 | | | | | |

## Checklist

- [ ] Continuity: each CS pin reaches only its board.
- [ ] No short between 3V3 and GND with all boards connected.
- [ ] With no load, each AIN0/AIN1 pair sits near 1.65 V (bridge balanced).
- [ ] Only the L1 DRDY is wired, to D2.
- [ ] Each shield/drain is connected to GND at the ADC end only.
