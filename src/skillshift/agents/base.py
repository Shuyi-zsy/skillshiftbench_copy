"""The SkillAgent contract.

Two methods.  That is the whole interface a third party has to implement to run
their own learned-skill method on all six conditions::

    class MyAgent:
        def reset(self, task: TaskSpec, recorder: SkillRecorder) -> None: ...
        def act(self, obs: Observation) -> Action: ...

`reset` receives the task and a fresh `SkillRecorder`; the agent keeps the
recorder and wraps each learned-skill invocation in `with recorder.call(...)`,
which is what produces ASC and SFR.  `act` returns a browsergym action string.

See `docs/custom-agent.md` for a worked example, and
`examples/minimal_agent.py` for a runnable one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ..conditions import resolve as resolve_condition
from ..errors import SkillShiftError
from .events import SkillRecorder

#: An action is a browsergym action string, e.g. ``click("42")``.
Action = str

DEFAULT_MAX_STEPS = 10


@dataclass(frozen=True)
class TaskSpec:
    """Everything an agent may condition on, and nothing it should not.

    Notably it carries the condition name, so an agent can tell a source run
    from a target run -- but not the evaluator or the reference answer.
    """

    uid: str
    family_id: str
    legacy_id: str
    site: str
    site_version: str
    condition: str
    intent: str
    max_steps: int = DEFAULT_MAX_STEPS
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            spec = resolve_condition(self.condition)
        except SkillShiftError as exc:
            raise SkillShiftError(f"TaskSpec {self.uid!r}: {exc}") from exc

        if spec.site_version != self.site_version:
            raise SkillShiftError(
                f"TaskSpec {self.uid!r}: condition {self.condition!r} runs on "
                f"{spec.site_version} but the task is a {self.site_version} task."
            )
        if self.max_steps < 1:
            raise SkillShiftError(f"TaskSpec {self.uid!r}: max_steps must be at least 1.")

    @classmethod
    def from_task_ref(cls, task_ref, *, condition: str, max_steps: int = DEFAULT_MAX_STEPS) -> TaskSpec:
        """Build a spec from a `registry.TaskRef`."""
        return cls(
            uid=task_ref.uid,
            family_id=task_ref.family_id,
            legacy_id=task_ref.legacy_id,
            site=task_ref.site,
            site_version=task_ref.site_version,
            condition=resolve_condition(condition).name,
            intent=task_ref.intent,
            max_steps=max_steps,
            metadata={"intent_template_id": task_ref.intent_template_id},
        )


@dataclass(frozen=True)
class Observation:
    """One step's view of the browser.

    A thin, stable rename of the browsergym observation, so that an agent
    written against this interface does not break when the underlying
    observation dict changes shape.
    """

    step: int
    goal: str
    url: str | None
    axtree: str = ""
    html: str = ""
    screenshot: Any = None
    last_action: str = ""
    last_action_error: str = ""
    open_pages_urls: tuple[str, ...] = ()
    active_page_index: int = 0
    raw: Mapping[str, Any] = field(default_factory=dict)
    #: Live Playwright page, when the harness can supply one.  Methods that
    #: probe current feasibility -- MPCR's Mask stage, for instance -- need it;
    #: methods that work from the accessibility tree alone can ignore it.  It is
    #: `None` in offline tests and when the harness runs without a browser.
    page: Any = None


def _goal_text(raw: Mapping[str, Any]) -> str:
    goal = raw.get("goal_object")
    if isinstance(goal, str):
        return goal
    if isinstance(goal, (list, tuple)):
        return "\n".join(
            str(part.get("text", "")) for part in goal if isinstance(part, Mapping)
        ).strip()
    return str(raw.get("goal", "") or "")


def _as_index(value: Any, default: int = 0) -> int:
    """Coerce browsergym's `active_page_index` to an int.

    It arrives as a one-element numpy array (`np.asarray([pages.index(page)])`),
    and numpy >= 2 refuses `int()` on anything with `ndim > 0`. Unwrapping by
    length rather than importing numpy keeps the core install free of it -- the
    array only lives in the `run` extra, but this module is imported by the
    aggregation path too.

    Anything unusable falls back to `default` instead of raising: a partial
    observation is normal on an error page, and losing a whole task to one is
    what this function exists to prevent.
    """
    if value is None:
        return default
    while hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
        if len(value) == 0:
            return default
        value = value[0]
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _flatten_axtree(raw: Mapping[str, Any]) -> str:
    """Render browsergym's raw `axtree_object` the way `mpcr/agent.py` does.

    browsergym's own observation never carries a flattened `axtree_txt` --
    only the structured `axtree_object`. Every agent that consumes it has to
    flatten it itself; skip this and `Observation.axtree` is silently always
    empty, which is indistinguishable from "the page has no content" to an
    agent that never sees a page.
    """
    text = raw.get("axtree_txt")
    if text:
        return str(text)

    axtree_object = raw.get("axtree_object")
    if not axtree_object:
        return ""

    from browsergym.utils.obs import flatten_axtree_to_str

    return flatten_axtree_to_str(axtree_object)


def _flatten_html(raw: Mapping[str, Any]) -> str:
    """Render browsergym's raw `dom_object` the way `mpcr/agent.py` does."""
    text = raw.get("pruned_html")
    if text:
        return str(text)

    dom_object = raw.get("dom_object")
    if not dom_object:
        return ""

    from browsergym.utils.obs import flatten_dom_to_str, prune_html

    return prune_html(flatten_dom_to_str(dom_object))


def observation_from(raw: Mapping[str, Any], *, step: int, page: Any = None) -> Observation:
    """Translate a browsergym observation dict into an `Observation`.

    Missing keys become empty defaults rather than raising: a partial
    observation is a normal occurrence at the first step and on error pages.
    """
    urls = tuple(str(url) for url in (raw.get("open_pages_urls") or ()))
    index = _as_index(raw.get("active_page_index"))
    url = urls[index] if 0 <= index < len(urls) else (urls[0] if urls else None)

    return Observation(
        step=int(step),
        goal=_goal_text(raw),
        url=url,
        axtree=_flatten_axtree(raw),
        html=_flatten_html(raw),
        screenshot=raw.get("screenshot"),
        last_action=str(raw.get("last_action") or ""),
        last_action_error=str(raw.get("last_action_error") or ""),
        open_pages_urls=urls,
        active_page_index=index,
        raw=dict(raw),
        page=page,
    )


@runtime_checkable
class SkillAgent(Protocol):
    """The interface every agent evaluated on SkillShift-Bench implements."""

    def reset(self, task: TaskSpec, recorder: SkillRecorder) -> None:
        """Prepare for a new task and keep the recorder for skill reporting."""

    def act(self, obs: Observation) -> Action:
        """Return the next action as a browsergym action string."""


def check_agent(agent: Any) -> None:
    """Fail fast, and say what is missing.

    Called before a run starts, so that a typo in a method name surfaces
    immediately instead of forty steps into the first task.
    """
    missing = []
    for name in ("reset", "act"):
        attribute = getattr(agent, name, None)
        if attribute is None:
            missing.append(f"{name}() is not defined")
        elif not callable(attribute):
            missing.append(f"{name} is {type(attribute).__name__}, not a method")

    if missing:
        raise SkillShiftError(
            f"{type(agent).__name__} does not implement the SkillAgent interface: "
            + "; ".join(missing)
            + ". It needs reset(task, recorder) and act(obs) -> str; see docs/custom-agent.md."
        )
