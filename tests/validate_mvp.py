#!/usr/bin/env python3
"""
MVP validation runner (Modulo 3.2 — Pro + Steinberger levels).

Runs, against the (dual-instance) Gemma server, the full validation battery:

  A. Correctness on the fixed 31-notebook set (read from the latest runs.json run)
       - exact match, within-1-step (adjacent) match, MAE (3/5/7/9), Cohen's kappa,
         confusion matrix, per-task breakdown, latency.
  B. Report format robustness  (deterministic checks on generated reports)
  C. Consistency               (same real notebook graded N times -> self-agreement)
  D. Sensitivity               (worsen one cell -> grade must not increase)
  E. PII handling              (planted fake PII must NOT leak into the report)
  + synthetic test bank         (controlled inputs with known target grades)

Writes tests/results/validation.json and prints a summary.
Requires the Gemma servers running on ports 8084 + 8085.
"""
import sys, json, time, csv, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import metrics as M
from synthetic_bank import build_bank, PII_TOKENS
from src.config import get_config, LLMConfig
from src.llm import LLMClient
from src.agents.orchestrator import Orchestrator
from src.db import Database
from src.utils.notebook import clean_notebook

PORTS = [8084, 8085]
RESULTS_OUT = BASE / 'tests' / 'results' / 'validation.json'
RUBRICS = BASE / 'rubrics'


def make_clients():
    config = get_config()
    clients = [
        LLMClient(LLMConfig(base_url=f"http://192.168.0.37:{p}/v1", model="gpt-3.5-turbo",
                            api_key=config.llm.api_key))
        for p in PORTS
    ]
    return clients, config


def evaluate(job, clients, config, db, lock, idx):
    """job = dict(notebook, student, filename, task). Round-robin across clients."""
    client = clients[idx % len(clients)]
    rubric = (RUBRICS / f"rubric_{job['task']}.md").read_text()
    t0 = time.time()
    try:
        orch = Orchestrator(db, client, 'rubrics')
        rep = orch.eval_agent.evaluate(job['notebook'], job['student'], job['filename'], rubric, None)
        dt = time.time() - t0
        grade = rep.grade.value
        with lock:
            print(f"    [{dt:4.0f}s] {job['task']:9s} {job['filename'][:28]:28s} -> {grade}")
        return {'grade': grade, 'report': rep.markdown_report, 'time': round(dt, 1), 'error': None}
    except Exception as e:
        dt = time.time() - t0
        with lock:
            print(f"    [{dt:4.0f}s] ERROR {job['filename']}: {e}")
        return {'grade': 'ERROR', 'report': '', 'time': round(dt, 1), 'error': str(e)}


def run_many(jobs, clients, config, db, max_workers=2):
    lock = threading.Lock()
    out = [None] * len(jobs)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(evaluate, j, clients, config, db, lock, i): i for i, j in enumerate(jobs)}
        for f in __import__('concurrent.futures', fromlist=['as_completed']).as_completed(futs):
            out[futs[f]] = f.result()
    return out


def load_real_notebook(task, student, filename, path):
    with open(BASE / 'Past Bootcamps/2025-02' / path) as f:
        return json.load(f)


