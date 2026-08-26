"""Token-usage reporting from the reference agent's own LLM calls.

Kept separate from test_reference_agent.py, which never touches the real
`openai` client (every test there injects a plain `completion` callable).
This file is specifically about the default completion path, mocked at the
`openai.OpenAI` boundary, and about `ReferenceReActAgent.last_usage` -- the
duck-typed attribute `runner.run_task` reads to attach spend to a trajectory
step. See docs/results-policy.md: this is a local debugging aid, not part of
per_task.jsonl or the receipt.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from skillshift.agents.base import Observation, TaskSpec
from skillshift.agents.events import SkillRecorder
from skillshift.agents.reference import ReferenceReActAgent
from skillshift.eval.trajectory import TokenUsage


def spec():
    return TaskSpec(
        uid="skillshift.gitlab.v1.0",
        family_id="skillshift.gitlab.0",
        legacy_id="myBenchmark.0",
        site="gitlab",
        site_version="v1",
        condition="src",
        intent="Check out my todos",
        max_steps=5,
    )


def obs(step=0, **kwargs):
    defaults = dict(goal="Check out my todos", url="http://localhost:8080", axtree="[1] link 'Todos'")
    defaults.update(kwargs)
    return Observation(step=step, **defaults)


def fake_openai_response(content='click("1")', prompt=8, completion=2, total=10):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total),
    )


class TestCustomCompletionReportsNoUsage:
    def test_last_usage_is_none_before_any_call(self):
        agent = ReferenceReActAgent(completion=lambda messages: 'click("1")')
        assert agent.last_usage is None

    def test_a_hand_supplied_completion_cannot_report_usage(self):
        # It returns a bare string by contract; there is nothing to attach.
        agent = ReferenceReActAgent(completion=lambda messages: 'click("1")')
        agent.reset(spec(), SkillRecorder())
        agent.act(obs())
        assert agent.last_usage is None


class TestDefaultCompletionReportsUsage:
    def test_a_real_api_call_populates_last_usage(self, monkeypatch):
        monkeypatch.setenv("my_api_key", "k")
        monkeypatch.setenv("my_base_url", "http://example.invalid/v1")

        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_: fake_openai_response(prompt=11, completion=4, total=15)
                )
            )
        )
        with patch("openai.OpenAI", return_value=client):
            agent = ReferenceReActAgent(model="test-model")
            agent.reset(spec(), SkillRecorder())
            agent.act(obs())

        assert agent.last_usage == TokenUsage(prompt_tokens=11, completion_tokens=4, total_tokens=15)

    def test_usage_updates_on_every_step(self, monkeypatch):
        monkeypatch.setenv("my_api_key", "k")
        monkeypatch.setenv("my_base_url", "http://example.invalid/v1")

        calls = [
            fake_openai_response(prompt=1, completion=1, total=2),
            fake_openai_response(prompt=5, completion=5, total=10),
        ]
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: calls.pop(0)))
        )
        with patch("openai.OpenAI", return_value=client):
            agent = ReferenceReActAgent(model="test-model")
            agent.reset(spec(), SkillRecorder())
            agent.act(obs(step=0))
            assert agent.last_usage.total_tokens == 2
            agent.act(obs(step=1))
            assert agent.last_usage.total_tokens == 10
