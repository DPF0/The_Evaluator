"""Rubric Agent — generates and manages rubrics."""
from src.llm import LLMClient
from src.models import Rubric
from src.utils.rubrics import load_rubric_from_file, save_rubric_to_file


class RubricAgent:
    """Agent that generates and manages evaluation rubrics."""

    def __init__(self, llm: LLMClient, rubrics_dir: str = "rubrics"):
        self.llm = llm
        self.rubrics_dir = rubrics_dir

    def get_rubric(self, topic_key: str) -> str:
        """Get rubric for a topic.

        Tries database first, then file system.

        Args:
            topic_key: Topic key (e.g., "numpy_i").

        Returns:
            Rubric content as string.
        """
        content = load_rubric_from_file(self.rubrics_dir, topic_key)
        if content:
            return content
        return self._default_rubric(topic_key)

    def generate_rubric(self, assignment_name: str, module: str,
                        topic: str, description: str,
                        num_exercises: int = 0) -> Rubric:
        """Generate a rubric using LLM.

        Args:
            assignment_name: Name of the assignment.
            module: Module name.
            topic: Topic key.
            description: Assignment description.
            num_exercises: Number of exercises.

        Returns:
            Generated Rubric object.
        """
        content = self.llm.generate_rubric(description, topic)
        rubric = Rubric(
            topic_key=topic,
            assignment_name=assignment_name,
            module=module,
            num_exercises=num_exercises,
            content=content,
        )
        # Save to file
        save_rubric_to_file(self.rubrics_dir, topic, content)
        return rubric

    def _default_rubric(self, topic_key: str) -> str:
        """Return default rubric if none found.

        Args:
            topic_key: Topic key.

        Returns:
            Default rubric content.
        """
        return f"""# Rúbrica de Evaluación: {topic_key}

## Criterios de Evaluación

### Factores Principales (70% del peso)

#### 1. Completitud (25%)
**¿Todos los ejercicios tienen al menos una celda de código como respuesta?**

| Nivel | Criterio |
|-------|----------|
| Excelente (9-10) | Todos los ejercicios completados con código ejecutable |
| Bien (7-8) | Mayoría completados (1-4 sin resolver) |
| Regular (5-6) | Mitad completados (5-9 sin resolver) |
| Insuficiente (3-4) | Menos de la mitad completados |

#### 2. Comprensión de la Tarea (25%)
**¿El estudiante usa el enfoque correcto y las funciones apropiadas?**

| Nivel | Indicadores |
|-------|-------------|
| Excelente | Usa siempre la función correcta; entiende la lógica |
| Bien | Usa funciones correctas en la mayoría |
| Regular | Mezcla funciones correctas con enfoques no óptimos |
| Insuficiente | No comprende los conceptos básicos |

#### 3. Correctitud de las Respuestas (20%)
**¿El código produce el output esperado sin errores?**

| Nivel | Criterio |
|-------|----------|
| Excelente | Todas las respuestas correctas |
| Bien | 80-95% correctas |
| Regular | 60-79% correctas |
| Insuficiente | Menos del 60% correctas |

### Factores Secundarios (30% del peso)

#### 4. Legibilidad del Código (15%)
#### 5. Comentarios y Documentación (15%)

## Escala de Calificación

| Nota | Calificación | Criterio |
|------|-------------|----------|
| 9-10 | Excepcional | Todo perfecto + código impecable |
| 7-8 | Bien | Completado + mayoritariamente correcto |
| 5-6 | Regular | Completado con errores o incompleto pero razonable |
| 3-4 | Mal | Muy incompleto o incorrecto |
"""
