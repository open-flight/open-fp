# Bill of materials

Everything needed for one pair of plates. The original build's parts list is in [`docs/PROJECT_INIT.md` §3](../docs/PROJECT_INIT.md#3-bill-of-materials-already-purchased).

The **Buy** links marked *used in the build* go to the exact listings the original plates were built from. The rest are Amazon searches, so check the spec in the Notes column before you order.

*As an Amazon Associate I earn from qualifying purchases. The links cost you nothing extra and help fund the project.*

| Qty | Part | Notes | Buy |
|---|---|---|---|
| 1 | Arduino UNO Q | 3.3 V logic on MCU header | [Amazon](https://www.amazon.com/s?k=Arduino+UNO+Q&tag=colemangolfs-20) |
| 8 | 50 kg half-bridge load cell, 34 × 34 × 7.8 mm, 3-wire | two 4-packs; bundled HX711s unused | [Amazon (used in the build)](https://www.amazon.com/dp/B079FTXR7Y?tag=colemangolfs-20) |
| 8 | ADS1220 24-bit ADC breakout (generic module) | one per corner | [Amazon (used in the build)](https://www.amazon.com/dp/B0DPMKMGNN?tag=colemangolfs-20) |
| 16 | 1 kΩ 0.1 % metal-film resistor | two per corner, completes each bridge | [Amazon](https://www.amazon.com/s?k=1k+ohm+0.1%25+metal+film+resistor&tag=colemangolfs-20) |
| 2 | 12" × 12" × 1/4" 6061 aluminum plate | | [Amazon (used in the build)](https://www.amazon.com/dp/B0DS5X5F51?tag=colemangolfs-20) |
| 2 | 12" × 12" × 1/16" textured (fabric-finish) neoprene, 60A | top surface | [Amazon](https://www.amazon.com/s?k=neoprene+sheet+1%2F16+12x12+fabric+finish+60A&tag=colemangolfs-20) |
| 1 | 3M 468MP transfer tape, 12" wide | bonds neoprene to plate | [Amazon](https://www.amazon.com/s?k=3M+468MP+adhesive+transfer+tape+12+inch&tag=colemangolfs-20) |
| 1 | Right-angle USB-C cable, 2 m | power + dev | [Amazon](https://www.amazon.com/s?k=right+angle+USB-C+cable+2m&tag=colemangolfs-20) |
| 1 | Shielded 4-conductor 24 AWG cable, 5 m | cell leads | [Amazon](https://www.amazon.com/s?k=shielded+4+conductor+24+AWG+cable&tag=colemangolfs-20) |
| 1 | JST-XH 4-pin connector kit | cells swappable at the cradle end | [Amazon (used in the build)](https://www.amazon.com/dp/B08G188ZQ8?tag=colemangolfs-20) |
| — | 3/8" rubber gym flooring | must cover the **whole** footprint, ~500 × 900 mm | [Amazon](https://www.amazon.com/s?k=3%2F8+rubber+gym+flooring&tag=colemangolfs-20) |
| 16 | M4 × 12 flat-head (90° countersunk) + 16 M4 heat-set inserts | cradle → plate | [Amazon](https://www.amazon.com/s?k=M4+heat+set+insert+and+countersunk+screw+kit&tag=colemangolfs-20) |
| 32 | M2 × 5 countersunk + 32 M2 heat-set inserts | retainers | [Amazon](https://www.amazon.com/s?k=M2+heat+set+insert+and+countersunk+screw+kit&tag=colemangolfs-20) |
| ~30 | M2.5 × 6 + M2.5 heat-set inserts, 8 × M2.5 × 6 mm standoffs | Uno Q, ADCs, lid | [Amazon](https://www.amazon.com/s?k=M2.5+heat+set+insert+standoff+screw+kit&tag=colemangolfs-20) |
| — | PETG or ABS (~650 g), TPU 95A (~10 g) | | [Amazon](https://www.amazon.com/s?k=PETG+filament+1.75mm&tag=colemangolfs-20) |
| — | CA glue, heat-shrink, 22–24 AWG hookup wire, labels | | [Amazon](https://www.amazon.com/s?k=CA+glue+heat+shrink+hookup+wire+22+AWG&tag=colemangolfs-20) |
| — | Calibration mass: 20 kg / 45 lb plate (known mass) + bathroom scale | | [Amazon](https://www.amazon.com/s?k=45+lb+weight+plate&tag=colemangolfs-20) |
| opt | 8 × 10 kΩ resistor | CS pull-ups | [Amazon](https://www.amazon.com/s?k=10k+ohm+resistor+kit&tag=colemangolfs-20) |
| opt | Assembled ADC board ([`pcb/adc-board`](pcb/adc-board/README.md)), PCBWay | no-solder alternative: replaces the 8 breakouts, 16 resistors, both stripboard carriers and the harness | [PCBWay](https://www.pcbway.com/) (upload the files in `pcb/adc-board`) |
| 2 | BusBoard ST2 stripboard, 100 × 80 mm, uncut strips, 2.54 mm | ADC carriers: cut one 37 × 17-hole piece from each, strips along the 37 (see `docs/harness.md`). Ordered 2026-09-28 | [Amazon](https://www.amazon.com/s?k=BusBoard+stripboard+ST2&tag=colemangolfs-20) |
| opt | JST XHP-3 housings + SXH-001T-P0.6 crimp contacts (~10 of each) and a JST-XH crimper | ADC board only: one plug per cell at the board end | [Amazon](https://www.amazon.com/s?k=JST+XH+2.5mm+crimp+housing+terminal+kit&tag=colemangolfs-20) [Amazon](https://www.amazon.com/s?k=JST+XH+crimping+tool&tag=colemangolfs-20) |
| opt | 4 × M2.5 × 15 mm standoffs | ADC board only: board supports (design asks 14.6 mm, see `pcb/adc-board/README.md`) | [Amazon](https://www.amazon.com/s?k=M2.5+15mm+standoff&tag=colemangolfs-20) |

## Printed parts

Print on the Bambu H2D. The STL files are in `cad/stl/`, the STEP files in `cad/step/`, and the CadQuery sources in `cad/src/`.

| File | Qty | Material | Settings | Orientation |
|---|---|---|---|---|
| `01_corner_cradle` | 8 | PETG/ABS | 5 walls, 40 % gyroid, ≥4 top layers | pocket side **up** (plate face on bed), see note below |
| `02_cradle_retainer` | 8 | PETG/ABS | 3 walls | flat |
| `03_centre_enclosure_base` | 1 | PETG/ABS | 3 walls, 20 % | open side up |
| `04_centre_enclosure_lid` | 1 | PETG/ABS | 3 walls, 20 % | vents up |
| `07_edge_ramp_left` | 4 | PETG/ABS | 3 walls, 20 % | flat bottom down. 24.5 mm rise, 45° mitre at the plate's outer corner |
| `07_edge_ramp_right` | 4 | PETG/ABS | 3 walls, 20 % | flat bottom down. Mirror of the left piece |
| `07_edge_ramp_inner` | 4 | PETG/ABS | 3 walls, 20 % | flat bottom down. Square-ended piece for the enclosure end of each plate's front and back side; the two plates' pieces stop 5 mm short of the gap centre, leaving a 10 mm channel (USB cable at the heel) |
| `09_drill_template` | 1 | any | 100 % | lips up. One template does all four corners: two from the plate's top face, the other two with the plate flipped over |
| `10_hub_foot_tpu` | 8 | TPU 95A | 100 % | flat, channel up. Ø18 × 4.7 mm, locates on the cell's centre strap; parametric source `cad/src/hub_foot.py` |
| `11_cell_shim_tpu_1.5mm` | 8 | TPU 95A | 100 % | flat. Goes between the cell frame and the retainer. 1.5 mm chosen from the tuning set (2026-09-23); the other thicknesses are only for re-tuning with a different cell. Source `cad/src/cell_shim.py` |
| `08_assembly_two_plates.step` | — | reference only | | |

**Cradle orientation:** print pocket side up, with the plate-mounting face on the bed. This changes the original plan of pocket side down. Pocket-up prints with no supports and no bridges. The only overhang is the blind end of the two M4 insert holes. The pocket seat, which carries the cell's frame and all the load, prints as a solid top surface instead of a 35 mm bridge that can sag. The plate-mounting face also comes out bed-flat. Use elephant-foot compensation so the M4 insert holes stay Ø5.6. After heat-setting the inserts, scrape the plate face flush.

**Before printing all eight cradles,** measure a load cell and print one cradle to check the fit.
