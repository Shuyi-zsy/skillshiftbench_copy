"""The `skillshift` command line."""

import json
import subprocess
import urllib.request

import pytest

from skillshift import cli
from skillshift.errors import SkillShiftError
from tests import fixtures


def run(argv, capsys):
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out + captured.err


class _FakeResponse:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _fake_urlopen(status):
    def urlopen(url, timeout=None):
        return _FakeResponse(status)

    return urlopen



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

    def test_up_points_at_the_environments_repository_when_absent(self, capsys, monkeypatch):
        monkeypatch.setattr(cli, "_find_envs_repo", lambda: None)

        code, out = run(["env", "up", "--site", "gitlab", "--condition", "src"], capsys)

        assert code == 2
        assert "skillshift-envs" in out
        assert "--site gitlab --condition src" in out

    def test_up_drives_the_setup_script_when_present(self, capsys, monkeypatch, tmp_path):
        setup = tmp_path / "setup.sh"
        setup.write_text("#!/bin/sh\nexit 0\n")
        monkeypatch.setattr(cli, "_find_envs_repo", lambda: tmp_path)
        seen = {}

        def fake_run(command, check=False):
            seen["command"] = command
            return subprocess.CompletedProcess(command, 0)

        monkeypatch.setattr(subprocess, "run", fake_run)

        code, out = run(["env", "up", "--site", "wordpress", "--condition", "tgt-perc"], capsys)

        assert code == 0
        assert seen["command"] == [
            str(setup),
            "--site",
            "wordpress",
            "--condition",
            "tgt-perc",
        ]
        assert "setup.sh" in out

    def test_up_forwards_from_hf_and_dry_run(self, monkeypatch, capsys, tmp_path):
        (tmp_path / "setup.sh").write_text("#!/bin/sh\nexit 0\n")
        monkeypatch.setattr(cli, "_find_envs_repo", lambda: tmp_path)
        seen = {}

        def fake_run(command, check=False):
            seen["command"] = command
            return subprocess.CompletedProcess(command, 0)

        monkeypatch.setattr(subprocess, "run", fake_run)

        run(["env", "up", "--site", "gitlab", "--condition", "src", "--from-hf", "--dry-run"], capsys)

        assert "--from-hf" in seen["command"]
        assert "--dry-run" in seen["command"]

    def test_up_reports_the_setup_scripts_exit_code(self, monkeypatch, capsys, tmp_path):
        # A failed provisioning must not look like a success to a caller
        # scripting several environments in a row.
        (tmp_path / "setup.sh").write_text("#!/bin/sh\nexit 1\n")
        monkeypatch.setattr(cli, "_find_envs_repo", lambda: tmp_path)
        monkeypatch.setattr(
            subprocess, "run", lambda command, check=False: subprocess.CompletedProcess(command, 3)
        )

        code, _ = run(["env", "up", "--site", "magento", "--condition", "tgt"], capsys)

        assert code == 3


