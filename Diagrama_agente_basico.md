# Propuesta Técnica: Agente de IA para Corrección Automatizada de Trabajos de Data Science

## 1. Flujo de Acciones Lógicas (Pasos del Agente)

El proceso se ejecuta de forma **manual y por lotes**, desencadenado por el docente cuando considere que las entregas están listas para evaluación. El flujo secuencial es el siguiente:

1. **Trigger Manual**: El profesor pulsa un botón en el panel de gestión del agente o ejecuta un script CLI que inicia la batch de corrección.
2. **Carga de Contexto de Tarea**: Se lee el notebook oficial de la asignación para extraer la rúbrica, criterios de ponderación, expectativas de resultados y guías pedagógicas.
3. **Ingesta de Repositorios**: Se consultan las URLs de GitHub proporcionadas por cada alumno. Al ser públicos, se clonan directamente mediante API o HTTPS.
4. **Análisis Estático + Extracción de Outputs**:
   - Se ejecutan herramientas de linting (`pylint`, `flake8`, `black`) y detección de patrones (imports innecesarios, fuga de datos, complejidad ciclomática).
   - Se parsean los `.ipynb` para extraer los outputs ya ejecutados por el alumno (tablas, métricas, stdout, rutas de imágenes) sin volver a ejecutar el código.
5. **Construcción de Contexto Estructurado**: Se ensambla un documento JSON/Markdown que incluye: enunciado, rúbrica, código, outputs, reportes estáticos y directrices de tono pedagógico.
6. **Inferencia del LLM On-Premise**: El contexto se envía al servidor local de IA, que genera:
   - Calificación ponderada (0-10)
   - Puntuación por criterio (opcional)
   - Feedback estructurado (puntos fuertes, errores, recomendaciones concretas)
7. **Almacenamiento y Registro**: Notas, feedback, logs y copia de los notebooks se guardan en una base de datos local cifrada con trazabilidad completa.
8. **Revisión Docente**: El equipo docente valida las calificaciones en un dashboard. Puede aprobar, modificar o solicitar reevaluación.
9. **Sincronización con Moodle**: Tras la aprobación, se invoca la API de Moodle para cargar la nota y el feedback en el gradebook del alumno.

---

## 2. Conexiones y Propósito de Cada Nodo

| Nodo / Servicio                                       | Propósito Técnico                                                                             | Tipo de Conexión                              |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **Moodle LMS**                                  | Recepción de URLs de repos, publicación de calificaciones y comentarios, autenticación SSO   | REST API / Webhooks (solo lectura/manual)      |
| **GitHub API**                                  | Clonado de repos públicos, descarga de `.ipynb`/`.py`, validación de estructura           | HTTPS / Git CLI                                |
| **Local LLM Server** (vLLM / Ollama)            | Inferencia del modelo, generación de feedback semántico, evaluación de criterios complejos   | API interna (FastAPI/HTTP) sobre GPU/CPU local |
| **Base de Datos Local** (PostgreSQL + MinIO/S3) | Almacenamiento cifrado de notebooks, logs, versiones de rúbrica, auditoría                    | TCP/IP local / S3-compatible                   |
| **Dashboard Docente**                           | UI para revisión, override de notas, visualización de confianza del modelo, gestión de colas | HTTP/HTTPS (intranet universitaria)            |
| **Static Analyzer & Output Parser**             | Validación de código, extracción de resultados ejecutados, detección de anomalías          | Procesamiento local (CPU)                      |

---

## 3. Demora Tolerable entre Nodos

Se prioriza la **precisión y trazabilidad** sobre la latencia. El sistema está diseñado para ejecución por lotes, no en tiempo real.

| Fase                                       | Demora Estimada       | Observaciones                                                                |
| ------------------------------------------ | --------------------- | ---------------------------------------------------------------------------- |
| Trigger → Ingesta GitHub + Contexto       | 5 – 15 s             | Depende del tamaño del repo y ancho de banda local                          |
| Análisis estático + extracción outputs  | 10 – 30 s            | Operaciones en CPU, paralelizables por entrega                               |
| Construcción de contexto + Inferencia LLM | 2 – 5 min            | Bottleneck principal. Aceptable por batch semanal                            |
| Almacenamiento + Sincronización Moodle    | 5 – 10 s             | API asíncrona con reintentos automáticos                                   |
| **Total por entrega**                | **~3 – 8 min** | Escalable a decenas de entregas simultáneas con cola de trabajo (Celery/RQ) |

