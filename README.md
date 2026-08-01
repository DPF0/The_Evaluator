# The Evaluator

AI-powered auto-grader for Jupyter notebook assignments in a Data Science bootcamp.

An n8n workflow downloads student notebooks from GitHub, evaluates them with a local LLM against rubrics, and returns a Markdown grade report.

## Architecture

```
Streamlit UI → POST → n8n Webhook → Download notebook → Clean & classify → Lookup rubric → LLM evaluation → Parse grade → Return JSON
```

## Components

- **n8n workflow** — Orchestration pipeline (see `n8n/`)
- **Rubrics** — Evaluation criteria for each assignment (see `rubrics/`)
- **Streamlit UI** — Frontend for instructors

## Grade Scale

| Categorical | Numeric |
|-------------|---------|
| Mal | 3 |
| Regular | 5 |
| Bien | 7 |
| Excepcional | 9 |

## Requirements

- n8n instance (v2.32.7)
- Local LLM server (OpenAI-compatible API)
- Streamlit + requests

## Usage

```bash
streamlit run grader_app.py
```

Test the webhook:

```bash
curl -X POST http://192.168.0.37:5678/webhook/grader \
  -H "Content-Type: application/json" \
  -d '{"student_name": "Test Student", "filename": "Ejercicios_Numpy_I.ipynb", "github_url": "<raw-github-url>"}'
```
