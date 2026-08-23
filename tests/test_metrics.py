"""SR / AS / ASC / SFR: the single authoritative implementation.

The definitions come from the paper, Section 2.4 (`benchmark.tex`).  The
aggregation rule is pinned by a golden regression against the published Table 1
in `test_table1_transcription.py`.
"""


from dataclasses import FrozenInstanceError

import pytest

from skillshift.errors import MetricError
from skillshift.eval import metrics
from skillshift.eval.records import TaskRecord


def records_for(site, condition, *, n, successes, steps, calls=0, failures=0):
    """Build `n` records with a given number of successes and constant steps."""
    return tuple(
        TaskRecord(
            uid=f"skillshift.{site}.v1.{i}",
            site=site,
            condition=condition,
            success=i < successes,
            steps=steps,
            skill_calls=calls,
            skill_failures=failures,
        )
        for i in range(n)
    )


class TestCell:
    def test_sr_is_a_percentage_of_tasks_that_met_the_success_criterion(self):
        cell = metrics.compute_cell(
            records_for("magento", "src", n=114, successes=57, steps=5)
        )
        assert cell.n == 114
        assert cell.sr == pytest.approx(50.0)

    def test_avg_steps_averages_over_every_task_not_only_successes(self):
        # AS is "the mean number of actions before success, failure, or timeout".
        records = (
            TaskRecord("skillshift.gitlab.v1.0", "gitlab", "src", True, 4, 0, 0),
            TaskRecord("skillshift.gitlab.v1.1", "gitlab", "src", False, 10, 0, 0),
        )
        assert metrics.compute_cell(records).avg_steps == pytest.approx(7.0)

    def test_asc_is_skill_calls_per_task(self):
        records = (
            TaskRecord("skillshift.gitlab.v1.0", "gitlab", "src", True, 4, 3, 0),
            TaskRecord("skillshift.gitlab.v1.1", "gitlab", "src", False, 4, 0, 0),
        )
        assert metrics.compute_cell(records).asc == pytest.approx(1.5)

    def test_sfr_is_the_share_of_invoked_skills_that_failed(self):
        records = (
            TaskRecord("skillshift.gitlab.v1.0", "gitlab", "src", True, 4, 4, 1),
            TaskRecord("skillshift.gitlab.v1.1", "gitlab", "src", False, 4, 4, 3),
        )
        cell = metrics.compute_cell(records)
        assert cell.n_skill_calls == 8
        assert cell.sfr == pytest.approx(50.0)

    def test_sfr_is_none_not_zero_when_no_skill_was_ever_invoked(self):
        # A ratio over an empty denominator is undefined.  Reporting 0.0 would
        # read as "no skill ever failed", which is a different claim.
        cell = metrics.compute_cell(records_for("wordpress", "src", n=79, successes=10, steps=3))
        assert cell.n_skill_calls == 0
        assert cell.sfr is None

    def test_sfr_is_flagged_low_confidence_under_the_call_threshold(self):
        records = (
            TaskRecord("skillshift.gitlab.v1.0", "gitlab", "src", True, 4, 2, 1),
        )
        cell = metrics.compute_cell(records)
        assert cell.sfr == pytest.approx(50.0)
        assert cell.sfr_low_confidence is True

    def test_sfr_is_not_flagged_above_the_threshold(self):
        records = records_for("gitlab", "src", n=100, successes=50, steps=4, calls=1, failures=0)
        cell = metrics.compute_cell(records)
        assert cell.n_skill_calls == 100
        assert cell.sfr_low_confidence is False

    def test_empty_records_are_rejected(self):
        with pytest.raises(MetricError):
            metrics.compute_cell(())

    def test_mixed_sites_in_one_cell_are_rejected(self):
        records = (
            TaskRecord("skillshift.gitlab.v1.0", "gitlab", "src", True, 4, 0, 0),
            TaskRecord("skillshift.magento.v1.0", "magento", "src", True, 4, 0, 0),
        )
        with pytest.raises(MetricError):
            metrics.compute_cell(records)

    def test_duplicate_task_ids_in_one_cell_are_rejected(self):
        records = (
            TaskRecord("skillshift.gitlab.v1.0", "gitlab", "src", True, 4, 0, 0),
            TaskRecord("skillshift.gitlab.v1.0", "gitlab", "src", False, 6, 0, 0),
        )
        with pytest.raises(MetricError):
            metrics.compute_cell(records)

    def test_more_failures_than_calls_is_rejected(self):
        records = (TaskRecord("skillshift.gitlab.v1.0", "gitlab", "src", True, 4, 1, 2),)
        with pytest.raises(MetricError):
            metrics.compute_cell(records)

    def test_cell_is_immutable(self):
        cell = metrics.compute_cell(records_for("gitlab", "src", n=2, successes=1, steps=4))
        with pytest.raises(FrozenInstanceError):
            cell.sr = 0.0


