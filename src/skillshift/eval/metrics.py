"""SR / AS / ASC / SFR -- the single authoritative implementation.

Definitions (paper, Section 2.4)
--------------------------------
Success Rate (SR)
    Fraction of tasks that meet the success criterion.  Reported as a
    percentage, matching the paper's table.
Average Steps (AS)
    Mean number of actions before success, failure, or timeout.  Averaged over
    *every* task, not only successful ones.
Average Skill Calls (ASC)
    Mean number of learned-skill invocations per task.
Skill Failure Rate (SFR)
    Proportion of invoked skills that fail during attempted execution, runtime
    errors included.  Reported as a percentage.  It is undefined -- `None`, not
    zero -- when no skill was invoked, and unstable when few were: the paper
    reports it as a supplementary diagnostic for exactly this reason, and cells
    below `SFR_MIN_SKILL_CALLS` invocations carry a low-confidence flag.

Aggregation
-----------
A *cell* is one (website, condition) pair; there are 3 x 6 = 18 of them.  The
website marginal is the unweighted mean of that website's six cells, the
condition marginal is the unweighted mean of that condition's three cells, and
the overall value (the paper's ``O/A`` column) is the unweighted mean of all
eighteen.

**Websites are not weighted by task count.**  This is verified against every row
of the published Table 1 in `tests/test_table1_transcription.py`: the macro
average reproduces the printed ``O/A`` for all fourteen rows, while weighting the
websites by 162 / 114 / 79 moves SR/AWM from 35.29 to 30.21.

Because both marginals are macro-averages of the same eighteen cells,

    mean(3 websites) == mean(6 conditions) == O/A

is an identity.  `check_marginals` enforces it, which is what lets the
leaderboard verify an entry that ships only the ten marginal numbers.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from ..conditions import CONDITIONS
from ..errors import MetricError
from ..sites import SITE_NAMES, task_counts
from .records import TaskRecord

#: The four diagnostics, in the order the paper's table lists them.
METRIC_NAMES: tuple[str, ...] = ("SR", "AS", "ASC", "SFR")

#: Below this many skill invocations, SFR is flagged as unstable.  The paper
#: measures ASC around 0.06-0.15 calls per task for ASI and MPCR, so whole cells
#: routinely land under this threshold; the flag is the normal case, not an edge
#: case, and the leaderboard must never sort on an unflagged-looking SFR.
SFR_MIN_SKILL_CALLS: int = 30

#: Absolute tolerance for the marginal identity.  The paper prints two decimals,
#: so the identity can only hold to about half of the last digit.
MARGINAL_TOLERANCE: float = 0.02


@dataclass(frozen=True)
class CellStats:
    """The four diagnostics for one (website, condition) cell."""

    site: str
    condition: str
    n: int
    sr: float | None
    avg_steps: float | None
    asc: float | None
    sfr: float | None
    n_skill_calls: int
    sfr_low_confidence: bool

    def value(self, metric: str) -> float | None:
        try:
            return {"SR": self.sr, "AS": self.avg_steps, "ASC": self.asc, "SFR": self.sfr}[metric]
        except KeyError:
            raise MetricError(f"Unknown metric {metric!r}. Expected one of {list(METRIC_NAMES)}.") from None


@dataclass(frozen=True)
class MetricBreakdown:
    """One metric's ten published numbers: 3 websites, 6 conditions, O/A."""

    name: str
    websites: Mapping[str, float | None]
    conditions: Mapping[str, float | None]
    overall: float | None
    low_confidence: Mapping[str, bool]

    def to_dict(self) -> dict:
        return {
            "websites": dict(self.websites),
            "conditions": dict(self.conditions),
            "overall": self.overall,
        }


