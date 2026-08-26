"""`skillshift calibrate`: the environment self-check.

Exit codes are part of the command's contract, so every path asserts one:

    0  every gated value is within tolerance of the anchor
    1  at least one gated value deviates beyond the threshold
    2  the check could not be made (no subset, or the anchor is unpublished)
"""

from __future__ import annotations

import json

import pytest

from skillshift import cli
from skillshift.calibration import subset
from skillshift.conditions import CONDITIONS
from skillshift.errors import CalibrationError
from skillshift.eval.records import TaskRecord
from skillshift.sites import SITE_NAMES
from tests.test_calibration_reference import anchor_payload


def run(argv, capsys):
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def published_anchor(tmp_path, **kwargs):
    path = tmp_path / "anchor.json"
    path.write_text(json.dumps(anchor_payload(**kwargs)), encoding="utf-8")
    return path


def fake_records(sr_percent: float, avg_steps: float):
    """A `_run_pairs` stand-in producing records with a chosen SR and AS."""

    def _run_pairs(plans, **kwargs):
        records = []
        for site, condition, task_ids in plans:
            ids = list(task_ids)
            n_success = round(len(ids) * sr_percent / 100.0)
            for position, family_id in enumerate(ids):
                records.append(
                    TaskRecord(
                        uid=f"{family_id}.{condition}",
                        site=site,
                        condition=condition,
                        success=position < n_success,
                        steps=int(avg_steps),
                        skill_calls=0,
                        skill_failures=0,
                    )
                )
        return tuple(records)

    return _run_pairs


class TestUnpublishedAnchor:
    def test_the_shipped_anchor_is_still_pending_and_the_command_says_so(self, capsys):
        code, out = run(["calibrate"], capsys)
        assert code == 2
        assert "not been published" in out or "pending" in out.lower()

    def test_it_does_not_claim_the_environment_is_fine(self, capsys):
        _, out = run(["calibrate"], capsys)
        assert "matches the reference anchor" not in out

    def test_a_missing_calibration_subset_is_reported(self, capsys, monkeypatch):
        from skillshift.calibration import subset as subset_mod

        def explode(path=None):
            raise CalibrationError("Calibration subset not found: /nowhere/calibration_set.json")

        monkeypatch.setattr(subset_mod, "load_calibration_set", explode)
        code, out = run(["calibrate"], capsys)

        assert code == 2
        assert "calibration_set.json" in out


class TestDryRun:
    def test_it_lists_the_runs_without_touching_a_browser(self, capsys):
        code, out = run(["calibrate", "--dry-run"], capsys)
        assert code == 0
        assert "180" in out

    def test_one_site_narrows_the_plan(self, capsys):
        code, out = run(["calibrate", "--dry-run", "--site", "wordpress"], capsys)
        assert code == 0
        assert "36" in out  # 6 families x 6 conditions
        assert "gitlab" not in out


