"""The `skillshift` command line.

    skillshift env status                      what is reachable right now
    skillshift env up --site --condition       (Phase 2: see skillshift-envs)
    skillshift calibrate                       check your setup against the anchor
    skillshift run --agent --site --condition  run tasks
    skillshift report RUN_DIR --out DIR        aggregate into a submission
    skillshift validate results.json           the leaderboard checks, locally

`validate` runs exactly the checks the leaderboard CI runs, so a submitter finds
out before opening a pull request rather than after.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__, conditions, paths, sites
from .errors import SkillShiftError

EXIT_OK = 0
EXIT_FAILED_CHECKS = 1
EXIT_USAGE = 2

DEFAULT_MAX_STEPS = 10
PROBE_TIMEOUT_SECONDS = 3


def _load_json(path: Path, what: str) -> dict:
    if not path.is_file():
        raise SkillShiftError(f"{what} not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SkillShiftError(f"{what} at {path} is not valid JSON: {exc}") from exc


# --------------------------------------------------------------------------
# env


def _site_urls() -> list[tuple[str, str, str | None]]:
    import os

    rows = []
    for site in sites.all_sites():
        for version in conditions.SITE_VERSIONS:
            name = f"{site.env_prefix}_{version.upper()}"
            rows.append((site.name, version, os.environ.get(name)))
    return rows


def _probe(url: str) -> str:
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=PROBE_TIMEOUT_SECONDS) as response:
            return f"ready (HTTP {response.status})"
    except urllib.error.HTTPError as exc:
        # A 4xx from a login page still means the server is up.
        return f"ready (HTTP {exc.code})"
    except Exception as exc:  # noqa: BLE001 - reported to the user verbatim
        return f"UNREACHABLE ({type(exc).__name__})"


def cmd_env_status(args: argparse.Namespace) -> int:
    print("SkillShift-Bench environments\n")
    missing = 0
    for site, version, url in _site_urls():
        if url is None:
            variable = f"{sites.get(site).env_prefix}_{version.upper()}"
            print(f"  {site:<10} {version}  not configured  (set {variable})")
            missing += 1
            continue
        status = "not probed" if args.no_probe else _probe(url)
        if "UNREACHABLE" in status:
            missing += 1
        print(f"  {site:<10} {version}  {url:<40} {status}")

    print("\nConditions map to versions as: src* -> v1, tgt* -> v2.")
    print("WordPress v1 and v2 intentionally share one URL: its contextual shift")
    print("is a theme swap on a single instance, not a second deployment.")

    if missing:
        print(f"\n{missing} environment(s) not ready. See docs/environments.md.")
        return EXIT_FAILED_CHECKS
    return EXIT_OK


def cmd_env_up(args: argparse.Namespace) -> int:
    print(
        "Environment provisioning lives in the companion repository:\n"
        "    https://github.com/SkillShift-Bench/skillshift-envs\n\n"
        f"    ./setup.sh --site {args.site} --condition {args.condition}\n\n"
        "This command will drive it once the pre-built images are published; until\n"
        "then, follow docs/environments.md and set the *_V1 / *_V2 URL variables."
    )
    return EXIT_USAGE


# --------------------------------------------------------------------------
# calibrate


def cmd_calibrate(args: argparse.Namespace) -> int:
    if not paths.CALIBRATION_SET_PATH.is_file():
        print(
            "The calibration subset has not been published yet.\n\n"
            f"  expected: {paths.CALIBRATION_SET_PATH}\n\n"
            "It pins 30 tasks and the reference agent's scores on them, so that you can\n"
            "tell a misconfigured environment from a genuinely weak method. Until it\n"
            "ships, verify your setup with `skillshift env status` and a single task run.",
            file=sys.stderr,
        )
        return EXIT_USAGE

    print("Calibration runs are wired but the published baseline is still pending.")
    return EXIT_USAGE


# --------------------------------------------------------------------------
# run


def cmd_run(args: argparse.Namespace) -> int:
    from .agents import load_agent_factory
    from .eval.records import write_jsonl
    from .runner import run_condition

    factory = load_agent_factory(args.agent)

    if args.all:
        pairs = [(site.name, condition) for site in sites.all_sites() for condition in conditions.CONDITIONS]
    else:
        if not args.site or not args.condition:
            raise SkillShiftError("Pass --site and --condition, or --all.")
        pairs = [(sites.get(args.site).name, conditions.resolve(args.condition).name)]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    records = []

    for site, condition in pairs:
        print(f"running {site} / {condition} ...", flush=True)
        records.extend(
            run_condition(
                site=site,
                condition=condition,
                agent_factory=factory,
                task_uids=args.tasks or None,
                max_steps=args.max_steps,
                headless=not args.headed,
                on_record=lambda record: print(
                    f"  {record.uid:<32} {'PASS' if record.success else 'fail'} "
                    f"steps={record.steps} skills={record.skill_calls}",
                    flush=True,
                ),
            )
        )

    per_task = out_dir / "per_task.jsonl"
    write_jsonl(records, per_task)
    print(f"\n{len(records)} task record(s) written to {per_task}")
    print(f"Next: skillshift report {out_dir} --out submission/ --name <method> --model <model>")
    return EXIT_OK


# --------------------------------------------------------------------------
# report


def cmd_report(args: argparse.Namespace) -> int:
    from . import report as report_mod
    from .eval.records import read_jsonl

    run_dir = Path(args.run_dir)
    per_task = run_dir if run_dir.is_file() else run_dir / report_mod.PER_TASK_FILENAME
    if not per_task.is_file():
        raise SkillShiftError(
            f"No {report_mod.PER_TASK_FILENAME} in {run_dir}. `skillshift run` writes it."
        )

    records = read_jsonl(per_task)
    env_digests = (
        _load_json(Path(args.digests), "Image digest file") if args.digests else {"unknown": None}
    )

    submission = {
        "name": args.name,
        "date": args.date,
        "contact": args.contact,
        "method": {
            "name": args.method or args.name,
            "description": None,
            "paper_url": args.paper_url,
            "code_url": args.code_url,
        },
        "model": {"id": args.model, "temperature": args.temperature, "vision": args.vision},
        "provenance": {
            "label": "self-reported",
            "source": f"run {args.date}",
            "code_released": args.code_url is not None,
        },
        "repro_command": args.repro_command,
    }

    results, receipt = report_mod.build(
        records,
        submission=submission,
        env_digests=env_digests,
        harness_commit=args.commit,
    )
    written = report_mod.write(args.out, results=results, receipt=receipt, records=records)

    print(f"wrote {written.results}")
    print(f"wrote {written.receipt}")
    print(f"wrote {written.private}")
    print("\n" + written.notice)
    print(f"\nNext: skillshift validate {written.results}")
    return EXIT_OK


# --------------------------------------------------------------------------
# validate


def cmd_validate(args: argparse.Namespace) -> int:
    from .eval import validate as validate_mod

    results_path = Path(args.results)
    results = _load_json(results_path, "Results file")

    receipt = None
    receipt_path = Path(args.receipt) if args.receipt else results_path.parent / "run_receipt.json"
    if receipt_path.is_file():
        receipt = _load_json(receipt_path, "Receipt file")
        print(f"using receipt {receipt_path}")

    digests = _load_json(Path(args.digests), "Image digest file") if args.digests else None

    report = validate_mod.validate_submission(results, receipt=receipt, official_digests=digests)

    for finding in report.findings:
        print(str(finding))

    print("\n" + report.summary())
    return EXIT_OK if report.ok else EXIT_FAILED_CHECKS


# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skillshift", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"skillshift-bench {__version__}")
    sub = parser.add_subparsers(dest="command")

    env = sub.add_parser("env", help="inspect or provision the benchmark websites")
    env_sub = env.add_subparsers(dest="env_command")
    status = env_sub.add_parser("status", help="show which sites and versions are reachable")
    status.add_argument("--no-probe", action="store_true", help="do not make HTTP requests")
    status.set_defaults(func=cmd_env_status)
    up = env_sub.add_parser("up", help="bring up one environment")
    up.add_argument("--site", required=True, choices=list(sites.SITE_NAMES))
    up.add_argument("--condition", required=True, choices=list(conditions.CONDITIONS))
    up.set_defaults(func=cmd_env_up)

    calibrate = sub.add_parser("calibrate", help="check your setup against the reference anchor")
    calibrate.set_defaults(func=cmd_calibrate)

    run = sub.add_parser("run", help="run tasks with an agent")
    run.add_argument("--agent", required=True, help="'reference', or 'module:Factory'")
    run.add_argument("--site", choices=list(sites.SITE_NAMES))
    run.add_argument("--condition", choices=list(conditions.CONDITIONS))
    run.add_argument("--all", action="store_true", help="all 3 sites x 6 conditions")
    run.add_argument("--tasks", nargs="*", help="specific task ids instead of the whole site")
    run.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS, dest="max_steps")
    run.add_argument("--headed", action="store_true", help="show the browser")
    run.add_argument("--out", default="runs/latest")
    run.set_defaults(func=cmd_run)

    report = sub.add_parser("report", help="aggregate a run into a submission")
    report.add_argument("run_dir")
    report.add_argument("--out", default="submission")
    report.add_argument("--name", required=True, help="leaderboard display name")
    report.add_argument("--model", required=True, help="model id used for the run")
    report.add_argument("--method", help="method name, if different from --name")
    report.add_argument("--date", default=None)
    report.add_argument("--contact", default=None)
    report.add_argument("--paper-url", default=None, dest="paper_url")
    report.add_argument("--code-url", default=None, dest="code_url")
    report.add_argument("--temperature", type=float, default=None)
    report.add_argument("--vision", action="store_true", default=None)
    report.add_argument("--repro-command", default=None, dest="repro_command")
    report.add_argument("--commit", default=None, help="git commit of the harness used")
    report.add_argument("--digests", default=None, help="path to DIGESTS.json")
    report.set_defaults(func=cmd_report)

    validate = sub.add_parser("validate", help="run the leaderboard checks locally")
    validate.add_argument("results")
    validate.add_argument("--receipt", default=None)
    validate.add_argument("--digests", default=None, help="path to DIGESTS.json")
    validate.set_defaults(func=cmd_validate)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if getattr(args, "func", None) is None:
        parser.print_usage(sys.stderr)
        print("\nRun `skillshift --help` to see the available commands.", file=sys.stderr)
        return EXIT_USAGE

    if args.command == "report" and args.date is None:
        from datetime import date

        args.date = date.today().isoformat()

    try:
        return int(args.func(args))
    except SkillShiftError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
