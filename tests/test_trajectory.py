"""`eval.trajectory`: the local-only, per-step debug log.

Governed by docs/results-policy.md -- this is a *different* file from
per_task.jsonl (tested in test_records.py) and never touches the receipt.
"""

from __future__ import annotations

import json

from skillshift.eval.trajectory import StepTrace, TokenUsage, TrajectoryWriter


def usage(prompt=10, completion=5, total=15) -> TokenUsage:
    return TokenUsage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)


def trace(**overrides) -> StepTrace:
    fields = dict(
        uid="skillshift.wordpress.v1.0",
        step=0,
        url="http://localhost:8000/",
        action='click("42")',
        action_error="",
        reward=0.0,
        terminated=False,
        truncated=False,
        axtree="[42] button 'Submit'",
        html="<button>Submit</button>",
        agent_usage=None,
        judge_usage=(),
    )
    fields.update(overrides)
    return StepTrace(**fields)


class TestTokenUsage:
    def test_round_trips_through_a_dict(self):
        u = usage(prompt=11, completion=22, total=33)
        assert u.to_dict() == {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33}


class TestStepTraceSerialization:
    def test_a_step_with_no_usage_serializes_usage_as_null(self):
        payload = trace().to_dict()
        assert payload["agent_usage"] is None
        assert payload["judge_usage"] == []

    def test_agent_usage_is_embedded_as_a_dict(self):
        payload = trace(agent_usage=usage(1, 2, 3)).to_dict()
        assert payload["agent_usage"] == {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}

    def test_judge_usage_is_a_list_of_dicts_one_per_call(self):
        payload = trace(judge_usage=(usage(1, 1, 2), usage(3, 3, 6))).to_dict()
        assert payload["judge_usage"] == [
            {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            {"prompt_tokens": 3, "completion_tokens": 3, "total_tokens": 6},
        ]

    def test_carries_the_fields_a_debugging_session_needs(self):
        payload = trace(
            uid="skillshift.wordpress.v1.65",
            step=3,
            url="http://localhost:8000/?p=487",
            action="send_msg_to_user(\"No\")",
            action_error="",
            reward=0.0,
            terminated=True,
            truncated=False,
            axtree="[1] image 'Getty Images ...'",
            html="<img alt='Getty Images ...'>",
        ).to_dict()
        assert payload["uid"] == "skillshift.wordpress.v1.65"
        assert payload["step"] == 3
        assert payload["url"] == "http://localhost:8000/?p=487"
        assert payload["action"] == 'send_msg_to_user("No")'
        assert payload["terminated"] is True
        assert "Getty Images" in payload["axtree"]
        assert "Getty Images" in payload["html"]


class TestTrajectoryWriter:
    def test_creates_the_parent_directory(self, tmp_path):
        path = tmp_path / "trajectories" / "skillshift.wordpress.v1.0.jsonl"
        TrajectoryWriter(path)
        assert path.parent.is_dir()

    def test_each_write_appends_one_json_line(self, tmp_path):
        path = tmp_path / "t.jsonl"
        writer = TrajectoryWriter(path)
        writer.write(trace(step=0))
        writer.write(trace(step=1))

        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["step"] == 0
        assert json.loads(lines[1])["step"] == 1

    def test_writes_are_valid_utf8_json_even_with_non_ascii_content(self, tmp_path):
        path = tmp_path / "t.jsonl"
        writer = TrajectoryWriter(path)
        writer.write(trace(html="<p>你好</p>"))

        line = path.read_text(encoding="utf-8").splitlines()[0]
        assert json.loads(line)["html"] == "<p>你好</p>"
