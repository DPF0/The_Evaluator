# Análisis de arquitectura — Refuerzo post-MVP

> **Contexto**: Módulo 3.1 entregado y calificado 10/10 (2026-08-24). El feedback pide
> preparar el 20 % restante — refinar sin convertir el MVP en un proyecto de ingeniería.
> Este documento analiza los puntos señalados con un criterio común:
>
> **Principios** (ordenados):
> 1. Sin quebraderos de cabeza: nada que exija operar infraestructura nueva.
> 2. Proporcionalidad: el coste del cambio debe pagar el problema a escala actual (1 docente, ~20 alumnxs, 1-2 asignaturas).
> 3. Reversibilidad: preferir decisiones baratas de deshacer (tablas, archivos, un módulo) a plataformas.
> 4. Local-first / BYO-LLM: el endpoint LLM es siempre intercambiable.

## 1. Estado actual (punto de partida)

| Componente | Estado | Limitación real |
|------------|--------|-----------------|
| App | Streamlit único (dashboard) + CLI `main.py` | Sin autenticación; URL pública = acceso total (evaluar, sobrescribir notas, borrar) |
| Datos | SQLite en disco efímero del contenedor Render | Se borra en cada redeploy/reciclado (limitación conocida del free tier) |
| LLM | Un endpoint por despliegue (`LLMClient`, retry + health-check). `RoundRobinLLMClient` existe pero no se usa | Sin fallback entre endpoints, sin medición de coste (los `usage` de la respuesta se descartan) |
| Prompts | Estring interpolado en `src/agents/evaluation.py` (criterios + few-shot incluidos) | Git lo versiona, pero ninguna evaluación registra *con qué versión* se calificó |
| Guardarraíles | Distribuidos: system prompt, criterios en el prompt, regex de extracción, preflight de salud | No hay validación centralizada de entrada/salida |
| Observabilidad | Ninguna: no se persiste la respuesta LLM cruda, no hay IDs de sesión ni logs | Imposible *replay* de una corrección mala; solo queda el informe parseado |
| "Memoria" | Stateless por petición; el único estado es SQLite (evaluar por alumnx+asignatura) | Sin memoria de sesión (estado UI entre redirecciones) ni memoria de calibración por usuario |

## 2. Memoria: ¿por sesión, por usuario, ambas?

**Opciones**

| Opción | Qué es | Coste |
|--------|--------|-------|
| A. Ninguna (actual) | Cada petición es independiente | 0 |
| B. Por sesión | `st.session_state` Streamlit: progreso de batch en curso, filtros, arrastre de archivos | ≈0 (ya es el mecanismo natural) |
| C. Por usuario | "Memoria de calibración": historial de cómo ha calificado cada docente (overrides, motivos) consultable en correcciones futuras | Tabla + prompt opcional; sin embeddings |
| D. Vectorial | RAG sobre informes pasados con embeddings | Infraestructura nueva (vector store) |

**Recomendación: A + B ya, C barata, D no.**
- B no es una decisión, es usar Streamlit como debe: estado de lote, selección y filtros viven en `session_state`.
- C ya tiene la mitad hecha: la tabla `evaluations` guarda `override_reason` y `override_at`. Basta una consulta "overrides del docente en este topic" para enriquecer el prompt futuro con su criterio. Sin vectores: son decenas de filas, no miles de documentos.
- D descarta-se hoy: la escala no justifica un vector store, y el planteamiento RAG (`archive/rag_planteamiento.md`) se revisa solo si aparece la necesidad concreta de "busca casos parecidos".

## 3. Autenticación y separación evaluador / admin

**Opciones**

| Opción | Qué es | Coste |
|--------|--------|-------|
| A. Cloudflare Access por delante de la URL | Zero-code: proxy frente a `*.onrender.com`, login con cuenta Google/SSO del bootcamp | 20 min de setup, gratis para <50 usuarios, sin tocar código |
| B. Basic-auth en la app | Middleware Streamlit con usuario/contraseña (o `st.login`) | ~30 líneas; credencial en variables de entorno |
| C. IdP completo con RBAC (Auth0/Clerk) | Roles por usuario, sesiones, auditoría | Planes free acotados; SDK + flujo OAuth en la app |

