"""Optional, local-only per-step trajectory and token-usage logging.

This is *not* `per_task.jsonl` (see `records.py`) and never feeds the run
receipt: `docs/results-policy.md` forbids publishing per-task judgements and
traces, but it never said the harness cannot produce them locally for
debugging. `.gitignore` already reserves `trajectories/` for exactly this.
Enabled with `--save-trajectories`; off by default so a normal run's disk
footprint and output-directory contents are unchanged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class TokenUsage:
    """One chat-completion call's token accounting."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(frozen=True)
class StepTrace:
    """One step of one task: what the agent saw, did, and spent."""

    uid: str
    step: int
    url: str | None
    action: str
    action_error: str
    reward: float
    terminated: bool
    truncated: bool
    axtree: str = ""
    html: str = ""
    #: The acting agent's own LLM call for this step, when it reports one.
    agent_usage: TokenUsage | None = None
    #: Any LLM-judge calls the evaluator made while scoring this step (only
    #: non-empty on the step that ends the task).
    judge_usage: tuple[TokenUsage, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "step": self.step,
            "url": self.url,
            "action": self.action,
            "action_error": self.action_error,
            "reward": self.reward,
            "terminated": self.terminated,
            "truncated": self.truncated,
            "axtree": self.axtree,
            "html": self.html,
            "agent_usage": self.agent_usage.to_dict() if self.agent_usage else None,
            "judge_usage": [usage.to_dict() for usage in self.judge_usage],
        }


class TrajectoryWriter:
    """Appends one JSON line per step to `path`, flushing immediately.

    A step is written as it happens rather than buffered for one final write,
    so a task that hangs or crashes mid-run still leaves the steps it did
    reach on disk instead of losing all of them to an unflushed buffer.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, trace: StepTrace) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(trace.to_dict(), ensure_ascii=False) + "\n")
            handle.flush()
