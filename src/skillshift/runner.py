"""The run loop: drive one agent through one task and record the outcome.

Kept independent of browsergym so it can be exercised offline: `run_task` takes
whatever environment object it is given, and `make_browsergym_env` supplies the
real one.  The environment contract is the gymnasium one --
`reset()`, `step(action)`, `close()`.
"""

from __future__ import annotations

import contextlib
import logging
import multiprocessing
import os
import signal
import threading
from collections.abc import Callable, Iterator, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from typing import Any

from . import conditions as conditions_mod
from . import registry as registry_mod
from .agents.base import TaskSpec, check_agent, observation_from
from .agents.events import SkillRecorder
from .errors import SkillShiftError
from .eval.records import TaskRecord

logger = logging.getLogger(__name__)


#: Wall-clock ceiling for one task, in seconds.
#
# Measured on the build machine: a GitLab task parked inside playwright's event
# loop -- main thread idle in `select`, chromium at 0% CPU, the site itself
# answering in 80ms -- and stayed there for eleven hours, because the run loop
# bounded only the number of steps and nothing bounded time.  `calibration.md`
# advertises the whole 180-run sweep as a fifteen-minute check; without a
# deadline a single hung page turns that into an overnight wait with nothing to
# show for it.
#
# 600s is generous next to the ~70-110s a real task took, so it fires on hangs
# rather than on slow pages.
DEFAULT_TASK_TIMEOUT_SECONDS = 600

#: Closing a wedged browser can wedge too, so the teardown gets its own, shorter,
#: ceiling.  A leaked chromium is worth less than a stalled sweep.
CLOSE_TIMEOUT_SECONDS = 60


class TaskTimeout(SkillShiftError):
    """One task exceeded its wall-clock ceiling."""


