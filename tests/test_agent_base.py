"""The SkillAgent contract.

Whether a third party can plug their own skill method in is what decides
whether this benchmark gets used, so the contract is two methods wide and is
checked eagerly with a message that says what is missing.
"""


from dataclasses import FrozenInstanceError

import pytest

from skillshift.agents.base import Observation, SkillAgent, TaskSpec, check_agent, observation_from
from skillshift.agents.events import SkillRecorder
from skillshift.errors import SkillShiftError


class MinimalAgent:
    def __init__(self):
        self.seen = []

    def reset(self, task, recorder):
        self.task = task
        self.recorder = recorder

    def act(self, obs):
        self.seen.append(obs.step)
        return 'send_msg_to_user("done")'


class TestProtocol:
    def test_a_two_method_class_satisfies_the_protocol(self):
        assert isinstance(MinimalAgent(), SkillAgent)

    def test_check_agent_accepts_a_conforming_agent(self):
        check_agent(MinimalAgent())

    def test_check_agent_names_the_missing_method(self):
        class NoAct:
            def reset(self, task, recorder):
                pass

        with pytest.raises(SkillShiftError) as excinfo:
            check_agent(NoAct())
        assert "act" in str(excinfo.value)

    def test_check_agent_rejects_a_non_callable_attribute(self):
        class Broken:
            reset = 1
            act = 2

        with pytest.raises(SkillShiftError):
            check_agent(Broken())


class TestTaskSpec:
    def test_carries_everything_an_agent_needs_to_condition_on(self):
        spec = TaskSpec(
            uid="skillshift.gitlab.v1.9",
            family_id="skillshift.gitlab.9",
            legacy_id="myBenchmark.9",
            site="gitlab",
            site_version="v1",
            condition="src-exec",
            intent="Check out my todos",
            max_steps=10,
        )
        assert spec.uid.endswith(".9")
        assert spec.condition == "src-exec"

    def test_is_immutable(self):
        spec = TaskSpec(
            uid="u", family_id="f", legacy_id="l", site="gitlab", site_version="v1",
            condition="src", intent="i", max_steps=10,
        )
        with pytest.raises(FrozenInstanceError):
            spec.intent = "other"

    def test_rejects_a_condition_outside_the_six(self):
        with pytest.raises(SkillShiftError):
            TaskSpec(
                uid="u", family_id="f", legacy_id="l", site="gitlab", site_version="v1",
                condition="target", intent="i", max_steps=10,
            )

    def test_rejects_a_condition_that_contradicts_the_site_version(self):
        with pytest.raises(SkillShiftError):
            TaskSpec(
                uid="u", family_id="f", legacy_id="l", site="gitlab", site_version="v2",
                condition="src", intent="i", max_steps=10,
            )

    def test_from_task_ref_builds_a_spec(self):
        from skillshift import registry

        task = registry.load_registry().get("skillshift.magento.v2.3")
        spec = TaskSpec.from_task_ref(task, condition="tgt-perc", max_steps=12)

        assert spec.uid == "skillshift.magento.v2.3"
        assert spec.site == "magento"
        assert spec.condition == "tgt-perc"
        assert spec.max_steps == 12


class TestObservation:
    def test_is_immutable(self):
        obs = Observation(step=0, goal="g", url="http://localhost:8080")
        with pytest.raises(FrozenInstanceError):
            obs.step = 1

    def test_translates_a_browsergym_observation_dict(self):
        raw = {
            "goal_object": [{"type": "text", "text": "Check out my todos"}],
            "open_pages_urls": ["http://localhost:8080/dashboard"],
            "active_page_index": 0,
            "last_action": 'click("42")',
            "last_action_error": "TimeoutError: Timeout 10000ms exceeded.",
            "axtree_txt": "RootWebArea ...",
            "pruned_html": "<html></html>",
            "screenshot": None,
        }
        obs = observation_from(raw, step=3)

        assert obs.step == 3
        assert obs.goal == "Check out my todos"
        assert obs.url == "http://localhost:8080/dashboard"
        assert obs.last_action == 'click("42")'
        assert obs.last_action_error.startswith("TimeoutError")
        assert obs.axtree.startswith("RootWebArea")

    def test_missing_keys_become_safe_defaults_rather_than_crashing(self):
        obs = observation_from({}, step=0)
        assert obs.goal == ""
        assert obs.url is None
        assert obs.axtree == ""


class TestRoundTrip:
    def test_an_agent_can_be_driven_with_a_recorder(self):
        agent = MinimalAgent()
        recorder = SkillRecorder()
        spec = TaskSpec(
            uid="skillshift.gitlab.v1.0", family_id="skillshift.gitlab.0",
            legacy_id="myBenchmark.0", site="gitlab", site_version="v1",
            condition="src", intent="i", max_steps=3,
        )

        agent.reset(spec, recorder)
        for step in range(3):
            action = agent.act(Observation(step=step, goal="i", url=None))
            assert isinstance(action, str)

        assert agent.seen == [0, 1, 2]
        assert recorder.n_calls == 0
