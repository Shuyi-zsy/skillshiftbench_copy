# Running your own method on SkillShift-Bench

**Target: fifteen minutes from reading this to a run on all six conditions.**

You implement two methods. Everything else — task loading, shift injection,
scoring, aggregation, the leaderboard file — is done for you.

```python
class MyAgent:
    def reset(self, task: TaskSpec, recorder: SkillRecorder) -> None: ...
    def act(self, obs: Observation) -> str: ...
```

---

## 1. The smallest thing that works

```python
# my_agent.py
from skillshift.agents.base import Observation, TaskSpec
from skillshift.agents.events import SkillRecorder


class MyAgent:
    def reset(self, task: TaskSpec, recorder: SkillRecorder) -> None:
        self.task = task
        self.recorder = recorder

    def act(self, obs: Observation) -> str:
        return 'send_msg_to_user("N/A")'
```

```bash
skillshift run --agent my_agent:MyAgent --site gitlab --condition src --tasks skillshift.gitlab.v1.0
```

`--agent` takes `module:attribute`, where the attribute is a class or any
zero-argument factory. If it does not import, you get an error naming the
module — not a traceback forty steps into the run.

---

## 2. Reporting skill usage — the part that matters

Two of the four diagnostics, **Average Skill Calls** and **Skill Failure Rate**,
describe something the harness cannot see from outside: whether *you* considered
an action to be an invocation of a learned skill. So you report it, with one
`with` statement:

```python
with self.recorder.call("gitlab.create_issue") as call:
    result = self.skills["gitlab.create_issue"].run(page)
    if not result.ok:
        call.fail("submit button never became enabled")
```

Rules, all of them:

- **Not calling `fail` means the invocation succeeded.** The common path costs
  you nothing.
- **An exception escaping the block counts as a failure**, and is re-raised
  unchanged. The paper counts runtime errors as skill failures.
- **Do not nest calls.** ASC counts invocations; a skill that internally uses
  another skill is still one invocation. Nesting raises.
- **Report at the point of invocation, not of retrieval.** Retrieving a skill
  and then deciding not to run it is not a call.

If your method uses no learned skills, never call `recorder.call`. Your ASC is
then exactly `0` and your SFR is `null` — not `0`, which would claim that
nothing ever failed. That is what the built-in reference agent does.

---

## 3. What you get in `reset`

```python
TaskSpec(
    uid="skillshift.gitlab.v1.9",     # canonical id
    family_id="skillshift.gitlab.9",  # same task, both contexts
    legacy_id="myBenchmark.9",        # the artifact's id
    site="gitlab",                    # gitlab | magento | wordpress
    site_version="v1",                # v1 = source, v2 = target
    condition="src-exec",             # one of the six
    intent="Check out my todos",
    max_steps=10,
)
```

`condition` is there on purpose: a method may legitimately behave differently
when it knows a shift is active. You do **not** get the evaluator or the
reference answer.

## 4. What you get in `act`

```python
Observation(
    step=3,
    goal="Check out my todos",
    url="http://localhost:8080/dashboard",
    axtree="[1] link 'Todos' ...",     # accessibility tree
    html="<html>...",                  # pruned DOM
    screenshot=<numpy array or None>,
    last_action='click("42")',
    last_action_error="TimeoutError: Timeout 10000ms exceeded.",
    open_pages_urls=("http://localhost:8080/dashboard",),
    page=<playwright Page or None>,    # live page, when available
    raw={...},                         # the untouched browsergym observation
)
```

`page` is the live Playwright page. Methods that check current feasibility
before acting — probing whether a target exists, is visible, is occluded —
need it. Methods that work from the accessibility tree alone can ignore it. It
is `None` in offline tests.

Return a browsergym action string: `click("42")`, `fill("7", "hello")`,
`goto(url)`, `send_msg_to_user(text)`, `report_infeasible(reason)`, and so on.
Several actions separated by newlines are executed in order.

---

## 5. Running all six conditions

```bash
skillshift env status                                   # is anything reachable?
skillshift run --agent my_agent:MyAgent --all --out runs/mine
skillshift report runs/mine --out submission/ \
    --name "MyMethod" --model gpt-5-mini-2025-08-07
skillshift validate submission/results.json
```

`--all` is 3 sites × 6 conditions = 2130 task runs. Start with one site and one
condition.

`report` writes three files. Two of them you submit; **`per_task.jsonl` stays on
your machine** — see [results-policy.md](results-policy.md). `validate` runs
exactly the checks the leaderboard CI runs, so you find out before opening a
pull request.

---

## 6. Common mistakes

| Symptom | Cause |
| --- | --- |
| ASC is 0 and SFR is empty on the leaderboard | you never called `recorder.call` |
| `SkillRecordingError: opened inside` | a skill invoked another skill inside its `with` block |
| `does not implement the SkillAgent interface` | a typo in `reset` or `act` |
| SFR looks great but is flagged low-confidence | fewer than 30 invocations behind it; see [metrics.md](metrics.md) |
| validate rejects your n | a cell must cover **all** of a site's tasks: 162 / 114 / 79 |

## 7. A worked example

[`examples/minimal_agent.py`](../examples/minimal_agent.py) is a complete agent
with a skill library, a feasibility check and failure reporting, in about fifty
lines.
