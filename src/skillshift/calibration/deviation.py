"""Grading an observed calibration run against the published anchor.

The reading is `|observed - anchor| / sigma`: how many standard deviations a
local environment sits away from the one the published numbers came from.  A
cell beyond the threshold is a statement about the *environment*, not about the
agent -- the reference agent is the same code on both sides.

Which metrics gate
------------------
Only SR and AS.  SR is the signal; AS is what actually catches a wrong image,
because an agent facing an unexpected page layout takes more steps before it
gives up.  ASC and SFR are reported but never fail a run: the reference agent
has no skill library, so its ASC is 0 by construction and its SFR has no
denominator at all.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..environments import environment_for
from ..errors import CalibrationError
from ..eval.metrics import METRIC_NAMES, CellStats
from .reference import ReferenceResults

#: Deviation beyond which a cell is called misconfigured.  Three sigma: the
#: check runs over eighteen cells at once, so a looser threshold would flag a
#: correct environment on almost every run.
DEVIATION_THRESHOLD: float = 3.0

#: Metrics whose deviation fails the run.  See the module docstring.
GATED_METRICS: tuple[str, ...] = ("SR", "AS")


@dataclass(frozen=True)
class MetricDeviation:
    """How far one observed metric sits from its anchor, in sigmas."""

    site: str
    condition: str
    environment: str
    metric: str
    observed: float | None
    expected: float | None
    sigma: float | None
    sigmas: float | None
    gated: bool
    beyond: bool

    def __str__(self) -> str:
        if self.sigmas is None:
            return (
                f"  {self.site:<10} {self.condition:<9} {self.metric:<4} "
                f"not compared (no anchored value)"
            )
        mark = "FAIL" if self.beyond else "ok"
        gate = "" if self.gated else "  [not gated]"
        return (
            f"  {self.site:<10} {self.condition:<9} {self.metric:<4} "
            f"observed {self.observed:>8.2f}  anchor {self.expected:>8.2f} "
            f"+/- {self.sigma:.2f}  {self.sigmas:>5.1f} sigma  {mark}"
            f"  [image {self.environment}]{gate}"
        )


@dataclass(frozen=True)
class CalibrationReport:
    """Every comparison made, and whether the environment passes."""

    deviations: tuple[MetricDeviation, ...]
    threshold: float

    @property
    def offenders(self) -> tuple[MetricDeviation, ...]:
        return tuple(d for d in self.deviations if d.gated and d.beyond)

    @property
    def compared(self) -> tuple[MetricDeviation, ...]:
        return tuple(d for d in self.deviations if d.sigmas is not None)

    @property
    def ok(self) -> bool:
        return not self.offenders

    def lines(self) -> tuple[str, ...]:
        return tuple(str(deviation) for deviation in self.deviations)

    def summary(self) -> str:
        if self.ok:
            return (
                f"Your environment matches the reference anchor: all "
                f"{len(self.compared)} compared value(s) are within "
                f"{self.threshold:g} sigma."
            )
        worst = max(self.offenders, key=lambda d: d.sigmas or 0.0)
        images = sorted({d.environment for d in self.offenders})
        return (
            f"{len(self.offenders)} value(s) deviate from the reference anchor by more "
            f"than {self.threshold:g} sigma. Worst: {worst.site} {worst.condition} "
            f"{worst.metric} is {worst.sigmas:.1f} sigma from the anchor. Check the "
            f"image version(s) for: {', '.join(images)}."
        )


def _check_observed(cells: Sequence[CellStats], reference: ReferenceResults) -> None:
    keys = [(cell.site, cell.condition) for cell in cells]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise CalibrationError(f"The same cell was measured more than once: {duplicates}.")

    for cell in cells:
        anchor = reference.cell(cell.site, cell.condition)
        if cell.n != anchor.n:
            raise CalibrationError(
                f"Cell ({cell.site}, {cell.condition}) covers {cell.n} tasks but the "
                f"calibration subset pins {anchor.n}. Run `skillshift calibrate`, which "
                f"selects the pinned families, rather than a hand-picked task list."
            )


def _deviation(cell: CellStats, reference: ReferenceResults, metric: str, threshold: float):
    anchor = reference.cell(cell.site, cell.condition).metric(metric)
    observed = cell.value(metric)
    gated = metric in GATED_METRICS

    comparable = anchor.is_published and observed is not None
    sigmas = abs(observed - anchor.value) / anchor.sigma if comparable else None

    return MetricDeviation(
        site=cell.site,
        condition=cell.condition,
        environment=environment_for(cell.site, cell.condition),
        metric=metric,
        observed=observed,
        expected=anchor.value,
        sigma=anchor.sigma,
        sigmas=sigmas,
        gated=gated,
        beyond=bool(sigmas is not None and sigmas > threshold),
    )


def compare(
    cells: Sequence[CellStats],
    reference: ReferenceResults,
    *,
    threshold: float | None = None,
) -> CalibrationReport:
    """Compare observed calibration cells with the anchor.

    Raises if the anchor carries no numbers yet: grading against an unpublished
    anchor would report a pass that means nothing.
    """
    if not reference.is_published:
        raise CalibrationError(
            "The reference anchor has not been published yet, so there is nothing to "
            "compare against. See data/reference_results/README.md."
        )

    cells = tuple(cells)
    if not cells:
        raise CalibrationError("No calibration cells were measured.")

    _check_observed(cells, reference)
    threshold = reference.threshold_sigma if threshold is None else float(threshold)

    deviations = tuple(
        _deviation(cell, reference, metric, threshold)
        for cell in cells
        for metric in METRIC_NAMES
    )
    return CalibrationReport(deviations=deviations, threshold=threshold)
