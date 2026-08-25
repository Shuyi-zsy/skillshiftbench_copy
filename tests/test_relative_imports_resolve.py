"""Every relative import in the package must point at a module that exists.

Phase 1 moved `evaluators` from `skillshift.tasks` to `skillshift.eval`, and
`tasks/task.py` kept asking for `.evaluators`.  Because the import is lazy --
inside `SkillShiftTask.setup`, which only runs when a browser is actually
driving a task -- nothing caught it: the whole test suite passed, the CLI
imported fine, and the failure surfaced only on the build machine at the first
real run, as `ModuleNotFoundError` recorded against the task.

This walks the source rather than importing it, so a lazy import is checked as
strictly as a top-level one and no browser dependency is needed.
"""

from __future__ import annotations

import ast

import pytest

from skillshift import paths

PACKAGE_ROOT = paths.PACKAGE_ROOT


def relative_imports():
    """(file, lineno, dotted target) for every `from .x import ...` in the package."""
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        package_parts = path.relative_to(PACKAGE_ROOT).parts[:-1]
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.level:
                continue
            # level 1 is this package, level 2 the one above it, and so on.
            base = ("skillshift", *package_parts)[: len(package_parts) + 1 - (node.level - 1)]
            target = (*base, *(node.module.split(".") if node.module else ()))
            yield path.relative_to(PACKAGE_ROOT), node.lineno, ".".join(target)


def module_exists(dotted: str) -> bool:
    parts = dotted.split(".")[1:]  # drop the leading 'skillshift'
    candidate = PACKAGE_ROOT.joinpath(*parts)
    return candidate.with_suffix(".py").is_file() or (candidate / "__init__.py").is_file()


ALL = list(relative_imports())


def test_the_walk_found_something():
    """A silent zero here would make every assertion below vacuous."""
    assert len(ALL) > 20


@pytest.mark.parametrize(
    ("where", "lineno", "target"),
    [pytest.param(*item, id=f"{item[0]}:{item[1]}->{item[2]}") for item in ALL],
)
def test_relative_import_target_exists(where, lineno, target):
    assert module_exists(target), (
        f"{where}:{lineno} imports {target}, which does not exist. A lazy import of a "
        f"module that moved fails only when that code path finally runs."
    )
