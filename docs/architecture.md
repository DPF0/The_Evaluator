# Architecture & File Reference

Component map and file layout for **The Evaluator**. Hot working knowledge (gotchas, commands, branch rules) lives in `AGENTS.md`; benchmark numbers and validation reports live in the linked docs.

## Architecture

```
main.py (CLI)
  └─ src/agents/orchestrator.py
       ├─ Evaluation agent (LLM grading + grade extraction)
       ├─ Report agent (Markdown feedback in Spanish)
       └─ Rubric agent (generate rubrics from reference notebooks)

apps/dashboard_app.py (Streamlit teacher dashboard)
  └─ SQLite database (evaluations, students, rubrics, reference_metadata)
```

## Components

- **CLI**: `main.py` — commands: `setup`, `evaluate`, `report`, `rubric`
- **Agents**: `src/agents/` — Evaluation, Report, Rubric, Orchestrator
- **LLM client**: `src/llm.py` — abstraction over OpenAI-compatible API, supports `RoundRobinLLMClient`
- **Config**: `src/config.py` — centralizes all settings (LLM, database, paths)
- **Database**: `data/evaluations.db` — SQLite with WAL mode, thread-safe
- **Rubrics**: `rubrics/rubric_numpy_i.md`, `rubrics/rubric_numpy_ii.md` (source of truth)
- **Student data**: `Past Bootcamps/2025-02/Ejercicios_alumnxs/` — 19 students, 30+ assignments
- **Dashboard**: `apps/dashboard_app.py` — Streamlit on `0.0.0.0:8501`

## Relevant Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point |
| `src/agents/evaluation.py` | Evaluation agent with reference-aware grading |
| `src/agents/orchestrator.py` | Main workflow coordinator |
| `src/llm.py` | LLM client abstraction + RoundRobinLLMClient |
| `src/config.py` | Centralized configuration |
| `src/utils/notebook.py` | Notebook cleaning (nbformat, no truncation) |
| `src/utils/reference.py` | Reference notebook analysis |
| `src/utils/code_analysis.py` | AST-based static analysis |
| `apps/dashboard_app.py` | Streamlit teacher dashboard |
| `tests/run_test.py` | Structured test runner (LLM benchmark) |
| `tests/test_core.py` | Core regression suite (pytest, no LLM needed) |
| `tests/test_metrics.py` | Unit tests for metrics.py + synthetic_bank.py (pytest, no LLM needed) |
| `tests/test_set.csv` | Fixed test set (31 notebooks) |
| `tests/models/*.conf` | Model server configurations |
| `tests/results/runs.json` | Registered test results |
| `tests/metrics.py` | Pure validation metric helpers (no LLM) |
| `tests/synthetic_bank.py` | Deterministic synthetic notebook generator |
| `tests/validate_mvp.py` | MVP validation orchestrator |
| `tests/synthetic/` | Synthetic test bank (8 notebooks + manifest) |
| `tests/results/validation.json` | Latest MVP validation results |
| `docs/validacion.md` | Model evaluation & testing report (Modulo 3.3) |
| `rubrics/rubric_numpy_i.md` | NumPy I rubric |
| `rubrics/rubric_numpy_ii.md` | NumPy II rubric |
| `docs/llm_benchmark_results.md` | Benchmark documentation |
| `archive/` | Deprecated files (old grader_app.py, test_batch.py) |
| `requirements.txt` | Python dependencies (used by Dockerfile and Render) |
| `requirements-dev.txt` | Dev dependencies (pytest) for the core test suite |
| `Dockerfile` | Container build (streamlit dashboard) |
| `docker-compose.yml` | Local docker compose (app only, LLM external) |
| `render.yaml` | Render deploy blueprint (free web tier, docker runtime) |

## Testing & Validation

Layout of the test/validation tooling. Actual numbers and reports live in the linked docs.

- **Fixed test set**: `tests/test_set.csv` — 31 notebooks (16 numpy_i, 15 numpy_ii) with Deepseek-R1-32B reference grades; every model is tested on the exact same set.
- **Model configs**: `tests/models/*.conf` — dual-instance (8084+8085) uses `ThreadPoolExecutor(2)`; split mode is sequential. Note: many still reference CUDA1 (now reserved) and are not runnable until rewritten for CUDA2-only.
- **Benchmark results**: `tests/results/runs.json` + `docs/llm_benchmark_results.md` (procedure, server/client params, per-model results).
- **MVP validation**: `tests/validate_mvp.py` → `tests/results/validation.json`; pure metric helpers in `tests/metrics.py`, deterministic synthetic generator in `tests/synthetic_bank.py`, bank in `tests/synthetic/`. Written report: `docs/validacion.md`.
- **pytest suites (no LLM/network)**: `tests/test_core.py` + `tests/test_metrics.py`.
