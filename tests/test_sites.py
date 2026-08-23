"""Site constants are the denominators of every leaderboard cell, so they are
pinned here rather than derived from whatever files happen to be on disk."""

import pytest

from skillshift import sites
from skillshift.errors import UnknownSiteError


def test_three_sites_in_paper_table_order():
    assert sites.SITE_NAMES == ("gitlab", "magento", "wordpress")


def test_task_counts_match_the_paper():
    assert sites.get("gitlab").n_tasks == 162
    assert sites.get("magento").n_tasks == 114
    assert sites.get("wordpress").n_tasks == 79


def test_task_counts_sum_to_355():
    assert sum(site.n_tasks for site in sites.all_sites()) == 355


def test_wordpress_shares_one_task_file_across_versions():
    # WordPress has no v1/v2 task split: the contextual shift is a theme swap on
    # the same instance, so both versions load the same file.
    assert sites.get("wordpress").versioned_tasks is False
    assert sites.get("gitlab").versioned_tasks is True
    assert sites.get("magento").versioned_tasks is True


def test_harness_and_instance_keys_for_magento_differ_from_the_paper_name():
    magento = sites.get("magento")
    assert magento.harness_key == "admin"
    assert magento.instance_key == "shopping_admin"
    assert magento.env_prefix == "SHOPPING_ADMIN"


def test_lookup_accepts_the_harness_alias():
    assert sites.get("admin") is sites.get("magento")


def test_lookup_rejects_unknown_site():
    with pytest.raises(UnknownSiteError):
        sites.get("reddit")
