# Wiring

This is the step-by-step wiring guide for 8 load cells, 8 ADS1220 boards, and the UNO Q. The design rationale is in [`PROJECT_INIT.md` §7](PROJECT_INIT.md#7-electrical). Pin assignments were checked against the installed UNO Q core (`arduino:zephyr` 1.0.0) on 2026-09-23; see [`VERIFIED.md`](VERIFIED.md).

> **Changed from the original spec: R4's chip select is on A2, not D10.** On the UNO Q, D10 (PB9) is the SPI bus's hardware chip-select pin. `SPI.begin()` takes it over and pulls it low during every transfer, so a board on D10 would talk over the others. Leave D10 unconnected.

Work in this order. Wire and test **one corner (L1) completely** before building the other seven.

1. [Tools and parts](#1-tools-and-parts)
2. [Identify and label each load cell](#2-identify-and-label-each-load-cell)
3. [Put JST-XH plugs on the cells](#3-put-jst-xh-plugs-on-the-cells)
4. [Make the 8 cable runs](#4-make-the-8-cable-runs)
5. [Prepare each ADS1220 board](#5-prepare-each-ads1220-board)
6. [Complete each bridge with two 1 kΩ resistors](#6-complete-each-bridge-with-two-1-kω-resistors)
7. [Connect the cable to the ADC board](#7-connect-the-cable-to-the-adc-board)
8. [Wire the shared bus to the UNO Q](#8-wire-the-shared-bus-to-the-uno-q)
9. [Check before power](#9-check-before-power)
10. [First power-up](#10-first-power-up)

---

## Pin map (reference)

| Signal | UNO Q pin | Goes to |
|---|---|---|
| SCK | D13 | SCLK on all 8 boards |
| MOSI | D11 | DIN on all 8 boards |
| MISO | D12 | DOUT on all 8 boards |
| DRDY | D2 | **DRDY of L1 only** |
| CS L1 · L2 · L3 · L4 | D3 · D4 · D5 · D6 | CS of that board |
| CS R1 · R2 · R3 | D7 · D8 · D9 | CS of that board |
| CS R4 | **A2** | CS of R4 |
| 3V3 | 3V3 | AVDD, DVDD, REFP0 on all 8, and the top of every bridge |
| GND | GND | AVSS, DGND, REFN0 on all 8, and the bottom of every bridge |
| — | D10 | **nothing** (SPI hardware chip-select) |
| — | D0, D1 | **nothing** (MCU console serial) |

Channel, position, and CS pin together:

| Ch | ID | Plate | Corner | CS pin | Stripboard carrier |
|---|---|---|---|---|---|
| 0 | L1 | L | toe, outer | D3 | plate L |
| 1 | L2 | L | toe, inner | D4 | plate L |
| 2 | L3 | L | heel, inner | D5 | plate L |
| 3 | L4 | L | heel, outer | D6 | plate L |
| 4 | R1 | R | toe, inner | D7 | plate R |
| 5 | R2 | R | toe, outer | D8 | plate R |
| 6 | R3 | R | heel, outer | D9 | plate R |
| 7 | R4 | R | heel, inner | A2 | plate R |

---

## 1. Tools and parts

- Multimeter with continuity and resistance modes, soldering iron, flush cutters, wire strippers, JST-XH crimper, heat gun.
- 8 load cells, 8 ADS1220 boards, 16 × 1 kΩ 0.1 % resistors, the 5 m shielded 4-core cable, the JST-XH kit, 22–24 AWG hookup wire, heat-shrink, and labels.
- Optional: 8 × 10 kΩ resistors as chip-select pull-ups (step 8).

**Label everything as you go.** Put the channel ID (L1…R4) on the cell, both ends of its cable, its ADC board, and its CS wire. Most bring-up problems in an 8-channel build are two swapped channels.

## 2. Identify and label each load cell

Each cell has 3 wires: two ends of a pair of strain gauges (excitation), and the centre tap between them (signal). Don't trust the colors. Measure:

1. Measure the resistance between each pair of wires. One pair reads about **2 kΩ**: those are the two **ends**. The other two pairs read about **1 kΩ**.
2. The wire that isn't in the 2 kΩ pair is the **centre tap, S**.
3. Call one end **E+** and the other **E−**. On the cells in this build (red/black/white), **red is the centre tap S**, and white and black are the ends. That was confirmed on L1, where wiring white as S put AIN0 at the 3.3 V rail. Still check each cell with the meter. If you guess E+/E− backwards, that channel reads negative under load, which is fixed in software (`signs` in config). Just be consistent.
4. Record each cell here and put a label on its lead:

| Ch | ID | E+ color | E− color | S color | End-to-end (Ω) | Sign (config) | Notes |
|---|---|---|---|---|---|---|---|
| 0 | L1 | white or black | the other | **red** | | | red is S on these cells (confirmed 2026-09-25) |
| 1 | L2 | | | | | | |
| 2 | L3 | | | | | | |
| 3 | L4 | | | | | | |
| 4 | R1 | | | | | | |
| 5 | R2 | | | | | | |
| 6 | R3 | | | | | | |
| 7 | R4 | | | | | | |

## 3. Put JST-XH plugs on the cells

The connector at the cradle lets you swap a cell without de-soldering. Use the same pinout everywhere:

| XH pin | Signal |
|---|---|
| 1 | E+ |
| 2 | E− |
| 3 | S |
| 4 | unused |

1. Crimp XH female terminals onto the cell's three wires and click them into a 4-way XH housing in the order above. Tug each one to check it's locked.
2. JST-XH is a wire-to-board connector, so the cable side needs the **male XH header**. Solder each cable conductor to a header pin and put heat-shrink over every joint (step 4). If your kit came with pre-made mating pigtails, use those instead.
3. Mark pin 1 on both halves with a paint dot so they're never plugged in flipped.

## 4. Make the 8 cable runs

Cable runs go from the cradle's JST under the plate to the enclosure (there's 14 mm of clearance under the plate).

| Corners | Length (JST to ADC) | Count |
|---|---|---|
| inner (L2, L3, R1, R4) | ~250 mm | 4 |
| outer (L1, L4, R2, R3) | ~450 mm | 4 |

That uses about 2.8 m of the 5 m cable. Cut each run 30–50 mm long so there's slack for re-terminating.

Pick one color scheme for the 4 cores and keep it for all 8 runs. Matching the cell's own colors avoids mix-ups at the JST, for example:

| Core | Signal |
|---|---|
| white | E+ (XH pin 1), same as the cell's white |
| black | E− (XH pin 2), same as the cell's black |
| red | S (XH pin 3), same as the cell's red centre tap |
| remaining color | spare, cut back and insulate at both ends |
| shield/drain | GND at the **ADC end only** |

1. At the **cradle end**, solder white, black, and red to XH header pins 1, 2, 3. Heat-shrink each pin. Cut the shield back flush and cover it with heat-shrink, because it must **not** connect at this end.
2. At the **ADC end**, thread the cable through its enclosure wall slot first (the slot is 6 × 6.7 mm, so nothing wider than the cable can pass), then strip about 30 mm of jacket, twist the shield/drain into a pigtail, and heat-shrink it up to where it'll reach GND.
3. Label both ends.

## 5. Prepare each ADS1220 board

Generic ADS1220 modules vary, so check yours before soldering anything and write the answers in [`VERIFIED.md`](VERIFIED.md) (item 7).

1. **Find these pins on the silkscreen:** CS, SCLK, DIN (labelled MOSI on this build's breakout), DOUT (MISO), DRDY, AVDD, DVDD, AGND and DGND (split on this build's breakout, so wire both), AIN0, AIN1, REFP0, REFN0, and CLK.
2. **Power:** check whether the board has a voltage regulator (a small 3- or 5-pin chip near the power pins). If it has a regulator that expects 5 V, **stop**: powering it from 3V3 may not work, and the reference would no longer match the bridge supply. Record it and ask before continuing.
3. **CLK:** if CLK is broken out and isn't already tied to ground on the board, connect it to GND. This selects the internal oscillator. If it's not broken out, the board already handles it.
4. **REFP0 / REFN0:** some modules tie REFP0 to AVDD and REFN0 to GND on the board. Check with continuity. If they aren't tied, you'll wire them in step 7.
5. Fit the breakout's straight pin headers, pins down, only when it goes onto its carrier: the carrier solders them into the stripboard ([`harness.md`](harness.md)). Never fit sockets; they add ~8.5 mm and won't fit under the lid (14.5 mm from the ADC pad).
6. Label the board L1…R4.

## 6. Complete each bridge with two 1 kΩ resistors

A load cell is only half of a Wheatstone bridge. Two matched 1 kΩ resistors form the other half and give a reference voltage (about 1.65 V) on AIN1. The ADC measures the small difference between the cell's centre tap (AIN0) and that reference.

Solder the two resistors **directly on the ADC board**, so both sit at the same temperature:

```
3V3 ── R1 (1 kΩ 0.1 %) ──┬── R2 (1 kΩ 0.1 %) ── GND
                         │
                        AIN1
```

- R1 goes from the 3V3/AVDD pad to AIN1. R2 goes from AIN1 to the GND/AVSS pad.
- Keep the leads short and heat-shrink them. Use two resistors from the same batch on each board.

## 7. Connect the cable to the ADC board

Full wiring for one corner (repeat ×8):

```
                 UNO Q 3V3 ─────┬──────────────┬───────────── AVDD, DVDD, REFP0
                                │              │
   cable white (E+) ────────────┘             R1 1 kΩ
                                               │
   cable red  (S) ──────────── AIN0            ├──────────── AIN1
                                               │
   cable black (E−) ────────────┐             R2 1 kΩ
                                │              │
                 UNO Q GND ─────┴──────────────┴───────────── AVSS/DGND, REFN0
   cable shield ─────────────── GND  (this end only)
```

1. **White (E+)** goes to the board's 3V3/AVDD pad, the same node as the top of R1.
2. **Black (E−)** goes to the board's GND pad, the same node as the bottom of R2.
3. **Red (S)** goes to **AIN0**. Red is the centre tap on this build's cells (§3); check yours with the meter.
4. **Shield** goes to GND.
5. If step 5 found REFP0/REFN0 not tied on the board, jumper **REFP0 to 3V3** and **REFN0 to GND** at the board. This makes the measurement ratiometric, so supply drift cancels out.
6. Leave AIN2 and AIN3 unconnected.

## 8. Build the two ADC carriers and the harness

The full harness has its own step-by-step guide with diagrams: **[`harness.md`](harness.md)**.

1. **Build 8 identical units.** Each is a breakout, R1/R2, and its cell cable soldered straight on (the JST is at the cradle, §3). Each exposes 6 wires (DRDY too on L1).
2. **Mount 4 units per carrier.** Each carrier has 5 bus rails with BUS IN / BUS OUT headers.
3. **Chain it all together:** Q → plate L carrier → plate R carrier on the bus, plus a chip-select bundle to each carrier. Each unit's CS pin must match the corner its cell is at (pin map above).

That's 14 UNO Q pins, one wire each. **Nothing goes to D10, D0 or D1, and only L1's DRDY is wired (to D2).** Whether 4 breakouts fit side by side on a pad depends on the breakout's size, which is still open (VERIFIED item 7). If they don't fit, mount them in two stacked pairs, as §6.7 of the spec allows.

## 9. Check before power

With the UNO Q **unplugged**:

- [ ] Continuity: each CS pin on the UNO Q reaches **only** its own board's CS pad (D3→L1 … D9→R3, A2→R4).
- [ ] No continuity from D10, D0, or D1 to anything.
- [ ] No short between 3V3 and GND. Each corner is 1 kΩ (the cell's 2 kΩ in parallel with R1+R2), so with all 8 connected expect about **125 Ω**, plus a little for the boards. Near 0 Ω means a short.
- [ ] Only L1's DRDY connects to D2. No other DRDY pad connects to anything.
- [ ] Each cable's shield connects to GND at the ADC end and to **nothing** at the cradle end.
- [ ] Each board's AIN0 reaches its cell's centre tap through the JST, and AIN1 sits at the R1/R2 junction.

## 10. First power-up

1. Plug in the UNO Q over USB-C.
2. On each board, measure **AIN0 to GND** and **AIN1 to GND**. Both should read close to **1.65 V** with nobody on the plates. Then measure **AIN0 to AIN1** directly: it should be within about 10 mV. More than ~20 mV uses up too much of the ADC's ±25.8 mV input range, so record it and check that cell's wiring.
3. Pressing a cell by hand moves AIN0 by well under 1 mV. Most multimeters won't show that, so don't worry if you see nothing. The bench sketch in step 5 shows it clearly as thousands of counts.
4. If a board's AIN0 sits at 0 V or 3.3 V, the centre tap isn't connected or E+/E− isn't connected. Recheck step 7.
5. Then run the one-cell bench test: [`bench-single-cell.md`](bench-single-cell.md). It flashes `bench/ads1220_single`, checks the register readback, and measures the unloaded reading, noise and press response.
