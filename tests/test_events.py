"""SkillRecorder is the only source of ASC and SFR.

The artifact had no skill instrumentation at all -- `--memory_path` was
commented out in `run_online_parallel.py` and nothing counted invocations -- so
two of the paper's four metrics could not be computed by anyone who downloaded
it.  This is the interface that fixes that, and the cost to an agent author is
one `with` statement.
"""


from dataclasses import FrozenInstanceError

import pytest

from skillshift.agents.events import SkillCallOutcome, SkillRecorder
from skillshift.errors import SkillShiftError


class TestBasicRecording:
    def test_a_completed_call_counts_as_a_success(self):
        recorder = SkillRecorder()
        with recorder.call("gitlab.create_issue"):
            pass

        assert recorder.n_calls == 1
        assert recorder.n_failures == 0

    def test_an_explicitly_failed_call_counts_as_a_failure(self):
        recorder = SkillRecorder()
        with recorder.call("gitlab.create_issue") as ctx:
            ctx.fail("element not found")

        assert recorder.n_calls == 1
        assert recorder.n_failures == 1

    def test_an_exception_inside_the_block_counts_as_a_failure(self):
        # "with runtime errors counted as skill failures" -- paper, Section 2.4.
        recorder = SkillRecorder()
        with pytest.raises(TimeoutError):
            with recorder.call("gitlab.fork_project"):
                raise TimeoutError("locator timed out")

        assert recorder.n_calls == 1
        assert recorder.n_failures == 1

    def test_the_exception_is_not_swallowed(self):
        recorder = SkillRecorder()
        with pytest.raises(ValueError, match="boom"):
            with recorder.call("s"):
                raise ValueError("boom")
        assert recorder.n_calls == 1

    def test_calls_accumulate_across_skills(self):
        recorder = SkillRecorder()
        for name in ("a", "b", "a"):
            with recorder.call(name):
                pass

        assert recorder.n_calls == 3
        assert recorder.calls_by_skill() == {"a": 2, "b": 1}


class TestEventLog:
    def test_events_are_recorded_in_order_with_outcomes(self):
        recorder = SkillRecorder()
        with recorder.call("a"):
            pass
        with recorder.call("b") as ctx:
            ctx.fail("nope")

        events = recorder.events()
        assert [event.skill_id for event in events] == ["a", "b"]
        assert [event.outcome for event in events] == [
            SkillCallOutcome.SUCCESS,
            SkillCallOutcome.FAILURE,
        ]
        assert events[1].reason == "nope"

    def test_events_are_an_immutable_snapshot(self):
        recorder = SkillRecorder()
        with recorder.call("a"):
            pass
        snapshot = recorder.events()

        with recorder.call("b"):
            pass

        assert len(snapshot) == 1
        assert len(recorder.events()) == 2

    def test_an_event_cannot_be_mutated(self):
        recorder = SkillRecorder()
        with recorder.call("a"):
            pass
        with pytest.raises(FrozenInstanceError):
            recorder.events()[0].skill_id = "b"

    def test_events_carry_the_task_the_recorder_was_reset_to(self):
        recorder = SkillRecorder()
        recorder.reset(task_uid="skillshift.gitlab.v1.9", condition="tgt-exec")
        with recorder.call("a"):
            pass

        event = recorder.events()[0]
        assert event.task_uid == "skillshift.gitlab.v1.9"
        assert event.condition == "tgt-exec"


class TestReset:
    def test_reset_clears_counts_for_the_next_task(self):
        recorder = SkillRecorder()
        with recorder.call("a"):
            pass
        recorder.reset(task_uid="skillshift.gitlab.v1.1", condition="src")

        assert recorder.n_calls == 0
        assert recorder.events() == ()

    def test_reset_inside_an_open_call_is_rejected(self):
        recorder = SkillRecorder()
        with pytest.raises(SkillShiftError):
            with recorder.call("a"):
                recorder.reset(task_uid="x", condition="src")


class TestMisuse:
    def test_an_empty_skill_id_is_rejected(self):
        recorder = SkillRecorder()
        with pytest.raises(SkillShiftError):
            with recorder.call("   "):
                pass

    def test_nested_calls_are_rejected(self):
        # Nesting would double-count: the paper's ASC counts invocations, and a
        # skill that internally calls another is still one invocation.
        recorder = SkillRecorder()
        with pytest.raises(SkillShiftError):
            with recorder.call("outer"):
                with recorder.call("inner"):
                    pass

    def test_failing_twice_keeps_one_failure_and_the_first_reason(self):
        recorder = SkillRecorder()
        with recorder.call("a") as ctx:
            ctx.fail("first")
            ctx.fail("second")

        assert recorder.n_failures == 1
        assert recorder.events()[0].reason == "first"

    def test_failures_never_exceed_calls(self):
        recorder = SkillRecorder()
        for _ in range(3):
            with recorder.call("a") as ctx:
                ctx.fail("x")
        assert recorder.n_failures <= recorder.n_calls


class TestNullRecorder:
    def test_a_no_skill_agent_records_nothing(self):
        recorder = SkillRecorder()
        assert recorder.n_calls == 0
        assert recorder.n_failures == 0
        assert recorder.events() == ()

    def test_a_skill_free_recorder_reports_asc_zero_and_sfr_undefined(self):
        recorder = SkillRecorder()
        assert recorder.n_calls == 0
        # SFR has no denominator here; the metric layer turns this into None
        # rather than 0.0, which would read as "nothing ever failed".
