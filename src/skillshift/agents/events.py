"""Skill-call reporting -- the only source of ASC and SFR.

Why this exists
---------------
Average Skill Calls and Skill Failure Rate depend on something the harness
cannot observe from outside: whether the agent considered a given action to be
an invocation of a learned skill.  The released artifact had no instrumentation
for this at all, so two of the paper's four metrics were not computable by
anyone who downloaded it.  This module is the fix.

Using it
--------
An agent wraps each learned-skill invocation in one `with` statement::

    with recorder.call("gitlab.create_issue") as ctx:
        run_the_skill()
        if not it_worked:
            ctx.fail("submit button never became enabled")

Not calling `fail` means the invocation succeeded.  An exception escaping the
block also counts as a failure, matching the paper's definition of SFR ("with
runtime errors counted as skill failures").

An agent that uses no learned skills -- the reference ReAct agent, for instance
-- simply never calls `call`.  Its ASC is then exactly 0 and its SFR is
undefined rather than zero.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from types import TracebackType

from ..errors import SkillRecordingError


class SkillCallOutcome(str, Enum):
    """How a skill invocation ended."""

    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True)
class SkillCallEvent:
    """One completed skill invocation."""

    skill_id: str
    outcome: SkillCallOutcome
    reason: str | None
    task_uid: str | None
    condition: str | None
    index: int


class SkillCallContext:
    """Handle yielded by `SkillRecorder.call`; use it to mark a failure."""

    def __init__(self, skill_id: str) -> None:
        self.skill_id = skill_id
        self._failed = False
        self._reason: str | None = None

    @property
    def failed(self) -> bool:
        return self._failed

    @property
    def reason(self) -> str | None:
        return self._reason

    def fail(self, reason: str | None = None) -> None:
        """Mark this invocation as failed.

        Calling it more than once is harmless: the invocation is already
        failed, and the first reason is kept as the closest one to the cause.
        """
        if self._failed:
            return
        self._failed = True
        self._reason = reason


class _CallScope:
    """Context manager returned by `SkillRecorder.call`."""

    def __init__(self, recorder: SkillRecorder, skill_id: str) -> None:
        self._recorder = recorder
        self._context = SkillCallContext(skill_id)

    def __enter__(self) -> SkillCallContext:
        self._recorder._open(self._context)
        return self._context

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc_type is not None:
            self._context.fail(f"{exc_type.__name__}: {exc}")
        self._recorder._close(self._context)
        return False  # never swallow the agent's exception


class SkillRecorder:
    """Collects skill invocations for one task.

    The harness creates one recorder per task, hands it to the agent through
    `SkillAgent.reset`, and reads the counts back when the task ends.
    """

    def __init__(self) -> None:
        self._events: list[SkillCallEvent] = []
        self._open_context: SkillCallContext | None = None
        self._task_uid: str | None = None
        self._condition: str | None = None

    # -- agent-facing -----------------------------------------------------

    def call(self, skill_id: str) -> _CallScope:
        """Record one invocation of a learned skill."""
        name = str(skill_id).strip()
        if not name:
            raise SkillRecordingError(
                "A skill call needs a non-empty skill id; it is what the leaderboard "
                "shows when a method's skills are broken down."
            )
        return _CallScope(self, name)

    # -- harness-facing ---------------------------------------------------

    def reset(self, *, task_uid: str | None = None, condition: str | None = None) -> None:
        """Start recording a new task, discarding the previous one's events."""
        if self._open_context is not None:
            raise SkillRecordingError(
                f"Cannot reset while a skill call is open "
                f"({self._open_context.skill_id!r}). Close the `with` block first."
            )
        self._events = []
        self._task_uid = task_uid
        self._condition = condition

    @property
    def task_uid(self) -> str | None:
        return self._task_uid

    @property
    def condition(self) -> str | None:
        return self._condition

    @property
    def n_calls(self) -> int:
        """Numerator of ASC for this task."""
        return len(self._events)

    @property
    def n_failures(self) -> int:
        """Numerator of SFR for this task."""
        return sum(1 for event in self._events if event.outcome is SkillCallOutcome.FAILURE)

    def events(self) -> tuple[SkillCallEvent, ...]:
        """An immutable snapshot of the recorded invocations."""
        return tuple(self._events)

    def calls_by_skill(self) -> dict[str, int]:
        """Invocation count per skill id."""
        return dict(Counter(event.skill_id for event in self._events))

    # -- internal ---------------------------------------------------------

    def _open(self, context: SkillCallContext) -> None:
        if self._open_context is not None:
            raise SkillRecordingError(
                f"Skill call {context.skill_id!r} was opened inside {self._open_context.skill_id!r}. "
                f"ASC counts invocations, so a skill that internally uses another skill is "
                f"still one invocation; record only the outermost one."
            )
        self._open_context = context

    def _close(self, context: SkillCallContext) -> None:
        self._open_context = None
        self._events.append(
            SkillCallEvent(
                skill_id=context.skill_id,
                outcome=SkillCallOutcome.FAILURE if context.failed else SkillCallOutcome.SUCCESS,
                reason=context.reason,
                task_uid=self._task_uid,
                condition=self._condition,
                index=len(self._events),
            )
        )
