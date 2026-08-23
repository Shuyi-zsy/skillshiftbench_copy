"""Detecting learned-skill invocations inside an executed action string.

MPCR's skill library is the set of induced Python functions in
`agents/mpcr/actions/*.py`; they are registered as callable high-level actions
alongside the primitive ones.  An invocation is therefore mechanically
detectable: it is a call to one of those names in the action the environment
executes.  That is what makes ASC and SFR computable for MPCR without asking
the method to instrument itself.
"""

import pytest

from skillshift.agents.mpcr.skill_tracking import skills_in_action

SKILLS = frozenset({"search_project", "fork_project", "submit_issue"})


class TestDetection:
    def test_a_primitive_action_is_not_a_skill_call(self):
        assert skills_in_action('click("42")', SKILLS) == ()

    def test_a_skill_call_is_detected_by_name(self):
        assert skills_in_action("search_project('238', '2019-nCov')", SKILLS) == ("search_project",)

    def test_multiaction_records_each_skill_in_order(self):
        code = "click('1')\nsearch_project('2', 'x')\nfork_project('3', '4', '5')"
        assert skills_in_action(code, SKILLS) == ("search_project", "fork_project")

    def test_the_same_skill_twice_counts_twice(self):
        code = "search_project('1', 'a')\nsearch_project('2', 'b')"
        assert skills_in_action(code, SKILLS) == ("search_project", "search_project")

    def test_a_skill_name_appearing_as_a_string_is_not_a_call(self):
        assert skills_in_action('send_msg_to_user("search_project")', SKILLS) == ()

    def test_a_skill_name_used_as_a_variable_is_not_a_call(self):
        assert skills_in_action("x = search_project", SKILLS) == ()

    def test_unparsable_code_yields_no_calls_rather_than_raising(self):
        # A malformed action is already an execution error; it must not also
        # crash the metric path.
        assert skills_in_action("click(", SKILLS) == ()

    def test_empty_action_yields_no_calls(self):
        assert skills_in_action("", SKILLS) == ()
        assert skills_in_action(None, SKILLS) == ()

    def test_an_empty_skill_set_detects_nothing(self):
        assert skills_in_action("search_project('1','a')", frozenset()) == ()

    def test_a_skill_called_inside_another_call_is_still_detected(self):
        assert skills_in_action("print(search_project('1','a'))", SKILLS) == ("search_project",)


class TestRecordingIntegration:
    def test_a_failed_action_marks_every_skill_it_invoked_as_failed(self):
        from skillshift.agents.events import SkillRecorder
        from skillshift.agents.mpcr.skill_tracking import record_action

        recorder = SkillRecorder()
        record_action(
            recorder,
            code="search_project('1', 'a')",
            skill_names=SKILLS,
            error="TimeoutError: Timeout 10000ms exceeded.",
        )

        assert recorder.n_calls == 1
        assert recorder.n_failures == 1
        assert "TimeoutError" in recorder.events()[0].reason

    def test_a_clean_action_marks_its_skills_as_successful(self):
        from skillshift.agents.events import SkillRecorder
        from skillshift.agents.mpcr.skill_tracking import record_action

        recorder = SkillRecorder()
        record_action(recorder, code="search_project('1', 'a')", skill_names=SKILLS, error="")

        assert recorder.n_calls == 1
        assert recorder.n_failures == 0

    def test_a_primitive_action_records_nothing(self):
        from skillshift.agents.events import SkillRecorder
        from skillshift.agents.mpcr.skill_tracking import record_action

        recorder = SkillRecorder()
        record_action(recorder, code='click("42")', skill_names=SKILLS, error="")

        assert recorder.n_calls == 0

    def test_a_missing_recorder_is_a_no_op(self):
        from skillshift.agents.mpcr.skill_tracking import record_action

        record_action(None, code="search_project('1','a')", skill_names=SKILLS, error="")


class TestSkillNames:
    def test_reads_the_induced_skill_names_from_the_action_modules(self):
        pytest.importorskip("browsergym")
        from skillshift.agents.mpcr.skill_tracking import induced_skill_names

        names = induced_skill_names(["gitlab"])
        assert "search_project" in names
        assert "click" not in names
