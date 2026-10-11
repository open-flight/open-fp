# Smart2Move vs open-fp: published metrics, events and capture specs

Researched 2026-10-09. Public material only: Smart2Move's website, its App Store listing, archived
copies of its old blog, a Swiss PGA flyer it wrote, and one peer-reviewed paper that used its plates.
No Smart2Move software was downloaded, decompiled or inspected. Anything not found in a public
source is marked **not published**.

Short labels like `[S2M-compare]` point to the Sources list at the end.

## Summary

- **Capture specs.** Smart2Move sells three dual-plate systems [S2M-compare]:
  - **1D:** vertical only, force gauges, **120 Hz**.
  - **3D:** vertical plus horizontal, force gauges plus a piezo-resistive sensor, **240 Hz**.
  - **3D RS:** piezoelectric, 3 components, **up to 10 kHz**, wired, Windows software.

  open-fp samples at 1 kHz per channel but averages to **200 Hz** before any analysis
  (`docs/PROJECT_INIT.md:29`, `pipeline.py:76`). That is a higher rate than the 1D's published rate
  and close to the 3D's.
- **Our hardware matches the 1D.** The 1D metric list is pressure shift, per-foot and global CoP,
  per-foot and total Fz, foot flare and stance [S2M-compare]. open-fp already computes everything on
  that list except foot flare and stance measurement.
- **Published events are body/club positions, not force events.** The S2M app labels swing phases
  **P1–P10** [S2M-appstore]. Older apps used Address, Backswing, Top, Downswing, Impact,
  Follow-through and Finish [S2M-glossary]. A 2026 paper lists P1–P7 with definitions
  [Belotti-2026].

  These are body and club positions. How the app detects them is not published. The same release
  says swings are auto-detected "from your camera" and adds body tracking [S2M-appstore]. open-fp
  deliberately labels force events instead (max trail, 50/50 transition, max lead), so the names
  differ by design.
- **The force metric Smart2Move stresses most is peak vertical force and its timing.** It says the
  "High Peak of Force" should land before impact, between lead-arm-parallel and
  shaft-parallel in the downswing (P5–P6) [S2M-blog-peak-when] [Belotti-2026]. It also names a
  "double peak" pattern [S2M-blog-double]. We already compute peak Fz as %BW, but we time it only
  against impact, and only when impact is known.
- **Several 1D-compatible features are cheap to add:**
  - impulse per foot (the app shows impulse in Compare Mode [S2M-appstore]);
  - peak timing against our own force events;
  - double-peak detection;
  - backswing trail-shift area (Smart2Move calls this "the bubble" [S2M-blog-bubble]);
  - CoP line angle;
  - stance width from per-foot CoP at address.
- **Some outputs need 3D plates and are out of reach for us:**
  - Fx and Fy, and anything derived from them: 3D vectors, lateral force peak, coefficient of
    friction;
  - vertical torque Tz, per foot and global, and free moment.

  These need shear sensors [S2M-compare] [S2M-blog-torque].
- **Many details are not published:** exact metric formulas, the P-position detection method,
  filtering, and accuracy figures for the current plates. The current pages name no study for the
  "independent university" validation [S2M-1D].

  The only validation numbers found are in a 2019 blog post. It compares the predecessor
  SmartBalance Pro with Kistler plates and reports a total vertical force difference of
  1.68 % ± 1.64 %, from 15 swings by one player [S2M-blog-validation]. It is not peer-reviewed.

## What Smart2Move publishes

### Capture specs

From the comparison page [S2M-compare] unless noted otherwise. Columns were matched to models by
page order.

| | 1D Dual | 3D Dual | 3D RS Dual |
|---|---|---|---|
| Sample / transmission rate | 120 Hz, real time | 240 Hz, real time | up to 10 000 Hz, real time |
| Sensors | force gauges | force gauges + piezo-resistive sensor | piezoelectric, 3-component |
| Sensors per plate | 4 vertical [S2M-1D] | 8: 4 vertical + 4 horizontal [S2M-3D] | not published |
| Size (mm) | 400 × 350 × 30 | 408 × 358 × 50 | 600 × 500 × 50 |
| Fz range | 100–2350 N | 80–2500 N | 0–5000 N |
| Fx/Fy range | none | ±600 N | ±2500 N |
| Link | BT 4.2, iPad (S2M App) | BT 5.0, iPad (S2M App) | wired DAQ, Windows (S2M Lab) |
| Video | iPad camera, 240 fps | iPad camera, 240 fps | external wired camera, 200 fps |
| Accuracy | not published | not published | not published |

