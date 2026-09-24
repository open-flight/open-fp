# Bill of materials

Everything here has already been purchased. The source is [`docs/PROJECT_INIT.md` §3](../docs/PROJECT_INIT.md#3-bill-of-materials-already-purchased).

| Qty | Part | Notes |
|---|---|---|
| 1 | Arduino UNO Q | 3.3 V logic on MCU header |
| 8 | 50 kg half-bridge load cell, 34 × 34 × 7.8 mm, 3-wire | two 4-packs; bundled HX711s unused |
| 8 | ADS1220 24-bit ADC breakout (generic module) | one per corner |
| 16 | 1 kΩ 0.1 % metal-film resistor | two per corner, completes each bridge |
| 2 | 12" × 12" × 1/4" 6061 aluminum plate | |
| 2 | 12" × 12" × 1/16" textured (fabric-finish) neoprene, 60A | top surface |
| 1 | 3M 468MP transfer tape, 12" wide | bonds neoprene to plate |
| 1 | Right-angle USB-C cable, 2 m | power + dev |
| 1 | Shielded 4-conductor 24 AWG cable, 5 m | cell leads |
| 1 | JST-XH 4-pin connector kit | cells swappable at the cradle end |
| — | 3/8" rubber gym flooring | must cover the **whole** footprint, ~500 × 900 mm |
| 16 | M4 × 12 flat-head (90° countersunk) + 16 M4 heat-set inserts | cradle → plate |
| 32 | M2 × 5 countersunk + 32 M2 heat-set inserts | retainers |
| ~30 | M2.5 × 6 + M2.5 heat-set inserts, 8 × M2.5 × 6 mm standoffs | Uno Q, ADCs, lid |
| — | PETG or ABS (~650 g), TPU 95A (~10 g) | |
| — | CA glue, heat-shrink, 22–24 AWG hookup wire, labels | |
| — | Calibration mass: 20 kg / 45 lb plate (known mass) + bathroom scale | |
| opt | 8 × 10 kΩ resistor | CS pull-ups |

## Printed parts

Print on the Bambu H2D. The STL files are in `cad/stl/`, the STEP files in `cad/step/`, and the CadQuery sources in `cad/src/`.

| File | Qty | Material | Settings | Orientation |
|---|---|---|---|---|
| `01_corner_cradle` | 8 | PETG/ABS | 5 walls, 40 % gyroid, ≥4 top layers | pocket side **up** (plate face on bed), see note below |
| `02_cradle_retainer` | 8 | PETG/ABS | 3 walls | flat |
| `03_centre_enclosure_base` | 1 | PETG/ABS | 3 walls, 20 % | open side up |
| `04_centre_enclosure_lid` | 1 | PETG/ABS | 3 walls, 20 % | vents up |
| `07_edge_ramp_left` | 6 | PETG/ABS | 3 walls, 20 % | flat bottom down |
| `07_edge_ramp_right` | 6 | PETG/ABS | 3 walls, 20 % | flat bottom down |
| `09_drill_template_a` | 1 | any | 100 % | lips up |
| `09_drill_template_b` | 1 | any | 100 % | lips up |
| `10_hub_foot_tpu` | 8 | TPU 95A | 100 % | flat |
| `08_assembly_two_plates.step` | — | reference only | | |

**Cradle orientation:** print pocket side up, with the plate-mounting face on the bed. This changes the original plan of pocket side down. Pocket-up prints with no supports and no bridges. The only overhang is the blind end of the two M4 insert holes. The pocket seat, which carries the cell's frame and all the load, prints as a solid top surface instead of a 35 mm bridge that can sag. The plate-mounting face also comes out bed-flat. Use elephant-foot compensation so the M4 insert holes stay Ø5.6. After heat-setting the inserts, scrape the plate face flush.

**Before printing all eight cradles,** measure a load cell and print one cradle to check the fit.
