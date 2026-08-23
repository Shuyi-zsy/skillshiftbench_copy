"""The three benchmark websites and the constants derived from them.

These numbers are the denominators of every leaderboard cell, so they live in
one place and are asserted against the shipped task files by the registry
(see `registry.load_registry`).  They are not read from disk: a corrupted or
truncated task file must fail loudly rather than quietly change a denominator.
"""

from dataclasses import dataclass

from .errors import UnknownSiteError


@dataclass(frozen=True)
class Site:
    """A benchmark website.

    Attributes:
        name: Canonical, paper-facing name, as printed in Table 1.
        harness_key: Value of the `website` environment variable read by the
            task loader.  Magento is historically called `admin` there.
        instance_key: Key used by the URL/credential table in `tasks.instance`.
        env_prefix: Prefix of the `<SITE>_V1` / `<SITE>_V2` URL variables.
        n_tasks: Number of tasks for this site.  This is the `n` of every
            (site, condition) cell on the leaderboard.
        versioned_tasks: Whether the site ships separate v1/v2 task files.
            WordPress does not: its contextual shift is a theme swap on a single
            instance, so both versions load the same file.
    """

    name: str
    harness_key: str
    instance_key: str
    env_prefix: str
    n_tasks: int
    versioned_tasks: bool


GITLAB = Site(
    name="gitlab",
    harness_key="gitlab",
    instance_key="gitlab",
    env_prefix="GITLAB",
    n_tasks=162,
    versioned_tasks=True,
)

MAGENTO = Site(
    name="magento",
    harness_key="admin",
    instance_key="shopping_admin",
    env_prefix="SHOPPING_ADMIN",
    n_tasks=114,
    versioned_tasks=True,
)

WORDPRESS = Site(
    name="wordpress",
    harness_key="wordpress",
    instance_key="wordpress",
    env_prefix="WORDPRESS",
    n_tasks=79,
    versioned_tasks=False,
)

#: Sites in the order they appear in the paper's Table 1.
SITE_NAMES: tuple[str, ...] = ("gitlab", "magento", "wordpress")

_SITES: dict[str, Site] = {
    "gitlab": GITLAB,
    "magento": MAGENTO,
    "wordpress": WORDPRESS,
}

#: Aliases accepted on input, including the harness's internal name for Magento.
_ALIASES: dict[str, str] = {
    "admin": "magento",
    "shopping_admin": "magento",
    "magento": "magento",
    "gitlab": "gitlab",
    "wordpress": "wordpress",
    "wp": "wordpress",
}

#: Total number of tasks in the benchmark.
TOTAL_TASKS: int = sum(_SITES[name].n_tasks for name in SITE_NAMES)


def get(name: str) -> Site:
    """Look up a site by canonical name or accepted alias."""
    key = _ALIASES.get(str(name).strip().lower())
    if key is None:
        raise UnknownSiteError(
            f"Unknown site {name!r}. Expected one of {list(SITE_NAMES)} "
            f"(the harness alias 'admin' for 'magento' is also accepted)."
        )
    return _SITES[key]


def all_sites() -> tuple[Site, ...]:
    """Every site, in paper-table order."""
    return tuple(_SITES[name] for name in SITE_NAMES)


def task_counts() -> dict[str, int]:
    """Canonical task count per site: the denominator of each leaderboard cell."""
    return {name: _SITES[name].n_tasks for name in SITE_NAMES}
