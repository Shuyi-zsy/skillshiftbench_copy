# Reference results — the calibration anchor

**Status: published.** Measured 2026-08-26 against `gpt-5-mini-2025-08-07`, on
the environment images recorded in `env_digests` — 180 real runs, 58
successes (32.2% SR overall), zero crashed tasks. See `reference-react.json`.

## What this directory is

The numbers a first-time user needs in order to tell *"my method is weak"* from
*"my GitLab image is the wrong version"*.

The four methods in the paper all carry a skill library, so none of them answers
that question. This directory holds the answer for the built-in **no-skill ReAct
reference agent** (`skillshift.agents.reference`) run over the thirty pinned
families in [`../calibration_set.json`](../calibration_set.json), under all six
conditions — 30 × 6 = 180 runs.

`skillshift calibrate` reproduces those 180 runs locally and reports, per cell,
how many standard deviations your environment sits from this anchor.

## What this directory is **not**

- **Not a leaderboard entry.** Its denominators are 14 / 10 / 6, not the
  benchmark's 162 / 114 / 79, so it fails the leaderboard's denominator check by
  construction — deliberately. See `docs/results-policy.md` §6.5.
- **Not a baseline to beat.** The reference agent is an instrument, not a method.
- **Not a dev set.** Tuning a method on these thirty families is calibrating
  against your own thermometer.

## Why it stayed empty until 2026-08-26

The anchor could only be measured once the environment images were actually
published, because its entire job is to detect a deployment that differs from
that one. Filling it in before the images were tagged — before
`skillshift-envs/DIGESTS.json` carried real digests — would have produced
numbers indistinguishable from measured ones, and `calibrate` would then
certify environments against fiction.

While it was `"pending"`, `skillshift calibrate` said so and exited 2. It
never reported a pass. Anyone building their own anchor before it is measured
hits the same refusal — see `TestUnpublishedAnchor` in `tests/test_cli_calibrate.py`.

## File format

One file per anchor agent. Currently: `reference-react.json`.

```jsonc
{
  "schema_version": "1.0",
  "status": "published",           // "pending" | "published"
  "agent": "reference",
  "model": "gpt-5-mini-2025-08-07",  // model id the anchor was measured with
  "harness_version": "0.1.0",
  "measured_at": "2026-08-26",     // ISO-8601 date of the reference run
  "env_digests": { "gitlab-v12": "sha256:...", "..." : "..." },  // the image digests it was measured against
  "calibration_set": { "rule": "uniform-by-index-v1", "n_families": 30, "n_runs": 180 },
  "sigma_method": "within-cell-standard-error-v1",  // how `sigma` below was produced
  "threshold_sigma": 3.0,          // deviation beyond which a cell fails
  "max_steps": 10,                 // step budget the sweep ran at; calibrate must match it
  "gated_metrics": ["SR", "AS"],   // which metrics can fail a run
  "cells": {
    "gitlab": {
      "src": {
        "n": 14,                   // pinned families for this site
        "n_skill_calls": 0,        // total skill invocations behind SFR
        "SR":  { "value": 14.29, "sigma": 9.35 },
        "AS":  { "value": 8.43, "sigma": 0.89 },
        "ASC": { "value": 0.0, "sigma": null },
        "SFR": { "value": null, "sigma": null }
      }
      // ... all six conditions
    }
    // ... all three sites: 18 cells, always all present
  }
}
```

A pending anchor (before its own sweep is measured) carries the same shape
with every value `null` and `status: "pending"` — that is the state this file
was in until 2026-08-26, and the state anyone building their own anchor
starts from.

`calibrate` reads `|observed − value| / sigma` and flags a cell when that
exceeds `threshold_sigma`.

### Where `sigma` comes from

**Within-cell standard error of a single 30 × 6 reference run.**

| metric | sigma |
| --- | --- |
| SR | binomial standard error, `sqrt(p(1−p)/n)`, in percentage points |
| AS | within-cell sample standard deviation ÷ `sqrt(n)` |
| ASC | within-cell sample standard deviation ÷ `sqrt(n)` |
| SFR | not anchored — no denominator for a no-skill agent |

This is estimable from **one** reference run, which is what keeps the anchor a
one-time cost. It captures the noise that dominates at n = 14 / 10 / 6 — which
tasks happened to be sampled — but not run-to-run variation of the language
model. The reference run is therefore made at temperature 0, and that limitation
is stated here rather than hidden in the tolerance.

A `sigma` of zero is rejected on load: it would make every observation
infinitely deviant. Cells whose metric genuinely has no spread keep `null` and
are reported as "not compared".

### Which metrics decide pass/fail

Only **SR** and **AS**.

- **SR** is the signal.
- **AS** is what actually catches a wrong image: an agent facing an unexpected
  page layout takes more steps before it gives up, and it does so before the
  success rate has moved enough to be visible at n = 14.
- **ASC** is 0 by construction for a no-skill agent.
- **SFR** has no denominator at all. It is never a gate, and never a sort key
  anywhere in this project — see `docs/metrics.md`.

## How this was measured (and how to re-measure it)

1. Tag and publish the environment images; record their digests in
   `skillshift-envs/DIGESTS.json`.
2. `skillshift run --agent reference --site SITE --condition COND --tasks ...
   --save-trajectories` over the calibration subset under all six conditions,
   at temperature 0 — one invocation per (site, condition) cell, 18 in total.
   `--save-trajectories` is optional (see `docs/results-policy.md`) but is
   what let the 2026-08-26 sweep's task-39/task-65-style failures be diagnosed
   from real per-step traces instead of re-probing the live site by hand.
3. `scripts/build_reference_anchor.py` aggregates the sweep's `per_task.jsonl`
   files into `value`/`sigma` per cell, sets `status` to `"published"`, and
   records `model`, `harness_version`, `measured_at`, `env_digests`,
   `sigma_method` and `max_steps`. It refuses to write anything from a sweep
   that is missing a cell, sits at a wrong denominator, contains a crashed
   task, or yields a gated metric with no spread — none of which happened in
   the 2026-08-26 sweep (see `TestTheShippedAnchor` in
   `tests/test_cli_calibrate.py`).
4. `skillshift calibrate` then grades against it; nightly regression (§7.3) uses
   the same file.

If the environment images change (a new WordPress theme, a GitLab version
bump), the anchor no longer describes the deployment it is meant to detect
drift from, and needs remeasuring the same way.
