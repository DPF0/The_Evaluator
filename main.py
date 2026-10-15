"""The Evaluator — CLI entry point."""
import argparse
import math
import sys
from pathlib import Path

from src.config import Config, get_config
from src.db import Database
from src.llm import LLMClient
from src.agents.orchestrator import Orchestrator
from src.models import Assignment, Rubric


def main():
    parser = argparse.ArgumentParser(description="The Evaluator — AI Notebook Grader")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Evaluate single notebook
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate a notebook")
    eval_parser.add_argument("--student", required=True, help="Student name")
    eval_parser.add_argument("--file", required=True, help="Notebook filename or path")
    eval_parser.add_argument("--github", help="GitHub URL to folder")
    eval_parser.add_argument("--task", help="Task key (e.g., numpy_i)")

    # Generate report
    report_parser = subparsers.add_parser("report", help="Generate feedback report")
    report_parser.add_argument("--student", help="Student ID or name")
    report_parser.add_argument("--cohort", help="Assignment ID for cohort report")

    # Rubric management
    rubric_parser = subparsers.add_parser("rubric", help="Manage rubrics")
    rubric_parser.add_argument("--generate", help="Generate rubric for topic")
    rubric_parser.add_argument("--topic", help="Topic key")
    rubric_parser.add_argument("--description", help="Assignment description")

    # Database setup
    setup_parser = subparsers.add_parser("setup", help="Initialize database and rubrics")

    # Usage monitoring
    monitor_parser = subparsers.add_parser("monitor", help="Print usage/cost/grade monitoring report")
    monitor_parser.add_argument("--days", type=int, default=None, help="Only include the last N days")
    monitor_parser.add_argument("--watts", type=float, default=160.0, help="GPU power draw in watts (local cost estimate)")
    monitor_parser.add_argument("--price-kwh", type=float, default=0.20, help="Electricity price in EUR/kWh (local cost estimate)")
    monitor_parser.add_argument("--price-per-1m", type=float, default=1.0, help="API price in EUR per 1M tokens (API cost estimate)")

    args = parser.parse_args()
    config = get_config()

    if args.command is None:
        parser.print_help()
        return

    db = Database(config.database.path)
    llm = LLMClient(config.llm)
    orchestrator = Orchestrator(db, llm, config.paths.rubrics_dir)

    try:
        if args.command == "setup":
            _setup_database(db, config.paths.rubrics_dir)
            print("Database and rubrics initialized.")

        elif args.command == "evaluate":
            reachable, detail = llm.health_check()
            if not reachable:
                print(f"Error: Cannot reach the LLM endpoint: {detail}")
                print("Check base_url/model (env vars EVALUATOR_LLM_* or config.json).")
                return
            if args.github:
                result = orchestrator.evaluate_notebook(
                    args.student, args.file, args.github
                )
            elif args.task:
                result = orchestrator.evaluate_local_notebook(
                    args.student, args.file, args.task
                )
            else:
                print("Error: Provide --github URL or --task key.")
                return
            print(f"Grade: {result.grade.value} ({result.numeric_grade}/10)")
            print(result.markdown_report)

        elif args.command == "report":
            if args.student:
                report = orchestrator.generate_student_feedback(args.student)
                print(report)
            elif args.cohort:
                report = orchestrator.generate_cohort_report(args.cohort)
                print(report)

        elif args.command == "monitor":
            _print_monitor_report(
                db,
                days=args.days,
                watts=args.watts,
                price_kwh=args.price_kwh,
                price_per_1m=args.price_per_1m,
            )

        elif args.command == "rubric":
            if args.generate:
                rubric = orchestrator.rubric_agent.generate_rubric(
                    args.generate, args.topic or args.generate,
                    args.topic or args.generate,
                    args.description or "",
                )
                db.add_rubric(rubric)
                print(f"Rubric generated for {rubric.topic_key}")

    finally:
        db.close()


