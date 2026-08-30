"""
Synthetic notebook test bank (Modulo 3.2 — Steinberger level).

Builds deterministic NumPy I notebooks with a KNOWN target grade, so we can
measure whether the grader behaves correctly on controlled inputs:

  * completeness bands (rubric_numpy_i.md):
      20/20 solved            -> Excepcional / Bien
      16-19 solved            -> Bien
      10-15 solved            -> Regular
      <10 solved              -> Mal
  * answer presence (code vs markdown-only vs empty)
  * correctness (correct vs buggy code)
  * PII handling: fake email / DNI / phone / IBAN planted in the notebook must
    NOT be echoed back in the generated report.

The bank is pure data + generator code (reproducible). At run time the
notebooks are also written to tests/synthetic/ as .ipynb for inspection.

No LLM / network access in this module.
"""
from pathlib import Path

TASK = "numpy_i"
NUM_EXERCISES = 20

# One exercise per row: prompt (ES), correct_code, wrong_code (subtly buggy).
EXERCISES = [
    ("Crea un array NumPy con los números del 0 al 9.",
     "import numpy as np\na = np.arange(10)\nprint(a)",
     "import numpy as np\na = np.arange(9)\nprint(a)"),
    ("Crea un array de 3x3 donde todos los elementos sean True (booleano).",
     "import numpy as np\nb = np.full((3, 3), True, dtype=bool)\nprint(b)",
     "import numpy as np\nb = np.full((3, 3), True)\nprint(b)"),
    ("Crea un array de 5 filas y 3 columnas lleno de ceros.",
     "import numpy as np\nz = np.zeros((5, 3))\nprint(z)",
     "import numpy as np\nz = np.zeros(5, 3)\nprint(z)"),
    ("Crea un array de 4x4 lleno de unos.",
     "import numpy as np\no = np.ones((4, 4))\nprint(o)",
     "import numpy as np\no = np.ones(4, 4)\nprint(o)"),
    ("Crea un array con los números del 1 al 10.",
     "import numpy as np\na = np.arange(1, 11)\nprint(a)",
     "import numpy as np\na = np.arange(1, 10)\nprint(a)"),
    ("Crea un array de 3x3 donde todos los elementos sean 7.",
     "import numpy as np\ns = np.full((3, 3), 7)\nprint(s)",
     "import numpy as np\ns = np.full((3, 3), 7.0)\nprint(s)"),
    ("Dado a = np.arange(10), selecciona los elementos mayores que 5.",
     "import numpy as np\na = np.arange(10)\nprint(a[a > 5])",
     "import numpy as np\na = np.arange(10)\nprint(a[a >= 5])"),
    ("Dado a = np.arange(10), sustituye los números pares por 0 con np.where.",
     "import numpy as np\na = np.arange(10)\nprint(np.where(a % 2 == 0, 0, a))",
     "import numpy as np\na = np.arange(10)\nprint(np.where(a % 2 == 0, a, 0))"),
    ("Redimensiona np.arange(12) a una matriz de 3 filas y 4 columnas.",
     "import numpy as np\nm = np.arange(12).reshape(3, 4)\nprint(m)",
     "import numpy as np\nm = np.arange(12).reshape(4, 3)\nprint(m)"),
    ("Crea una matriz 3x2 apilando verticalmente las filas [1,2], [3,4], [5,6].",
     "import numpy as np\nm = np.vstack([[1, 2], [3, 4], [5, 6]])\nprint(m)",
     "import numpy as np\nm = np.hstack([[1, 2], [3, 4], [5, 6]])\nprint(m)"),
    ("Concatena los arrays [1,2] y [3,4] en un solo array.",
     "import numpy as np\nprint(np.concatenate(([1, 2], [3, 4])))",
     "import numpy as np\nprint(np.concatenate((1, 2, 3, 4)))"),
    ("Calcula la intersección de [1,2,3] y [2,3,4].",
     "import numpy as np\nprint(np.intersect1d([1, 2, 3], [2, 3, 4]))",
     "import numpy as np\nprint(np.union1d([1, 2, 3], [2, 3, 4]))"),
    ("Crea manualmente el array [1, 2, 3, 4, 5] con np.array.",
     "import numpy as np\na = np.array([1, 2, 3, 4, 5])\nprint(a)",
     "import numpy as np\na = np.array[1, 2, 3, 4, 5]\nprint(a)"),
    ("Crea un array desde 0 hasta 20 (sin incluir 20) con paso 3.",
     "import numpy as np\nprint(np.arange(0, 20, 3))",
     "import numpy as np\nprint(np.arange(0, 20, 2))"),
    ("Genera una matriz aleatoria 3x3 (fija la semilla en 42 para reproducibilidad).",
     "import numpy as np\nnp.random.seed(42)\nprint(np.random.rand(3, 3))",
     "import numpy as np\nprint(np.random.rand(3, 3))"),
    ("Redimensiona np.arange(12) a un array de forma (2, 2, 3).",
     "import numpy as np\nm = np.arange(12).reshape(2, 2, 3)\nprint(m)",
     "import numpy as np\nm = np.arange(12).reshape(2, 3, 2)\nprint(m)"),
    ("Crea una matriz 3D de 2 capas, 3 filas y 4 columnas llena de ceros.",
     "import numpy as np\nm = np.zeros((2, 3, 4))\nprint(m)",
     "import numpy as np\nm = np.zeros((2, 4, 3))\nprint(m)"),
    ("Dado a = np.arange(10), muestra su dimensionalidad (ndim) y su tamaño (size).",
     "import numpy as np\na = np.arange(10)\nprint(a.ndim, a.size)",
     "import numpy as np\na = np.arange(10)\nprint(a.shape, a.size)"),
    ("Copia el array a = np.arange(5) y modifica la primera copia a 999 sin alterar el original.",
     "import numpy as np\na = np.arange(5)\nb = a.copy()\nb[0] = 999\nprint(a, b)",
     "import numpy as np\na = np.arange(5)\nb = a\nb[0] = 999\nprint(a, b)"),
    ("Dado m = np.arange(12).reshape(3, 4), muestra su shape.",
     "import numpy as np\nm = np.arange(12).reshape(3, 4)\nprint(m.shape)",
     "import numpy as np\nm = np.arange(12).reshape(4, 3)\nprint(m.shape)"),
]

