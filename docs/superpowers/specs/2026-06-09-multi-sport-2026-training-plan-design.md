# Multi-Sport 2026 Training Plan — Design

**Date:** 2026-06-09
**Status:** Approved (pending spec review)
**Owner:** Howard Bergen (Strava athlete id 16729669, Tampa / Davis Island)

## Goal

Replace the cycling-only, single-event training tool with a data-driven,
multi-sport plan covering the **remainder of the 2026 calendar year
(Jun 9 → Dec 31, 2026, ~29 weeks)**, focused on three goals:

1. **Run** — 5k under 22:00 (sub-7:05/mi).
2. **Swim** — establish a durable 2×/week swim habit.
3. **Bike** — 100 miles under 4:00 (25 mph avg) **and** build up to the
   Tuesday/Thursday 05:25 Davis Island morning rides where the athlete can
   rotate through and pull each of the 6 laps.

### Decisions locked during brainstorming
- **Deliverable:** rebuild the Python tool to be multi-sport (Approach C, hybrid).
- **Target dates:** no fixed events — achieve each goal by Dec 31, 2026. Peak
  windows chosen for Florida weather.
- **Availability:** 7 days/week, using easy/recovery days (athlete already rides
  5–6×/week).
- **Priority:** **bike-first** — Davis Island + century are protected; run/swim
  flex around the key bike days.
- **plan.py is replaced**, not kept alongside.
- **WHOOP integrated**, and recovery **drives** the plan (adaptive gating), not
  just displayed. Access via WHOOP developer OAuth app (credentials in `.env`).
- **Weekly grade (A–D ±) posted to ClickUp** as a new task per week, generated
  automatically every Sunday night. Bike-first GPA rubric (40/20/20/20).
  Destination resolved: workspace **Kviagent** → Space **HRB_Strava_Whoop** →
  List **Weekly Grades** (`CLICKUP_LIST_ID=901417168718`). Connection verified
  2026-06-10 with a test task.

## Baseline (last 3 years, 669 activities, pulled 2026-06-09)

- **Run:** 96 runs. Best recent ~5k-equivalent **22:47 / 7:18 pace** (2025-11-27);
  several 22:5x–23:xx efforts. Only 10 runs / 42 mi in last 90 days. Sub-22 is
  ~45s away over 5k — a speed-and-consistency problem, not a base problem.
- **Swim:** 14 swims ever, all in a single Oct–Dec 2025 block (~1,372 m / ~21 min).
  Near-zero habit; goal is consistency, not performance.
- **Bike:** Strong engine — 40 rides / 1,453 mi in 90 days; 19.1 mph avg on 20mi+
  rides. Already doing Tue/Thu ~05:00 rides at 32–36 mi, 21–23 mph. 25 mph century
  is elite solo, realistic in a paceline.
- **Recovery (WHOOP, pulled 2026-06-10):** well-recovered — recovery mostly green
  over the last 7 days (69–95%), RHR 46–51, HRV ~68–97 ms, sleep performance
  78–82%. Supports the planned bike build.

## Approach

**Hybrid (C):** a fixed, periodized weekly *skeleton* per training block, plus a
*data layer* that re-grounds targets from the latest Strava **and WHOOP** pull
each time the tool runs. The athlete re-runs it (e.g. monthly for the structure,
daily for recovery gating) and the prescribed paces, recovery-adjusted intensity,
and goal-progress numbers update without rewriting the plan structure.

## Architecture

Python modules consistent with the existing project style
(`requests` + `python-dotenv`, console output + saved files):

### `fetch.py` (extend)
- Today filters to `{"Ride", "VirtualRide", "EBikeRide"}`. Extend the type set to
  also include `Run` and `Swim`.
- Keep token auto-refresh logic unchanged.
- Save all matched activities to `activities.json` (now multi-sport).
- Default lookback expanded so run/swim history is captured (full history; the
  existing fetch already pages all activities, so just widen the type filter).

