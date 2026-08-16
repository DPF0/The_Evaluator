"""Regression tests for core pipeline logic (no LLM required).

Covers the parts that historically broke:
- task classification (filename fast-path, content scoring, word boundaries)
- grade extraction from LLM responses
- notebook cleaning
- LLM client retry behavior (mocked HTTP)

Run:  python3 -m pytest tests/test_core.py -v
"""
import csv
import json
import sys
import time
from pathlib import Path

import pytest
import requests

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from src.config import LLMConfig
from src.llm import LLMClient
from src.models import Grade
from src.utils.notebook import clean_notebook
from src.utils.task_classifier import classify_task
from src.agents.evaluation import EvaluationAgent


# ---------------------------------------------------------------------------
# Task classification — full regression over the 31-notebook test set
# ---------------------------------------------------------------------------

def _load_test_set() -> list[dict]:
    with open(BASE / "tests" / "test_set.csv") as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("row", _load_test_set(), ids=lambda r: r["filename"])
def test_classify_known_notebook(row):
    nb_path = BASE / "Past Bootcamps/2025-02" / row["path"]
    if not nb_path.exists():
        pytest.skip(f"notebook missing: {row['path']}")
    with open(nb_path) as f:
        nb = json.load(f)
    cleaned = clean_notebook(nb)
    assert classify_task(cleaned, row["filename"]) == row["task"]


# ---------------------------------------------------------------------------
# Task classification — targeted edge cases from past debugging rounds
# ---------------------------------------------------------------------------

NUMPY_I_CODE = (
    "import numpy as np\n"
    "a = np.array([1, 2, 3])\n"
    "b = np.zeros((3, 3))\n"
    "c = np.ones((2, 2))\n"
    "np.sum(a)\n"
)


def test_filename_wins_over_conflicting_content():
    # NumPy II notebooks contain ALL 26 exercises (including NumPy I code);
    # the filename must decide.
    assert classify_task(NUMPY_I_CODE, "Ejercicios Numpy II david.ipynb") == "numpy_ii"


def test_numpy_ii_content_signal():
    text = "import numpy as np\nnp.argsort(arr)\n# ejercicio 18\nbroadcasting"
    assert classify_task(text, "") == "numpy_ii"


def test_numpy_i_content_signal():
    assert classify_task(NUMPY_I_CODE, "") == "numpy_i"


def test_filename_underscores_and_dashes_normalized():
    assert classify_task("", "numpy_ii_final.ipynb") == "numpy_ii"
    assert classify_task("", "Ejercicios Numpy I-david.ipynb") == "numpy_i"


def test_word_boundary_prevents_substring_match():
    # \b must stop "broadcastings" from matching the "broadcasting" pattern
    assert classify_task("broadcastings everywhere", "") == "unknown"


def test_no_signal_returns_unknown():
    assert classify_task("el tiempo hoy es agradable", "nota.ipynb") == "unknown"


# ---------------------------------------------------------------------------
# Notebook cleaning
# ---------------------------------------------------------------------------

def test_clean_notebook_removes_outputs_keeps_code_and_markdown():
    nb = {
        "cells": [
            {"cell_type": "markdown", "source": ["# Titulo\n", "texto"]},
            {
                "cell_type": "code",
                "source": "print(1)\n",
                "outputs": [{"output_type": "stream", "text": ["spam-output"]}],
            },
        ]
    }
    text = clean_notebook(nb)
    assert "# Titulo" in text
    assert "texto" in text
    assert "print(1)" in text
    assert "Celda 1 (markdown)" in text
    assert "Celda 2 (code)" in text
    assert "spam-output" not in text


def test_clean_notebook_handles_string_source():
    nb = {"cells": [{"cell_type": "code", "source": "x = 1"}]}
    assert "x = 1" in clean_notebook(nb)


# ---------------------------------------------------------------------------
# Grade extraction from LLM responses
# ---------------------------------------------------------------------------

def _parse(raw: str) -> "Grade":
    agent = EvaluationAgent(llm=None)
    return agent._parse_response(raw, "Ana", "nb.ipynb").grade


