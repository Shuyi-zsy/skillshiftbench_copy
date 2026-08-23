"""Leaderboard ordering, naming, and the pull-request preview.

Two rules from the results policy are enforced here rather than left to the
renderer's good intentions:

* SR is the primary key and **SFR is never a sort key** (paper Section 2.4:
  at the measured skill-call rates its denominator is tiny).
* An SFR value resting on fewer than `metrics.SFR_MIN_SKILL_CALLS` invocations
  is marked, using that same constant and not a second copy of it.
"""

from __future__ import annotations

import copy
import json

import pytest

from skillshift import leaderboard
from skillshift.errors import ValidationError
from skillshift.eval import metrics
from tests import fixtures


def write(directory, name, payload, receipt=None):
    path = directory / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    if receipt is not None:
        leaderboard.receipt_path_for(path).write_text(json.dumps(receipt), encoding="utf-8")
    return path


def submission_with(name, sr_overall, *, skill_calls=None, sfr=10.0):
    payload = copy.deepcopy(fixtures.self_reported_submission())
    payload["submission"]["name"] = name
    payload["submission"]["method"]["name"] = name
    payload["metrics"]["SR"] = fixtures.breakdown(
        [sr_overall] * 3, [sr_overall] * 6, sr_overall
    )
    payload["metrics"]["SFR"] = fixtures.breakdown([sfr] * 3, [sfr] * 6, sfr)
    if skill_calls is not None:
        payload["n"]["skill_calls"] = {
            **dict.fromkeys(fixtures.WEBSITES, skill_calls),
            **dict.fromkeys(fixtures.CONDITIONS, skill_calls),
            "overall": skill_calls,
        }
    return payload


class TestFilenames:
    def test_a_conforming_name_parses(self):
        parsed = leaderboard.parse_filename("2026-09-01--mpcr-full--gpt-5-mini.json")
        assert parsed.date == "2026-09-01"
        assert parsed.method == "mpcr-full"
        assert parsed.model == "gpt-5-mini"

    @pytest.mark.parametrize(
        "name",
        [
            "mpcr--gpt-5-mini.json",
            "2026-09-01--mpcr.json",
            "2026-9-1--mpcr--gpt.json",
            "2026-09-01--MPCR--gpt.json",
            "2026-09-01--mpcr--gpt-5-mini.txt",
            "2026-09-01--a--b--c.json",
        ],
    )
    def test_a_non_conforming_name_is_rejected(self, name):
        with pytest.raises(ValidationError):
            leaderboard.parse_filename(name)

    def test_a_receipt_filename_is_derived_from_the_results_filename(self, tmp_path):
        path = tmp_path / "2026-09-01--mpcr--gpt-5-mini.json"
        assert leaderboard.receipt_path_for(path).name == "2026-09-01--mpcr--gpt-5-mini.receipt.json"

    def test_the_filename_date_must_match_the_submission_date(self, tmp_path):
        payload = fixtures.awm_submission()  # date 2026-09-01
        path = write(tmp_path, "2026-01-01--awm--mixed.json", payload)
        problems = leaderboard.check_filename(path, payload)
        assert any("date" in problem for problem in problems)

    def test_a_matching_date_has_no_complaint(self, tmp_path):
        payload = fixtures.awm_submission()
        path = write(tmp_path, "2026-09-01--awm--mixed.json", payload)
        assert leaderboard.check_filename(path, payload) == ()


class TestLoading:
    def test_a_directory_of_submissions_loads(self, tmp_path):
        write(tmp_path, "2026-09-01--awm--mixed.json", fixtures.awm_submission())
        write(tmp_path, "2026-09-02--walt--mixed.json", fixtures.awm_submission())
        assert len(leaderboard.load_entries(tmp_path)) == 2

    def test_receipt_files_are_not_mistaken_for_submissions(self, tmp_path):
        results = fixtures.self_reported_submission()
        write(tmp_path, "2026-09-15--mymethod--gpt-5-mini.json", results,
              receipt=fixtures.matching_receipt(results))
        entries = leaderboard.load_entries(tmp_path)
        assert len(entries) == 1
        assert entries[0].receipt is not None

    def test_an_entry_without_a_receipt_loads_with_none(self, tmp_path):
        path = write(tmp_path, "2026-09-01--awm--mixed.json", fixtures.awm_submission())
        assert leaderboard.load_entry(path).receipt is None

    def test_an_empty_directory_is_not_an_error(self, tmp_path):
        assert leaderboard.load_entries(tmp_path) == ()


