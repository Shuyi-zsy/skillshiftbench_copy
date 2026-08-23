"""`skillshift report`: records in, three files out, one of which must not be
committed."""

import json

import pytest

from skillshift import report
from skillshift.errors import MetricError
from skillshift.eval import validate
from skillshift.eval.records import TaskRecord
from skillshift.sites import task_counts


def full_records(*, successes_per_cell=10, calls=1, failures=0):
    """One record per task, for every one of the eighteen cells."""
    counts = task_counts()
    records = []
    for site, n in counts.items():
        for condition in ("src", "src-perc", "src-exec", "tgt", "tgt-perc", "tgt-exec"):
            version = "v1" if condition.startswith("src") else "v2"
            for index in range(n):
                records.append(
                    TaskRecord(
                        uid=f"skillshift.{site}.{version}.{index}",
                        site=site,
                        condition=condition,
                        success=index < successes_per_cell,
                        steps=5,
                        skill_calls=calls,
                        skill_failures=failures,
                    )
                )
    return tuple(records)


SUBMISSION = {
    "name": "MyMethod",
    "date": "2026-09-15",
    "contact": "someone@example.org",
    "method": {"name": "MyMethod", "description": None, "paper_url": None, "code_url": None},
    "model": {"id": "gpt-5-mini-2025-08-07", "temperature": 0.0, "vision": True},
    "provenance": {"label": "self-reported", "source": "run 2026-09-15", "code_released": True},
    "repro_command": "skillshift run --agent mymethod --all",
}


class TestBuild:
    def test_produces_a_submission_that_passes_validation(self):
        results, receipt = report.build(
            full_records(),
            submission=SUBMISSION,
            env_digests={"gitlab-v12": "sha256:" + "11" * 32},
        )
        found = validate.validate_submission(
            results, receipt=receipt, official_digests={"gitlab-v12": "sha256:" + "11" * 32}
        )
        assert found.ok, found.errors

    def test_metrics_have_the_table_1_shape(self):
        results, _ = report.build(
            full_records(), submission=SUBMISSION, env_digests={"wordpress": None}
        )
        assert set(results["metrics"]) == {"SR", "AS", "ASC", "SFR"}
        assert set(results["metrics"]["SR"]["websites"]) == {"gitlab", "magento", "wordpress"}
        assert len(results["metrics"]["SR"]["conditions"]) == 6

    def test_the_receipt_commits_to_every_record(self):
        records = full_records()
        _, receipt = report.build(
            records, submission=SUBMISSION, env_digests={"wordpress": None}
        )
        assert receipt["per_task_commitment"]["n_records"] == len(records)

    def test_an_incomplete_sweep_is_rejected_rather_than_reported(self):
        records = tuple(record for record in full_records() if record.site != "wordpress")
        with pytest.raises(MetricError):
            report.build(records, submission=SUBMISSION, env_digests={"wordpress": None})

    def test_skill_call_totals_are_carried_so_sfr_can_be_flagged(self):
        results, _ = report.build(
            full_records(calls=1), submission=SUBMISSION, env_digests={"wordpress": None}
        )
        assert results["n"]["skill_calls"]["gitlab"] == 162 * 6

    def test_a_run_with_no_skill_calls_reports_sfr_as_null_with_a_reason(self):
        results, _ = report.build(
            full_records(calls=0), submission=SUBMISSION, env_digests={"wordpress": None}
        )
        assert results["metrics"]["SFR"]["overall"] is None
        assert results["metrics"]["ASC"]["overall"] == 0.0
        assert "SFR" in results["reasons"]


class TestWrite:
    def test_writes_three_files_and_names_the_private_one(self, tmp_path):
        records = full_records()
        results, receipt = report.build(
            records, submission=SUBMISSION, env_digests={"wordpress": None}
        )
        written = report.write(tmp_path, results=results, receipt=receipt, records=records)

        assert (tmp_path / "results.json").is_file()
        assert (tmp_path / "run_receipt.json").is_file()
        assert (tmp_path / "per_task.jsonl").is_file()
        assert written.private == tmp_path / "per_task.jsonl"
        assert "per_task.jsonl" in written.notice
        assert "not" in written.notice.lower()

    def test_the_written_results_are_valid_json(self, tmp_path):
        records = full_records()
        results, receipt = report.build(
            records, submission=SUBMISSION, env_digests={"wordpress": None}
        )
        report.write(tmp_path, results=results, receipt=receipt, records=records)

        assert json.loads((tmp_path / "results.json").read_text())["schema_version"] == "1.0"

    def test_records_round_trip_and_still_match_the_commitment(self, tmp_path):
        from skillshift.eval import receipt as receipt_mod
        from skillshift.eval.records import read_jsonl

        records = full_records()
        results, receipt = report.build(
            records, submission=SUBMISSION, env_digests={"wordpress": None}
        )
        report.write(tmp_path, results=results, receipt=receipt, records=records)

        reloaded = read_jsonl(tmp_path / "per_task.jsonl")
        receipt_mod.verify_commitment(reloaded, receipt["per_task_commitment"])