class TestAgainstAPublishedAnchor:
    def test_matching_numbers_pass_with_exit_zero(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(cli, "_run_pairs", fake_records(sr_percent=20.0, avg_steps=8.0))
        code, out = run(
            ["calibrate", "--reference", str(published_anchor(tmp_path)), "--out", str(tmp_path / "runs")],
            capsys,
        )
        assert code == 0
        assert "matches the reference anchor" in out

    def test_a_deviating_cell_fails_with_exit_one_and_names_the_image(
        self, tmp_path, capsys, monkeypatch
    ):
        monkeypatch.setattr(cli, "_run_pairs", fake_records(sr_percent=80.0, avg_steps=8.0))
        code, out = run(
            ["calibrate", "--reference", str(published_anchor(tmp_path)), "--out", str(tmp_path / "runs")],
            capsys,
        )
        assert code == 1
        assert "sigma" in out.lower()
        assert "gitlab-v16" in out or "gitlab-v12" in out

    def test_the_per_cell_deviation_table_is_printed(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(cli, "_run_pairs", fake_records(sr_percent=20.0, avg_steps=8.0))
        _, out = run(
            ["calibrate", "--reference", str(published_anchor(tmp_path)), "--out", str(tmp_path / "runs")],
            capsys,
        )
        assert "SR" in out and "AS" in out
        for site in SITE_NAMES:
            assert site in out

    def test_the_run_covers_thirty_families_under_six_conditions(
        self, tmp_path, capsys, monkeypatch
    ):
        seen = []

        def spy(plans, **kwargs):
            seen.extend(plans)
            return fake_records(20.0, 8.0)(plans, **kwargs)

        monkeypatch.setattr(cli, "_run_pairs", spy)
        run(
            ["calibrate", "--reference", str(published_anchor(tmp_path)), "--out", str(tmp_path / "runs")],
            capsys,
        )

        assert len(seen) == len(SITE_NAMES) * len(CONDITIONS)
        assert sum(len(task_ids) for _, _, task_ids in seen) == (
            subset.CALIBRATION_SET_SIZE * len(CONDITIONS)
        )

    def test_it_pins_family_ids_not_uids(self, tmp_path, capsys, monkeypatch):
        seen = []

        def spy(plans, **kwargs):
            seen.extend(plans)
            return fake_records(20.0, 8.0)(plans, **kwargs)

        monkeypatch.setattr(cli, "_run_pairs", spy)
        run(
            ["calibrate", "--reference", str(published_anchor(tmp_path)), "--out", str(tmp_path / "runs")],
            capsys,
        )

        for _, _, task_ids in seen:
            for task_id in task_ids:
                assert ".v1." not in task_id and ".v2." not in task_id

    def test_the_per_task_records_stay_local_and_are_flagged_as_such(
        self, tmp_path, capsys, monkeypatch
    ):
        monkeypatch.setattr(cli, "_run_pairs", fake_records(sr_percent=20.0, avg_steps=8.0))
        out_dir = tmp_path / "runs"
        _, out = run(
            ["calibrate", "--reference", str(published_anchor(tmp_path)), "--out", str(out_dir)],
            capsys,
        )
        assert (out_dir / "per_task.jsonl").is_file()
        assert "do not commit" in out.lower()

    @pytest.mark.parametrize("threshold,expected_code", [(0.5, 1), (100.0, 0)])
    def test_the_threshold_can_be_overridden(
        self, tmp_path, capsys, monkeypatch, threshold, expected_code
    ):
        monkeypatch.setattr(cli, "_run_pairs", fake_records(sr_percent=28.6, avg_steps=8.0))
        code, _ = run(
            [
                "calibrate",
                "--reference", str(published_anchor(tmp_path)),
                "--out", str(tmp_path / "runs"),
                "--threshold", str(threshold),
            ],
            capsys,
        )
        assert code == expected_code


class TestStepBudgetGuard:
    """A budget mismatch is exit 2 -- the check could not be made, not a finding."""

    def _anchor(self, tmp_path, max_steps):
        path = tmp_path / "anchor.json"
        path.write_text(json.dumps(anchor_payload(max_steps=max_steps)), encoding="utf-8")
        return path

    def test_a_differing_budget_refuses_to_grade(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(cli, "_run_pairs", fake_records(sr_percent=20.0, avg_steps=8.0))
        code, out = run(
            [
                "calibrate",
                "--reference", str(self._anchor(tmp_path, 10)),
                "--max-steps", "20",
                "--out", str(tmp_path / "runs"),
            ],
            capsys,
        )
        assert code == 2
        assert "10" in out and "20" in out

    def test_a_differing_budget_does_not_spend_a_single_run(self, tmp_path, capsys, monkeypatch):
        called = []
        monkeypatch.setattr(cli, "_run_pairs", lambda *a, **k: called.append(1) or ())
        run(
            [
                "calibrate",
                "--reference", str(self._anchor(tmp_path, 10)),
                "--max-steps", "20",
                "--out", str(tmp_path / "runs"),
            ],
            capsys,
        )
        assert called == []

    def test_a_matching_budget_grades_normally(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(cli, "_run_pairs", fake_records(sr_percent=20.0, avg_steps=8.0))
        code, _ = run(
            [
                "calibrate",
                "--reference", str(self._anchor(tmp_path, 10)),
                "--max-steps", "10",
                "--out", str(tmp_path / "runs"),
            ],
            capsys,
        )
        assert code == 0

    def test_an_anchor_without_a_budget_still_grades(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(cli, "_run_pairs", fake_records(sr_percent=20.0, avg_steps=8.0))
        code, _ = run(
            ["calibrate", "--reference", str(self._anchor(tmp_path, None)), "--out", str(tmp_path / "runs")],
            capsys,
        )
        assert code == 0


class TestWorkers:
    def test_the_default_is_serial(self, tmp_path, capsys, monkeypatch):
        seen = {}

        def spy(plans, **kwargs):
            seen.update(kwargs)
            return fake_records(sr_percent=20.0, avg_steps=8.0)(plans, **kwargs)

        monkeypatch.setattr(cli, "_run_pairs", spy)
        code, _ = run(
            ["calibrate", "--reference", str(published_anchor(tmp_path)), "--out", str(tmp_path / "runs")],
            capsys,
        )

        assert code == 0
        assert seen["workers"] == 1
        assert seen["agent_spec"] == "reference"

    def test_workers_and_agent_reach_run_pairs(self, tmp_path, capsys, monkeypatch):
        seen = {}

        def spy(plans, **kwargs):
            seen.update(kwargs)
            return fake_records(sr_percent=20.0, avg_steps=8.0)(plans, **kwargs)

        monkeypatch.setattr(cli, "_run_pairs", spy)
        code, _ = run(
            [
                "calibrate",
                "--reference", str(published_anchor(tmp_path)),
                "--workers", "5",
                "--out", str(tmp_path / "runs"),
            ],
            capsys,
        )

        assert code == 0
        assert seen["workers"] == 5
        assert seen["agent_spec"] == "reference"

    def test_zero_workers_is_rejected_before_anything_runs(self, tmp_path, capsys, monkeypatch):
        called = []
        monkeypatch.setattr(cli, "_run_pairs", lambda *a, **k: called.append(1) or ())

        code, out = run(
            [
                "calibrate",
                "--reference", str(published_anchor(tmp_path)),
                "--workers", "0",
                "--out", str(tmp_path / "runs"),
            ],
            capsys,
        )

        assert code == 2
        assert "workers" in out
        assert called == []


class TestSaveTrajectories:
    def test_the_default_is_off(self, tmp_path, capsys, monkeypatch):
        seen = {}

        def spy(plans, **kwargs):
            seen.update(kwargs)
            return fake_records(sr_percent=20.0, avg_steps=8.0)(plans, **kwargs)

        monkeypatch.setattr(cli, "_run_pairs", spy)
        run(
            ["calibrate", "--reference", str(published_anchor(tmp_path)), "--out", str(tmp_path / "runs")],
            capsys,
        )

        assert seen["trajectory_dir"] is None

    def test_the_flag_points_at_out_dir_slash_trajectories(self, tmp_path, capsys, monkeypatch):
        seen = {}

        def spy(plans, **kwargs):
            seen.update(kwargs)
            return fake_records(sr_percent=20.0, avg_steps=8.0)(plans, **kwargs)

        monkeypatch.setattr(cli, "_run_pairs", spy)
        out_dir = tmp_path / "runs"
        run(
            [
                "calibrate",
                "--reference", str(published_anchor(tmp_path)),
                "--save-trajectories",
                "--out", str(out_dir),
            ],
            capsys,
        )

        assert seen["trajectory_dir"] == out_dir / "trajectories"
