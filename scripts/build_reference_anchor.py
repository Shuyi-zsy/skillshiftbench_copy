#!/usr/bin/env python3
"""Turn a measured 30 x 6 reference sweep into `data/reference_results/reference-react.json`.

Why this is a separate script
-----------------------------
`skillshift calibrate` grades a deployment *against* the anchor, and it refuses
to run at all while the anchor is pending -- so it cannot be the thing that
produces one.  The sweep is therefore made with the ordinary run path,

    skillshift run --agent reference --site SITE --condition COND \
        --tasks $(the site's calibration family ids) --out runs/anchor/SITE-COND

which is the same `run_condition` loop a real evaluation uses, and this script
aggregates the eighteen resulting `per_task.jsonl` files.

What it refuses to do
---------------------
Everything here exists to stop a number that was not measured from reaching the
file.  A sweep missing a cell, a cell at the wrong denominator, a task that
crashed, or a gated metric whose tolerance collapses to zero all abort without
writing.  The anchor's whole job is to tell a misconfigured environment from a
weak method; an anchor assembled from a partial sweep would do the opposite.

Usage
-----
    python scripts/build_reference_anchor.py runs/anchor \
        --model gpt-5-mini-2025-08-07 \
        --digests ../skillshift-envs/DIGESTS.json \
        --out data/reference_results/reference-react.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skillshift import __version__, paths  # noqa: E402
from skillshift.calibration import reference as reference_mod  # noqa: E402
from skillshift.calibration import subset  # noqa: E402
from skillshift.cli import DEFAULT_MAX_STEPS  # noqa: E402
from skillshift.conditions import CONDITIONS  # noqa: E402
from skillshift.eval.metrics import METRIC_NAMES, compute_cell  # noqa: E402
from skillshift.eval.records import TaskRecord, read_jsonl  # noqa: E402
from skillshift.sites import SITE_NAMES  # noqa: E402

PER_TASK_GLOB = "per_task.jsonl"

#: Recorded in the file so that a reader knows how `sigma` was produced without
#: having to find this script.
SIGMA_METHOD = "within-cell-standard-error-v1"

SIGMA_METHOD_NOTE = (
    "Within-cell standard error of a single 30 x 6 reference run. SR uses the binomial "
    "standard error sqrt(p(1-p)/n) in percentage points; AS and ASC use the within-cell "
    "sample standard deviation (ddof=1) divided by sqrt(n). This captures task-sampling "
    "noise, which dominates at n = 14 / 10 / 6, but not run-to-run variation of the "
    "language model; the reference run is therefore made at temperature 0."
)

AGENT_NOTE = (
    "The built-in no-skill ReAct agent (skillshift.agents.reference). It is a calibration "
    "anchor, not a competitive method, and it does not appear on the leaderboard."
)

GATED_METRICS_NOTE = (
    "Only SR and AS decide pass or fail. ASC is 0 by construction for a no-skill agent and "
    "SFR has no denominator at all; both are recorded for completeness and reported by "
    "`skillshift calibrate`, but neither can fail a run."
)

GATED_METRICS: tuple[str, ...] = ("SR", "AS")


class IncompleteSweep(Exception):
    """The records do not constitute a full 30 x 6 sweep of the calibration subset."""


class DegenerateTolerance(Exception):
    """A gated metric has no spread, so its cell could never be graded."""


# ---------------------------------------------------------------------------
# reading the sweep


def collect_records(roots: Sequence[Path | str]) -> tuple[TaskRecord, ...]:
    """Every record under every `per_task.jsonl` beneath the given directories."""
    records: list[TaskRecord] = []
    seen: set[Path] = set()
    for root in roots:
        root = Path(root)
        files = [root] if root.is_file() else sorted(root.rglob(PER_TASK_GLOB))
        if not files:
            raise IncompleteSweep(f"No {PER_TASK_GLOB} found under {root}.")
        for path in files:
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            records.extend(read_jsonl(path))
    return tuple(records)


# ---------------------------------------------------------------------------
# the sigma rule


def _standard_error_of_mean(values: Sequence[float]) -> float | None:
    """Sample standard deviation over sqrt(n); `None` when there is no spread.

    A zero is not a tight tolerance, it is the absence of one: the loader
    rejects `sigma <= 0` because it would make every observation infinitely
    deviant.  Returning `None` keeps that distinction visible instead of
    inventing a floor.
    """
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    variance = sum((value - mean) ** 2 for value in values) / (n - 1)
    if variance <= 0:
        return None
    return math.sqrt(variance) / math.sqrt(n)


def _binomial_standard_error(successes: int, n: int) -> float | None:
    """Binomial standard error in percentage points; `None` at p = 0 or p = 1."""
    if n <= 0:
        return None
    p = successes / n
    if p <= 0 or p >= 1:
        return None
    return 100.0 * math.sqrt(p * (1 - p) / n)


def anchor_cell(records: Sequence[TaskRecord]) -> dict:
    """One cell of the anchor: the four metrics, each with its tolerance.

    Values come from `compute_cell`, the same implementation the leaderboard
    and `calibrate` use -- an anchor computed by a second implementation would
    be measuring a second harness.
    """
    records = tuple(records)
    stats = compute_cell(records)

    successes = sum(1 for record in records if record.success)
    steps = [float(record.steps) for record in records]
    calls = [float(record.skill_calls) for record in records]

    sigmas = {
        "SR": _binomial_standard_error(successes, stats.n),
        "AS": _standard_error_of_mean(steps),
        "ASC": _standard_error_of_mean(calls),
        "SFR": None,  # no denominator for a no-skill agent; never anchored
    }
    values = {
        "SR": stats.sr,
        "AS": stats.avg_steps,
        "ASC": stats.asc,
        "SFR": None,  # recorded for completeness, never graded
    }

    cell: dict = {"n": stats.n, "n_skill_calls": stats.n_skill_calls}
    for name in METRIC_NAMES:
        cell[name] = {"value": values[name], "sigma": sigmas[name]}
    return cell


# ---------------------------------------------------------------------------
# assembling the file


def _group(records: Iterable[TaskRecord]) -> dict[tuple[str, str], list[TaskRecord]]:
    grouped: dict[tuple[str, str], list[TaskRecord]] = {}
    for record in records:
        grouped.setdefault((record.site, record.condition), []).append(record)
    return grouped


def _require_complete_sweep(grouped: Mapping[tuple[str, str], list[TaskRecord]]) -> None:
    problems: list[str] = []
    for site in SITE_NAMES:
        expected = subset.SAMPLE_COUNTS[site]
        for condition in CONDITIONS:
            cell = grouped.get((site, condition))
            if not cell:
                problems.append(f"{site}/{condition}: no records at all")
                continue
            if len(cell) != expected:
                problems.append(
                    f"{site}/{condition}: {len(cell)} record(s), expected {expected}"
                )
            crashed = [record.uid for record in cell if record.error]
            if crashed:
                problems.append(
                    f"{site}/{condition}: {len(crashed)} task(s) ended in a harness error "
                    f"({crashed[0]}); a crashed task is not a measurement"
                )
    if problems:
        raise IncompleteSweep(
            "The sweep is not a complete 30 x 6 measurement of the calibration subset:\n  "
            + "\n  ".join(problems)
        )


def _require_gradeable(cells: Mapping[tuple[str, str], dict]) -> None:
    problems = [
        f"{site}/{condition}: {name} has value "
        f"{cells[(site, condition)][name]['value']} with no spread"
        for site in SITE_NAMES
        for condition in CONDITIONS
        for name in GATED_METRICS
        if cells[(site, condition)][name]["sigma"] is None
    ]
    if problems:
        raise DegenerateTolerance(
            "These gated cells have a tolerance of zero, so `calibrate` could never grade "
            "them -- every observation would be infinitely deviant:\n  "
            + "\n  ".join(problems)
            + "\n\nThis is a finding about the sweep, not a formatting problem. Do not "
            "widen the tolerance to make it go away."
        )


def build_anchor(
    records: Iterable[TaskRecord],
    *,
    model: str,
    harness_version: str = __version__,
    measured_at: str | None = None,
    env_digests: Mapping[str, str | None] | None = None,
    threshold_sigma: float = 3.0,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> dict:
    """The anchor payload, or an exception explaining why there is not one."""
    grouped = _group(records)
    _require_complete_sweep(grouped)

    cells = {
        (site, condition): anchor_cell(grouped[(site, condition)])
        for site in SITE_NAMES
        for condition in CONDITIONS
    }
    _require_gradeable(cells)

    return {
        "schema_version": "1.0",
        "status": reference_mod.STATUS_PUBLISHED,
        "agent": "reference",
        "agent_note": AGENT_NOTE,
        "model": model,
        "harness_version": harness_version,
        "measured_at": measured_at,
        "env_digests": dict(env_digests) if env_digests is not None else None,
        "calibration_set": {
            "path": "data/calibration_set.json",
            "rule": subset.SAMPLING_RULE_ID,
            "n_families": subset.CALIBRATION_SET_SIZE,
            "n_runs": subset.CALIBRATION_SET_SIZE * len(CONDITIONS),
        },
        "sigma_method": SIGMA_METHOD,
        "sigma_method_note": SIGMA_METHOD_NOTE,
        "threshold_sigma": threshold_sigma,
        "max_steps": max_steps,
        "gated_metrics": list(GATED_METRICS),
        "gated_metrics_note": GATED_METRICS_NOTE,
        "cells": {
            site: {condition: cells[(site, condition)] for condition in CONDITIONS}
            for site in SITE_NAMES
        },
    }


# ---------------------------------------------------------------------------
# command line


def _load_digests(path: Path | None) -> dict | None:
    if path is None:
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} is not a JSON object.")
    return payload


def _summarize(anchor: Mapping) -> str:
    lines = [
        f"{'site':<10} {'condition':<9} {'n':>3}  "
        f"{'SR':>7} {'+/-':>6}   {'AS':>6} {'+/-':>6}"
    ]
    for site in SITE_NAMES:
        for condition in CONDITIONS:
            cell = anchor["cells"][site][condition]
            sr, as_ = cell["SR"], cell["AS"]
            lines.append(
                f"{site:<10} {condition:<9} {cell['n']:>3}  "
                f"{sr['value']:>7.2f} {sr['sigma']:>6.2f}   "
                f"{as_['value']:>6.2f} {as_['sigma']:>6.2f}"
            )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "run_dirs", nargs="+", help="directories holding the sweep's per_task.jsonl files"
    )
    parser.add_argument("--model", required=True, help="model id the sweep was measured with")
    parser.add_argument("--harness-version", default=__version__, dest="harness_version")
    parser.add_argument("--measured-at", default=None, dest="measured_at", help="ISO-8601 date")
    parser.add_argument("--digests", default=None, help="path to skillshift-envs/DIGESTS.json")
    parser.add_argument("--threshold", type=float, default=3.0, dest="threshold_sigma")
    parser.add_argument(
        "--max-steps",
        type=int,
        default=DEFAULT_MAX_STEPS,
        dest="max_steps",
        help="step budget the sweep was run at; recorded so calibrate can refuse a mismatch",
    )
    parser.add_argument(
        "--out",
        default=str(paths.REFERENCE_RESULTS_DIR / reference_mod.REFERENCE_RESULTS_FILENAME),
    )
    parser.add_argument("--dry-run", action="store_true", help="print the anchor, write nothing")
    args = parser.parse_args(argv)

    records = collect_records([Path(d) for d in args.run_dirs])
    print(f"{len(records)} record(s) read")

    try:
        anchor = build_anchor(
            records,
            model=args.model,
            harness_version=args.harness_version,
            measured_at=args.measured_at,
            env_digests=_load_digests(Path(args.digests) if args.digests else None),
            threshold_sigma=args.threshold_sigma,
            max_steps=args.max_steps,
        )
    except (IncompleteSweep, DegenerateTolerance) as exc:
        print(f"\nrefusing to write an anchor:\n{exc}", file=sys.stderr)
        return 1

    print()
    print(_summarize(anchor))

    if args.dry_run:
        print("\nNothing was written: --dry-run.")
        return 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(anchor, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
