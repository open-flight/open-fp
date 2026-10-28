# Swing Catalyst vs open-fp: software features, taught metrics, and what to build

Researched 2026-10-28. Public material only: Swing Catalyst's product pages, its help center, its
2015 *3D Motion Plate Data Guide*, articles on its site, and a conference slide deck by its research
director, Dr. Scott Lynn. No Swing Catalyst software was downloaded, decompiled or inspected. The
paid Academy courses were not viewed. Anything not found in a public source is marked
**not published**.

Short labels like `[SC-keymetrics-col]` point to the Sources list at the end. The companion
document [`smart2move-comparison.md`](smart2move-comparison.md) describes what open-fp computes
today (pipeline, swing detection, events, metrics). This document doesn't repeat it.

## Summary

- **Swing Catalyst sells pressure mats and true force plates, and teaches mostly from the
  software.**
  - Its plates range from a 150 Hz pressure mat (Balance Plate, $7,300) to 1000 Hz six-channel
    force plates per foot with a pressure mat on top (Dual Motion Plate, $36,400)
    [SC-balance] [SC-dualforce] [SC-dualmotion].
  - The software is the product coaches live in: synced video, a stance view, force graphs with
    phase markers, and (since 26.2) a "Key Metrics column" of explained cards
    [SC-keymetrics-col].
- **Our hardware sits between its products.** We measure true vertical force per foot, which the
  Balance Plate can't. We have no pressure image and no shear or torque, which the force plates
  have.
- **Two things we can do that its software doesn't:**
  - **Per-foot force metrics.** Its Key Metrics column reports force and torque "for the two feet
    combined" and lists per-foot force as a current limit [SC-keymetrics-col]. We already have
    `fz_L` and `fz_R`.
  - **Impact from a launch monitor.** Its timing metrics hang off swing markers that come from
    video or markerless motion capture [SC-phases]. We get impact from OpenFlight's shot event.
- **What it teaches, in short:**
  - A good CoP trace is smooth and repeatable for that player. Several rapid direction changes
    mean unnecessary movement [SC-guide].
  - Pressure is not body mass. Around transition, pressure is often still on the trail foot while
    mass is moving forward [SC-bodymass].
  - Peak vertical force comes late in the downswing, around club parallel. It is the last of the
    three ground-force peaks: horizontal, then torque, then vertical [SC-kinseq].
  - CoP toward the toes goes with higher vertical force [SC-vertical].
  - More force is not always better. Tune forces to the player; don't maximize them
    [SC-carry].
  - Reference averages exist (see "Reference values"), and the spread between good players is
    large. Don't coach to the mean [Lynn-deck].
- **The best-value work for open-fp is presentation, not new physics.** Explained metric cards with
  reference ranges, a few cheap vertical-only metrics, compare mode, synced phone video, and
  linking force metrics to ball flight. See "What to build".

## What Swing Catalyst publishes

### Products

| Product | What it measures | Rate | Price (excl. tax) |
|---|---|---|---|
| Balance Plate | Pressure map (over 2,000 sensors): pressure trace, per-foot "Individual Balance Trace", L/R distribution, stance width, heat map, "Balance Point Speed" | 150 Hz | $7,300 [SC-balance] |
| Dual Force Plates | Six channels per plate: Fx, Fy, Fz, Mx, My, Mz | 1000 Hz | $12,500 [SC-dualforce] |
| Dual Motion Plate | Pressure map plus per-foot force: vertical, horizontal shear, twisting force / free moment, force vectors | 1000 Hz (force) | $36,400 [SC-dualmotion] |

- The force plates and the Dual Motion Plate need the "Pro+" software licence [SC-dualforce]
  [SC-dualmotion]. The licence price is on a separate pricing page and was **not checked**.
- A single Motion Plate and a larger Balance Plate (XL) also exist, according to a research summary.
  Their prices were **not checked**.

### Software features coaches use

- **Pressure & Stance box** [SC-guide] [SC-stance]:
  - foot outlines with a heat map, and a white dot for the combined CoP;
  - per-foot CoP dots joined by a line;
  - the CoP trace in grey, recolored as the video is scrubbed past it;
  - L/R distribution bars;
  - stance width, measured between the centres of the two feet.
- **Dynamic stance width.** Width can lock to the first phase, lock to the current phase, or follow
  live. Plate spacing is a setting (Narrow, Wide or custom), and the help center stresses that it
  must be right for stance width to be right [SC-stance].
