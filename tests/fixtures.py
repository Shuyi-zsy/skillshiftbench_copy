"""Submission fixtures shared by the validation tests."""

from __future__ import annotations

import copy

from tests.table1 import CONDITIONS, WEBSITES  # noqa: F401

NULL_BREAKDOWN = {
    "websites": dict.fromkeys(WEBSITES),
    "conditions": dict.fromkeys(CONDITIONS),
    "overall": None,
}


def breakdown(websites, conditions, overall):
    return {
        "websites": dict(zip(WEBSITES, websites, strict=True)),
        "conditions": dict(zip(CONDITIONS, conditions, strict=True)),
        "overall": overall,
    }


def awm_submission() -> dict:
    """The AWM row of Table 1, transcribed: a `reported-only` entry with no receipt."""
    return {
        "schema_version": "1.0",
        "submission": {
            "name": "AWM",
            "date": "2026-09-01",
            "contact": None,
            "method": {
                "name": "Agent Workflow Memory",
                "description": "Prompted textual workflows.",
                "paper_url": "https://arxiv.org/abs/2409.07429",
                "code_url": None,
            },
            "model": {"id": "mixed (DeepSeek-V3.2 / GPT-5 mini / Claude Haiku 4.5)"},
            "provenance": {
                "label": "reported-only",
                "source": "paper Table 1",
                "code_released": False,
            },
            "repro_command": None,
        },
        "harness_version": "n/a",
        "metrics": {
            "SR": breakdown(
                [17.71, 25.49, 62.66], [50.07, 43.35, 22.45, 41.28, 37.65, 16.90], 35.29
            ),
            "AS": breakdown([8.03, 8.22, 4.76], [6.04, 6.32, 8.31, 6.34, 6.59, 8.44], 7.01),
            "ASC": copy.deepcopy(NULL_BREAKDOWN),
            "SFR": copy.deepcopy(NULL_BREAKDOWN),
        },
        "n": {
            "websites": {"gitlab": 162, "magento": 114, "wordpress": 79},
            "conditions": dict.fromkeys(CONDITIONS, 355),
            "skill_calls": None,
        },
        "reasons": {
            "ASC": "Not applicable to AWM: it reuses prompted textual workflows rather than executable skill invocations (paper Table 1, '--').",
            "SFR": "Not applicable to AWM: no executable skill invocations, so the ratio has no denominator.",
        },
    }


def self_reported_submission() -> dict:
    """A well-formed external submission with every metric filled in."""
    return {
        "schema_version": "1.0",
        "submission": {
            "name": "MyMethod",
            "date": "2026-09-15",
            "contact": "someone@example.org",
            "method": {
                "name": "MyMethod",
                "description": "A learned-skill method.",
                "paper_url": None,
                "code_url": "https://github.com/example/mymethod",
            },
            "model": {"id": "gpt-5-mini-2025-08-07", "temperature": 0.0, "vision": True},
            "provenance": {"label": "self-reported", "source": "run 2026-09-15", "code_released": True},
            "repro_command": "skillshift run --agent mymethod --all",
        },
        "harness_version": "0.1.0",
        "metrics": {
            "SR": breakdown([30.0, 30.0, 30.0], [30.0] * 6, 30.0),
            "AS": breakdown([8.0, 8.0, 8.0], [8.0] * 6, 8.0),
            "ASC": breakdown([0.5, 0.5, 0.5], [0.5] * 6, 0.5),
            "SFR": breakdown([10.0, 10.0, 10.0], [10.0] * 6, 10.0),
        },
        "n": {
            "websites": {"gitlab": 162, "magento": 114, "wordpress": 79},
            "conditions": dict.fromkeys(CONDITIONS, 355),
            "skill_calls": {
                **dict.fromkeys(WEBSITES, 400),
                **dict.fromkeys(CONDITIONS, 200),
                "overall": 1200,
            },
        },
        "reasons": {},
    }


def matching_receipt(results: dict) -> dict:
    """A receipt whose embedded aggregate matches the given submission."""
    return {
        "schema_version": "1.0",
        "harness_version": results["harness_version"],
        "harness_commit": "a1b2c3d",
        "env_digests": {
            "gitlab-v12": "sha256:" + "11" * 32,
            "gitlab-v16": "sha256:" + "22" * 32,
            "magento-v19": "sha256:" + "33" * 32,
            "magento-v24": "sha256:" + "44" * 32,
            "wordpress": "sha256:" + "55" * 32,
        },
        "model": dict(results["submission"]["model"]),
        "n_per_cell": {
            "gitlab": dict.fromkeys(CONDITIONS, 162),
            "magento": dict.fromkeys(CONDITIONS, 114),
            "wordpress": dict.fromkeys(CONDITIONS, 79),
        },
        "aggregate": {
            "metrics": copy.deepcopy(results["metrics"]),
            "n": copy.deepcopy(results["n"]),
        },
        "per_task_commitment": {
            "algorithm": "sha256",
            "canonical_form": "skillshift/per-task-v1",
            "value": "0" * 64,
            "n_records": 2130,
        },
        "timestamp": "2026-09-15T12:00:00Z",
        "notes": None,
    }


OFFICIAL_DIGESTS = {
    "gitlab-v12": "sha256:" + "11" * 32,
    "gitlab-v16": "sha256:" + "22" * 32,
    "magento-v19": "sha256:" + "33" * 32,
    "magento-v24": "sha256:" + "44" * 32,
    "wordpress": "sha256:" + "55" * 32,
}