def _setup_database(db, rubrics_dir):
    """Initialize database with default rubrics."""
    from src.utils.rubrics import load_all_rubrics
    rubrics = load_all_rubrics(rubrics_dir)
    for topic_key, content in rubrics.items():
        import re
        match = re.search(r"#\s*Rúbrica\s*de\s*Evaluación:\s*(.+?)\s*[-\n]", content)
        assignment_name = match.group(1).strip() if match else topic_key
        module = topic_key.split("_")[0].title() if "_" in topic_key else topic_key
        num_match = re.search(r"num_exercises:\s*(\d+)", content)
        num_exercises = int(num_match.group(1)) if num_match else 0

        db.add_rubric(Rubric(
            topic_key=topic_key,
            assignment_name=assignment_name,
            module=module,
            num_exercises=num_exercises,
            content=content,
        ))
    print(f"Loaded {len(rubrics)} rubrics into database.")


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def _grade_shares(counts: dict) -> dict:
    total = sum(counts.values())
    if not total:
        return {}
    return {g: c / total for g, c in counts.items()}


def _print_monitor_report(db, days=None, watts=160.0, price_kwh=0.20, price_per_1m=1.0):
    scope = f"last {days} days" if days else "all time"
    print("=" * 62)
    print(f"The Evaluator — usage monitor ({scope})")
    print("=" * 62)

    rows = db.get_usage_log(days)
    if not rows:
        print("No usage data recorded yet.")
        print("  evaluations: 0 | prompt: 0 | completion: 0 | total: 0 tokens")
        print(f"  cost estimate (LOCAL, {watts:g} W @ {price_kwh} EUR/kWh): 0.00 EUR")
        print(f"  cost estimate (API, {price_per_1m} EUR / 1M tokens): 0.00 EUR")
        print("  grade distribution: (no data)")
        print("  failure rate: (no data)")
        print("  latency p50/p95: (no data)")
        return

    agg = db.get_usage_aggregates(days)
    totals = agg["totals"]
    total = totals.get("total") or 0
    prompt_tokens = totals.get("prompt_tokens") or 0
    completion_tokens = totals.get("completion_tokens") or 0
    total_tokens = totals.get("total_tokens") or 0
    ok_count = totals.get("ok_count") or 0
    avg_latency = totals.get("avg_latency_s") or 0.0

    print(f"Evaluations: {total} (ok: {ok_count}, failed: {total - ok_count})")
    print(f"Tokens: prompt {prompt_tokens} | completion {completion_tokens} | total {total_tokens}")

    gpu_seconds = avg_latency * total
    local_cost = (watts / 1000.0) * (gpu_seconds / 3600.0) * price_kwh
    api_cost = (total_tokens / 1_000_000.0) * price_per_1m
    print(f"Cost estimate (LOCAL, {watts:g} W x avg {avg_latency:.1f}s @ {price_kwh} EUR/kWh): {local_cost:.2f} EUR")
    print(f"Cost estimate (API, {price_per_1m} EUR / 1M tokens): {api_cost:.2f} EUR")

    print("Grade distribution:")
    grade_counts = {r["grade"]: r["count"] for r in agg["by_grade"]}
    known = ("Excepcional", "Bien", "Regular", "Mal", None)
    for grade in known:
        count = grade_counts.get(grade, 0)
        print(f"  {(grade or '(no grade)'):<12} {count:>4}  ({100.0 * count / total:.1f}%)")
    for grade, count in grade_counts.items():
        if grade not in known:
            print(f"  {grade:<12} {count:>4}  ({100.0 * count / total:.1f}%)")

    print(f"Failure rate: {100.0 * (total - ok_count) / total:.1f}% ({total - ok_count}/{total})")

    latencies = [r["latency_s"] for r in rows if r["latency_s"] is not None]
    print(f"Latency: p50 {_percentile(latencies, 0.50):.1f}s | p95 {_percentile(latencies, 0.95):.1f}s | avg {avg_latency:.1f}s")

    window = 10
    if total > window:
        recent_counts: dict = {}
        for r in rows[:window]:
            recent_counts[r["grade"]] = recent_counts.get(r["grade"], 0) + 1
        overall_shares = _grade_shares(grade_counts)
        recent_shares = _grade_shares(recent_counts)
        drifts = []
        for g in sorted(set(overall_shares) | set(recent_shares), key=str):
            diff = (recent_shares.get(g, 0.0) - overall_shares.get(g, 0.0)) * 100.0
            if abs(diff) > 20.0:
                drifts.append(f"{g or '(no grade)'} {diff:+.1f}pp")
        if drifts:
            print(f"Drift (last {window} vs overall): " + ", ".join(drifts))
        else:
            print(f"Drift (last {window} vs overall): no grade share shifted by more than 20pp.")
    else:
        print(f"Drift: not enough data (need more than {window} evaluations).")


if __name__ == "__main__":
    main()