### `whoop_auth.py` (built)
- One-time WHOOP OAuth2 flow, mirrors `auth.py`: local callback server on
  `localhost:8081`, opens browser, exchanges code, saves
  `WHOOP_ACCESS_TOKEN` / `WHOOP_REFRESH_TOKEN` / `WHOOP_TOKEN_EXPIRES_AT` to
  `.env`. Uses a `state` param (CSRF check). Scopes: `read:recovery`,
  `read:cycles`, `read:sleep`, `read:workout`, `read:profile`, `offline`.

### `whoop_fetch.py` (new)
- Pulls recovery, sleep, and cycle (day strain) data from the WHOOP **v2** API
  (`https://api.prod.whoop.com/developer/v2/...`). **Note:** WHOOP v1 is dead for
  these resources — `/v2/recovery`, `/v2/activity/sleep`, `/v2/cycle`,
  `/v2/activity/workout` are the live endpoints; `/v2/user/profile/basic` for
  profile.
- Auto-refreshes the WHOOP token when expired (same pattern as `fetch.py`),
  writing the rotated tokens back to `.env`.
- Saves recent records (default trailing ~60 days) to `whoop.json`.

### `grade.py` (new)
- Computes a **weekly training grade** for the most recently completed week
  (Mon–Sun) and posts it to ClickUp as a new task.
- **Rubric (GPA 0–4.0, bike-first):**
  - 🚴 Bike adherence — **40%**: hit Tue/Thu Davis Island + Sat long; weekly
    volume within target band (and not over the ≤10% cap); pull progression met.
  - 🏊 Swim consistency — **20%**: 2 swims completed.
  - 🏃 Run execution — **20%**: prescribed quality run done at/under target paces.
  - ❤️ Recovery management — **20%**: respected red/yellow WHOOP days; no overreach.
  - Each component scores 0–4.0; weighted average → letter with +/−
    (≥3.85 A, 3.5–3.84 A−, 3.15–3.49 B+, …, GPA-standard bands). Goal-progress
    trend (e.g. 5k pace improving) may nudge ±0.1.
- Reads `activities.json` + `whoop.json` (no extra fetch needed if those are
  fresh; otherwise it triggers `fetch.py` / `whoop_fetch.py` first).
- **ClickUp delivery:** POST a task to `CLICKUP_LIST_ID` via the ClickUp v2 API
  (`https://api.clickup.com/api/v2/list/{list_id}/task`, `Authorization:
  CLICKUP_API_TOKEN`). Task name: `Week of {Mon date} — Grade: {letter}`;
  description: per-component scores, weekly bike volume vs target, swim/run/
  recovery detail, and goal-progress deltas (markdown).
- **Scheduling:** runs automatically **every Sunday night** via Windows Task
  Scheduler invoking `python grade.py` (the implementation plan will include the
  scheduled-task setup; on-demand `python grade.py` also works).
- Idempotency: before creating, it checks the List for an existing task with the
  same "Week of …" name and updates it instead of duplicating.

### `plan.py` (replace)
The new multi-sport generator + goal tracker. Sections:

1. **Config constants** — goals, dates (`START = 2026-06-09`,
   `END = 2026-12-31`), the four blocks with date ranges, weekly template,
   and Davis Island pull progression per block.
2. **Parsing** — `parse_activity(a)` normalizes each activity with `sport`
   (`run`/`swim`/`bike`), date, distance (mi for run/bike, m for swim),
   moving time, pace/speed.
3. **Analysis per sport:**
   - `analyze_run` — best rolling ~5k-equivalent pace (90d and all-time),
     runs/week, derived workout paces (VO2 ~current-5k pace minus ~15–25s,
     threshold, easy) from current 5k fitness.
   - `analyze_swim` — sessions/week over trailing 8 weeks; streak vs 2×/week.
   - `analyze_bike` — 20mi+ avg speed, weekly volume, longest ride, and Tue/Thu
     pre-07:00 ride detection (count + avg speed) for Davis Island progression.
   - `analyze_recovery` — reads `whoop.json`: latest recovery score, 7-day
     recovery trend, HRV/RHR baseline and deviation, recent sleep performance.
4. **Plan generation** — emit a week-by-week schedule from START to END using the
   block the week falls in + the weekly template, substituting block-specific run
   workouts, swim focus, bike long-ride distance, and pull targets. Distances/paces
   come from the data layer where applicable.
