"""Task registry: the only place a task id becomes a concrete task.

Ids
---
The canonical id names one task variant::

    skillshift.<site>.<version>.<index>      e.g. skillshift.gitlab.v1.9

Its version-free prefix names the *aligned family* -- the same task intent in
both the source and the target context::

    skillshift.<site>.<index>                e.g. skillshift.gitlab.9

Legacy ids
----------
The artifact addressed tasks as ``myBenchmark.<n>``.  That id was never globally
unique: each site numbers its tasks from zero, so ``myBenchmark.9`` means three
different tasks depending on the ``website`` environment variable, and the old
flat ``range(355)`` registration made ids up to 354 look valid for every site.
It is still accepted, but only together with an explicit site, and it emits a
``DeprecationWarning``.
"""

from __future__ import annotations

import csv
import functools
import json
import re
import warnings
from collections.abc import Iterator
from dataclasses import dataclass

from . import conditions, paths, sites
from .errors import TaskDataError, UnknownTaskError

_UID_RE = re.compile(r"^skillshift\.(?P<site>[a-z]+)\.(?P<version>v[12])\.(?P<index>\d+)$")
_FAMILY_RE = re.compile(r"^skillshift\.(?P<site>[a-z]+)\.(?P<index>\d+)$")
_LEGACY_RE = re.compile(r"^myBenchmark\.(?P<index>\d+)$")

#: Task files, relative to `data/tasks/`.  WordPress serves one file to both
#: versions: its contextual shift is a theme swap on a single instance.
_TASK_FILES: dict[tuple[str, str], str] = {
    ("gitlab", "v1"): "gitlab/v1.json",
    ("gitlab", "v2"): "gitlab/v2.json",
    ("magento", "v1"): "magento/v1.json",
    ("magento", "v2"): "magento/v2.json",
    ("wordpress", "v1"): "wordpress/tasks.json",
    ("wordpress", "v2"): "wordpress/tasks.json",
}


@dataclass(frozen=True)
class TaskRef:
    """One task variant: a task family instantiated in one site version."""

    uid: str
    family_id: str
    legacy_id: str
    site: str
    site_version: str
    index: int
    intent: str
    intent_template_id: int | None
    eval_types: tuple[str, ...]
    task_file: str

    @property
    def is_source(self) -> bool:
        return self.site_version == "v1"


def task_file_path(site: str, site_version: str):
    """Absolute path of the task file for one (site, version) pair."""
    site_name = sites.get(site).name
    version = str(site_version).strip().lower()
    key = (site_name, version)
    if key not in _TASK_FILES:
        raise TaskDataError(
            f"No task file for site={site_name!r}, site_version={version!r}. "
            f"Expected one of {sorted(_TASK_FILES)}."
        )
    return paths.TASKS_DIR / _TASK_FILES[key]


def make_uid(site: str, site_version: str, index: int) -> str:
    """Build a canonical uid.  `site` may be a name or an accepted alias."""
    return f"skillshift.{sites.get(site).name}.{site_version}.{int(index)}"


def make_family_id(site: str, index: int) -> str:
    return f"skillshift.{sites.get(site).name}.{int(index)}"


