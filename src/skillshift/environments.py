"""Which deployed environment serves which (site, version) pair.

One name per deployment, used in three places that must agree: the image tags
published by `skillshift-envs`, the keys of its `DIGESTS.json`, and the
`env_digests` block of a run receipt.  WordPress appears once for both versions
because its contextual shift is a theme swap on a single instance, not a second
deployment.
"""

from __future__ import annotations

from . import conditions, sites

#: (site, site_version) -> environment name.
ENVIRONMENT_NAMES: dict[tuple[str, str], str] = {
    ("gitlab", "v1"): "gitlab-v12",
    ("gitlab", "v2"): "gitlab-v16",
    ("magento", "v1"): "magento-v19",
    ("magento", "v2"): "magento-v24",
    ("wordpress", "v1"): "wordpress",
    ("wordpress", "v2"): "wordpress",
}

#: The keys of `skillshift-envs/DIGESTS.json`, in a stable order.
DIGEST_KEYS: tuple[str, ...] = (
    "gitlab-v12",
    "gitlab-v16",
    "magento-v19",
    "magento-v24",
    "wordpress",
)


def environment_for(site: str, condition: str) -> str:
    """The environment a run of `site` under `condition` talks to."""
    site_name = sites.get(site).name
    version = conditions.resolve(condition).site_version
    return ENVIRONMENT_NAMES[(site_name, version)]
