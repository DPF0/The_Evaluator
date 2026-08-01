---
task: numpy_basics
assignment: "NumPy I - Fundamentos de NumPy"
course: "Data Science Bootcamp"
module: "NumPy Basics"
num_exercises: 20
weight: 1.0
---

# Rúbrica de Evaluación: NumPy I - Fundamentos

## Criterios de Evaluación

### Factores Principales (70% del peso)

#### 1. Completitud (25%)
**¿Todos los ejercicios tienen al menos una celda de código como respuesta?**

| Nivel | Criterio |
|-------|----------|
| Excelente (9-10) | Todos los 20 ejercicios completados con código ejecutable |
| Bien (7-8) | 16-19 ejercicios completados (1-4 sin resolver) |
| Regular (5-6) | 10-15 ejercicios completados (5-9 sin resolver) |
| Insuficiente (3-4) | Menos de 10 ejercicios completados |

**Penalización:** Cada ejercicio sin resolver resta 0.5 puntos de la nota base.

#### 2. Comprensión de la Tarea (25%)
**¿El estudiante usa el enfoque correcto y las funciones de NumPy apropiadas?**

| Nivel | Indicadores |
|-------|-------------|
| Excelente | Usa siempre la función de NumPy correcta; entiende la lógica detrás de cada operación |
| Bien | Usa funciones correctas en la mayoría; ocasionalmente usa workarounds funcionales |
| Regular | Mezcla funciones correctas con enfoques no óptimos; confunde algunos conceptos |
| Insuficiente | Usa listas Python en vez de arrays NumPy; no comprende operaciones vectoriales |

**Señales de alerta:**
- Crear listas manualmente en vez de `np.array()`
- Usar loops `for` donde se podría vectorizar
- Confundir `reshape`, `resize`, `resize_`
- No asignar resultados a variables cuando se requiere

#### 3. Correctitud de las Respuestas (20%)
**¿El código produce el output esperado sin errores?**

| Nivel | Criterio |
|-------|----------|
| Excelente | Todas las respuestas correctas; código libre de errores |
| Bien | 80-95% correctas; errores menores (signo, índice) |
| Regular | 60-79% correctas; errores de sintaxis o lógica |
| Insuficiente | Menos del 60% correctas; errores críticos |

**Errores comunes que penalizar:**
- Sintaxis incorrecta: `np.array[[...]]` vs `np.array([...])`
- Valores incorrectos: `True` donde debería ser `False`
- Dimensiones incorrectas en `reshape`
- No copiar arrays antes de modificarlos

### Factores Secundarios (30% del peso)

#### 4. Legibilidad del Código (15%)
| Nivel | Indicadores |
|-------|-------------|
| Excelente | Nombres de variables descriptivos; estructura clara; código limpio |
| Bien | Nombres razonables; algunos problemas menores |
| Regular | Nombres ambiguos (`ml`, `arrrrrray`, `a`); estructura confusa |
| Insuficiente | Nombres sin sentido; código ilegible |

#### 5. Comentarios y Documentación (15%)
| Nivel | Indicadores |
|-------|-------------|
| Excelente | Comentarios explicativos en cada ejercicio; docstrings en funciones |
| Bien | Comentarios en la mayoría de ejercicios |
| Regular | Pocos comentarios; solo donde es estrictamente necesario |
| Insuficiente | Sin comentarios en absoluto |

## Detalle por Ejercicio

### Ejercicios 1-6: Fundamentos de Arrays
- `np.arange()`, `np.full()`, boolean indexing, `np.where()`
- **Clave:** Entender indexación booleana y `where`
- **Error común:** Modificar array original sin hacer copia

### Ejercicios 7-10: Manipulación de Arrays
- `reshape`, `vstack`, `concatenate`, `intersect1d`
- **Clave:** Diferenciar concatenación vertical vs horizontal
- **Error común:** Confundir `axis` en concatenate

### Ejercicios 11-13: Documentación y Creación Manual
- `help()`, `np.array()`, indexación
- **Clave:** Saber consultar documentación
- **Error común:** No asignar resultado de operaciones

### Ejercicios 14-17: Secuencias y Aleatoriedad
- `np.arange` con paso, arrays random, `reshape`
- **Clave:** Multidimensionalidad y propiedades de arrays
- **Error común:** Dimensiones incorrectas

### Ejercicios 18-20: Avanzados
- Matrices 3D, valores booleanos, propiedades de arrays
- **Clave:** Entender estructura multidimensional
- **Error común:** Confundir shape, size, ndim

## Escala de Calificación

| Nota | Calificación | Criterio |
|------|-------------|----------|
| 9-10 | Excepcional | Todo perfecto + código impecable |
| 7-8 | Bien | Completado + mayoritariamente correcto |
| 5-6 | Regular | Completado con errores o incompleto pero razonable |
| 3-4 | Mal | Muy incompleto o incorrecto |

## Instrucciones para el Evaluador

1. Revisa si todos los ejercicios tienen celdas de código
2. Verifica que se usan funciones de NumPy (no Python nativo)
3. Comprueba que los outputs coinciden con lo esperado
4. Evalúa legibilidad y comentarios como factor diferencial
5. Entre dos trabajos completados, la calidad del código decide la nota
