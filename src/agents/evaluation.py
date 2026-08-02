"""Evaluation Agent — evaluates notebooks against rubrics using LLM."""
from src.llm import LLMClient
from src.models import Evaluation, ExerciseIssue, Grade
from src.utils.notebook import clean_notebook, classify_task
from src.utils.rubrics import load_rubric_from_file


class EvaluationAgent:
    """Agent that evaluates student notebooks against rubrics."""

    def __init__(self, llm: LLMClient, rubrics_dir: str = "rubrics"):
        self.llm = llm
        self.rubrics_dir = rubrics_dir

    def evaluate(self, notebook_json: dict, student_name: str,
                 filename: str, rubric_content: str) -> Evaluation:
        """Evaluate a notebook against a rubric.

        Args:
            notebook_json: Parsed notebook JSON.
            student_name: Student name.
            filename: Notebook filename.
            rubric_content: Rubric Markdown content.

        Returns:
            Evaluation with grade and report.
        """
        cleaned = clean_notebook(notebook_json)
        prompt = self._build_prompt(rubric_content, cleaned, student_name, filename)
        raw_response = self.llm.evaluate_notebook(prompt)
        return self._parse_response(raw_response, student_name, filename)

    def _build_prompt(self, rubric: str, notebook_text: str,
                      student_name: str, filename: str) -> str:
        """Build evaluation prompt."""
        return f"""{rubric}

### INSTRUCCIONES DE EVALUACIÓN:
Primero averigua cuántos ejercicios hay en el notebook y verifica que cada uno tenga al menos una celda de código como respuesta. Si no hay código Python en la solución, el ejercicio probablemente está sin resolver. Revisa uno por uno, leyendo cuidadosamente.
Si la respuesta está presente, evalúa la basándote en los criterios de la rúbrica anterior.
Resolver un problema de más de una manera es un plus, siempre que todas las respuestas sean correctas.
Verifica si el código es correcto ejecutándolo mentalmente, paso a paso. Si encuentras algún error, anótalo.

**IMPORTANTE: Aplica la escala de calificación de la rúbrica de forma estricta.**
- Si la mayoría de ejercicios están completados y el código es mayoritariamente correcto, la calificación debe ser 'Bien' o superior.
- 'Regular' se reserva para trabajos con muchos errores conceptuales o incompletos de forma significativa.
- 'Mal' solo si más de la mitad de los ejercicios están sin resolver o hay problemas graves.

### FORMATO DEL INFORME:
Estructura el informe final en español de España como sigue:
- Título del informe con el nombre del alumno y el nombre del archivo.
- Calificación Global del notebook según esta Escala:
    - 'Mal': Las tareas no se entienden, más de la mitad de los ejercicios sin resolver, problemas graves.
    - 'Regular': Muchos problemas con la comprensión de tareas, corrección del código o sintaxis.
    - 'Bien': Buena comprensión de tareas, código mayoritariamente funcional con problemas menores.
    - 'Excepcional': Sin problemas mayores; código limpio y completamente funcional.
- Resumen del rendimiento en factores principales.
- Resumen del rendimiento en factores secundarios.
- Lista de ejercicios con problemas (formato tabla: Nº | Ejercicio | Problema | Recomendación).

Aquí está el notebook a revisar:
**Alumno:** {student_name}
**Archivo:** {filename}
**Contenido (Limpio):**
{notebook_text}"""

    def _parse_response(self, raw_text: str, student_name: str,
                        filename: str) -> Evaluation:
        """Parse LLM response into structured evaluation."""
        import re

        # Extract grade - find grade after "Calificación Global" heading
        grade_text = "Regular"
        match = re.search(
            r"Calificación Global.*?\*\*(Mal|Regular|Bien|Excepcional)\*\*",
            raw_text, flags=re.I | re.DOTALL
        )
        if match:
            grade_text = match[1]
        else:
            # Fallback: any grade mention
            matches = re.findall(r"\b(Mal|Regular|Bien|Excepcional)\b", raw_text, flags=re.I)
            if matches:
                grade_text = matches[0]

        grade = Grade(grade_text)

        # Extract exercise issues
        issues = []
        issue_pattern = re.compile(
            r"(\d+)\.\s*\**Exercise\s*(\d+)\s*\((.+?)\)\**:\s*\n"
            r"\s*-?\s*\**Issue\**:\s*(.+?)\n"
            r"\s*-?\s*\**Recommendation\**:\s*(.+?)(?=\n\n|\n\d+|$)",
            re.I | re.DOTALL
        )
        for match in issue_pattern.finditer(raw_text):
            issues.append(ExerciseIssue(
                exercise_number=int(match.group(2)),
                exercise_name=match.group(3).strip(),
                issue=match.group(4).strip(),
                recommendation=match.group(5).strip(),
            ))

        # Count unresolved exercises
        unresolved = sum(1 for i in issues if "no code" in i.issue.lower() or
                        "sin resolver" in i.issue.lower() or
                        "no provided" in i.issue.lower())

        return Evaluation(
            student_id=0,  # Set by orchestrator
            assignment_id=0,  # Set by orchestrator
            filename=filename,
            grade=grade,
            numeric_grade=grade.numeric,
            markdown_report=raw_text,
            unresolved_exercises=unresolved,
            exercise_issues=issues,
        )
