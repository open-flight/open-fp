# ADC board (8 × ADS1220, UNO Q shield)

One assembled PCB that replaces the two stripboard ADC carriers, the eight ADS1220 breakouts, the bridge resistors and the whole wire harness. It plugs straight onto the UNO Q like any UNO shield. Each load-cell cable plugs into its own JST-XH socket. PCBWay assembles every part, so you don't solder anything.

**Firmware doesn't change.** The pin map and the ADC configuration (`0E C4 40 00`: AIN0−AIN1, gain 128, PGA on, 1 kSPS turbo, continuous, external reference REFP0/REFN0) are the same as on the stripboard build.

| | |
|---|---|
| Board | 284 × 50 mm (54.7 mm at the header tabs), 2 layers, 1.6 mm FR4, 1 oz |
| Parts | 8 × ADS1220IPWR (on the board itself, not modules), 8 × JST-XH 3-pin side-entry SMT, 4 SMD shield headers, 0603/0805 passives. **All on the underside.** The top has copper and silkscreen only |
| Renders | [`renders/`](renders): top, bottom, 3D |
| Schematic | [`adc-board-schematic.pdf`](adc-board-schematic.pdf) |
| Order files | [`adc-board-gerbers.zip`](adc-board-gerbers.zip), [`assembly/adc-board-bom.csv`](assembly/adc-board-bom.csv), [`assembly/adc-board-centroid.csv`](assembly/adc-board-centroid.csv) |
| Checks | ERC 0 errors 0 warnings; DRC 0 errors, 0 unconnected, schematic parity clean (`kicad-cli`, KiCad 10.0.4) |

## Circuit (one channel; there are eight)

The same circuit as the proven breakout build, with the chip on the board:

