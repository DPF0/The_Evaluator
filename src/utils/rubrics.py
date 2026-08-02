"""Rubric management utilities."""
from pathlib import Path
from typing import Optional


def load_rubric_from_file(rubrics_dir: str, topic_key: str) -> Optional[str]:
    """Load a rubric from a Markdown file.

    Args:
        rubrics_dir: Path to rubrics directory.
        topic_key: Topic key (e.g., "numpy_i").

    Returns:
        Rubric content as string, or None if not found.
    """
    rubric_path = Path(rubrics_dir) / f"rubric_{topic_key}.md"
    if rubric_path.exists():
        return rubric_path.read_text()
    return None


def load_all_rubrics(rubrics_dir: str) -> dict[str, str]:
    """Load all rubrics from directory.

    Args:
        rubrics_dir: Path to rubrics directory.

    Returns:
        Dict mapping topic_key to rubric content.
    """
    rubrics = {}
    rubrics_path = Path(rubrics_dir)
    for file in rubrics_path.glob("rubric_*.md"):
        key = file.stem.replace("rubric_", "")
        rubrics[key] = file.read_text()
    return rubrics


def save_rubric_to_file(rubrics_dir: str, topic_key: str, content: str) -> None:
    """Save a rubric to a Markdown file.

    Args:
        rubrics_dir: Path to rubrics directory.
        topic_key: Topic key (e.g., "numpy_i").
        content: Rubric content.
    """
    rubric_path = Path(rubrics_dir) / f"rubric_{topic_key}.md"
    rubric_path.write_text(content)
