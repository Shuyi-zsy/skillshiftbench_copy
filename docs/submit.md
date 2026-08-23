# Submitting to the leaderboard

## Before you start

Read [results-policy.md](results-policy.md). The short version: you submit
aggregate numbers and a run receipt. You do **not** submit per-task judgements
or traces.

## 0. Calibrate

```bash
skillshift calibrate
```

An uncalibrated run tells you that a number came out, not that it means
anything. Do this before the full sweep, not after it. See
[calibration.md](calibration.md).

## 1. Run

```bash
skillshift run --agent my_agent:MyAgent --all --out runs/mine
```

`--all` is 3 sites × 6 conditions. A cell must cover **all** of its site's tasks
— 162 GitLab, 114 Magento, 79 WordPress — or validation rejects it. Partial
sweeps are not accepted; they are the mistake the denominator check exists to
catch.

## 2. Report

```bash
skillshift report runs/mine --out submission/ \
    --name "MyMethod" \
    --model gpt-5-mini-2025-08-07 \
    --code-url https://github.com/you/mymethod \
    --digests path/to/DIGESTS.json \
    --repro-command "skillshift run --agent my_agent:MyAgent --all"
```

Three files:

| File | |
| --- | --- |
| `results.json` | submit |
| `run_receipt.json` | submit |
| `per_task.jsonl` | **keep local.** Do not commit it, do not attach it. |

Keep `per_task.jsonl` somewhere you can find it again: if your entry is ever
questioned it is the only thing that can answer.

## 3. Validate locally

```bash
skillshift validate submission/results.json
```

This runs exactly the checks the leaderboard CI runs:

1. **schema** — the file matches `results.schema.json`.
2. **coverage** — all ten slots per metric are present; every null has a reason.
3. **marginals** — task counts are 162 / 114 / 79, and
   `mean(3 websites) == mean(6 conditions) == overall`.
4. **metric-ranges** — values are in range, and SFR is flagged when it rests on
   too few skill invocations.
5. **receipt** — the receipt's provenance is official and its embedded aggregate
   matches the submission exactly.

Fix everything it reports before opening a pull request.

## 4. Open the pull request

Copy both files into the site repository and open a PR:

```
skillshift-bench.github.io/submissions/
    2026-09-15--mymethod--gpt-5-mini.json
    2026-09-15--mymethod--gpt-5-mini.receipt.json
```

CI re-runs the five checks and comments with where your entry lands and a
preview of the breakdown. A maintainer checks one thing by hand: that the method
description is accurate. Everything else is automatic.

## Labels

| Label | When |
| --- | --- |
| `self-reported` | you ran this harness — **receipt required** |
| `reported-only` | numbers from a paper whose code is not released |
| `verified-paper` | numbers from the SkillShift-Bench paper |

## Sorting, and SFR

The leaderboard sorts by SR. **SFR is not available as a sort key**, and values
resting on fewer than 30 skill invocations are marked `⚠︎`. Measured ASC is well
under one call per task, so this is the normal case rather than an edge case.
See [metrics.md](metrics.md).

## Disputes

If an entry is questioned, the maintainers may ask its submitter privately for
the run's `per_task.jsonl` and check it against the published commitment. The
file is used for verification only and is never published. An entry whose
submitter declines is marked `unverifiable` or removed.
