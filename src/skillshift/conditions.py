"""The six evaluation conditions, and the only place they map to environment.

The paper evaluates every task family under six conditions (Section 2.3):

    src        clean source context                 v1, no shift
    src-perc   source + Perceptual Shift            v1, perceptual
    src-exec   source + Execution Shift             v1, execution
    tgt        clean target context                 v2, no shift
    tgt-perc   target + Perceptual Shift            v2, perceptual
    tgt-exec   target + Execution Shift             v2, execution

The harness itself is driven by four loosely coupled environment variables.
Composing them by hand is how a run silently lands in a cell it does not belong
to, so `--condition` is the only supported surface and this module is the only
translator.
"""

from dataclasses import dataclass

from . import sites
from .errors import UnknownConditionError


@dataclass(frozen=True)
class ConditionSpec:
    """One column of the paper's environment breakdown."""

    name: str
    site_version: str
    perceptual_shift: bool
    execution_shift: bool

    @property
    def is_source(self) -> bool:
        return self.site_version == "v1"


#: The six conditions, in the order they appear in Table 1.
CONDITIONS: tuple[str, ...] = (
    "src",
    "src-perc",
    "src-exec",
    "tgt",
    "tgt-perc",
    "tgt-exec",
)

SITE_VERSIONS: tuple[str, ...] = ("v1", "v2")

_SPECS: dict[str, ConditionSpec] = {
    "src": ConditionSpec("src", "v1", False, False),
    "src-perc": ConditionSpec("src-perc", "v1", True, False),
    "src-exec": ConditionSpec("src-exec", "v1", False, True),
    "tgt": ConditionSpec("tgt", "v2", False, False),
    "tgt-perc": ConditionSpec("tgt-perc", "v2", True, False),
    "tgt-exec": ConditionSpec("tgt-exec", "v2", False, True),
}

_FLAGS_TO_NAME: dict[tuple[str, bool, bool], str] = {
    (spec.site_version, spec.perceptual_shift, spec.execution_shift): name
    for name, spec in _SPECS.items()
}


def _normalize(name: str) -> str:
    return str(name).strip().lower().replace("_", "-")


def resolve(name: str) -> ConditionSpec:
    """Return the spec for a condition name.

    Accepts any case and either `-` or `_` as the separator.
    """
    key = _normalize(name)
    spec = _SPECS.get(key)
    if spec is None:
        raise UnknownConditionError(
            f"Unknown condition {name!r}. Expected one of {list(CONDITIONS)}."
        )
    return spec


def from_flags(
    *,
    site_version: str,
    perceptual_shift: bool,
    execution_shift: bool,
) -> ConditionSpec:
    """Recover a condition from the raw harness flags.

    Used to interpret a legacy environment-variable configuration.  Combinations
    the paper does not define -- notably both shifts at once -- are rejected
    rather than mapped to a nearby cell.
    """
    version = str(site_version).strip().lower()
    if version not in SITE_VERSIONS:
        raise UnknownConditionError(
            f"Unknown site_version {site_version!r}. Expected one of {list(SITE_VERSIONS)}."
        )

    key = (version, bool(perceptual_shift), bool(execution_shift))
    name = _FLAGS_TO_NAME.get(key)
    if name is None:
        raise UnknownConditionError(
            f"No SkillShift-Bench condition corresponds to "
            f"site_version={version!r}, perceptual_shift={bool(perceptual_shift)}, "
            f"execution_shift={bool(execution_shift)}. Perceptual and Execution Shift "
            f"are evaluated separately; there is no cell with both enabled."
        )
    return _SPECS[name]


def to_env(*, site: str, condition: str) -> dict[str, str]:
    """Build the environment variables that put the harness in one cell.

    Both the upper-case and lower-case spellings are emitted.  The harness reads
    `WEBSITE` before `website`, so setting only one of them lets a stale variable
    already present in the user's shell decide the run.
    """
    site_spec = sites.get(site)
    spec = resolve(condition)

    values = {
        "website": site_spec.harness_key,
        "site_version": spec.site_version,
        "with_perceptual_shift": "true" if spec.perceptual_shift else "false",
        "with_execution_shift": "true" if spec.execution_shift else "false",
    }
    return {**values, **{key.upper(): value for key, value in values.items()}}


def all_specs() -> tuple[ConditionSpec, ...]:
    """Every condition, in paper-table order."""
    return tuple(_SPECS[name] for name in CONDITIONS)
