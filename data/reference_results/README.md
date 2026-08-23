# Reference results — the calibration anchor

**Status: not measured yet. Every value in `reference-react.json` is `null`.**

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

## Why it is empty

The anchor can only be measured on the environment images that are actually
published, because its entire job is to detect a deployment that differs from
that one. Filling it in before the images are tagged — before
`skillshift-envs/DIGESTS.json` carries real digests — would produce numbers
indistinguishable from measured ones, and `calibrate` would then certify
environments against fiction.

Until it is measured, `skillshift calibrate` says so and exits 2. It never
reports a pass.

## File format

One file per anchor agent. Currently: `reference-react.json`.

```jsonc
{
  "schema_version": "1.0",
  "status": "pending",             // "pending" | "published"
  "agent": "reference",
  "model": null,                   // model id the anchor was measured with
  "harness_version": null,
  "measured_at": null,             // ISO-8601 date of the reference run
  "env_digests": null,             // the image digests it was measured against
  "calibration_set": { "rule": "uniform-by-index-v1", "n_families": 30, "n_runs": 180 },
  "sigma_method": null,            // how `sigma` below was produced
  "threshold_sigma": 3.0,          // deviation beyond which a cell fails
  "gated_metrics": ["SR", "AS"],   // which metrics can fail a run
  "cells": {
    "gitlab": {
      "src": {
        "n": 14,                   // pinned families for this site
        "n_skill_calls": null,     // total skill invocations behind SFR
        "SR":  { "value": null, "sigma": null },
        "AS":  { "value": null, "sigma": null },
        "ASC": { "value": null, "sigma": null },
        "SFR": { "value": null, "sigma": null }
      }
      // ... all six conditions
    }
    // ... all three sites: 18 cells, always all present
  }
}
```

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

## Filling this in

1. Tag and publish the environment images; record their digests in
   `skillshift-envs/DIGESTS.json`.
2. `skillshift run --agent reference` over the calibration subset under all six
   conditions, at temperature 0.
3. Write `value` and `sigma` per cell, set `status` to `"published"`, and record
   `model`, `harness_version`, `measured_at`, `env_digests`, and `sigma_method`.
4. `skillshift calibrate` then grades against it; nightly regression (§7.3) uses
   the same file.
