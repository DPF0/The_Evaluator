# The Evaluator — AGENTS.md

## What This Is

AI-powered auto-grader for Jupyter notebook assignments in a Data Science bootcamp. A Python pipeline evaluates student notebooks against rubrics using local LLMs, produces Markdown grade reports, and stores results in SQLite.

Repo: https://github.com/DPF0/The_Evaluator

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

- **CLI**: `main.py` — commands: `setup`, `evaluate`, `report`, `rubric`
- **Agents**: `src/agents/` — Evaluation, Report, Rubric, Orchestrator
- **LLM client**: `src/llm.py` — abstraction over OpenAI-compatible API, supports `RoundRobinLLMClient`
- **Config**: `src/config.py` — centralizes all settings (LLM, database, paths)
- **Database**: `data/evaluations.db` — SQLite with WAL mode, thread-safe
- **Rubrics**: `rubrics/rubric_numpy_i.md`, `rubrics/rubric_numpy_ii.md` (source of truth)
- **Student data**: `Past Bootcamps/2025-02/Ejercicios_alumnxs/` — 19 students, 30+ assignments
- **Dashboard**: `apps/dashboard_app.py` — Streamlit on `0.0.0.0:8501`

## Critical Gotchas

### LLM endpoints default to the dev LAN, but are configurable
`config.py` defaults to `http://192.168.0.37:8084/v1` (private LAN, unreachable off the dev network).
Override with `EVALUATOR_`-prefixed env vars or `config.json` (the dashboard's ⚙️ Configuración tab writes
`config.json`). The CLI `evaluate` and both dashboard evaluation flows run a short `LLMClient.health_check()`
preflight and fail fast with a clear error if the endpoint is unreachable (instead of hanging for the 300s chat timeout).

### CUDA0 is the user's main server — never touch it
Qwen3.6-27B runs on CUDA0:8083 with speculative decoding. Only use CUDA1 and CUDA2 for testing.

### Task classification is filename-based
`numpy_i` if filename contains `numpy_i` or `numpy1`. `numpy_ii` if `numpy_ii` or `numpy2`. Content-based classification was unreliable.

### Notebook cleaning uses nbformat, no truncation
Clears outputs via nbformat, keeps all code/markdown intact. No character limits.

### LLM client params differ from server params
- **Client**: `temperature=0.2`, `top_p=0.5`, `top_k=10`, `seed=42`, `max_tokens=8000`
- **Server** (Gemma test, `:8084`): `--temp 0.6`, `--top-p 0.95`, `--top-k 64`, `--ctx-size 128000`, `-fa on`, `--cache-type-k q8_0`, `--cache-type-v q5_1`, `--parallel 5`, `--jinja`, `-kvu`

### Grade extraction regex
Matches `calificación global` section in LLM output. Deepseek uses English grades (Good/Regular/Bad) → mapped to Spanish (Bien/Regular/Mal).

### Package management is minimal
`requirements.txt` (requests, streamlit, nbformat, pandas) — used by `Dockerfile` (`COPY requirements.txt`) and by Render. No pyproject.toml or setup.py.

### Linting / formatting
No ruff, black, or mypy.

### Test framework: pytest
- **Core regression suite**: `tests/test_core.py` (no LLM/network needed). Covers task classification over all 31 test-set notebooks, targeted classifier edge cases, notebook cleaning, grade extraction, and LLM client retry logic (mocked HTTP).
- Run: `./.venv/bin/pytest tests/test_core.py -v` (dev venv in `.venv`, already gitignored)
- Install dev deps: `python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt -r requirements-dev.txt`
- The benchmark runner `tests/run_test.py` is a standalone script (separate concern: LLM model benchmarks).

## Known Limitations
- `Database.close()` only closes the calling thread's connection (plus the main one). Per-thread connections from other threads leak until process exit — harmless in practice (SQLite + OS reclaim), but not a clean multi-thread shutdown.
- The dashboard re-extracts the uploaded ZIP into a temp dir on every Streamlit rerun (minor I/O, not cached).
- `download_notebook_from_github` assumes the `main` branch when building the raw URL.

## Commands

| Command | Purpose |
|---------|---------|
| `python3 main.py setup` | Initialize database and load rubrics |
| `python3 main.py evaluate --student <name> --file <path> [--task <key>]` | Grade a single local notebook |
| `python3 main.py evaluate --student <name> --file <nb> --github <url>` | Grade a notebook from a GitHub folder |
| `python3 main.py report --student <name>` | Generate Markdown feedback report |
| `python3 main.py rubric --generate <name> --topic <key> --description <desc>` | Generate rubric for a topic |
| `streamlit run apps/dashboard_app.py` | Launch teacher dashboard |
| `python3 tests/run_test.py --model <config>` | Run benchmark test (31 notebooks) |
| `./.venv/bin/pytest tests/test_core.py -v` | Run core regression tests (no LLM needed) |

## Testing Infrastructure

### Fixed test set
- **31 notebooks** (16 numpy_i, 15 numpy_ii) with Deepseek-R1-32B reference grades
- Location: `tests/test_set.csv`
- Every model is tested on the exact same notebooks

### Model configs
- Location: `tests/models/*.conf`
- Dual-instance models (8084+8085): `ThreadPoolExecutor(2)` concurrent evaluation
- Split models (CUDA1,CUDA2): sequential evaluation

### Results
- Location: `tests/results/runs.json`
- Each run registered with timestamp, model config, rubrics used, per-notebook results

### Benchmark results
- Location: `docs/llm_benchmark_results.md`
- 7 models tested, ranked by match rate vs Deepseek reference

### Best performing models
| Model | Match Rate | Effective s/nb | Mode |
|-------|-----------|----------------|------|
| Gemma 4 12B Q4_K | 80.6% | 12.7s | Dual instance |
| Qwen3-Coder 30B Q4_K | 74.2% | 14.4s | Split |
| Gemma 4 26B Q4_K | 71.0% | 15.6s | Split |

## Grade Scale

| Categorical | Numeric |
|-------------|---------|
| Mal | 3 |
| Regular | 5 |
| Bien | 7 |
| Excepcional | 9 |

LLM params: `temperature=0.2`, `top_p=0.5`, `top_k=10`, `seed=42`, `max_tokens=8000`. System prompt forbids chain-of-thought output. All reports are in Spanish (Spain).

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
| `tests/test_set.csv` | Fixed test set (31 notebooks) |
| `tests/models/*.conf` | Model server configurations |
| `tests/results/runs.json` | Registered test results |
| `rubrics/rubric_numpy_i.md` | NumPy I rubric |
| `rubrics/rubric_numpy_ii.md` | NumPy II rubric |
| `docs/llm_benchmark_results.md` | Benchmark documentation |
| `archive/` | Deprecated files (old grader_app.py, test_batch.py) |
| `requirements.txt` | Python dependencies (used by Dockerfile and Render) |
| `requirements-dev.txt` | Dev dependencies (pytest) for the core test suite |
| `Dockerfile` | Container build (streamlit dashboard) |
| `docker-compose.yml` | Local docker compose (app only, LLM external) |
| `render.yaml` | Render deploy blueprint (free web tier, docker runtime) |

## Project Documentation

- `docs/llm_benchmark_results.md` — Benchmark results, test procedure, model comparison.
- `docs/despliegue.md` — Deployment doc (Modulo 3.1): options chosen, Render deploy, bring-your-own-LLM design.