The RS product page adds no rate beyond "high-frequency data acquisition" [S2M-RS]. The software
pages give no sample rates [S2M-software]. The support page gives accuracy only as "high accuracy",
with no number [S2M-support].

Smart2Move's case for force gauges over pressure mats is that pressure sensors top out around
100 Hz while force gauges go "far over 1000 hertz". It says this makes peak vertical force and CoP
more accurate with force gauges [S2M-blog-pressure]. That statement is about the sensor type. The
1D plates still transmit at 120 Hz [S2M-compare].

On sensor count, a 2019 blog post says the 1D system has 8 vertical sensors (one per corner of each
plate). It says the 3D system has 8 three-axis sensors, giving 24 channels [S2M-blog-1d3d]. That
post predates the current wireless 3D (2022 [S2PGA-flyer]), so the current 3D page's "4 vertical +
4 horizontal per plate" may describe a different design.

### Metrics by product

The comparison page lists these metrics [S2M-compare]:

- **1D:**
  - weight pressure shift;
  - independent left and right foot CoP;
  - global CoP;
  - independent left and right foot Fz;
  - total Fz;
  - foot flare position;
  - stance measurement.
- **3D:** all 1D metrics, plus:
  - left and right Fx and Fy;
  - total Fx and Fy;
  - global vertical torque (Tz).
- **3D RS:** all 3D metrics, plus:
  - left and right Tz;
  - total X, Y and Z "momentum";
  - per-plate x, y and z "momentum";
  - left and right coefficient of friction.

The 3D product page also lists free moment and coefficient of friction [S2M-3D]. The comparison page
puts coefficient of friction only on the RS, so the two pages conflict.

#### Named metrics and definitions

- **Pressure shift.** The percentage split of vertical force between the left and right foot
  [S2M-1D] [S2M-3D].
- **Lateral weight distribution.** The percentage of body weight on the left foot versus the right
  foot. The glossary says it shows which way the CoP moves during the swing [S2M-glossary].
- **CoP.** The point where the ground reaction force vector acts [S2M-glossary]. The blog says a
  system measuring vertical force is enough to get CoP, while CoM needs kinematics
  [S2M-blog-com-cop].
- **CoP line / "Line of Pressure" (LoP).** The line joining each foot's CoP. The blog measures
  its direction against the target line [S2M-1D] [S2M-blog-lop]. Smart2Move says the LoP direction
  during transition and downswing correlates with swing direction at impact. It also links how the
  LoP rotates from transition to follow-through with rotation about the vertical axis
  [S2M-blog-lop]. No supporting data is shown.
- **Stance width.** The lateral distance and the anterior-posterior (open or closed) stance
  [S2M-1D] [S2M-3D].
- **Foot flare.** The foot angle relative to hip position [S2M-1D]. Feet are found by a
  "Pre-shot Stance" or "feet position" detection step before capture [S2M-glossary]
  [S2M-blog-automode].
- **High peak of force (vertical).** Smart2Move treats the size of the peak as an indication of how
  much power a player creates from the ground [S2M-blog-highpeak]. It says the peak should occur
  before impact, between lead arm parallel and shaft parallel in the downswing. It adds that the
  range depends on club kinematics and the player's muscular properties
  [S2M-blog-peak-when].
- **Double peak.** Two vertical peaks around impact. Smart2Move reads it as a player who stops
  pushing to "maintain posture" and pushes again after impact. It distinguishes this from a landing
  peak after a jump [S2M-blog-double].
- **"The bubble".** The difference in vertical force between the feet during the backswing, seen as
  the size of the shift toward the trail foot. A small or flat bubble means little lateral transfer
  [S2M-blog-bubble].
- **Lateral peak of force (3D).** Smart2Move says the "peak of total lateral force should occur
  around the transition" [S2M-blog-lateral].
- **Alternating per-foot vertical peaks.** Smart2Move's argument for dual plates is that per-foot
  Fz reveals whether power comes from one load under one leg, or from successive alternating peaks
  (lead / trail / lead around impact). Total Fz hides this [S2M-blog-dual].
