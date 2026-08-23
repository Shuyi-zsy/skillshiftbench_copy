"""SkillShift-Bench: learned-skill executability under controlled website evolution.

The public surface is intentionally small.  Heavy submodules (`tasks`, `agents`)
pull in the browser stack and are imported on demand, so that
`import skillshift` stays cheap for the aggregation and validation path.
"""

__version__ = "0.1.0"

from . import conditions, errors, sites  # noqa: F401

__all__ = ["__version__", "conditions", "errors", "sites"]
