# Informe de Evaluación: NumPy I - Fundamentos de NumPy
**Estudiante:** Estudiante  
**Archivo:** notebook.ipynb  

## Calificación Global
**8/10 - Bien**

## Resumen de Factores Principales (70%)
El notebook presenta una **completitud excelente**, con todos los ejercicios abordados y celdas de código ejecutables. La **comprensión de la tarea** es sólida: el estudiante domina las funciones clave de NumPy (`arange`, `full`, `where`, `reshape`, `vstack`/`hstack`, `intersect1d`, indexación booleana) y logra los outputs esperados con alta **correctitud**. Se observa un proceso de aprendizaje positivo al explorar múltiples enfoques antes de llegar a la solución vectorizada óptima.

## Resumen de Factores Secundarios (30%)
La **legibilidad del código** es buena, con nombres de variables descriptivos y una estructura clara. No obstante, la **documentación y comentarios** son prácticamente inexistentes, lo que impacta negativamente en este criterio. Se recomienda incorporar comentarios breves que expliquen la lógica o el propósito de cada bloque de código para mejorar la mantenibilidad y claridad pedagógica.

## Ejercicios con Observaciones
| Nº | Ejercicio | Problema | Recomendación |
|----|-----------|----------|---------------|
| 4 | Extrae todos los impares de `my_array` | Uso inicial de bucles `for` y listas Python antes de aplicar indexación booleana. | Priorizar directamente las operaciones vectorizadas de NumPy para mayor eficiencia. |
| 5 & 6 | Sustituye impares por -1 (con y sin `where`) | Modificación *in-place* del array original en lugar de generar un nuevo array como solicita el enunciado. | Utilizar `.copy()` o asignar el resultado de la operación a una variable distinta para preservar el array original. |
| 12 | Operaciones e indexación en `my_array` | Uso de un bucle `for` para imprimir un rango de elementos. | Imprimir directamente el slice (`print(my_array[1:8])`), aprovechando la capacidad nativa de NumPy para mostrar arrays. |
| General | Todos los ejercicios | Ausencia casi total de comentarios explicativos. | Añadir comentarios concisos que justifiquen la elección de funciones o pasos clave en cada ejercicio. |