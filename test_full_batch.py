"""Comprehensive batch test for multiple assignments."""
import concurrent.futures
import json
import time
from pathlib import Path
from src.config import get_config
from src.db import Database
from src.llm import LLMClient
from src.agents.orchestrator import Orchestrator
from src.utils.notebook import clean_notebook, classify_task

# Define assignments to test
ASSIGNMENTS = {
    "numpy_i": {
        "dir": "Past Bootcamps/2025-02/Ejercicios_alumnxs/25FEBBILFTDS-📋 Entrega - Numpy I y II-19349",
        "pattern": "*Numpy_I*.ipynb",
    },
    "numpy_ii": {
        "dir": "Past Bootcamps/2025-02/Ejercicios_alumnxs/25FEBBILFTDS-📋 Entrega - Numpy I y II-19349",
        "pattern": "*Numpy_II*.ipynb",
    },
    "euro12": {
        "dir": "Past Bootcamps/2025-02/Ejercicios_alumnxs/25FEBBILFTDS-📋 Entrega - Euro12 y alcohol_consumption-19356",
        "pattern": "*Euro12*.ipynb",
    },
    "logistic_regression": {
        "dir": "Past Bootcamps/2025-02/Ejercicios_alumnxs/25FEBBILFTDS-📋Entrega 22 - Logistic Regression predict-ad-click-26804",
        "pattern": "*Logistic*click*.ipynb",
    },
}

def find_notebooks(assignments):
    """Find all notebooks for each assignment."""
    all_notebooks = []
    for task_key, config in assignments.items():
        notebook_dir = Path(config["dir"])
        if not notebook_dir.exists():
            print(f"Warning: Directory not found: {notebook_dir}")
            continue
        for student_dir in sorted(notebook_dir.iterdir()):
            if not student_dir.is_dir():
                continue
            for nb in student_dir.glob(config["pattern"]):
                # Extract student name from directory
                student_name = student_dir.name.split("_assignsubmission")[0]
                all_notebooks.append((student_name, str(nb), task_key))
    return all_notebooks


def get_deepseek_grade(nb_path):
    """Get deepseek-r1 grade from historical report."""
    md_path = Path(str(nb_path).replace(".ipynb", ".ipynb_deepseek-r1_32b_v2.md"))
    if md_path.exists():
        content = md_path.read_text()
        for grade in ["Excepcional", "Bien", "Regular", "Mal"]:
            if grade.lower() in content.lower():
                return grade
    return None


def evaluate_one(item):
    """Evaluate a single notebook."""
    student_name, filepath, task_key = item
    start = time.time()
    try:
        result = orchestrator.evaluate_local_notebook(student_name, filepath, task_key)
        elapsed = time.time() - start
        deepseek = get_deepseek_grade(filepath)
        return {
            "student": student_name,
            "filename": Path(filepath).name,
            "task": task_key,
            "grade": result.grade.value,
            "numeric": result.numeric_grade,
            "time": f"{elapsed:.1f}s",
            "deepseek": deepseek or "N/A",
            "status": "OK",
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "student": student_name,
            "filename": Path(filepath).name,
            "task": task_key,
            "grade": "ERROR",
            "numeric": 0,
            "time": f"{elapsed:.1f}s",
            "deepseek": "N/A",
            "status": str(e)[:80],
        }


def main():
    global orchestrator

    notebooks = find_notebooks(ASSIGNMENTS)
    print(f"Found {len(notebooks)} notebooks to evaluate\n")

    # Show notebook sizes
    print("Notebook sizes:")
    for student_name, filepath, task_key in notebooks:
        with open(filepath) as f:
            nb = json.load(f)
        cleaned = clean_notebook(nb)
        raw_size = Path(filepath).stat().st_size
        trunc = " [TRUNCATED]" if "truncado" in cleaned else ""
        print(f"  [{task_key}] {Path(filepath).name}: {raw_size:,}B → {len(cleaned):,} chars{trunc}")

    print()

    # Initialize
    config = get_config()
    db = Database(config.database.path)
    llm = LLMClient(config.llm)
    orchestrator = Orchestrator(db, llm, config.paths.rubrics_dir)

    # Evaluate concurrently
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(evaluate_one, nb) for nb in notebooks]
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            results.append(r)
            match = "✅" if r["grade"] == r["deepseek"] or r["deepseek"] == "N/A" else "❌"
            print(f"[{r['time']}] {match} {r['task']:20} | {r['student']:30} | {r['grade']:12} (deepseek: {r['deepseek']})")

    # Summary
    print(f"\n{'='*70}")
    print(f"Total: {len(results)} notebooks evaluated")
    ok = [r for r in results if r["status"] == "OK"]
    if ok:
        avg_time = sum(float(r["time"].rstrip("s")) for r in ok) / len(ok)
        print(f"Average time: {avg_time:.1f}s")

    # Grade distribution
    print(f"\nGrade distribution:")
    for grade in ["Excepcional", "Bien", "Regular", "Mal"]:
        count = sum(1 for r in results if r["grade"] == grade)
        print(f"  {grade}: {count}")

    # Comparison with deepseek
    print(f"\nComparison with deepseek-r1:")
    matches = 0
    total = 0
    for r in results:
        if r["deepseek"] != "N/A" and r["status"] == "OK":
            total += 1
            if r["grade"] == r["deepseek"]:
                matches += 1
    if total > 0:
        print(f"  Matches: {matches}/{total} ({matches/total*100:.1f}%)")

    db.close()


if __name__ == "__main__":
    main()
