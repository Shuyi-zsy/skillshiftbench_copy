# What SkillShift-Bench publishes, and what it does not

SkillShift-Bench publishes the harness, the 355 tasks, the environments, the
restore scripts, the reproduction commands and the aggregate results. It does
**not** publish per-task pass/fail judgements or execution traces.

This is a design decision, not a pending upload.

## Why

A benchmark whose per-task judgements are public can be optimized task by task.
The failure is gradual and hard to see from the outside: methods start to encode
which specific tasks are hard, reported numbers keep rising, and the benchmark's
ability to tell you anything about a *new* website evolution quietly disappears.
Withholding per-task results keeps the diagnostic value intact over time. It has
been standard practice since SWE-bench for the same reason.

What you lose is the ability to inspect somebody else's mistakes. What you keep
is a benchmark that still measures something in two years.

## What this costs, and how it is paid for

Without per-task results, a leaderboard entry cannot be recomputed by a third
party. Three mechanisms replace that:

**1. The run receipt.** `skillshift report` publishes a SHA-256 commitment to
the per-task results without publishing the results. The serialization is fixed
and documented (`skillshift.eval.receipt.canonical_per_task_form`), so anyone can
recompute the digest from a per-task file. The file itself never leaves the
machine that produced it.

**2. Aggregate-level consistency checks.** The overall value is the unweighted
mean of the eighteen cells, so `mean(3 websites) == mean(6 conditions) == O/A`
is an identity that a hand-edited number breaks. Task counts per cell are fixed
at 162 / 114 / 79. See [metrics.md](metrics.md).

**3. Provenance labels.** Every entry says where its numbers came from:

| Label | Meaning | Receipt |
| --- | --- | --- |
| `reported-only` | transcribed from a paper whose code is not released | none |
| `verified-paper` | from the SkillShift-Bench paper, by its authors | none |
| `self-reported` | an external run of this harness | **required** |

## Disputes

> If an entry is questioned, the maintainers may ask the submitter **privately**
> for that run's `per_task.jsonl`, to check it against the published
> `per_task_commitment`. The file is used only for verification and is not
> published. An entry whose submitter declines is marked `unverifiable` or
> removed from the leaderboard.

This clause is what gives the receipt teeth. Without it the digest would be
decoration.

## Practical consequences

- `per_task.jsonl` is in `.gitignore`, and `skillshift report` prints a notice
  about it on every run.
- Do not attach per-task files or traces to a leaderboard pull request. A pull
  request containing them will be asked to remove them before review.
- Keep your `per_task.jsonl`. If your entry is ever questioned, it is the only
  thing that can answer.

## Baselines

The four compared methods (AWM, ASI, SkillWeaver, WALT) are **not** re-released
here. Their leaderboard entries are transcribed from the paper's Table 1 and
labelled `reported-only`, with the original repositories and our integration
details recorded in [baselines.md](baselines.md).