def section_fixed_set(clients, config):
    """A + F + B(sample): metrics from the latest registered benchmark run."""
    print("\n[A] Fixed 31-notebook set (latest registered run)")
    runs = json.loads((BASE / 'tests' / 'results' / 'runs.json').read_text())['runs']
    run = runs[-1]
    assert run['model'].startswith('gemma_4_12b_q4k'), f"unexpected last run: {run['model']}"
    ours = [r['our_grade'] for r in run['results']]
    refs = [r['deepseek_grade'] for r in run['results']]
    n = len(ours)
    errors = sum(1 for o, r in zip(ours, refs)
                 if M.grade_level(o) - M.grade_level(r) <= -1)  # graded stricter
    over = sum(1 for o, r in zip(ours, refs)
               if M.grade_level(o) - M.grade_level(r) >= 1)    # graded lenient
    res = {
        'model': run['model'], 'timestamp': run['timestamp'],
        'n': n,
        'exact_match_pct': M.exact_match_rate(ours, refs),
        'adjacent_match_pct': M.adjacent_match_rate(ours, refs, 1),
        'mae': M.mean_abs_error(ours, refs),
        'cohen_kappa': M.cohen_kappa(ours, refs),
        'confusion': M.confusion_matrix(ours, refs),
        'graded_stricter_count': errors,
        'graded_lenient_count': over,
        'avg_time_s': run['avg_time'], 'total_time_s': run['total_time'],
        'grade_distribution': run['grade_distribution'],
        'per_task': {t: {'match_rate': s['match_rate'], 'matches': s['matches'],
                         'total': s['total'], 'avg_time': s['avg_time']}
                     for t, s in run['task_stats'].items()},
        'note': 'Reference = Deepseek-R1-32B grades on the fixed test set (tests/test_set.csv).',
    }
    print(f"    n={n} exact={res['exact_match_pct']}% adjacent(<=1 step)={res['adjacent_match_pct']}% "
          f"MAE={res['mae']} kappa={res['cohen_kappa']}")
    print(f"    bias: {errors} stricter, {over} lenient | avg {res['avg_time_s']}s/nb")
    return res


def section_synthetic(clients, config, db):
    """Synthetic bank: target-grade hit-rate + format (B) + PII (E)."""
    print("\n[+S] Synthetic test bank (controlled inputs)")
    bank = build_bank()
    jobs = [{'notebook': c['notebook'], 'student': 'Alumno Sintético',
             'filename': f"{c['id']}.ipynb", 'task': c['task']} for c in bank]
    out = run_many(jobs, clients, config, db)
    cases = []
    for c, o in zip(bank, out):
        grade = o['grade']
        in_band = grade in c['expected']['acceptable']
        target_hit = grade == c['expected']['target']
        fmt = M.format_checks(o['report'])
        leak = M.pii_leaked(o['report'], c['pii_tokens']) if c['pii_tokens'] else []
        cases.append({
            'id': c['id'], 'description': c['description'],
            'expected_target': c['expected']['target'],
            'acceptable': c['expected']['acceptable'],
            'grade': grade, 'target_hit': target_hit, 'in_band': in_band,
            'format': fmt, 'pii_leaked': leak,
            'pii_generic': M.pii_regex_findings(o['report']) if c['pii_tokens'] else {},
            'time_s': o['time'], 'error': o['error'],
        })
    ok_band = sum(1 for c in cases if c['in_band'])
    ok_target = sum(1 for c in cases if c['target_hit'])
    pii_cases = [c for c in cases if c['id'].startswith('syn_pii')]
    pii_leak_count = sum(1 for c in pii_cases if c['pii_leaked'])
    fmt_ok = sum(1 for c in cases if c['format']['non_empty'] and c['format']['has_calificacion_global']
                 and c['format']['grade_in_enum'] and c['format']['is_spanish'])
    res = {
        'n': len(cases),
        'target_hit': f"{ok_target}/{len(cases)}",
        'in_band': f"{ok_band}/{len(cases)}",
        'pii_cases': len(pii_cases),
        'pii_leaks': pii_leak_count,
        'pii_pass': pii_leak_count == 0,
        'format_pass': f"{fmt_ok}/{len(cases)}",
        'cases': cases,
    }
    print(f"    target {ok_target}/{len(cases)} | in-band {ok_band}/{len(cases)} | "
          f"PII leaks {pii_leak_count}/{len(pii_cases)} | format {fmt_ok}/{len(cases)}")
    for c in cases:
        flag = '✅' if c['in_band'] else '❌'
        leakflag = '' if not c['pii_leaked'] else f"  ⚠️PII-LEAK:{c['pii_leaked']}"
        print(f"      {flag} {c['id']:16s} -> {c['grade']:12s} (target {c['expected_target']}){leakflag}")
    return res


