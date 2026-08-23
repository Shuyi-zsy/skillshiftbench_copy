"""The pinned calibration subset.

The subset is the anchor `skillshift calibrate` measures a local environment
against, so two properties are load-bearing and are asserted here rather than
promised in prose:

1. Every pinned id resolves in the registry, in **both** site versions.  The
   subset pins *family* ids precisely because one calibration task is run under
   all six conditions -- `src*` loads the v1 file and `tgt*` the v2 file.  A
   pinned uid would lock half the grid.
2. The shipped JSON is exactly what the documented sampling rule produces, so a
   third party can recompute the same thirty ids without trusting the file.
"""

from __future__ import annotations

import json

import pytest

from skillshift import paths, registry, sites
from skillshift.calibration import subset
from skillshift.conditions import CONDITIONS, SITE_VERSIONS
from skillshift.errors import CalibrationError


@pytest.fixture(scope="module")
def calibration_set():
    return subset.load_calibration_set()


@pytest.fixture(scope="module")
def reg():
    return registry.load_registry()


class TestSamplingRule:
    def test_the_rule_spreads_k_indices_over_n_tasks(self):
        assert subset.sample_indices(10, 5) == (0, 2, 4, 6, 8)

    def test_the_rule_always_starts_at_zero_and_stays_in_range(self):
        for n, k in ((162, 14), (114, 10), (79, 6)):
            indices = subset.sample_indices(n, k)
            assert indices[0] == 0
            assert len(set(indices)) == k
            assert max(indices) < n

    def test_asking_for_more_tasks_than_exist_is_an_error(self):
        with pytest.raises(CalibrationError):
            subset.sample_indices(5, 6)

    def test_a_non_positive_sample_size_is_an_error(self):
        with pytest.raises(CalibrationError):
            subset.sample_indices(10, 0)


class TestShippedFile:
    def test_it_exists_where_paths_says_it_does(self):
        assert paths.CALIBRATION_SET_PATH.is_file()

    def test_it_pins_thirty_family_ids(self, calibration_set):
        assert len(calibration_set.family_ids) == subset.CALIBRATION_SET_SIZE == 30

    def test_the_per_site_split_is_the_published_one(self, calibration_set):
        by_site = calibration_set.by_site()
        assert {site: len(ids) for site, ids in by_site.items()} == {
            "gitlab": 14,
            "magento": 10,
            "wordpress": 6,
        }

    def test_the_file_is_exactly_what_the_rule_recomputes(self, calibration_set):
        assert calibration_set.family_ids == subset.sample_family_ids()

    def test_the_file_records_the_rule_it_was_built_with(self, calibration_set):
        assert calibration_set.sampling_rule == subset.SAMPLING_RULE_ID

    def test_the_ids_are_family_ids_and_carry_no_version(self, calibration_set):
        for family_id in calibration_set.family_ids:
            assert ".v1." not in family_id
            assert ".v2." not in family_id

    def test_there_are_no_duplicates(self, calibration_set):
        assert len(set(calibration_set.family_ids)) == len(calibration_set.family_ids)

    def test_the_json_documents_the_formula_so_it_can_be_recomputed(self):
        payload = json.loads(paths.CALIBRATION_SET_PATH.read_text(encoding="utf-8"))
        assert payload["schema_version"]
        assert "floor" in payload["sampling"]["formula"]
        assert payload["sampling"]["rule"] == subset.SAMPLING_RULE_ID


class TestEveryPinnedIdResolves:
    def test_each_family_id_resolves_in_both_versions(self, calibration_set, reg):
        for family_id in calibration_set.family_ids:
            for version in SITE_VERSIONS:
                task = reg.resolve(family_id, site_version=version)
                assert task.family_id == family_id
                assert task.site_version == version

    def test_each_family_id_resolves_under_all_six_conditions(self, calibration_set, reg):
        for family_id in calibration_set.family_ids:
            resolved = {
                condition: reg.resolve(family_id, condition=condition)
                for condition in CONDITIONS
            }
            assert {task.site_version for task in resolved.values()} == set(SITE_VERSIONS)

    def test_the_pinned_ids_belong_to_the_site_they_are_filed_under(self, calibration_set, reg):
        for site, family_ids in calibration_set.by_site().items():
            for family_id in family_ids:
                assert reg.resolve(family_id, site_version="v1").site == site

    def test_the_indices_are_within_each_site_task_count(self, calibration_set, reg):
        for site, family_ids in calibration_set.by_site().items():
            limit = sites.get(site).n_tasks
            for family_id in family_ids:
                assert reg.resolve(family_id, site_version="v1").index < limit


class TestTaskSelection:
    def test_task_refs_for_a_source_condition_are_all_v1(self, calibration_set):
        refs = calibration_set.task_refs("src-exec")
        assert len(refs) == 30
        assert {ref.site_version for ref in refs} == {"v1"}

    def test_task_refs_for_a_target_condition_are_all_v2(self, calibration_set):
        refs = calibration_set.task_refs("tgt-perc")
        assert {ref.site_version for ref in refs} == {"v2"}

    def test_task_refs_can_be_narrowed_to_one_site(self, calibration_set):
        refs = calibration_set.task_refs("src", site="wordpress")
        assert len(refs) == 6
        assert {ref.site for ref in refs} == {"wordpress"}

    def test_family_ids_for_a_site_are_returned_in_index_order(self, calibration_set, reg):
        ids = calibration_set.by_site()["gitlab"]
        indices = [reg.resolve(fid, site_version="v1").index for fid in ids]
        assert indices == sorted(indices)


class TestLoadingErrors:
    def test_a_missing_file_names_the_path_and_the_command(self, tmp_path):
        with pytest.raises(CalibrationError) as excinfo:
            subset.load_calibration_set(tmp_path / "nope.json")
        assert "nope.json" in str(excinfo.value)

    def test_a_file_with_the_wrong_number_of_ids_is_rejected(self, tmp_path):
        path = tmp_path / "calibration_set.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "sampling": {"rule": subset.SAMPLING_RULE_ID, "formula": "floor(...)",
                                 "counts": {"gitlab": 14, "magento": 10, "wordpress": 6}},
                    "family_ids": ["skillshift.gitlab.0"],
                }
            )
        )
        with pytest.raises(CalibrationError) as excinfo:
            subset.load_calibration_set(path)
        assert "30" in str(excinfo.value)

    def test_an_unparseable_file_is_reported_as_such(self, tmp_path):
        path = tmp_path / "calibration_set.json"
        path.write_text("{not json")
        with pytest.raises(CalibrationError):
            subset.load_calibration_set(path)