@dataclass(frozen=True)
class Aggregate:
    """Every metric's breakdown, plus the denominators behind them."""

    metrics: Mapping[str, MetricBreakdown]
    n_websites: Mapping[str, int]
    n_conditions: Mapping[str, int]
    n_skill_calls: Mapping[str, int]

    def metric(self, name: str) -> MetricBreakdown:
        try:
            return self.metrics[name]
        except KeyError:
            raise MetricError(
                f"Unknown metric {name!r}. Expected one of {list(METRIC_NAMES)}."
            ) from None

    def to_dict(self) -> dict:
        return {
            "metrics": {name: self.metrics[name].to_dict() for name in METRIC_NAMES},
            "n": {
                "websites": dict(self.n_websites),
                "conditions": dict(self.n_conditions),
                "skill_calls": dict(self.n_skill_calls),
            },
        }


def compute_cell(records: Sequence[TaskRecord]) -> CellStats:
    """Compute one cell's diagnostics from its per-task records."""
    records = tuple(records)
    if not records:
        raise MetricError("Cannot compute a cell from zero records.")

    sites_seen = {record.site for record in records}
    conditions_seen = {record.condition for record in records}
    if len(sites_seen) != 1 or len(conditions_seen) != 1:
        raise MetricError(
            f"A cell must hold exactly one (site, condition) pair; got "
            f"sites={sorted(sites_seen)}, conditions={sorted(conditions_seen)}."
        )

    uids = [record.uid for record in records]
    if len(set(uids)) != len(uids):
        duplicates = sorted({uid for uid in uids if uids.count(uid) > 1})
        raise MetricError(f"Duplicate task ids in one cell: {duplicates[:5]}")

    for record in records:
        if record.steps < 0 or record.skill_calls < 0 or record.skill_failures < 0:
            raise MetricError(f"Negative counts in record {record.uid!r}.")
        if record.skill_failures > record.skill_calls:
            raise MetricError(
                f"Record {record.uid!r} reports {record.skill_failures} skill failures "
                f"but only {record.skill_calls} skill calls."
            )

    n = len(records)
    n_calls = sum(record.skill_calls for record in records)
    n_failures = sum(record.skill_failures for record in records)

    return CellStats(
        site=records[0].site,
        condition=records[0].condition,
        n=n,
        sr=100.0 * sum(1 for record in records if record.success) / n,
        avg_steps=sum(record.steps for record in records) / n,
        asc=n_calls / n,
        sfr=(100.0 * n_failures / n_calls) if n_calls else None,
        n_skill_calls=n_calls,
        sfr_low_confidence=n_calls < SFR_MIN_SKILL_CALLS,
    )


def compute_cells(records: Iterable[TaskRecord]) -> tuple[CellStats, ...]:
    """Group records by (site, condition) and compute every cell."""
    grouped: dict[tuple[str, str], list[TaskRecord]] = {}
    for record in records:
        grouped.setdefault((record.site, record.condition), []).append(record)

    return tuple(
        compute_cell(grouped[key])
        for key in sorted(grouped, key=lambda key: (SITE_NAMES.index(key[0]) if key[0] in SITE_NAMES else 99, key[1]))
    )


