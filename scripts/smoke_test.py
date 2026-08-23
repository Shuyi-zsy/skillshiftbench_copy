#!/usr/bin/env python3
"""Offline integrity check.

Verifies the repository is intact WITHOUT Docker, a GPU, an API key, or the
browser stack:

  1. Task files load and every version bundle totals 355 tasks.
  2. Per-site counts are the paper's 162 / 114 / 79, and `id_map.csv` agrees.
  3. Every condition maps to exactly one set of harness flags.
  4. The shipped JSON schemas parse and accept a transcribed Table 1 row.
  5. Nothing that must stay local is committed, and no live API key leaked.

Run from anywhere:

    python scripts/smoke_test.py

Exit code 0 = all pass, 1 = something failed.
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ok = True


def check(name, condition, detail=""):
    global ok
    if not condition:
        ok = False
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


# ---- 1 & 2. tasks -----------------------------------------------------------
from skillshift import conditions, registry, sites  # noqa: E402

try:
    reg = registry.load_registry()
    loaded = True
except Exception as exc:  # noqa: BLE001
    loaded = False
    check("task registry loads", False, str(exc))

if loaded:
    for version in conditions.SITE_VERSIONS:
        total = sum(len(reg.for_site_version(site, version)) for site in sites.SITE_NAMES)
        check(f"{version} bundle == 355 tasks", total == 355, f"got {total}")

    for site in sites.all_sites():
        actual = len(reg.for_site_version(site.name, "v1"))
        check(f"{site.name} == {site.n_tasks} tasks", actual == site.n_tasks, f"got {actual}")

    rows = registry.load_id_map()
    check("id_map.csv covers every task", len(rows) == len(reg), f"{len(rows)} vs {len(reg)}")
    check(
        "id_map.csv ids agree with the registry",
        {row["uid"] for row in rows} == set(reg.uids()),
    )

# ---- 3. conditions ----------------------------------------------------------
flags = {
    (spec.site_version, spec.perceptual_shift, spec.execution_shift)
    for spec in conditions.all_specs()
}
check("six conditions map to six distinct flag sets", len(flags) == 6, f"got {len(flags)}")

# ---- 4. schemas -------------------------------------------------------------
from skillshift.eval import schema, validate  # noqa: E402

for name in schema.SCHEMA_NAMES:
    try:
        schema.load(name)
        check(f"{name}.schema.json parses", True)
    except Exception as exc:  # noqa: BLE001
        check(f"{name}.schema.json parses", False, str(exc))

sys.path.insert(0, str(ROOT))
try:
    from tests.fixtures import awm_submission

    report = validate.validate_submission(awm_submission())
    check("a transcribed Table 1 row passes the leaderboard checks", report.ok, str(report.errors))
except ImportError:
    print("[SKIP] Table 1 fixture not available (tests/ not shipped)")

# ---- 5. nothing private, no leaked key --------------------------------------
private = [
    path
    for path in ROOT.rglob("per_task.jsonl")
    if ".git" not in path.parts and ".venv" not in path.parts
]
check(
    "no per-task judgements committed",
    not private,
    f"found {[str(p.relative_to(ROOT)) for p in private]}",
)

LEAKS = {
    "live OpenAI-style key": re.compile(r"sk-[A-Za-z0-9]{24,}"),
    "personal path": re.compile(r"/Users/[A-Za-z0-9]+/"),
}
_leak_name = os.environ.get("_LEAK_NAME")
if _leak_name:
    LEAKS["author name"] = re.compile(re.escape(_leak_name), re.I)

TEXT_EXT = {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".csv"}
found = []
for path in ROOT.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in TEXT_EXT:
        continue
    if path.name == "smoke_test.py" or ".git" in path.parts or ".venv" in path.parts:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for label, pattern in LEAKS.items():
        if pattern.search(text):
            found.append(f"{label} in {path.relative_to(ROOT)}")
check("no secret or identity leaks", not found, "; ".join(found))

print()
print("SMOKE TEST:", "ALL CHECKS PASSED" if ok else "FAILURES ABOVE")
sys.exit(0 if ok else 1)
