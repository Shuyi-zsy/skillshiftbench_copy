"""`skillshift run`: argument validation and `--workers` wiring.

`_run_pairs` is the single execution path shared with `calibrate` (see
test_cli_calibrate.py for its own coverage); here we only check what is
specific to `run`: required arguments, and that `--workers`/`--agent` reach
`_run_pairs` as `workers=`/`agent_spec=`.
"""

from __future__ import annotations

import pytest

from skillshift import cli
from skillshift.eval.records import TaskRecord


def run(argv, capsys):
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def fake_records(plans, **kwargs):
    records = []
    for site, condition, task_ids in plans:
        for task_id in task_ids or ["skillshift.wordpress.0"]:
            records.append(
                TaskRecord(
                    uid=task_id,
                    site=site,
                    condition=condition,
                    success=True,
                    steps=1,
                    skill_calls=0,
                    skill_failures=0,
                )
            )
    return tuple(records)


class TestRunArguments:
    def test_neither_site_condition_nor_all_is_a_clear_error(self, capsys):
        code, out = run(["run", "--agent", "reference"], capsys)
        assert code == 2
        assert "--site" in out or "--all" in out

    def test_a_missing_agent_is_a_usage_error(self, capsys):
        # argparse itself enforces `--agent required=True` and exits before
        # cmd_run ever runs.
        with pytest.raises(SystemExit) as excinfo:
            cli.main(["run", "--site", "wordpress", "--condition", "src"])
        assert excinfo.value.code == 2


class TestRunWorkers:
    def test_the_default_is_serial(self, tmp_path, capsys, monkeypatch):
        seen = {}

        def spy(plans, **kwargs):
            seen.update(kwargs)
            return fake_records(plans, **kwargs)

        monkeypatch.setattr(cli, "_run_pairs", spy)
        code, _ = run(
            [
                "run", "--agent", "reference", "--site", "wordpress", "--condition", "src",
                "--tasks", "skillshift.wordpress.0", "--out", str(tmp_path / "runs"),
            ],
            capsys,
        )

        assert code == 0
        assert seen["workers"] == 1
        assert seen["agent_spec"] == "reference"

    def test_workers_and_agent_reach_run_pairs(self, tmp_path, capsys, monkeypatch):
        seen = {}

        def spy(plans, **kwargs):
            seen.update(kwargs)
            return fake_records(plans, **kwargs)

        monkeypatch.setattr(cli, "_run_pairs", spy)
        code, _ = run(
            [
                "run", "--agent", "reference", "--site", "wordpress", "--condition", "src",
                "--tasks", "skillshift.wordpress.0", "--workers", "4",
                "--out", str(tmp_path / "runs"),
            ],
            capsys,
        )

        assert code == 0
        assert seen["workers"] == 4
        assert seen["agent_spec"] == "reference"

    def test_zero_workers_is_rejected_before_anything_runs(self, tmp_path, capsys, monkeypatch):
        called = []
        monkeypatch.setattr(cli, "_run_pairs", lambda *a, **k: called.append(1) or ())

        code, out = run(
            [
                "run", "--agent", "reference", "--site", "wordpress", "--condition", "src",
                "--workers", "0", "--out", str(tmp_path / "runs"),
            ],
            capsys,
        )

        assert code == 2
        assert "workers" in out
        assert called == []

    def test_negative_workers_is_rejected(self, tmp_path, capsys, monkeypatch):
        called = []
        monkeypatch.setattr(cli, "_run_pairs", lambda *a, **k: called.append(1) or ())

        code, _ = run(
            [
                "run", "--agent", "reference", "--site", "wordpress", "--condition", "src",
                "--workers", "-1", "--out", str(tmp_path / "runs"),
            ],
            capsys,
        )

        assert code == 2
        assert called == []


class TestSaveTrajectories:
    def test_the_default_is_off(self, tmp_path, capsys, monkeypatch):
        seen = {}

        def spy(plans, **kwargs):
            seen.update(kwargs)
            return fake_records(plans, **kwargs)

        monkeypatch.setattr(cli, "_run_pairs", spy)
        code, _ = run(
            [
                "run", "--agent", "reference", "--site", "wordpress", "--condition", "src",
                "--tasks", "skillshift.wordpress.0", "--out", str(tmp_path / "runs"),
            ],
            capsys,
        )

        assert code == 0
        assert seen["trajectory_dir"] is None

    def test_the_flag_points_at_out_dir_slash_trajectories(self, tmp_path, capsys, monkeypatch):
        seen = {}

        def spy(plans, **kwargs):
            seen.update(kwargs)
            return fake_records(plans, **kwargs)

        monkeypatch.setattr(cli, "_run_pairs", spy)
        out_dir = tmp_path / "runs"
        code, _ = run(
            [
                "run", "--agent", "reference", "--site", "wordpress", "--condition", "src",
                "--tasks", "skillshift.wordpress.0", "--save-trajectories", "--out", str(out_dir),
            ],
            capsys,
        )

        assert code == 0
        assert seen["trajectory_dir"] == out_dir / "trajectories"