- **Impulse.** Shown on the curves in Compare Mode (app 3.9.5) [S2M-appstore]. The formula, the
  integration window and the component are **not published**.
- **Vertical torque Tz (3D only).** Rotation about the vertical axis at the CoP, coming from the
  horizontal forces. It can be per foot (each foot "screwing" into the ground) or global, from the
  two feet's opposing shear [S2M-blog-torque].
- **Moment Mx/My/Mz.** Taken about the plate centre. Smart2Move describes it as how the plate would
  rotate if it were free [S2M-blog-torque].
- **Peak vGRF in %BW.** Reported per foot in a study that used the 1D plates. Its Table 2 gives
  lead-foot vGR in %BW [Belotti-2026]. Whether the app itself shows %BW is **not published**.
- **Target data.** Reference values from high-level players at key swing positions, in the legacy
  Pro and Light apps [S2M-glossary].
- **CoM and "frontal plane torque".** Attributed to "body tracking 2.0", which is video, not the
  plates [S2PGA-flyer].

  In a 2021 study, Smart2Move itself tested whether CoM position can be estimated from 3D GRF alone.
  It compared the estimate with motion capture over more than 300 swings and concluded "the method
  is not valid, the error is too big" [S2M-blog-com-study]. That conclusion was for 3D GRF, so a
  vertical-only CoM estimate would be weaker still.

### Phases and events

- **P1–P10.** In golf-mode replay the S2M App "detects all swing phases from P1 to P10". The same
  release added automatic swing detection "from your camera" and 27-marker face-on body tracking
  [S2M-appstore]. The P positions themselves are not defined on Smart2Move's site.
- **P1–P7 as described by researchers using the 1D system** [Belotti-2026, Appendix A]:

  | Position | Description |
  |---|---|
  | P1 | Start |
  | P2 | Club parallel, backswing |
  | P3 | Lead arm parallel, backswing |
  | P4 | Top of backswing |
  | P5 | Lead arm parallel, downswing |
  | P6 | Club parallel, downswing |
  | P7 | Impact |

  The authors also note that peak vertical GRF happens between P5 and P6.
- **Legacy keyframes** in SmartBalance Pro and Light: Address, Backswing, Top swing, Downswing,
  Impact, Follow through, Finish. Each keyframe is placed on the video and the graph
  [S2M-glossary].
- **Impact** can come from the TrackMan 4 integration [S2M-1D] [S2M-compare].
- **Auto mode (2020, 1D app).** Records swings automatically, with optional feet-position detection
  once or before each swing [S2M-blog-automode]. The trigger logic is **not published**.
- **Transition timing, sequencing, rate of force development.** No Smart2Move definitions were
  found. Phrases such as "timing and sequencing" appear only as general claims
  [S2M-blog-highpeak].

## What open-fp computes

### Pipeline

Source: `app/python/open_fp/pipeline.py`, matching `docs/PROJECT_INIT.md:570-578`.

- **Stream rate.** The stream is 200 Hz (`pipeline.py:76`). The MCU samples at 1000 SPS and sends
  a 5-sample mean (`docs/PROJECT_INIT.md:29`).
- **Per-channel force.** `F_i = sign_i · g_i · (c_i − z_i)` (`pipeline.py:131-132`).
- **Per-plate force and CoP.**
  - `Fz_p = Σ F_i` (`pipeline.py:149`).
  - `CoP_p = Σ F_i·pos_i / Fz_p` (`pipeline.py:151`).
  - CoP is NaN when `Fz_p < 20 N` (`pipeline.py:152`, `config.py:54`).
- **Combined CoP.** The Fz-weighted mean of the plate CoPs (`pipeline.py:154-161`).
- **Lead share.** `lead_pct = 100·Fz_lead/(Fz_L+Fz_R)`, with lead and trail set by handedness
  (`pipeline.py:160`, `config.py:81-92`).
- **Bodyweight.** BW is the mean total force over the quiet address window at arming, or a manual
  override (`swing.py:400-405`, `config.py:53`).

### Swing detection

Source: the state machine in `app/python/open_fp/swing.py`, matching
`docs/PROJECT_INIT.md:607-617`.

