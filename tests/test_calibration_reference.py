"""The published reference anchor and the deviation check built on it.

The anchor is empty on purpose until the environment images are tagged: a
placeholder number here would be indistinguishable from a measured one, and
`calibrate` would start certifying environments against fiction.  These tests
pin both halves of that: the shipped file must parse and must *not* claim to be
published, and `compare` must refuse to grade against an unpublished anchor.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from skillshift import paths
from skillshift.calibration import deviation as compare_mod
from skillshift.calibration import reference as reference_mod
from skillshift.calibration import subset
from skillshift.conditions import CONDITIONS
from skillshift.errors import CalibrationError
from skillshift.eval.metrics import CellStats
from skillshift.sites import SITE_NAMES


def cell_payload(n, *, sr=None, avg_steps=None, sigma=None):
    return {
        "n": n,
        "n_skill_calls": 0,
        "SR": {"value": sr, "sigma": sigma},
        "AS": {"value": avg_steps, "sigma": sigma},
        "ASC": {"value": 0.0 if sr is not None else None, "sigma": None},
        "SFR": {"value": None, "sigma": None},
    }


def anchor_payload(*, status="published", sr=20.0, avg_steps=8.0, sigma=2.0):
    return {
        "schema_version": "1.0",
        "status": status,
        "agent": "reference",
        "model": "some-model" if status == "published" else None,
        "harness_version": "0.1.0" if status == "published" else None,
        "sigma_method": "within-cell-standard-error" if status == "published" else None,
        "threshold_sigma": 3.0,
        "gated_metrics": ["SR", "AS"],
        "calibration_set": {"rule": subset.SAMPLING_RULE_ID, "n_families": 30},
        "cells": {
            site: {
                condition: cell_payload(
                    subset.SAMPLE_COUNTS[site], sr=sr, avg_steps=avg_steps, sigma=sigma
                )
                for condition in CONDITIONS
            }
            for site in SITE_NAMES
        },
    }


def write_anchor(tmp_path, payload):
    path = tmp_path / "reference-react.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def observed(site, condition, *, sr, avg_steps):
    return CellStats(
        site=site,
        condition=condition,
        n=subset.SAMPLE_COUNTS[site],
        sr=sr,
        avg_steps=avg_steps,
        asc=0.0,
        sfr=None,
        n_skill_calls=0,
        sfr_low_confidence=True,
    )


class TestShippedAnchor:
    def test_the_file_ships_and_parses(self):
        path = paths.REFERENCE_RESULTS_DIR / reference_mod.REFERENCE_RESULTS_FILENAME
        assert path.is_file()
        assert reference_mod.load_reference_results(path) is not None

    def test_it_does_not_claim_to_be_published(self):
        anchor = reference_mod.load_reference_results()
        assert not anchor.is_published

    def test_every_value_is_still_null(self):
        anchor = reference_mod.load_reference_results()
        for cell in anchor.cells():
            for value in cell.metrics.values():
                assert value.value is None
                assert value.sigma is None

    def test_it_covers_the_full_grid_with_the_subset_denominators(self):
        anchor = reference_mod.load_reference_results()
        assert len(anchor.cells()) == len(SITE_NAMES) * len(CONDITIONS)
        for cell in anchor.cells():
            assert cell.n == subset.SAMPLE_COUNTS[cell.site]

    def test_the_directory_explains_itself(self):
        assert (paths.REFERENCE_RESULTS_DIR / "README.md").is_file()


class TestLoading:
    def test_a_missing_file_names_the_path(self, tmp_path):
        with pytest.raises(CalibrationError) as excinfo:
            reference_mod.load_reference_results(tmp_path / "absent.json")
        assert "absent.json" in str(excinfo.value)

    def test_a_missing_cell_is_rejected(self, tmp_path):
        payload = anchor_payload()
        del payload["cells"]["gitlab"]["src-exec"]
        with pytest.raises(CalibrationError) as excinfo:
            reference_mod.load_reference_results(write_anchor(tmp_path, payload))
        assert "src-exec" in str(excinfo.value)

    def test_a_wrong_denominator_is_rejected(self, tmp_path):
        payload = anchor_payload()
        payload["cells"]["gitlab"]["src"]["n"] = 162
        with pytest.raises(CalibrationError) as excinfo:
            reference_mod.load_reference_results(write_anchor(tmp_path, payload))
        assert "14" in str(excinfo.value)

    def test_a_published_anchor_reports_itself_as_published(self, tmp_path):
        anchor = reference_mod.load_reference_results(write_anchor(tmp_path, anchor_payload()))
        assert anchor.is_published

    def test_a_published_status_with_missing_numbers_is_not_published(self, tmp_path):
        payload = anchor_payload()
        payload["cells"]["magento"]["tgt"]["SR"] = {"value": None, "sigma": None}
        anchor = reference_mod.load_reference_results(write_anchor(tmp_path, payload))
        assert not anchor.is_published
        assert "magento/tgt" in " ".join(anchor.unpublished_cells())

    def test_a_zero_sigma_is_rejected_as_unusable(self, tmp_path):
        payload = anchor_payload(sigma=0.0)
        with pytest.raises(CalibrationError) as excinfo:
            reference_mod.load_reference_results(write_anchor(tmp_path, payload))
        assert "sigma" in str(excinfo.value).lower()


class TestCompare:
    def test_an_unpublished_anchor_cannot_grade_anything(self, tmp_path):
        anchor = reference_mod.load_reference_results(
            write_anchor(tmp_path, anchor_payload(status="pending", sr=None, avg_steps=None, sigma=None))
        )
        with pytest.raises(CalibrationError) as excinfo:
            compare_mod.compare([observed("gitlab", "src", sr=20.0, avg_steps=8.0)], anchor)
        assert "not been published" in str(excinfo.value)

    def test_matching_numbers_pass(self, tmp_path):
        anchor = reference_mod.load_reference_results(write_anchor(tmp_path, anchor_payload()))
        cells = [
            observed(site, condition, sr=20.0, avg_steps=8.0)
            for site in SITE_NAMES
            for condition in CONDITIONS
        ]
        report = compare_mod.compare(cells, anchor)
        assert report.ok
        assert report.offenders == ()
        assert "matches" in report.summary().lower() or "within" in report.summary().lower()

    def test_a_deviation_is_measured_in_sigmas(self, tmp_path):
        anchor = reference_mod.load_reference_results(write_anchor(tmp_path, anchor_payload()))
        report = compare_mod.compare([observed("gitlab", "tgt", sr=28.0, avg_steps=8.0)], anchor)
        deviation = next(d for d in report.deviations if d.metric == "SR")
        assert deviation.sigmas == pytest.approx(4.0)
        assert deviation.beyond

    def test_a_deviation_beyond_the_threshold_fails_and_names_the_image(self, tmp_path):
        anchor = reference_mod.load_reference_results(write_anchor(tmp_path, anchor_payload()))
        report = compare_mod.compare([observed("gitlab", "tgt", sr=40.0, avg_steps=8.0)], anchor)
        assert not report.ok
        text = "\n".join(report.lines())
        assert "gitlab-v16" in text
        assert "sigma" in text.lower()

    def test_a_deviation_within_the_threshold_passes(self, tmp_path):
        anchor = reference_mod.load_reference_results(write_anchor(tmp_path, anchor_payload()))
        report = compare_mod.compare([observed("gitlab", "src", sr=24.0, avg_steps=8.0)], anchor)
        assert report.ok

    def test_sfr_is_never_a_gate(self, tmp_path):
        assert "SFR" not in compare_mod.GATED_METRICS

    def test_ungated_metrics_are_reported_but_do_not_fail_the_run(self, tmp_path):
        payload = anchor_payload()
        for site in SITE_NAMES:
            for condition in CONDITIONS:
                payload["cells"][site][condition]["ASC"] = {"value": 0.0, "sigma": 0.5}
        anchor = reference_mod.load_reference_results(write_anchor(tmp_path, payload))

        cell = dataclasses.replace(observed("gitlab", "src", sr=20.0, avg_steps=8.0), asc=9.0)
        report = compare_mod.compare([cell], anchor)

        asc = next(d for d in report.deviations if d.metric == "ASC")
        assert not asc.gated
        assert report.ok

    def test_running_the_wrong_number_of_tasks_is_an_error(self, tmp_path):
        anchor = reference_mod.load_reference_results(write_anchor(tmp_path, anchor_payload()))
        wrong = CellStats(
            site="gitlab", condition="src", n=162, sr=20.0, avg_steps=8.0,
            asc=0.0, sfr=None, n_skill_calls=0, sfr_low_confidence=True,
        )
        with pytest.raises(CalibrationError) as excinfo:
            compare_mod.compare([wrong], anchor)
        assert "14" in str(excinfo.value)

    def test_a_cell_outside_the_grid_is_an_error(self, tmp_path):
        anchor = reference_mod.load_reference_results(write_anchor(tmp_path, anchor_payload()))
        stray = CellStats(
            site="gitlab", condition="src", n=14, sr=20.0, avg_steps=8.0,
            asc=0.0, sfr=None, n_skill_calls=0, sfr_low_confidence=True,
        )
        with pytest.raises(CalibrationError):
            compare_mod.compare([stray, stray], anchor)