class TestEnvVersionProbe:
    """`env status` reports the version, using skillshift-envs' own criteria."""

    def test_a_reachable_site_reports_http_status_and_version(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen(200))
        monkeypatch.setattr(cli, "_probe_version", lambda environment: ", version OK")

        assert cli._probe("http://localhost:8080", "gitlab-v12") == "ready (HTTP 200), version OK"

    def test_an_unreachable_site_is_not_asked_for_its_version(self, monkeypatch):
        def refuse(*args, **kwargs):
            raise OSError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", refuse)
        monkeypatch.setattr(
            cli, "_probe_version", lambda environment: pytest.fail("must not be called")
        )

        assert cli._probe("http://localhost:8080", "gitlab-v12").startswith("UNREACHABLE")

    def test_without_an_environment_the_probe_stays_http_only(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen(302))
        monkeypatch.setattr(
            cli, "_probe_version", lambda environment: pytest.fail("must not be called")
        )

        assert cli._probe("http://localhost:8000") == "ready (HTTP 302)"

    def test_wrong_version_is_surfaced_and_counted_as_not_ready(self, capsys, monkeypatch):
        monkeypatch.setenv("GITLAB_V1", "http://localhost:8080")
        for name in ("GITLAB_V2", "SHOPPING_ADMIN_V1", "SHOPPING_ADMIN_V2",
                     "WORDPRESS_V1", "WORDPRESS_V2"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setattr(
            cli, "_probe", lambda url, environment=None, timeout=None: "ready (HTTP 200), WRONG VERSION"
        )

        code, out = run(["env", "status"], capsys)

        assert "WRONG VERSION" in out
        assert code == 1, "a wrong version must not count as a ready environment"

    def test_every_site_and_version_maps_to_an_environment(self):
        # These names are the keys of skillshift-envs/DIGESTS.json, which
        # receipt.schema.json freezes.
        assert cli._ENVIRONMENT_NAMES[("gitlab", "v1")] == "gitlab-v12"
        assert cli._ENVIRONMENT_NAMES[("gitlab", "v2")] == "gitlab-v16"
        assert cli._ENVIRONMENT_NAMES[("magento", "v1")] == "magento-v19"
        assert cli._ENVIRONMENT_NAMES[("magento", "v2")] == "magento-v24"
        assert cli._ENVIRONMENT_NAMES[("wordpress", "v1")] == "wordpress"
        assert cli._ENVIRONMENT_NAMES[("wordpress", "v2")] == "wordpress"

    def test_an_explicit_but_wrong_envs_home_is_an_error_not_a_fallback(self, monkeypatch, tmp_path):
        # Silently using a different checkout would provision the wrong thing
        # while appearing to obey.
        monkeypatch.setenv("SKILLSHIFT_ENVS_HOME", str(tmp_path / "absent"))
        with pytest.raises(SkillShiftError, match="SKILLSHIFT_ENVS_HOME"):
            cli._find_envs_repo()

    def test_an_explicit_envs_home_is_used_verbatim(self, monkeypatch, tmp_path):
        (tmp_path / "setup.sh").write_text("#!/bin/sh\n")
        monkeypatch.setenv("SKILLSHIFT_ENVS_HOME", str(tmp_path))
        assert cli._find_envs_repo() == tmp_path

    def test_without_an_envs_checkout_the_version_is_not_claimed(self, monkeypatch):
        monkeypatch.setattr(cli, "_find_envs_repo", lambda: None)
        assert cli._probe_version("gitlab-v12") == ", version not checked (no skillshift-envs checkout)"

    def test_healthcheck_exit_codes_are_translated(self, monkeypatch, tmp_path):
        healthcheck = tmp_path / "scripts" / "healthcheck.sh"
        healthcheck.parent.mkdir(parents=True)
        healthcheck.write_text("#!/bin/sh\nexit 0\n")
        monkeypatch.setattr(cli, "_find_envs_repo", lambda: tmp_path)

        for code, expected in [
            (0, ", version OK"),
            (2, ", WRONG VERSION"),
            (1, ", serving but the container is not ready"),
            (3, ", version not checked"),
        ]:
            monkeypatch.setattr(
                subprocess,
                "run",
                lambda command, capture_output=False, timeout=None, check=False, _code=code: (
                    subprocess.CompletedProcess(command, _code)
                ),
            )
            assert cli._probe_version("gitlab-v12") == expected


class TestEnvStatusProbeTimeout:
    """A three-second probe calls a healthy site unreachable.

    Measured on the build machine with all five environments up: the WordPress
    front page renders 516 posts in ~2.8s, so `env status` reported
    `UNREACHABLE (TimeoutError)` for a site that `healthcheck.sh` passed in the
    same second, with HTTP 200 and the right theme. Nothing was wrong except
    the timeout, and the message sends a first-time user hunting a fault that
    does not exist.
    """

    def test_the_default_is_not_tighter_than_a_warm_php_page(self):
        assert cli.PROBE_TIMEOUT_SECONDS >= 10, (
            "a loaded Magento or WordPress page takes several seconds; a probe "
            "shorter than that reports UNREACHABLE for a healthy site"
        )

    def test_the_timeout_is_overridable(self, capsys, monkeypatch):
        seen = {}

        def fake_probe(url, timeout):
            seen["timeout"] = timeout
            raise TimeoutError

        monkeypatch.setattr(cli, "_open_url", fake_probe)
        monkeypatch.setenv("WORDPRESS_V1", "http://localhost:8000")
        cli.main(["env", "status", "--timeout", "42"])
        capsys.readouterr()
        assert seen["timeout"] == 42

    def test_a_real_timeout_is_still_reported_as_unreachable(self, monkeypatch):
        def fake_probe(url, timeout):
            raise TimeoutError

        monkeypatch.setattr(cli, "_open_url", fake_probe)
        assert "UNREACHABLE" in cli._probe("http://localhost:1", None)
