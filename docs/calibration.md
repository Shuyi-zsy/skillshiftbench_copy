# Calibration — telling a bad environment from a bad method

The first number you get out of a new benchmark is uninterpretable. If your
method scores 22% on GitLab, you cannot tell whether the method is weak, or
whether your GitLab container came up as the wrong version, or whether the
restore left the database half-populated.

The four methods in the paper do not answer that question, because all four
carry a skill library. `skillshift calibrate` does.

```bash
skillshift calibrate
```

It runs the built-in **no-skill ReAct reference agent** over a fixed subset of
thirty task families under all six conditions — 180 runs — and reports, per
cell, how far your deployment sits from the published anchor.

Budget hours, not minutes. Measured on a 16-core x86_64 host with all five
environments up, one task takes roughly 70–110 seconds: ten LLM calls at most,
each carrying a full accessibility tree, plus the browser work between them.

Each task also has a wall-clock ceiling (`--task-timeout`, 600s by default).
The run loop bounds *steps*, not time, and a browser call that never returns
would otherwise stall the whole sweep — one did, for eleven hours, while the
sites themselves answered in under 100ms. A task that hits the ceiling is
recorded as an error rather than as a failure, because it is the absence of a
measurement, not a measurement of failure.

> **Status: published.** Measured 2026-08-26 against `gpt-5-mini-2025-08-07` —
> 180 real runs, 58 successes (32.2% SR overall), zero crashed tasks. See
> [`../data/reference_results/README.md`](../data/reference_results/README.md).

## Exit codes

| code | meaning |
| ---: | --- |
| `0` | every gated value is within tolerance — your environment matches the anchor |
| `1` | at least one gated value deviates beyond the threshold — something is different |
| `2` | the check could not be made: the subset is missing, the anchor is unpublished, or your step budget is not the one the anchor was measured at |

`1` and `2` are deliberately distinct. `1` is a finding; `2` is the absence of
one, and a script must not treat them the same.

### The step budget has to match

AS is a count of steps, so the same agent behaving identically scores a
different AS under a different `--max-steps`. The anchor records the budget it
was measured at, and `calibrate` refuses (exit `2`) rather than grading across
two of them — reporting a budget difference as a misconfigured environment
would be a wrong answer, not a conservative one. Nothing is run when the
budgets disagree, so a mismatch costs no API calls.

## The subset

[`data/calibration_set.json`](../data/calibration_set.json) pins thirty **task
families** — GitLab 14, Magento 10, WordPress 6.

It pins *families*, not task uids, because one calibration task is run under all
six conditions: `src*` loads the v1 task file and `tgt*` the v2 one. A pinned
uid such as `skillshift.gitlab.v1.0` would lock only half of each family's grid.

The choice is a stated rule, not a hand-picked list, so anyone can recompute it:

```
index_j = floor(j * n_tasks / k)     for j = 0 .. k-1
```

with `(n_tasks, k)` = `(162, 14)`, `(114, 10)`, `(79, 6)`. No seed, no
randomness. The rule lives in `skillshift.calibration.subset`, the shipped JSON
is its output, and `tests/test_calibration_set.py` asserts the two agree — and
that all thirty ids resolve in both site versions.

To see the plan without running anything:

```bash
skillshift calibrate --dry-run
skillshift calibrate --dry-run --site wordpress
```

## The anchor and its tolerance

[`data/reference_results/reference-react.json`](../data/reference_results/reference-react.json)
holds, per (site, condition) cell and per metric, a `value` and a `sigma`.
`calibrate` reads

```
deviation = |observed - value| / sigma
```

and flags a cell when that exceeds `threshold_sigma` (3.0 by default;
`--threshold` overrides it).

`sigma` is the **within-cell standard error of a single 30 × 6 reference run**:
the binomial standard error `sqrt(p(1-p)/n)` for SR, and the within-cell sample
standard deviation over `sqrt(n)` for AS and ASC. That is estimable from one
run, which is what keeps the anchor a one-time cost, and it covers the noise
that dominates at n = 14 / 10 / 6 — which tasks happened to be sampled. It does
**not** cover run-to-run variation of the language model; the reference run is
made at temperature 0, and the limitation is written down rather than absorbed
into a rounder tolerance.

### Only SR and AS decide pass or fail

- **SR** is the signal.
- **AS** is what actually catches a wrong image. An agent facing an unexpected
  page layout takes more steps before giving up, and it does so before the
  success rate has moved enough to be visible at n = 14.
- **ASC** is 0 by construction — the reference agent has no skill library.
- **SFR** has no denominator at all, and is never a gate anywhere in this
  project. See [metrics.md](metrics.md).

ASC and SFR are still printed, marked `[not gated]`.

## Reading the output

```
  gitlab     tgt       SR   observed    41.00  anchor    22.00 +/- 2.10    9.0 sigma  FAIL  [image gitlab-v16]
```

The image name is the one `skillshift-envs` publishes and the key under which
its digest is recorded in `DIGESTS.json` — so a failing row names the container
to go and look at.

## What calibration is not

- **Not a benchmark score.** Its denominators are 14 / 10 / 6, not
  162 / 114 / 79. A calibration number fails the leaderboard's denominator check
  by construction, deliberately. It is not a leaderboard entry and the reference
  agent does not appear on the leaderboard.
- **Not a dev set.** Tuning a method on these thirty families is calibrating
  against your own thermometer.

## Options

| flag | |
| --- | --- |
| `--site` | calibrate one website instead of all three |
| `--dry-run` | print the cells and task counts, run nothing |
| `--reference PATH` | grade against a different anchor file |
| `--threshold N` | override the anchor's own sigma threshold |
| `--agent` | anchor agent, default `reference` |
| `--out` | where `per_task.jsonl` goes, default `runs/calibration` |
| `--workers N` | run N tasks at once within each (site, condition) cell, default 1 (serial) |
| `--save-trajectories` | write a local per-step trace (actions, observations, token usage) per task under `<out>/trajectories/`; off by default |

The per-task records a calibration run produces are per-task judgements like any
other, and are covered by the same rule: they stay on your machine. See
[results-policy.md](results-policy.md).
