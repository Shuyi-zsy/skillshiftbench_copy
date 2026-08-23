"""Run receipts: provenance plus a hash commitment to the per-task results.

`skillshift report` writes three files.  Two are published -- `results.json` and
`run_receipt.json` -- and one, `per_task.jsonl`, stays on the machine that
produced it.  The receipt closes the gap that this opens: it publishes a
SHA-256 of the per-task results without publishing the results themselves, so a
disputed entry can be checked later against a file the submitter cannot
retroactively edit.

Canonical form
--------------
The digest is taken over a deliberately boring serialization, so that anyone can
recompute it in any language::

    line 1        skillshift/per-task-v1
    then, one line per record, sorted by (uid, condition):
        <uid>\\t<condition>\\t<success as 0|1>\\t<steps>\\t<skill_calls>\\t<skill_failures>
    every line terminated by "\\n", encoded UTF-8

    digest = sha256(that text).hexdigest()
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone

from .. import __version__
from ..conditions import CONDITIONS
from ..errors import ReceiptError
from ..sites import SITE_NAMES, task_counts
from .metrics import Aggregate
from .records import TaskRecord

#: Version tag of the serialization the digest is taken over.  Any change to the
#: format must bump this, so that an old receipt can never be silently compared
#: against a new serialization.
CANONICAL_FORM: str = "skillshift/per-task-v1"

SCHEMA_VERSION: str = "1.0"

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def canonical_per_task_form(records: Sequence[TaskRecord]) -> str:
    """Serialize per-task records into the exact text the digest is taken over."""
    records = tuple(records)
    if not records:
        raise ReceiptError("Cannot commit to zero per-task records.")

    keys = [(record.uid, record.condition) for record in records]
    if len(set(keys)) != len(keys):
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        raise ReceiptError(
            f"Duplicate (task id, condition) pairs in the per-task records: {duplicates[:5]}"
        )

    lines = [CANONICAL_FORM]
    for record in sorted(records, key=lambda record: (record.uid, record.condition)):
        lines.append(
            "\t".join(
                (
                    record.uid,
                    record.condition,
                    "1" if record.success else "0",
                    str(int(record.steps)),
                    str(int(record.skill_calls)),
                    str(int(record.skill_failures)),
                )
            )
        )
    return "\n".join(lines) + "\n"


def per_task_commitment(records: Sequence[TaskRecord]) -> dict:
    """Build the commitment block for a set of per-task records."""
    body = canonical_per_task_form(records)
    return {
        "algorithm": "sha256",
        "canonical_form": CANONICAL_FORM,
        "value": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "n_records": len(tuple(records)),
    }


def verify_commitment(records: Sequence[TaskRecord], commitment: Mapping) -> None:
    """Check per-task records against a published commitment.

    Used when a leaderboard entry is disputed and the submitter supplies their
    `per_task.jsonl` privately.  Raises `ReceiptError` on any mismatch.
    """
    declared_form = commitment.get("canonical_form")
    if declared_form != CANONICAL_FORM:
        raise ReceiptError(
            f"Receipt uses canonical form {declared_form!r}, but this harness computes "
            f"{CANONICAL_FORM!r}. Use the harness version that produced the receipt."
        )
    if commitment.get("algorithm") != "sha256":
        raise ReceiptError(f"Unsupported digest algorithm {commitment.get('algorithm')!r}.")

    actual = per_task_commitment(records)
    if actual["n_records"] != commitment.get("n_records"):
        raise ReceiptError(
            f"Record count mismatch: receipt commits to {commitment.get('n_records')} "
            f"records, the supplied file has {actual['n_records']}."
        )
    if actual["value"] != commitment.get("value"):
        raise ReceiptError(
            f"Per-task commitment mismatch: receipt says "
            f"{str(commitment.get('value'))[:12]}..., supplied records hash to "
            f"{actual['value'][:12]}..."
        )


def _validated_model(model: Mapping) -> dict:
    model_id = str(model.get("id", "")).strip()
    if not model_id:
        raise ReceiptError("Receipt needs a non-empty model id.")

    validated = {"id": model_id}
    for field in ("temperature", "vision", "base_url"):
        if field in model:
            validated[field] = model[field]
    return validated


def _validated_env_digests(env_digests: Mapping) -> dict:
    if not env_digests:
        raise ReceiptError(
            "Receipt needs at least one environment digest. Take them from "
            "skillshift-envs/DIGESTS.json, or record null for an environment that "
            "was not built from an official image."
        )

    validated = {}
    for name, digest in env_digests.items():
        if digest is not None and not _DIGEST_RE.match(str(digest)):
            raise ReceiptError(
                f"Environment digest for {name!r} is {digest!r}; expected "
                f"'sha256:<64 hex chars>' or null."
            )
        validated[str(name)] = digest
    return validated


def default_n_per_cell() -> dict:
    """The official task count for every (website, condition) cell."""
    counts = task_counts()
    return {site: {condition: counts[site] for condition in CONDITIONS} for site in SITE_NAMES}


def build_receipt(
    *,
    records: Sequence[TaskRecord],
    aggregate: Aggregate,
    model: Mapping,
    env_digests: Mapping,
    harness_version: str = __version__,
    harness_commit: str | None = None,
    n_per_cell: Mapping | None = None,
    timestamp: str | None = None,
    notes: str | None = None,
) -> dict:
    """Assemble a run receipt.  Every field is required by the schema."""
    aggregate_dict = aggregate.to_dict()

    return {
        "schema_version": SCHEMA_VERSION,
        "harness_version": str(harness_version),
        "harness_commit": harness_commit,
        "env_digests": _validated_env_digests(env_digests),
        "model": _validated_model(model),
        "n_per_cell": dict(n_per_cell) if n_per_cell is not None else default_n_per_cell(),
        "aggregate": {"metrics": aggregate_dict["metrics"], "n": aggregate_dict["n"]},
        "per_task_commitment": per_task_commitment(records),
        "timestamp": timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notes": notes,
    }