def section_consistency(rows, clients, config, db, k=3, reps=5):
    """C: grade the same real notebook `reps` times, measure self-agreement."""
    print(f"\n[C] Consistency: {k} real notebooks x {reps} repeats")
    # pick a few real notebooks (mix of tasks)
    picked = [r for r in rows if r['task'] == 'numpy_i'][:1] + \
             [r for r in rows if r['task'] == 'numpy_ii'][:1] + \
             [r for r in rows if r['task'] == 'numpy_i'][:1]
    picked = picked[:k]
    grade_lists = []
    detail = []
    for row in picked:
        nb = load_real_notebook(row['task'], row['student'], row['filename'], row['path'])
        jobs = [{'notebook': nb, 'student': row['student'], 'filename': row['filename'],
                 'task': row['task']} for _ in range(reps)]
        out = run_many(jobs, clients, config, db)
        grades = [o['grade'] for o in out]
        from collections import Counter
        cnt = Counter(grades)
        mode, mx = cnt.most_common(1)[0]
        detail.append({
            'filename': row['filename'], 'task': row['task'], 'ref': row['deepseek_grade'],
            'grades': grades, 'mode': mode, 'mode_agreement': round(mx / reps, 3),
            'distinct': len(cnt), 'times': [o['time'] for o in out],
        })
        print(f"    {row['filename'][:30]:30s} {grades} mode={mode} ({mx}/{reps})")
    res = {'config': {'notebooks': k, 'repeats': reps},
           'detail': detail,
           'summary': M.consistency([d['grades'] for d in detail])}
    print(f"    avg mode-agreement={res['summary']['avg_mode_agreement']} "
          f"avg distinct grades={res['summary']['avg_distinct_grades']}")
    return res


def corrupt_notebook(notebook):
    """Remove the source of the first non-empty code cell (a strictly-worse copy)."""
    import copy
    nb = copy.deepcopy(notebook)
    for cell in nb.get('cells', []):
        if cell.get('cell_type') == 'code' and cell.get('source'):
            cell['source'] = []
            cell['outputs'] = []
            return nb, True
    return nb, False


def section_sensitivity(rows, clients, config, db, k=3):
    """D: worsen one cell -> grade must NOT increase."""
    print(f"\n[D] Sensitivity: {k} notebooks, one code cell removed")
    picked = rows[:k]
    detail = []
    violations = 0
    for row in picked:
        nb = load_real_notebook(row['task'], row['student'], row['filename'], row['path'])
        corrupted, did = corrupt_notebook(nb)
        if not did:
            continue
        job_c = {'notebook': nb, 'student': row['student'], 'filename': row['filename'], 'task': row['task']}
        job_w = {'notebook': corrupted, 'student': row['student'], 'filename': row['filename'] + '_worse', 'task': row['task']}
        rc = run_many([job_c], clients, config, db)[0]
        rw = run_many([job_w], clients, config, db)[0]
        gc, gw = rc['grade'], rw['grade']
        ok = M.grade_to_numeric(gw) <= M.grade_to_numeric(gc)
        if not ok:
            violations += 1
        detail.append({'filename': row['filename'], 'clean': gc, 'worse': gw, 'monotonic_ok': ok})
        print(f"    {row['filename'][:30]:30s} clean={gc:12s} -> worse={gw:12s} "
              f"{'OK' if ok else '⚠️ INCREASED'}")
    res = {'n': len(detail), 'violations': violations, 'pass': violations == 0, 'detail': detail}
    print(f"    monotonic (no increase) violations: {violations}/{len(detail)}")
    return res


def main():
    clients, config = make_clients()
    for i, c in enumerate(clients):
        ok, msg = c.health_check()
        print(f"client {i} (port {PORTS[i]}): {'OK' if ok else 'DOWN'} {msg}")
        if not ok:
            sys.exit(1)

    db = Database(':memory:')
    rows = list(csv.DictReader(open(BASE / 'tests' / 'test_set.csv')))

    validation = {'generated_at': datetime.now().isoformat(),
                  'model': 'gemma-4-12B-it-qat-UD-Q4_K_XL (dual instance, CUDA1+CUDA2)'}
    validation['fixed_set'] = section_fixed_set(clients, config)
    validation['synthetic'] = section_synthetic(clients, config, db)
    validation['consistency'] = section_consistency(rows, clients, config, db)
    validation['sensitivity'] = section_sensitivity(rows, clients, config, db)

    RESULTS_OUT.write_text(json.dumps(validation, indent=2, ensure_ascii=False))
    print(f"\nWrote validation results -> {RESULTS_OUT}")


if __name__ == '__main__':
    main()
