"""Batch test script for concurrent evaluation."""
import concurrent.futures
import json
import time
from pathlib import Path
from src.config import get_config
from src.db import Database
from src.llm import LLMClient
from src.agents.orchestrator import Orchestrator
from src.utils.notebook import clean_notebook

notebook_dir = Path("Past Bootcamps/2025-02/Ejercicios_alumnxs/25FEBBILFTDS-📋 Entrega - Numpy I y II-19349")
notebooks = []
for student_dir in sorted(notebook_dir.iterdir()):
    if not student_dir.is_dir():
        continue
    for nb in student_dir.glob("*Numpy_I*.ipynb"):
        notebooks.append((student_dir.name, str(nb)))
    if len(notebooks) >= 6:
        break

print(f"Testing {len(notebooks)} notebooks concurrently\n")
print("Notebook sizes (checking truncation):")
for student_name, filepath in notebooks:
    with open(filepath) as f:
        nb = json.load(f)
    cleaned = clean_notebook(nb)
    raw_size = Path(filepath).stat().st_size
    trunc_marker = " [TRUNCATED]" if "truncado" in cleaned else ""
    print(f"  {Path(filepath).name}: {raw_size:,}B raw → {len(cleaned):,} chars cleaned{trunc_marker}")

print()
config = get_config()
db = Database(config.database.path)
llm = LLMClient(config.llm)
orchestrator = Orchestrator(db, llm, config.paths.rubrics_dir)

def evaluate_one(item):
    student_name, filepath = item
    start = time.time()
    try:
        result = orchestrator.evaluate_local_notebook(student_name, filepath)
        elapsed = time.time() - start
        return {"student": student_name, "grade": result.grade.value, "numeric": result.numeric_grade, "time": f"{elapsed:.1f}s", "status": "OK"}
    except Exception as e:
        elapsed = time.time() - start
        return {"student": student_name, "grade": "ERROR", "numeric": 0, "time": f"{elapsed:.1f}s", "status": str(e)[:80]}

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(evaluate_one, nb) for nb in notebooks]
    for future in concurrent.futures.as_completed(futures):
        r = future.result()
        print(f"[{r['time']}] {r['student']}: {r['grade']} ({r['numeric']}) - {r['status']}")

db.close()
