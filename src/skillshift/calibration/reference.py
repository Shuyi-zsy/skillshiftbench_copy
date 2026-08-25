"""The published reference anchor: what the no-skill agent scores on the subset.

Shape
-----
One value per (site, condition, metric), each carrying its own `sigma` -- the
spread the value is allowed to move within before a local environment counts as
misconfigured.  `skillshift calibrate` reads `|observed - value| / sigma`.

Why the file ships empty
------------------------
The anchor can only be measured once the environment images are tagged, because
its whole purpose is to say "your GitLab is not the GitLab these numbers came
from".  A placeholder would be indistinguishable from a measurement and would
make `calibrate` certify environments against fiction.  Until then the file
carries `status: "pending"` and every value is `null`; `calibrate` says so and
refuses to grade.  See `data/reference_results/README.md`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .. import paths
from ..conditions import CONDITIONS
from ..errors import CalibrationError
from ..eval.metrics import METRIC_NAMES
from ..sites import SITE_NAMES
from .subset import SAMPLE_COUNTS

REFERENCE_RESULTS_FILENAME = "reference-react.json"

STATUS_PENDING = "pending"
STATUS_PUBLISHED = "published"


@dataclass(frozen=True)
class ReferenceValue:
    """One anchored number and the spread it is graded against."""

    value: float | None
    sigma: float | None

    @property
    def is_published(self) -> bool:
        return self.value is not None and self.sigma is not None


@dataclass(frozen=True)
class ReferenceCell:
    """The anchor for one (site, condition) cell of the calibration subset."""

    site: str
    condition: str
    n: int
    n_skill_calls: int | None
    metrics: Mapping[str, ReferenceValue]

    @property
    def key(self) -> str:
        return f"{self.site}/{self.condition}"

    def metric(self, name: str) -> ReferenceValue:
        try:
            return self.metrics[name]
        except KeyError:
            raise CalibrationError(
                f"Reference cell {self.key} has no entry for metric {name!r}."
            ) from None


@dataclass(frozen=True)
class ReferenceResults:
    """The whole anchor: eighteen cells plus how it was produced."""

    schema_version: str
    status: str
    agent: str | None
    model: str | None
    harness_version: str | None
    sigma_method: str | None
    threshold_sigma: float
    #: Step budget the sweep was measured at.  AS is a count of steps, so an
    #: anchor is only comparable with a local run made at the same budget.
    #: `None` for an anchor that predates the field, which grades unguarded.
    max_steps: int | None
    gated_metrics: tuple[str, ...]
    _cells: Mapping[tuple[str, str], ReferenceCell]

    def cells(self) -> tuple[ReferenceCell, ...]:
        return tuple(
            self._cells[(site, condition)]
            for site in SITE_NAMES
            for condition in CONDITIONS
        )

    def cell(self, site: str, condition: str) -> ReferenceCell:
        try:
            return self._cells[(site, condition)]
        except KeyError:
            raise CalibrationError(
                f"The reference anchor has no cell for ({site}, {condition})."
            ) from None

    def unpublished_cells(self) -> tuple[str, ...]:
        """Cells whose gated metrics are not both anchored, as 'site/condition'."""
        return tuple(
            cell.key
            for cell in self.cells()
            if any(not cell.metric(name).is_published for name in self.gated_metrics)
        )

    @property
    def is_published(self) -> bool:
        """True only when the file says so *and* every gated number is present."""
        return self.status == STATUS_PUBLISHED and not self.unpublished_cells()


def default_path() -> Path:
    return paths.REFERENCE_RESULTS_DIR / REFERENCE_RESULTS_FILENAME


def _read(path: Path) -> dict:
    if not path.is_file():
        raise CalibrationError(
            f"Reference results not found: {path}. They ship with the repository; "
            f"a source checkout or an editable install has them under "
            f"data/reference_results/."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CalibrationError(f"Reference results at {path} are not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise CalibrationError(f"Reference results at {path} must be a JSON object.")
    return payload


def _read_value(raw: object, *, where: str, metric: str) -> ReferenceValue:
    if not isinstance(raw, Mapping):
        raise CalibrationError(f"{where}: metric {metric!r} must be an object with value and sigma.")

    value = raw.get("value")
    sigma = raw.get("sigma")
    if sigma is not None and float(sigma) <= 0:
        raise CalibrationError(
            f"{where}: metric {metric!r} has sigma={sigma}, which cannot grade anything. "
            f"A zero or negative sigma would make every observation infinitely deviant; "
            f"leave it null until it has been measured."
        )
    return ReferenceValue(
        value=None if value is None else float(value),
        sigma=None if sigma is None else float(sigma),
    )


def _read_cell(raw: object, *, site: str, condition: str, path: Path) -> ReferenceCell:
    where = f"{path}: cell {site}/{condition}"
    if not isinstance(raw, Mapping):
        raise CalibrationError(f"{where} must be an object.")

    expected_n = SAMPLE_COUNTS[site]
    n = raw.get("n")
    if n != expected_n:
        raise CalibrationError(
            f"{where} has n={n}, expected {expected_n}: the calibration subset pins "
            f"{expected_n} {site} families."
        )

    n_skill_calls = raw.get("n_skill_calls")
    return ReferenceCell(
        site=site,
        condition=condition,
        n=int(n),
        n_skill_calls=None if n_skill_calls is None else int(n_skill_calls),
        metrics={
            name: _read_value(raw.get(name), where=where, metric=name) for name in METRIC_NAMES
        },
    )


def _read_cells(payload: Mapping, path: Path) -> dict[tuple[str, str], ReferenceCell]:
    blocks = payload.get("cells")
    if not isinstance(blocks, Mapping):
        raise CalibrationError(f"Reference results at {path} have no `cells` object.")

    cells: dict[tuple[str, str], ReferenceCell] = {}
    for site in SITE_NAMES:
        site_block = blocks.get(site)
        if not isinstance(site_block, Mapping):
            raise CalibrationError(f"Reference results at {path} have no cells for {site!r}.")
        for condition in CONDITIONS:
            if condition not in site_block:
                raise CalibrationError(
                    f"Reference results at {path} are missing cell {site}/{condition}. "
                    f"All {len(SITE_NAMES) * len(CONDITIONS)} cells must be present, null or not."
                )
            cells[(site, condition)] = _read_cell(
                site_block[condition], site=site, condition=condition, path=path
            )
    return cells


def _read_max_steps(raw: object, *, path: Path) -> int | None:
    """The step budget, if the anchor records one.

    Absent is allowed -- an anchor written before the field existed grades
    without the guard.  Present but not a positive whole number is not: it
    would silently disable a check that exists to stop AS being compared
    across two different budgets.
    """
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise CalibrationError(
            f"Reference results at {path} record max_steps={raw!r}, which is not a number."
        ) from None
    if value < 1:
        raise CalibrationError(
            f"Reference results at {path} record max_steps={value}, which cannot have "
            f"produced any run."
        )
    return value


def load_reference_results(path: Path | str | None = None) -> ReferenceResults:
    """Load and validate the anchor.  Absent numbers are fine; a broken shape is not."""
    path = Path(path) if path is not None else default_path()
    payload = _read(path)

    gated = payload.get("gated_metrics") or ()
    unknown = [name for name in gated if name not in METRIC_NAMES]
    if unknown:
        raise CalibrationError(f"Reference results at {path} gate on unknown metric(s) {unknown}.")

    return ReferenceResults(
        schema_version=str(payload.get("schema_version", "")),
        status=str(payload.get("status", STATUS_PENDING)),
        agent=payload.get("agent"),
        model=payload.get("model"),
        harness_version=payload.get("harness_version"),
        sigma_method=payload.get("sigma_method"),
        threshold_sigma=float(payload.get("threshold_sigma") or 3.0),
        max_steps=_read_max_steps(payload.get("max_steps"), path=path),
        gated_metrics=tuple(str(name) for name in gated),
        _cells=_read_cells(payload, path),
    )
