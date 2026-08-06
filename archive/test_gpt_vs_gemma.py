"""Compare GPT-oss-20b vs Gemma 4 12B on numpy notebooks."""
import json, time, re, sys
from pathlib import Path
from src.config import get_config, LLMConfig
from src.db import Database
from src.llm import LLMClient
from src.agents.orchestrator import Orchestrator

config = get_config()
base_url = config.llm.base_url.rsplit(':', 1)[0]

gpt_config = LLMConfig(
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
gpt_llm = LLMClient(gpt_config)

gemma_config = LLMConfig(
    provider='openai',
    base_url=f'{base_url}:8085/v1',
    model='gemma-4-12b-it-qat-UD-Q4_K_XL',
    api_key='sk-xxx',
    temperature=0.2,
    top_p=0.5,
    top_k=10,
    seed=42,
    max_tokens=8000,
)
gemma_llm = LLMClient(gemma_config)

db = Database(config.database.path)
orch_gpt = Orchestrator(db, gpt_llm, config.paths.rubrics_dir)
orch_gemma = Orchestrator(db, gemma_llm, config.paths.rubrics_dir)

GRADE_MAP = {
    'good': 'Bien', 'regular': 'Regular', 'bad': 'Mal',
    'excellent': 'Excepcional', 'bien': 'Bien', 'mal': 'Mal',
    'excepcional': 'Excepcional'
}

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
for sd in sorted(numpy_dir.iterdir()):
    if not sd.is_dir():
        continue
    for nb in sorted(sd.glob('*Numpy*.ipynb')):
        sn = sd.name.split('_assignsubmission')[0]
        fk = nb.name.lower()
        tk = 'numpy_ii' if 'numpy_ii' in fk or 'numpy2' in fk else 'numpy_i'
        ds = get_deepseek_grade(nb)
        if ds:
            notebooks.append((sn, str(nb), tk))

print(f"Comparing GPT-oss-20b vs Gemma 4 12B on {len(notebooks)} numpy notebooks", flush=True)

gpt_r, gemma_r = [], []
gpt_t, gemma_t = 0, 0

for i, (sn, np_, tk) in enumerate(notebooks, 1):
    with open(np_) as f:
        nb_json = json.load(f)
    rubric = (Path(config.paths.rubrics_dir) / f'rubric_{tk}.md').read_text()
    ds = get_deepseek_grade(Path(np_))

    # GPT-oss
    t0 = time.time()
    try:
        r = orch_gpt.eval_agent.evaluate(nb_json, sn, Path(np_).name, rubric, None)
        gpt_t += time.time() - t0
        g = r.grade.value if hasattr(r.grade, 'value') else str(r.grade)
        gpt_r.append({'grade': g, 'deepseek': ds, 'match': g == ds})
        gm = '✅' if g == ds else '❌'
    except Exception as e:
        gm = f'ERR'
        gpt_r.append({'grade': 'ERR', 'deepseek': ds, 'match': False})

    # Gemma 12B
    t0 = time.time()
    try:
        r = orch_gemma.eval_agent.evaluate(nb_json, sn, Path(np_).name, rubric, None)
        gemma_t += time.time() - t0
        g = r.grade.value if hasattr(r.grade, 'value') else str(r.grade)
        gemma_r.append({'grade': g, 'deepseek': ds, 'match': g == ds})
        gmm = '✅' if g == ds else '❌'
    except Exception as e:
        gmm = f'ERR'
        gemma_r.append({'grade': 'ERR', 'deepseek': ds, 'match': False})

    print(f'{i:2d}/{len(notebooks)} | {sn[:30]:30s} | GPT:{gm} | Gemma:{gmm} | DS:{ds}', flush=True)

gpm = sum(1 for r in gpt_r if r['match'])
gmm_count = sum(1 for r in gemma_r if r['match'])

print(f"\n{'='*70}", flush=True)
print(f"GPT-oss-20b: {gpm}/{len(gpt_r)} ({gpm/len(gpt_r)*100:.1f}%) | Avg: {gpt_t/len(notebooks):.0f}s", flush=True)
print(f"Gemma 4 12B: {gmm_count}/{len(gemma_r)} ({gmm_count/len(gemma_r)*100:.1f}%) | Avg: {gemma_t/len(notebooks):.0f}s", flush=True)
print(f"\nGPT-oss grade distribution:", flush=True)
for g in ['Excepcional', 'Bien', 'Regular', 'Mal']:
    gc = sum(1 for r in gpt_r if r['grade'] == g)
    print(f"  {g}: {gc}", flush=True)
print(f"Gemma 12B grade distribution:", flush=True)
for g in ['Excepcional', 'Bien', 'Regular', 'Mal']:
    gc = sum(1 for r in gemma_r if r['grade'] == g)
    print(f"  {g}: {gc}", flush=True)
