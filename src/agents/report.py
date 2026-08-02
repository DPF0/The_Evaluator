"""Report Agent — generates feedback reports for students and instructors."""
from src.llm import LLMClient


class ReportAgent:
    """Agent that generates feedback reports."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate_student_report(self, student_name: str,
                                 evaluations: list[dict],
                                 cohort_stats: dict) -> str:
        """Generate a personalized feedback report for a student.

        Args:
            student_name: Student name.
            evaluations: List of evaluation dicts for the student.
            cohort_stats: Cohort statistics.

        Returns:
            Markdown report.
        """
        return self.llm.generate_feedback_report(
            student_name, evaluations, cohort_stats
        )

    def generate_instructor_report(self, assignment_name: str,
                                    evaluations: list[dict],
                                    cohort_stats: dict) -> str:
        """Generate a cohort overview report for the instructor.

        Args:
            assignment_name: Assignment name.
            evaluations: List of all evaluations for the assignment.
            cohort_stats: Cohort statistics.

        Returns:
            Markdown report.
        """
        system_prompt = (
            "Eres un analista educativo experto en Data Science. "
            "Genera un informe de análisis de cohorte en español de España. "
            "El tono debe ser profesional y orientado a la toma de decisiones."
        )
        prompt = f"""Genera un informe de análisis de cohorte para la asignatura "{assignment_name}".

Estadísticas del grupo:
{cohort_stats}

Evaluaciones individuales:
{evaluations}

El informe debe incluir:
1. Resumen estadístico general
2. Distribución de calificaciones
3. Temas donde el grupo tiene más dificultades
4. Errores más comunes identificados
5. Alumnos que necesitan atención especial
6. Recomendaciones pedagógicas para la siguiente sesión
"""
        return self.llm.chat([{"role": "user", "content": prompt}], system_prompt)
