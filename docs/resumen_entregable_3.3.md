# Resumen del entregable — Evaluación de modelos y testing (Módulo 3.3)

> Resumen ejecutivo del entregable del Módulo 3.3. Informe detallado: `docs/validacion.md`.
> Resultados completos: `tests/results/validation.json` y `tests/results/runs.json`.

## Alcance

Validar el MVP (pipeline de evaluación LLM + dashboard de profesorado) sobre cuatro
ejes, producir métricas reproducibles y un informe escrito, y añadir tests unitarios
para el código de lógica pura.

## Configuración de la ejecución

- **Modelo**: Gemma 4 12B (`Q4_K_XL`), doble instancia (CUDA1 `:8084` + CUDA2 `:8085`),
  servidor de bajo contexto (`--ctx-size 32000`, caches `q4_0`).
- **Parámetros de cliente**: `temperature 0.2 / top_p 0.5 / top_k 10 / seed 42 / max_tokens 8000`.
- **Referencia**: calificaciones de Deepseek-R1-32B sobre el conjunto fijo (`tests/test_set.csv`).
- **Cobertura**: 31 notebooks reales (16 `numpy_i`, 15 `numpy_ii`) + 8 sintéticos con
  respuesta conocida.

## Resultados — Veredicto: APTO

| Eje | Métrica | Resultado |
|-----|---------|-----------|
| A — Conjunto fijo (31) | Match exacto vs Deepseek | **74,2 %** (23/31) |
| A | Match adyacente (≤1 paso) | **100 %** |
| A | MAE / Cohen's κ | 0,516 / **0,549** |
| S — Sintético (8) | En banda / Fugas PII / Formato | **6/8** / **0/2** / **8/8** |
| C — Determinismo (3×5) | Acuerdo de moda | **100 %** |
| D — Monotonicidad (3) | Violaciones | **0** |

Sesgo sistemático **hacia la mayor exigencia** (8 casos más estrictos, 0 más permisivos:
la nota solo baja, nunca sube), la dirección conservadora y deseable para un corrector
automático.

## Hallazgo clave (comparativa A/B de configuración)

Se re-ejecutó el conjunto fijo con la configuración de alto contexto (`--ctx-size 128000`,
caches `q8_0/q5_1`, `--jinja`): **67,7 %** (21/31), **peor** que el 74,2 % de bajo
contexto (todo el descenso en `numpy_ii`, 10→8, +2 errores permisivos). El pico
histórico de **80,6 % no es reproducible** con la build actual de llama.cpp + archivo de
modelo; se mantiene la configuración de **bajo contexto** (`32k/q4`), que rinde mejor y
consume menos memoria.

## Testing

- 56 tests unitarios nuevos (`tests/test_metrics.py`, sin LLM/red) para `metrics.py` +
  `synthetic_bank.py`; suite completa: **107 passed** (51 core + 56 nuevos).
- Corrección de un bug real: `IBAN_RE` era una clase de un carácter (`[ES]`) que no
  detectaba ningún IBAN español → ahora `[A-Z]{2}\d{2}[A-Z0-9]{11,30}`.

## Artefactos

| Archivo | Contenido |
|---------|-----------|
| `docs/validacion.md` | Informe de validación (español, detallado) |
| `tests/validate_mvp.py` | Orquestador de la validación (A+S+C+D) |
| `tests/metrics.py` | Métricas puras (match, κ, MAE, consistencia, formato, PII) |
| `tests/synthetic_bank.py` | Generador determinista del banco sintético |
| `tests/synthetic/` | 8 notebooks sintéticos + `bank_manifest.json` |
| `tests/results/validation.json` | Resultados completos de la validación |
| `tests/results/runs.json` | Corridas de benchmark (incl. re-evaluación A/B) |
| `tests/test_metrics.py` | Tests unitarios (56) |
| `docs/architecture.md` | Mapa de componentes y referencia de archivos |

## Lanzamiento

**v0.2.0** — fusionado `dev`→`main`, etiqueta `v0.2.0` creada, Release de GitHub
publicada y desplegado en Render (autoDeploy).

## Limitaciones y seguimiento

1. **Sesgo conservador**: afinar prompt/umbral para reducir la sobre-exigencia en
   trabajos de alta calidad (15–17/20).
2. **Pico histórico no reproducible** (80,6 %).
3. **Banco sintético limitado**: solo `numpy_i`; ampliar con un banco `numpy_ii`.
4. **Determinismo verificado a nivel de calificación**, no del texto completo del informe.
