"""The generic run loop, exercised against a fake environment."""

import pytest

from skillshift.agents.base import TaskSpec
from skillshift.errors import SkillShiftError
from skillshift.runner import run_task


class FakeEnv:
    """Minimal stand-in for a browsergym env."""

    def __init__(self, *, reward_at=None, terminate_at=None, n_steps=10):
        self.reward_at = reward_at
        self.terminate_at = terminate_at if terminate_at is not None else n_steps
        self.actions = []
        self.closed = False

    def reset(self):
        return {"goal_object": [{"type": "text", "text": "g"}], "open_pages_urls": ["u"]}, {}

    def step(self, action):
        self.actions.append(action)
        step = len(self.actions)
        reward = 1.0 if step == self.reward_at else 0.0
        terminated = step >= self.terminate_at
        return {"open_pages_urls": ["u"]}, reward, terminated, False, {}

    def close(self):
        self.closed = True


class ScriptedAgent:
    def __init__(self, skills_at=(), fail_skills=False):
        self.skills_at = set(skills_at)
        self.fail_skills = fail_skills
        self.recorder = None
        self.steps = 0

    def reset(self, task, recorder):
        self.recorder = recorder
        self.steps = 0

    def act(self, obs):
        self.steps += 1
        if self.steps in self.skills_at:
            with self.recorder.call("some.skill") as ctx:
                if self.fail_skills:
                    ctx.fail("did not work")
        return 'click("1")'


def spec(condition="src", max_steps=5):
    return TaskSpec(
        uid="skillshift.gitlab.v1.0",
        family_id="skillshift.gitlab.0",
        legacy_id="myBenchmark.0",
        site="gitlab",
        site_version="v1" if condition.startswith("src") else "v2",
        condition=condition,
        intent="i",
        max_steps=max_steps,
    )


class TestOutcome:
    def test_a_positive_reward_is_a_success(self):
        record = run_task(task=spec(), agent=ScriptedAgent(), env=FakeEnv(reward_at=2, terminate_at=2))
        assert record.success is True
        assert record.steps == 2

    def test_termination_without_reward_is_a_failure(self):
        record = run_task(task=spec(), agent=ScriptedAgent(), env=FakeEnv(terminate_at=3))
        assert record.success is False
        assert record.steps == 3

    def test_the_step_budget_truncates_the_episode(self):
        env = FakeEnv(terminate_at=99)
        record = run_task(task=spec(max_steps=4), agent=ScriptedAgent(), env=env)
        assert record.steps == 4
        assert len(env.actions) == 4
        assert record.success is False

    def test_the_record_carries_the_task_and_condition(self):
        record = run_task(task=spec("tgt-exec"), agent=ScriptedAgent(), env=FakeEnv(terminate_at=1))
        assert record.uid == "skillshift.gitlab.v1.0"
        assert record.condition == "tgt-exec"
        assert record.site == "gitlab"

    def test_the_environment_is_always_closed(self):
        env = FakeEnv(terminate_at=1)
        run_task(task=spec(), agent=ScriptedAgent(), env=env)
        assert env.closed is True


class TestSkillCounts:
    def test_skill_calls_are_taken_from_the_recorder(self):
        record = run_task(
            task=spec(), agent=ScriptedAgent(skills_at=(1, 3)), env=FakeEnv(terminate_at=4)
        )
        assert record.skill_calls == 2
        assert record.skill_failures == 0

    def test_failed_skill_calls_are_counted(self):
        record = run_task(
            task=spec(),
            agent=ScriptedAgent(skills_at=(1, 2), fail_skills=True),
            env=FakeEnv(terminate_at=3),
        )
        assert record.skill_calls == 2
        assert record.skill_failures == 2

    def test_an_agent_that_reports_nothing_yields_zero_calls(self):
        record = run_task(task=spec(), agent=ScriptedAgent(), env=FakeEnv(terminate_at=2))
        assert record.skill_calls == 0
        assert record.skill_failures == 0


class TestFailureHandling:
    def test_an_agent_crash_is_recorded_not_swallowed_silently(self):
        class Exploding(ScriptedAgent):
            def act(self, obs):
                raise RuntimeError("model exploded")

        record = run_task(task=spec(), agent=Exploding(), env=FakeEnv(terminate_at=5))

        assert record.success is False
        assert record.error is not None
        assert "model exploded" in record.error

    def test_an_agent_crash_still_closes_the_environment(self):
        class Exploding(ScriptedAgent):
            def act(self, obs):
                raise RuntimeError("boom")

        env = FakeEnv(terminate_at=5)
        run_task(task=spec(), agent=Exploding(), env=env)
        assert env.closed is True

    def test_an_agent_missing_the_interface_fails_before_the_run_starts(self):
        class NotAnAgent:
            pass

        env = FakeEnv(terminate_at=5)
        with pytest.raises(SkillShiftError):
            run_task(task=spec(), agent=NotAnAgent(), env=env)
        assert env.actions == []
