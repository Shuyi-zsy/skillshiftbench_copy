"""Golden regression: the aggregation rule must reproduce the published Table 1.

Every leaderboard entry transcribed from the paper has to pass the same
consistency check as a freshly computed one.  If the check disagreed with the
paper, it would reject the paper's own numbers -- which is exactly what a
task-count-weighted overall does (see `test_task_weighted_overall_...`).
"""

import pytest

from skillshift.eval import metrics
from tests.table1 import rows


@pytest.mark.parametrize("metric,method,websites,conditions,overall", list(rows()))
def test_published_marginals_are_internally_consistent(metric, method, websites, conditions, overall):
    problems = metrics.check_marginals(websites=websites, conditions=conditions, overall=overall)
    assert problems == (), f"{metric}/{method}: {problems}"


@pytest.mark.parametrize("metric,method,websites,conditions,overall", list(rows()))
def test_macro_average_reproduces_the_printed_overall(metric, method, websites, conditions, overall):
    macro_sites = sum(websites.values()) / len(websites)
    macro_conditions = sum(conditions.values()) / len(conditions)

    assert macro_sites == pytest.approx(overall, abs=metrics.MARGINAL_TOLERANCE)
    assert macro_conditions == pytest.approx(overall, abs=metrics.MARGINAL_TOLERANCE)


def test_task_weighted_overall_would_contradict_the_paper():
    # Documents why the leaderboard check is macro and not micro: weighting the
    # website marginals by 162 / 114 / 79 moves SR/AWM by five points.
    websites = dict(zip(("gitlab", "magento", "wordpress"), [17.71, 25.49, 62.66], strict=True))
    n = {"gitlab": 162, "magento": 114, "wordpress": 79}

    weighted = sum(websites[s] * n[s] for s in websites) / sum(n.values())

    assert weighted == pytest.approx(30.21, abs=0.01)
    assert abs(weighted - 35.29) > 5.0


def test_check_marginals_catches_a_single_mistyped_cell():
    metric, method, websites, conditions, overall = next(iter(rows()))
    broken = dict(websites)
    broken["magento"] = broken["magento"] + 3.0

    problems = metrics.check_marginals(websites=broken, conditions=conditions, overall=overall)

    assert problems != ()


def test_check_marginals_tolerates_two_decimal_rounding():
    # The paper prints two decimals, so the identity holds only to ~0.005.
    websites = {"gitlab": 17.71, "magento": 25.49, "wordpress": 62.66}
    conditions = dict(
        zip(
            ("src", "src-perc", "src-exec", "tgt", "tgt-perc", "tgt-exec"),
            [50.07, 43.35, 22.45, 41.28, 37.65, 16.90],
            strict=True,
        )
    )
    assert metrics.check_marginals(websites=websites, conditions=conditions, overall=35.29) == ()


def test_check_marginals_skips_nulls_and_says_so():
    websites = {"gitlab": None, "magento": None, "wordpress": None}
    conditions = dict.fromkeys(
        ("src", "src-perc", "src-exec", "tgt", "tgt-perc", "tgt-exec"), None
    )
    assert metrics.check_marginals(websites=websites, conditions=conditions, overall=None) == ()