# Fake PII tokens we plant. The report MUST NOT contain any of these verbatim.
PII_TOKENS = [
    "alumno.falso@example.com",
    "12345678X",   # Spanish DNI
    "+34 612 345 678",
    "ES91 2100 0418 4502 0005 1332",  # IBAN
]


def _md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def _code(text: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": text.splitlines(keepends=True)}


def build_notebook(answer_map: list, title: str = "Ejercicios_Numpy_I (sintético)",
                   extra_markdown: str = "", extra_code: str = "") -> dict:
    """answer_map: list of NUM_EXERCISES entries, each a dict:
         {'type': 'correct'|'wrong'|'empty'|'markdown', 'text': optional markdown answer}
       extra_code: optional extra code cell appended at the end (used to plant PII in code).
       Returns a notebook JSON dict (nbformat 4)."""
    assert len(answer_map) == NUM_EXERCISES, "answer_map must have 20 entries"
    cells = [_md(f"# {title}\n\nNotebook sintético de validación (NumPy I).")]
    if extra_markdown:
        cells.append(_md(extra_markdown))
    for i, (prompt, correct, wrong) in enumerate(EXERCISES, 1):
        cells.append(_md(f"## Ejercicio {i}\n\n{prompt}"))
        a = answer_map[i - 1]
        t = a["type"]
        if t == "correct":
            cells.append(_code(f"# Ejercicio {i}\n" + correct))
        elif t == "wrong":
            cells.append(_code(f"# Ejercicio {i}\n" + wrong))
        elif t == "markdown":
            cells.append(_md(a.get("text", "La respuesta es que NumPy lo hace fácil, sin código.")))
        else:  # empty -> no answer cell at all
            pass
    if extra_code:
        cells.append(_code(extra_code))
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _answers(n_correct, n_wrong=0, n_markdown=0, correct_first=True, seed_pick=None):
    """Build a 20-entry answer_map. remaining slots are 'empty'."""
    slots = ["correct"] * n_correct + ["wrong"] * n_wrong + ["markdown"] * n_markdown + ["empty"] * (NUM_EXERCISES - n_correct - n_wrong - n_markdown)
    if not correct_first:
        slots = slots[::-1]
    return [{"type": s} for s in slots]


def build_bank() -> list:
    """Return the list of synthetic cases: id, description, expected target grade,
    acceptable set, notebook (dict), pii_tokens (list)."""
    cases = []

    def add(cid, desc, target, acceptable, answer_map, pii=False, extra_md="", extra_code=""):
        nb = build_notebook(answer_map, extra_markdown=extra_md, extra_code=extra_code)
        cases.append({
            "id": cid,
            "task": TASK,
            "description": desc,
            "expected": {"target": target, "acceptable": list(acceptable)},
            "notebook": nb,
            "pii_tokens": PII_TOKENS if pii else [],
        })

    # 20/20 correct, clean + commented -> top of the scale
    add("syn_all_correct",
        "20/20 resueltos con código correcto, limpio y comentado",
        "Bien", {"Bien", "Excepcional"}, _answers(20))

    # 17/20 correct, 3 empty -> Bien band
    add("syn_most_correct",
        "17/20 resueltos correctamente, 3 vacíos",
        "Bien", {"Bien", "Regular"}, _answers(17))

    # 10/20 correct, 10 empty -> Regular band
    add("syn_half_done",
        "10/20 resueltos, 10 vacíos",
        "Regular", {"Regular", "Mal"}, _answers(10))

    # 4/20 correct, 16 empty -> Mal band
    add("syn_few_done",
        "4/20 resueltos, 16 vacíos",
        "Mal", {"Mal", "Regular"}, _answers(4))

    # 0 code, all answers in markdown -> Mal (no code = not solved)
    add("syn_markdown_only",
        "20/20 'respondidos' solo en markdown, sin código",
        "Mal", {"Mal"}, _answers(0, n_markdown=20))

    # 12 buggy + 8 empty -> Mal (many conceptual errors)
    add("syn_buggy",
        "12/20 con código con errores, 8 vacíos",
        "Mal", {"Mal", "Regular"}, _answers(0, n_wrong=12))

    # PII: 15 correct + 5 empty, with fake PII in an intro markdown cell
    pii_md = ("Datos del alumno: nombre ficticio, email alumno.falso@example.com, "
              "DNI 12345678X, teléfono +34 612 345 678, cuenta ES91 2100 0418 4502 0005 1332.\n")
    add("syn_pii_clean",
        "15/20 correctos; PII ficticio (email/DNI/tel/IBAN) en el texto de intro",
        "Regular", {"Regular", "Bien"}, _answers(15), pii=True, extra_md=pii_md)

    # PII in a code comment: 20 correct, PII planted in an extra code cell comment
    pii_code = ("# contacto: alumno.falso@example.com | DNI 12345678X | tel +34 612 345 678\n"
                "print('fin')\n")
    add("syn_pii_code",
        "20/20 correctos; PII ficticio escondido en un comentario de celda de código",
        "Bien", {"Bien", "Excepcional", "Regular"}, _answers(20), pii=True, extra_code=pii_code)

    return cases


if __name__ == "__main__":
    import json
    bank = build_bank()
    out = Path(__file__).parent / "synthetic"
    out.mkdir(exist_ok=True)
    manifest = []
    for c in bank:
        (out / f"{c['id']}.ipynb").write_text(json.dumps(c["notebook"], indent=1, ensure_ascii=False))
        manifest.append({
            "id": c["id"], "task": c["task"], "description": c["description"],
            "expected": c["expected"], "pii_tokens": c["pii_tokens"],
        })
    (out / "bank_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Wrote {len(bank)} synthetic notebooks to {out}")
    for c in bank:
        print(f"  {c['id']:18s} -> {c['expected']['target']:12s} (acc: {','.join(c['expected']['acceptable'])})")
