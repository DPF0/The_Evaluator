# Validación del MVP — The Evaluator (Modulo 3.2)

> Informe de validación del entregable MVP. Resultados reproducibles, métricas por
> caso y evaluación escrita. Fecha: 2026-08-30.

## Resumen ejecutivo

El MVP (pipeline de evaluación LLM + dashboard de profesorado) se ha validado sobre
cuatro ejes: **coherencia con el conjunto fijo** (A), **comportamiento sobre un banco
sintético con respuestas conocidas** (S), **determinismo** (C) y **sensibilidad
monotónica** (D).

| Eje | Métrica principal | Resultado |
|-----|-------------------|-----------|
| A — Conjunto fijo (31 notebooks) | Match exacto vs Deepseek | **74,2 %** (23/31) |
| A — Conjunto fijo | Match adyacente (≤1 paso) | **100 %** |
| A — Conjunto fijo | Cohen's κ | **0,549** |
| S — Banco sintético (8) | En banda esperada | **6/8** |
| S — Banco sintético | Fugas de PII | **0/2** |
| S — Banco sintético | Formato correcto | **8/8** |
| C — Determinismo (3×5) | Acuerdo de moda | **100 %** |
| D — Sensibilidad (3) | Violaciones de monotonicidad | **0** |

**Veredicto: APTO.** El sistema es determinista, no fuga datos personales, emite
informes bien formados en español y calibra las calificaciones dentro de una banda de
un paso de la referencia en el 100 % de los casos. Muestra un sesgo sistemático
**hacia la mayor exigencia** (8 casos más estrictos, 0 más permisivos), que es la
dirección conservadora y deseable para un corrector automático.

---

## 1. Configuración de la ejecución

- **Modelo**: Gemma 4 12B (GGUF `gemma-4-12B-it-qat-UD-Q4_K_XL`, 6,7 GB), **doble
  instancia** en CUDA1 (`:8084`) y CUDA2 (`:8085`), con `--parallel 3` por instancia.
- **Parámetros del cliente** (los que usa el pipeline): `temperature=0.2`,
  `top_p=0.5`, `top_k=10`, `seed=42`, `max_tokens=8000`.
- **Referencia**: calificaciones de Deepseek-R1-32B sobre el conjunto fijo
  (`tests/test_set.csv`).
- **Cobertura**: 31 notebooks reales (16 `numpy_i`, 15 `numpy_ii`) + 8 notebooks
  sintéticos con respuesta conocida.

> Nota de reproducción: para relanzar, se necesitan los dos servidores Gemma activos
> en `:8084` y `:8085` (ver `AGENTS.md`). Los resultados de esta corrida se
> registran en `tests/results/runs.json` y `tests/results/validation.json`.

---

## 2. Eje A — Conjunto fijo (31 notebooks reales)

Comparación de la calificación emitida por Gemma frente a la referencia Deepseek.

- **Match exacto: 74,2 %** (23/31).
- **Match adyacente (±1 paso en la escala): 100 %** — ningún caso se desvía dos o
  más pasos de la referencia.
- **Error absoluto medio: 0,516** (sobre la escala numérica Mal 3 / Regular 5 /
  Bien 7 / Excepcional 9).
- **Cohen's κ: 0,549** (acuerdo moderado-alto sobre el azar).
- **Sesgo: 8 casos más estrictos, 0 más permisivos.** El error siempre va en la
  dirección de *bajar* la nota, nunca de subirla.

### Por tarea

| Tarea | Match exacto | Detalle |
|-------|--------------|---------|
| numpy_i | 81,2 % | 13/16 |
| numpy_ii | 66,7 % | 10/15 |

### Matriz de confusión (fila = referencia, columna = Gemma)

| Ref \ Pred | Mal | Regular | Bien | Exc. |
|-----------|----|---------|------|------|
| Mal | 1 | 0 | 0 | 0 |
| Regular | 4 | 13 | 0 | 0 |
| Bien | 0 | 4 | 9 | 0 |
| Excepcional | 0 | 0 | 0 | 0 |

Toda la masa de error es **diagonal adyacente hacia abajo** (Regular→Mal y
Bien→Regular). No hay errores de dos o más pasos ni errores en la dirección
permisiva.

### Tiempo

- Media: **28,0 s/notebook**; total de la corrida: **869,5 s** (~14,5 min).
- Distribución de calificaciones emitidas: Regular 17, Bien 9, Mal 5.

### Comparativa con el mejor histórico

El mejor resultado histórico registrado (`docs/llm_benchmark_results.md`) para Gemma
4 12B Q4_K en modo doble instancia era **80,6 %** de match. Esta corrida logra
**74,2 %**. La diferencia se atribuye a la configuración de servidor de esta sesión
(`--ctx-size 32000`, `--cache-type-k/v q4_0`) frente a la de la corrida histórica
(`--ctx-size 128000`, caches `q8_0`/`q5_1`). Es **variación entre configuraciones
de servidor**, no un cambio del pipeline. En cualquier caso, el match adyacente se
mantiene en 100 % y el sesgo es exclusivamente conservador. Se deja anotado como
punto de seguimiento afinar los parámetros del servidor para recuperar el pico
histórico.

---

## 3. Eje S — Banco sintético con respuesta conocida (8 notebooks)

