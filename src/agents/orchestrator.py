"""Orchestrator — coordinates agents and manages evaluation workflow."""
from typing import Optional
from src.db import Database
from src.llm import LLMClient
from src.models import Student, Assignment, Evaluation, Rubric, Grade
from src.agents.evaluation import EvaluationAgent
from src.agents.rubric import RubricAgent
from src.agents.report import ReportAgent
from src.utils.notebook import download_notebook_from_github, clean_notebook
from src.utils.task_classifier import classify_task
from src.utils.email import send_feedback_email


class Orchestrator:
    """Main orchestrator that coordinates the evaluation pipeline."""

    def __init__(self, db: Database, llm: LLMClient, rubrics_dir: str = "rubrics"):
        self.db = db
        self.llm = llm
        self.eval_agent = EvaluationAgent(llm, rubrics_dir, db)
        self.rubric_agent = RubricAgent(llm, rubrics_dir)
        self.report_agent = ReportAgent(llm)

    def evaluate_notebook(self, student_name: str, filename: str,
                          github_url: str) -> Evaluation:
        """Evaluate a single notebook.

        Args:
            student_name: Student name.
            filename: Notebook filename.
            github_url: GitHub URL to the folder containing the notebook.

        Returns:
            Evaluation object.
        """
        # Get or create student
        student = self.db.get_student(student_name)
        if not student:
            student_id = self.db.add_student(Student(name=student_name))
            student = self.db.get_student(student_name)
        else:
            student_id = student["id"]

        # Download notebook
        notebook_json = download_notebook_from_github(github_url, filename)

        # Classify task
        cleaned_text = clean_notebook(notebook_json)
        task_key = classify_task(cleaned_text, filename)

        # Get assignment
        assignment = self.db.get_assignment(task_key)
        if not assignment:
            parts = task_key.split("_")
            roman = {"i": "I", "ii": "II", "iii": "III"}
            assign_name = " ".join(roman.get(p.lower(), p.capitalize()) for p in parts)
            assignment_id = self.db.add_assignment(Assignment(
                name=assign_name,
                module=task_key,
                topic_key=task_key,
            ))
        else:
            assignment_id = assignment["id"]

        # Get rubric
        rubric_content = self.rubric_agent.get_rubric(task_key)

        # Evaluate (with reference metadata)
        evaluation = self.eval_agent.evaluate(
            notebook_json, student_name, filename, rubric_content,
            topic_key=task_key
        )
        evaluation.student_id = student_id
        evaluation.assignment_id = assignment_id
        evaluation.topic_key = task_key

        # Save to database
        self.db.add_evaluation(evaluation)
        return evaluation

    def evaluate_local_notebook(self, student_name: str, filepath: str,
                                 task_key: Optional[str] = None) -> Evaluation:
        """Evaluate a notebook from local file.

        Args:
            student_name: Student name.
            filepath: Path to .ipynb file.
            task_key: Task key (e.g., "numpy_i"). If None, auto-detected from content.

        Returns:
            Evaluation object.
        """
        import json
        from pathlib import Path

        # Get or create student
        student = self.db.get_student(student_name)
        if not student:
            student_id = self.db.add_student(Student(name=student_name))
            student = self.db.get_student(student_name)
        else:
            student_id = student["id"]

        # Load notebook
        with open(filepath) as f:
            notebook_json = json.load(f)

        filename = Path(filepath).name

        # Auto-detect task if not provided
        if not task_key:
            cleaned = clean_notebook(notebook_json)
            task_key = classify_task(cleaned, filename)

        # Get assignment
        assignment = self.db.get_assignment(task_key)
        if not assignment:
            parts = task_key.split("_")
            roman = {"i": "I", "ii": "II", "iii": "III"}
            assign_name = " ".join(roman.get(p.lower(), p.capitalize()) for p in parts)
            assignment_id = self.db.add_assignment(Assignment(
                name=assign_name,
                module=task_key,
                topic_key=task_key,
            ))
        else:
            assignment_id = assignment["id"]

        # Get rubric
        rubric_content = self.rubric_agent.get_rubric(task_key)

        # Evaluate (with reference metadata)
        evaluation = self.eval_agent.evaluate(
            notebook_json, student_name, filename, rubric_content,
            topic_key=task_key
        )
        evaluation.student_id = student_id
        evaluation.assignment_id = assignment_id
        evaluation.topic_key = task_key

        # Save to database
        self.db.add_evaluation(evaluation)
        return evaluation

    def generate_student_feedback(self, student_id: int) -> str:
        """Generate feedback report for a student.

        Args:
            student_id: Student ID.

        Returns:
            Markdown report.
        """
        student = self.db.get_student(student_id)
        if not student:
            return "Student not found."

        evaluations = self.db.get_student_evaluations(student_id)

        # Get cohort stats for each assignment
        cohort_stats = {}
        for eval_data in evaluations:
            aid = eval_data["assignment_id"]
            if aid not in cohort_stats:
                cohort_stats[aid] = self.db.get_cohort_stats(aid)

        return self.report_agent.generate_student_report(
            student["name"], evaluations, cohort_stats
        )

    def generate_cohort_report(self, assignment_id: int) -> str:
        """Generate cohort overview report.

        Args:
            assignment_id: Assignment ID.

        Returns:
            Markdown report.
        """
        assignment = self.db.get_assignment(assignment_id)
        if not assignment:
            return "Assignment not found."

        cohort_stats = self.db.get_cohort_stats(assignment_id)

        # Get all evaluations for this assignment
        all_students = self.db.get_all_students()
        evaluations = []
        for student in all_students:
            eval_data = self.db.get_evaluation(student["id"], assignment_id)
            if eval_data:
                evaluations.append(eval_data)

        return self.report_agent.generate_instructor_report(
            assignment["name"], evaluations, cohort_stats
        )

    def send_feedback_email(self, student_id: int, email_config) -> bool:
        """Send feedback email to a student.

        Args:
            student_id: Student ID.
            email_config: Email configuration.

        Returns:
            True if email sent successfully.
        """
        student = self.db.get_student(student_id)
        if not student or not student.get("email"):
            return False

        report = self.generate_student_feedback(student_id)
        body = f"""Hola {student['name']},

Adjunto encontrarás tu informe de feedback personalizado basado en tus evaluaciones recientes.

Saludos,
The Evaluator — Sistema de Evaluación Automatizada
"""
        return send_feedback_email(
            email_config,
            student["email"],
            f"Informe de Feedback — {student['name']}",
            body,
            report,
            f"{student['name']}_feedback.md",
        )