5. **Adaptive recovery gating** (see dedicated section) — adjusts *today's*
   prescribed session up or down based on the latest WHOOP recovery score.
6. **Goal scorecard** — for each of the 3 goals, compute on-track/off-track with
   the live number (e.g. "Swim 2×/wk: 6 of last 8 weeks", "5k best 22:47 → −47s
   to go", "Davis Island: pulling 3 of 6 laps"), plus a recovery summary
   (latest score + 7-day trend).
7. **Output** — console analysis + full schedule + scorecard + today's
   recovery-gated recommendation; save to `training_plan.txt`.

### `excel.py` (update)
Render the multi-sport weekly schedule (one row per day, color-coded by sport)
plus a goal scorecard section/tab. Save to `training_plan.xlsx`.

## Periodization — 4 blocks (heat-aware, bike-first)

| Block | Dates | Run | Swim | Bike |
|---|---|---|---|---|
| **1 · Base + Habit** | Jun 9 – Jul 31 | Easy + strides only (heat) | Lock 2×/wk habit | Strength: Tue/Thu + Sat long |
| **2 · Build** | Aug 1 – Sep 30 | Intro intervals as temps ease | Maintain 2×/wk | Century volume ramp (Sat 50→80 mi) |
| **3 · Sharpen** | Oct 1 – Nov 15 | 5k-specific track speed | Maintain | Race-pace + paceline pull blocks |
| **4 · Peak/Attempt** | Nov 16 – Dec 31 | Sub-22 5k TT window (cool) | Maintain | 100-in-4 attempt window + taper |

### Weekly template (7 days, bike-first)
- **Mon** — Swim (technique)
- **Tue** — Davis Island AM ride (paceline / pulls) — *key bike*
- **Wed** — Run quality (strides → intervals by block)
- **Thu** — Davis Island AM ride — *key bike*
- **Fri** — Swim (endurance)
- **Sat** — Long ride (century build) — *key bike*
- **Sun** — Easy run / recovery spin / brick

2 swims, 2 runs, 3 key bikes. Sun and easy days absorb recovery. When run and
bike conflict, bike wins (priority decision); run quality is placed on non-Tue/Thu
days to protect both.

### Bike volume progression rules (hard constraints)
The plan generator MUST enforce these when emitting weekly bike mileage:
- **≤10% week-over-week increase.** No build week's total bike volume may exceed
  the previous week's by more than 10%. This is a hard cap checked in code; if a
  block's target would jump more, the generator clamps it and carries the
  remainder into the following week.
- **Starting point = current sustainable load.** Week 1 anchors at **~170 mi**,
  the athlete's trailing active-week average as of 2026-06-09 (recent weeks:
  175 / 155 / off / 143 / 244; last week was a 244 mi peak, deliberately NOT used
  as the anchor to avoid compounding upward from a spike). The 90-day average
  (~112) is too low — it includes lighter early-spring weeks — so it is not used.
- **3-up / 1-down cadence.** Every 4th week is a recovery week at ~75–80% of the
  prior week's volume (a *decrease* is always allowed — the 10% cap governs
  increases only). The next build week resumes from the pre-recovery level, then
  may rise ≤10% from there.
- **Volume ceiling = ~225 mi/wk.** Build weeks are also clamped to a ceiling so
  the ≤10% ramp doesn't compound past a sustainable peak. With the 170 anchor the
  curve is 170 → 187 → 206 → *(recovery 161)* → **225 and hold**, reached ~week 5.
  225 sits just under the athlete's historical max week (244). After the ceiling,
  bike progression comes from **intensity** (Saturday long-ride distance, Davis
  Island pull count, race-pace blocks), not weekly volume.
- **Down weeks and taper are exempt** from the 10% cap (they reduce volume). The
  Block 4 taper drops below the 225 hold for the 100-mile attempt.
- The weekly-total ranges in the table above are guidance; the ≤10% rule is the
  binding constraint and wins if they ever conflict.

