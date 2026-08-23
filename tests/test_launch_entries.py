"""The six launch entries, built from the paper's tables rather than retyped.

`scripts/build_launch_entries.py` is the only thing that turns
`tests/table1.py` into leaderboard JSON.  These tests hold it to three
promises: every entry passes the checks the leaderboard CI runs, every number
equals the transcription it came from, and no entry carries a receipt it could
not honestly produce.
"""

from __future__ import annotations

import importlib.util
import json

import pytest

from skillshift import leaderboard, paths
from skillshift.eval.validate import validate_submission
from tests.table1 import TABLE1, TABLE3, TABLE3_MODEL


def _load_builder():
    path = paths.REPO_ROOT / "scripts" / "build_launch_entries.py"
    spec = importlib.util.spec_from_file_location("build_launch_entries", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_builder()


@pytest.fixture(scope="module")
def entries():
    return builder.build_entries()


def entry_named(entries, filename):
    return next(payload for name, payload in entries if name == filename)


class TestTheSetOfEntries:
    def test_there_are_six(self, entries):
        assert len(entries) == 6

    def test_four_are_reported_only_and_two_are_verified_paper(self, entries):
        labels = [payload["submission"]["provenance"]["label"] for _, payload in entries]
        assert labels.count("reported-only") == 4
        assert labels.count("verified-paper") == 2

    def test_the_four_table_one_methods_are_all_present(self, entries):
        names = {payload["submission"]["name"] for _, payload in entries}
        assert {"AWM", "ASI", "SkillWeaver", "WALT"} <= names

    def test_mpcr_is_present_as_a_verified_paper_entry(self, entries):
        mpcr = [p for _, p in entries if p["submission"]["name"] == "MPCR"]
        assert len(mpcr) == 1
        assert mpcr[0]["submission"]["provenance"]["label"] == "verified-paper"

    def test_no_entry_ships_a_receipt(self, entries):
        assert all(not name.endswith(".receipt.json") for name, _ in entries)


class TestFilenames:
    def test_every_filename_conforms_to_the_convention(self, entries):
        for name, _ in entries:
            leaderboard.parse_filename(name)

    def test_every_filename_date_matches_its_submission_date(self, tmp_path, entries):
        for name, payload in entries:
            path = tmp_path / name
            path.write_text(json.dumps(payload), encoding="utf-8")
            assert leaderboard.check_filename(path, payload) == ()

    def test_the_two_asi_entries_do_not_collide(self, entries):
        asi = [name for name, p in entries if p["submission"]["name"] == "ASI"]
        assert len(asi) == 2
        assert len(set(asi)) == 2


class TestEveryEntryValidates:
    def test_each_entry_passes_the_leaderboard_checks(self, entries):
        for name, payload in entries:
            report = validate_submission(payload)
            assert report.ok, f"{name}: {[str(f) for f in report.errors]}"


class TestNumbersComeFromTheTranscription:
    @pytest.mark.parametrize("method", sorted(TABLE1["SR"]))
    def test_table1_success_rates_are_copied_verbatim(self, entries, method):
        websites, conditions, overall = TABLE1["SR"][method]
        payload = next(
            p
            for _, p in entries
            if p["submission"]["name"] == method
            and p["submission"]["provenance"]["source"] == "paper Table 1"
        )
        block = payload["metrics"]["SR"]
        assert list(block["websites"].values()) == websites
        assert list(block["conditions"].values()) == conditions
        assert block["overall"] == overall

    def test_awm_has_no_skill_metrics_and_says_why(self, entries):
        payload = next(p for _, p in entries if p["submission"]["name"] == "AWM")
        for metric in ("ASC", "SFR"):
            assert payload["metrics"][metric]["overall"] is None
            assert metric in payload["reasons"]

    @pytest.mark.parametrize("method", sorted(TABLE3["SR"]))
    def test_table3_numbers_are_copied_verbatim(self, entries, method):
        conditions, average = TABLE3["SR"][method]
        payload = next(
            p
            for _, p in entries
            if p["submission"]["name"] == method
            and p["submission"]["provenance"]["source"] == "paper Table 3"
        )
        assert list(payload["metrics"]["SR"]["conditions"].values()) == conditions
        assert payload["metrics"]["SR"]["overall"] == average
        assert payload["submission"]["model"]["id"] == TABLE3_MODEL

    def test_table3_entries_declare_the_missing_website_breakdown(self, entries):
        payload = next(
            p for _, p in entries if p["submission"]["provenance"]["source"] == "paper Table 3"
        )
        assert all(value is None for value in payload["metrics"]["SR"]["websites"].values())
        assert "SR" in payload["reasons"]
        for metric in ("AS", "SFR"):
            assert payload["metrics"][metric]["overall"] is None
            assert metric in payload["reasons"]

    def test_every_entry_carries_the_official_denominators(self, entries):
        for name, payload in entries:
            assert payload["n"]["websites"] == {"gitlab": 162, "magento": 114, "wordpress": 79}
            assert set(payload["n"]["conditions"].values()) == {355}, name


class TestProvenance:
    def test_no_baseline_claims_released_code(self, entries):
        for _, payload in entries:
            if payload["submission"]["provenance"]["label"] == "reported-only":
                assert payload["submission"]["method"]["code_url"] is None
                assert payload["submission"]["provenance"]["code_released"] is False

    def test_every_entry_links_the_paper_it_came_from(self, entries):
        for _, payload in entries:
            assert payload["submission"]["method"]["paper_url"]

    def test_the_harness_version_is_not_a_released_version(self, entries):
        for _, payload in entries:
            assert payload["harness_version"] == "n/a"


class TestWriting:
    def test_it_writes_one_file_per_entry(self, tmp_path, entries):
        builder.write_entries(tmp_path)
        written = sorted(p.name for p in tmp_path.glob("*.json"))
        assert written == sorted(name for name, _ in entries)

    def test_the_written_files_load_and_rank(self, tmp_path):
        builder.write_entries(tmp_path)
        loaded = leaderboard.load_entries(tmp_path)
        ranked = leaderboard.rank(loaded)
        assert len(ranked) == 6
        assert ranked[0].overall("SR") >= ranked[-1].overall("SR")
