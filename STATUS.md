# The Evaluator — Status Report

## What Has Been Built

### 1. Python Evaluation Pipeline (`src/`)

Replaced the n8n workflow with a clean Python pipeline. The architecture:

```
CLI (main.py)
  └─ Orchestrator
       ├─ Evaluation Agent (LLM grading)
       ├─ Rubric Agent (rubric loading/generation)
       ├─ Report Agent (feedback generation)
       └─ Code Analysis (static metrics)
```

**Key components:**

| Module | Purpose |
|--------|---------|
| `src/agents/orchestrator.py` | Coordinates the full pipeline: load notebook → clean → classify → evaluate → save |
| `src/agents/evaluation.py` | Builds LLM prompt with rubric + notebook + code metrics, parses grade from response |
| `src/agents/rubric.py` | Loads rubrics from `rubrics/` dir, can generate new ones via LLM |
| `src/agents/report.py` | Generates student feedback and cohort reports |
| `src/utils/notebook.py` | Cleans notebooks (strips images, truncates outputs), classifies tasks |
| `src/utils/code_analysis.py` | AST-based static analysis: complexity, unused imports, vectorization detection |
| `src/utils/email.py` | SMTP email delivery for feedback |
| `src/llm.py` | LLM client abstraction (OpenAI-compatible API) |
| `src/db.py` | Thread-safe SQLite with WAL mode |
| `src/config.py` | Centralized configuration |
| `src/models.py` | Data models: Student, Assignment, Evaluation, Rubric, Grade |

### 2. Teacher Dashboard (`dashboard_app.py`)

Streamlit app for reviewing evaluations:
- Filter by student, assignment, grade
- Statistics overview
- Detailed report view with full Markdown
- Grade override with reason tracking

### 3. Batch Testing (`test_batch.py`)

Concurrent evaluation script (3 parallel workers) for testing multiple notebooks.

---

## Architectural Decisions & Rationale

**Why Python over n8n?**
- n8n's sandbox blocked file I/O (rubrics had to be embedded as JS strings)
- Hard to debug, version control, and extend
- Python gives full control, testability, and integrates with agent frameworks later

**Why SQLite?**
- Simple, no infrastructure needed
- WAL mode enables concurrent reads during batch evaluation
- Sufficient for <1000 evaluations; can migrate to PostgreSQL later if needed

**Why thread-safe DB with per-thread connections?**
- Batch evaluation uses `ThreadPoolExecutor` (3 workers)
- SQLite doesn't allow shared connections across threads
- Each thread gets its own connection, main connection handles schema

**Why filename-based task classification?**
- Content-based classification failed: NumPy II notebooks often lack keywords like "broadcasting" or "structured array"
- Filenames (`Ejercicios_Numpy_II_*.ipynb`) are reliable indicators
- Content-based as fallback for unknown formats

**Why AST-based code analysis?**
- Lightweight, no external dependencies
- Detects patterns the LLM might miss: unused imports, complexity, vectorization vs loops
- Metrics included in LLM prompt for informed grading

**Why 300s LLM timeout?**
- Qwen35 on local hardware takes 80-180s per evaluation
- 3 concurrent requests via `--parallel 3` on the vLLM server
- Trade-off: slower per-request, but 3x throughput

**Why per-output truncation at 2000 chars, total at 30000?**
- Original 800/15000 was too aggressive (lost exercise outputs)
- 2000 chars captures most exercise results
- 30000 total handles most notebooks without truncation
- Images always stripped (base64 bloat)

---

## Current State

| Feature | Status |
|---------|--------|
| Notebook cleaning | ✅ Working, handles all edge cases |
| Task classification | ✅ Filename-based, reliable |
| LLM evaluation | ✅ Consistent with deepseek-r1 historical grades |
| Code analysis | ✅ Integrated into evaluation prompt |
| Database | ✅ Thread-safe, override tracking |
| Teacher dashboard | ✅ Running on 0.0.0.0:8501 |
| Batch evaluation | ✅ 3 concurrent workers |
| Email delivery | ⏳ Code exists, not tested |
| Agent framework | ⏳ Planned for Week 2-3 |

---

## Next Steps

**Immediate:**
1. **Batch evaluation CLI** — Add `main.py evaluate --batch` for directory-based evaluation
2. **Rubric refinement** — Update exercise counts to match actual notebooks (NumPy I: 17, NumPy II: 19)
3. **Email testing** — Verify SMTP delivery with test emails

**Week 2-3 (Agent Framework integration):**
4. **LangGraph multi-agent** — Replace simple orchestrator with proper agent graph
5. **Human-in-the-loop** — Teacher approval workflow with agent re-evaluation
6. **Confidence scoring** — LLM self-assessment of grading confidence

**Week 4+ (Deployment):**
7. **Docker containerization** — Package for easy deployment
8. **Moodle integration** — Grade sync (pending API access)
9. **GDPR compliance** — Data retention, encryption, audit logs
10. **Full cohort testing** — 19 students × 30 assignments

---

## Infrastructure

| Component | Details |
|-----------|---------|
| LLM | `unsloth/Qwen35` on `http://192.168.0.37:8084/v1` |
| n8n | `http://192.168.0.37:5678` (being phased out) |
| Dashboard | `http://192.168.0.37:8501` |
| Database | `data/evaluations.db` (SQLite) |
| Hardware | BigBrain server with GPU |

---

## Grade Scale

| Categorical | Numeric |
|-------------|---------|
| Mal | 3 |
| Regular | 5 |
| Bien | 7 |
| Excepcional | 9 |

LLM params: `temperature=0.2`, `top_p=0.5`, `top_k=10`, `seed=42`, `max_tokens=8000`. System prompt forbids chain-of-thought output. All reports in Spanish (Spain).