- **Force graphs:**
  - Vertical force is plotted relative to body weight, with 100% BW as the baseline [SC-guide].
  - Dual plates can be shown per plate as well as combined, with zoom and pan [SC-graphs].
  - The databox shows Max, Min, and "Max W. Timing": the time of maximum vertical force relative
    to impact in ms, negative meaning before impact [SC-guide].
  - A light grey vertical line runs through the graphs at each marker [SC-graph-phases].
- **Body-weight weigh-in** [SC-bw]:
  - It starts automatically when the user enters capture mode. The player stands still for a few
    seconds, ideally holding the club.
  - It is stored per user per session and used to normalize metrics.
  - The help center explains why: golfers move around before hitting, so background weighing
    gave wrong values.
- **Swing markers (phases)** [SC-phases]:
  - Ten positions, often written P1–P10: Start of Take Away through End of Swing. Older
    recordings may have only three.
  - Since 26.2 they are detected from tracked body pose in video. Detected markers behave like
    hand-set ones, and the coach's own markers can be restored.
- **Key Metrics column (26.2)** [SC-keymetrics-col]:
  - Coaches pick five or six numbers that stay on screen between the video and the data boxes.
  - Each card has a "?" that explains what the metric measures and how to read it. Where enough
    tour data exists, the explanation shows a tour-average range.
  - Five built-in sets: Ball flight; Distance & strike; Ground force & power; Weight shift;
    Tempo & transition. Users can save ten sets of their own per activity.
  - A raw vs normalized-to-body-weight toggle. Normalized force reads as %BW, and torque as N·m/kg.
  - Missing values read **No data** rather than a guessed number. A dimmed "–" means the value is
    still being calculated or no body weight is on file.
  - Stated limits: force and torque metrics are two feet combined only, and the "?" isn't
    available in Compare mode.
- **Golf timing metrics**, computed from marker positions only, so they work on camera-only
  recordings [SC-keymetrics]:
  - Tempo Ratio: backswing time ÷ downswing time. Target range 2.0–3.0.
  - Transition Duration: Top of Swing → Early Downswing, in ms.
  - Release Timing: Impact → Release, in ms.
- **Force vectors on video** [SC-vectors]:
  - Arrows are drawn over the live or recorded video. The plate is located in each camera view by
    autodetect or by clicking its corners.
  - Scale: an arrow 1 m tall is 1000 N.
- **Raw data export** [SC-export]:
  - Columns are Time, Fx, Fy, Fz, Mx, My, Mz, CopX, CopY, plus separate CoP Velocity and
    "CoP Distribution" (Left, Right, Heel, Toe fractions) files.
  - Marker times and the video files are exported alongside.
- **Education.** Swing Catalyst Academy sells courses such as "Coaching with Pressure"
  [SC-course]. Course content was **not viewed**.

### What it teaches about reading the data

#### Pressure and CoP

- **Trace shape** [SC-guide]:
  - Successful swings typically have a smooth trace that is repeatable for that player.
  - Several rapid direction changes usually mean unnecessary or even harmful movement.
- **Good players' downswing shift.** Strong players tend to make a rapid, continuous pressure shift
  in the downswing. It shows as a smooth, near-straight line from trail foot to lead foot
  [SC-pressureshift].
- **Pressure shift is not weight shift** [SC-pressureshift] [SC-bodymass]:
  - Pressure shift is the change in how force is split between the feet. Weight shift is movement
    of the body's mass.
  - They usually track each other, except around transition. There, the player pushes into the
    trail foot to start the downswing, so pressure stays on the trail side while mass moves
    forward. Pressure then catches up quickly.
- **Case study** [SC-casestudy]:
  - A player had up to 86% of pressure on the trail foot, loaded on its outside edge.
  - One session of heat-map biofeedback moved that pressure toward the centre of the foot.
  - The offline miss went from 38 yards to 11 yards.
  - This is one player, with no control and no repeat measurement.

#### Vertical force

- **Shape** [SC-guide]:
  - Minimum vertical force typically falls around transition, around impact, or late in the
    follow-through. What it means depends on when it happens: moving down, or resisting the
    previous upward movement.
  - Maximum vertical force typically comes late in the downswing, after maximum torque.
  - A later pressure shift goes with a later vertical peak.
- **Toe vs heel** [SC-vertical]:
  - CoP slightly toward the toes goes with higher vertical force.
  - Example: Justin Rose peaked at 146% BW with pressure toward the heels, and 182% with pressure
    toward the toes.
