"""Every `func:` locator a shipped task uses must be in the evaluator's globals.

`HTMLContentEvaluator` resolves a locator of the form `func:name(...)` with a
bare `eval(func)`, which looks the name up in `skillshift.eval.evaluators`'s
module globals. The module imported only `PseudoPage` out of WebArena's
`helper_functions`, so every task whose evaluation calls a helper died with
`NameError: name 'gitlab_get_project_memeber_role' is not defined` -- 24 of the
shipped tasks do, and three of them turned up in the reference sweep.

The check is static, over the shipped task files and the evaluator's source, so
it runs without WebArena installed and without the seven site URLs that
importing `helper_functions` demands.
"""

from __future__ import annotations

import ast
import json
import re

import pytest

from skillshift import paths

EVALUATORS_SOURCE = (paths.PACKAGE_ROOT / "eval" / "evaluators.py").read_text(encoding="utf-8")


def func_locator_names() -> set[str]:
    """Every helper name a shipped task's `func:` locator calls."""
    names: set[str] = set()
    for path in sorted(paths.TASKS_DIR.rglob("*.json")):
        try:
            tasks = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            for program in (task.get("eval") or {}).get("program_html") or []:
                locator = str(program.get("locator", ""))
                if locator.startswith("func:"):
                    names.add(re.split(r"[(\s.]", locator[len("func:") :])[0])
    return names


def imported_names() -> set[str]:
    """Names bound at module scope in evaluators.py -- what `eval` can see."""
    bound: set[str] = set()
    tree = ast.parse(EVALUATORS_SOURCE)
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Assign):
            bound.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return bound


NAMES = sorted(func_locator_names())


def test_the_task_files_really_use_func_locators():
    """A silent zero would make the parametrised check below vacuous."""
    assert NAMES, "no func: locator found in data/tasks -- the scan is broken"


@pytest.mark.parametrize("name", NAMES)
def test_every_func_locator_is_in_the_evaluator_namespace(name):
    assert name in imported_names(), (
        f"tasks call func:{name}(...) but {name} is not bound at module scope in "
        f"eval/evaluators.py, so `eval()` raises NameError and the task is lost."
    )


def test_the_imported_helpers_exist_in_the_installed_webarena():
    """The static check above cannot tell a real helper from a misremembered one.

    Written after importing `llm_ufo_match`, which does not exist -- the real
    name is `llm_ua_match`. A name list copied from memory passes every static
    check and then fails at import time, taking the whole evaluator with it.
    Skipped without the `run` extra, which is where webarena lives.
    """
    pytest.importorskip("webarena")
    evaluators = pytest.importorskip("skillshift.eval.evaluators")

    tree = ast.parse(EVALUATORS_SOURCE)
    helper_imports = [
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("helper_functions")
        for alias in node.names
    ]
    assert helper_imports, "the helper_functions import disappeared"
    for name in helper_imports:
        assert hasattr(evaluators, name), f"{name} is imported but not present at runtime"