class TestRanking:
    def test_entries_are_ordered_by_success_rate(self, tmp_path):
        write(tmp_path, "2026-09-01--low--gpt-5-mini.json", submission_with("Low", 10.0))
        write(tmp_path, "2026-09-01--high--gpt-5-mini.json", submission_with("High", 50.0))
        write(tmp_path, "2026-09-01--mid--gpt-5-mini.json", submission_with("Mid", 30.0))

        ranked = leaderboard.rank(leaderboard.load_entries(tmp_path))

        assert [entry.name for entry in ranked] == ["High", "Mid", "Low"]

    def test_an_entry_without_a_success_rate_sorts_last(self, tmp_path):
        payload = submission_with("NoSR", 10.0)
        payload["metrics"]["SR"] = copy.deepcopy(fixtures.NULL_BREAKDOWN)
        payload["reasons"]["SR"] = "not reported"
        write(tmp_path, "2026-09-01--nosr--gpt-5-mini.json", payload)
        write(tmp_path, "2026-09-01--low--gpt-5-mini.json", submission_with("Low", 1.0))

        ranked = leaderboard.rank(leaderboard.load_entries(tmp_path))

        assert [entry.name for entry in ranked] == ["Low", "NoSR"]

    def test_the_primary_metric_is_success_rate(self):
        assert leaderboard.PRIMARY_METRIC == "SR"

    def test_skill_failure_rate_is_not_sortable(self):
        assert "SFR" not in leaderboard.SORTABLE_METRICS

    def test_asking_to_sort_on_skill_failure_rate_is_refused(self, tmp_path):
        write(tmp_path, "2026-09-01--low--gpt-5-mini.json", submission_with("Low", 10.0))
        with pytest.raises(ValidationError) as excinfo:
            leaderboard.rank(leaderboard.load_entries(tmp_path), metric="SFR")
        assert "SFR" in str(excinfo.value)


class TestLowConfidenceMarking:
    def test_a_thin_skill_call_count_marks_the_cell(self, tmp_path):
        thin = metrics.SFR_MIN_SKILL_CALLS - 1
        path = write(tmp_path, "2026-09-01--thin--gpt-5-mini.json",
                     submission_with("Thin", 30.0, skill_calls=thin))
        entry = leaderboard.load_entry(path)

        assert "overall" in entry.low_confidence_slots()
        assert leaderboard.LOW_CONFIDENCE_MARK in entry.format("SFR")

    def test_a_thick_skill_call_count_does_not(self, tmp_path):
        thick = metrics.SFR_MIN_SKILL_CALLS * 10
        path = write(tmp_path, "2026-09-01--thick--gpt-5-mini.json",
                     submission_with("Thick", 30.0, skill_calls=thick))
        entry = leaderboard.load_entry(path)

        assert entry.low_confidence_slots() == ()
        assert leaderboard.LOW_CONFIDENCE_MARK not in entry.format("SFR")

    def test_the_threshold_is_the_metrics_module_constant(self, tmp_path):
        assert leaderboard.LOW_CONFIDENCE_THRESHOLD is metrics.SFR_MIN_SKILL_CALLS

    def test_the_mark_carries_the_call_count_in_the_rendered_table(self, tmp_path):
        thin = metrics.SFR_MIN_SKILL_CALLS - 1
        path = write(tmp_path, "2026-09-01--thin--gpt-5-mini.json",
                     submission_with("Thin", 30.0, skill_calls=thin))
        entry = leaderboard.load_entry(path)

        text = leaderboard.render_preview([entry], entry)

        assert str(thin) in text
        assert leaderboard.LOW_CONFIDENCE_MARK in text

    def test_an_entry_without_skill_call_counts_is_not_silently_confident(self, tmp_path):
        path = write(tmp_path, "2026-09-01--awm--mixed.json", fixtures.awm_submission())
        entry = leaderboard.load_entry(path)
        assert entry.low_confidence_slots() == ()  # SFR itself is null, nothing to mark