def macro_mean(values: Iterable[float | None]) -> float | None:
    """Unweighted mean over the values that are defined; `None` if none are."""
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def aggregate(cells: Sequence[CellStats]) -> Aggregate:
    """Turn the eighteen cells into the ten published numbers per metric."""
    cells = tuple(cells)

    keys = [(cell.site, cell.condition) for cell in cells]
    if len(set(keys)) != len(keys):
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        raise MetricError(f"Duplicate cells: {duplicates}")

    expected = {(site, condition) for site in SITE_NAMES for condition in CONDITIONS}
    missing = expected - set(keys)
    if missing:
        raise MetricError(
            f"Incomplete cell grid: {len(missing)} of {len(expected)} cells missing, "
            f"e.g. {sorted(missing)[:3]}. Every (website, condition) pair must be present; "
            f"use an explicit null with a reason for cells that were not run."
        )
    unexpected = set(keys) - expected
    if unexpected:
        raise MetricError(f"Unexpected cells outside the 3x6 grid: {sorted(unexpected)}")

    by_key = {(cell.site, cell.condition): cell for cell in cells}

    breakdowns: dict[str, MetricBreakdown] = {}
    for metric in METRIC_NAMES:
        websites = {
            site: macro_mean(by_key[(site, condition)].value(metric) for condition in CONDITIONS)
            for site in SITE_NAMES
        }
        conditions = {
            condition: macro_mean(by_key[(site, condition)].value(metric) for site in SITE_NAMES)
            for condition in CONDITIONS
        }
        overall = macro_mean(cell.value(metric) for cell in cells)

        low_confidence = {
            **{
                site: any(by_key[(site, condition)].sfr_low_confidence for condition in CONDITIONS)
                for site in SITE_NAMES
            },
            **{
                condition: any(by_key[(site, condition)].sfr_low_confidence for site in SITE_NAMES)
                for condition in CONDITIONS
            },
            "overall": any(cell.sfr_low_confidence for cell in cells),
        }
        if metric != "SFR":
            low_confidence = dict.fromkeys(low_confidence, False)

        breakdowns[metric] = MetricBreakdown(
            name=metric,
            websites=websites,
            conditions=conditions,
            overall=overall,
            low_confidence=low_confidence,
        )

    n_websites = {site: by_key[(site, CONDITIONS[0])].n for site in SITE_NAMES}
    n_conditions = {
        condition: sum(by_key[(site, condition)].n for site in SITE_NAMES)
        for condition in CONDITIONS
    }
    n_skill_calls = {
        **{
            site: sum(by_key[(site, condition)].n_skill_calls for condition in CONDITIONS)
            for site in SITE_NAMES
        },
        **{
            condition: sum(by_key[(site, condition)].n_skill_calls for site in SITE_NAMES)
            for condition in CONDITIONS
        },
        "overall": sum(cell.n_skill_calls for cell in cells),
    }

    _check_denominators(by_key)

    return Aggregate(
        metrics=breakdowns,
        n_websites=n_websites,
        n_conditions=n_conditions,
        n_skill_calls=n_skill_calls,
    )


def _check_denominators(by_key: Mapping[tuple[str, str], CellStats]) -> None:
    official = task_counts()
    for (site, condition), cell in by_key.items():
        if cell.n != official[site]:
            raise MetricError(
                f"Cell ({site}, {condition}) has n={cell.n}, but {site} has "
                f"{official[site]} tasks. A cell must cover every task of its site."
            )


def check_marginals(
    *,
    websites: Mapping[str, float | None],
    conditions: Mapping[str, float | None],
    overall: float | None,
    tol: float = MARGINAL_TOLERANCE,
) -> tuple[str, ...]:
    """Check the macro-average identity on one metric's ten numbers.

    Returns a tuple of human-readable problems; empty means consistent.  Null
    entries are skipped rather than treated as zero.
    """
    problems: list[str] = []

    if set(websites) != set(SITE_NAMES):
        problems.append(
            f"website keys are {sorted(websites)}, expected {sorted(SITE_NAMES)}"
        )
    if set(conditions) != set(CONDITIONS):
        problems.append(
            f"condition keys are {sorted(conditions)}, expected {sorted(CONDITIONS)}"
        )
    if problems:
        return tuple(problems)

    site_macro = macro_mean(websites.values())
    condition_macro = macro_mean(conditions.values())

    if overall is None:
        if site_macro is not None or condition_macro is not None:
            problems.append(
                "overall is null but the website/condition marginals are not; "
                "a null overall needs every marginal to be null too"
            )
        return tuple(problems)

    if site_macro is None and condition_macro is None:
        problems.append("overall is given but every marginal is null")
        return tuple(problems)

    if site_macro is not None and abs(site_macro - overall) > tol:
        problems.append(
            f"mean of the 3 website values is {site_macro:.4f} but overall is "
            f"{overall:.4f} (tolerance {tol})"
        )
    if condition_macro is not None and abs(condition_macro - overall) > tol:
        problems.append(
            f"mean of the 6 condition values is {condition_macro:.4f} but overall is "
            f"{overall:.4f} (tolerance {tol})"
        )
    if (
        site_macro is not None
        and condition_macro is not None
        and abs(site_macro - condition_macro) > tol
    ):
        problems.append(
            f"mean of the websites ({site_macro:.4f}) disagrees with mean of the "
            f"conditions ({condition_macro:.4f})"
        )

    return tuple(problems)
