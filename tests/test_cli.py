"""The `skillshift` command line."""

import json

import pytest

from skillshift import cli
from tests import fixtures


def run(argv, capsys):
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out + captured.err


class TestTopLevel:
    def test_no_arguments_prints_usage_and_fails(self, capsys):
        code, out = run([], capsys)
        assert code != 0
        assert "usage" in out.lower()

    def test_version_is_reported(self, capsys):
        from skillshift import __version__

        with pytest.raises(SystemExit):
            cli.main(["--version"])
        assert __version__


class TestValidate:
    def test_a_good_submission_passes(self, tmp_path, capsys):
        path = tmp_path / "results.json"
        path.write_text(json.dumps(fixtures.awm_submission()))

        code, out = run(["validate", str(path)], capsys)

        assert code == 0
        assert "PASS" in out

    def test_a_bad_submission_fails_and_lists_the_problems(self, tmp_path, capsys):
        results = fixtures.awm_submission()
        results["n"]["websites"]["gitlab"] = 1
        path = tmp_path / "results.json"
        path.write_text(json.dumps(results))

        code, out = run(["validate", str(path)], capsys)

        assert code == 1
        assert "162" in out

    def test_a_receipt_is_checked_when_given(self, tmp_path, capsys):
        results = fixtures.self_reported_submission()
        receipt = fixtures.matching_receipt(results)
        (tmp_path / "results.json").write_text(json.dumps(results))
        (tmp_path / "run_receipt.json").write_text(json.dumps(receipt))
        (tmp_path / "digests.json").write_text(json.dumps(fixtures.OFFICIAL_DIGESTS))

        code, out = run(
            [
                "validate",
                str(tmp_path / "results.json"),
                "--receipt",
                str(tmp_path / "run_receipt.json"),
                "--digests",
                str(tmp_path / "digests.json"),
            ],
            capsys,
        )

        assert code == 0, out

    def test_the_receipt_next_to_the_results_is_picked_up_automatically(self, tmp_path, capsys):
        results = fixtures.self_reported_submission()
        (tmp_path / "results.json").write_text(json.dumps(results))
        (tmp_path / "run_receipt.json").write_text(json.dumps(fixtures.matching_receipt(results)))

        code, out = run(["validate", str(tmp_path / "results.json")], capsys)

        assert "run_receipt.json" in out

    def test_a_missing_file_is_a_clear_error_not_a_traceback(self, tmp_path, capsys):
        code, out = run(["validate", str(tmp_path / "nope.json")], capsys)
        assert code == 2
        assert "nope.json" in out

    def test_malformed_json_is_a_clear_error(self, tmp_path, capsys):
        path = tmp_path / "results.json"
        path.write_text("{not json")
        code, out = run(["validate", str(path)], capsys)
        assert code == 2
        assert "json" in out.lower()


class TestReport:
    def test_reports_from_a_per_task_file(self, tmp_path, capsys):
        from skillshift.eval.records import write_jsonl
        from tests.test_report import full_records

        run_dir = tmp_path / "run"
        run_dir.mkdir()
        write_jsonl(full_records(), run_dir / "per_task.jsonl")

        code, out = run(
            [
                "report",
                str(run_dir),
                "--out",
                str(tmp_path / "out"),
                "--name",
                "MyMethod",
                "--model",
                "gpt-5-mini-2025-08-07",
            ],
            capsys,
        )

        assert code == 0, out
        assert (tmp_path / "out" / "results.json").is_file()
        assert (tmp_path / "out" / "run_receipt.json").is_file()

    def test_it_warns_about_the_private_file(self, tmp_path, capsys):
        from skillshift.eval.records import write_jsonl
        from tests.test_report import full_records

        run_dir = tmp_path / "run"
        run_dir.mkdir()
        write_jsonl(full_records(), run_dir / "per_task.jsonl")

        _, out = run(
            ["report", str(run_dir), "--out", str(tmp_path / "out"), "--name", "M", "--model", "m"],
            capsys,
        )

        assert "per_task.jsonl" in out
        assert "do not commit" in out.lower()

    def test_an_empty_run_directory_is_a_clear_error(self, tmp_path, capsys):
        code, out = run(
            ["report", str(tmp_path), "--out", str(tmp_path / "o"), "--name", "M", "--model", "m"],
            capsys,
        )
        assert code == 2
        assert "per_task.jsonl" in out


class TestCalibrate:
    def test_it_says_the_calibration_set_is_not_published_yet(self, capsys):
        code, out = run(["calibrate"], capsys)
        assert code == 2
        assert "calibration" in out.lower()


class TestEnv:
    def test_status_reports_every_site_and_version(self, capsys, monkeypatch):
        for name in ("GITLAB_V1", "GITLAB_V2", "SHOPPING_ADMIN_V1", "SHOPPING_ADMIN_V2",
                     "WORDPRESS_V1", "WORDPRESS_V2"):
            monkeypatch.delenv(name, raising=False)

        code, out = run(["env", "status", "--no-probe"], capsys)

        assert "gitlab" in out
        assert "wordpress" in out
        assert code != 0  # nothing configured

    def test_status_reads_the_configured_urls(self, capsys, monkeypatch):
        monkeypatch.setenv("GITLAB_V1", "http://localhost:8080")
        code, out = run(["env", "status", "--no-probe"], capsys)
        assert "http://localhost:8080" in out

    def test_up_points_at_the_environments_repository(self, capsys):
        code, out = run(["env", "up", "--site", "gitlab", "--condition", "src"], capsys)
        assert code == 2
        assert "skillshift-envs" in out
