"""LLM client abstraction for local and cloud backends."""
import json
from typing import Optional
from src.config import LLMConfig


class LLMClient:
    """Client for interacting with LLM backends."""

    def __init__(self, config: LLMConfig):
        self.config = config

    def chat(self, messages: list[dict], system_prompt: Optional[str] = None) -> str:
        """Send chat messages to LLM and return response text."""
        import requests
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "top_k": self.config.top_k,
            "seed": self.config.seed,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }

        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        resp = requests.post(
            f"{self.config.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def chat_structured(self, messages: list[dict], schema: dict,
                        system_prompt: Optional[str] = None) -> dict:
        """Send chat messages and parse response as structured JSON."""
        text = self.chat(messages, system_prompt)
        # Try to extract JSON from response
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        # Try to find JSON block
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Could not parse structured response: {text[:200]}")

    def evaluate_notebook(self, prompt: str) -> str:
        """Evaluate a notebook with the standard system prompt."""
        system_prompt = (
            "Eres un evaluador pedagógico experto en Data Science. "
            "Responde ÚNICAMENTE con el informe en Markdown solicitado. "
            "NO generes bloques de pensamiento, razonamiento interno, "
            "chain-of-thought ni explicaciones previas. "
            "Salta directamente al informe final en español de España."
        )
        return self.chat([{"role": "user", "content": prompt}], system_prompt)

    def generate_rubric(self, assignment_description: str, topic: str) -> str:
        """Generate a rubric for an assignment."""
        system_prompt = (
            "Eres un diseñador curricular experto en Data Science. "
            "Genera una rúbrica de evaluación en formato Markdown. "
            "Responde ÚNICAMENTE con la rúbrica en español de España."
        )
        prompt = f"""Genera una rúbrica de evaluación para:
Tema: {topic}
Descripción de la asignatura: {assignment_description}

La rúbrica debe incluir:
1. Criterios de evaluación principales (completitud, comprensión, correctitud)
2. Criterios secundarios (legibilidad, comentarios)
3. Detalle por ejercicio con claves y errores comunes
4. Escala de calificación (Mal/Regular/Bien/Excepcional)
5. Instrucciones para el evaluador
"""
        return self.chat([{"role": "user", "content": prompt}], system_prompt)

    def generate_feedback_report(self, student_name: str, evaluations: list[dict],
                                  cohort_stats: dict) -> str:
        """Generate a personalized feedback report for a student."""
        system_prompt = (
            "Eres un tutor pedagógico experto en Data Science. "
            "Genera un informe de feedback personalizado en español de España. "
            "El tono debe ser constructivo, motivador y específico."
        )
        prompt = f"""Genera un informe de feedback para {student_name} basado en sus evaluaciones.

Evaluaciones:
{json.dumps(evaluations, indent=2, ensure_ascii=False)}

Estadísticas del grupo:
{json.dumps(cohort_stats, indent=2, ensure_ascii=False)}

El informe debe incluir:
1. Resumen del rendimiento general
2. Fortalezas identificadas
3. Áreas de mejora con recomendaciones específicas
4. Comparativa con el grupo (sin mencionar nombres de otros alumnos)
5. Siguientes pasos recomendados
"""
        return self.chat([{"role": "user", "content": prompt}], system_prompt)
