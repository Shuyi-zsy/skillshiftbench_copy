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
import ast
import json

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

# SYSTEM_PROMPT = """You are a web agent operating a browser through a fixed action space.

# Available actions:
# {actions}

# Rules:
# - Choose exactly ONE browser action per response.
# - Give a short reason, followed by one fenced code block.
# - Use ```python for the code block.
# - The code block must contain exactly one valid Python function call.
# - Always quote string arguments with single or double quotes.
# - For URLs, write goto("https://example.com/path"), never goto(https://example.com/path).
# - Use only the available browser actions.
# - Use element IDs from the current accessibility tree.
# - Do not invent element IDs.
# - Do not output multiple actions or explanatory comments inside the code block.
# - When the task asks for an answer, use send_msg_to_user(...).
# """



_FENCE_RE = re.compile(r"```(.*?)```", re.DOTALL)
_LANGUAGE_RE = re.compile(
    r"^(?:python|py|action|browsergym|json)(?:\s+|$)",
    re.IGNORECASE,
)
_BARE_URL_RE = re.compile(
    r"^goto\(\s*(https?://[^\s'\"()]+)\s*\)$"
)

_ALLOWED_ACTIONS = {
    "click",
    "fill",
    "hover",
    "select_option",
    "keyboard_press",
    "scroll",
    "goto",
    "go_back",
    "go_forward",
    "new_tab",
    "tab_focus",
    "tab_close",
    "send_msg_to_user",
    "report_infeasible",
}


def _normalize_action(candidate: str) -> str:
    """Normalize and validate one BrowserGym action."""
    candidate = candidate.strip().rstrip(";").strip()

    # Repair only an unquoted HTTP(S) URL in goto(...).
    match = _BARE_URL_RE.fullmatch(candidate)
    if match:
        candidate = f"goto({match.group(1)!r})"

    try:
        tree = ast.parse(candidate, mode="exec")
    except SyntaxError as exc:
        raise SkillShiftError(
            f"Invalid action syntax: {candidate!r}"
        ) from exc

    # Exactly one top-level function call is allowed.
    if len(tree.body) != 1:
        raise SkillShiftError("Expected exactly one action")

    statement = tree.body[0]
    if not isinstance(statement, ast.Expr):
        raise SkillShiftError("Expected a function call")

    call = statement.value
    if not isinstance(call, ast.Call):
        raise SkillShiftError("Expected a function call")

    if not isinstance(call.func, ast.Name):
        raise SkillShiftError("Unsupported action expression")

    if call.func.id not in _ALLOWED_ACTIONS:
        raise SkillShiftError(
            f"Unknown browser action: {call.func.id}"
        )

    # Reject nested function calls, attribute access,
    # assignments and other executable expressions.
    for argument in [*call.args, *(kw.value for kw in call.keywords)]:
        for node in ast.walk(argument):
            if isinstance(
                node,
                (
                    ast.Call,
                    ast.Attribute,
                    ast.Lambda,
                    ast.NamedExpr,
                    ast.Await,
                    ast.Yield,
                    ast.YieldFrom,
                    ast.ListComp,
                    ast.SetComp,
                    ast.DictComp,
                    ast.GeneratorExp,
                ),
            ):
                raise SkillShiftError(
                    "Complex expressions are not valid action arguments"
                )

    # Return a valid Python action, never execute it here.
    return candidate


def _json_to_action(text: str) -> str:
    """Convert a JSON action object to a BrowserGym action."""

    data = json.loads(text)

    if not isinstance(data, dict):
        raise SkillShiftError("JSON action must be an object")

    name = data.get("action")

    if not isinstance(name, str):
        raise SkillShiftError("JSON action name must be a string")

    # Start with the actions relevant to the current failure.
    if name == "click":
        bid = data.get("bid")
        if not isinstance(bid, (str, int)):
            raise SkillShiftError("click requires a bid")
        return f"click({str(bid)!r})"

    if name == "goto":
        url = data.get("url")
        if not isinstance(url, str):
            raise SkillShiftError("goto requires a URL")
        if not url.startswith(("http://", "https://")):
            raise SkillShiftError("goto requires an HTTP(S) URL")
        return f"goto({url!r})"

    if name == "fill":
        bid = data.get("bid")
        value = data.get("value")
        if not isinstance(bid, (str, int)):
            raise SkillShiftError("fill requires a bid")
        if not isinstance(value, str):
            raise SkillShiftError("fill requires a string value")
        return f"fill({str(bid)!r}, {value!r})"

    if name == "scroll":
        dx = data.get("dx")
        dy = data.get("dy")
        if not all(
            isinstance(v, (int, float)) and not isinstance(v, bool)
            for v in (dx, dy)
        ):
            raise SkillShiftError("scroll requires numeric dx and dy")
        return f"scroll({dx!r}, {dy!r})"

    raise SkillShiftError(f"Unsupported JSON action: {name!r}")


def _parse_candidate(candidate: str) -> str:
    candidate = candidate.strip()

    if candidate.startswith("{"):
        try:
            converted = _json_to_action(candidate)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise SkillShiftError(
                f"Invalid JSON action: {exc}"
            ) from exc
        return _normalize_action(converted)

    return _normalize_action(candidate)



def extract_action(text: str) -> Action:
    """Extract one valid action from a model response."""
    if not text or not text.strip():
        raise SkillShiftError("The model returned an empty reply")

    candidates = []

    # Prefer fenced code blocks.
    for match in _FENCE_RE.finditer(text):
        body = match.group(1).strip()

        # Strip optional language marker:
        # ```python, ```action, ```browsergym, etc.
        body = _LANGUAGE_RE.sub("", body, count=1).strip()

        if body:
            candidates.append(body)

    # Fallback for models that omit code fences.
    if not candidates:
        for line in reversed(text.splitlines()):
            line = line.strip()
            if re.match(
                r"^[a-zA-Z_]\w*\s*\(",
                line,
            ):
                candidates.append(line)

    errors = []
    for candidate in candidates:
        try:
            return _parse_candidate(candidate)
        except SkillShiftError as exc:
            errors.append(str(exc))

    raise SkillShiftError(
    "No valid browser action found in model response.\n"
    f"Candidate count: {len(candidates)}\n"
    f"Errors: {errors[:3]!r}\n"
    f"Candidate previews: {[c[:200] for c in candidates[:3]]!r}"
)



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
        print("\n========== RAW MODEL REPLY ==========")
        print(repr(reply))
        print("=====================================\n")

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
