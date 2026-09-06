# The Evaluator — AGENTS.md

## What This Is

AI-powered auto-grader for Jupyter notebook assignments in a Data Science bootcamp. A Python pipeline evaluates student notebooks against rubrics using local LLMs, produces Markdown grade reports, and stores results in SQLite.

Repo: https://github.com/DPF0/The_Evaluator

Component map & file reference: `docs/architecture.md`.

## Branching & Releases

- **`main`** = stable, release-only. Reviewers and Render track `main`.
- **`dev`** = integration branch. All new work lands here first; small feature branches off `dev` are optional for isolated work.
- **Never develop directly on `main`** — no commits/pushes to `main` except release merges.
- **Release process**: merge `dev` → `main`, tag `vMAJOR.MINOR.PATCH` (annotated), push branch + tag. Releases live at 0.x (pre-1.0 MVP). Current: `v0.2.0`.
- **Render deploy**: `autoDeploy: true` is set in `render.yaml`, but it did NOT fire on the v0.1.1 push — after every release, check the Render dashboard and manually trigger "Deploy latest commit" if the build didn't start.

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

Full component list and file map: `docs/architecture.md`.

## Critical Gotchas

### LLM endpoints default to the dev LAN, but are configurable
`config.py` defaults to `http://192.168.0.37:8084/v1` (private LAN, unreachable off the dev network).
Override with `EVALUATOR_`-prefixed env vars or `config.json` (the dashboard's ⚙️ Configuración tab writes
`config.json`). The CLI `evaluate` and both dashboard evaluation flows run a short `LLMClient.health_check()`
preflight and fail fast with a clear error if the endpoint is unreachable (instead of hanging for the 300s chat timeout).

### CUDA0 and CUDA1 are reserved — only CUDA2 is free
CUDA0 hosts the user's main server (`:8083`); CUDA1 is also reserved.
Never start, stop, or modify anything on CUDA0 or CUDA1.
Any model we serve (tests, benchmarks, experiments) runs on CUDA2 only.

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

### Tests: pytest (no LLM/network)
- `tests/test_core.py` (core regression) + `tests/test_metrics.py` (unit tests for `tests/metrics.py` + `tests/synthetic_bank.py`).
- Run: `./.venv/bin/pytest tests/test_core.py tests/test_metrics.py -v`
- Install dev deps: `python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt -r requirements-dev.txt`
- LLM-dependent runners are separate: `tests/run_test.py` (benchmark) and `tests/validate_mvp.py` (full MVP validation).

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
| `python3 tests/validate_mvp.py` | Run full MVP validation (needs Gemma on :8084+:8085) |
| `./.venv/bin/pytest tests/test_core.py tests/test_metrics.py -v` | Run pytest suites (no LLM needed) |

## Grade Scale

| Categorical | Numeric |
|-------------|---------|
| Mal | 3 |
| Regular | 5 |
| Bien | 7 |
| Excepcional | 9 |

System prompt forbids chain-of-thought output. All reports are in Spanish (Spain).

## Reference Docs

- `docs/architecture.md` — component map & file reference.
- `docs/llm_benchmark_results.md` — benchmark procedure, params, per-model results.
- `docs/validacion.md` — model evaluation & testing report (Modulo 3.3): fixed-set, synthetic, determinism, monotonicity.
- `docs/despliegue.md` — deployment (Modulo 3.1): options chosen, Render deploy, bring-your-own-LLM design.
- `docs/analisis_arquitectura.md` — post-MVP architecture analysis (Modulo 3.1).
