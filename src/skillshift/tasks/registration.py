"""Registering SkillShift-Bench tasks with browsergym.

Two id families are registered:

``skillshift.<site>.<v1|v2>.<index>``
    The canonical id.  It carries its own site and version, so the task does not
    depend on which environment variables happen to be set.

``myBenchmark.<n>``
    The id the artifact used, kept working because it is printed in the
    artifact's own README.  It is *not* self-describing: each site numbers its
    tasks from zero, so which task ``myBenchmark.9`` means depends on the
    ``website`` environment variable.  It is registered for indices 0..161 --
    the largest site -- and instantiating one emits a ``DeprecationWarning``.
"""

from __future__ import annotations

import functools
import warnings

from browsergym.core.registration import register_task

from .. import conditions, registry, sites
from .task import GenericMyBenchmarkTask

#: Every canonical gym id, populated by `register_tasks`.
ALL_TASK_IDS: list[str] = []

#: Every legacy gym id, populated by `register_tasks`.
ALL_LEGACY_TASK_IDS: list[str] = []


class LegacyMyBenchmarkTask(GenericMyBenchmarkTask):
    """`myBenchmark.<n>`: resolves its site from the environment, and says so."""

    def __init__(self, *args, **kwargs) -> None:
        task_id = kwargs.get("task_id")
        warnings.warn(
            f"Task id 'myBenchmark.{task_id}' is deprecated and depends on the ambient "
            f"`website` environment variable. Use a canonical id such as "
            f"'skillshift.gitlab.v1.{task_id}'; see data/tasks/id_map.csv.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


@functools.lru_cache(maxsize=1)
def register_tasks() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Register every task with browsergym.  Idempotent."""
    reg = registry.load_registry()

    for task in reg:
        register_task(
            task.uid,
            GenericMyBenchmarkTask,
            task_kwargs={
                "task_id": task.index,
                "website": task.site,
                "site_version": task.site_version,
            },
        )
        ALL_TASK_IDS.append(task.uid)

    largest_site = max(site.n_tasks for site in sites.all_sites())
    for index in range(largest_site):
        gym_id = f"myBenchmark.{index}"
        register_task(gym_id, LegacyMyBenchmarkTask, task_kwargs={"task_id": index})
        ALL_LEGACY_TASK_IDS.append(gym_id)

    return tuple(ALL_TASK_IDS), tuple(ALL_LEGACY_TASK_IDS)


def gym_id_for(task_uid: str, condition: str) -> str:
    """The gym id to run for one task under one condition.

    A canonical uid already fixes the version, so the condition only has to agree
    with it; the shift flags are applied through the environment.
    """
    task = registry.load_registry().resolve(task_uid, condition=condition)
    conditions.resolve(condition)
    return task.uid
