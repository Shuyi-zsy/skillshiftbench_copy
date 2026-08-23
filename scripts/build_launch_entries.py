#!/usr/bin/env python3
"""Build the leaderboard's launch entries from the paper's transcribed tables.

The leaderboard opens with six entries, and none of them is retyped from the
PDF: every number comes from `tests/table1.py`, which the transcription tests
already hold to the paper's own marginal identities.  This script is the only
bridge between that module and the JSON the leaderboard repository stores.

    python scripts/build_launch_entries.py --out ../skillshift-bench.github.io/submissions

Entries
-------
`reported-only`  AWM, ASI, SkillWeaver, WALT -- paper Table 1, three backbones
                 pooled, code not released by us or by the original authors.
`verified-paper` MPCR and ASI -- paper Table 3, GPT-5 mini, one fixed library.

Neither kind ships a receipt: a receipt commits to a per-task result vector
produced by this harness, and these numbers predate it.  See docs/submit.md
Section "Three labels".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for entry in (str(REPO_ROOT), str(REPO_ROOT / "src")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from skillshift.conditions import CONDITIONS  # noqa: E402
from skillshift.eval.metrics import METRIC_NAMES  # noqa: E402
from skillshift.sites import SITE_NAMES, task_counts  # noqa: E402
from tests.table1 import TABLE1, TABLE3, TABLE3_MODEL  # noqa: E402

#: Date the leaderboard opened.  It is part of every launch filename, so it is
#: fixed here rather than taken from the clock: regenerating the entries must
#: not rename them.
LAUNCH_DATE = "2026-08-23"

#: The backbones Table 1 pools.  One display string, one filename slug.
TABLE1_MODEL_ID = "mixed (DeepSeek-V3.2 / GPT-5 mini / Claude Haiku 4.5)"
TABLE1_MODEL_SLUG = "mixed"

HARNESS_VERSION = "n/a"

METHODS = {
    "AWM": {
        "slug": "awm",
        "full_name": "Agent Workflow Memory",
        "description": "Induces reusable textual workflows from experience and prepends them to the prompt.",
        "paper_url": "https://proceedings.mlr.press/v267/wang25bx.html",
    },
    "ASI": {
        "slug": "asi",
        "full_name": "Agent Skill Induction",
        "description": "Induces executable programmatic skills and calls them as actions.",
        "paper_url": "https://openreview.net/forum?id=lsAY6fWsog",
    },
    "SkillWeaver": {
        "slug": "skillweaver",
        "full_name": "SkillWeaver",
        "description": "Self-improves by discovering and honing reusable web skills through exploration.",
        "paper_url": "https://arxiv.org/abs/2504.07079",
    },
    "WALT": {
        "slug": "walt",
        "full_name": "WALT: Web Agents that Learn Tools",
        "description": "Reverse-engineers website functionality into structured, callable tools.",
        "paper_url": "https://openreview.net/forum?id=cgIDqcJcoI",
    },
    "MPCR": {
        "slug": "mpcr",
        "full_name": "Masked Prior-Guided Candidate Reranking",
        "description": (
            "Executor-side test-time adaptation: proposes primitive and skill-action "
            "candidates, verifies them against current-page feasibility evidence, and "
            "reranks the shortlist. Introduces no new skills."
        ),
        # The SkillShift-Bench paper itself. Pointed at the project page rather
        # than a guessed arXiv id: the ACL Anthology identifier is not assigned
        # yet (see the TODO in CITATION.cff). Swap it in when it is.
        "paper_url": "https://skillshift-bench.github.io",
    },
}

AWM_ASC_REASON = (
    "Not applicable to AWM: it reuses prompted textual workflows rather than executable "
    "skill invocations, so there is nothing to count (paper Table 1, '--')."
)
AWM_SFR_REASON = (
    "Not applicable to AWM: no executable skill invocations, so the ratio has no "
    "denominator (paper Table 1, '--')."
)
TABLE3_WEBSITE_REASON = (
    "Paper Table 3 reports this comparison by condition only; it prints no per-website "
    "breakdown. The value is null rather than recomputed, because recomputing it would "
    "need the per-task results, which this project does not publish."
)
TABLE3_MISSING_METRIC_REASON = (
    "Paper Table 3 reports SR and ASC only. Reported as null rather than carried over "
    "from Table 1, whose numbers come from a different model pool."
)

NULL_BREAKDOWN = {
    "websites": dict.fromkeys(SITE_NAMES),
    "conditions": dict.fromkeys(CONDITIONS),
    "overall": None,
}


def _breakdown(websites, conditions, overall) -> dict:
    return {
        "websites": dict(zip(SITE_NAMES, websites, strict=True))
        if websites is not None
        else dict.fromkeys(SITE_NAMES),
        "conditions": dict(zip(CONDITIONS, conditions, strict=True)),
        "overall": overall,
    }


def _submission(method: str, *, model_id: str, label: str, source: str) -> dict:
    meta = METHODS[method]
    return {
        "name": method,
        "date": LAUNCH_DATE,
        "contact": None,
        "method": {
            "name": meta["full_name"],
            "description": meta["description"],
            "paper_url": meta["paper_url"],
            # Deliberately null: neither the original implementations nor our
            # integration of them is released. docs/baselines.md records the
            # upstream repositories and how each method was wired in.
            "code_url": None,
        },
        "model": {"id": model_id, "temperature": None, "vision": None},
        "provenance": {"label": label, "source": source, "code_released": False},
        "repro_command": None,
    }


def _denominators() -> dict:
    counts = task_counts()
    return {
        "websites": dict(counts),
        "conditions": dict.fromkeys(CONDITIONS, sum(counts.values())),
        "skill_calls": None,
    }


def _table1_entry(method: str) -> tuple[str, dict]:
    metrics: dict[str, dict] = {}
    reasons: dict[str, str] = {}
    for metric in METRIC_NAMES:
        row = TABLE1[metric].get(method)
        if row is None:
            metrics[metric] = json.loads(json.dumps(NULL_BREAKDOWN))
            reasons[metric] = AWM_ASC_REASON if metric == "ASC" else AWM_SFR_REASON
            continue
        websites, conditions, overall = row
        metrics[metric] = _breakdown(websites, conditions, overall)

    payload = {
        "schema_version": "1.0",
        "submission": _submission(
            method,
            model_id=TABLE1_MODEL_ID,
            label="reported-only",
            source="paper Table 1",
        ),
        "harness_version": HARNESS_VERSION,
        "metrics": metrics,
        "n": _denominators(),
        "reasons": reasons,
        "notes": (
            "Transcribed from Table 1 of the SkillShift-Bench paper, which pools "
            "DeepSeek-V3.2, GPT-5 mini and Claude Haiku 4.5. The website and condition "
            "values are macro-averages over the same eighteen cells, so they agree with "
            "the overall value by construction."
        ),
    }
    filename = f"{LAUNCH_DATE}--{METHODS[method]['slug']}--{TABLE1_MODEL_SLUG}.json"
    return filename, payload


def _table3_entry(method: str) -> tuple[str, dict]:
    metrics: dict[str, dict] = {}
    reasons: dict[str, str] = {}
    for metric in METRIC_NAMES:
        row = TABLE3.get(metric, {}).get(method)
        if row is None:
            metrics[metric] = json.loads(json.dumps(NULL_BREAKDOWN))
            reasons[metric] = TABLE3_MISSING_METRIC_REASON
            continue
        conditions, average = row
        metrics[metric] = _breakdown(None, conditions, average)
        reasons[metric] = TABLE3_WEBSITE_REASON

    payload = {
        "schema_version": "1.0",
        "submission": _submission(
            method,
            model_id=TABLE3_MODEL,
            label="verified-paper",
            source="paper Table 3",
        ),
        "harness_version": HARNESS_VERSION,
        "metrics": metrics,
        "n": _denominators(),
        "reasons": reasons,
        "notes": (
            "Transcribed from Table 3 of the SkillShift-Bench paper: GPT-5 mini over a "
            "single fixed skill library, pooled across all three websites. Table 3 prints "
            "no per-website breakdown and no AS or SFR row; those stay null."
        ),
    }
    filename = f"{LAUNCH_DATE}--{METHODS[method]['slug']}--{TABLE3_MODEL}.json"
    return filename, payload


def build_entries() -> tuple[tuple[str, dict], ...]:
    """Every launch entry, as (filename, payload) pairs."""
    return (
        *(_table1_entry(method) for method in ("AWM", "ASI", "SkillWeaver", "WALT")),
        *(_table3_entry(method) for method in ("MPCR", "ASI")),
    )


def write_entries(out_dir: Path | str) -> tuple[Path, ...]:
    """Write every entry into `out_dir`, one JSON file each."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, payload in build_entries():
        path = out_dir / filename
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(path)
    return tuple(written)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="the leaderboard's submissions/ directory")
    args = parser.parse_args(argv)

    for path in write_entries(args.out):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