- **More is not always better** [SC-carry]:
  - Matthew Wolff reaches about 284% BW with the driver.
  - An unnamed player went from 234% to 175% BW on a 7-iron after coaching cues, with better
    timing. Clubhead speed rose by close to 6 mph.
  - The conclusion is to tune forces per player rather than maximize them all.
- **Kinetic sequence** [SC-kinseq]:
  - Horizontal force peaks first, around the top. Torque peaks around lead arm parallel in the
    downswing. Vertical force peaks last, around club parallel.
  - Lynn calls this the closest thing to a universal truth he has found in golf biomechanics, with
    rare exceptions.
  - We can see only the last of the three peaks.
- **Three power sources** [Lynn-deck]:
  - Horizontal (linear), torque (rotational) and vertical.
  - In a PING study each swing was classified by its highest z-score against tour averages.
  - Lynn links them to leg dominance: left-leg dominant → vertical, right-leg dominant → linear,
    no dominance → torque.

#### Reference values

Pressure distribution, lead foot % [Lynn-deck]. The slide credits McGhie (unpublished data). The
subject population is not described beyond n.

| Position | Driver (n=86, 23 golfers) | Mid iron (n=102, 24) | Short iron (n=71, 17) |
|---|---|---|---|
| Address | 53.7 ± 8.3 | 54.0 ± 7.6 | 53.2 ± 7.4 |
| Top | 21.7 ± 14.0 | 24.7 ± 12.4 | 28.3 ± 11.6 |
| Impact | 75.9 ± 17.7 | 81.8 ± 10.5 | 84.2 ± 8.8 |
| Clubhead speed (mph) | 109.6 ± 3.6 | 93.5 ± 4.1 | 86.1 ± 3.0 |

- For the driver, lead-foot % at impact ranged from 3.6 to 100 [Lynn-deck]. The deck uses this to
  show how large individual variation is.
- Tour averages used for the PING study's z-scores [Lynn-deck]: vertical 179 ± 20 %BW, torque
  127.7 ± 16.0 N·m, horizontal 19.0 ± 4.1 %BW. The deck doesn't say how these were measured.
- These are pressure-mat distributions. Our `lead_pct` is a force split. The two should be close,
  but they are not the same measurement.
- "Top" in the table is a video position. Our nearest event is `max_trail`, which is near the top
  but not at it (`docs/PROJECT_INIT.md:623`).

## Mapping table

open-fp definitions are in `app/python/open_fp/swing.py:117-194` and in the companion document.

| Swing Catalyst feature or metric | open-fp today | Notes |
|---|---|---|
| L/R pressure distribution | `lead_pct` stream; `lead_pct_*` at events | Ours is a force split, not a pressure split. |
| Distribution at address / top / impact | `lead_pct_address`, `lead_pct_max_trail`, `lead_pct_impact` | Our "top" is `max_trail`, a force event. |
| Combined CoP trace | `cop_C`, drawn in the stance view | Same idea. |
| Per-foot CoP ("Individual Balance Trace", detailed view) | `cop_L`, `cop_R`, drawn in the stance view | We have no heat map. |
| Stance width (dynamic) | none | Feasible from per-foot CoP. See gap 4. |
| Balance Point Speed / CoP velocity | `peak_lateral_speed_mm_s` (lateral only) | Formula **not published**. Feasible as a full 2D series. |
| Vertical force Max / Min (%BW) | `peak_fz_pct_bw`; no minimum | Minimum is gap 2. |
| Max W. Timing (ms rel. impact) | `peak_lead_fz_rel_impact_ms` (lead foot) | Ours is per foot and needs a shot event. Theirs is combined. |
| Body-weight weigh-in | BW from quiet address at arming (`swing.py:400-405`) | Theirs is an explicit once-per-session step. |
| Key Metrics cards, "?" explanations, tour ranges, metric sets | flat metric list (`app/assets/js/swings.js:49-60`) | Gap 1. Largest UX difference. |
| "No data" for missing values | "—" or "no shot event" (`swings.js:62-69`) | Already similar. |
| Tempo Ratio, Transition Duration, Release Timing | `time_max_trail_to_transition_ms`, `time_transition_to_max_lead_ms` | Theirs use video markers. Takeaway and top can only be estimated from force. |
| Compare mode (side by side, metric strip) | none (specified in `docs/PROJECT_INIT.md:705`) | Gap 6. |
| Synced multi-camera video | none | Gap 7. |
| Force vectors on video | none | Vertical-only arrows are possible. See "Not possible". |
| Raw TSV export | CSV per swing | Mirror their column names where they overlap. |
| Launch monitor integration | OpenFlight shot event (`swing.py:265-282`) | Ours also supplies impact time. |
| Shear, torque, free moment, kinetic sequence, power-source typing | none | Not possible. See below. |

