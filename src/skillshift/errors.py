"""Explicit error types for SkillShift-Bench.

Every failure a user can cause -- a misspelled condition, a task id that does
not exist, a results file that will not pass leaderboard CI -- gets its own type
and a message that names the valid alternatives.  Nothing is swallowed.
"""


class SkillShiftError(Exception):
    """Base class for every error raised by this package."""


class UnknownSiteError(SkillShiftError):
    """Raised for a site name outside {gitlab, magento, wordpress}."""


class UnknownConditionError(SkillShiftError):
    """Raised for a condition outside the six defined by the paper."""


class UnknownTaskError(SkillShiftError):
    """Raised for a task id that is not in the registry."""


class TaskDataError(SkillShiftError):
    """Raised when the shipped task files are missing, malformed, or miscounted."""


class MetricError(SkillShiftError):
    """Raised when a metric cannot be computed from the given records."""


class ReceiptError(SkillShiftError):
    """Raised when a run receipt is incomplete or inconsistent with its results."""


class ValidationError(SkillShiftError):
    """Raised when a submission fails one of the leaderboard checks."""


class EnvironmentNotReadyError(SkillShiftError):
    """Raised when a benchmark website is unreachable or reports the wrong version."""


class SkillRecordingError(SkillShiftError):
    """Raised when an agent misuses the skill-call recorder."""


class CalibrationError(SkillShiftError):
    """Raised when the calibration subset or the reference results cannot be used."""