def test_grade_from_calificacion_global_section():
    raw = "# Informe\n**Calificación Global:**\n**Bien**\nResumen..."
    assert _parse(raw) is Grade.BIEN


def test_grade_regular():
    raw = "# Informe\nCalificación Global\n**Regular**"
    assert _parse(raw) is Grade.REGULAR


def test_grade_fallback_to_first_mention():
    raw = "# Informe\nEl trabajo es **Regular** en general.\nResumen."
    assert _parse(raw) is Grade.REGULAR


def test_grade_defaults_to_regular_when_absent():
    raw = "# Informe\nSin mención de nota en el texto."
    assert _parse(raw) is Grade.REGULAR


def test_numeric_grade_mapping():
    assert Grade.MAL.numeric == 3
    assert Grade.REGULAR.numeric == 5
    assert Grade.BIEN.numeric == 7
    assert Grade.EXCEPCIONAL.numeric == 9


def test_exercise_issue_extraction_and_unresolved_count():
    raw = (
        "Calificación Global\n**Regular**\n"
        "\n"
        "1. **Exercise 5 (Reshape)**:\n"
        "   - **Issue**: Sin resolver — no code in cell.\n"
        "   - **Recommendation**: Usa np.reshape.\n"
        "\n"
        "2. **Exercise 7 (Where)**:\n"
        "   - **Issue**: Resultado incorrecto.\n"
        "   - **Recommendation**: Revisa la condición.\n"
    )
    agent = EvaluationAgent(llm=None)
    result = agent._parse_response(raw, "Ana", "nb.ipynb")
    assert len(result.exercise_issues) == 2
    assert result.exercise_issues[0].exercise_number == 5
    assert result.exercise_issues[0].exercise_name == "Reshape"
    assert result.unresolved_exercises == 1


# ---------------------------------------------------------------------------
# LLM client retry behavior (mocked HTTP, no network)
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status_code: int, content: str = "OK"):
        self.status_code = status_code
        self._content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def _make_client() -> LLMClient:
    return LLMClient(LLMConfig(base_url="http://test.local/v1", model="fake-model"))


def _patch_post(monkeypatch, side_effects):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        eff = side_effects[len(calls) - 1]
        if isinstance(eff, Exception):
            raise eff
        return eff

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    return calls


def test_chat_success_first_try(monkeypatch):
    calls = _patch_post(monkeypatch, [FakeResponse(200, "hola")])
    assert _make_client().chat([{"role": "user", "content": "h"}]) == "hola"
    assert len(calls) == 1


def test_chat_retries_connection_error(monkeypatch):
    calls = _patch_post(
        monkeypatch, [requests.ConnectionError("boom"), FakeResponse(200, "ok")]
    )
    assert _make_client().chat([{"role": "user", "content": "h"}]) == "ok"
    assert len(calls) == 2


def test_chat_does_not_retry_4xx(monkeypatch):
    calls = _patch_post(monkeypatch, [FakeResponse(400), FakeResponse(200, "ok")])
    with pytest.raises(requests.HTTPError):
        _make_client().chat([{"role": "user", "content": "h"}])
    assert len(calls) == 1


def test_chat_retries_5xx_then_succeeds(monkeypatch):
    calls = _patch_post(monkeypatch, [FakeResponse(500), FakeResponse(503), FakeResponse(200, "ok")])
    assert _make_client().chat([{"role": "user", "content": "h"}]) == "ok"
    assert len(calls) == 3


def test_chat_gives_up_after_max_retries(monkeypatch):
    calls = _patch_post(monkeypatch, [FakeResponse(500)] * 3)
    with pytest.raises(requests.HTTPError):
        _make_client().chat([{"role": "user", "content": "h"}])
    assert len(calls) == 3


def test_chat_retries_timeout(monkeypatch):
    calls = _patch_post(monkeypatch, [requests.Timeout("slow"), FakeResponse(200, "ok")])
    assert _make_client().chat([{"role": "user", "content": "h"}]) == "ok"
    assert len(calls) == 2