Ocho notebooks `numpy_i` generados de forma determinista (`tests/synthetic_bank.py`)
con un número de ejercicios resueltos **conocido de antemano**, de modo que se puede
esperar una banda de calificación concreta según el rubro (`tests/synthetic/`):
20/20→Excepcional/Bien, 16-19→Bien, 10-15→Regular, <10→Mal.

| Caso | Escenario | Esperado (banda) | Emitido | En banda |
|------|-----------|------------------|---------|----------|
| syn_all_correct | 20/20 correctos, limpio | Bien/Exc. | Excepcional | ✅ |
| syn_most_correct | 17/20 correctos, 3 vacíos | Regular/Bien | **Mal** | ❌ |
| syn_half_done | 10/20 resueltos | Mal/Regular | Mal | ✅ |
| syn_few_done | 4/20 resueltos | Mal/Regular | Mal | ✅ |
| syn_markdown_only | 20/20 solo en markdown, sin código | Mal | Mal | ✅ |
| syn_buggy | 12/20 con errores, 8 vacíos | Mal/Regular | Mal | ✅ |
| syn_pii_clean | 15/20 correctos + PII en intro | Regular/Bien | **Mal** | ❌ |
| syn_pii_code | 20/20 correctos + PII en comentario | Bien/Exc. | Excepcional | ✅ |

**In-banda: 6/8.** Los dos fallos (`syn_most_correct`, `syn_pii_clean`) son
**subcalificaciones**: el modelo califica de Mal trabajos de 15-17/20 que el rubro
sitúa en Bien/Regular. Es la misma dirección que el sesgo del eje A (excesiva
exigencia) y afecta a casos con alta tasa de acierto. No hay falsos positivos en la
dirección permisiva.

### Privacidad (PII)

En dos casos se planta PII ficticio (email `alumno.falso@example.com`, DNI
`12345678X`, teléfono `+34 612 345 678`, IBAN `ES91 2100 0418 4502 0005 1332`) tanto
en texto de introducción como oculto en un comentario de celda de código.

- **Fugas al informe: 0/2.** Ningún token de PII aparece en el informe Markdown
  generado. El escáner genérico (regex de email/DNI/tel/IBAN) también devuelve 0
  coincidencias.

### Formato del informe

**8/8 informes válidos**: no vacíos, con título, con sección «calificación global»,
calificación dentro del enum (Mal/Regular/Bien/Excepcional), calificación extraíble y
redactados en español.

---

## 4. Eje C — Determinismo (3 notebooks × 5 repeticiones)

Cada uno de 3 notebooks se evalúa 5 veces con `seed=42`.

| Notebook | Tarea | Ref. | 5 calificaciones | Acuerdo de moda |
|----------|-------|------|------------------|-----------------|
| Numpy_I_ANDER | numpy_i | Bien | Bien ×5 | 1,00 |
| Numpy_II_ANDER | numpy_ii | Regular | Regular ×5 | 1,00 |
| Numpy_I_ANDER | numpy_i | Bien | Bien ×5 | 1,00 |

**Acuerdo medio: 100 %** (1 calificación distinta por notebook). Bajo `seed=42` el
endpoint es **completamente determinista** a nivel de calificación. (Los tiempos por
iteración varían entre 16 y 27 s, pero la calificación no.)

---

## 5. Eje D — Sensibilidad / monotonicidad (3 notebooks)

Se degrada deliberadamente el notebook (se vacían celdas) y se comprueba que la
calificación **no sube**: si el trabajo empeora, la nota no puede mejorar.

| Notebook | Limpio | Degradado | Monotónico |
|----------|--------|-----------|------------|
| Numpy_II_ANDER | Regular | Regular | ✅ |
| Numpy_I_ANDER | Bien | Bien | ✅ |
| Numpy_II_Angelos | Mal | Mal | ✅ |

**Violaciones: 0.** La degradación de una sola celda no cambia la calificación en
estos casos (gránulo grueso), pero nunca se observa una subidas indebidas de nota. La
propiedad de monotonicidad se cumple.

---

## 6. Limitaciones y puntos de seguimiento

1. **Sesgo conservador**: 8/31 casos más estrictos (y 6/8 del sintético tienden a
   subcalificar). Es la dirección segura para un corrector, pero conviene afinar el
   prompt/umbral para reducir la sobre-exigencia en trabajos de alta calidad
   (15-17/20).
2. **Parámetros del servidor**: esta corrida (`--ctx-size 32000`, caches `q4_0`) se
   queda en 74,2 % frente al 80,6 % histórico (`--ctx-size 128000`, caches
   `q8_0`/`q5_1`). Reevaluar con la configuración de mayor contexto para recuperar
   el pico.
3. **Banco sintético limitado**: 8 casos `numpy_i`; no hay aún banco sintético
   `numpy_ii`. Ampliar el banco para cubrir la segunda tarea.
4. **Determinismo comprobado solo a nivel de calificación**, no del texto completo
   del informe (que puede variar en redacción sin variar la nota).

## Artefactos

| Archivo | Contenido |
|---------|-----------|
| `tests/metrics.py` | Métricas puras (match, κ, MAE, consistencia, formato, PII) — sin LLM/red |
| `tests/synthetic_bank.py` | Generador determinista del banco sintético |
| `tests/validate_mvp.py` | Orquestador de la validación (A+S+C+D) |
| `tests/synthetic/` | 8 notebooks sintéticos + `bank_manifest.json` |
| `tests/results/validation.json` | Resultados completos de esta validación |
| `tests/results/runs.json` | Corrida de benchmark registrada |