## What to build

Ordered by value for effort. Effort is rated S (small), M (medium) or L (large). The Smart2Move
document's gaps overlap with several of these (downswing-scoped peak, impulse, double peak, stance
width). Do them once.

1. **Explained metric cards with reference ranges (M).** The single biggest UX gain.
   - One card per metric, with a "?" that says what it measures, how to read it, and a reference
     range.
   - Use the published reference values above, labelled with their source and their caveats.
   - Show the player's own spread across the session next to the reference. The literature's
     message is that each player's repeatability matters more than the tour mean.
   - Built-in sets for vertical-only data: *Weight shift*, *Vertical force*, *Timing*.
   - Normalized (%BW) vs raw (N) toggle.
2. **Minimum vertical force and its timing (S).** Depth of unweighting, its time relative to
   `transition` and `impact`, and where it falls (transition, impact or follow-through)
   [SC-guide].
3. **Peak vertical force timing against our own events (S).**
   - Restrict the peak to the downswing, and report it for the total as well as per foot.
   - Report its time relative to `transition` (always available) as well as to impact.
4. **Stance width and heel/toe at peak force (S).**
   - Stance width is `|cop_R.x − cop_L.x|`, live and locked to address. Label it as CoP-based, not
     outline-based.
   - Per-foot CoP y at the vertical peak tests the toe-bias pattern directly [SC-vertical].
5. **Trace quality (S).**
   - Count direction reversals of lateral CoP during the downswing, above a minimum amplitude.
   - Measure how straight the downswing trace is: chord length ÷ path length from `max_trail` to
     `max_lead`.
   - Swing-to-swing variability of the trace and of the headline metrics.
6. **Compare mode (M).** Already specified in `docs/PROJECT_INIT.md:705`. Overlay two swings,
   aligned on transition or impact, with a metric strip of differences.
7. **Synced phone video (L).**
   - Browser camera capture (`getUserMedia`) on the iPad or phone beside the bay, cut to the same
     window as the force capture.
   - Sync it with the existing clock and the shot event.
   - This is the only honest route to video positions such as takeaway and top.
8. **Force metrics against ball flight (M).**
   - Over a session, link per-swing force metrics to OpenFlight ball speed and carry. For example:
     "your five longest drives peaked 20 ms later".
   - Swing Catalyst's own articles say the right amount of force depends on the player
     [SC-carry]. A per-player correlation shows that directly. Present it as association, not
     cause.
9. **Quality of life (S each).**
   - player profiles and sessions;
   - an explicit weigh-in step with the club in hand [SC-bw];
   - an export whose column names match the overlapping part of their schema [SC-export];
   - a large-type replay screen for a second monitor.

## Not possible with our hardware

- **Pressure heat maps and foot outlines.** We have four cells per plate, so we get one CoP point
  per foot. Inside/outside-of-foot loading can only be guessed from where that point sits.
- **Horizontal force (R/L and toe/heel shear) and its timing.** The cells are vertical-only. See
  the companion document for detail.
- **Torque, free moment, and Force Factor.** These need shear.
- **The first two kinetic-sequence peaks** (horizontal and torque), and the three-power-source
  classification. Only the vertical leg is measurable.
- **True 3D force vectors on video.** A vertical arrow at each foot's CoP, scaled by Fz, is
  possible. It must not be drawn as if it were the full force.
- **Video positions (P1–P10, top, takeaway) from force alone.** Force events can only approximate
  them. Name them as force events.
- **1000 Hz peak timing.** Our 200 Hz stream quantizes event times to 5 ms. Our impact time also
  carries 5–20 ms of clock error over Wi-Fi (`docs/PROJECT_INIT.md:665`).

## Open questions / not publicly documented

- Formulas and filtering behind every metric, including "Balance Point Speed".
- How "stance width" chooses the centre of each foot: from the outline or from the CoP.
- Where the Key Metrics tour-average ranges come from, and how large the sample is.
- The subject population behind the McGhie distribution table: tour, elite amateur, or mixed.
- How the Lynn deck's tour averages for vertical force, torque and horizontal force were measured,
  and with which club.