- **States:** idle → address → armed → swinging → review.
- **Address (quiet stance)** requires all of the following (`swing.py:324-344`):
  - each foot carries more than 10 % of the total;
  - the total stays within ±5 % of its EMA;
  - CoP speed is below 20 mm/s.
- **Armed.** Quiet stance held for 0.8 s (`swing.py:346-353`).
- **Motion start.** Lateral CoP speed above 50 mm/s for 50 ms. The start time is backdated to the
  last slow sample (`swing.py:355-371`).
- **Trigger.** Lead % must first drop at least 5 points below address. Then the lateral CoP must
  move toward lead at more than 300 mm/s. A shot event or a manual trigger also works
  (`swing.py:393-396`, `swing.py:253-282`).
- **Abort.** The swing is dropped if either foot falls below 2 % of BW before the trigger
  (stepping), or if the golfer settles back into quiet stance (`swing.py:383-389`).
- **Capture window.** From 0.5 s before motion start to 1.5 s after the trigger, up to 6 s
  (`swing.py:378-381`, `config.py:39-41`).

### Force events

Computed by `analyze()`, `swing.py:117-154`.

| Event | Definition | Code |
|---|---|---|
| `motion_start` | first sustained lateral CoP motion | `swing.py:367-369` |
| `max_trail` | minimum lead % between motion start and trigger | `swing.py:131` |
| `transition` | first lead % ≥ 50 after max_trail | `swing.py:132-135` |
| `max_lead` | maximum lead % from transition to end | `swing.py:136` |
| `finish` | 2D CoP speed below 30 mm/s for 0.3 s after max_lead | `swing.py:138-148` |
| `impact` | external shot event or manual mark only | `swing.py:265-282` |
| `trigger` | detector trigger time | `swing.py:153-154` |

### Metrics

Computed by `analyze()`, `swing.py:172-194`, matching `docs/PROJECT_INIT.md:629-641`.

| Key | Definition |
|---|---|
| `lead_pct_address` | mean lead % before motion start |
| `lead_pct_max_trail`, `lead_pct_max_lead`, `lead_pct_impact` | lead % at that event |
| `lead_cop_y_address_mm`, `trail_cop_y_address_mm` | per-foot heel/toe CoP, mean before motion start |
| `lead_cop_y_max_lead_mm`, `trail_cop_y_max_lead_mm` | per-foot heel/toe CoP at max_lead |
| `time_max_trail_to_transition_ms` | max_trail → transition |
| `time_transition_to_max_lead_ms` | transition → max_lead |
| `peak_shift_rate_pct_s` | maximum d(lead %)/dt over a 50 ms lag, from motion start (positive, toward lead) |
| `lateral_cop_range_mm`, `lateral_cop_path_mm` | range and path length of smoothed combined CoP x, from motion start to finish |
| `peak_lateral_speed_mm_s`, `peak_lateral_speed_rel_transition_ms` | peak \|dx/dt\| of combined CoP, and its time relative to transition |
| `peak_fz_pct_bw` {lead, trail, total} | maximum Fz over the whole capture window, as %BW |
| `peak_lead_fz_rel_impact_ms` | time of the lead-Fz maximum relative to impact, only when impact is known |

The UI shows a subset of these metrics (`app/assets/js/swings.js:49-60`).

### Explicit non-goals

`docs/PROJECT_INIT.md:35` rules out displaying "ground torque", "horizontal force" or "vertical
torque" metrics.

## Mapping table

