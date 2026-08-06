#!/usr/bin/env python3
"""
Structured test runner for The Evaluator.

Uses a single fixed test set (tests/test_set.csv) for all models.
Every model is evaluated on the exact same 31 notebooks.

Evaluation mode:
  - Dual-instance models (8084+8085): ThreadPoolExecutor(2) — both GPUs run concurrently
  - Single-instance models (split or one port): sequential

Usage:
    python3 tests/run_test.py --model gemma_4_12b_q4k_inst1
    python3 tests/run_test.py --model gpt_oss_20b_q6k
"""
import argparse, csv, json, time, re, sys, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

MODEL_DIR = BASE / 'tests' / 'models'
TEST_SET = BASE / 'tests' / 'test_set.csv'
RESULTS_FILE = BASE / 'tests' / 'results' / 'runs.json'


def parse_model_config(config_path):
    """Parse a model config file into a dict."""
    config = {}
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value.isdigit():
                    value = int(value)
                config[key] = value
    return config


def load_test_set():
    """Load the fixed test set."""
    if not TEST_SET.exists():
        print(f"ERROR: Test set not found: {TEST_SET}")
        sys.exit(1)
    notebooks = []
    with open(TEST_SET) as f:
        reader = csv.DictReader(f)
        for row in reader:
            notebooks.append(row)
    return notebooks


def evaluate_one(notebook_info, clients, config, idx, total, lock):
    """Evaluate a single notebook. Assign to client round-robin."""
    import json as j
    from src.agents.orchestrator import Orchestrator
    from src.db import Database

    nb_path = BASE / 'Past Bootcamps/2025-02' / notebook_info['path']
    if not nb_path.exists():
        return {
            'student': notebook_info['student'],
            'filename': notebook_info['filename'],
            'task': notebook_info['task'],
            'deepseek_grade': notebook_info['deepseek_grade'],
            'our_grade': 'ERROR',
            'match': False,
            'time': 0,
            'error': 'notebook not found'
        }

    with open(nb_path) as f:
        notebook = j.load(f)

    rubric_path = Path(config.paths.rubrics_dir) / f"rubric_{notebook_info['task']}.md"
    if not rubric_path.exists():
        return {
            'student': notebook_info['student'],
            'filename': notebook_info['filename'],
            'task': notebook_info['task'],
            'deepseek_grade': notebook_info['deepseek_grade'],
            'our_grade': 'NO_RUBRIC',
            'match': False,
            'time': 0,
            'error': 'rubric not found'
        }

    rubric = rubric_path.read_text()

    # Pick client round-robin
    with lock:
        client_idx = idx % len(clients)
        client = clients[client_idx]

    t0 = time.time()
    try:
        db = Database(config.database.path)
        orch = Orchestrator(db, client, config.paths.rubrics_dir)
        report = orch.eval_agent.evaluate(notebook, notebook_info['student'], notebook_info['filename'], rubric, None)
        elapsed = time.time() - t0
        grade = report.grade.value if hasattr(report.grade, 'value') else str(report.grade)
        match = grade == notebook_info['deepseek_grade']
        symbol = '✅' if match else '❌'
        with lock:
            print(f"  [{elapsed:.0f}s] {symbol} {notebook_info['task']:10s} | {notebook_info['student'][:30]:30s} | {grade:12s} (ds: {notebook_info['deepseek_grade']})")
        return {
            'student': notebook_info['student'],
            'filename': notebook_info['filename'],
            'task': notebook_info['task'],
            'deepseek_grade': notebook_info['deepseek_grade'],
            'our_grade': grade,
            'match': match,
            'time': round(elapsed, 1),
            'error': None
        }
    except Exception as e:
        elapsed = time.time() - t0
        with lock:
            print(f"  [{elapsed:.0f}s] ERROR {notebook_info['filename']}: {e}")
        return {
            'student': notebook_info['student'],
            'filename': notebook_info['filename'],
            'task': notebook_info['task'],
            'deepseek_grade': notebook_info['deepseek_grade'],
            'our_grade': 'ERROR',
            'match': False,
            'time': round(elapsed, 1),
            'error': str(e)
        }


def run_evaluation(model_config, notebooks, config, ports=None):
    """Run evaluations on the test set."""
    from src.config import LLMConfig
    from src.llm import LLMClient

    ports = ports or [model_config['port']]
    clients = []
    for port in ports:
        llm_cfg = LLMConfig(
            provider=model_config.get('provider', 'openai'),
            base_url=f"http://192.168.0.37:{port}/v1",
            model=model_config.get('model', 'gpt-3.5-turbo'),
            api_key=config.llm.api_key,
            temperature=config.llm.temperature,
            top_p=config.llm.top_p,
            top_k=config.llm.top_k,
            seed=config.llm.seed,
            max_tokens=config.llm.max_tokens,
        )
        clients.append(LLMClient(llm_cfg))

    lock = threading.Lock()
    results = [None] * len(notebooks)

    max_workers = len(clients)
    if max_workers == 1:
        # Sequential for single instance
        for i, nb_info in enumerate(notebooks):
            result = evaluate_one(nb_info, clients, config, i, len(notebooks), lock)
            results[i] = result
    else:
        # Concurrent for dual instance
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for i, nb_info in enumerate(notebooks):
                future = executor.submit(evaluate_one, nb_info, clients, config, i, len(notebooks), lock)
                futures[future] = i
            for future in as_completed(futures):
                idx = futures[future]
                results[idx] = future.result()

    return results


