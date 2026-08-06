"""Test GPT-oss-20b on numpy notebooks only (with rubrics)."""
import json, time, re, sys
from pathlib import Path
from src.config import get_config, LLMConfig
from src.db import Database
from src.llm import LLMClient, RoundRobinLLMClient
from src.agents.orchestrator import Orchestrator

config = get_config()
base_url = config.llm.base_url.rsplit(':', 1)[0]
port_config = LLMConfig(
    provider=config.llm.provider,
    base_url=f'{base_url}:8084/v1',
    model=config.llm.model,
    api_key=config.llm.api_key,
    temperature=config.llm.temperature,
    top_p=config.llm.top_p,
    top_k=config.llm.top_k,
    seed=config.llm.seed,
    max_tokens=config.llm.max_tokens,
)
llm = RoundRobinLLMClient([LLMClient(port_config)])
db = Database(config.database.path)
orchestrator = Orchestrator(db, llm, config.paths.rubrics_dir)

GRADE_MAP = {'good': 'Bien', 'regular': 'Regular', 'bad': 'Mal', 'excellent': 'Excepcional',
             'bien': 'Bien', 'mal': 'Mal', 'excepcional': 'Excepcional'}

def get_deepseek_grade(nb_path):
    md_path = Path(str(nb_path).replace('.ipynb', '.ipynb_deepseek-r1_32b_v2.md'))
    if not md_path.exists():
        return None
    content = md_path.read_text().lower()
    match = re.search(r'global grade:\s*\*\*(\w+)\*\*', content)
    if match:
        return GRADE_MAP.get(match.group(1).lower())
    for eng, esp in GRADE_MAP.items():
        if eng in content:
            return esp
    return None

numpy_dir = Path('Past Bootcamps/2025-02/Ejercicios_alumnxs/25FEBBILFTDS-\U0001f4cb Entrega - Numpy I y II-19349')
notebooks = []
for student_dir in sorted(numpy_dir.iterdir()):
    if not student_dir.is_dir():
        continue
    for nb in sorted(student_dir.glob('*Numpy*.ipynb')):
        student_name = student_dir.name.split('_assignsubmission')[0]
        filename = nb.name.lower()
        task_key = 'numpy_ii' if 'numpy_ii' in filename or 'numpy2' in filename else 'numpy_i'
        deepseek = get_deepseek_grade(nb)
        if deepseek:
            notebooks.append((student_name, str(nb), task_key))

log_path = Path('/tmp/gpt20b_numpy_results.log')
sys.stdout = open(log_path, 'w')
sys.stderr = sys.stdout

print(f"Testing {len(notebooks)} numpy notebooks (with rubrics only)\n")

total_time = 0
results = []
for i, (student_name, nb_path, task_key) in enumerate(notebooks, 1):
    t0 = time.time()
    try:
        with open(nb_path) as f:
            nb_json = json.load(f)
        rubric = (Path(config.paths.rubrics_dir) / f'rubric_{task_key}.md').read_text()
        eval_result = orchestrator.eval_agent.evaluate(nb_json, student_name, Path(nb_path).name, rubric, None)
        elapsed = time.time() - t0
        total_time += elapsed
        grade = eval_result.grade
        deepseek = get_deepseek_grade(Path(nb_path))
        match = grade == deepseek
        marker = '✅' if match else '❌'
        print(f'[{elapsed:.0f}s] {marker} {task_key:10} | {student_name:35} | {grade:12} (ds: {deepseek})')
        results.append({'grade': grade, 'deepseek': deepseek, 'match': match, 'task': task_key})
    except Exception as e:
        elapsed = time.time() - t0
        total_time += elapsed
        print(f'[{elapsed:.0f}s] ❌ ERROR: {e}')

matches = sum(1 for r in results if r['match'])
print(f"\n{'='*70}")
print(f"Completed: {len(results)}/{len(notebooks)}")
print(f"Matches: {matches}/{len(results)} ({matches/len(results)*100:.1f}%)")
print(f"Total time: {total_time:.0f}s | Avg: {total_time/len(notebooks):.0f}s")
print(f"\nGrade distribution:")
for g in ['Excepcional', 'Bien', 'Regular', 'Mal']:
    cnt = sum(1 for r in results if r['grade'] == g)
    print(f"  {g}: {cnt}")
for task in ['numpy_i', 'numpy_ii']:
    tr = [r for r in results if r['task'] == task]
    tm = sum(1 for r in tr if r['match'])
    print(f"  {task}: {tm}/{len(tr)} ({tm/len(tr)*100:.1f}%)")