| Smart2Move metric | Definition (cited) | open-fp equivalent | Notes |
|---|---|---|---|
| Pressure shift / lateral weight distribution | % of vertical force (or BW) per foot [S2M-1D] [S2M-glossary] | `lead_pct` stream (`pipeline.py:160`); event values `lead_pct_*` (`swing.py:173-176`) | Same quantity. We report lead/trail; Smart2Move reports L/R. The glossary says % of BW; we use % of instantaneous total. These differ when total ≠ BW (dynamic loading). |
| Independent L/R foot CoP | per-foot CoP [S2M-compare] | `cop["L"]`, `cop["R"]` (`pipeline.py:151-153`) | Same. We also extract heel/toe y at address and max lead (`swing.py:177-180`). |
| Global CoP | combined CoP [S2M-compare] | `cop["C"]` (`pipeline.py:154-161`) | Same definition (Fz-weighted). |
| Independent L/R Fz, total Fz | vertical force per foot and total [S2M-compare] | `fz["L"]`, `fz["R"]`, `fz_total` (`pipeline.py:149,154`) | Same. |
| CoP line / Line of Pressure | line joining L and R CoP, measured against the target line [S2M-1D] [S2M-blog-lop] | none as a metric | The UI draws both CoPs. Angle and length are not computed. Our +y axis is toward the ball, so the target line is ±x (`docs/PROJECT_INIT.md:181-186`). |
| Stance measurement / width | lateral and AP distances [S2M-1D] | none | Could approximate from per-foot CoP at address (see Gaps). |
| Foot flare | foot angle relative to hips [S2M-1D] | none | Not feasible with 4 cells per plate (see Not possible). |
| High peak of vertical force | peak vertical force [S2M-blog-highpeak] | `peak_fz_pct_bw` (`swing.py:188-192`) | Ours is the maximum over the whole capture window, so a post-impact landing or step could win. Smart2Move ties the peak to the downswing (P5–P6). |
| Peak timing (before impact, P5–P6) | [S2M-blog-peak-when] [Belotti-2026] | `peak_lead_fz_rel_impact_ms` (`swing.py:193`) | Only works when impact is known. No P5/P6 without video. |
| Double peak | two vertical peaks around impact [S2M-blog-double] | none | Gap; vertical only, so feasible. |
| "The bubble" | backswing L/R force difference [S2M-blog-bubble] | partial: `lead_pct_max_trail` (`swing.py:174`) | They describe the shape or area. We take one extreme value. |
| Impulse | shown on curves in Compare Mode [S2M-appstore] | none | Formula not published. Feasible for Fz (see Gaps). |
| %BW normalisation | per-foot vGR in %BW in a study using the 1D [Belotti-2026] | `peak_fz_pct_bw`; BW captured at arming (`swing.py:400-405`) | How Smart2Move gets BW is not published. The paper mentions a "participant-loaded calibration" step. |
| Swing phases P1–P10 / keyframes | video/body-tracking positions [S2M-appstore] [S2M-glossary] | force events `motion_start`, `max_trail`, `transition`, `max_lead`, `finish` (`swing.py:153-154`) | Different concepts. Our `transition` is the 50/50 crossing, not P4 (top). `max_trail` is "near but not necessarily at" the top (`docs/PROJECT_INIT.md:623`). |
| Impact | TrackMan 4 integration [S2M-compare] | `impact` from shot event or manual mark (`swing.py:265-282`) | Same idea (external source). Our clock error is about 5–20 ms over Wi-Fi (`docs/PROJECT_INIT.md:665`). |
| Auto mode / auto swing detection | camera-based in 3.10 [S2M-appstore]; earlier Auto Mode not described [S2M-blog-automode] | force-only state machine (`swing.py:304-396`) | We need no camera. |
| Alternating per-foot peaks | lead/trail/lead peaks around impact [S2M-blog-dual] | none | Gap (per-foot peak sequence). |
| Lateral force peak at transition | [S2M-blog-lateral] | none | Needs Fx. Our `transition` is a 50/50 Fz crossing, which is a different "transition". |
| Fx, Fy, 3D vectors, Tz, free moment, momentum, coefficient of friction | 3D / RS only [S2M-compare] [S2M-blog-torque] | none | Not possible; needs shear sensors. |
| CoM, frontal plane torque | body tracking 2.0 [S2PGA-flyer] | none | Video-derived, out of scope. |
| (none published) | — | `time_max_trail_to_transition_ms`, `time_transition_to_max_lead_ms`, `peak_shift_rate_pct_s`, lateral CoP range/path/peak speed (`swing.py:181-187`) | open-fp-specific. No public Smart2Move counterpart found. |

## Gaps we could add with vertical-force-only plates

All of these use only `fz_L`, `fz_R`, `cop_L`, `cop_R`, `cop_C` and `lead_pct`, which are already in
the swing arrays (`swing.py:430-435`). Effort is rated S (small), M (medium) or L (large).

1. **Downswing-scoped peak Fz (S).**
   - Take the peak of `fz_lead` (and the total) between `max_trail` and `finish`, or between
     `max_trail` and `impact` + 100 ms, instead of over the whole window.
   - Report its time relative to `transition` (always available) and to `impact` (when known).
   - Reason: this matches Smart2Move's emphasis on peak timing, and it stops a post-swing step from
     being reported as the peak.
