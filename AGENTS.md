# The Evaluator — AGENTS.md

## What This Is

AI-powered auto-grader for Jupyter notebook assignments in a Data Science bootcamp. An n8n workflow downloads student notebooks from GitHub, evaluates them with a local LLM against rubrics, and returns a Markdown grade report.

## Architecture

```
Streamlit UI (grader_app.py)
  └─ POST → n8n Webhook (/webhook/grader) on 192.168.0.37:5678
       └─ Download notebook → Clean & classify task → Lookup rubric → LLM evaluation → Parse grade → Return JSON
```

- **Frontend**: `grader_app.py` — Streamlit app, single file
- **Workflow**: n8n JSON exports in root and `n8n/` directory
- **Rubrics**: `rubrics/rubric_numpy_i.md`, `rubrics/rubric_numpy_ii.md` (source of truth)
- **Student data**: `25FEBBILFTDS-*/` folder with per-student notebooks and past evaluations

## Critical Gotchas

### Rubrics must be synced to n8n manually
The rubric files in `rubrics/` are the source of truth. But n8n's sandbox blocks file I/O, so rubrics are **embedded as JS string constants** inside the workflow's Code node. When you update a rubric file, you must also update the embedded copy in the n8n workflow JSON and re-import it.

### All infrastructure is hardcoded to 192.168.0.37
No env vars, no config files. The n8n instance, LLM server (`:8083`), and secondary LLM (`:8084`) are all hardcoded as string literals across scripts.

### n8n API key is embedded in scripts
The API key appears as a plain string in `test_*.py`, `check_*.py`, `fix_*.py`, `get_*.py`. Never commit changes that expose it differently.

### Task classification is content-based, not filename-based
The v12 workflow classifies assignments by scanning notebook content for keywords (`"structured array"`, `"broadcasting"`, etc.) → `numpy_ii`, otherwise `numpy_i`. Filenames and URLs proved unreliable.

### No package management
No `requirements.txt`, `pyproject.toml`, or `setup.py`. Dependencies (`streamlit`, `requests`) are assumed installed. The repo is **not a git repository**.

### No linting, formatting, or test framework
The `test_*.py` files are manual curl wrappers, not pytest/unittest. No ruff, black, mypy, or any code quality tooling.

## Commands

| Command | Purpose |
|---------|---------|
| `streamlit run grader_app.py` | Launch the Streamlit grading UI |
| `python test_webhook_full.py` | End-to-end webhook test (prints full grading result) |
| `python get_execution_error.py` | Fetch latest n8n execution and identify failed node |

### Test the webhook with curl
```bash
curl -X POST http://192.168.0.37:5678/webhook/grader \
  -H "Content-Type: application/json" \
  -d '{"student_name": "Test Student", "filename": "Ejercicios_Numpy_I.ipynb", "github_url": "<raw-github-url>"}'
```

## Grade Scale

| Categorical | Numeric |
|-------------|---------|
| Mal | 3 |
| Regular | 5 |
| Bien | 7 |
| Excepcional | 9 |

LLM params: `temperature=0.2`, `top_p=0.5`, `top_k=10`, `seed=42`, `max_tokens=8000`. System prompt forbids chain-of-thought output. All reports are in Spanish.

## Workflow Versions

| File | Status |
|------|--------|
| `AI Notebook Grader (v2.27.4-RAG-v12).json` | **Current production** (webhook, RAG, content-based classification) |
| `n8n/AI Notebook Grader (v2.27.4).json` | Original v1 (manual trigger, no RAG) |
| Other `.json` files | Archived iterations |

The active workflow in n8n is `AI Notebook Grader (v2.27.4-RAG) (v12)` (ID: `5xIoukUY3js6kxy8`).

## Notebook Cleaning Limits

- Per-output truncation: **800 chars**
- Total cleaned notebook cap: **15,000 chars**
- Images (base64 PNG/JPEG) are stripped entirely

## Project Documentation

`Continue Extension Prompt - AI Notebook Grader MVP_v2.md` — closest thing to a README; contains project overview, technical decisions, and infrastructure details.
