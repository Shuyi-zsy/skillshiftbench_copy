# Contributing

## Leaderboard submissions

See [docs/submit.md](docs/submit.md). Submissions go to the site repository, not
to this one.

**Never include per-task judgements or execution traces in a pull request.**
SkillShift-Bench publishes aggregate numbers only — see
[docs/results-policy.md](docs/results-policy.md). CI rejects a branch that tracks
`per_task.jsonl`, `runs/` or `trajectories/`.

## Code

```bash
pip install -e ".[dev]"
make test
make lint
```

House rules, in the order they matter:

1. **Tests first for anything in `eval/`, `conditions.py`, `registry.py` or the
   schemas.** These decide what a number on the leaderboard means; a change that
   is not pinned by a test is a change nobody can verify.
2. **The metric implementation is authoritative and singular.** If you need SR
   somewhere, import it from `skillshift.eval.metrics`. A second implementation
   is a future disagreement.
3. **Task counts are constants**, not something derived from whatever files are
   on disk: 162 / 114 / 79. A file that disagrees is a corrupted file and must
   fail loudly.
4. **Errors are explicit and name the alternatives.** `UnknownConditionError`
   lists the six conditions. Nothing is silently coerced to a nearby value.
5. **Data is immutable.** Frozen dataclasses, new objects rather than mutation.

Vendored method code (`agents/mpcr/`, `shifts/`, `eval/evaluators.py`,
`eval/llm_judge.py`) is kept close to the artifact it came from, so that the
released code is recognisably the code the paper's numbers were produced with.
Reformatting it is not an improvement; it is lost provenance. Lint is relaxed
there on purpose.

## Reporting a problem with a leaderboard entry

Open an issue naming the entry. If the maintainers ask its submitter for the
per-task file, that exchange is private and the file is not published.

## Security

See [SECURITY.md](SECURITY.md). The committed benchmark credentials are
deliberate; please do not file issues about them.