2. **Vertical impulse per foot (S).**
   - `J = Σ (Fz − w·BW)·Δt`, where `w` is the foot's share of BW at address. Also report the raw
     `∫Fz dt`.
   - Integrate over backswing (`motion_start` → `transition`) and downswing (`transition` →
     `max_lead`/impact).
   - Express it as %BW·s. Smart2Move's own definition is not published, so state ours.
3. **Double-peak flag (S/M).**
   - On a 20 Hz low-passed `fz_lead`, use `scipy.signal.find_peaks` with a prominence of about
     10 % BW, between `transition` and `finish`.
   - Flag two peaks separated by a dip greater than X % BW.
   - Separate a "landing" second peak by a preceding near-zero lead or total Fz (a jump).
   - Thresholds need tuning on real swings.
   - Extension: list per-foot Fz peaks in time order (lead / trail / lead) to expose the alternating
     pattern Smart2Move describes [S2M-blog-dual].
4. **Unweighting / low peak (S).**
   - Take the minimum total Fz in %BW and its time between motion start and the downswing peak.
   - This is the standard vertical-GRF pattern (unload, then load). Smart2Move's blog doesn't name
     it, but it is vertical-only and cheap.
5. **"Bubble" area (S).**
   - Compute `∫ max(0, lead_pct_address − lead_pct) dt` from `motion_start` to `transition`, in
     %·s. Also report its depth (already `max_trail`).
6. **Rate of force development (S).**
   - Peak `dFz_lead/dt` in %BW/s over a 20–50 ms lag, between `transition` and the lead peak.
   - Reuse `lateral_speed()` (`swing.py:29-38`).
   - At 200 Hz with a 5-sample mean, keep the lag at 25 ms or more.
7. **Line of Pressure angle and length (S).**
   - `atan2(cop_R.y − cop_L.y, cop_R.x − cop_L.x)` and the distance, at address, max_trail,
     transition, max_lead and impact.
   - Our frame already has a common origin (`docs/PROJECT_INIT.md:181-186`).
   - Measure the angle against the x axis, which is the target-line direction when the plates are
     square to the target.
   - Also report the angle's rate of change from transition to finish. This is the LoP rotation
     Smart2Move describes [S2M-blog-lop].
8. **Stance width estimate (S/M).**
   - Lateral width is `|cop_R.x − cop_L.x|` at address. AP offset (open or closed) is
     `cop_R.y − cop_L.y`.
   - Label these as CoP-based. They are not foot-outline-based. Smart2Move's method is not
     published, and it appears to use a foot-detection step [S2M-blog-automode].
9. **Heel/toe pressure shift per foot over time (S).**
   - Today we report CoP y only at address and max lead. Add CoP y at each event.
   - Add the per-foot CoP-y range during the downswing.
10. **Force-event-aligned compare (M).**
    - The app aligns compares on custom P positions [S2M-appstore]. We could let the user pick any
      force event as the anchor.
    - `docs/PROJECT_INIT.md:705` already specifies alignment on transition or impact.
11. **P-position labels (L, needs video).**
    - P1–P10 need club and arm kinematics, so they can't be inferred honestly from force.
    - Only external input could supply them: impact from the launch monitor, or a future camera.
      Not recommended under the "vertical force only" rule.

## Not possible with our hardware

- **Fx and Fy (lateral and anterior-posterior shear), per foot and total, and 3D force vectors**
  [S2M-compare].
  - Our load cells are uniaxial vertical beams. Each plate gives only `Σ F_i` (vertical) and the
    moments of the vertical forces.
  - Horizontal components put very little load on these cells, and only through crosstalk.
  - Smart2Move's 3D adds dedicated horizontal sensors (4 per plate) for exactly this [S2M-3D].
- **Lateral or AP force peaks and their timing.** One example is Smart2Move's claim that the total
  lateral force peaks around transition [S2M-blog-lateral].
  - These need Fx and Fy, same reason as above.
  - The `lateral_cop_*` metrics are CoP kinematics, not forces. Don't present them as force.
