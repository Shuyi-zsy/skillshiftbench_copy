"""The reference agent is the calibration anchor.

The paper has no no-skill baseline: all four compared methods carry a skill
library.  Without an anchor, someone running this benchmark for the first time
cannot tell a badly configured environment from a genuinely weak method.  This
agent is that anchor, so its behaviour is pinned by tests rather than left to
whatever the model says.
"""

import pytest

from skillshift.agents.base import Observation, TaskSpec, check_agent
from skillshift.agents.events import SkillRecorder
from skillshift.agents.reference import ReferenceReActAgent, extract_action
from skillshift.errors import SkillShiftError


def spec(condition="src"):
    return TaskSpec(
        uid="skillshift.gitlab.v1.0",
        family_id="skillshift.gitlab.0",
        legacy_id="myBenchmark.0",
        site="gitlab",
        site_version="v1" if condition.startswith("src") else "v2",
        condition=condition,
        intent="Check out my todos",
        max_steps=5,
    )


def obs(step=0, **kwargs):
    defaults = dict(goal="Check out my todos", url="http://localhost:8080", axtree="[1] link 'Todos'")
    defaults.update(kwargs)
    return Observation(step=step, **defaults)


class TestActionExtraction:
    def test_takes_the_fenced_code_block(self):
        assert extract_action('I will click.\n```\nclick("42")\n```') == 'click("42")'

    def test_takes_a_python_tagged_fence(self):
        assert extract_action('```python\nfill("7", "hello")\n```') == 'fill("7", "hello")'

    def test_falls_back_to_the_last_non_empty_line(self):
        assert extract_action("thinking...\nclick(\"42\")\n\n") == 'click("42")'

    def test_keeps_a_multiline_fenced_action(self):
        action = extract_action('```\nclick("1")\nclick("2")\n```')
        assert action == 'click("1")\nclick("2")'

    def test_empty_output_raises_rather_than_sending_a_blank_action(self):
        with pytest.raises(SkillShiftError):
            extract_action("   \n\n")


class TestAgent:
    def test_satisfies_the_skill_agent_interface(self):
        check_agent(ReferenceReActAgent(completion=lambda messages: 'click("1")'))

    def test_returns_the_action_the_model_produced(self):
        agent = ReferenceReActAgent(completion=lambda messages: '```\nclick("42")\n```')
        agent.reset(spec(), SkillRecorder())
        assert agent.act(obs()) == 'click("42")'

    def test_never_reports_a_skill_call(self):
        # This is the point of the reference agent: ASC is exactly 0 and SFR is
        # undefined, which is the anchor every other number is read against.
        recorder = SkillRecorder()
        agent = ReferenceReActAgent(completion=lambda messages: 'click("1")')
        agent.reset(spec(), recorder)
        for step in range(3):
            agent.act(obs(step))

        assert recorder.n_calls == 0
        assert recorder.events() == ()

    def test_prompt_states_the_goal_and_the_observation(self):
        seen = {}

        def completion(messages):
            seen["messages"] = messages
            return 'click("1")'

        agent = ReferenceReActAgent(completion=completion)
        agent.reset(spec(), SkillRecorder())
        agent.act(obs(axtree="[1] link 'Todos'"))

        text = "\n".join(str(message["content"]) for message in seen["messages"])
        assert "Check out my todos" in text
        assert "[1] link 'Todos'" in text

    def test_prompt_offers_no_skill_library(self):
        seen = {}

        def completion(messages):
            seen["messages"] = messages
            return 'click("1")'

        agent = ReferenceReActAgent(completion=completion)
        agent.reset(spec(), SkillRecorder())
        agent.act(obs())

        text = "\n".join(str(message["content"]) for message in seen["messages"]).lower()
        assert "skill" not in text.replace("skillshift", "")

    def test_history_is_bounded(self):
        agent = ReferenceReActAgent(
            completion=lambda messages: 'click("1")', max_history=2
        )
        agent.reset(spec(), SkillRecorder())
        for step in range(6):
            agent.act(obs(step, last_action='click("1")'))

        assert len(agent.history) == 2

    def test_reset_clears_history_between_tasks(self):
        agent = ReferenceReActAgent(completion=lambda messages: 'click("1")')
        agent.reset(spec(), SkillRecorder())
        agent.act(obs())
        agent.reset(spec("tgt"), SkillRecorder())

        assert agent.history == ()

    def test_a_model_error_is_surfaced_not_swallowed(self):
        def completion(messages):
            raise RuntimeError("api down")

        agent = ReferenceReActAgent(completion=completion)
        agent.reset(spec(), SkillRecorder())
        with pytest.raises(RuntimeError, match="api down"):
            agent.act(obs())

    def test_acting_before_reset_is_rejected(self):
        agent = ReferenceReActAgent(completion=lambda messages: 'click("1")')
        with pytest.raises(SkillShiftError):
            agent.act(obs())

    def test_last_action_error_is_shown_to_the_model(self):
        seen = {}

        def completion(messages):
            seen["messages"] = messages
            return 'click("1")'

        agent = ReferenceReActAgent(completion=completion)
        agent.reset(spec(), SkillRecorder())
        agent.act(obs(last_action='click("9")', last_action_error="TimeoutError: Timeout"))

        text = "\n".join(str(message["content"]) for message in seen["messages"])
        assert "TimeoutError" in text
