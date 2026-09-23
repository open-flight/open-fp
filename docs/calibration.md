# Calibration

The full procedure is in [`PROJECT_INIT.md` §9.5](PROJECT_INIT.md#95-calibration-calibrationpy--ui-wizard). The UI wizard follows these steps.

1. Zero with the plates empty (2 s average).
2. On each plate, place a known mass *m* at five marked spots: the centre, and over each cradle about 40 mm inboard. Hold each for 3 s.
3. Solve for each plate's four gains by least squares: `m · 9.80665 = Σ_i g_i · Δc_{i,k}`. Review the residuals.
4. Validate at the centre and at two off-centre spots. Targets: force error < 1 %, CoP error < 10 mm.
5. Bodyweight check: stand on both plates and compare with a bathroom scale. Target: within 1 %.
6. The wizard saves `data/calibration.json` and keeps timestamped copies of earlier files.

## Calibration log

| Date | Mass (kg) | Residuals | Force err | CoP err | BW vs scale | Notes |
|---|---|---|---|---|---|---|
