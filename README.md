# The Evaluator

AI-powered auto-grader for Jupyter notebook assignments in a Data Science bootcamp.

Evaluates student notebooks against rubrics using a local LLM, generates personalized feedback reports in Spanish, and provides a teacher dashboard for review and approval.

## Architecture

```
Student Notebook → Clean & Extract Code → Static Analysis → LLM Evaluation → Grade Report → SQLite DB
                                                                                ↓
                                                                        Teacher Dashboard (Streamlit)
```

## Components

- **`src/`** — Core evaluation pipeline
  - `agents/` — Evaluation, Rubric, Report, and Orchestrator agents
  - `llm.py` — LLM client abstraction (OpenAI-compatible API)
  - `db.py` — SQLite database layer
  - `utils/` — Notebook cleaning, static code analysis, task classification
- **`apps/dashboard_app.py`** — Streamlit teacher dashboard for reviewing evaluations
- **`tests/`** — Batch testing scripts
- **`rubrics/`** — Evaluation criteria (source of truth)
- **`docs/`** — Project documentation and diagrams

## Features

- **Automated grading** with LLM-based evaluation against rubrics
- **Static code analysis** using AST for objective metrics
- **Few-shot calibration** for consistent grading aligned with reference evaluations
- **Teacher dashboard** for review, approval, and export
- **Batch evaluation** support for multiple notebooks
- **SQLite storage** for persistent evaluation records

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
# Evaluate a single notebook
python main.py evaluate --student "Student Name" --file "path/to/notebook.ipynb"

# Generate report
python main.py report --student "Student Name" --assignment "NumPy I"
```

### Teacher Dashboard

```bash
streamlit run apps/dashboard_app.py
```

### Batch Testing

```bash
python tests/test_full_batch.py
```

## Configuration

Edit `config.json` to adjust:
- LLM endpoint and parameters
- Database path
- Rubric directory
- Notebook cleaning limits

## Project Status

- **Week 1 complete**: Core pipeline, CLI, dashboard, batch testing
- **Grading calibration**: 64% alignment with reference evaluations (deepseek-r1)
- **Week 2 planned**: LangGraph multi-agent integration for enhanced evaluation workflow