- **Vertical torque Tz (per foot or global) and free moment.**
  - Tz is built from the horizontal forces about the CoP [S2M-blog-torque]. Four vertical forces
    have no component about the z axis, so Tz is unobservable.
  - `docs/PROJECT_INIT.md:35` already forbids showing it.
- **Coefficient of friction.** This is `|F_xy| / Fz`, so it needs shear [S2M-compare].
- **Moments Mx and My about the plate centre.** These *are* computable from vertical forces: they
  are equivalent to CoP × Fz. The RS's "x, y, z momentum" includes Mz, which needs shear.

  What the RS's "momentum" means is not defined publicly. It may mean moments or linear momentum
  (the integral of force). Linear momentum in z is just vertical impulse, which we can compute
  (Gap 2).
- **Foot flare (foot angle).**
  - With 4 cells per plate we get one CoP point per foot, not a pressure image or a foot outline.
  - A CoP trace during a weight rock could give a rough heel-toe axis, but it would be unreliable.
    Treat it as not possible to a useful accuracy.
  - How Smart2Move does it on 4-sensor 1D plates is not published.
- **Impact transients at high bandwidth.** Our 200 Hz stream is a 5-sample mean of 1 kHz data
  (`docs/PROJECT_INIT.md:37`). It is enough for weight shift, but not for the RS's
  10 kHz-class analysis.

  This is a firmware and link limit, not a sensor limit. It also doesn't stop us matching the 1D
  (120 Hz) or the 3D (240 Hz).
- **CoM and "frontal plane torque".** These come from video body tracking [S2PGA-flyer], not from
  plates.

## Open questions / not publicly documented

- Formulas and filtering for every displayed metric, including how impulse is defined and what
  window it covers.
- How the P1–P10 positions are detected: camera, body tracking, force, or a mix. The app's auto
  swing detection is described only as working "from your camera".
- How BW is obtained for %BW. The paper mentions a "participant-loaded calibration" step.
- Accuracy, linearity, crosstalk and CoP error for every current model. The pages cite an
  "independent university" validation without naming the university or the study [S2M-1D].
  - The 2019 blog test was of the predecessor SmartBalance Pro: IRMIS, University of Saint-Étienne,
    April 2016, 15 swings, one player, total Fz only [S2M-blog-validation]. It is not a published
    paper, and it did not cover CoP.
  - PubMed has no validation paper for Smart2Move hardware (search on 2026-10-09).
  - The only indexed paper mentioning it uses the 1D as a measurement tool [Belotti-2026].
- The per-sensor layout of the current 3D plate. The 2019 blog [S2M-blog-1d3d] and the current
  product page [S2M-3D] differ.
- Coefficient of friction: the 3D product page lists it [S2M-3D], but the comparison page lists it
  for the RS only [S2M-compare].
- How foot flare and stance are measured on 1D plates.
- Whether "120 Hz" is the internal sampling rate or only the BLE transmission rate. The comparison
  page labels the row "Sample rate / transmission".
- The old blog (blog.smart2move.com) is offline (HTTP 404 on 2026-10-09). The posts cited here were
  read from Internet Archive copies.
- Two archived posts could not be retrieved because of archive rate limits: "How ground reaction
  forces peaks act on the player's swing and club" and "The relation between GRF and CHS in golf".
  They may define further peak or timing metrics.

## Sources

All accessed 2026-10-09.

