"""Loading and applying the published JSON Schemas.

The schema files under `skillshift/schemas/` are the contract a submission is
held to.  They ship with the package so that `skillshift validate` gives the
same answer locally as the leaderboard CI does.
"""

from __future__ import annotations

import functools
import json
from typing import Any

import jsonschema

from ..errors import ValidationError
from ..paths import SCHEMA_DIR

SCHEMA_NAMES: tuple[str, ...] = ("results", "receipt")


@functools.lru_cache(maxsize=len(SCHEMA_NAMES))
def load(name: str) -> dict:
    """Load a schema by short name (`results` or `receipt`)."""
    if name not in SCHEMA_NAMES:
        raise ValidationError(f"Unknown schema {name!r}. Expected one of {list(SCHEMA_NAMES)}.")

    path = SCHEMA_DIR / f"{name}.schema.json"
    if not path.is_file():
        raise ValidationError(f"Schema file missing from the installed package: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def validate(payload: Any, name: str) -> tuple[str, ...]:
    """Validate a payload, returning human-readable problems (empty = valid)."""
    validator = jsonschema.Draft202012Validator(load(name))
    problems = []
    for error in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path)):
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        problems.append(f"{location}: {error.message}")
    return tuple(problems)
