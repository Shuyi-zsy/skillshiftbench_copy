"""Turning executed actions into skill-call events.

MPCR inherits ASI's skill format: an induced skill is a Python function in
`actions/{gitlab,admin,wordpress}.py`, registered as a callable high-level
action next to the primitives.  So an invocation is exactly a call to one of
those names in the code the environment executes, and it can be detected
without asking the method to instrument itself.

An action that raised marks every skill it invoked as failed -- the paper counts
runtime errors as skill failures (Section 2.4).
"""

from __future__ import annotations

import ast
from typing import Collection

from ..events import SkillRecorder

#: Modules whose functions are treated as learned skills.  `webarena` and
#: `general` hold the primitive action set and are deliberately excluded.
SKILL_MODULES: tuple[str, ...] = ("gitlab", "admin", "wordpress", "shopping", "reddit", "map")


def skills_in_action(code: str | None, skill_names: Collection[str]) -> tuple[str, ...]:
    """Names of the learned skills invoked by one action string, in order.

    Returns an empty tuple for a primitive action, an empty action, or code that
    does not parse -- a malformed action is already an execution error and must
    not also break the metric path.
    """
    if not code or not skill_names:
        return ()

    try:
        tree = ast.parse(str(code))
    except SyntaxError:
        return ()

    names = set(skill_names)

    # `ast.walk` does not preserve source order, so sort by position: a
    # multiaction should read left to right.
    calls = [
        (node.lineno, node.col_offset, node.func.id)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in names
    ]
    calls.sort()
    return tuple(name for _, _, name in calls)


def record_action(
    recorder: SkillRecorder | None,
    *,
    code: str | None,
    skill_names: Collection[str],
    error: str | None,
) -> tuple[str, ...]:
    """Record the skill invocations of one executed action.

    Called after execution, so the outcome is already known.  A missing recorder
    is a no-op, which keeps the harness usable with agents that do not report
    skills at all.
    """
    called = skills_in_action(code, skill_names)
    if recorder is None:
        return called

    for name in called:
        with recorder.call(name) as context:
            if error:
                context.fail(str(error))
    return called


def induced_skill_names(websites: Collection[str]) -> frozenset[str]:
    """Every induced skill name available for the given websites.

    Imports the action modules lazily: they pull in browsergym, which the
    aggregation path does not need.
    """
    from .actions import ACTION_DICT

    names: set[str] = set()
    for website in websites:
        key = str(website).strip().lower()
        if key not in SKILL_MODULES:
            continue
        for function in ACTION_DICT.get(key, ()):
            names.add(function.__name__)
    return frozenset(names)
