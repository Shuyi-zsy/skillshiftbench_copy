#!/usr/bin/env python3
"""Regenerate `data/calibration_set.json` from the sampling rule.

The rule lives in `skillshift.calibration.subset`; this script only serializes
its output together with enough context that a reader can recompute the same
thirty ids by hand.  Run it after changing the rule -- and give the rule a new
id when you do, because the published reference results were measured on the
subset the old id names.

    python scripts/build_calibration_set.py [--check]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from skillshift import paths, registry, sites  # noqa: E402
from skillshift.calibration import subset  # noqa: E402
from skillshift.conditions import CONDITIONS  # noqa: E402

WHAT_THIS_IS = (
    "A fixed subset of 30 task families used to check that a local deployment of the "
    "benchmark websites behaves like the one the published numbers were produced on. "
    "`skillshift calibrate` runs the built-in no-skill reference agent over these "
    "families under all six conditions (30 x 6 = 180 runs) and compares the result "
    "with data/reference_results/."
)

WHAT_THIS_IS_NOT = (
    "Not a leaderboard split, not a dev set, and not a benchmark score. Its "
    "denominators (14 / 10 / 6) are not the benchmark's (162 / 114 / 79), and a "
    "number measured on it must never be reported as a SkillShift-Bench result. "
    "Tuning a method on these 30 families is measuring your own thermometer."
)


def build() -> dict:
    """The full contents of `data/calibration_set.json`."""
    indices = {
        site: list(subset.sample_indices(sites.get(site).n_tasks, count))
        for site, count in subset.SAMPLE_COUNTS.items()
    }
    return {
        "schema_version": subset.SCHEMA_VERSION,
        "name": "SkillShift-Bench calibration subset",
        "what_this_is": WHAT_THIS_IS,
        "what_this_is_not": WHAT_THIS_IS_NOT,
        "id_kind": "family_id",
        "id_kind_note": (
            "Family ids carry no site version on purpose: one calibration task is run "
            "under all six conditions, and src* loads the v1 task file while tgt* loads "
            "the v2 one. Pinning a uid such as 'skillshift.gitlab.v1.0' would lock only "
            "half of each family's grid."
        ),
        "sampling": {
            "rule": subset.SAMPLING_RULE_ID,
            "formula": subset.SAMPLING_FORMULA,
            "randomness": "none: the rule is deterministic and takes no seed",
            "n_tasks": {site: sites.get(site).n_tasks for site in subset.SAMPLE_COUNTS},
            "counts": dict(subset.SAMPLE_COUNTS),
            "counts_rationale": (
                "Roughly proportional to each site's share of the 355 tasks, rounded so "
                "that the smallest site still contributes a cell that can move at all."
            ),
            "indices": indices,
            "recompute": (
                "for site, (n, k) in {'gitlab': (162, 14), 'magento': (114, 10), "
                "'wordpress': (79, 6)}.items(): "
                "[f'skillshift.{site}.{j * n // k}' for j in range(k)]"
            ),
        },
        "conditions": list(CONDITIONS),
        "n_families": subset.CALIBRATION_SET_SIZE,
        "n_runs": subset.CALIBRATION_SET_SIZE * len(CONDITIONS),
        "family_ids": list(subset.sample_family_ids()),
        "uids": {
            version: [
                registry.load_registry().resolve(family_id, site_version=version).uid
                for family_id in subset.sample_family_ids()
            ]
            for version in ("v1", "v2")
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the file on disk differs from what the rule produces",
    )
    args = parser.parse_args(argv)

    text = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    path = paths.CALIBRATION_SET_PATH

    if args.check:
        if not path.is_file():
            print(f"{path} does not exist", file=sys.stderr)
            return 1
        if path.read_text(encoding="utf-8") != text:
            print(f"{path} is stale; rerun scripts/build_calibration_set.py", file=sys.stderr)
            return 1
        print(f"{path} is up to date")
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path} ({subset.CALIBRATION_SET_SIZE} families)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
