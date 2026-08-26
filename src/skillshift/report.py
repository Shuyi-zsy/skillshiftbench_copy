"""Turning a run into the three files `skillshift report` produces.

    results.json      aggregate numbers                -> submit
    run_receipt.json  provenance + per-task commitment -> submit
    per_task.jsonl    the raw per-task judgements      -> keep local

The third file is git-ignored by default and the command says so on every run.
SkillShift-Bench publishes aggregates and not per-task judgements, so that the
benchmark cannot be overfitted task by task; the receipt is what keeps the
unpublished half accountable.  See `docs/results-policy.md`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .eval import metrics as metrics_mod
from .eval import receipt as receipt_mod
from .eval.records import TaskRecord, write_jsonl

RESULTS_FILENAME = "results.json"
RECEIPT_FILENAME = "run_receipt.json"
PER_TASK_FILENAME = "per_task.jsonl"

PRIVATE_FILE_NOTICE = (
    f"{PER_TASK_FILENAME} holds the per-task judgements for this run. "
    f"Do not commit it and do not attach it to a leaderboard pull request: "
    f"SkillShift-Bench publishes aggregate numbers only. It is covered by the "
    f"repository's .gitignore. The receipt already commits to its contents, so "
    f"keep the file if you may need to answer a dispute later."
)

TRAJECTORY_DIRNAME = "trajectories"

PRIVATE_TRAJECTORY_NOTICE = (
    f"{TRAJECTORY_DIRNAME}/ holds this run's per-step traces (actions, "
    f"observations, token usage) for local debugging. Same rule as "
    f"{PER_TASK_FILENAME}: do not commit it, do not attach it anywhere public. "
    f"It is covered by the repository's .gitignore and is not part of the "
    f"receipt."
)

NO_SKILL_CALL_REASON = (
    "No learned skill was invoked in this run, so the skill failure rate has no "
    "denominator. Reported as null rather than 0, which would claim that no skill "
    "ever failed."
)


@dataclass(frozen=True)
class WrittenReport:
    """Where the three files went."""

    results: Path
    receipt: Path
    private: Path
    notice: str = PRIVATE_FILE_NOTICE


def build(
    records: Sequence[TaskRecord],
    *,
    submission: Mapping,
    env_digests: Mapping,
    harness_version: str = __version__,
    harness_commit: str | None = None,
    timestamp: str | None = None,
) -> tuple[dict, dict]:
    """Aggregate records into a submission and its receipt.

    An incomplete sweep raises: reporting a partial run as if it covered the
    benchmark is the failure mode the leaderboard's denominator check exists to
    catch, and it is better caught here.
    """
    cells = metrics_mod.compute_cells(records)
    aggregate = metrics_mod.aggregate(cells)
    aggregate_dict = aggregate.to_dict()

    reasons: dict[str, str] = {}
    for metric in metrics_mod.METRIC_NAMES:
        breakdown = aggregate_dict["metrics"][metric]
        has_null = (
            breakdown["overall"] is None
            or any(value is None for value in breakdown["websites"].values())
            or any(value is None for value in breakdown["conditions"].values())
        )
        if has_null and metric == "SFR":
            reasons[metric] = NO_SKILL_CALL_REASON

    results = {
        "schema_version": "1.0",
        "submission": dict(submission),
        "harness_version": str(harness_version),
        "metrics": aggregate_dict["metrics"],
        "n": aggregate_dict["n"],
        "reasons": reasons,
    }

    receipt = receipt_mod.build_receipt(
        records=records,
        aggregate=aggregate,
        model=submission["model"],
        env_digests=env_digests,
        harness_version=harness_version,
        harness_commit=harness_commit,
        timestamp=timestamp,
    )

    return results, receipt


def write(
    out_dir: Path | str,
    *,
    results: Mapping,
    receipt: Mapping,
    records: Sequence[TaskRecord],
) -> WrittenReport:
    """Write the three files, returning their paths and the privacy notice."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results_path = out_dir / RESULTS_FILENAME
    receipt_path = out_dir / RECEIPT_FILENAME
    private_path = out_dir / PER_TASK_FILENAME

    results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_jsonl(records, private_path)

    return WrittenReport(results=results_path, receipt=receipt_path, private=private_path)
