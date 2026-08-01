---
task: numpy_intermediate
assignment: "NumPy II - Manipulación Avanzada"
course: "Data Science Bootcamp"
module: "NumPy Intermediate"
num_exercises: 19
weight: 1.0
---

# Rúbrica de Evaluación: NumPy II - Manipulación Avanzada

## Criterios de Evaluación

### Factores Principales (70% del peso)

#### 1. Completitud (25%)
**¿Todos los ejercicios tienen al menos una celda de código como respuesta?**

| Nivel | Criterio |
|-------|----------|
| Excelente (9-10) | Todos los 19 ejercicios completados con código ejecutable |
| Bien (7-8) | 16-18 ejercicios completados (1-3 sin resolver) |
| Regular (5-6) | 10-15 ejercicios completados (4-8 sin resolver) |
| Insuficiente (3-4) | Menos de 10 ejercicios completados |

**Penalización:** Cada ejercicio sin resolver resta 0.5 puntos de la nota base.

#### 2. Comprensión de la Tarea (25%)
**¿El estudiante demuestra dominio de slicing, indexing y manipulación avanzada?**

| Nivel | Indicadores |
|-------|-------------|
| Excelente | Usa slicing avanzado correctamente; entiende inversión de ejes; encapsula en funciones cuando se pide |
| Bien | slicing correcto en la mayoría; confunde ocasionalmente índices negativos vs positivos |
| Regular | Funcional pero usa múltiples celdas para lograr lo que una haría; workarounds |
| Insuficiente | Confunde reshape con slicing; no entiende matrices 2D |

**Señales de alerta:**
- Usar `.T` cuando debería ser `[::-1, ::-1]` (inversión ≠ transposición)
- Múltiples enfoques redundantes en la misma celda
- No encapsular código en funciones cuando se solicita explícitamente
- `np.random.rand()` vs arrays de enteros

#### 3. Correctitud de las Respuestas (20%)
**¿El código produce el output esperado sin errores?**

| Nivel | Criterio |
|-------|----------|
| Excelente | Todos correctos; código limpio |
| Bien | 80-95% correctos; errores menores |
| Regular | 60-79% correctos; errores de lógica |
| Insuficiente | < 60% correctos |

**Errores comunes que penalizar:**
- Slicing incorrecto: `[-2:-4:-1]` cuando basta `[-2:]`
- `reshape` dimensiones incompatibles
- No usar step en slicing `[::2]`
- Confundir `np.nonzero()` con indexación booleana

### Factores Secundarios (30% del peso)

#### 4. Legibilidad del Código (15%)
| Nivel | Indicadores |
|-------|-------------|
| Excelente | Nombres descriptivos; slicing limpio; funciones bien definidas |
| Bien | Razonablemente legible |
| Regular | Nombres ambiguos; código redundante |
| Insuficiente | Ilegible |

#### 5. Comentarios y Documentación (15%)
| Nivel | Indicadores |
|-------|-------------|
| Excelente | Comentarios explicativos; docstrings en funciones |
| Bien | Comentarios presentes |
| Regular | Pocas o ningún comentario |
| Insuficiente | Sin comentarios |

## Detalle por Ejercicio

### Ejercicios 1-3: Slicing Avanzado
- Indexación negativa, paso, inversión
- **Clave:** Dominio de `[start:stop:step]` y `::-1`

### Ejercicios 4-7: Manipulación de Matrices 2D
- `reshape`, slicing 2D, inversión, extracción de sub-matrices
- **Clave:** Slicing en dos dimensiones `[rows, cols]`
- **Error común:** Confundir `.T` con inversión completa

### Ejercicios 8-9: Filtrado y División
- Indexación booleana, `np.where()`, `np.vsplit()`
- **Clave:** Múltiples métodos para filtrar; dividir arrays

### Ejercicios 10-12: Funciones y Operaciones
- Memoria, `np.nonzero()`, encapsular en funciones
- **Clave:** Documentar funciones con docstrings

### Ejercicios 13-16: Estadística y Patrones
- `np.mean()`, `np.std()`, normalización, patrones de matrices
- **Clave:** Estadística básica con NumPy; crear patrones con slicing

### Ejercicios 17-19: Avanzados
- `np.tile()`, normalización completa, interpolación
- **Clave:** Reutilización de patrones; normalización z-score

## Escala de Calificación

| Nota | Calificación | Criterio |
|------|-------------|----------|
| 9-10 | Excepcional | Todo perfecto + código impecable |
| 7-8 | Bien | Completado + mayoritariamente correcto |
| 5-6 | Regular | Completado con errores o incompleto pero razonable |
| 3-4 | Mal | Muy incompleto o incorrecto |

## Diferencias Clave entre NumPy I y II

| Aspecto | NumPy I | NumPy II |
|---------|---------|----------|
| Complejidad slicing | 1D básico | 2D avanzado + pasos negativos |
| Funciones | `arange`, `full`, `where` | `nonzero`, `tile`, `vsplit` |
| Énfasis | Creación y manipulación básica | Transformación avanzada y estadística |
| Funciones requeridas | No | Sí (ejercicio 12) |
