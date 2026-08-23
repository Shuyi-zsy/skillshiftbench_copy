"""Calibration: telling a misconfigured environment from a weak method.

`skillshift calibrate` runs the built-in no-skill reference agent over thirty
pinned task families under all six conditions and compares the result with the
published anchor in `data/reference_results/`.  Nothing here is a leaderboard
number: the subset's denominators (14 / 10 / 6) are not the benchmark's
(162 / 114 / 79), and the reference agent is not a competitive method.
"""

from .deviation import (
    DEVIATION_THRESHOLD,
    GATED_METRICS,
    CalibrationReport,
    MetricDeviation,
    compare,
)
from .reference import (
    ReferenceCell,
    ReferenceResults,
    ReferenceValue,
    load_reference_results,
)
from .subset import (
    CALIBRATION_SET_SIZE,
    SAMPLE_COUNTS,
    SAMPLING_FORMULA,
    SAMPLING_RULE_ID,
    CalibrationSet,
    load_calibration_set,
    sample_family_ids,
    sample_indices,
)

__all__ = [
    "CALIBRATION_SET_SIZE",
    "DEVIATION_THRESHOLD",
    "GATED_METRICS",
    "SAMPLE_COUNTS",
    "SAMPLING_FORMULA",
    "SAMPLING_RULE_ID",
    "CalibrationReport",
    "CalibrationSet",
    "MetricDeviation",
    "ReferenceCell",
    "ReferenceResults",
    "ReferenceValue",
    "compare",
    "load_calibration_set",
    "load_reference_results",
    "sample_family_ids",
    "sample_indices",
]
