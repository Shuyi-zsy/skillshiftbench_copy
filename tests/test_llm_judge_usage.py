"""Token-usage accounting for the LLM judge.

Only `drain_usage()` is under test here -- `judge()`/`judge_unachievable()`'s
scoring behavior is exercised elsewhere (test_evaluators.py). This file checks
that every real API call's usage is captured exactly once and that draining
clears it, since a stale value leaking into the next task's trajectory would
misattribute spend.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from skillshift.eval import llm_judge


def fake_response(content="VERDICT: CORRECT", prompt=10, completion=4, total=14, usage=True):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)
        if usage
        else None,
    )


class TestDrainUsage:
    def setup_method(self):
        llm_judge.drain_usage()  # clear any residue from another test

    def test_starts_empty(self):
        assert llm_judge.drain_usage() == ()

    def test_a_judged_call_is_recorded(self, monkeypatch):
        monkeypatch.setenv("my_api_key", "k")
        monkeypatch.setenv("my_base_url", "http://example.invalid/v1")
        monkeypatch.setenv("my_model", "test-model")
        llm_judge._client = None  # force a fresh client for this env

        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **_: fake_response(prompt=7, completion=3, total=10))
            )
        )
        with patch("openai.OpenAI", return_value=client):
            score = llm_judge.judge("intent", ["gold"], "gold", mode="exact")

        assert score == 1.0
        usages = llm_judge.drain_usage()
        assert len(usages) == 1
        assert usages[0].prompt_tokens == 7
        assert usages[0].completion_tokens == 3
        assert usages[0].total_tokens == 10

    def test_draining_clears_it(self, monkeypatch):
        monkeypatch.setenv("my_api_key", "k")
        monkeypatch.setenv("my_base_url", "http://example.invalid/v1")
        monkeypatch.setenv("my_model", "test-model")
        llm_judge._client = None

        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: fake_response()))
        )
        with patch("openai.OpenAI", return_value=client):
            llm_judge.judge("intent", ["gold"], "gold", mode="exact")

        assert len(llm_judge.drain_usage()) == 1
        assert llm_judge.drain_usage() == ()

    def test_a_response_without_usage_is_skipped_not_crashed(self, monkeypatch):
        monkeypatch.setenv("my_api_key", "k")
        monkeypatch.setenv("my_base_url", "http://example.invalid/v1")
        monkeypatch.setenv("my_model", "test-model")
        llm_judge._client = None

        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **_: fake_response(usage=False))
            )
        )
        with patch("openai.OpenAI", return_value=client):
            llm_judge.judge("intent", ["gold"], "gold", mode="exact")

        assert llm_judge.drain_usage() == ()

    def teardown_method(self):
        llm_judge._client = None
        llm_judge._model = None
        llm_judge.drain_usage()
