"""Agents: the SkillAgent contract, skill-call reporting, and the built-ins.

Built-in agents are looked up lazily so that importing this package does not
pull in the browser stack.
"""

from __future__ import annotations

from collections.abc import Callable

from ..errors import SkillShiftError

#: Built-in agent names accepted by `skillshift run --agent`.
BUILTIN_AGENTS: tuple[str, ...] = ("reference", "mpcr")


def load_agent(name: str, **kwargs):
    """Instantiate a built-in agent by name."""
    key = str(name).strip().lower()

    if key == "reference":
        from .reference import ReferenceReActAgent

        return ReferenceReActAgent(**kwargs)

    if key == "mpcr":
        raise SkillShiftError(
            "MPCR does not yet run through the SkillAgent interface: its Mask stage "
            "probes the live page during action selection, which the generic runner "
            "does not expose yet. Use its own entry point meanwhile:\n"
            "    python -m skillshift.agents.mpcr.run_single_task --task_name <uid>\n"
            "See docs/custom-agent.md."
        )

    raise SkillShiftError(
        f"Unknown agent {name!r}. Built-in agents: {list(BUILTIN_AGENTS)}. "
        f"To run your own, pass a 'module:Factory' path; see docs/custom-agent.md."
    )


def load_agent_factory(spec: str) -> Callable[[], object]:
    """Resolve `--agent` into a zero-argument factory.

    Accepts a built-in name, or a `module:attribute` path pointing at a class or
    a factory function.
    """
    text = str(spec).strip()

    if ":" not in text:
        return lambda: load_agent(text)

    module_name, _, attribute = text.partition(":")
    import importlib

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise SkillShiftError(
            f"Could not import {module_name!r} for --agent {spec!r}: {exc}"
        ) from exc

    factory = getattr(module, attribute, None)
    if factory is None:
        raise SkillShiftError(f"{module_name!r} has no attribute {attribute!r}.")
    if not callable(factory):
        raise SkillShiftError(f"{spec!r} is not callable.")

    return factory
