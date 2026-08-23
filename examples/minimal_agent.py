"""A complete SkillShift-Bench agent in about fifty lines.

Run it:

    export my_api_key=... my_base_url=... my_model=...
    skillshift run --agent examples.minimal_agent:MinimalSkillAgent \
        --site gitlab --condition tgt-exec --out runs/demo

The only thing this file does beyond a plain ReAct loop is the `with
recorder.call(...)` block: that is what produces Average Skill Calls and Skill
Failure Rate.  Without it your entry has SR and AS on the leaderboard, and two
empty columns.
"""

from skillshift.agents.base import Observation, TaskSpec
from skillshift.agents.events import SkillRecorder

# Stand-in for your own skill library: a name, and something that runs it.
MY_SKILLS = {
    "gitlab.open_issues": 'click("issues-tab")',
    "gitlab.search_repo": 'fill("search", "{query}")',
}


class MinimalSkillAgent:
    """Implements the two methods SkillShift-Bench requires."""

    def reset(self, task: TaskSpec, recorder: SkillRecorder) -> None:
        # Called once per task.  Keep the recorder: it is how skill usage is
        # reported.  `task.condition` tells you which of the six cells you are
        # in, if your method wants to know.
        self.task = task
        self.recorder = recorder
        self.step = 0

    def act(self, obs: Observation) -> str:
        self.step += 1

        skill_id = self.choose_skill(obs)
        if skill_id is None:
            # A primitive action: nothing to report.
            return 'send_msg_to_user("I could not find a way forward.")'

        # A learned-skill invocation.  Report it.
        with self.recorder.call(skill_id) as call:
            action = MY_SKILLS[skill_id]
            if "{query}" in action:
                action = action.replace("{query}", self.task.intent[:40])

            # If you can tell in advance that the skill cannot run here -- its
            # target is missing, the page changed -- say so.  Not calling
            # `fail` means the invocation succeeded; an exception escaping this
            # block also counts as a failure.
            if not self.looks_runnable(action, obs):
                call.fail("target element is not present on this page")
                return 'scroll(0, 400)'

        return action

    def choose_skill(self, obs: Observation) -> str | None:
        """Your method goes here.  This one is a keyword match."""
        goal = obs.goal.lower()
        if "issue" in goal:
            return "gitlab.open_issues"
        if "search" in goal or "find" in goal:
            return "gitlab.search_repo"
        return None

    def looks_runnable(self, action: str, obs: Observation) -> bool:
        """A trivial feasibility check against the accessibility tree."""
        target = action.split('"')[1] if '"' in action else ""
        return target in obs.axtree
