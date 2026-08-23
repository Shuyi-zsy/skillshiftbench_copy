"""The five leaderboard checks, run identically here and in CI."""


import copy
from dataclasses import FrozenInstanceError

import pytest

from skillshift.eval import validate
from tests import fixtures


def run(results, receipt=None):
    return validate.validate_submission(
        results,
        receipt=receipt,
        official_digests=fixtures.OFFICIAL_DIGESTS,
        supported_harness_versions=("0.1.0", "n/a"),
    )


class TestHappyPath:
    def test_a_transcribed_paper_row_passes_without_a_receipt(self):
        report = run(fixtures.awm_submission())
        assert report.ok, report.errors

    def test_a_complete_self_reported_run_passes(self):
        results = fixtures.self_reported_submission()
        report = run(results, fixtures.matching_receipt(results))
        assert report.ok, report.errors


class TestSchemaCheck:
    def test_an_unknown_top_level_key_is_rejected(self):
        results = fixtures.awm_submission()
        results["extra"] = 1
        assert not run(results).ok

    def test_a_success_rate_above_100_is_rejected(self):
        results = fixtures.awm_submission()
        results["metrics"]["SR"]["overall"] = 135.0
        assert any(finding.check == "schema" for finding in run(results).errors)

    def test_a_non_positive_average_step_count_is_rejected(self):
        results = fixtures.awm_submission()
        results["metrics"]["AS"]["websites"]["gitlab"] = 0.0
        assert any(finding.check == "schema" for finding in run(results).errors)

    def test_a_negative_skill_call_count_is_rejected(self):
        results = fixtures.self_reported_submission()
        results["metrics"]["ASC"]["websites"]["gitlab"] = -0.1
        assert any(finding.check == "schema" for finding in run(results).errors)


class TestCoverageCheck:
    def test_a_null_without_a_reason_is_rejected(self):
        results = fixtures.self_reported_submission()
        results["metrics"]["SFR"]["websites"]["wordpress"] = None
        report = run(results, fixtures.matching_receipt(results))
        assert any(finding.check == "coverage" for finding in report.errors)

    def test_a_null_with_a_cell_level_reason_is_accepted(self):
        results = fixtures.self_reported_submission()
        results["metrics"]["SFR"]["websites"]["wordpress"] = None
        results["metrics"]["SFR"]["overall"] = None
        results["metrics"]["SFR"]["conditions"] = dict.fromkeys(
            results["metrics"]["SFR"]["conditions"], None
        )
        results["reasons"]["SFR"] = "No skill was invoked on WordPress in this run."
        receipt = fixtures.matching_receipt(results)
        report = run(results, receipt)
        assert not any(finding.check == "coverage" for finding in report.errors), report.errors

    def test_an_unused_reason_is_only_a_warning(self):
        results = fixtures.self_reported_submission()
        results["reasons"]["ASC"] = "leftover note"
        report = run(results, fixtures.matching_receipt(results))
        assert report.ok
        assert any(finding.check == "coverage" for finding in report.warnings)


class TestDenominatorAndMarginalCheck:
    def test_a_wrong_website_task_count_is_rejected(self):
        results = fixtures.awm_submission()
        results["n"]["websites"]["gitlab"] = 160
        report = run(results)
        assert any("162" in finding.message for finding in report.errors)

    def test_a_wrong_condition_task_count_is_rejected(self):
        results = fixtures.awm_submission()
        results["n"]["conditions"]["src"] = 300
        assert any("355" in finding.message for finding in run(results).errors)

    def test_a_single_mistyped_cell_breaks_the_marginal_identity(self):
        results = fixtures.awm_submission()
        results["metrics"]["SR"]["websites"]["magento"] = 35.49
        report = run(results)
        assert any(finding.check == "marginals" for finding in report.errors)

    def test_the_published_table_1_rows_satisfy_the_identity(self):
        # Guards against re-introducing a task-count-weighted overall, which
        # would reject the paper's own numbers.
        assert run(fixtures.awm_submission()).ok