**Recomendación: A (inmediata) + separación de capas en código (barata); C solo al hacer multiusuario real.**
- A resuelve el problema real sin una línea de código y sin meter contraseñas en la app.
- Separación evaluador/admin no con RBAC (sobradísimo para 1-2 personas) sino **con estructura**: el dashboard deja de ser "un montón de tabs" y pasa a dos capas claras — *docente* (subir, evaluar, aprobar, sobrescribir con motivo) y *administración* (configuración LLM, rúbricas, gestión de datos) en un apartado propio, accesible solo con un flag de rol. Es movimiento de código, no infraestructura.
- C se activaría el día en que haya >2 personas con permisos distintos; el flag de rol ya lo permite sin reescribir nada.

## 4. Gateway de modelos: control de costes y fallback

**Opciones**

| Opción | Qué es | Coste |
|--------|--------|-------|
| A. Gateway fino propio (`src/gateway.py`) | Lista ordenada de endpoints (primario + fallbacks): health-check → probar siguiente; registrar `usage` (tokens, coste estimado) en una tabla `usage_log` por evaluación | ~100 líneas + 1 tabla. Sin nuevo servicio |
| B. Gateway gestionado (LiteLLM u otro) | Servicio proxy con cuotas, métricas, balanceo | Un servicio más que levantar, configurar y vigilar |
| C. Mantener el estado actual | Un endpoint, nada de costes | 0 |

**Recomendación: A.** Es el cambio con mejor ratio de la lista.
- Fallback real: cuando el free-tier endpoint externo se satura (ocurre en Groq/OpenRouter), el gateway cambia al siguiente sin que el batch muera. `RoundRobinLLMClient` demuestra que el patrón ya se conoce; el gateway le añade *prioridad* y *relevo por salud*.
- Control de costes: hoy el campo `usage` de cada respuesta OpenAI-compatible se tira. Guardar `tokens_in/tokens_out/model/endpoint/latency` por evaluación cuesta una columna y permite la pregunta de la retroalimentación — **ratio rendimiento/coste por modelo** — con datos, no con sensaciones. Es la base medible del análisis de benchmark.
- B contradice los principios 1-2: un proxy gestionado solo empieza a pagar sus mantenedores con varios consumidores (dashboard + CLI + benchmarks) y necesidades de cuotas. Si ese día llega, A migra a B casi sin tocar agentes.

## 5. Versionar prompts y configuraciones: ¿merece la pena?

**Opciones**

| Opción | Qué es | Coste |
|--------|--------|-------|
| A. Git + rastro | Los prompts viven ya versionados en el repo. Añadir una columna `prompt_version` (hash del archivo/commit) y `model+endpoint` a `evaluations` | ~10 líneas |
| B. Gestión externa de prompts (promptfoo, DSPy, plataformas) | Ciclos de experimentación, diffs, regresión de prompts | Herramienta + flujo de trabajo |
| C. Nada | Git ya versiona el código | 0 |

**Recomendación: sí, pero solo la mitad barata — A.**
- La versión de git responde "¿cómo era el prompt entonces?"; lo que **no** responde es "¿con qué prompt se calificó *esta* evaluación concreta?" La columna `prompt_version` (+ `model`, `endpoint`) cierra esa duda por ~10 líneas y hace cada fila de `evaluations` **auditable y reproducible** ("esta nota se caló con el prompt X y el modelo Y").
- B se justifica solo cuando empiece a haber *ciclos activos de tuning* de prompts medidos contra el test set de 31 notebooks (entonces: promptfoo contra ese set). Hasta entonces es ferramenta sin problema.

## 6. Reglas y guardarraíles centralizados

**Opciones**

| Opción | Qué es | Coste |
|--------|--------|-------|
| A. Módulo `src/guardrails.py` | `validate_input(notebook)` (tamaños, saneamiento — hoy ad hoc en `clean_notebook`) y `validate_output(response)` (formato de informe, calificación en el enum, idioma, largo acotado). Los agentes lo llaman; las políticas se configuran en config | 1 archivo |
| B. Motor de políticas externo | Servicio aparte que media cada petición | Infraestructura nueva |
| C. Repartido (actual) | System prompt + regex de extracción + preflight, cada uno en su sitio | 0 |

