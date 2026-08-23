# Baselines

The paper compares four learned-skill methods: **AWM**, **ASI**, **SkillWeaver**
and **WALT**. Their integrations are **not** released here.

Stating that plainly is the honest thing to do, and it is more useful than a
vague promise. What follows is everything needed to reproduce the integrations
independently.

## What is and is not released

| | Released |
| --- | --- |
| The four methods' code as we ran them | **no** |
| The four methods' per-task results and traces | **no** ([results-policy.md](results-policy.md)) |
| Their aggregate numbers | yes — transcribed from the paper's Table 1, labelled `reported-only` |
| Which upstream repository and commit we started from | yes — below |
| How each was attached to the harness | yes — below |
| MPCR, including all six ablation variants | **yes**, `src/skillshift/agents/mpcr/` |
| The frozen skill library ASI and MPCR share | **yes**, `src/skillshift/agents/mpcr/actions/` and `workflows/` |

Leaderboard entries transcribed from a paper carry the `reported-only` label and
no run receipt. They are not claims about this harness; they are the published
numbers, reproduced verbatim, with their source named. See
[results-policy.md](results-policy.md).

## Method cards

> **Open item — to be completed by the authors before release.** The upstream
> repository URLs and the exact commit hashes we built on are not recorded in
> the artifact and must be filled in from the original experiment environment
> rather than guessed. Each entry below marks what is still missing.

### AWM — Agent Workflow Memory

Skills are **prompted textual workflows**: induced task/action-trajectory pairs
injected into the agent's context. There is no executable invocation, so
Average Skill Calls and Skill Failure Rate are undefined for AWM and Table 1
prints `--`.

- Upstream: _TODO: repository URL_
- Commit: _TODO_
- Integration: workflows injected as a context block, one library per site.
- Library: the equivalent format is shipped as
  `src/skillshift/agents/mpcr/workflows/{gitlab,admin,wordpress}.txt`.

### ASI — Inducing Programmatic Skills for Agentic Tasks

Skills are **executable Python functions**, verified for correctness, usage and
validity, then exposed as callable high-level actions alongside the primitives.

- Upstream: _TODO: repository URL_
- Commit: _TODO_
- Integration: induced skills registered into the action space next to the
  browsergym primitives.
- Library: the frozen library ASI and MPCR share is
  `src/skillshift/agents/mpcr/actions/{gitlab,admin,wordpress}.py` — 24
  functions (8 GitLab, 12 Magento, 4 WordPress).

### SkillWeaver

- Upstream: _TODO: repository URL_
- Commit: _TODO_
- Integration: _TODO_

### WALT

- Upstream: _TODO: repository URL_
- Commit: _TODO_
- Integration: _TODO_

## The fixed-library protocol

For the MPCR comparison, ASI first learns a library on `src`. The library is
then **frozen** and shared: ASI uses its own selector, MPCR changes only
test-time selection over the same skills and primitives. This isolates
executor-side adaptation from additional skill acquisition, and it is why the
comparison in the paper's Table 3 is attributable to selection rather than to
learning.

## Reference agent

The paper has no no-skill baseline — all four methods carry a library. The
built-in `reference` agent fills that gap: plain ReAct over the primitive action
set only, `ASC = 0` and `SFR = null` by construction. Its purpose is
calibration, not comparison, and it does not appear on the leaderboard. See
[calibration.md](calibration.md) for what `skillshift calibrate` does with it,
and [metrics.md](metrics.md) for the metric definitions.