class TestMetricSanityCheck:
    def test_sfr_over_few_skill_calls_is_flagged_low_confidence(self):
        results = fixtures.self_reported_submission()
        results["n"]["skill_calls"] = {
            **dict.fromkeys(fixtures.WEBSITES, 5),
            **dict.fromkeys(fixtures.CONDITIONS, 3),
            "overall": 15,
        }
        report = run(results, fixtures.matching_receipt(results))
        assert report.ok, report.errors
        assert any(finding.check == "metric-ranges" for finding in report.warnings)
        assert "SFR" in report.labels

    def test_a_self_reported_entry_without_skill_call_counts_is_rejected(self):
        # Without them the low-confidence flag cannot be decided, and SFR would
        # appear on the leaderboard as if it were stable.
        results = fixtures.self_reported_submission()
        results["n"]["skill_calls"] = None
        report = run(results, fixtures.matching_receipt(results))
        assert any(finding.check == "metric-ranges" for finding in report.errors)

    def test_all_null_sfr_needs_no_skill_call_counts(self):
        results = fixtures.self_reported_submission()
        results["metrics"]["SFR"] = copy.deepcopy(fixtures.NULL_BREAKDOWN)
        results["metrics"]["ASC"] = copy.deepcopy(fixtures.NULL_BREAKDOWN)
        results["n"]["skill_calls"] = None
        results["reasons"]["SFR"] = "No executable skill interface."
        results["reasons"]["ASC"] = "No executable skill interface."
        report = run(results, fixtures.matching_receipt(results))
        assert report.ok, report.errors


class TestReceiptCheck:
    def test_a_self_reported_entry_without_a_receipt_is_rejected(self):
        results = fixtures.self_reported_submission()
        report = run(results)
        assert any(finding.check == "receipt" for finding in report.errors)

    def test_a_reported_only_entry_must_not_carry_a_receipt(self):
        results = fixtures.awm_submission()
        report = run(results, fixtures.matching_receipt(results))
        assert any(finding.check == "receipt" for finding in report.errors)

    def test_a_receipt_aggregate_that_disagrees_with_results_is_rejected(self):
        results = fixtures.self_reported_submission()
        receipt = fixtures.matching_receipt(results)
        receipt["aggregate"]["metrics"]["SR"]["overall"] = 31.0
        report = run(results, receipt)
        assert any(finding.check == "receipt" for finding in report.errors)

    def test_an_unsupported_harness_version_is_rejected(self):
        results = fixtures.self_reported_submission()
        results["harness_version"] = "0.0.1-dev"
        receipt = fixtures.matching_receipt(results)
        report = run(results, receipt)
        assert any("harness" in finding.message.lower() for finding in report.errors)

    def test_an_unofficial_environment_digest_is_rejected(self):
        results = fixtures.self_reported_submission()
        receipt = fixtures.matching_receipt(results)
        receipt["env_digests"]["gitlab-v12"] = "sha256:" + "ff" * 32
        report = run(results, receipt)
        assert any(finding.check == "receipt" for finding in report.errors)

    def test_a_receipt_cell_count_that_disagrees_with_the_official_one_is_rejected(self):
        results = fixtures.self_reported_submission()
        receipt = fixtures.matching_receipt(results)
        receipt["n_per_cell"]["gitlab"]["src"] = 1
        report = run(results, receipt)
        assert any(finding.check == "receipt" for finding in report.errors)


class TestReport:
    def test_report_is_immutable_and_summarises(self):
        report = run(fixtures.awm_submission())
        with pytest.raises(FrozenInstanceError):
            report.findings = ()
        assert isinstance(report.summary(), str)
        assert "PASS" in report.summary()

    def test_a_failing_report_summary_says_fail(self):
        results = fixtures.awm_submission()
        results["n"]["websites"]["gitlab"] = 1
        assert "FAIL" in run(results).summary()