**Recomendación: A, y pronto.** Es el cambio más barato de todos y elimina la clase de fallo que ha costado más debugging (variación de formato → extracción rota, ver "Known Limitations" de AGENTS.md). Con A, una salidas del modelo que no cumpla el contrato falla **antes** de tocar la DB, con un error legible, igual en CLI, dashboard y benchmark.

## 7. Observabilidad: replay de lo que falla y alertas

**Opciones**

| Opción | Qué es | Coste |
|--------|--------|-------|
| A. Persistencia de crudo | Columnas `raw_response` (+ opcionale `raw_prompt`) en `evaluations`; `id` de sesión ya existe (`evaluation_id`) | Ampliación de tabla |
| B. Alertas mínimas | Regla: N extracciones fallidas en un batch → aviso (el envío SMTP ya está configurado en `src/config.py`) | ~30 líneas |
| C. APM completo (Sentry/Honeycomb) | Trazas, errores, métricas gestionados | SaaS + instrumentación |

**Recomendación: A + B; C cuando el equipo crezca.**
- **Replay sin crudo es imposible**: hoy, si una corrección sale mal, solo queda el informe parseado — no se puede re-ejecutar el caso, no se puede decir qué vio el LLM, y tampoco se puede re-elegir con otro prompt/modelo. A lo hace posible y además alimenta el benchmark (mismos crudos, modelos distintos = tabla de ratios directa).
- Coste de A: `raw_response` es texto de ~2-8 KB por fila; para cientos de evaluaciones es irrelevante.
- B no es un sistema de alertas: es "el batch no se quede ciego". Con la preflight de salud ya no pasa que un endpoint caído mate el lote en silencio; B cubre el otro modo de fallo (endpoint vivo pero modelo degradado).

## 8. Hygiene: la deuda real heredada del MVP

El feedback no la cita, pero es el riesgo más concreto del despliegue actual:

| Problema | Realidad | Movimiento barato |
|----------|----------|-------------------|
| **SQLite en disco efímero** | Cada redeploy (y cada reciclado del free tier) borra evaluaciones, overrides y configuración guardada | Mover a un Postgres con tier gratuito duradero (p. ej. Supabase) — el layer `src/db.py` ya aísla el motor; es cambio de cadena de conexión, no de esquema |
| `config.json` efímero | La pestaña de Configuración se desconfigura en cada redeploy | Mismo fix (config en la BD o variables de entorno en Render, que sí persisten) |

## 9. Resumen y priorización

Criterio: impacto real vs. coste de tenerlo, siempre ≤1 módulo / ≤1 tabla sin añadir infraestructura.

| # | Cambio | Dónde | Esfuerzo | Prioridad |
|---|--------|-------|----------|-----------|
| 1 | **Hygiene**: BD duradera (Postgres) + config persistente | `src/db.py` + deploy | bajo | **P0** — sin esto, lo demás se evapora |
| 2 | **Auth**: Cloudflare Access + capas docente/admin en el dashboard | infra + `apps/` | bajo | **P0** — URL pública sin control es el riesgo mayor |
| 3 | **Observabilidad**: `raw_response` + modelo/endpoint + alerta de batch en rojo | `src/db.py`, `src/agents/` | bajo | **P0** — habilita el replay y el análisis de costes |
| 4 | **Gateway fino**: fallback por health-check + `usage_log` (coste por modelo) | `src/gateway.py` + 1 tabla | medio | **P1** — base medible del ratio rendimiento/coste |
| 5 | **Guardarraíles centralizados** | `src/guardrails.py` | bajo | **P1** |
| 6 | `prompt_version` + `model` en `evaluations` | `src/db.py` + agente | muy bajo | **P1** (hacerlo junto con 3-4) |
| 7 | **Memoria**: `session_state` en el dashboard; overrides como "criterio del docente" en el prompt | `apps/`, agente | medio | **P2** |
| 8 | LiteLLM, APM, vector DB, RBAC completo | — | alto | **No ahora** — re-evaluar con señales concretas de escala |

**Cada ítem P0/P1 cabe en una entrega pequeña, es reversible por sí solo y no depende de los demás** (salvo 6, que piggybacks de 3-4). El resultado final: la misma arquitectura que hoy, con cada capa — acceso, datos, LLM, prompt, validación, observabilidad — en su sitio propio y medible.