class Registry:
    """An immutable view over every task variant in the benchmark."""

    def __init__(self, tasks: tuple[TaskRef, ...]) -> None:
        self._tasks = tasks
        self._by_uid = {task.uid: task for task in tasks}
        self._by_site_version: dict[tuple[str, str], tuple[TaskRef, ...]] = {}
        for site in sites.SITE_NAMES:
            for version in conditions.SITE_VERSIONS:
                self._by_site_version[(site, version)] = tuple(
                    task
                    for task in tasks
                    if task.site == site and task.site_version == version
                )

    def __len__(self) -> int:
        return len(self._tasks)

    def __iter__(self) -> Iterator[TaskRef]:
        return iter(self._tasks)

    def uids(self) -> tuple[str, ...]:
        return tuple(task.uid for task in self._tasks)

    def get(self, uid: str) -> TaskRef:
        """Look up a task by canonical uid."""
        task = self._by_uid.get(str(uid).strip())
        if task is None:
            raise UnknownTaskError(
                f"Unknown task id {uid!r}. Expected a canonical id such as "
                f"'skillshift.gitlab.v1.0'; see data/tasks/id_map.csv."
            )
        return task

    def for_site_version(self, site: str, site_version: str) -> tuple[TaskRef, ...]:
        """Every task of one site in one version, ordered by index."""
        site_name = sites.get(site).name
        version = str(site_version).strip().lower()
        if version not in conditions.SITE_VERSIONS:
            raise UnknownTaskError(
                f"Unknown site_version {site_version!r}. "
                f"Expected one of {list(conditions.SITE_VERSIONS)}."
            )
        return self._by_site_version[(site_name, version)]

    def for_condition(self, site: str, condition: str) -> tuple[TaskRef, ...]:
        """Every task of one site under one condition."""
        spec = conditions.resolve(condition)
        return self.for_site_version(site, spec.site_version)

    def resolve(
        self,
        task_id: str,
        *,
        site: str | None = None,
        condition: str | None = None,
        site_version: str | None = None,
    ) -> TaskRef:
        """Resolve any accepted id form to a task.

        Accepts a canonical uid, a family id, or a deprecated ``myBenchmark.<n>``
        id.  The version comes from `condition` or `site_version` when the id
        does not carry one; when the id does carry one, it must agree.
        """
        raw = str(task_id).strip()
        wanted_version = self._wanted_version(condition, site_version)

        match = _UID_RE.match(raw)
        if match:
            task = self.get(raw)
            if wanted_version is not None and task.site_version != wanted_version:
                raise UnknownTaskError(
                    f"Task id {raw!r} is a {task.site_version} task but the requested "
                    f"condition needs {wanted_version}. Pass the family id "
                    f"{task.family_id!r} to let the condition choose the version."
                )
            return task

        match = _FAMILY_RE.match(raw)
        if match:
            if wanted_version is None:
                raise UnknownTaskError(
                    f"Task id {raw!r} names a task family, which exists in both v1 and v2. "
                    f"Pass --condition (or a full id such as {raw.replace('.', '.v1.', 2)!r})."
                )
            return self._lookup(match["site"], wanted_version, int(match["index"]), raw)

        match = _LEGACY_RE.match(raw)
        if match:
            return self._resolve_legacy(raw, int(match["index"]), site, wanted_version)

        raise UnknownTaskError(
            f"Unrecognized task id {raw!r}. Expected 'skillshift.<site>.<v1|v2>.<index>', "
            f"'skillshift.<site>.<index>', or the deprecated 'myBenchmark.<index>'."
        )

    @staticmethod
    def _wanted_version(condition: str | None, site_version: str | None) -> str | None:
        if condition is not None and site_version is not None:
            resolved = conditions.resolve(condition).site_version
            if resolved != str(site_version).strip().lower():
                raise UnknownTaskError(
                    f"condition={condition!r} implies {resolved} but site_version="
                    f"{site_version!r} was also given."
                )
            return resolved
        if condition is not None:
            return conditions.resolve(condition).site_version
        if site_version is not None:
            return str(site_version).strip().lower()
        return None

    def _resolve_legacy(
        self,
        raw: str,
        index: int,
        site: str | None,
        wanted_version: str | None,
    ) -> TaskRef:
        if site is None:
            raise UnknownTaskError(
                f"Legacy task id {raw!r} needs an explicit site: each site numbers its "
                f"tasks from 0, so {raw!r} names a different task on gitlab, magento and "
                f"wordpress. Pass --site, or use a canonical id such as "
                f"'skillshift.gitlab.v1.{index}'."
            )
        if wanted_version is None:
            raise UnknownTaskError(
                f"Legacy task id {raw!r} needs a condition (or site_version) to choose "
                f"between the v1 and v2 variant."
            )

        site_name = sites.get(site).name
        task = self._lookup(site_name, wanted_version, index, raw)
        warnings.warn(
            f"Task id {raw!r} is deprecated; use {task.uid!r}. "
            f"The mapping is recorded in data/tasks/id_map.csv.",
            DeprecationWarning,
            stacklevel=3,
        )
        return task

    def _lookup(self, site: str, version: str, index: int, raw: str) -> TaskRef:
        site_name = sites.get(site).name
        uid = make_uid(site_name, version, index)
        task = self._by_uid.get(uid)
        if task is None:
            n_tasks = sites.get(site_name).n_tasks
            raise UnknownTaskError(
                f"Task id {raw!r} does not exist: {site_name} has {n_tasks} tasks "
                f"(indices 0-{n_tasks - 1})."
            )
        return task


