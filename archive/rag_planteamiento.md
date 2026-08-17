# Modulo 2.3 — Sistemas RAG: Planteamiento

## Proyecto: The Evaluator

Auto-calificador de notebooks Jupyter para asignaturas de un bootcamp de Data Science.

**Repo**: https://github.com/DPF0/The_Evaluator

## 1. Información interna relevante

El agente evaluador necesita acceder a documentos internos para calificar de forma consistente y alineada con los criterios del bootcamp:

| Tipo de documento | Descripción | Formato |
|-------------------|-------------|---------|
| **Rúbricas por tarea** | Criterios de evaluación específicos para cada asignatura (NumPy I, NumPy II, Pandas, etc.) | Markdown (`rubrics/rubric_*.md`) |
| **Notebooks de referencia** | Soluciones modelo evaluadas con Deepseek-R1-32B (ground truth) | Jupyter + Markdown |
| **Evaluaciones previas** | Historial de calificaciones por alumno y tarea | SQLite |
| **Metadatos de referencia** | Información extraída de los notebooks de referencia (funciones usadas, patrones, etc.) | SQLite (`reference_metadata`) |
| **Ejemplos few-shot** | Pares notebook-calificación usados para calibrar el modelo | Integrados en prompt del agente |

## 2. Almacenamiento y recuperación

### Arquitectura de recuperación

```
Notebook del alumno
    ↓
Clasificar tarea (por nombre de archivo)
    ↓
Recuperar rúbrica correspondiente (rubrics/rubric_<task>.md)
    ↓
Recuperar metadatos de referencia (SQLite → reference_metadata)
    ↓
Ensamblar prompt: sistema + rúbrica + few-shot + código del alumno
    ↓
LLM → informe de calificación
```

### ¿Por qué recuperación basada en reglas y no vectorial?

La clasificación de tareas es **determinista**: el nombre del archivo indica inequívocamente la tarea (`numpy_i`, `numpy_ii`, etc.). No existe ambigüedad semántica que requiera búsqueda por similitud.

| Criterio | Recuperación por reglas | Recuperación vectorial |
|----------|------------------------|----------------------|
| Precisión | 100% (filename → rubric) | ~90% (depende de embeddings) |
| Latencia | <1ms (lectura de archivo) | ~100ms (embedding + búsqueda) |
| Coste | Ninguno | GPU/CPU para embeddings |
| Mantenimiento | Añadir rubric.md | Indexar, reindexar, validar |
| Explicabilidad | Total (se sabe qué rubric se usa) | Parcial (similitud semántica) |

La recuperación por reglas es suficiente y superior en este caso porque:
- El espacio de tareas es cerrado y conocido (~30 tareas)
- Cada tarea tiene una única rúbrica asociada
- La clasificación por nombre de archivo es fiable (se validó frente a clasificación por contenido)

## 3. Implementación actual

### Pipeline de RAG

```python
# src/agents/orchestrator.py
def evaluate(self, notebook, student, filename, rubric, reference):
    # 1. Retrieve: rubric ya cargada por task classification
    # 2. Augment: few-shot examples + reference metadata
    # 3. Generate: LLM evaluation
    prompt = self.eval_agent.build_prompt(rubric, code, few_shot_examples)
    report = self.llm.evaluate_notebook(prompt)
    return self.extract_grade(report)
```

### Componentes

| Componente | Archivo | Función RAG |
|------------|---------|-------------|
| Task classifier | `src/agents/orchestrator.py` | Determina qué rubrica recuperar |
| Rubric loader | `src/agents/orchestrator.py` | Carga `rubrics/rubric_<task>.md` |
| Reference analyzer | `src/utils/reference.py` | Extrae metadatos de notebooks de referencia |
| Few-shot builder | `src/agents/evaluation.py` | Selecciona ejemplos representativos |
| Prompt assembler | `src/agents/evaluation.py` | Combina sistema + rubric + ejemplos + código |

### Rubric como fuente de verdad

Las rúbricas en `rubrics/` son la fuente de verdad. Se actualizan manualmente y se cargan en tiempo de ejecución (no embebidas). Cada tarea tiene su propia rúbrica:

- `rubric_numpy_i.md` → tareas NumPy I
- `rubric_numpy_ii.md` → tareas NumPy II

## 4. Mejoras futuras

### Retrieval de few-shot dinámico

Actualmente los "few-shot examples" son fijos. Se podría implementar selección dinámica basada en:
- Similitud del código del alumno con notebooks de referencia (AST-based)
- Distribución de calificaciones previas del alumno
- Complejidad detectada del notebook

### Indexación de materiales del curso

Las transcripciones de las clases podrían indexarse para:
- Enriquecer el contexto del evaluador con los objetivos de la sesión
- Detectar si el alumno cubre los temas enseñados
- Generar feedback más específico

### Vector DB para feedback personalizado

Si el espacio de tareas crece o se vuelve ambiguo, se podría añadir una vector DB (Chroma, Qdrant) para:
- Búsqueda semántica de rúbricas similares
- Recuperación de casos límite conocidos
- Recomendación de mejoras al alumno basada en errores comunes

## 5. Benchmark de modelos

Se han evaluado 7 modelos locales contra el mismo test set (31 notebooks de cursos pasados, ya evaluados):

| Modelo | Match Rate | Modo |
|--------|-----------|------|
| Gemma 4 12B Q4_K | **80.6%** | Dual instance |
| Qwen3-Coder 30B Q4_K | 74.2% | Split |
| Gemma 4 26B Q4_K | 71.0% | Split |
| GPT-oss 20B Q6_K | 51.6% | Split |
| Qwen3.6 35B Q4_K | 48.4% | Split |
| Gemma 4 12B FT | 41.9% | Dual instance |
| Qwen3.5 9B Q4_K | 16.1% | Dual instance |

Detalle completo: `docs/llm_benchmark_results.md`

## 6. Conclusiones

El sistema implementa RAG mediante recuperación determinista de rúbricas por tarea. Esta aproximación es:
- **Suficiente**: el espacio de tareas es cerrado y la clasificación es fiable
- **Eficiente**: sin overhead de embeddings ni vector DB
- **Explicable**: se sabe exactamente qué rubric se usa para cada evaluación
- **Extensible**: se pueden añadir nuevas tareas añadiendo un archivo `rubric_*.md`

La calidad de la calificación depende más del modelo LLM elegido que del mecanismo de retrieval. Gemma 4 12B alcanza 80.6% de alineación con la evaluación original.
