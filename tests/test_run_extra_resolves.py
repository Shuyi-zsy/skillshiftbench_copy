"""The `run` extra has to be installable, which is the one thing it is for.

`pip install -e ".[run]"` is the documented way to get the browser stack, and
it failed outright: the extra asked for `playwright>=1.44` while the pinned
`browsergym-core==0.10.2` asks for `playwright~=1.39` and `libwebarena==0.0.3`
for `playwright<1.40`.  pip cannot satisfy all three, so the extra had never
been installed anywhere.

These are offline guards on the constraint arithmetic, not a network test: they
fail on the next well-meaning bump of playwright while browsergym stays pinned.
"""

from __future__ import annotations

import re

from skillshift import paths

PYPROJECT = (paths.REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

#: browsergym-core 0.10.2 declares `playwright~=1.39`; libwebarena 0.0.3, which
#: browsergym-webarena pulls in, declares `playwright>=1.32,<1.40`.  The
#: intersection is what the extra may ask for.
BROWSERGYM_PLAYWRIGHT_CEILING = (1, 40)


def requirement(name: str) -> str:
    match = re.search(rf'^\s*"({re.escape(name)}[^"]*)",\s*$', PYPROJECT, re.MULTILINE)
    assert match, f"{name} is not pinned in pyproject.toml at all"
    return match.group(1)


def upper_bound(spec: str) -> tuple[int, int] | None:
    match = re.search(r"<\s*(\d+)\.(\d+)", spec)
    return (int(match.group(1)), int(match.group(2))) if match else None


def lower_bound(spec: str) -> tuple[int, int] | None:
    match = re.search(r">=\s*(\d+)\.(\d+)", spec)
    return (int(match.group(1)), int(match.group(2))) if match else None


def test_browsergym_is_still_pinned_where_the_ceiling_came_from():
    """If browsergym moves, the ceiling below has to be re-derived, not assumed."""
    assert requirement("browsergym-core") == "browsergym-core==0.10.2"
    assert requirement("browsergym-webarena") == "browsergym-webarena==0.10.2"


def test_playwright_stays_under_the_ceiling_browsergym_imposes():
    spec = requirement("playwright")
    bound = upper_bound(spec)
    assert bound is not None, (
        f"playwright is specified as {spec!r} with no upper bound. browsergym-core "
        f"0.10.2 requires playwright~=1.39 and libwebarena 0.0.3 requires <1.40, so an "
        f"open-ended pin makes `pip install -e '.[run]'` unresolvable."
    )
    assert bound <= BROWSERGYM_PLAYWRIGHT_CEILING, (
        f"playwright is capped at {bound}, above the {BROWSERGYM_PLAYWRIGHT_CEILING} "
        f"that browsergym-core 0.10.2 and libwebarena 0.0.3 jointly allow."
    )


def test_playwright_floor_is_one_browsergym_also_accepts():
    floor = lower_bound(requirement("playwright"))
    assert floor is not None and floor >= (1, 32), (
        "libwebarena 0.0.3 requires playwright>=1.32; a lower floor lets pip pick a "
        "version browsergym cannot use."
    )
