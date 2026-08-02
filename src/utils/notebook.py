"""Notebook processing utilities."""
import json
from pathlib import Path


def clean_notebook(notebook_json: dict, max_output_chars: int = 800,
                   max_total_chars: int = 15000) -> str:
    """Clean a Jupyter notebook JSON into readable text.

    Args:
        notebook_json: Parsed notebook JSON dict.
        max_output_chars: Max characters per output cell.
        max_total_chars: Max total characters for cleaned notebook.

    Returns:
        Cleaned notebook text.
    """
    cells = notebook_json.get("cells", [])
    clean_text = []

    for i, cell in enumerate(cells):
        cell_type = cell.get("cell_type", "unknown")
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)

        clean_text.append(f"--- Celda {i + 1} ({cell_type}) ---")
        clean_text.append(source.strip())

        if cell_type == "code":
            outputs = cell.get("outputs", [])
            if outputs:
                clean_text.append("## OUTPUTS:")
                for output in outputs:
                    # Skip images
                    if output.get("data", {}).get("image/png") or \
                       output.get("data", {}).get("image/jpeg"):
                        continue

                    text = ""
                    if output.get("output_type") == "stream":
                        text = output.get("text", "")
                    elif output.get("data", {}).get("text/plain"):
                        text = "".join(output["data"]["text/plain"])

                    if text:
                        if len(text) > max_output_chars:
                            text = text[:max_output_chars] + "\n... [Output truncado] ..."
                        clean_text.append(text)

    cleaned = "\n".join(clean_text)
    if len(cleaned) > max_total_chars:
        cleaned = cleaned[:max_total_chars] + "\n\n[Nota: Notebook muy largo, se ha truncado el final]"
    return cleaned


def classify_task(notebook_text: str) -> str:
    """Classify notebook task based on content.

    Args:
        notebook_text: Cleaned notebook text.

    Returns:
        Task key (e.g., "numpy_i", "numpy_ii", "pandas_i").
    """
    lower = notebook_text.lower()

    if "numpy" in lower:
        advanced_keywords = ["structured array", "broadcasting", "eigenvalue", "polynomial"]
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
