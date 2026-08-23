"""Legacy parallel runner for MPCR.

Kept working for continuity with the artifact.  The supported entry point is
`skillshift run --agent ... --site ... --condition ...`, which also produces the
per-task records that `skillshift report` aggregates.

    python -m skillshift.agents.mpcr.run_online_parallel --task_ids 0-161 --workers 8
"""

import argparse
import multiprocessing
import os
import sys
from functools import partial
from subprocess import PIPE, STDOUT, Popen

# --- 辅助函数 ---

def parse_task_ids(task_id_str: str) -> list[str]:
    chunks = [c.strip() for c in task_id_str.split(",")]
    task_id_list = []
    for c in chunks:
        s, e = [int(n.strip()) for n in c.split("-")]
        task_id_list.extend([str(i) for i in range(s, e + 1)])
    return task_id_list


def run_process(cmd, env=None, task_prefix=""):
    """
    运行子进程。不再统计调用次数，不再缓存所有日志。
    """

    process = Popen(
        cmd,
        stdout=PIPE,
        stderr=STDOUT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    try:
        for line in process.stdout:
            pass

        process.wait()
    except KeyboardInterrupt:
        print(f"\n{task_prefix} Stopping process...")
        process.kill()
        process.wait()
        raise

    return


def skill_library_path(website: str) -> str:
    """Path of the textual skill library shipped for one site."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "workflows", f"{website}.txt")


def process_single_task(tid, args, lock):
    """
    快速模式：只执行 Step 1: Solving。
    """
    task_prefix = f"[Task {tid}]"
    print(f"{task_prefix} Starting FAST process (Step 1 Only)...")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    # --- Step 1: Solving ---
    print(f"{task_prefix} Step 1: Solving...")
    cmd1 = [
        sys.executable, "-m", "skillshift.agents.mpcr.run_single_task",
        "--task_name", f"myBenchmark.{tid}",
        "--websites", args.website,
        "--rename_to", f"myBenchmark.{tid}",
        "--headless",
    ]

    # The skill library is on by default.  In the artifact this line was
    # commented out, which meant no skill was ever loaded and ASC / SFR came out
    # of an agent that had no skills to call.  Pass --no-skill-library for a
    # deliberate no-skill run.
    if not args.no_skill_library:
        cmd1 += ["--memory_path", str(skill_library_path(args.website))]

    run_process(cmd1, env, task_prefix)
    print(f"{task_prefix} Done.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--task_ids",
        type=str,
        required=True,
        help="xxx-xxx,xxx-xxx",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of parallel processes",
    )
    parser.add_argument(
        "--no-skill-library",
        action="store_true",
        dest="no_skill_library",
        help="Run without loading the skill library (ASC will be 0 by construction).",
    )

    args = parser.parse_args()

    website = os.environ.get("website")
    if website is None:
        raise ValueError("Environment variable WEBSITE is not set.")

    if website not in ["admin", "gitlab", "wordpress"]:
        raise ValueError(
            f"Invalid WEBSITE={website}. "
            "Expected one of: admin, gitlab, wordpress."
        )

    args.website = website

    task_id_list = parse_task_ids(args.task_ids)
    print(f"Website: {args.website}")
    print(f"Total tasks to process: {len(task_id_list)}")

    target_func = process_single_task

    multiprocessing.set_start_method("spawn", force=True)

    with multiprocessing.Manager() as manager:
        lock = manager.Lock()

        func = partial(target_func, args=args, lock=lock)

        with multiprocessing.Pool(processes=args.workers) as pool:
            pool.map(func, task_id_list)


if __name__ == "__main__":
    main()