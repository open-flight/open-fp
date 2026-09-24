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

| Ch | ID | Plate | Corner | CS pin | ADC pad in enclosure |
|---|---|---|---|---|---|
| 0 | L1 | L | toe, outer | D3 | +y (toe) end |
| 1 | L2 | L | toe, inner | D4 | +y (toe) end |
| 2 | L3 | L | heel, inner | D5 | −y (heel) end |
| 3 | L4 | L | heel, outer | D6 | −y (heel) end |
| 4 | R1 | R | toe, inner | D7 | +y (toe) end |
| 5 | R2 | R | toe, outer | D8 | +y (toe) end |
| 6 | R3 | R | heel, outer | D9 | −y (heel) end |
| 7 | R4 | R | heel, inner | A2 | −y (heel) end |

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
3. Call one end **E+** and the other **E−**. Typically white/black are the ends and red is the centre, but go by the meter. If you guess E+/E− backwards, that channel reads negative under load, which is fixed in software (`signs` in config). Just be consistent.
4. Record each cell here and put a label on its lead:

| Ch | ID | E+ color | E− color | S color | End-to-end (Ω) | Sign (config) | Notes |
|---|---|---|---|---|---|---|---|
| 0 | L1 | | | | | | |
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

Pick one color scheme for the 4 cores and keep it for all 8 runs, for example:

| Core | Signal |
|---|---|
| red | E+ (XH pin 1) |
| black | E− (XH pin 2) |
| white or green | S (XH pin 3) |
| remaining color | spare, cut back and insulate at both ends |
| shield/drain | GND at the **ADC end only** |

1. At the **cradle end**, solder red, black, and white to XH header pins 1, 2, 3. Heat-shrink each pin. Cut the shield back flush and cover it with heat-shrink, because it must **not** connect at this end.
2. At the **ADC end**, strip about 30 mm of jacket, twist the shield/drain into a pigtail, and heat-shrink it up to where it'll reach GND.
3. Label both ends.

## 5. Prepare each ADS1220 board

Generic ADS1220 modules vary, so check yours before soldering anything and write the answers in [`VERIFIED.md`](VERIFIED.md) (item 7).

1. **Find these pins on the silkscreen:** CS, SCLK, DIN, DOUT (sometimes "DOUT/DRDY"), DRDY, AVDD, DVDD, AVSS/DGND (often a single GND), AIN0, AIN1, REFP0, REFN0, and CLK if it's broken out.
2. **Power:** check whether the board has a voltage regulator (a small 3- or 5-pin chip near the power pins). If it has a regulator that expects 5 V, **stop**: powering it from 3V3 may not work, and the reference would no longer match the bridge supply. Record it and ask before continuing.
3. **CLK:** if CLK is broken out and isn't already tied to ground on the board, connect it to GND. This selects the internal oscillator. If it's not broken out, the board already handles it.
4. **REFP0 / REFN0:** some modules tie REFP0 to AVDD and REFN0 to GND on the board. Check with continuity. If they aren't tied, you'll wire them in step 7.
5. Don't fit pin headers. Solder wires directly to the pads, so everything fits under the enclosure lid (17.5 mm inside height).
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
   cable red  (E+) ─────────────┘             R1 1 kΩ
                                               │
   cable white (S) ─────────── AIN0            ├──────────── AIN1
                                               │
   cable black (E−) ────────────┐             R2 1 kΩ
                                │              │
                 UNO Q GND ─────┴──────────────┴───────────── AVSS/DGND, REFN0
   cable shield ─────────────── GND  (this end only)
```

1. **Red (E+)** goes to the board's 3V3/AVDD pad, the same node as the top of R1.
2. **Black (E−)** goes to the board's GND pad, the same node as the bottom of R2.
3. **White (S)** goes to **AIN0**.
4. **Shield** goes to GND.
5. If step 5 found REFP0/REFN0 not tied on the board, jumper **REFP0 to 3V3** and **REFN0 to GND** at the board. This makes the measurement ratiometric, so supply drift cancels out.
6. Leave AIN2 and AIN3 unconnected.

## 8. Wire the shared bus to the UNO Q

All 8 boards share power and three SPI lines. Each board gets its own CS wire, and **only L1** has DRDY wired.

The enclosure has two ADC pads: toe (+y) with L1, L2, R1, R2, and heel (−y) with L3, L4, R3, R4. The UNO Q sits between them. Run one short bundle from the UNO Q header to each pad and daisy-chain the shared lines across the 4 boards on that pad:

```
            toe pad (+y)                             heel pad (−y)
   ┌──────┬──────┬──────┬──────┐            ┌──────┬──────┬──────┬──────┐
   │  L1  │  L2  │  R1  │  R2  │            │  L3  │  L4  │  R3  │  R4  │
   └──┬───┴──┬───┴──┬───┴──┬───┘            └──┬───┴──┬───┴──┬───┴──┬───┘
      └──────┴──────┴──────┴── 3V3 GND SCK MOSI MISO ──┴──────┴──────┴──────┘
      │  │      │      │      │                   │      │      │      │
     D2 D3     D4     D7     D8                  D5     D6     D9     A2
   (DRDY)                                                        (R4 CS)
                               UNO Q header
```

1. **Power:** 3V3 and GND from the UNO Q to every board. Use 22 AWG for these two runs. The total draw is about 30 mA, so size isn't critical, but a solid ground matters.
2. **SPI:** D13 goes to every SCLK, D11 to every DIN, and D12 to every DOUT. Keep these runs short: about 15 cm total per pad is fine at 2 MHz.
3. **Chip selects:** one wire from each UNO Q pin to its board's CS, per the pin map. **R4 goes to A2. Nothing goes to D10.**
4. **DRDY:** wire **L1's DRDY to D2**. Leave the other seven boards' DRDY pads unconnected. **Never tie DRDY pins together.** They are push-pull outputs and would fight each other.
5. **Optional CS pull-ups:** a 10 kΩ resistor from each CS to 3V3 keeps every board deselected while the MCU boots. The firmware also drives every CS high as its very first action.

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