- Price of the Pro+ licence, the Motion Plate and the Balance Plate XL (not checked).
- Course content of Swing Catalyst Academy (paid; not viewed).
- User sentiment. No independent reviews were found on Reddit or GolfWRX. The only user
  discussion found was one golf simulator forum thread about price [GSF-thread].

## Sources

All accessed 2026-10-28.

- [SC-balance] Swing Catalyst, Balance Plate: https://swingcatalyst.com/products/balance-plate
- [SC-dualforce] Swing Catalyst, Dual Force Plates: https://swingcatalyst.com/products/dual-force-plates
- [SC-dualmotion] Swing Catalyst, Dual Motion Plate: https://swingcatalyst.com/products/dual-motion-plate
- [SC-guide] Swing Catalyst, *3D Motion Plate Data Guide* (2015, PDF): https://support.swingcatalyst.com/images/zendesk/Data_Guide_3D_Motion_Plate_2015_-_email.pdf
- [SC-stance] Help center, "Using the new Pressure and Stance settings" (24.1+): https://support.swingcatalyst.com/en/software-features/data-analysis/pressure-stance-settings/
- [SC-graphs] Help center, "Graph library": https://support.swingcatalyst.com/en/software-features/data-analysis/graph-library/
- [SC-graph-phases] Help center, "Force graph phases" (10.2+): https://support.swingcatalyst.com/en/software-features/data-analysis/force-graph-phases/
- [SC-bw] Help center, "New body weight measurement functionality" (10.2): https://support.swingcatalyst.com/en/software-features/data-analysis/body-weight-measurement/
- [SC-phases] Help center, "Golf swing phase detection": https://support.swingcatalyst.com/en/software-features/motion-capture/golf-swing-phase-detection/
- [SC-keymetrics-col] Help center, "The Key Metrics Column" (26.2): https://support.swingcatalyst.com/en/software-features/data-analysis/key-metrics-column/
- [SC-keymetrics] Help center, "Key Metrics" (data box, 10.2+): https://support.swingcatalyst.com/en/software-features/data-analysis/key-metrics/
- [SC-vectors] Help center, "How to use Force Vectors": https://support.swingcatalyst.com/en/software-features/data-analysis/force-vectors/
- [SC-export] Help center, "Raw data export guide": https://support.swingcatalyst.com/en/software-features/recording-export/raw-data-export-guide/
- [SC-course] Swing Catalyst Academy, "Coaching with Pressure": https://swingcatalyst.com/products/pressure-course
- [SC-pressureshift] D. McGhie, "Weight shift or pressure shift?": https://swingcatalyst.com/resources/articles/weight-shift-or-pressure-shift
- [SC-bodymass] D. McGhie, "Body mass and pressure": https://swingcatalyst.com/resources/articles/body-mass-and-pressure
- [SC-casestudy] Swing Catalyst, "How pressure data saved a player's tournament" (no author named): https://swingcatalyst.com/resources/articles/how-pressure-data-saved-a-players-tournament
- [SC-vertical] S. K. Lynn, "Vertical forces": https://swingcatalyst.com/resources/articles/vertical-forces
- [SC-carry] S. K. Lynn, "Do increased vertical forces equal increased carry distance?": https://swingcatalyst.com/resources/articles/do-increased-vertical-forces-equal-increased-carry-distance
- [SC-kinseq] S. K. Lynn, "The kinetic sequence": https://swingcatalyst.com/resources/articles/the-kinetic-sequence
- [Lynn-deck] S. Lynn, "Understanding Leg Dominance in order to Optimize Ground Reaction Forces and Pressure Shifts in the Golf Swing" (slides, hosted by the Carolinas PGA; upload path dated 2019-03): https://carolinas.pga.com/wp-content/uploads/sites/3/2019/03/Dr.-Scott-Lynn-PhD-Swing-Catalyst.pdf
- [GSF-thread] Golf Simulator Forum, "Swing Catalyst Motion Plate price": https://golfsimulatorforum.com/forum/play-golf/instruction-academy/358801-swing-catalyst-motion-plate-price
- open-fp: `docs/PROJECT_INIT.md`, `app/python/open_fp/swing.py`, `app/assets/js/swings.js` (at commit 53d682c); `docs/research/smart2move-comparison.md`.