- [S2M-compare] Smart2Move, "Compare our systems": https://www.smart2move.com/force-plates/compare
- [S2M-1D] Smart2Move, 1D Dual Force Plates: https://smart2move.com/force-plates/1d-dual-force-plates
- [S2M-3D] Smart2Move, 3D Dual Force Plates: https://smart2move.com/force-plates/3d-dual-force-plates
- [S2M-RS] Smart2Move, 3D RS Dual Force Plates: https://smart2move.com/force-plates/3d-rs-dual-force-plates
- [S2M-glossary] Smart2Move, Glossary: https://smart2move.com/force-plates/glossary
- [S2M-software] Smart2Move, Software: https://smart2move.com/software and https://smart2move.com/software/s2m-app
- [S2M-support] Smart2Move, Support: https://smart2move.com/support
- [S2M-appstore] Apple App Store, "S2M" by Smart2Move AG: description and version history (3.9.5–3.11.15). Listing text only; the app was not downloaded. https://apps.apple.com/us/app/s2m/id1359042934
- [S2M-blog-peak-when] "What is the vertical High Peak of Force and when should it occur ?", 2019-09-16. Archived: http://web.archive.org/web/20251215055116/https://blog.smart2move.com/what-is-the-vertical-high-peak-of-force-and-when-should-it-occur/
- [S2M-blog-highpeak] "The High Peak Force", 2019-03-12. Archived: http://web.archive.org/web/20260124203716/https://blog.smart2move.com/the-high-peak-force/
- [S2M-blog-double] "The Double Peak of Force", 2019-03-12. Archived: http://web.archive.org/web/20260115152639/https://blog.smart2move.com/the-double-peak-of-force/
- [S2M-blog-bubble] "The Bubble", 2019-03-12. Archived: http://web.archive.org/web/20260115152310/https://blog.smart2move.com/the-bubble/
- [S2M-blog-torque] "What is the Moment and the Torque on The S2M Dual 3D Force plates?", 2019-03-12. Archived: http://web.archive.org/web/20260115155301/https://blog.smart2move.com/what-is-the-moment-and-the-torque-on-the-s2m-dual-3d-force-plates/
- [S2M-blog-com-cop] "What is the difference between COM … & COP …?", 2019-11-08. Archived: http://web.archive.org/web/20260124210444/https://blog.smart2move.com/what-is-the-difference-between-com-center-of-mass-cop-center-of-pressure/
- [S2M-blog-1d3d] "Do you know the difference between the S2M 1D & 3D Dual Force Plates ?", 2019-12-10. Archived: http://web.archive.org/web/20251215050506/https://blog.smart2move.com/do-you-know-the-difference-between-the-s2m-1d-3d-dual-force-plates/
- [S2M-blog-automode] "Auto Mode now available with the S2M 1D Dual Force plates", 2020-05-20. Archived: http://web.archive.org/web/20260124201208/https://blog.smart2move.com/auto-mode-now-available-with-the-s2m-1d-dual-force-plates/
- [S2M-blog-lateral] "When should the lateral peak of force occurring ?", 2019-10-11. Archived: https://web.archive.org/web/2025/https://blog.smart2move.com/when-should-the-lateral-peak-of-force-occurring/
- [S2M-blog-lop] "The Line of Pressure (LoP)", 2019-03-12. Archived: https://web.archive.org/web/2025/https://blog.smart2move.com/the-line-of-pressure-lop/
- [S2M-blog-dual] "Why would a Dual Force Plate make more sense to analyse a swing?", 2019-03-12. Archived: https://web.archive.org/web/2025/https://blog.smart2move.com/why-would-a-dual-force-plate-make-more-sense-to-analyse-a-swing/
- [S2M-blog-validation] "Scientific Validation", 2019-03-12. Archived: https://web.archive.org/web/2025/https://blog.smart2move.com/scientific-validation/
- [S2M-blog-com-study] "Sciences and Technology – Research study on Center of Mass measurement in golf swing", 2021-09-22. Archived: https://web.archive.org/web/2025/https://blog.smart2move.com/sciences-and-technology-research-study-on-center-of-mass-measurement-in-golf-swing/
- [S2M-blog-pressure] "The difference between Pressure & Force", 2019-03-12. Archived: https://web.archive.org/web/2025/https://blog.smart2move.com/the-difference-between-pressure-force/
- [S2PGA-flyer] Smart2Move, "Force creates & precedes motion" (2026 flyer, hosted by Swiss PGA): https://swisspga.ch/Smart-2-Move (PDF linked from that page)
- [Belotti-2026] Belotti A, Bisazza N, Calcari A, Perrone P, Panichi R, Biscarini A. "Training the proprioceptive and propulsive function of the foot for improved technique and enhanced performance of the golf swing: a pilot study." *Front Sports Act Living* 2026. doi:10.3389/fspor.2026.1888684. PMC13616624. Its Methods describe the 1D plates (120 Hz, 100–2350 N, force gauges); Appendix A lists P1–P7. https://pmc.ncbi.nlm.nih.gov/articles/PMC13616624/
- open-fp: `docs/PROJECT_INIT.md`, `app/python/open_fp/pipeline.py`, `app/python/open_fp/swing.py`, `app/python/open_fp/config.py`, `app/assets/js/swings.js` (at commit 9e0c43d).