@contextmanager
def _deadline(seconds: float | None) -> Iterator[None]:
    """Raise `TaskTimeout` in the main thread after `seconds`.

    SIGALRM rather than a watchdog thread, because the thing that needs
    interrupting is a blocking read inside playwright's event loop and a thread
    cannot interrupt that.  Where SIGALRM does not exist, or where this is not
    the main thread, the deadline is skipped rather than faked -- a timeout that
    silently does nothing would be worse than none at all.
    """
    usable = (
        seconds
        and seconds > 0
        and hasattr(signal, "SIGALRM")
        and threading.current_thread() is threading.main_thread()
    )
    if not usable:
        yield
        return

    def _fire(_signum, _frame):
        raise TaskTimeout(
            f"the task exceeded its {seconds:g}s ceiling and was stopped. The run loop "
            f"bounds steps, not time; a browser call that never returns is what this "
            f"catches. Raise it with --task-timeout if a task legitimately needs longer."
        )

    previous = signal.signal(signal.SIGALRM, _fire)
    signal.setitimer(signal.ITIMER_REAL, float(seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, previous)


def run_task(
    *,
    task: TaskSpec,
    agent: Any,
    env: Any,
    timeout: float | None = DEFAULT_TASK_TIMEOUT_SECONDS,
) -> TaskRecord:
    """Run one task to completion and return its record.

    A crash inside the agent or the environment ends that task, not the whole
    run: it is recorded as a failure with the error attached, and logged.  A
    355-task sweep must not be lost to one bad page.
    """
    check_agent(agent)

    recorder = SkillRecorder()
    recorder.reset(task_uid=task.uid, condition=task.condition)

    steps = 0
    success = False
    error: str | None = None

    try:
        with _deadline(timeout):
            raw_obs, _ = env.reset()
            agent.reset(task, recorder)

            while steps < task.max_steps:
                action = agent.act(observation_from(raw_obs, step=steps, page=_page_of(env)))
                raw_obs, reward, terminated, truncated, _ = env.step(action)
                steps += 1

                if reward and float(reward) > 0:
                    success = True
                if terminated or truncated:
                    break

    except Exception as exc:  # noqa: BLE001 - recorded, logged, and reported
        error = f"{type(exc).__name__}: {exc}"
        logger.exception("Task %s failed during execution", task.uid)
    finally:
        with contextlib.suppress(Exception):
            with _deadline(CLOSE_TIMEOUT_SECONDS):
                _close(env)

    return TaskRecord(
        uid=task.uid,
        site=task.site,
        condition=task.condition,
        success=success,
        steps=steps,
        skill_calls=recorder.n_calls,
        skill_failures=recorder.n_failures,
        error=error,
    )


def _page_of(env: Any) -> Any:
    """The live Playwright page, when the environment exposes one."""
    unwrapped = getattr(env, "unwrapped", env)
    return getattr(unwrapped, "page", None)


def _close(env: Any) -> None:
    close = getattr(env, "close", None)
    if not callable(close):
        return
    try:
        close()
    except Exception:  # noqa: BLE001 - closing must never mask the real error
        logger.warning("Closing the environment raised; continuing.", exc_info=True)


#: The upstream `webarena` package asserts all seven of these at *import* time
#: (`webarena.browser_env.env_config`), and `libwebarena` is a hard dependency
#: of browsergym-webarena.  The paper's artifact told users to export them by
#: hand -- four of them meaningless -- and the refactor dropped that from the
#: docs, so every task died in `setup` with "Please setup the URLs to each
#: site".  The harness knows the two that mean something and fills the rest.
WEBARENA_REQUIRED_VARS: tuple[str, ...] = (
    "REDDIT",
    "SHOPPING",
    "SHOPPING_ADMIN",
    "GITLAB",
    "WIKIPEDIA",
    "MAP",
    "HOMEPAGE",
)

#: Deliberately unresolvable, and named so that a value showing up in a log or
#: a trace is recognisable as a placeholder rather than a site someone forgot
#: to start.  SkillShift-Bench evaluates GitLab, Magento and WordPress only.
WEBARENA_UNUSED_URL = "http://unused-by-skillshift.invalid"

#: Which SkillShift environment variable backs each webarena one, per version.
WEBARENA_SITE_SOURCES: Mapping[str, str] = {
    "GITLAB": "GITLAB",
    "SHOPPING_ADMIN": "SHOPPING_ADMIN",
}


def webarena_env(version: str) -> dict[str, str]:
    """Values for webarena's seven variables, for one site version."""
    values = {name: WEBARENA_UNUSED_URL for name in WEBARENA_REQUIRED_VARS}
    for target, prefix in WEBARENA_SITE_SOURCES.items():
        # Absent is not fatal: `skillshift env status` is the command that
        # reports an unconfigured site, and entering the context must not be
        # the thing that raises.
        values[target] = os.environ.get(f"{prefix}_{version.upper()}") or WEBARENA_UNUSED_URL
    return values


@contextmanager
def condition_environment(site: str, condition: str) -> Iterator[dict[str, str]]:
    """Temporarily set the environment variables for one cell, then restore."""
    values = dict(conditions_mod.to_env(site=site, condition=condition))
    values.update(webarena_env(conditions_mod.resolve(condition).site_version))
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield values
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def make_browsergym_env(task_uid: str, *, headless: bool = True, max_steps: int = 10) -> Any:
    """Create the browsergym environment for one task.

    Imported lazily: the aggregation and validation path must stay installable
    without playwright.
    """
    try:
        import gymnasium as gym

        from .tasks.registration import register_tasks
    except ImportError as exc:
        raise SkillShiftError(
            "Running tasks needs the browser stack: pip install 'skillshift-bench[run]'"
        ) from exc

    register_tasks()
    return gym.make(
        f"browsergym/{task_uid}",
        headless=headless,
        max_episode_steps=max_steps,
        wait_for_user_message=False,
    )


def _run_one_task_in_worker(
    *,
    agent_spec: str,
    site: str,
    condition: str,
    task_uid: str,
    max_steps: int,
    headless: bool,
    timeout: float | None,
) -> TaskRecord:
    """`--workers>1` entry point: run exactly one task in a fresh subprocess.

    Takes only picklable primitives and rebuilds everything else (the task,
    the agent, the browser) from scratch inside the worker. A worker process
    is spawned, not forked: forking after a sibling worker has already opened
    a browser would copy that worker's live Playwright connection into the
    child, corrupting both. Spawning always starts a clean interpreter, so
    `browsergym`/`playwright` are imported here for the first time and
    `_deadline`'s SIGALRM lands on this process's only -- and therefore
    main -- thread, exactly as it does in the serial path.
    """
    from .agents import load_agent_factory

    task_ref = registry_mod.load_registry().resolve(task_uid, site=site, condition=condition)
    task = TaskSpec.from_task_ref(task_ref, condition=condition, max_steps=max_steps)
    agent = load_agent_factory(agent_spec)()
    env = make_browsergym_env(task.uid, headless=headless, max_steps=max_steps)
    return run_task(task=task, agent=agent, env=env, timeout=timeout)


def run_condition(
    *,
    site: str,
    condition: str,
    agent_factory: Callable[[], Any],
    task_uids: Sequence[str] | None = None,
    max_steps: int = 10,
    headless: bool = True,
    env_factory: Callable[..., Any] | None = None,
    on_record: Callable[[TaskRecord], None] | None = None,
    timeout: float | None = DEFAULT_TASK_TIMEOUT_SECONDS,
    workers: int = 1,
    agent_spec: str | None = None,
) -> tuple[TaskRecord, ...]:
    """Run every task of one site under one condition.

    Records are handed to `on_record` as they are produced, so a long sweep can
    be written to disk incrementally rather than lost on interruption.

    `workers` parallelises the tasks *within* this one (site, condition) cell
    only -- never across cells or across environments, since a whole other
    environment does not fit in memory next to this one, and WordPress's v1/v2
    share a single instance (a theme swap, not a second deployment). Each
    worker gets its own subprocess and its own browser; nothing about the
    tasks is guaranteed independent on the site side, so two workers hitting
    the same GitLab or Magento instance at once can race if the tasks happen
    to write overlapping state. That trade-off is the caller's to make.
    """
    if workers < 1:
        raise SkillShiftError(f"workers must be at least 1, got {workers}.")

    spec = conditions_mod.resolve(condition)
    reg = registry_mod.load_registry()

    if task_uids is None:
        tasks = reg.for_condition(site, spec.name)
    else:
        tasks = tuple(reg.resolve(uid, site=site, condition=spec.name) for uid in task_uids)

    if workers > 1:
        if env_factory is not None:
            raise SkillShiftError(
                "workers>1 runs each task in its own subprocess, so a custom "
                "env_factory (which is typically a closure) cannot be sent "
                "along -- it is not picklable. Use workers=1 with a custom "
                "env_factory, e.g. in tests."
            )
        if not agent_spec:
            raise SkillShiftError(
                "workers>1 needs agent_spec (the same string passed to "
                "--agent) so each worker subprocess can rebuild the agent "
                "itself; an already-built agent_factory cannot be sent to a "
                "subprocess."
            )

    make_env = env_factory or make_browsergym_env
    task_specs = [
        TaskSpec.from_task_ref(task_ref, condition=spec.name, max_steps=max_steps)
        for task_ref in tasks
    ]

    with condition_environment(site, spec.name):
        if workers <= 1:
            records: list[TaskRecord] = []
            for task in task_specs:
                env = make_env(task.uid, headless=headless, max_steps=max_steps)
                record = run_task(task=task, agent=agent_factory(), env=env, timeout=timeout)
                records.append(record)
                if on_record is not None:
                    on_record(record)
            return tuple(records)

        results: list[TaskRecord | None] = [None] * len(task_specs)
        mp_context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=workers, mp_context=mp_context) as pool:
            future_to_index = {
                pool.submit(
                    _run_one_task_in_worker,
                    agent_spec=agent_spec,
                    site=site,
                    condition=spec.name,
                    task_uid=task.uid,
                    max_steps=max_steps,
                    headless=headless,
                    timeout=timeout,
                ): index
                for index, task in enumerate(task_specs)
            }
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                task = task_specs[index]
                try:
                    record = future.result()
                except Exception as exc:  # noqa: BLE001 - a worker crash is one failed task
                    logger.exception("Task %s failed inside a worker subprocess", task.uid)
                    record = TaskRecord(
                        uid=task.uid,
                        site=site,
                        condition=spec.name,
                        success=False,
                        steps=0,
                        skill_calls=0,
                        skill_failures=0,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                results[index] = record
                if on_record is not None:
                    on_record(record)

        return tuple(results)