def _read_tasks(site: str, version: str) -> tuple[TaskRef, ...]:
    rel = _TASK_FILES[(site, version)]
    path = paths.TASKS_DIR / rel
    if not path.is_file():
        raise TaskDataError(
            f"Task file missing: {path}. Rebuild it with scripts/build_task_data.py."
        )

    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskDataError(f"Task file {path} is not valid JSON: {exc}") from exc

    if not isinstance(records, list):
        raise TaskDataError(f"Task file {path} must contain a JSON list, got {type(records).__name__}.")

    expected = sites.get(site).n_tasks
    if len(records) != expected:
        raise TaskDataError(
            f"Task file {path} has {len(records)} tasks, expected {expected}. "
            f"The per-site task counts are the denominators of every leaderboard cell "
            f"and must not drift."
        )

    tasks = []
    for record in records:
        try:
            index = int(record["task_id"])
            intent = str(record["intent"])
            eval_block = record.get("eval") or {}
        except (KeyError, TypeError, ValueError) as exc:
            raise TaskDataError(f"Malformed task record in {path}: {exc}") from exc

        tasks.append(
            TaskRef(
                uid=make_uid(site, version, index),
                family_id=make_family_id(site, index),
                legacy_id=f"myBenchmark.{index}",
                site=site,
                site_version=version,
                index=index,
                intent=intent,
                intent_template_id=record.get("intent_template_id"),
                eval_types=tuple(eval_block.get("eval_types") or ()),
                task_file=rel,
            )
        )

    indices = [task.index for task in tasks]
    if len(set(indices)) != len(indices):
        raise TaskDataError(f"Duplicate task_id values in {path}.")

    return tuple(sorted(tasks, key=lambda task: task.index))


@functools.lru_cache(maxsize=1)
def load_registry() -> Registry:
    """Load and validate every task file.  Cached for the process lifetime."""
    tasks: list[TaskRef] = []
    for site in sites.SITE_NAMES:
        for version in conditions.SITE_VERSIONS:
            tasks.extend(_read_tasks(site, version))

    registry = Registry(tuple(tasks))

    total_per_version = {
        version: sum(len(registry.for_site_version(site, version)) for site in sites.SITE_NAMES)
        for version in conditions.SITE_VERSIONS
    }
    for version, total in total_per_version.items():
        if total != sites.TOTAL_TASKS:
            raise TaskDataError(
                f"Version bundle {version} has {total} tasks, expected {sites.TOTAL_TASKS}."
            )

    return registry


@functools.lru_cache(maxsize=1)
def load_id_map() -> tuple[dict[str, str], ...]:
    """Read `data/tasks/id_map.csv` as an immutable tuple of rows."""
    if not paths.ID_MAP_PATH.is_file():
        raise TaskDataError(
            f"Id map missing: {paths.ID_MAP_PATH}. Rebuild it with scripts/build_task_data.py."
        )
    with paths.ID_MAP_PATH.open(encoding="utf-8", newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))
