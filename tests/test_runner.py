"""The generic run loop, exercised against a fake environment."""

import os
import signal
import time

import pytest

from skillshift import runner
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


class TestWebArenaEnvironmentVariables:
    """The upstream `webarena` package asserts seven URLs at *import* time.

    `libwebarena` -> `webarena.browser_env.env_config` raises
    "Please setup the URLs to each site" unless REDDIT, SHOPPING,
    SHOPPING_ADMIN, GITLAB, WIKIPEDIA, MAP and HOMEPAGE are all non-empty.
    The paper's artifact told users to export all seven by hand, four of them
    meaningless placeholders; the refactor dropped that from the docs and
    nothing supplied them, so every task died at setup.

    The harness already knows the URLs, so it fills them itself.
    """

    def test_all_seven_are_set_inside_the_context(self, monkeypatch):
        for name in runner.WEBARENA_REQUIRED_VARS:
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("GITLAB_V1", "http://localhost:8080")
        monkeypatch.setenv("SHOPPING_ADMIN_V1", "http://dockerized-magento.local/admin")

        with runner.condition_environment("wordpress", "src"):
            for name in runner.WEBARENA_REQUIRED_VARS:
                assert os.environ.get(name), f"{name} is empty; webarena asserts on it"

    def test_the_two_it_actually_knows_carry_the_real_urls(self, monkeypatch):
        monkeypatch.setenv("GITLAB_V1", "http://localhost:8080")
        monkeypatch.setenv("GITLAB_V2", "http://localhost:8081")
        monkeypatch.setenv("SHOPPING_ADMIN_V1", "http://dockerized-magento.local/admin")
        monkeypatch.setenv("SHOPPING_ADMIN_V2", "http://localhost:7780/admin")

        with runner.condition_environment("gitlab", "src"):
            assert os.environ["GITLAB"] == "http://localhost:8080"
            assert os.environ["SHOPPING_ADMIN"] == "http://dockerized-magento.local/admin"
        with runner.condition_environment("gitlab", "tgt-exec"):
            assert os.environ["GITLAB"] == "http://localhost:8081"
            assert os.environ["SHOPPING_ADMIN"] == "http://localhost:7780/admin"

    def test_the_four_this_benchmark_does_not_use_say_so(self, monkeypatch):
        monkeypatch.setenv("GITLAB_V1", "http://localhost:8080")
        monkeypatch.setenv("SHOPPING_ADMIN_V1", "http://x/admin")
        with runner.condition_environment("wordpress", "src"):
            for name in ("REDDIT", "WIKIPEDIA", "MAP", "HOMEPAGE"):
                assert "skillshift" in os.environ[name], (
                    f"{name} should be an obviously inert placeholder, not a plausible URL"
                )

    def test_the_previous_values_are_restored(self, monkeypatch):
        monkeypatch.setenv("GITLAB", "http://someone-elses-value")
        monkeypatch.setenv("GITLAB_V1", "http://localhost:8080")
        monkeypatch.setenv("SHOPPING_ADMIN_V1", "http://x/admin")
        with runner.condition_environment("wordpress", "src"):
            pass
        assert os.environ["GITLAB"] == "http://someone-elses-value"

    def test_a_missing_site_url_does_not_crash_the_context(self, monkeypatch):
        """`env status` reports unconfigured sites; entering a context must not raise."""
        for name in ("GITLAB_V1", "GITLAB_V2", "SHOPPING_ADMIN_V1", "SHOPPING_ADMIN_V2"):
            monkeypatch.delenv(name, raising=False)
        with runner.condition_environment("wordpress", "src"):
            assert os.environ["GITLAB"]


class TestTaskDeadline:
    """One hung page must not cost the whole sweep.

    Measured: a GitLab task parked inside playwright's event loop -- main
    thread idle in `select`, chromium at 0% CPU, the site answering in 80ms --
    and stayed there for eleven hours. `run_task` looped on `steps <
    max_steps` with no wall-clock bound of any kind, so nothing was ever going
    to end it. `calibration.md` promises the whole run takes about fifteen
    minutes; a stranger would have left it overnight, as this run did.

    A task that runs out of time is recorded as an error, not as a plain
    failure: it is the absence of a measurement, and `build_reference_anchor`
    refuses a sweep containing one rather than folding a hang into an anchor.
    """

    def hanging_env(self, seconds=30):
        class HangingEnv:
            closed = False

            def reset(self):
                time.sleep(seconds)
                return {}, {}

            def step(self, action):
                time.sleep(seconds)
                return {}, 0, False, False, {}

            def close(self):
                HangingEnv.closed = True

        return HangingEnv()

    def test_a_hanging_task_ends_and_is_recorded_as_an_error(self):
        record = runner.run_task(
            task=spec(max_steps=10),
            agent=ScriptedAgent(),
            env=self.hanging_env(),
            timeout=1,
        )
        assert record.error is not None
        assert "timeout" in record.error.lower() or "TaskTimeout" in record.error
        assert record.success is False

    def test_it_really_stops_rather_than_waiting_out_the_env(self):
        started = time.monotonic()
        runner.run_task(
            task=spec(max_steps=10),
            agent=ScriptedAgent(),
            env=self.hanging_env(seconds=30),
            timeout=1,
        )
        assert time.monotonic() - started < 20, "the deadline did not interrupt the blocked call"

    def test_a_task_that_finishes_in_time_is_untouched(self):
        record = runner.run_task(
            task=spec(max_steps=2),
            agent=ScriptedAgent(),
            env=FakeEnv(reward_at=1, terminate_at=2),
            timeout=60,
        )
        assert record.error is None
        assert record.success is True

    def test_no_timeout_means_no_alarm_is_left_armed(self):
        runner.run_task(
            task=spec(max_steps=1),
            agent=ScriptedAgent(),
            env=FakeEnv(reward_at=1, terminate_at=1),
            timeout=None,
        )
        assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
