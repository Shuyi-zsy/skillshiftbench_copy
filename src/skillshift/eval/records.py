"""Per-task run records -- the input to every metric.

These records never leave the machine that produced them.  `skillshift report`
writes them to `per_task.jsonl`, which is git-ignored by default, and commits to
their content only through the SHA-256 in the run receipt.  See
`docs/results-policy.md` for why.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from ..errors import MetricError

#: Fields written to `per_task.jsonl`, in the order used by the receipt hash.
RECORD_FIELDS: tuple[str, ...] = (
    "uid",
    "site",
    "condition",
    "success",
    "steps",
    "skill_calls",
    "skill_failures",
)


@dataclass(frozen=True)
class TaskRecord:
    """The outcome of running one task under one condition.

    Attributes:
        uid: Canonical task id, e.g. `skillshift.gitlab.v1.9`.
        site: Canonical site name.
        condition: One of the six conditions.
        success: Whether the task's automatic scorer returned a positive score.
        steps: Actions taken before success, failure, or timeout.
        skill_calls: Learned-skill invocations reported by the agent.
        skill_failures: Of those, the ones that failed during execution.
    """

    uid: str
    site: str
    condition: str
    success: bool
    steps: int
    skill_calls: int
    skill_failures: int
    #: Harness-level failure (an agent crash, a browser error). Diagnostic only:
    #: it is deliberately *not* part of the receipt hash, so that re-running a
    #: crashed task with a fixed agent does not silently change a commitment.
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def to_jsonl(records: Iterable[TaskRecord]) -> str:
    """Serialize records as JSON Lines, one record per line."""
    return "".join(
        json.dumps(record.to_dict(), sort_keys=True, ensure_ascii=False) + "\n"
        for record in records
    )


def write_jsonl(records: Iterable[TaskRecord], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_jsonl(records), encoding="utf-8")
    return path


def read_jsonl(path: Path) -> tuple[TaskRecord, ...]:
    """Read records back, failing loudly on any malformed line."""
    path = Path(path)
    if not path.is_file():
        raise MetricError(f"Per-task record file not found: {path}")

    records = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MetricError(f"{path}:{lineno} is not valid JSON: {exc}") from exc

        missing = [field for field in RECORD_FIELDS if field not in payload]
        if missing:
            raise MetricError(f"{path}:{lineno} is missing field(s): {missing}")

        records.append(
            TaskRecord(
                uid=str(payload["uid"]),
                site=str(payload["site"]),
                condition=str(payload["condition"]),
                success=bool(payload["success"]),
                steps=int(payload["steps"]),
                skill_calls=int(payload["skill_calls"]),
                skill_failures=int(payload["skill_failures"]),
                error=payload.get("error"),
            )
        )

    return tuple(records)