- **ADS1220IPWR** (TSSOP-16). AVDD and DVDD go to 3V3, AVSS and DGND to GND. A 100 nF X7R sits at each supply pin, plus 10 µF per channel.
- **Ratiometric reference:** REFP0 goes to 3V3 (the same rail as the cell's E+) and REFN0 to GND, with 100 nF across them at the pins.
- **CLK** goes to GND (internal oscillator). AIN2 and AIN3 are not connected.
- **AIN0 = cell S.** **AIN1** is the midpoint of a 1.5 kΩ / 1.5 kΩ divider (Susumu RG1608P, 0.1 %, 25 ppm/°C thin film, 0603). The two resistors sit side by side next to their ADC, so they share its temperature. AIN1 is about 1.65 V, the same as the stripboard's 1 kΩ pair. Each channel draws about 3.3 mA in total (cell 1.65 mA, divider 1.1 mA, ADC ~0.4 mA), so the whole board draws about 30 mA from the Q's 3V3 pin.
- **Input RC filter (new):** 100 Ω in series with AIN0 and AIN1, 10 nF C0G across them, 1 nF C0G from each to GND. That's a differential corner of about 76 kHz and a common-mode corner of about 1.6 MHz. It keeps RF and SPI edges out of the PGA without touching the 1 kSPS signal.
- **JST-XH 3-pin** per channel. **Pin 1 = E+ (white), pin 2 = E− (black), pin 3 = S (red)**, the same order as the cradle-end JST in [`docs/wiring.md` §3–4](../../../docs/wiring.md#3-put-jst-xh-plugs-on-the-cells). The silkscreen shows the channel name, pin 1 and W/B/R next to every socket, on both sides.
- **Shared SPI.** SCLK, DIN and DOUT/DRDY go to all eight chips; SCLK has a 33 Ω series resistor at the Q. Only **L1's DRDY pin goes to D2**. The other seven DRDY pins are left unconnected (they are push-pull outputs and must never be joined). DOUT goes high-Z while CS is high, so all eight share MISO.
- **3V3 entry:** 10 µF + 100 nF next to the header's 3V3 pin. There's no power LED.

### UNO Q pin map (unchanged)

| Q pin | Net | | Q pin | Net |
|---|---|---|---|---|
| D3 | CS L1 | | D13 | SCLK (via R1 33 Ω) |
| D4 | CS L2 | | D11 | MOSI → DIN |
| D5 | CS L3 | | D12 | MISO ← DOUT |
| D6 | CS L4 | | D2 | DRDY of L1 only |
| D7 | CS R1 | | 3V3 | 3V3 |
| D8 | CS R2 | | GND | GND (three header pins) |
| D9 | CS R3 | | D0, D1, D10 | **not connected** |
| A2 | CS R4 | | everything else | not connected (pins are still fitted, for strength) |

## Layout

- All four shield headers are fitted (1×10, 2× 1×8, 1×6), at the UNO R3 positions (including the 0.16" offset between D7 and D8). The generator checks every pin against the UNO R3 grid.
- Each channel sits beside its wall slot. From the board centre outwards: the ADC, then the RC network and divider, then the JST, whose mouth points along the board toward the slot. The plug lies flat under the board, in a strip kept free of parts.
- SPI and the chip selects run in the middle of the board. Over each channel's analog end (AIN pair, divider, RC, JST), keepouts stop tracks on the top layer and along the board edge, so no SPI line runs over or past AIN0/AIN1. The top layer there is solid ground.
- GND pours on both layers, stitched with about 195 vias. The Gerbers were re-read and rasterized with pygerber 2.4 as a check (outline 284.0 × 54.7 mm, both copper layers).
- Rules: 0.2 mm tracks and clearance (0.4 mm for power). The only exception is tracks entering the ADS1220's 0.65 mm-pitch pins, which may come within 0.15 mm (`adc-board.kicad_dru`). Vias are 0.6/0.3 mm. Copper stays ≥ 0.3 mm from the edge.

## Channel → connector → slot

Slot x positions are in the enclosure frame (+x = toe). The JST mouth is where the plug goes in. The plug body then runs about 10 mm further toward the slot (**VERIFY**).

| Ch | Ref | CS | Plate corner | Wall | Slot x | ADC at x | JST mouth at x |
|---|---|---|---|---|---|---|---|
| L1 | J1, U1 | D3 | toe, outer | +y | +125 | +88 | +110, facing +x |
| L2 | J2, U2 | D4 | toe, inner | +y | +85 | +48 | +70, facing +x |
| L3 | J3, U3 | D5 | heel, inner | +y | −85 | −48 | −70, facing −x |
| L4 | J4, U4 | D6 | heel, outer | +y | −125 | −88 | −110, facing −x |
| R1 | J5, U5 | D7 | toe, inner | −y | +85 | +48 | +70, facing +x |
| R2 | J6, U6 | D8 | toe, outer | −y | +125 | +88 | +110, facing +x |
| R3 | J7, U7 | D9 | heel, outer | −y | −125 | −88 | −110, facing −x |
| R4 | J8, U8 | A2 | heel, inner | −y | −85 | −48 | −70, facing −x |

Each JST is centred 17.8 mm from the board's centreline, on the same side as its wall.

## Stack-up (enclosure frame, z in mm)

The board sits on the Q's headers, so its height is set by the Q. Nothing fits under the current lid, so the enclosure has to grow by 2.4 mm. That's within the 2.6 mm the ramps allow.

| z | What |
|---|---|
| 0 | base underside |
| 2.4 | floor top |
| 5.4 | ADC pad tops (standoffs start here) |
| 7.4 – 9.0 | UNO Q PCB (on its 5 mm bosses) |
| ~12.5 | tallest Q top-side parts (USB-C) |
| 17.5 | top of the Q's female headers (8.5 mm; **VERIFY**) |
| 17.5 – 20.0 | our SMD male headers' plastic body (2.54 mm); posts go down into the Q's headers |
| **20.0 – 21.6** | **this board** |
| ~13.9 – 20.0 | underside parts: JST-XH side-entry (~6.1 mm high, **VERIFY**) and the plug beside it; the TSSOP and passives reach only 18.8 – 20.0 |
| 21.6 | board top: copper and silkscreen only, no parts, no through-hole pins |
| 22.3 | lid underside **after the change below** (0.7 mm air gap) |
| 24.3 | lid top after the change (ceiling 24.5) |

Support: four M2.5 holes at (±54.5, 0) and (±129.5, 0), on the ADC pads' insert grid. Use standoffs **14.5 mm long** (board underside 20.0 − pad top 5.4 = 14.6). Male-female hex standoffs work if the male thread fits the 2.5 mm-deep insert; otherwise use F-F standoffs with a short M2.5 set screw (**VERIFY** the insert depth). There's no room for screw heads on top (0.7 mm gap), so the standoffs only carry the board. The 32 header pins hold it down, and the lid stops it lifting more than 0.7 mm. If you want it clamped, stick a 0.5–0.7 mm rubber or foam dot on the board top over each standoff.

The USB-C cable to the Q runs along the floor/pads under the board (z 5.4 – ~10). Route it beside the two heel standoffs at y = 0. Nothing else under the board comes below z ≈ 13.9.

## Enclosure changes required (don't edit the CAD here; these are for `hardware/cad/src`)

1. **Raise the base walls by 2.4 mm:** wall top z 19.9 → **22.3**. Lid posts (±140, ±23) grow by the same amount, so the M2.5 inserts stay at the top. The lid plate stays 2.0 mm thick, so the outer height goes 21.9 → **24.3** (ramps rise 24.5). The Q bosses, ADC pads and inserts stay as they are.
2. **Cut the lid's locating lip away along both long sides for x −20 … +34.** The board has tabs out to y ±27.35 under the shield headers (x −18 … +32). The SMD header pads need them, because the Q's headers sit only 2.5 mm from its edge. Elsewhere the board stays inside y ±25.0, clear of the lip ring (inner edge ±25.3). After the raise, the lip spans z 20.8 – 22.3 and would hit the tabs (board top 21.6).
3. **Make the eight cable slots taller:** z 2.4 … 9.4 → **z 2.4 … 19.0**, same 6 mm width, at x ±85 and ±125 in both long walls. The plug and cable leave the JST at about z 15 – 18 (just under the board), 7 mm in from the wall, so a tall slot lets the cable run straight out instead of kinking down to the floor. If you'd rather keep the slots, the cable needs an S-bend of about 8 mm in the last 10 mm (**VERIFY** with a real plug).
4. Board corner notches (x beyond ±135.5, |y| beyond 18.5) clear the lid posts. Nothing to change there.

## What changes for you, compared with the stripboard build

- **Nothing in the firmware or config.** Same pins, same registers, same channel order. `signs` in the config still covers E+/E− swaps.
- **No soldering.** At each cable's board end, crimp a 3-way **JST XHP-3** housing (pin 1 white E+, 2 black E−, 3 red S), the same pinout as the cradle end, then thread the cable through its slot. Plug it in before you lower the board onto the Q (the plugs go in sideways, under the board).
- The cable **shield/drain** has no pin on the 3-way XH. Cut it back and insulate it at both ends. If noise turns out worse than on the stripboard, ground the drain at the board end under a standoff screw (**VERIFY** on the bench).
- The bridge resistors are 1.5 kΩ instead of 1 kΩ (same 0.1 % class, now 25 ppm/°C thin film). AIN1 sits at the same ~1.65 V, so the calibration procedure is the same. Recalibrate anyway, as with any new hardware.
- No breakout modules, no headers to solder, no harness, no strip cuts. The bring-up checks in `docs/harness.md` §4–5 still apply. The `bench/spi_diag` sketch and `tools/bench/multi_cell.py` work unchanged.

## Ordering at PCBWay

**PCB:** 2 layers, 284 × 54.7 mm, FR-4 TG150, 1.6 mm, 1 oz outer copper, min track/space 6/6 mil (0.15 mm), min hole 0.3 mm, lead-free HASL (or ENIG for a flatter TSSOP land, about +$10), green mask, white silk, quantity **5**. Upload `adc-board-gerbers.zip` (Gerber X2 + separate PTH/NPTH Excellon, origin at the board's lower-left corner).

**Assembly:** turnkey, quantity **2** (or 3), **single side: bottom** (every part is on the bottom; there are no through-hole parts). Upload `assembly/adc-board-bom.csv` and `assembly/adc-board-centroid.csv`. In the notes:

- "All components on the bottom side. Centroid file is KiCad's, viewed from the top. Please send the placement review (DFM) before production."
- "Samtec TSM headers: please use the -P (pick-and-place pad) version, or an equivalent 2.54 mm SMT male header with 0.64 mm square posts, 2.54 mm body, posts ≥ 5.8 mm, tails alternating."
- "U1–U8 pin 1: dot on silkscreen/fab. J1–J8: JST S3B-XH-SM4-TB(LF)(SN), mouth facing the board end."

Rough cost (prices vary): PCBs about $30–60 for 5. Parts about $110–140 per board (8 × ADS1220 ≈ $55–75, 16 Susumu 0.1 % ≈ $10–15, 4 Samtec TSM ≈ $15–25, JSTs ≈ $5, passives ≈ $3). Assembly setup plus labour about $50–90 for 2 boards. Expect **about $350–450 for 2 assembled boards** plus shipping.

### BOM (12 lines; the full file is `assembly/adc-board-bom.csv`)

| Refs | Qty | Part | MPN |
|---|---|---|---|
| U1–U8 | 8 | ADC, TSSOP-16 | TI ADS1220IPWR |
| R101, R102, … R801, R802 | 16 | 1.5 kΩ 0.1 % 25 ppm 0603 | Susumu RG1608P-152-B-T5 (alt. Panasonic ERA-3AEB152V) |
| R103, R104, … | 16 | 100 Ω 1 % 0603 | Yageo RC0603FR-07100RL |
| R1 | 1 | 33 Ω 1 % 0603 | Yageo RC0603FR-0733RL |
| C?01–C?03, C2 | 25 | 100 nF X7R 50 V 0603 | Murata GRM188R71H104KA93D |
| C?04 | 8 | 10 nF C0G 50 V 0603 | Murata GRM1885C1H103JA01D |
| C?05, C?06 | 16 | 1 nF C0G 50 V 0603 | Murata GRM1885C1H102JA01D |
| C?07, C1 | 9 | 10 µF X5R 16 V 0805 | Murata GRM21BR61C106KE15L |
| J1–J8 | 8 | JST-XH 3-pin side-entry SMT | JST S3B-XH-SM4-TB(LF)(SN) |
| J12 | 1 | 1×10 SMT male header | Samtec TSM-110-01-T-SV-P |
| J9, J11 | 2 | 1×8 SMT male header | Samtec TSM-108-01-T-SV-P |
| J10 | 1 | 1×6 SMT male header | Samtec TSM-106-01-T-SV-P |

Mating parts you need (not on the board): 8 × JST XHP-3 housings + 24 × SXH-001T-P0.6 crimp terminals (in the XH kit you already have).

## Regenerating

Everything is generated from [`scripts/design.py`](scripts/design.py), which holds the parts, nets and MPNs. The `.kicad_pro`, `.kicad_sch` and `.kicad_pcb` open and edit as a normal KiCad 10 project. If you edit by hand, don't rerun the generators.

```sh
# KiCad 10 (macOS paths are the defaults; override KICAD_CLI / KPY), Java 21+, Freerouting 2.x
hardware/pcb/adc-board/scripts/build.sh /path/to/freerouting.jar   # sch, ERC, netlist check, place, route, DRC
hardware/pcb/adc-board/scripts/export.sh                           # gerbers, drill, zip, BOM, centroid, renders, PDF
```

`build.sh` reruns Freerouting (non-deterministic) until DRC reports zero errors.

## VERIFY before ordering / on arrival

1. **UNO Q female header height.** This assumes 8.5 mm (tops at z 17.5). Measure it. Every z above depends on it.
2. **Samtec TSM-1xx-01-T-SV-P:** body 2.54 mm, post length ≥ 5.8 mm, and the land pattern. KiCad's `PinHeader_1x..._Vertical_SMD_Pin1Left` uses alternating 2.51 × 1.0 mm pads at ±1.655 mm; check it against Samtec's drawing. PCBWay may suggest an equivalent part.
3. **JST S3B-XH-SM4-TB:** mouth on the side away from the signal pads (toward the MP tabs), body height ~6 mm, and how far the mated XHP-3 plug and its crimps stick out (~10 mm assumed). KiCad has no 3D model for this part, so the renders don't show it.
4. **Cable route from plug to slot.** Do it with a real plug and cable. Ideally make the slots taller first (change 3).
5. **Noise, chip-on-board vs breakout module.** It should be equal or better: same die, decoupling at the pins, plus an RC filter. Confirm with `tools/bench/single_cell.py` and the 4-cell live view before calibrating.
6. **Standoff length** (14.5 mm) and the insert depth (2.5 mm).
7. **Lid fit:** 0.7 mm between the board top and the raised lid. The board has no top-side parts and no through-hole pins, but check the board isn't bowed.
8. **Shield drain** left unconnected (see above).
