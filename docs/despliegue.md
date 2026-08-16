# Despliegue — Módulo 3.1

## Objetivo

Expresar el MVP de **The Evaluator** a terceros (equipo docente y personas que
quieran probarlo) mediante una URL pública, con una interfaz de acceso (Streamlit)
y un backend LLM configurable sin exponer nuestra infraestructura interna.

## Opciones valoradas

| Opción | Coste | Ventajas | Inconvenientes | ¿Descartado? |
|--------|-------|----------|----------------|-------------|
| **Cloudflare Tunnel (quick tunnel)** del servidor local | Gratis | 1 comando, todo local (LLM incluido) | Solo accesible con la máquina encendida; URL efímera; requiere exponer parte del servidor | Sí — no queremos exponer el servidor local |
| **Streamlit Community Cloud** | Gratis (subdominio `*.streamlit.app`) | Diseñado para Streamlit, 24/7 | Carpeta de la app read-only: guardar la configuración desde la UI podría fallar | Posible alternativa |
| **Render** (free tier, web service) | Gratis (512 MB, `*.onrender.com`) | **La plataforma sugerida en la tarea**; despliega desde nuestro `Dockerfile` ya existente; variables de entorno con secretos | Duerme tras 15 min inactivo (despierta en 30-60 s); 512 MB; sistema de archivos efímero | **Opción elegida** |
| **Hugging Face Spaces** | Gratis | Streamlit/Gradio nativo | Repo read-only → el guardado de configuración no funciona | Sí |
| **VM Oracle Always Free** (4 cores / 24 GB) | Gratis (requiere tarjeta como garantía, sin cobro) | 24/7, control total; podría alojar también un LLM de referencia (Ollama) para quien no tenga clave API | Más esfuerzo de setup (cuenta, SSH, docker) | Guardado como evolución |

## Opción elegida y por qué

**Render (web service, free tier)** desplegando la imagen Docker existente.

1. Es la plataforma citada explícitamente en la tarea ("exponer nuestro agente en
   una plataforma como Render y plantear una interfaz de acceso").
2. El `Dockerfile` del proyecto ya estaba listo (Python 3.12 slim, Streamlit en
   `:8501`, healthcheck en `/_stcore/health`), así que el despliegue no requirió
   cambios de código.
3. El free tier es suficiente para un MVP de demostración.

## Decisión de arquitectura: el LLM lo aporta quien prueba

**No exponemos nuestro servidor LLM local** (`192.168.0.37:8084`) a Internet.
En su lugar, la instancia pública funciona así:

- La app se instala con una configuración por defecto (nuestro endpoint LAN),
  **no accesible desde fuera**. Antes de evaluar, el panel muestra un aviso.
- La pestaña **⚙️ Configuración** del dashboard permite a quien lo pruebe
  introducir cualquier backend OpenAI-compatible: URL, modelo y API key
  (por ejemplo, una clave gratuita de Groq, OpenRouter o Google AI Studio).
- La configuración se guarda en el contenedor (prefijo de variables de
  entorno `EVALUATOR_*` > `config.json` > valores por defecto), y el botón
  **"Probar conexión"** verifica el endpoint antes de lanzar un lote.

Esto cumple el objetivo de la tarea —demostrar que el agente funciona de extremo
a extremo— sin comprometer infraestructura propia, y además hace que el
proyecto sea portable: el mismo dashboard funciona con cualquier backend
(llama.cpp, vLLM, API cloud).

## Qué hizo falta técnicamente (cambios en el repo)

| Cambio | Archivo | Motivo |
|--------|---------|--------|
| Declarar dependencias | `requirements.txt` | Era implícito el stack; se añade `pandas` (se usaba solo por dependencia transitiva de Streamlit). Lo usan Docker y Render. |
| Blueprint de despliegue | `render.yaml` | Deployment con un clic desde Render: runtime Docker, plan free, healthcheck, auto-deploy en cada push a `main`. |
| Dockerfile | `Dockerfile` | Ya existía; se mantuvo (build verificado localmente: contenedor levanta y pasa el healthcheck). |
| Batch en paralelo | `apps/dashboard_app.py` | `ThreadPoolExecutor(5)`: hasta 5 notebooks se evalúan a la vez (alineado con `--parallel 5` del servidor LLM local). |
| Clasificación robusta | `src/utils/task_classifier.py` | Fast-path por nombre de archivo + content scoring con word boundaries; verificado con 10 notebooks de 5 alumnos. |

## Pasos de despliegue (Render)

1. Conectar el repo `DPF0/The_Evaluator` en [dashboard.render.com](https://dashboard.render.com).
2. **New → Blueprint** → seleccionar el repo → Render lee `render.yaml` (servicio web `the-evaluator`, plan free) → **Apply**.
3. El primer build dura ~2-3 min. URL resultante:
   **https://the-evaluator.onrender.com**
4. Cada push a `main` re-despliega automáticamente (auto-deploy).

## Resultado final y cómo probarlo

Estado: desplegado en Render (free tier) — ver URL arriba.

Para probarlo:

1. Abrir la URL → pestaña **📝 Evaluar**.
2. Pestaña **⚙️ Configuración** → introducir un backend LLM propio
   (OpenAI-compatible) → **Probar conexión**.
3. Subir un ZIP con la estructura de Moodle (una subcarpeta por alumno,
   notebooks `.ipynb` dentro) — p. ej., el `test_batch.zip` de ejemplo
   (5 alumnos × 2 notebooks NumPy) — y pulsar **Evaluar lote**.
4. Resultados en la pestaña **📋 Evaluaciones** (calificación, informe Markdown,
   posibilidad de revisar y_override con motivo la nota).

## Limitaciones conocidas (aceptadas para un MVP)

- **Free tier de Render**: 512 MB de RAM, y el servicio duerme tras 15 minutos
  de inactividad (el primer request después de despertarlo tarda 30-60 s).
- **Sistema de archivos efímero**: la base SQLite y la configuración guardada
  desde la UI se reinician en cada re-despliegue. Para demo basta; para uso
  real tocaría persistencia externa (p. ej. Postgres o disco conectado).
- **El LLM por defecto no es alcanzable desde Internet** (diseño a propósito):
  quien lo prueba debe configurar el suyo.

## Evolución prevista

- **VM Oracle Always Free** como host 24/7, opcionalmente con un LLM de
  referencia (Ollama + modelo pequeño) para que quien no tenga clave API pueda
  probar el flujo completo sin configurar nada.
- Persistencia de la base de datos externa a Render.
- Posible variante de interfaz con Gradio si se quiere una demo aún más simple.
