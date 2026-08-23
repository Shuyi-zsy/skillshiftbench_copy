"""The registry is the only place a task id becomes a concrete task."""


import warnings
from dataclasses import FrozenInstanceError

import pytest

from skillshift import registry
from skillshift.errors import UnknownTaskError


@pytest.fixture(scope="module")
def reg():
    return registry.load_registry()


def test_counts_match_the_paper_per_site_and_version(reg):
    assert len(reg.for_site_version("gitlab", "v1")) == 162
    assert len(reg.for_site_version("gitlab", "v2")) == 162
    assert len(reg.for_site_version("magento", "v1")) == 114
    assert len(reg.for_site_version("magento", "v2")) == 114
    assert len(reg.for_site_version("wordpress", "v1")) == 79
    assert len(reg.for_site_version("wordpress", "v2")) == 79


def test_each_version_bundle_totals_355(reg):
    for version in ("v1", "v2"):
        total = sum(len(reg.for_site_version(site, version)) for site in ("gitlab", "magento", "wordpress"))
        assert total == 355


def test_uid_format_encodes_site_version_and_index(reg):
    task = reg.get("skillshift.gitlab.v1.0")
    assert task.site == "gitlab"
    assert task.site_version == "v1"
    assert task.index == 0
    assert task.family_id == "skillshift.gitlab.0"
    assert task.legacy_id == "myBenchmark.0"


def test_family_id_links_the_aligned_source_and_target_variants(reg):
    src = reg.get("skillshift.gitlab.v1.9")
    tgt = reg.get("skillshift.gitlab.v2.9")
    assert src.family_id == tgt.family_id
    assert src.uid != tgt.uid


def test_resolve_accepts_a_family_id_together_with_a_condition(reg):
    task = reg.resolve("skillshift.gitlab.9", condition="tgt")
    assert task.uid == "skillshift.gitlab.v2.9"


def test_resolve_accepts_a_full_uid_consistent_with_the_condition(reg):
    task = reg.resolve("skillshift.gitlab.v2.9", condition="tgt-exec")
    assert task.uid == "skillshift.gitlab.v2.9"


def test_resolve_rejects_a_uid_that_contradicts_the_condition(reg):
    with pytest.raises(UnknownTaskError) as excinfo:
        reg.resolve("skillshift.gitlab.v1.9", condition="tgt")
    assert "v2" in str(excinfo.value)


def test_legacy_id_still_resolves_and_warns(reg):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        task = reg.resolve("myBenchmark.9", site="gitlab", condition="src")
    assert task.uid == "skillshift.gitlab.v1.9"
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


def test_legacy_id_without_a_site_is_an_explicit_error(reg):
    # `myBenchmark.N` was never globally unique: each site numbers its tasks
    # from 0, so the same string means three different tasks.
    with pytest.raises(UnknownTaskError) as excinfo:
        reg.resolve("myBenchmark.9", condition="src")
    assert "site" in str(excinfo.value).lower()


def test_legacy_id_out_of_range_for_its_site_is_rejected(reg):
    # WordPress has 79 tasks; the old flat `range(355)` registration made ids up
    # to 354 look valid for every site.
    with pytest.raises(UnknownTaskError):
        reg.resolve("myBenchmark.200", site="wordpress", condition="src")


def test_unknown_uid_raises(reg):
    with pytest.raises(UnknownTaskError):
        reg.get("skillshift.gitlab.v1.9999")


def test_task_refs_are_immutable(reg):
    task = reg.get("skillshift.gitlab.v1.0")
    with pytest.raises(FrozenInstanceError):
        task.index = 1


def test_id_map_csv_agrees_with_the_registry(reg):
    rows = registry.load_id_map()
    assert len(rows) == 710
    assert {row["uid"] for row in rows} == set(reg.uids())


def test_registry_is_cached(reg):
    assert registry.load_registry() is reg
