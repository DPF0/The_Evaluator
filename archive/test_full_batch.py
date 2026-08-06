"""Comprehensive batch test for multiple assignments."""
import concurrent.futures
import json
import time
from pathlib import Path
from src.config import get_config, LLMConfig
from src.db import Database
from src.llm import LLMClient, RoundRobinLLMClient
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

# LLM backend ports for round-robin distribution
LLM_PORTS = ["8084"]


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
                student_name = student_dir.name.split("_assignsubmission")[0]
                # Use filename to distinguish numpy_i vs numpy_ii
                filename = nb.name.lower()
                if "numpy_ii" in filename or "numpy2" in filename:
                    actual_task = "numpy_ii"
                elif "numpy_i" in filename or "numpy1" in filename:
                    actual_task = "numpy_i"
                else:
                    actual_task = task_key  # Use directory-based for others
                all_notebooks.append((student_name, str(nb), actual_task))
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

    # Filter to only notebooks with deepseek evaluations
    notebooks_with_deepseek = [(s, f, t) for s, f, t in notebooks if get_deepseek_grade(f)]
    print(f"Found {len(notebooks)} notebooks total, {len(notebooks_with_deepseek)} with deepseek-r1 evaluations\n")

    if not notebooks_with_deepseek:
        print("No notebooks with deepseek evaluations found. Exiting.")
        return

    notebooks = notebooks_with_deepseek

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

    # Initialize LLM clients for round-robin distribution
    config = get_config()
    base_url = config.llm.base_url.rsplit(":", 1)[0]
    llm_clients = []
    for port in LLM_PORTS:
        port_config = LLMConfig(
            provider=config.llm.provider,
            base_url=f"{base_url}:{port}/v1",
            model=config.llm.model,
            api_key=config.llm.api_key,
            temperature=config.llm.temperature,
            top_p=config.llm.top_p,
            top_k=config.llm.top_k,
            seed=config.llm.seed,
            max_tokens=config.llm.max_tokens,
        )
        llm_clients.append(LLMClient(port_config))

    llm = RoundRobinLLMClient(llm_clients)
    db = Database(config.database.path)
    orchestrator = Orchestrator(db, llm, config.paths.rubrics_dir)

    print(f"Using {len(LLM_PORTS)} LLM backends (ports {LLM_PORTS}), 3 concurrent workers\n")

    # Evaluate concurrently
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(evaluate_one, nb) for nb in notebooks]
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            results.append(r)
            match = "✅" if r["grade"] == r["deepseek"] else "❌"
            print(f"[{r['time']}] {match} {r['task']:20} | {r['student']:30} | {r['grade']:12} (deepseek: {r['deepseek']})")

    # Summary
    print(f"\n{'='*70}")
    print(f"Total: {len(results)} notebooks evaluated")
    ok = [r for r in results if r["status"] == "OK"]
    if ok:
        avg_time = sum(float(r["time"].rstrip("s")) for r in ok) / len(ok)
        times = [float(r["time"].rstrip("s")) for r in ok]
        print(f"Avg time: {avg_time:.1f}s (min: {min(times):.1f}s, max: {max(times):.1f}s)")

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
        if r["status"] == "OK":
            total += 1
            if r["grade"] == r["deepseek"]:
                matches += 1
    if total > 0:
        print(f"  Matches: {matches}/{total} ({matches/total*100:.1f}%)")

    # Per-task breakdown
    print(f"\nPer-task breakdown:")
    tasks = set(r["task"] for r in results)
    for task in sorted(tasks):
        task_results = [r for r in results if r["task"] == task and r["status"] == "OK"]
        task_matches = sum(1 for r in task_results if r["grade"] == r["deepseek"])
        print(f"  {task}: {task_matches}/{len(task_results)} ({task_matches/len(task_results)*100:.1f}%)")

    db.close()


if __name__ == "__main__":
    main()
