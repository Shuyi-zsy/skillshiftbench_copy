"""The pinned calibration subset: thirty task families, chosen by a stated rule.

Why families and not uids
-------------------------
Every task family exists in both site versions, and one calibration task is run
under all six conditions -- `src*` against the v1 task file, `tgt*` against the
v2 one.  Pinning a uid such as ``skillshift.gitlab.v1.0`` would therefore lock
only half of each family's grid.  The subset pins `family_id`, and the condition
chooses the version at run time.

Why a rule and not a hand-picked list
-------------------------------------
The subset is an anchor other people measure their environment against, so it
has to be auditable.  `sample_family_ids` *is* the rule; the shipped
`data/calibration_set.json` is its output, and a test asserts the two agree.
Anyone can recompute the same thirty ids from the formula in the file without
trusting the file.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .. import paths, registry, sites
from ..errors import CalibrationError, SkillShiftError

#: How many families each site contributes.  Roughly proportional to the site's
#: share of the benchmark (162 / 114 / 79), rounded to keep every site's cell
#: large enough to move at all: WordPress at six tasks is already the noisiest
#: cell, and going lower would make its calibration reading meaningless.
SAMPLE_COUNTS: Mapping[str, int] = {"gitlab": 14, "magento": 10, "wordpress": 6}

#: Total size of the subset.  30 families x 6 conditions = 180 runs.
CALIBRATION_SET_SIZE: int = sum(SAMPLE_COUNTS.values())

#: Identifier of the sampling rule, recorded in the shipped file.  A new rule
#: gets a new id rather than silently changing what the anchor measures.
SAMPLING_RULE_ID = "uniform-by-index-v1"

#: The rule, in one line, as printed in `data/calibration_set.json`.
SAMPLING_FORMULA = "index_j = floor(j * n_tasks / k) for j = 0 .. k-1"

SCHEMA_VERSION = "1.0"


def sample_indices(n_tasks: int, k: int) -> tuple[int, ...]:
    """The `k` task indices the rule selects out of `n_tasks`.

    Deterministic and seed-free: `index_j = floor(j * n_tasks / k)`.  Spreads
    the picks evenly across the file order and always includes index 0.
    """
    n_tasks = int(n_tasks)
    k = int(k)
    if k <= 0:
        raise CalibrationError(f"Sample size must be positive, got k={k}.")
    if k > n_tasks:
        raise CalibrationError(
            f"Cannot sample {k} tasks out of {n_tasks}: the subset would have to repeat a task."
        )
    return tuple(j * n_tasks // k for j in range(k))


def sample_family_ids(counts: Mapping[str, int] = SAMPLE_COUNTS) -> tuple[str, ...]:
    """Recompute the whole subset from the rule, in site-then-index order."""
    family_ids: list[str] = []
    for site in sites.SITE_NAMES:
        k = counts.get(site)
        if k is None:
            continue
        n_tasks = sites.get(site).n_tasks
        family_ids.extend(
            registry.make_family_id(site, index) for index in sample_indices(n_tasks, k)
        )
    return tuple(family_ids)


@dataclass(frozen=True)
class CalibrationSet:
    """The thirty pinned families, plus the rule that produced them."""

    schema_version: str
    sampling_rule: str
    family_ids: tuple[str, ...]

    def by_site(self) -> Mapping[str, tuple[str, ...]]:
        """The pinned families grouped by site, each group in index order."""
        reg = registry.load_registry()
        grouped: dict[str, list[str]] = {site: [] for site in sites.SITE_NAMES}
        for family_id in self.family_ids:
            task = reg.resolve(family_id, site_version="v1")
            grouped[task.site].append(family_id)
        return {site: tuple(ids) for site, ids in grouped.items() if ids}

    def task_refs(self, condition: str, *, site: str | None = None) -> tuple:
        """Resolve the subset to concrete task variants for one condition."""
        reg = registry.load_registry()
        wanted = sites.get(site).name if site is not None else None
        refs = [reg.resolve(family_id, condition=condition) for family_id in self.family_ids]
        return tuple(ref for ref in refs if wanted is None or ref.site == wanted)


def _read(path: Path) -> dict:
    if not path.is_file():
        raise CalibrationError(
            f"Calibration subset not found: {path}. It ships with the repository; "
            f"a source checkout or an editable install has it at data/calibration_set.json."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CalibrationError(f"Calibration subset at {path} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise CalibrationError(f"Calibration subset at {path} must be a JSON object.")
    return payload


def _family_ids_of(payload: Mapping, path: Path) -> tuple[str, ...]:
    raw = payload.get("family_ids")
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        raise CalibrationError(f"Calibration subset at {path} has no `family_ids` list.")

    family_ids = tuple(str(value) for value in raw)
    if len(family_ids) != CALIBRATION_SET_SIZE:
        raise CalibrationError(
            f"Calibration subset at {path} pins {len(family_ids)} families, expected "
            f"{CALIBRATION_SET_SIZE}. The subset size is fixed: it is what the published "
            f"reference results were measured on."
        )
    if len(set(family_ids)) != len(family_ids):
        raise CalibrationError(f"Calibration subset at {path} repeats a family id.")
    return family_ids


def load_calibration_set(path: Path | str | None = None) -> CalibrationSet:
    """Load the pinned subset, checking that every id resolves."""
    path = Path(path) if path is not None else paths.CALIBRATION_SET_PATH
    payload = _read(path)
    family_ids = _family_ids_of(payload, path)

    reg = registry.load_registry()
    for family_id in family_ids:
        try:
            reg.resolve(family_id, site_version="v1")
            reg.resolve(family_id, site_version="v2")
        except SkillShiftError as exc:
            raise CalibrationError(
                f"Calibration subset at {path} pins {family_id!r}, which does not resolve "
                f"in both site versions: {exc}"
            ) from exc

    sampling = payload.get("sampling") or {}
    return CalibrationSet(
        schema_version=str(payload.get("schema_version", "")),
        sampling_rule=str(sampling.get("rule", "")),
        family_ids=family_ids,
    )
