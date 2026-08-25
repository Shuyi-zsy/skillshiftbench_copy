"""The writer that turns 180 measured runs into the published anchor.

`skillshift calibrate` refuses to run while the anchor is pending, so it cannot
be the thing that produces the anchor.  `scripts/build_reference_anchor.py` is,
and the risk it carries is the one the whole anchor exists to avoid: writing a
number that was not measured.  These tests hold it to that -- a partial sweep,
a wrong denominator, or a degenerate tolerance must all refuse to produce a
file that says `published`, and the sigmas it does write must be the rule
`data/reference_results/README.md` states rather than something rounder.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import math

import pytest

from skillshift import paths
from skillshift.calibration import reference as reference_mod
from skillshift.calibration import subset
from skillshift.conditions import CONDITIONS
from skillshift.eval.records import TaskRecord, write_jsonl
from skillshift.sites import SITE_NAMES


def _load_builder():
    path = paths.REPO_ROOT / "scripts" / "build_reference_anchor.py"
    spec = importlib.util.spec_from_file_location("build_reference_anchor", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_builder()


def records_for(site, condition, *, n, successes=0, steps=None):
    """`n` records for one cell, with a controllable success count and steps."""
    steps = steps if steps is not None else [10] * n
    return [
        TaskRecord(
            uid=f"skillshift.{site}.v1.{i}",
            site=site,
            condition=condition,
            success=i < successes,
            steps=steps[i],
            skill_calls=0,
            skill_failures=0,
        )
        for i in range(n)
    ]


def full_sweep(*, successes=None, steps=None):
    """All eighteen cells at their proper denominators."""
    out = []
    for site in SITE_NAMES:
        n = subset.SAMPLE_COUNTS[site]
        for condition in CONDITIONS:
            out.extend(
                records_for(
                    site,
                    condition,
                    n=n,
                    successes=n // 3 if successes is None else successes,
                    steps=steps if steps is not None else [4 + (i % 5) for i in range(n)],
                )
            )
    return out


def write_run_dir(tmp_path, records):
    """Lay records out the way `skillshift run --out` does, one dir per cell."""
    root = tmp_path / "runs"
    by_cell = {}
    for record in records:
        by_cell.setdefault((record.site, record.condition), []).append(record)
    for (site, condition), cell in by_cell.items():
        write_jsonl(cell, root / f"{site}-{condition}" / "per_task.jsonl")
    return root


# ---------------------------------------------------------------------------
# reading the sweep back


def test_collects_records_from_every_per_task_file(tmp_path):
    root = write_run_dir(tmp_path, full_sweep())
    assert len(builder.collect_records([root])) == 180


def test_rejects_a_sweep_missing_a_cell(tmp_path):
    records = [r for r in full_sweep() if not (r.site == "magento" and r.condition == "tgt-exec")]
    root = write_run_dir(tmp_path, records)

    with pytest.raises(builder.IncompleteSweep) as exc:
        builder.build_anchor(builder.collect_records([root]), model="m", harness_version="0.1.0")
    assert "magento/tgt-exec" in str(exc.value)


def test_rejects_a_cell_with_the_wrong_denominator(tmp_path):
    records = full_sweep()
    records = [
        r for r in records if not (r.site == "wordpress" and r.condition == "src" and r.uid.endswith(".5"))
    ]
    root = write_run_dir(tmp_path, records)

    with pytest.raises(builder.IncompleteSweep) as exc:
        builder.build_anchor(builder.collect_records([root]), model="m", harness_version="0.1.0")
    assert "wordpress/src" in str(exc.value)
    assert "6" in str(exc.value)


def test_rejects_a_sweep_where_a_task_crashed(tmp_path):
    records = full_sweep()
    records[3] = dataclasses.replace(records[3], error="RuntimeError: boom")
    root = write_run_dir(tmp_path, records)

    with pytest.raises(builder.IncompleteSweep) as exc:
        builder.build_anchor(builder.collect_records([root]), model="m", harness_version="0.1.0")
    assert "error" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# the sigma rule


def test_sr_sigma_is_the_binomial_standard_error_in_percentage_points():
    records = records_for("wordpress", "src", n=6, successes=2)
    cell = builder.anchor_cell(records)

    p = 2 / 6
    assert cell["SR"]["value"] == pytest.approx(100 * p)
    assert cell["SR"]["sigma"] == pytest.approx(100 * math.sqrt(p * (1 - p) / 6))


def test_as_sigma_is_the_sample_standard_deviation_over_sqrt_n():
    steps = [3, 5, 7, 9, 4, 8]
    records = records_for("wordpress", "src", n=6, successes=1, steps=steps)
    cell = builder.anchor_cell(records)

    mean = sum(steps) / 6
    var = sum((s - mean) ** 2 for s in steps) / (6 - 1)
    assert cell["AS"]["value"] == pytest.approx(mean)
    assert cell["AS"]["sigma"] == pytest.approx(math.sqrt(var) / math.sqrt(6))


def test_asc_is_zero_with_no_sigma_for_a_no_skill_agent():
    cell = builder.anchor_cell(records_for("wordpress", "src", n=6, successes=1))
    assert cell["ASC"]["value"] == 0.0
    assert cell["ASC"]["sigma"] is None
    assert cell["n_skill_calls"] == 0


def test_sfr_is_never_anchored():
    cell = builder.anchor_cell(records_for("wordpress", "src", n=6, successes=1))
    assert cell["SFR"] == {"value": None, "sigma": None}


# ---------------------------------------------------------------------------
# degenerate tolerances must not be smoothed over


def test_a_cell_where_every_task_failed_has_no_sr_sigma():
    cell = builder.anchor_cell(records_for("wordpress", "src", n=6, successes=0))
    assert cell["SR"]["value"] == 0.0
    assert cell["SR"]["sigma"] is None


def test_a_cell_where_every_task_took_the_same_steps_has_no_as_sigma():
    cell = builder.anchor_cell(records_for("wordpress", "src", n=6, successes=0, steps=[10] * 6))
    assert cell["AS"]["value"] == 10.0
    assert cell["AS"]["sigma"] is None


def test_build_refuses_to_publish_when_a_gated_sigma_degenerates(tmp_path):
    records = full_sweep(successes=0, steps=None)
    # every wordpress src task fails in exactly ten steps: both gated sigmas vanish
    records = [
        r
        for r in records
        if not (r.site == "wordpress" and r.condition == "src")
    ] + records_for("wordpress", "src", n=6, successes=0, steps=[10] * 6)

    with pytest.raises(builder.DegenerateTolerance) as exc:
        builder.build_anchor(records, model="m", harness_version="0.1.0")
    assert "wordpress/src" in str(exc.value)


# ---------------------------------------------------------------------------
# the file it writes


@pytest.fixture()
def anchor():
    return builder.build_anchor(
        full_sweep(),
        model="gpt-5-mini-2025-08-07",
        harness_version="0.1.0",
        measured_at="2026-08-26",
        env_digests={"wordpress": "sha256:" + "a" * 64},
    )


def test_the_written_anchor_says_published(anchor):
    assert anchor["status"] == reference_mod.STATUS_PUBLISHED
    assert anchor["model"] == "gpt-5-mini-2025-08-07"
    assert anchor["measured_at"] == "2026-08-26"
    assert anchor["sigma_method"] is not None


def test_the_written_anchor_loads_and_is_published(anchor, tmp_path):
    path = tmp_path / "reference-react.json"
    path.write_text(json.dumps(anchor), encoding="utf-8")

    loaded = reference_mod.load_reference_results(path)
    assert loaded.is_published
    assert loaded.unpublished_cells() == ()


def test_the_written_anchor_keeps_all_eighteen_cells(anchor):
    assert set(anchor["cells"]) == set(SITE_NAMES)
    for site in SITE_NAMES:
        assert set(anchor["cells"][site]) == set(CONDITIONS)
        for condition in CONDITIONS:
            assert anchor["cells"][site][condition]["n"] == subset.SAMPLE_COUNTS[site]


def test_the_written_anchor_keeps_the_pending_notes_out(anchor):
    """`status_note` explains an emptiness that no longer applies."""
    assert "status_note" not in anchor


def test_the_written_anchor_records_the_step_budget(anchor):
    """AS is a step count; without the budget it was measured at it grades nothing."""
    assert anchor["max_steps"] == 10


def test_the_step_budget_is_settable():
    built = builder.build_anchor(
        full_sweep(), model="m", harness_version="0.1.0", max_steps=25
    )
    assert built["max_steps"] == 25
