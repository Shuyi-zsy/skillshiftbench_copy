#!/usr/bin/env python3
"""One-shot transform: artifact task JSONs -> `data/tasks/` + `id_map.csv`.

The artifact shipped two copies of every task file, under `Data/tasks/` and
under `Software/src/Benchmark/`.  They are byte-identical for GitLab and
WordPress but differ for Magento: four tasks (ids 18, 20, 21, 22 in both v1 and
v2) carry a corrected `September` spelling in the `Software/src/Benchmark/`
copy and a `Sepetember` typo in the `Data/` copy.

`Software/src/Benchmark/` is the copy the harness actually loads -- the task
loader resolves its path relative to its own module directory -- so it is the
copy the paper's numbers were produced with, and it is the one kept here.

Re-run with:

    python scripts/build_task_data.py --artifact <path-to-SkillShift-Bench-artifact>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

# (site, version) -> path inside the artifact, relative to Software/src/Benchmark
SOURCE_FILES = {
    ("gitlab", "v1"): "gitlab_task/gitlab_tasks_v1.json",
    ("gitlab", "v2"): "gitlab_task/gitlab_tasks_v2.json",
    ("magento", "v1"): "admin_task/admin_tasks_v1.json",
    ("magento", "v2"): "admin_task/admin_tasks_v2.json",
    ("wordpress", "v1"): "wordpress_task/wordpress_tasks.json",
    ("wordpress", "v2"): "wordpress_task/wordpress_tasks.json",
}

# WordPress ships a single file used by both versions (the contextual shift is a
# theme swap), so it is written once rather than duplicated.
OUTPUT_FILES = {
    ("gitlab", "v1"): "gitlab/v1.json",
    ("gitlab", "v2"): "gitlab/v2.json",
    ("magento", "v1"): "magento/v1.json",
    ("magento", "v2"): "magento/v2.json",
    ("wordpress", "v1"): "wordpress/tasks.json",
    ("wordpress", "v2"): "wordpress/tasks.json",
}

EXPECTED_COUNTS = {"gitlab": 162, "magento": 114, "wordpress": 79}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    args = parser.parse_args()

    benchmark_dir = args.artifact / "Software" / "src" / "Benchmark"
    data_dir = args.artifact / "Data" / "tasks"
    if not benchmark_dir.is_dir():
        raise SystemExit(f"not an artifact directory: {args.artifact}")

    tasks_out = args.out / "tasks"
    rows: list[dict[str, object]] = []
    provenance: list[dict[str, object]] = []
    written: set[str] = set()

    for (site, version), rel in SOURCE_FILES.items():
        src = benchmark_dir / rel
        alt = data_dir / rel
        records = json.loads(src.read_text(encoding="utf-8"))

        if len(records) != EXPECTED_COUNTS[site]:
            raise SystemExit(
                f"{site} {version}: expected {EXPECTED_COUNTS[site]} tasks, got {len(records)}"
            )

        enriched = []
        for record in records:
            index = record["task_id"]
            # `uid` is deliberately NOT stored: it depends on the version, and
            # WordPress serves one file to both versions.  The registry derives
            # it from (site, version, index).
            enriched.append(
                {
                    "family_id": f"skillshift.{site}.{index}",
                    "legacy_id": f"myBenchmark.{index}",
                    **record,
                }
            )
            rows.append(
                {
                    "uid": f"skillshift.{site}.{version}.{index}",
                    "family_id": f"skillshift.{site}.{index}",
                    "legacy_id": f"myBenchmark.{index}",
                    "site": site,
                    "site_version": version,
                    "index": index,
                    "intent_template_id": record.get("intent_template_id", ""),
                }
            )

        out_path = tasks_out / OUTPUT_FILES[(site, version)]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if str(out_path) not in written:
            out_path.write_text(
                json.dumps(enriched, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            written.add(str(out_path))

        provenance.append(
            {
                "site": site,
                "site_version": version,
                "output": str(out_path.relative_to(args.out)),
                "source": f"Software/src/Benchmark/{rel}",
                "source_sha256": sha256_of(src),
                "duplicate_copy": f"Data/tasks/{rel}",
                "duplicate_copy_sha256": sha256_of(alt) if alt.exists() else None,
                "copies_identical": sha256_of(src) == sha256_of(alt) if alt.exists() else None,
                "n_tasks": len(records),
            }
        )

    rows.sort(key=lambda r: (r["site"], r["site_version"], r["index"]))
    with (tasks_out / "id_map.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "uid",
                "family_id",
                "legacy_id",
                "site",
                "site_version",
                "index",
                "intent_template_id",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    (tasks_out / "PROVENANCE.json").write_text(
        json.dumps(
            {
                "note": (
                    "Task files are taken from the artifact's Software/src/Benchmark copy, "
                    "which is the copy the harness loads and therefore the copy the paper's "
                    "numbers were produced with. The uid / family_id / legacy_id fields are "
                    "added here; all other fields are verbatim."
                ),
                "files": provenance,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"wrote {len(written)} task files, {len(rows)} id_map rows")
    for entry in provenance:
        if entry["copies_identical"] is False:
            print(f"  note: artifact copies differed for {entry['source']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