La demora entre nodos se gestiona mediante una **cola asíncrona interna** que permite al docente lanzar la corrección y revisar los resultados cuando estén listos, sin bloquear la interfaz.

---

## 4. Costes y Mantenimiento

### Estimación Económica (On-Premise)

| Concepto                               | Estimación                                                                                  |
| -------------------------------------- | -------------------------------------------------------------------------------------------- |
| **CapEx (Infraestructura base)** | €2.500 – €4.000 (servidor GPU/CPU, almacenamiento NAS, licencia OS, UPS)                  |
| **OpEx mensual**                 | €80 – €150 (electricidad, refrigeración, backups automáticos, renovaciones de software) |
| **Coste marginal por entrega**   | €0.01 – €0.05 (energía + almacenamiento incremental)                                     |
| **Total anual estimativo**       | €3.500 – €5.800 (dependiendo de uso y vida útil del hardware)                            |

### Mantenimiento y Capacidad del Equipo Docente

- **Frecuencia de intervención**: ~5 – 10 horas/mes
- **Responsabilidades**:
  - Ajuste y versionado de prompts según feedback docente
  - Actualización del modelo LLM open-source (ej. migración a nuevas versiones o fine-tuning ligero con datos anónimos)
  - Parches de seguridad y mantenimiento de dependencias Python/Docker
  - Monitoreo de calidad (drift de calificaciones, alertas de baja confianza)
  - Gestión de política de retención y borrado GDPR
- **Perfil requerido**: Ingeniero AI/ML + DevOps base. No se requiere mantenimiento 24/7 ni soporte externo especializado.

---

## 5. Restricciones y Cumplimiento

| Restricción                           | Impacto en la Arquitectura                                                | Mitigación / Control                                                                                                                      |
| -------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **GDPR & Privacidad**            | Prohibido enviar datos a APIs externas. Almacenamiento local obligatorio. | Procesamiento 100% on-premise. Cifrado AES-256 en reposo y TLS en tránsito. Sin telemetría externa.                                      |
| **Almacenamiento de notebooks**  | Retención legal + trazabilidad académica                                | Base de datos con política de retención configurable (ej. 12 meses post-curso). Borrado seguro con log de auditoría.                    |
| **Repositorios públicos**       | Riesgo de PII o código no autorizado                                     | Sanitización automática de emails, IPs y metadatos antes de la inferencia. Acceso solo mediante URLs verificadas por el docente.         |
| **Precisión > Velocidad**       | Inferencia con modelos grandes, validación multi-criterio                | Cola batch, retry con fallback, generación de `confidence_score`. El docente aprueba antes de publicar.                                 |
| **Despliegue On-Premise**        | Dependencia de hardware local y red de campus                             | Arquitectura containerizada (Docker/K8s ligero), fácil migración entre servidores del departamento. Backup automático a NAS secundario. |
| **Override Docente Obligatorio** | La IA no publica notas directamente                                       | Flujo de aprobación en 2 pasos. Historial completo de cambios (`who/when/why`). Cumplimiento normativo académico.                      |

---

## Complemento con el Diagrama de Eraser.io

- **Capa 1 (Ingesta)** → cubre `Trigger`, `GitHub`, `Context Loader`
- **Capa 2 (Procesamiento)** → cubre `Static Analyzer`, `Output Extractor`, `Context Builder`
- **Capa 3 (IA On-Prem)** → cubre `Local LLM Server`, `Prompt Engine`, `Scoring/Feedback`
- **Capa 4 (Output/Almacenamiento)** → cubre `Local DB`, `Moodle Sync`, `Teacher Dashboard`
- **Capa 5 (Gobernanza)** → cubre `GDPR`, `Monitoring`, `Maintenance Workflow`, `Constraints`

Las flechas del diagrama reflejan fielmente el flujo secuencial y las tolerancias de latencia indicadas. El bloque de resumen incluido en el prompt de Eraser contiene las métricas de coste y restricciones para visibilidad inmediata.