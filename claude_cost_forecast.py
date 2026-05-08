#!/usr/bin/env python3
"""
Claude Code cost forecast tool.

Runs a fixed set of representative READ-ONLY tasks against a target repo
using `claude -p`, captures per-task cost/tokens, and projects monthly
team spend at API-equivalent rates.

Usage:
    python claude_cost_forecast.py <repo_path>
    python claude_cost_forecast.py ~/code/my-repo --devs 5 --active-days 20
    python claude_cost_forecast.py ~/code/my-repo --model opus --only pr_review bug_hunt

Requires:
    - Claude Code installed and authenticated (`claude` on PATH)
    - Python 3.8+
    - A clean working directory in the target repo (script does not modify
      files, but Claude Code may create cache/state in ~/.claude/)
"""

import argparse
import csv
import json
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Optional


# Each task is intentionally READ-ONLY / proposal-only.
# `weight_per_day` = how many times a typical dev does this kind of task
# during one active workday. Tweak these to match your team's reality
# and re-run; the forecast scales linearly with the weights.
TASKS = [
    {
        "name": "architecture_summary",
        "prompt": (
            "Read the source files in this repository and produce a 200-word "
            "summary of the overall architecture. Identify the main modules, "
            "their responsibilities, and how they communicate. "
            "Do not modify any files."
        ),
        "weight_per_day": 1,
    },
    {
        "name": "pr_review",
        "prompt": (
            "Examine the most recently modified source files in this repository. "
            "Pretend you are reviewing them as a pull request and list exactly "
            "3 concrete improvements. For each: (a) one sentence on what and "
            "why, (b) a 5-10 line code sketch showing the change. "
            "Do not modify any files."
        ),
        "weight_per_day": 3,
    },
    {
        "name": "bug_hunt",
        "prompt": (
            "Identify 3 potential bugs, race conditions, or correctness issues "
            "in this codebase. For each, cite the file and line, explain the "
            "issue in 1-2 sentences, and sketch a fix in 5-10 lines of code. "
            "Do not modify any files."
        ),
        "weight_per_day": 2,
    },
    {
        "name": "refactor_plan",
        "prompt": (
            "Identify the single most complex file in this repository and "
            "propose a refactor plan: what to extract, what to rename, what "
            "to delete, and in what order. No code, just the plan in 200 "
            "words. Do not modify any files."
        ),
        "weight_per_day": 1,
    },
    {
        "name": "test_proposal",
        "prompt": (
            "Pick one important untested or under-tested function in this "
            "repository. Describe what tests it needs and write the test code "
            "in your response (do not write to disk). Aim for 5-8 test cases "
            "covering happy path, edge cases, and error conditions."
        ),
        "weight_per_day": 2,
    },
    {
        "name": "feature_design",
        "prompt": (
            "Propose a design for adding a structured logging layer to this "
            "codebase. Include: where it plugs in, what API it exposes, how "
            "existing code adopts it incrementally, and what the rollout "
            "looks like. 250 words max. Do not modify any files."
        ),
        "weight_per_day": 1,
    },
]


@dataclass
class TaskResult:
    name: str
    cost_usd: float = 0.0
    duration_sec: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    total_tokens: int = 0
    num_turns: int = 0
    weight_per_day: int = 1
    error: Optional[str] = None


def run_task(repo_path: Path, task: dict, model: str, timeout: int) -> TaskResult:
    """Run a single task with `claude -p` and return a structured result."""
    result = TaskResult(name=task["name"], weight_per_day=task["weight_per_day"])

    cmd = [
        "claude",
        "-p", task["prompt"],
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",  # tasks are read-only
        "--model", model,
    ]

    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        result.duration_sec = time.time() - start
        result.error = f"timeout after {timeout}s"
        return result
    except FileNotFoundError:
        result.error = "`claude` not found on PATH — install Claude Code first"
        return result

    result.duration_sec = time.time() - start

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip().replace("\n", " ")[:200]
        result.error = f"exit {proc.returncode}: {stderr}"
        return result

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        result.error = f"json decode failed: {e}"
        return result

    # Field names vary slightly between Claude Code versions; handle both.
    usage = data.get("usage") or {}
    result.input_tokens = int(usage.get("input_tokens") or 0)
    result.output_tokens = int(usage.get("output_tokens") or 0)
    result.cache_read_tokens = int(usage.get("cache_read_input_tokens") or 0)
    result.cache_creation_tokens = int(usage.get("cache_creation_input_tokens") or 0)
    result.total_tokens = (
        result.input_tokens + result.output_tokens
        + result.cache_read_tokens + result.cache_creation_tokens
    )
    result.cost_usd = float(
        data.get("total_cost_usd")
        or data.get("cost_usd")
        or 0.0
    )
    result.num_turns = int(data.get("num_turns") or 0)
    return result


