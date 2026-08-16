"""The Evaluator — CLI entry point."""
import argparse
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


if __name__ == "__main__":
    main()
