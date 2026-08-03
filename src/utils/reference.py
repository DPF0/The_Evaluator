"""Reference notebook analysis — extracts exercise metadata from reference notebooks."""
import json
from pathlib import Path
from typing import Optional


def analyze_reference_notebook(notebook_path: str) -> dict:
    """Analyze a reference notebook and extract exercise metadata.

    Args:
        notebook_path: Path to the reference notebook.

    Returns:
        Dictionary with exercise metadata.
    """
    with open(notebook_path) as f:
        nb = json.load(f)

    exercises = []
    current = None

    for i, cell in enumerate(nb["cells"]):
        src = "".join(cell["source"]).strip()
        cell_type = cell["cell_type"]

        # Detect exercise headers
        if (
            ("## Ejercicio" in src or "### Step" in src or "## " in src)
            and cell_type == "markdown"
        ):
            if current:
                exercises.append(current)
            current = {
                "name": src[:80],
                "requires_code": False,
                "code_cells": 0,
                "cell_index": i,
            }
        elif current and cell_type == "code" and src:
            current["requires_code"] = True
            current["code_cells"] += 1

    if current:
        exercises.append(current)

    return {
        "total_exercises": len(exercises),
        "exercises_requiring_code": sum(1 for e in exercises if e["requires_code"]),
        "exercises": exercises,
    }


def format_reference_for_prompt(metadata: dict) -> str:
    """Format reference metadata for the evaluation prompt.

    Args:
        metadata: Reference metadata dictionary (from DB row).

    Returns:
        Formatted string for the evaluation prompt.
    """
    if not metadata:
        return ""

    # metadata is a DB row with exercises_json string
    import json as json_mod

    exercises_json = metadata.get("exercises_json", "[]")
    exercises = json_mod.loads(exercises_json) if isinstance(exercises_json, str) else exercises_json
    code_required = metadata.get("exercises_requiring_code", 0)
    total = metadata.get("total_exercises", 0)

    lines = [
        f"### INFORMACIÓN DEL NOTEBOOK DE REFERENCIA:",
        f"- Total ejercicios: {total}",
        f"- Ejercicios que requieren código: {code_required}",
    ]

    # List exercises without code (if any)
    no_code = [e for e in exercises if not e.get("requires_code")]
    if no_code:
        lines.append("- Ejercicios que NO requieren código:")
        for e in no_code:
            lines.append(f"    - {e['name']}")

    if code_required == total:
        lines.append(
            "**IMPORTANTE:** TODOS los ejercicios requieren al menos una celda de código. "
            "Respuestas solo en markdown están incompletas."
        )

    return "\n".join(lines)


def download_reference_notebooks(
    repo_url: str = "TheBridge-BBK-Bootcamps/2025-OCT-BILBAO-FT-Data-Science",
    output_dir: str = "/tmp/refs",
) -> dict[str, str]:
    """Download reference notebooks from the course repository.

    Args:
        repo_url: GitHub repository URL.
        output_dir: Directory to save notebooks.

    Returns:
        Dictionary mapping task keys to notebook paths.
    """
    import urllib.request

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    raw_base = f"https://raw.githubusercontent.com/{repo_url}/main"
    notebooks = {
        "numpy_i": (
            "2-Data_Analysis/1-Numpy/Practica/Ejercicios_Numpy_I.ipynb",
            "Ejercicios_Numpy_I.ipynb",
        ),
        "numpy_ii": (
            "2-Data_Analysis/1-Numpy/Practica/Ejercicios_Numpy_II.ipynb",
            "Ejercicios_Numpy_II.ipynb",
        ),
        "euro12": (
            "2-Data_Analysis/2-Pandas/Practica/3-Euro12/Euro12.ipynb",
            "Euro12.ipynb",
        ),
        "logistic_regression": (
            "3-Machine_Learning/1-Supervisado/2-Classification/"
            "4-Logistic_Regression/ejercicios/Logistic-regression%20predict-ad-click.ipynb",
            "logistic_predict_ad_click.ipynb",
        ),
    }

    paths = {}
    for task_key, (remote_path, filename) in notebooks.items():
        url = f"{raw_base}/{remote_path}"
        local_path = str(Path(output_dir) / filename)
        try:
            urllib.request.urlretrieve(url, local_path)
            paths[task_key] = local_path
            print(f"Downloaded: {task_key} → {local_path}")
        except Exception as e:
            print(f"Failed to download {task_key}: {e}")

    return paths


def sync_references_to_db(db, output_dir: str = "/tmp/refs") -> None:
    """Analyze reference notebooks and store metadata in database.

    Args:
        db: Database instance.
        output_dir: Directory containing reference notebooks.
    """
    import json as json_mod

    notebooks = {
        "numpy_i": "Ejercicios_Numpy_I.ipynb",
        "numpy_ii": "Ejercicios_Numpy_II.ipynb",
        "euro12": "Euro12.ipynb",
        "logistic_regression": "logistic_predict_ad_click.ipynb",
    }

    for task_key, filename in notebooks.items():
        nb_path = str(Path(output_dir) / filename)
        if not Path(nb_path).exists():
            print(f"Skipping {task_key}: {nb_path} not found")
            continue

        metadata = analyze_reference_notebook(nb_path)
        exercises_json = json_mod.dumps(metadata["exercises"], ensure_ascii=False)

        db.add_reference_metadata(
            topic_key=task_key,
            total_exercises=metadata["total_exercises"],
            exercises_requiring_code=metadata["exercises_requiring_code"],
            exercises_json=exercises_json,
        )
        print(
            f"Stored reference metadata for {task_key}: "
            f"{metadata['exercises_requiring_code']}/{metadata['total_exercises']} require code"
        )
