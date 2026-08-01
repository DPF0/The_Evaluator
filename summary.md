# The Evaluator — Progress Summary

**Last updated**: 2026-08-01

## Objective

Fix the n8n AI Notebook Grader workflow so `/webhook/grader` executes the full grading pipeline and returns results with correct metadata, then propose MVP improvements.

## Infrastructure

| Component | Details |
|-----------|---------|
| n8n instance | `http://192.168.0.37:5678` — **upgraded from v2.8.4 → v1.90.3** (via `npm install -g n8n@next`) |
| Node.js | Upgraded to **v22.22** (via nvm) to satisfy n8n v1.90.3 requirement |
| LLM server (port 8083) | `Qwen3.6-MTP-27B-UD-Q4_K_XL.gguf` (not used by workflow) |
| LLM server (port 8084) | `unsloth/Qwen35` — **active LLM for grading** |
| Workflow ID | `4TUyjhtQ5ASB18I1` (AI Notebook Grader v2.27.4-RAG) |
| MCP access | Instance-level, configured in `~/.config/opencode/opencode.jsonc` |
| n8n API key | **INVALID after upgrade** — old JWT tokens no longer work in v1.90.3. Need to generate a new one in n8n Settings → API. All `test_*.py`, `check_*.py`, `fix_*.py`, `get_*.py` scripts reference the old key. |

## Current Architecture

```
Webhook Trigger (POST /grader)
  → Normaliza entrada webhook (Code: extract student_name, filename, build raw_url)
    → Descarga notebook a corregir (HTTP Request: fetch notebook JSON from GitHub)
      → Formatea y limpia notebook (Code: clean cells, classify task, read metadata from $('Normaliza entrada webhook'))
        → Recupera rúbrica (Code: embedded rubric lookup by task_key)
          → Build Prompt (Code: assemble prompt with rubric + notebook + metadata)
            → Evalúa notebook (HTTP Request: POST to LLM on :8084)
              → Formatea salida evaluación (Code: parse grade, read metadata from $('Build Prompt'))
                → Respond to Webhook (JSON response)
```

**9 nodes, linear flow, no Merge node.**

## Key Design Decisions

### Metadata passthrough via node references
Instead of a Merge node (which n8n's JSON import keeps resetting), the workflow uses n8n's node reference syntax to read data from upstream nodes:
- `Formatea y limpia notebook` reads metadata from `$('Normaliza entrada webhook').item.json.student_name`
- `Formatea salida evaluación` reads metadata from `$('Build Prompt').item.json.student_name`

This avoids the problem of HTTP Request nodes overwriting `$json`.

### Grade regex
The LLM outputs `Calificación Global: Bien (8/10)`. The regex in `Formatea salida evaluación` matches:
```javascript
/(?:Calificación Global|Nota)[:,]\s*\**\**?(Mal|Regular|Bien|Excepcional)/i
```

### Task classification
Content-based (not filename-based): scans notebook text for keywords (`"structured array"`, `"broadcasting"`, etc.) → `numpy_ii`, otherwise `numpy_i`.

### LLM parameters
`temperature=0.2`, `top_p=0.5`, `top_k=10`, `seed=42`, `max_tokens=8000`. System prompt forbids chain-of-thought. All reports in Spanish.

## What Works

- [x] Webhook receives POST with student_name, filename, github_url
- [x] Notebook downloads from GitHub (multi-segment paths work)
- [x] Notebook content reaches LLM correctly
- [x] LLM evaluates and returns grade report in Spanish
- [x] Grade regex matches LLM output
- [x] student_name and filename pass through correctly to final response
- [x] End-to-end test: Grade=`Bien`, Numeric=`7`, metadata correct

## Known Issues

1. **n8n API key invalid** — All Python scripts (`test_*.py`, `check_*.py`, etc.) use the old JWT API key that doesn't work in n8n v1.90.3. Need to generate a new key in n8n Settings → API and update all scripts.

2. **Rubrics embedded as JS strings** — Rubric files in `rubrics/` are the source of truth, but n8n's sandbox blocks file I/O. Rubrics are embedded in the workflow's Code node. When a rubric file changes, you must also update the embedded copy in the n8n workflow JSON and re-import.

3. **n8n JSON import resets node settings** — Importing a workflow JSON via the UI can reset Merge node mode, lose multi-branch connections, etc. The current linear flow avoids this problem.

4. **MCP tools** — `n8n_get_workflow_details` works. `n8n_search_workflows` has a schema mismatch in v1.90.3. `n8n_execute_workflow` requires `executionMode` parameter not exposed in the schema.

## Files

| File | Purpose |
|------|---------|
| `n8n/AI Notebook Grader (v2.27.4-RAG).json` | Current workflow JSON (source of truth) |
| `rubrics/rubric_numpy_i.md` | NumPy I rubric (source of truth) |
| `rubrics/rubric_numpy_ii.md` | NumPy II rubric (source of truth) |
| `grader_app.py` | Streamlit UI (single file) |
| `test_webhook_debug.py` | Manual webhook test script |
| `~/.config/opencode/opencode.jsonc` | MCP server config with n8n Bearer token |

## Grade Scale

| Categorical | Numeric |
|-------------|---------|
| Mal | 3 |
| Regular | 5 |
| Bien | 7 |
| Excepcional | 9 |

## Test Command

```bash
curl -s -m 120 -X POST http://192.168.0.37:5678/webhook/grader \
  -H "Content-Type: application/json" \
  -d '{"student_name":"Test Student","filename":"Ejercicios_Numpy_I.ipynb","github_url":"https://github.com/chiaralopez/2026-02-BILBAO-FT-Data-Science-1/2-Data_Analysis/1-Numpy/Practica"}'
```

## Next Steps (if continuing)

1. Generate new n8n API key and update all Python scripts
2. Verify grade accuracy against rubric criteria for multiple student notebooks
3. Consider MVP improvements (error handling, timeout management, etc.)