def write_csv(results: List[TaskResult], path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))


def print_forecast(results: List[TaskResult], devs: int, active_days: int) -> None:
    """Project monthly/yearly team spend at API-equivalent rates."""
    valid = [r for r in results if r.error is None and r.cost_usd > 0]
    if not valid:
        print("\nNo successful tasks with cost data; cannot forecast.")
        return

    cost_per_dev_per_day = sum(r.cost_usd * r.weight_per_day for r in valid)
    monthly_per_dev = cost_per_dev_per_day * active_days
    monthly_team = monthly_per_dev * devs
    yearly_team = monthly_team * 12

    base_seats_yearly = 100 * devs * 12  # Premium @ $100/seat/mo (annual billing)
    overage_yearly = max(0.0, yearly_team - base_seats_yearly)

    print()
    print("=" * 72)
    print("  FORECAST (API-equivalent rates)")
    print("=" * 72)
    print(f"  Per dev per active day:        ${cost_per_dev_per_day:>10.2f}")
    print(f"  Per dev per month:             ${monthly_per_dev:>10.2f}  "
          f"({active_days} active days)")
    print(f"  Team ({devs} devs) per month:        ${monthly_team:>10.2f}")
    print(f"  Team ({devs} devs) per year:         ${yearly_team:>10.2f}")
    print()
    print(f"  Premium seats list price:      ${base_seats_yearly:>10.2f}/yr "
          f"(5 × $100/mo annual)")
    print(f"  Estimated overage above seats: ${overage_yearly:>10.2f}/yr")
    print(f"  Expected total cost:           "
          f"${base_seats_yearly + overage_yearly:>10.2f}/yr")
    print()
    print("Caveats:")
    print("  - Numbers are API-equivalent. Premium seats include allowance,")
    print("    so real overage is lower than the gross 'team per year' figure.")
    print("  - Forecast assumes weight_per_day in TASKS reflects real work.")
    print("  - Heavy Opus, Agent Teams, and long autonomous sessions are NOT")
    print("    modeled here and can multiply the bill (sometimes 5-10x).")
    print("  - Run on 2-3 representative repos and average for a better signal.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo", type=Path, help="Path to the target repo")
    parser.add_argument("--devs", type=int, default=5,
                        help="Team size for forecast (default: 5)")
    parser.add_argument("--active-days", type=int, default=20,
                        help="Active coding days per dev/month (default: 20)")
    parser.add_argument("--model", default="sonnet",
                        help="Model alias: sonnet | opus | haiku (default: sonnet)")
    parser.add_argument("--timeout", type=int, default=600,
                        help="Per-task timeout in seconds (default: 600)")
    parser.add_argument("--output", type=Path, default=Path("claude_cost_report.csv"),
                        help="CSV output path (default: claude_cost_report.csv)")
    parser.add_argument("--only", nargs="+", metavar="TASK",
                        help="Run only the named tasks (default: all)")
    parser.add_argument("--list-tasks", action="store_true",
                        help="List available tasks and exit")
    args = parser.parse_args()

    if args.list_tasks:
        print("Available tasks:")
        for t in TASKS:
            print(f"  {t['name']:<24} weight_per_day={t['weight_per_day']}")
        return 0

    if not args.repo.is_dir():
        print(f"Error: not a directory: {args.repo}", file=sys.stderr)
        return 1

    tasks = TASKS
    if args.only:
        tasks = [t for t in TASKS if t["name"] in args.only]
        if not tasks:
            available = [t["name"] for t in TASKS]
            print(f"Error: no matching tasks. Available: {available}",
                  file=sys.stderr)
            return 1

    print(f"Running {len(tasks)} task(s) against {args.repo} on {args.model} ...")
    print()

    results: List[TaskResult] = []
    for i, task in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] {task['name']:<24} ", end="", flush=True)
        r = run_task(args.repo, task, args.model, args.timeout)
        if r.error:
            print(f"ERROR  ({r.error})")
        else:
            print(f"${r.cost_usd:>7.4f}  "
                  f"{r.total_tokens:>9,} tok  "
                  f"{r.duration_sec:>5.1f}s")
        results.append(r)

    write_csv(results, args.output)
    print(f"\nPer-task results written to: {args.output}")
    print_forecast(results, args.devs, args.active_days)
    return 0


if __name__ == "__main__":
    sys.exit(main())
