# The Evaluator — Status Report

> Snapshot of current state. For the canonical, always-current reference see `AGENTS.md`.

## What This Is

AI-powered auto-grader for Jupyter notebook assignments in a Data Science bootcamp.
A Python pipeline evaluates student notebooks against rubrics using a local LLM,
produces Spanish Markdown grade reports, and stores results in SQLite.
A Streamlit teacher dashboard reviews and approves the results.

## Architecture

```
main.py (CLI: setup / evaluate / report / rubric)
  └─ src/agents/orchestrator.py
       ├─ Evaluation agent (LLM grading + grade extraction)
       ├─ Report agent (Markdown feedback in Spanish)
       └─ Rubric agent (generate rubrics from reference notebooks)

apps/dashboard_app.py (Streamlit teacher dashboard, parallel batch evaluation)
  └─ SQLite (evaluations, students, rubrics, reference_metadata)
```

| Module | Purpose |
|--------|---------|
| `src/agents/orchestrator.py` | Coordinates load → clean → classify → evaluate → save |
| `src/agents/evaluation.py` | Builds prompt (rubric + notebook), parses grade |
| `src/agents/rubric.py` | Loads / generates rubrics |
| `src/agents/report.py` | Student & cohort feedback reports |
| `src/utils/notebook.py` | Notebook cleaning (nbformat, no truncation), GitHub download |
| `src/utils/task_classifier.py` | Filename-based task classification |
| `src/utils/reference.py` | Reference notebook analysis + metadata |
| `src/utils/code_analysis.py` | AST-based static analysis |
| `src/llm.py` | OpenAI-compatible client (retry, health check) |
| `src/db.py` | Thread-safe SQLite (per-thread connections, WAL) |
| `src/config.py` | Configuration (env vars > config.json > defaults) |
| `src/models.py` | Data models, incl. the `Grade` enum |

## Feature Status

| Feature | Status |
|---------|--------|
| Notebook cleaning | ✅ nbformat, outputs cleared, no truncation |
| Task classification | ✅ Filename-based (`numpy_i` / `numpy_ii`) |
| LLM evaluation | ✅ Reference-aware, retry on transient errors, health check |
| Teacher dashboard | ✅ Parallel batch (5 workers), grade override, config tab |
| Grade scale | ✅ Mal 3 / Regular 5 / Bien 7 / Excepcional 9 |
| Deployment | ✅ Live on Render (free tier): `https://the-evaluator.onrender.com` — blueprint + bring-your-own-LLM (`docs/despliegue.md`) |
| Email delivery | ⏳ Code exists, not wired to the UI |

## Milestones

| When | What |
|------|------|
| 2026-08-24 | **Modulo 3.1 delivered and graded 10.00/10.00** (I. Montalbán) — public deployment + BYO-LLM interface |
| v0.1.0 | First stable release: grading pipeline, dashboard, tests, Render blueprint |
| v0.1.1 | Config tab shows active configuration + unsaved-changes warning |
| 2026-08-30 | **Modulo 3.3 — model evaluation & testing** (`docs/validacion.md`): fixed-set benchmark (74.2% exact, 100% adjacent, κ 0.549), synthetic bank (8 notebooks, 0 PII leaks, 8/8 format), determinism (100%), monotonicity (0 violations) |
| v0.2.0 | Validation suite shipped: `tests/metrics.py`, `tests/synthetic_bank.py`, `tests/validate_mvp.py`, `tests/synthetic/`, `tests/results/validation.json` |

## Testing

- Core regression suite (no LLM/network): `./.venv/bin/pytest tests/test_core.py -v`
- LLM benchmark (fixed 31-notebook set): `python3 tests/run_test.py --model <config>`
- MVP validation (needs Gemma on :8084+:8085): `python3 tests/validate_mvp.py` → `tests/results/validation.json`
- Best model so far: Gemma 4 12B Q4_K (80.6% match vs Deepseek reference) — see `docs/llm_benchmark_results.md`; full validation in `docs/validacion.md`

## Grade Scale

| Categorical | Numeric |
|-------------|---------|
| Mal | 3 |
| Regular | 5 |
| Bien | 7 |
| Excepcional | 9 |

LLM params: `temperature=0.2`, `top_p=0.5`, `top_k=10`, `seed=42`, `max_tokens=8000`.
System prompt forbids chain-of-thought output. All reports in Spanish (Spain).