class TestPreview:
    def test_the_preview_states_the_new_entry_rank(self, tmp_path):
        write(tmp_path, "2026-09-01--low--gpt-5-mini.json", submission_with("Low", 10.0))
        new_path = write(tmp_path, "2026-09-01--high--gpt-5-mini.json", submission_with("High", 50.0))
        entries = leaderboard.load_entries(tmp_path)
        new_entry = leaderboard.load_entry(new_path)

        text = leaderboard.render_preview(entries, new_entry)

        assert "High" in text
        assert "1" in text
        assert "SR" in text

    def test_the_preview_shows_the_full_breakdown_of_the_new_entry(self, tmp_path):
        new_path = write(tmp_path, "2026-09-01--high--gpt-5-mini.json", submission_with("High", 50.0))
        entry = leaderboard.load_entry(new_path)

        text = leaderboard.render_preview([entry], entry)

        for key in ("gitlab", "magento", "wordpress", "src-exec", "tgt-perc"):
            assert key in text

    def test_the_preview_suggests_labels(self, tmp_path):
        path = write(tmp_path, "2026-09-01--awm--mixed.json", fixtures.awm_submission())
        entry = leaderboard.load_entry(path)

        text = leaderboard.render_preview([entry], entry)

        assert "reported-only" in text

    def test_the_preview_says_sfr_is_not_a_sort_key(self, tmp_path):
        path = write(tmp_path, "2026-09-01--awm--mixed.json", fixtures.awm_submission())
        entry = leaderboard.load_entry(path)
        assert "sort" in leaderboard.render_preview([entry], entry).lower()

    def test_validation_findings_are_included_when_given(self, tmp_path):
        from skillshift.eval.validate import validate_submission

        payload = fixtures.awm_submission()
        payload["n"]["websites"]["gitlab"] = 1
        path = write(tmp_path, "2026-09-01--awm--mixed.json", payload)
        entry = leaderboard.load_entry(path)
        report = validate_submission(payload)

        text = leaderboard.render_preview([entry], entry, report=report)

        assert "162" in text
        assert "FAIL" in text


class TestLeaderboardCommand:
    def test_a_good_submission_passes_and_prints_the_preview(self, tmp_path, capsys):
        path = write(tmp_path, "2026-09-01--awm--mixed.json", fixtures.awm_submission())
        from skillshift import cli

        code = cli.main(["leaderboard", "check", str(tmp_path), "--new", str(path)])
        out = capsys.readouterr().out

        assert code == 0
        assert "Ranking preview" in out
        assert "reported-only" in out

    def test_a_bad_submission_fails_with_exit_one(self, tmp_path, capsys):
        payload = fixtures.awm_submission()
        payload["n"]["websites"]["gitlab"] = 1
        path = write(tmp_path, "2026-09-01--awm--mixed.json", payload)
        from skillshift import cli

        code = cli.main(["leaderboard", "check", str(tmp_path), "--new", str(path)])

        assert code == 1
        assert "162" in capsys.readouterr().out

    def test_a_misnamed_file_fails_and_says_why(self, tmp_path, capsys):
        path = write(tmp_path, "awm.json", fixtures.awm_submission())
        from skillshift import cli

        code = cli.main(["leaderboard", "check", str(tmp_path), "--new", str(path)])
        out = capsys.readouterr().out

        assert code == 1
        assert "YYYY-MM-DD" in out

    def test_the_comment_can_be_written_to_a_file(self, tmp_path, capsys):
        path = write(tmp_path, "2026-09-01--awm--mixed.json", fixtures.awm_submission())
        comment = tmp_path / "comment.md"
        from skillshift import cli

        cli.main(
            ["leaderboard", "check", str(tmp_path), "--new", str(path), "--comment", str(comment)]
        )

        assert "Ranking preview" in comment.read_text(encoding="utf-8")

    def test_checking_every_entry_in_a_directory_needs_no_new_flag(self, tmp_path, capsys):
        write(tmp_path, "2026-09-01--awm--mixed.json", fixtures.awm_submission())
        write(tmp_path, "2026-09-02--walt--mixed.json", fixtures.awm_submission())
        from skillshift import cli

        code = cli.main(["leaderboard", "check", str(tmp_path)])
        out = capsys.readouterr().out

        assert code == 1  # the second file's date does not match its name
        assert "2026-09-02" in out
