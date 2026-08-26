"""A no-skill ReAct agent: the calibration anchor.

Why it exists
-------------
The paper compares four learned-skill methods (AWM, ASI, SkillWeaver, WALT).
All four carry a skill library, so none of them tells you what this benchmark
looks like *without* one.  Someone running SkillShift-Bench for the first time
therefore has no way to tell "my method is weak" from "my GitLab image is the
wrong version".  This agent supplies that reading: it uses only the primitive
action set, reports no skill calls at all, and its numbers on the calibration
subset are published in `data/reference_results/`.

It is deliberately plain -- observation in, one action out, bounded history.  It
is not a competitive method and does not appear on the leaderboard.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..errors import SkillShiftError
from ..eval.trajectory import TokenUsage
from .base import Action, Observation, TaskSpec
from .events import SkillRecorder

DEFAULT_MAX_HISTORY = 5

#: The primitive action set the agent is told about.  No induced skills.
PRIMITIVE_ACTIONS = (
    'click(bid)                       e.g. click("42")',
    'fill(bid, value)                 e.g. fill("7", "hello")',
    'hover(bid)',
    'select_option(bid, option)',
    'keyboard_press(key_comb)         e.g. keyboard_press("Enter")',
    'scroll(dx, dy)',
    'goto(url)',
    'go_back()  /  go_forward()',
    'new_tab()  /  tab_focus(index)  /  tab_close()',
    'send_msg_to_user(text)           use this to answer the task',
    'report_infeasible(reason)        use this if the task cannot be done',
)

SYSTEM_PROMPT = """You are a web agent operating a browser through a fixed action space.

Available actions:
{actions}

Rules:
- Reply with a short reason, then the single next action in a fenced code block.
- Use only the actions listed above, with element ids taken from the accessibility tree.
- When you have the answer the task asks for, send it with send_msg_to_user(...).
"""

_FENCE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def extract_action(text: str) -> Action:
    """Pull the action out of a model reply.

    Prefers a fenced code block; otherwise takes the last non-empty line.  An
    empty reply raises rather than sending a blank action, which the environment
    would report as an opaque execution error.
    """
    match = _FENCE_RE.search(text or "")
    if match:
        action = match.group(1).strip()
        if action:
            return action

    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        raise SkillShiftError(
            "The model returned no action. Expected an action in a fenced code block, "
            "e.g. ```\\nclick(\"42\")\\n```"
        )
    return lines[-1]


@dataclass(frozen=True)
class _Turn:
    step: int
    action: str
    error: str


def _default_completion(
    model: str,
    temperature: float,
    *,
    on_usage: Callable[[TokenUsage | None], None] | None = None,
) -> Callable[[Sequence[Mapping[str, Any]]], str]:
    """Build an OpenAI-compatible chat completion callable.

    Reads the same environment variables as the rest of the harness
    (`my_api_key`, `my_base_url`, `my_model`), so a user configures the model in
    one place. `on_usage`, when given, is called with the response's token
    usage right after each real call -- a hand-supplied `completion` callable
    has no such hook, since its contract is a bare string return.
    """

    def completion(messages: Sequence[Mapping[str, Any]]) -> str:
        try:
            import openai
        except ImportError as exc:  # pragma: no cover - depends on the extra
            raise ImportError(
                "The reference agent needs an OpenAI-compatible client: "
                "pip install 'skillshift-bench[run]'"
            ) from exc

        client = openai.OpenAI(
            api_key=os.getenv("my_api_key"),
            base_url=os.getenv("my_base_url"),
        )
        response = client.chat.completions.create(
            model=model,
            messages=list(messages),
            temperature=temperature,
        )
        if on_usage is not None:
            usage = getattr(response, "usage", None)
            on_usage(
                TokenUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                )
                if usage is not None
                else None
            )
        return response.choices[0].message.content or ""

    return completion


class ReferenceReActAgent:
    """No-skill ReAct baseline. Implements `SkillAgent`."""

    def __init__(
        self,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_history: int = DEFAULT_MAX_HISTORY,
        completion: Callable[[Sequence[Mapping[str, Any]]], str] | None = None,
    ) -> None:
        self.model = model or os.getenv("my_model") or "gpt-5-mini-2025-08-07"
        self.temperature = temperature
        self.max_history = max(1, int(max_history))
        #: The last call's token usage, or `None` if the call did not report
        #: one (a hand-supplied `completion` never does). Read by
        #: `runner.run_task` -- see docs/results-policy.md for why this is
        #: local-debugging-only and never part of a task's outcome.
        self.last_usage: TokenUsage | None = None
        self._completion = completion or _default_completion(
            self.model, temperature, on_usage=self._set_last_usage
        )
        self._task: TaskSpec | None = None
        self._recorder: SkillRecorder | None = None
        self._history: list[_Turn] = []

    def _set_last_usage(self, usage: TokenUsage | None) -> None:
        self.last_usage = usage

    @property
    def history(self) -> tuple[_Turn, ...]:
        return tuple(self._history)

    def reset(self, task: TaskSpec, recorder: SkillRecorder) -> None:
        self._task = task
        # The recorder is kept for interface symmetry only: this agent invokes
        # no learned skills, so it never calls `recorder.call`.  That is exactly
        # what makes it an anchor -- its ASC is 0 by construction.
        self._recorder = recorder
        self._history = []

    def act(self, obs: Observation) -> Action:
        if self._task is None:
            raise SkillShiftError(
                "ReferenceReActAgent.act() was called before reset(). The harness calls "
                "reset(task, recorder) once per task."
            )

        reply = self._completion(self._build_messages(obs))
        action = extract_action(reply)

        self._history.append(_Turn(step=obs.step, action=action, error=obs.last_action_error))
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]

        return action

    def _build_messages(self, obs: Observation) -> list[dict]:
        parts = [
            f"# Goal\n{obs.goal or (self._task.intent if self._task else '')}",
            f"# Current URL\n{obs.url or '(unknown)'}",
        ]

        if self._history:
            lines = [
                f"step {turn.step}: {turn.action}"
                + (f"  -> ERROR: {turn.error}" if turn.error else "")
                for turn in self._history
            ]
            parts.append("# Recent actions\n" + "\n".join(lines))

        if obs.last_action_error:
            parts.append(f"# Last action error\n{obs.last_action_error}")

        if obs.axtree:
            parts.append(f"# Accessibility tree\n{obs.axtree}")
        elif obs.html:
            parts.append(f"# HTML\n{obs.html}")

        return [
            {"role": "system", "content": SYSTEM_PROMPT.format(actions="\n".join(PRIMITIVE_ACTIONS))},
            {"role": "user", "content": "\n\n".join(parts)},
        ]