def register_run(model_name, results, model_config):
    """Register test run in results file."""
    total_time = sum(r['time'] for r in results)
    avg_time = total_time / len(results) if results else 0
    matches = [r for r in results if r['match']]
    match_rate = len(matches) / len(results) * 100 if results else 0

    grade_dist = {}
    for r in results:
        g = r['our_grade']
        grade_dist[g] = grade_dist.get(g, 0) + 1

    task_stats = {}
    rubrics_used = {}
    for task in ['numpy_i', 'numpy_ii']:
        tr = [r for r in results if r['task'] == task]
        tm = [r for r in tr if r['match']]
        task_stats[task] = {
            'total': len(tr),
            'matches': len(tm),
            'match_rate': round(len(tm) / len(tr) * 100, 1) if tr else 0,
            'avg_time': round(sum(r['time'] for r in tr) / len(tr), 1) if tr else 0,
            'grade_dist': {},
        }
        for r in tr:
            g = r['our_grade']
            task_stats[task]['grade_dist'][g] = task_stats[task]['grade_dist'].get(g, 0) + 1
        rubrics_used[task] = f'rubrics/rubric_{task}.md'

    run = {
        'timestamp': datetime.now().isoformat(),
        'model': model_name,
        'total_notebooks': len(results),
        'total_time': round(total_time, 1),
        'avg_time': round(avg_time, 1),
        'match_rate': round(match_rate, 1),
        'grade_distribution': grade_dist,
        'rubrics_used': rubrics_used,
        'task_stats': task_stats,
        'model_config': model_config,
        'results': results,
    }

    runs_data = json.loads(RESULTS_FILE.read_text()) if RESULTS_FILE.exists() else {'runs': []}
    runs_data['runs'].append(run)
    RESULTS_FILE.write_text(json.dumps(runs_data, indent=2))
    return run


def print_summary(run):
    """Print formatted results summary."""
    print("\n" + "=" * 60)
    print(f"RESULTS: {run['model']}")
    print("=" * 60)
    print(f"Match rate: {run['match_rate']:.1f}% ({sum(1 for r in run['results'] if r['match'])}/{run['total_notebooks']})")
    print(f"Total: {run['total_time']:.0f}s | Avg: {run['avg_time']:.0f}s")
    print(f"\nGrade distribution:")
    for g in ['Excepcional', 'Bien', 'Regular', 'Mal', 'ERROR', 'NO_RUBRIC']:
        if g in run['grade_distribution']:
            print(f"  {g:12s}: {run['grade_distribution'][g]}")
    print(f"\nPer-task:")
    for task in ['numpy_i', 'numpy_ii']:
        if task in run['task_stats']:
            s = run['task_stats'][task]
            print(f"  {task}: {s['match_rate']:.1f}% ({s['matches']}/{s['total']}) | avg {s['avg_time']:.0f}s")
            for g in ['Excepcional', 'Bien', 'Regular', 'Mal']:
                if g in s['grade_dist']:
                    print(f"    {g}: {s['grade_dist'][g]}")


def main():
    parser = argparse.ArgumentParser(description='Test runner for The Evaluator')
    parser.add_argument('--model', required=True, help='Model config name (without .conf)')
    args = parser.parse_args()

    model_config_path = MODEL_DIR / f'{args.model}.conf'
    if not model_config_path.exists():
        print(f"ERROR: Model config not found: {model_config_path}")
        print(f"Available: {', '.join(p.stem for p in MODEL_DIR.glob('*.conf'))}")
        sys.exit(1)

    model_config = parse_model_config(model_config_path)
    notebooks = load_test_set()

    # Detect dual-instance models
    base_name = args.model.replace('_inst1', '').replace('_inst2', '')
    inst1 = MODEL_DIR / f'{base_name}_inst1.conf'
    inst2 = MODEL_DIR / f'{base_name}_inst2.conf'
    if inst1.exists() and inst2.exists():
        cfg1 = parse_model_config(inst1)
        cfg2 = parse_model_config(inst2)
        ports = [cfg1['port'], cfg2['port']]
        print(f"Model: {base_name} (dual instance, concurrent)")
        print(f"Ports: {ports[0]}, {ports[1]}")
    else:
        ports = [model_config['port']]
        print(f"Model: {args.model}")
        print(f"Port: {model_config['port']}")

    print(f"Test set: {len(notebooks)} notebooks")
    print("=" * 60)

    from src.config import get_config
    config = get_config()

    results = run_evaluation(model_config, notebooks, config, ports)
    run = register_run(args.model, results, model_config)
    print_summary(run)


if __name__ == '__main__':
    main()