### Davis Island "pull all 6 laps" progression
Prescribed on Tue/Thu rides, tracked against detected ride data:
- **Block 1:** sit in + 1–2 short pulls
- **Block 2:** 3–4 pulls
- **Block 3:** all 6 laps, shorter pulls
- **Block 4:** all 6 laps, full strong pulls

## Adaptive recovery gating (WHOOP)

WHOOP recovery **drives** today's session, not just displays it. On any day the
tool runs, it reads the most recent recovery score from `whoop.json` and adjusts
the scheduled session:

| Recovery | Band | Action on a scheduled **hard/quality** day | Action on an easy/recovery day |
|---|---|---|---|
| **67–100%** | 🟢 Green | Greenlight as prescribed (or allow the optional "extra" if planned) | Keep easy |
| **34–66%** | 🟡 Yellow | Hold intensity but trim volume ~20–30% (fewer intervals / shorter pulls) | Keep easy |
| **0–33%** | 🔴 Red | **Downgrade to easy/recovery** — swap intervals/pulls for Zone 2, or rest | Convert to rest/mobility |

Rules and guardrails:
- **Bike-first still applies:** a red day downgrades a Tue/Thu paceline ride to a
  sit-in Zone 2 spin rather than skipping the bike entirely, unless recovery is
  red **and** sleep performance is poor, in which case full rest is recommended.
- **Gating is advisory + logged:** the tool prints the original prescription and
  the recovery-adjusted recommendation side by side; it never silently rewrites
  the saved 29-week plan structure.
- **Trend, not just today:** if recovery is red ≥2 days running, the tool flags a
  possible need to insert an unplanned recovery week (overrides the 3-up/1-down
  cadence for that week).
- **Thresholds are config constants** (green ≥67, red ≤33 by default) so they can
  be tuned.

## Error handling
- Missing `activities.json` → instruct to run `fetch.py` (existing behavior).
- Empty sport (e.g. no runs) → analysis returns a neutral baseline and the plan
  still generates with default prescribed paces; scorecard flags "insufficient
  data".
- Token expiry handled by the `fetch.py` / `whoop_fetch.py` refresh paths.
- **Missing/stale `whoop.json`** → recovery gating is skipped gracefully; the plan
  prints sessions as prescribed with a "no recent WHOOP data — gating off" note.
  WHOOP being unavailable never blocks plan generation.
- **Missing `CLICKUP_API_TOKEN`/`CLICKUP_LIST_ID`** → `grade.py` still computes and
  prints/saves the grade locally, and warns that the ClickUp post was skipped.
- **ClickUp API error** (auth/network) → logged; the grade is saved locally so the
  week is never lost, and the post is retried on the next run.

## Testing
- Unit-test parsing + per-sport analysis against a small fixture of
  run/swim/bike activities (known paces/dates) to verify: 5k-equivalent pace,
  swim sessions/week, Tue/Thu detection, derived workout paces.
- Smoke-test full `plan.py` run against the real `activities.json`: 29 weeks
  generated, every week assigned a block, scorecard renders all 3 goals.
- **Volume-cap test:** assert no week's total bike volume exceeds the prior
  week's by more than 10%, that week 1 starts at ~170 mi (the configured anchor),
  and that a recovery week appears every 4th week.
- **Recovery-gating test:** with fixture WHOOP data, assert a red day (≤33%)
  downgrades a scheduled hard session to easy, a yellow day trims volume, a green
  day passes through, and missing `whoop.json` disables gating without error.
- **Grading test:** with fixture week data, assert each component scores correctly
  (e.g. 2 swims → swim 4.0; 1 swim → 2.0), the weighted GPA maps to the right
  letter+/− band, and a perfect/poor week grade as expected.
- **ClickUp test:** mock the ClickUp API to assert the correct task name/body are
  POSTed to the configured list, that a missing token skips the post without
  raising, and that an existing same-week task is updated rather than duplicated.
- Verify `excel.py` produces a valid workbook with the schedule + scorecard.

## Out of scope (YAGNI)
- No fully adaptive day-by-day rewriting (Approach B).
- No GUI / web UI.
- No nutrition or strength-program detail beyond brief notes.
- No multi-athlete support.
