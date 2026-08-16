# The Evaluator

AI-powered auto-grader for Jupyter notebook assignments in a Data Science bootcamp.

Evaluates student notebooks against rubrics using a local LLM, generates personalized feedback reports in Spanish, and provides a teacher dashboard for review and approval.

## Architecture

```
Student Notebook → Clean & Extract Code → Static Analysis → LLM Evaluation → Grade Report → SQLite DB
                                                                                    ↓
                                                                            Teacher Dashboard (Streamlit)
```

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

- **`src/`** — Core evaluation pipeline
  - `agents/` — Evaluation, Rubric, Report, and Orchestrator agents
  - `llm.py` — LLM client abstraction (OpenAI-compatible API, supports RoundRobinLLMClient)
  - `db.py` — SQLite database layer
  - `utils/` — Notebook cleaning (nbformat), static code analysis, task classification
- **`apps/dashboard_app.py`** — Streamlit teacher dashboard for reviewing evaluations
- **`tests/`** — Structured testing infrastructure (fixed test set, model configs, results)
- **`rubrics/`** — Evaluation criteria (source of truth)
- **`docs/`** — Project documentation, benchmark results

## Features

- **Automated grading** with LLM-based evaluation against rubrics
- **Static code analysis** using AST for objective metrics
- **Few-shot calibration** for consistent grading aligned with reference evaluations
- **Teacher dashboard** for review, approval, and export
- **Batch evaluation** support for multiple notebooks
- **SQLite storage** for persistent evaluation records
- **Structured benchmark testing** — fixed test set, model configs, registered results

## Grade Scale

| Categorical | Numeric |
|-------------|---------|
| Mal | 3 |
| Regular | 5 |
| Bien | 7 |
| Excepcional | 9 |

## Requirements

- Python 3.10+
- Local LLM server (OpenAI-compatible API on `http://192.168.0.37:8084/v1`)
- Dependencies: `streamlit`, `requests`, `nbformat`, `openai`

## Usage

### CLI

```bash
# Initialize database and load rubrics
python3 main.py setup

# Evaluate a single notebook (auto-detects topic)
python3 main.py evaluate --student "Student Name" --file "path/to/notebook.ipynb" --task numpy_i

# Evaluate a notebook from a GitHub folder
python3 main.py evaluate --student "Student Name" --file "notebook.ipynb" --github "https://github.com/org/repo/tree/main/folder"

# Generate Markdown feedback report
python3 main.py report --student "Student Name"

# Generate a rubric for a topic
python3 main.py rubric --generate "NumPy I" --topic numpy_i --description "Fundamentos de NumPy"
```

### Teacher Dashboard

```bash
streamlit run apps/dashboard_app.py
```

### Benchmark Testing

```bash
# Run test on a model (31 notebooks, same test set for all models)
python3 tests/run_test.py --model gemma_4_12b_q4k_inst1
```

## Configuration

Edit `src/config.py` to adjust:
- LLM endpoint and parameters
- Database path
- Rubric directory
- Paths

## Benchmark Results

7 models tested on the same 31 notebooks (16 NumPy I, 15 NumPy II) with Deepseek-R1-32B reference grades.

| Rank | Model | Match Rate | Effective s/nb | Mode |
|------|-------|-----------|----------------|------|
| 1 | Gemma 4 12B Q4_K | 80.6% | 12.7s | Dual instance |
| 2 | Qwen3-Coder 30B Q4_K | 74.2% | 14.4s | Split |
| 3 | Gemma 4 26B Q4_K | 71.0% | 15.6s | Split |
| 4 | GPT-oss 20B Q6_K | 51.6% | 65.0s | Split |
| 5 | Qwen3.6 35B Q4_K | 48.4% | 27.5s | Split |
| 6 | Gemma 4 12B FT | 41.9% | 12.0s | Dual instance |
| 7 | Qwen3.5 9B Q4_K | 16.1% | 17.7s | Dual instance |

Full benchmark documentation: `docs/llm_benchmark_results.md`

## Project Status

- **Core pipeline**: Complete — CLI, agents, dashboard, batch testing
- **Benchmark testing**: Complete — 7 models evaluated, structured test infrastructure
- **Best model**: Gemma 4 12B Q4_K (80.6% match rate, 12.7s effective/nb)