class TestMacroAggregation:
    """The paper's O/A is an unweighted mean of the 18 cells.

    Both marginals are macro-averages of the same 18 cells, so
    `mean(3 websites) == mean(6 conditions) == O/A` is an identity.  This is
    what makes the leaderboard's cross-check meaningful.
    """

    def build_cells(self, value_of):
        return tuple(
            metrics.CellStats(
                site=site,
                condition=condition,
                n={"gitlab": 162, "magento": 114, "wordpress": 79}[site],
                sr=value_of(site, condition),
                avg_steps=1.0,
                asc=0.0,
                sfr=None,
                n_skill_calls=0,
                sfr_low_confidence=True,
            )
            for site in ("gitlab", "magento", "wordpress")
            for condition in ("src", "src-perc", "src-exec", "tgt", "tgt-perc", "tgt-exec")
        )

    def test_overall_equals_both_marginal_means(self):
        cells = self.build_cells(lambda site, cond: 10.0 + len(site) + len(cond))
        agg = metrics.aggregate(cells)

        by_site = agg.metric("SR").websites
        by_condition = agg.metric("SR").conditions
        overall = agg.metric("SR").overall

        assert sum(by_site.values()) / 3 == pytest.approx(overall)
        assert sum(by_condition.values()) / 6 == pytest.approx(overall)

    def test_sites_are_not_weighted_by_task_count(self):
        # GitLab has 162 tasks and WordPress 79; a task-weighted overall would
        # differ.  The paper's does not.
        cells = self.build_cells(lambda site, cond: {"gitlab": 0.0, "magento": 0.0, "wordpress": 90.0}[site])
        agg = metrics.aggregate(cells)
        assert agg.metric("SR").overall == pytest.approx(30.0)

        weighted = 90.0 * 79 / 355
        assert agg.metric("SR").overall != pytest.approx(weighted)

    def test_site_marginal_averages_its_six_conditions(self):
        cells = self.build_cells(
            lambda site, cond: 60.0 if (site == "gitlab" and cond == "src") else 0.0
        )
        agg = metrics.aggregate(cells)
        assert agg.metric("SR").websites["gitlab"] == pytest.approx(10.0)
        assert agg.metric("SR").conditions["src"] == pytest.approx(20.0)

    def test_n_is_reported_per_site_and_per_condition(self):
        agg = metrics.aggregate(self.build_cells(lambda s, c: 1.0))
        assert agg.n_websites == {"gitlab": 162, "magento": 114, "wordpress": 79}
        assert agg.n_conditions == {c: 355 for c in metrics.CONDITIONS}

    def test_incomplete_cell_grid_is_rejected(self):
        cells = self.build_cells(lambda s, c: 1.0)[:-1]
        with pytest.raises(MetricError):
            metrics.aggregate(cells)

    def test_duplicate_cells_are_rejected(self):
        cells = self.build_cells(lambda s, c: 1.0)
        with pytest.raises(MetricError):
            metrics.aggregate(cells + cells[:1])


class TestSfrMarginals:
    def build_cells(self, sfr_of, calls_of):
        return tuple(
            metrics.CellStats(
                site=site,
                condition=condition,
                n={"gitlab": 162, "magento": 114, "wordpress": 79}[site],
                sr=1.0,
                avg_steps=1.0,
                asc=0.0,
                sfr=sfr_of(site, condition),
                n_skill_calls=calls_of(site, condition),
                sfr_low_confidence=calls_of(site, condition) < metrics.SFR_MIN_SKILL_CALLS,
            )
            for site in ("gitlab", "magento", "wordpress")
            for condition in metrics.CONDITIONS
        )

    def test_undefined_cells_are_skipped_rather_than_treated_as_zero(self):
        cells = self.build_cells(
            lambda site, cond: None if site == "wordpress" else 20.0,
            lambda site, cond: 0 if site == "wordpress" else 100,
        )
        agg = metrics.aggregate(cells)
        assert agg.metric("SFR").websites["wordpress"] is None
        assert agg.metric("SFR").conditions["src"] == pytest.approx(20.0)
        assert agg.metric("SFR").overall == pytest.approx(20.0)

    def test_marginal_is_none_when_every_cell_is_undefined(self):
        cells = self.build_cells(lambda site, cond: None, lambda site, cond: 0)
        agg = metrics.aggregate(cells)
        assert agg.metric("SFR").overall is None

    def test_marginal_inherits_low_confidence_from_its_cells(self):
        cells = self.build_cells(lambda site, cond: 20.0, lambda site, cond: 3)
        agg = metrics.aggregate(cells)
        assert agg.metric("SFR").low_confidence["overall"] is True
        assert agg.metric("SFR").low_confidence["gitlab"] is True
