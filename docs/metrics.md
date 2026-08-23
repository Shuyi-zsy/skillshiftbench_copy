# Metrics

Four diagnostics, defined in Section 2.4 of the paper and implemented once, in
[`src/skillshift/eval/metrics.py`](../src/skillshift/eval/metrics.py).

| | Definition | Unit |
| --- | --- | --- |
| **SR** | Success Rate — fraction of tasks meeting the success criterion | percent |
| **AS** | Average Steps — mean actions before success, failure, or timeout | count |
| **ASC** | Average Skill Calls — mean learned-skill invocations per task | count |
| **SFR** | Skill Failure Rate — share of invoked skills that failed | percent |

Two details that are easy to get wrong:

- **AS averages over every task**, not only successful ones. It measures
  interaction cost and recovery burden, so a task that burned ten steps and
  failed belongs in the average.
- **SFR counts runtime errors as failures.** A skill whose steps are correct but
  which cannot be realized on the current page has failed.

## The cells and the ten numbers

A *cell* is one (website, condition) pair — three websites × six conditions =
eighteen cells. A submission publishes ten numbers per metric: three website
marginals, six condition marginals, and the overall value. This is the shape of
the paper's Table 1, deliberately: an entry transcribed from a paper and an
entry computed from a run are the same object.

```
              Website                      Environment                     O/A
        GitLab  Magento  WordPress   Src  Src-Perc  Src-Exec  Tgt  Tgt-Perc  Tgt-Exec
SR       17.71    25.49      62.66  50.07     43.35     22.45 41.28    37.65     16.90   35.29
```

## Aggregation is macro, not task-weighted

The website marginal is the **unweighted** mean of that website's six cells.
The condition marginal is the **unweighted** mean of that condition's three
cells. The overall value is the unweighted mean of all eighteen.

Websites are **not** weighted by task count. GitLab has 162 tasks, Magento 114
and WordPress 79, but each contributes one third of the overall value. This is
verified against every row of the published Table 1 in
[`tests/test_table1_transcription.py`](../tests/test_table1_transcription.py):
the macro average reproduces the printed `O/A` for all fourteen rows, while
weighting by task count moves SR/AWM from 35.29 to 30.21.

Because both marginals are macro-averages of the same eighteen cells,

```
mean(3 websites) == mean(6 conditions) == O/A
```

is an identity. The leaderboard checks it. It is what lets an entry be verified
from ten numbers, without publishing the per-task judgements behind them — a
single mistyped cell breaks it.

## SFR is a supplementary diagnostic, and often unstable

The paper is explicit about this, and so is the leaderboard.

SFR is a ratio over the number of skill invocations. Measured ASC is small:
0.06 calls per task for ASI and 0.15 for MPCR in the paper's fixed-library
comparison — **fewer than one skill call per task**. A whole cell can therefore
rest on a handful of invocations, and the ratio is then dominated by sampling
noise.

Consequently:

- **The leaderboard sorts by SR by default. SFR is not available as a sort key.**
- A value resting on fewer than **30** invocations is displayed as `0.32 ⚠︎`,
  with the invocation count on hover.
- `n.skill_calls` is required in a self-reported submission, because without it
  the flag cannot be decided and an unstable value would look stable.

From the paper: SFR "is unstable when skills are rarely invoked, since the ratio
is then taken over a very small denominator; we therefore report it as a
supplementary diagnostic and characterize low-invocation regimes through ASC."

## Undefined values

`null` and `0` mean different things and are never interchanged.

- **ASC = 0** — the method invoked no learned skill. A real measurement.
- **SFR = null** — no skill was invoked, so the ratio has no denominator.
  Reporting `0` here would claim that no skill ever failed.
- **ASC = null, SFR = null** — the metric does not apply to the method at all.
  AWM is the paper's example: it reuses prompted textual workflows rather than
  executable skill invocations, and Table 1 prints `--` for both.

Every null in a submission needs an entry in `reasons`, keyed by metric
(`"ASC"`) or by cell (`"SFR.websites.wordpress"`).

## Where the numbers come from

`skillshift report` computes all of this from `per_task.jsonl`, which holds one
record per task:

```json
{"uid": "skillshift.gitlab.v1.9", "site": "gitlab", "condition": "tgt-exec",
 "success": false, "steps": 10, "skill_calls": 1, "skill_failures": 1}
```

`success` comes from the task's automatic scorer, `steps` from the run loop, and
`skill_calls` / `skill_failures` from the agent's `SkillRecorder` — see
[custom-agent.md](custom-agent.md).
