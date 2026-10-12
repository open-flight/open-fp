# System wiring, step by step

How 8 load cells, 8 ADS1220 breakouts and the UNO Q connect. The build is in three steps:

1. **Build 8 identical units.** A unit is one breakout, its two bridge resistors, and a socket for its cell.
2. **Mount 4 units on each of two carriers.** A carrier is a perfboard whose 5 bus rails join its units.
3. **Chain the carriers to the UNO Q.** One bus runs from the Q to the toe carrier and on to the heel carrier. Each carrier also gets a bundle of chip-select wires.

Test each unit on the bench before it goes on a carrier: see [`bench-single-cell.md`](bench-single-cell.md). Pin assignments and the reasoning behind them are in [`wiring.md`](wiring.md).

## 1. Build a unit (×8)

![Step 1: one unit](img/harness-1-unit.svg)

A unit is the one-cell bench circuit with the UNO Q replaced by a **6-wire connector**: **3V3, GND, SCLK, MOSI, MISO, CS**. Unit L1 also has **DRDY**. Everything else stays on the unit:

- **Supplies and grounds:** DVDD and AVDD go to 3V3; DGND and AGND go to GND. Both of each pair.
- **Reference:** REFP0 goes to 3V3, REFN0 to GND. The ADC then measures relative to its own supply, so supply drift cancels.
- **CLK** goes to GND, selecting the internal oscillator.
- **R1 and R2 (1 kΩ 0.1 %, or any matched equal pair from 680 Ω to 2 kΩ; never mixed values):** AVDD → R1 → AIN1 → R2 → AGND, soldered at the breakout.
- **The cell cable, soldered straight on:** E+ → 3V3, E− → GND, S → AIN0. The plug-in JST is at the cradle, not here ([`wiring.md` §3–4](wiring.md#3-put-jst-xh-plugs-on-the-cells)), so nothing inside the enclosure is taller than the breakouts and a cell swaps without opening the lid. **Red is S** on this build's cells. White/black are E+/E−; swapping them only flips the sign, which is a config setting.
- **The cell cable's shield** goes to GND at this end only.

Label each unit L1…R4 as you build it. Before it goes on a carrier, run the bench test on it (`tools/bench/single_cell.py`). The bench sketch only reads the unit on CS D3, so wire each unit to D3 for its test.

## 2. Put four units on a carrier (×2)

![Step 2: four units on a carrier](img/harness-2-carrier.svg)

Each carrier is a strip of 2.54 mm perfboard:

- **5 bus rails** run the full width: 3V3, GND, SCLK, MOSI, MISO. Use 22 AWG for 3V3 and GND.
- **Each unit taps all 5 rails** with short wires (the dots in the drawing).
- **BUS IN / BUS OUT:** a 5-pin header at each end of the rails. BUS IN takes the bus from the Q (toe carrier) or from the other carrier (heel carrier). BUS OUT passes it on. **This is what lets the carriers chain:** the rails are continuous, so BUS OUT carries the same 5 signals as BUS IN.
- **Along the bottom edge:** each unit's **CS** pin (and L1's **DRDY**), and the three wires of each unit's **cell cable** (E+, E−, S) plus its shield.

| Carrier | Units | CS pins on the UNO Q | Extra |
|---|---|---|---|
| Toe (+y end pad) | L1, L2, R1, R2 | D3, D4, D7, D8 | L1's DRDY → D2 |
| Heel (−y end pad) | L3, L4, R3, R4 | D5, D6, D9, **A2** | BUS OUT not used |

### Building a carrier on stripboard

![Carrier layout on stripboard](img/carrier-stripboard.svg)

The same layout as a [DIY Layout Creator](https://github.com/bancika/diy-layout-creator) project, for editing: [`hardware/carrier-stripboard.diy`](../hardware/carrier-stripboard.diy) (regenerate with `docs/img/make_carrier_diylc.py`; hand edits in DIYLC are lost if you do).

Use single-sided 2.54 mm stripboard, 37 × 17 holes (about 94 × 43 mm). That fits the enclosure between the UNO Q and the lid posts, roughly x = 40–134 mm from centre, overhanging the 90 mm pad a little at each end. Mount it on the pad with short **nylon** standoffs (about 3 mm) through holes in the unused strips I and M. Height is tight: the pad top to the lid is 14.5 mm, and the stack is standoff + 1.6 mm board + ~2.5 mm header spacer + 1.6 mm breakout + the resistors on top, about standoff + 8.5 mm. The pad's inserts sit on a 7.5 mm grid, so only one row of board holes can land on it; drill the board's mounting holes to match the inserts you use. The breakout's pins pair up across the board (AGND|DGND, AVDD|DVDD, …), so with the header columns across the strips:

- **Strip A is the GND rail and strip B the 3V3 rail**, running under all four breakouts and never cut.
- **Strips J, K, L are the SCLK, MOSI and MISO rails.**
- **Strips N and O repeat 3V3 and GND** next to the cable pads, tied to B and A by the links in columns 19 and 10.

Build order:

1. **Cut the strips (✕):**
   - rows C–H at columns 6, 15, 24, 33 (x0+4), which falls between each breakout's two header columns
   - rows C–H at columns 10, 19, 28, between breakouts
   - row P at columns 6, 9, 15, 18, 24, 27, 33, 36 (x0+4 and x0+7), so each unit's S strip is separate

   **The drawing is the component side.** Cutting from the copper side mirrors it: on the copper side, column 1 (BUS IN) is on the **right**. Count columns from that edge. Check every cut with a meter. (The first carrier was cut mirrored; the layout was changed on 2026-10-11 to match that board, which is why the in-unit cut is at x0+4 and SCLK is a diagonal.) A mirrored board also mirrors the **unit order**: L1 ends up where R2 should be. The press test in §5 catches that, and swapping the CS wires at the Q fixes it.
2. **Fit the wire links**, all of them before any breakout, since they run underneath. Per breakout, with x0 = its left header column (2, 11, 20, 29):

   | Link | From | To |
   |---|---|---|
   | REFP0 → 3V3 | x0+1, C | x0+1, B |
   | REFN0 → GND | x0+2, D | x0+2, A |
   | CLK → GND | x0+6, C | x0+6, A |
   | SCLK → rail | x0+6, E | x0+4, J (diagonal; **insulated wire**, it crosses MOSI) |
   | MOSI → rail | x0+5, F | x0+5, K |
   | MISO → rail | x0+6, G | x0+6, L |
   | AIN0 → S | x0+1, H | x0+1, P |

   Plus two tie links: **column 10, A→O** (GND) and **column 19, B→N** (3V3).
3. **Solder the breakouts:** pins down, header spacer underneath, left column (AGND…AIN0) at x0 and right column (DGND…DRDY) at x0+7, rows A–H. Then solder **R1 (AVDD–AIN1) and R2 (AIN1–AGND)** on top of each breakout.
4. **External wires:**
   - the bus into column 1 (BUS IN) and column 37 (BUS OUT) on strips A, B, J, K, L
   - each unit's CS wire onto the **top of its CS pin** (right column, row D), the same way as L1's DRDY. The holes under the breakout are covered once it's soldered on
   - L1's DRDY onto L1's DRDY pin on top
   - each cell cable, threaded through its wall slot first as bare cable: **E+ into (x0+2, N), E− into (x0+2, O), S into (x0+2, P)**. Row Q is spare. Tie each cable to the board or a standoff with a small cable tie so a tug doesn't land on the joints.
   - each cell cable's shield onto strip O

The heel carrier is the same board with L3, L4, R3, R4 (CS ← D5, D6, D9, A2); leave its BUS OUT empty.

Don't use a solderless breadboard for the carriers. A swing shakes the floor, and a loose contact on CS or MISO corrupts readings in ways that are hard to track down.

## 3. Chain the carriers to the UNO Q

![Step 3: the whole system](img/harness-3-system.svg)

Four bundles leave the UNO Q's header area, plus the cell cables:

| # | From | To | Wires |
|---|---|---|---|
| ① | UNO Q **3V3, GND, D13, D11, D12** | toe carrier **BUS IN** | 3V3, GND, SCLK, MOSI, MISO |
| ② | toe carrier **BUS OUT** | heel carrier **BUS IN** | the same 5, chained |
| ③ | UNO Q **D3, D4, D7, D8, D2** | toe carrier bottom edge | CS L1, L2, R1, R2 + L1's DRDY |
| ④ | UNO Q **D5, D6, D9, A2** | heel carrier bottom edge | CS L3, L4, R3, R4 |
| — | each cell, via its JST at the cradle | its unit's cable pads on the carrier (soldered) | ~450 mm outer corners, ~250 mm inner |

That's **14 UNO Q pins, one wire each**. The 5 bus signals reach all 8 units through the chain, not through 8 wires on each pin.

**Never connect:** D10 (the SPI hardware chip select), D0/D1 (the MCU console), or any DRDY other than L1's. DRDY outputs are push-pull and would fight each other.

## 4. Check before power

A guided version of these checks, stage by stage as you build, asks for each meter reading and says what's wrong:

```bash
.venv/bin/python tools/bench/carrier_check.py --units L1 --stage units   # one unit, breakout + R1/R2 fitted
.venv/bin/python tools/bench/carrier_check.py                            # toe carrier, wired to the Q
```

Stages: `bare` (cuts and links), `units` (breakouts and R1/R2), `cables` (cells plugged in), `uno` (wired to the Q, which is unplugged from USB). Each stage includes the ones before it.

With the UNO Q unplugged:

- [ ] **3V3 to GND ≈ 125 Ω.** That's 8 corners of 1 kΩ in parallel. Near 0 Ω is a short.
- [ ] Each CS pin reaches **only** its own unit (D3 → L1 … D9 → R3, A2 → R4).
- [ ] BUS IN and BUS OUT on each carrier show continuity rail by rail, and the heel carrier's rails match the toe carrier's.
- [ ] Only L1's DRDY reaches D2; nothing connects to D10, D0 or D1.
- [ ] Each cable shield connects to GND at the carrier end and to nothing at the cell end.

Then power up and bring units up **one at a time**: plug in one cell's JST at its cradle, check it, then the next. Each unit's bench-tested numbers (noise, readback) are the reference.

## 5. Test the carrier

With the UNO Q plugged into the dev machine by **USB-C** (flashing goes over USB) and on the network:

```bash
tools/bench/flash.sh bench/ads1220_all          # flash the all-channel bench sketch
.venv/bin/python tools/bench/multi_cell.py      # toe carrier: L1, L2, R1, R2
.venv/bin/python tools/bench/multi_cell.py --channels L3,L4,R3,R4   # heel carrier
.venv/bin/python tools/bench/multi_cell.py --channels all           # both
```

It runs four checks, each unit in turn, and ends with a PASS/FAIL table and the reason for every failure:

1. **Who answers.** Each unit must read back its registers on its own CS pin, and nothing may answer on a CS that isn't in `--channels`. If no unit answers, the shared wires are the suspect: 3V3, GND, SCLK (D13), MOSI (D11), MISO (D12) into BUS IN.
2. **Voltages**, measured by each ADC: supply ~3.3 V, reference equal to the supply (the REFP0/REFN0 links), and the cell's centre tap near half supply (the cable's S wire). It also detects R1/R2 (AIN1 at half supply). If every unit has them it measures **differential**, the real configuration; otherwise **single-ended**, which still tests wiring and response. Use `--mode` to force one.
3. **Baseline, hands off:** each unit must be neither stuck (a working ADS1220 always shows some noise; repeating the same value is the fault seen on the second breakout), noisy, at full scale, nor drifting.
4. **Press test, one cell at a time:** the unit you press must move, and **only** that unit. If another unit moves instead, the two cables (or two CS wires) are swapped, and the message names them.

Once every unit passes, watch all four cells live in the browser (each cell's load on a plan of the plates, total, left/right split, a 30 s chart, and a one-step calibration with a known weight):

```bash
.venv/bin/python tools/bench/live_multi.py      # http://localhost:7072
```

Skip the press test with `--no-press`. The sketch paces on L1's DRDY; if L1 is missing it falls back to a 1 ms timer, so the other units can still be tested. `ssh -t arduino@open-fp.local arduino-app-cli monitor` shows the raw output; its keys are listed at the top of `bench/ads1220_all/ads1220_all.ino` (`x` dumps 16 raw reads per unit).

## 6. Pitfalls from the first build

Everything below happened on the first toe carrier (2026-10-11/12). Each fault took a while to find, so here is the symptom each one produced, from `multi_cell.py`, and how it was found. Work through faults **one at a time** and re-run the test after each fix: one fault can hide or imitate another.

### Fault → symptom

| What was wrong | What the test showed | How it was found |
|---|---|---|
| Solder bridge **DVDD–DGND** on top of a breakout | The UNO Q **switches off** as soon as the carrier is connected (3V3 shorted to GND) | 3V3 ↔ GND reads ~0 Ω. Look between each breakout's top two pin pairs |
| Strips **cut mirrored** (cut from the copper side while reading the component-side drawing) | Everything electrically fine, but the press test said **L1↔R2 and L2↔R1 swapped** | Press test. Fixed by swapping the CS wires at the Q (D3↔D8, D4↔D7); the layout was also updated to the mirrored cuts |
| **REFN0 link** not soldered to strip A | Voltage check: REF far from AVDD | Meter: REFN0 pin ↔ AGND should beep |
| **MOSI–MISO** bridge on one unit (rows F/G at its digital header, or strips K/L) | **Every** unit reads back `00 00 00 00`, including ones that passed before; L1's DRDY still ticks (writes still work) | K ↔ L reads 0.3 Ω. Lift each unit's MOSI link from K in turn until K ↔ L opens; the unit whose link clears it has the bridge |
| **DRDY–MISO** bridge on one unit (rows G/H at its digital header) | **Every** unit reads back `FF FF FF FF`; strip L sits at 3.3 V even with every CS high, but L ↔ 3V3 is **not** a short on the meter | `bench/spi_diag` (below) shows MISO driven high with all CS high. Meter: strip L ↔ each unit's DRDY pin; the bridged one reads ~0 Ω. Every breakout's DRDY is always driven, selected or not |
| MISO header joint **cracked** by the rework above | That one unit reads `00 00 00 00`, the rest are fine | Meter: the unit's MISO pin ↔ strip L, then hop by hop: pin → strip G → link → strip L |
| A unit's **R1/R2** not connected, and a weak **REFP0/REFN0** joint | AIN1 0 mV, REF 3100 mV (others 3317) | Reflow the reference links and the resistor joints |
| Stray wire ends on the **underside** touching strips | One unit's AIN0 = 1 mV (S held at ground), pinned at −full scale | P ↔ GND = 0 Ω on the meter. Trim and flatten everything on the copper side |
| **Cold joint** on a cell's E+ (white) wire | Same symptom: AIN0 ≈ 0 mV. Nothing pulls S up, so the bridge drags it to E− | White ↔ red on the bare wire is fine but white ↔ black **at the board** is open: reflow the joint until the solder wets the pad |
| A unit's R1/R2 pair 8 mV off centre | Offset ≈ −2.5 M counts (30 % of range) | Not a fault: a cell only swings ~±3 mV at full load. Use 0.1 % resistors if you want it centred |

### Reading the symptoms

- **All units fail the same way → look at the shared bus first** (strips J/K/L and A/B, the bus wires, or one unit loading the bus). One unit failing → that unit.
- **`00 00 00 00` vs `FF FF FF FF`.** `00` means MISO is held low or tied to MOSI. `FF` means MISO is held high (a DRDY bridge), or no chip is driving it while it floats high. Heel slots with nothing fitted read `00`.
- **DRDY still ticking at ~944 Hz** (the third number on each `S,` line, ×10) means power, SCLK, MOSI and L1's CS all work: L1 accepted its configuration. The fault is on the way back (MISO).
- **AIN0 ≈ 600 mV** with no cell plugged in is just a floating input: expected. **AIN0 ≈ 0** with a cell plugged in means S is at ground: E+ not connected, or S shorted to GND.
- **"noise 0, repeats 100 %"** while pinned at ±8,388,608 is saturation, not a stuck ADC: fix the input (usually AIN0 far from AIN1).

### Using the meter

- **Use ohms, not only the beep.** With chips and capacitors on the board, the continuity beeper can chirp through protection diodes and charging capacitors. A real short reads the same as touching the probes together (~0.3 Ω) **in both probe directions**; a reading that drifts, or changes when you swap the probes, is the circuit, not a short.
- A reading that **jumps up then falls back** on an input with nothing connected is the meter charging the input capacitance. Not a short.
- To localise a short between two rails, **lift one link at a time** and re-measure. On stripboard you can't see along a strip, but you can cut it out of the circuit.

### Soldering

- Use **flux paste** (tan or clear, greasy) to clean up bridges, not **solder paste** (grey, metallic; it adds solder balls). The flux in fresh solder wire also works.
- After any rework, **re-check the neighbouring joints**. Cleaning the DRDY bridge cracked the MISO joint next to it.
- Drag a knife blade along every strip gap near new joints, and brush the copper side clean of solder balls.
- Fit **header pins** (not sockets) when soldering breakouts to stripboard, and keep the copper side tidy. Clipped wire ends and stray strands under the board caused one fault.

### `bench/spi_diag`: who is driving MISO?

When every unit fails readback, flash this instead of `ads1220_all`:

```bash
tools/bench/flash.sh bench/spi_diag
ssh -t arduino@open-fp.local arduino-app-cli monitor
```

It bit-bangs the bus (no SPI peripheral) and every 3 s prints:

- `P,A4,1,0`: a control pin, proving the pull-down works.
- `I,<pull-up>,<pull-down>`: MISO with every CS high. `1,0` is right: nothing drives it. `1,1` means something holds it high (a DRDY bridge). `0,0` means something holds it low (MOSI or GND).
- `C,<unit>,...` per CS: the MISO level and the registers read with each pull. Registers that read the same with both pulls are real data.

Flash `bench/ads1220_all` again afterwards.

### Workflow gotchas

- **Flashing needs USB-C to the Mac**; the tests and live views run over the network (SSH). `flash.sh` says "No UNO Q found on USB" right after the Q is replugged; wait a few seconds and run it again.
- **`Permission denied (publickey)`** from SSH: the key lives in a password manager's SSH agent (1Password here) that has locked. Unlock it and retry.
- A key sent to the sketch in the first second or two after `arduino-app-cli monitor` connects is lost. The tools wait for output before sending.
- The bench loop misses ~30 % of conversions and reads ~10 % twice (`repeats`), because each `Monitor` print blocks it. Expected for the bench sketch; the real firmware batches its output.
