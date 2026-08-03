"""Notebook processing utilities."""
import json
from pathlib import Path


def clean_notebook(notebook_json: dict) -> str:
    """Clean a Jupyter notebook by removing outputs, keeping all code/markdown intact.

    No truncation - let LLM context window handle it.

    Args:
        notebook_json: Parsed notebook JSON dict.

    Returns:
        Cleaned notebook text with all code/markdown cells preserved.
    """
    cells = notebook_json.get("cells", [])
    clean_text = []

    for i, cell in enumerate(cells):
        cell_type = cell.get("cell_type", "unknown")
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(str(line) for line in source)
        elif not isinstance(source, str):
            source = str(source)

        clean_text.append(f"--- Celda {i + 1} ({cell_type}) ---")
        clean_text.append(source.strip())

    return "\n".join(clean_text)


def classify_task(notebook_text: str, filename: str = "") -> str:
    """Classify notebook task based on content and filename.

    Args:
        notebook_text: Cleaned notebook text.
        filename: Notebook filename (used as fallback for classification).

    Returns:
        Task key (e.g., "numpy_i", "numpy_ii", "pandas_i").
    """
    lower = notebook_text.lower()
    filename_lower = filename.lower()

    # Check filename first (more reliable than content)
    if "numpy_ii" in filename_lower or "numpy2" in filename_lower or "numpy_2" in filename_lower:
        return "numpy_ii"
    if "numpy_i" in filename_lower or "numpy1" in filename_lower or "numpy_1" in filename_lower:
        return "numpy_i"

    # Fallback to content-based classification
    if "numpy" in lower:
        advanced_keywords = ["structured array", "broadcasting", "eigenvalue", "polynomial",
                            "ejercicio 18", "ejercicio 19", "ejercicio 20", "ejercicio 21"]
        if any(kw in lower for kw in advanced_keywords):
            return "numpy_ii"
        return "numpy_i"
    elif "pandas" in lower:
        return "pandas_i"
    elif "matplotlib" in lower:
        return "matplotlib_i"
    elif "seaborn" in lower:
        return "seaborn_i"
    elif "scikit" in lower or "sklearn" in lower:
        return "scikit_i"
    return "unknown"


def load_notebook_from_file(path: str) -> dict:
    """Load a Jupyter notebook from a file.

    Args:
        path: Path to .ipynb file.

    Returns:
        Parsed notebook JSON dict.
    """
    with open(path) as f:
        return json.load(f)


def download_notebook_from_github(github_url: str, filename: str) -> dict:
    """Download a notebook from GitHub.

    Args:
        github_url: GitHub URL to the folder containing the notebook.
        filename: Name of the notebook file.

    Returns:
        Parsed notebook JSON dict.
    """
    import requests
    import re

    # Convert GitHub URL to raw URL
    raw_url = re.sub(
        r"github\.com/([\w-]+/[\w-]+)(/.+|$)",
        r"raw.githubusercontent.com/\1/main\2",
        github_url
    )
    raw_url = raw_url.rstrip("/") + "/" + filename

    resp = requests.get(raw_url, timeout=60)
    resp.raise_for_status()
    return resp.json()
