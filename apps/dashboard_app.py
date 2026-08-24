"""Teacher dashboard for reviewing and approving evaluations."""
import json
import sys
import tempfile
import requests
import streamlit as st
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config, Config
from src.db import Database
from src.llm import LLMClient
from src.agents.orchestrator import Orchestrator


@st.cache_resource
def get_db():
    """Get a shared database connection across Streamlit reruns."""
    config = get_config()
    return Database(config.database.path)


def render_config_tab():
    """Configuration tab for LLM and system settings."""
    st.header("⚙️ Configuración")

    config = get_config()
    saved = Path("config.json").exists()
    st.caption(
        f"**Configuración activa** (la que usa la evaluación): `{config.llm.base_url}` · "
        f"modelo `{config.llm.model}` · "
        + ("API key definida · " if config.llm.api_key else "sin API key · ")
        + ("origen: `config.json`" if saved
           else "origen: **valores por defecto** — no hay config.json guardado")
    )

    with st.expander("Backend LLM", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            base_url = st.text_input("URL del endpoint (OpenAI-compatible)",
                                     value=config.llm.base_url, key="cfg_base_url")
            model = st.text_input("Modelo", value=config.llm.model, key="cfg_model")
            api_key = st.text_input("API Key (opcional)", value=config.llm.api_key or "",
                                    key="cfg_api_key", type="password")
        with col2:
            temperature = st.slider("Temperature", 0.0, 2.0,
                                    float(config.llm.temperature), 0.1, key="cfg_temp")
            top_p = st.slider("Top P", 0.0, 1.0,
                              float(config.llm.top_p), 0.05, key="cfg_top_p")
            top_k = st.number_input("Top K", value=int(config.llm.top_k),
                                    key="cfg_top_k")
            max_tokens = st.number_input("Max Tokens",
                                         value=int(config.llm.max_tokens), key="cfg_max_tokens")

        if st.button("🔗 Probar conexión", type="primary"):
            with st.spinner("Conectando..."):
                try:
                    url = base_url.rstrip("/")
                    if not url.endswith("/v1"):
                        url = f"{url}/v1"
                    resp = requests.post(
                        f"{url}/chat/completions",
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": "Say OK"}],
                            "max_tokens": 10,
                        },
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}" if api_key else "",
                        },
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "N/A")
                        st.success(f"✅ Conectado — respuesta: {content[:100]}")
                    else:
                        st.error(f"❌ Error {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    with st.expander("Base de datos"):
        col1, col2 = st.columns(2)
        with col1:
            db_path = st.text_input("Ruta de la base de datos",
                                    value=config.database.path, key="cfg_db_path")
        with col2:
            rubrics_dir = st.text_input("Directorio de rúbricas",
                                        value=config.paths.rubrics_dir, key="cfg_rubrics")

    if (base_url != config.llm.base_url or model != config.llm.model
            or (api_key or None) != config.llm.api_key or temperature != config.llm.temperature
            or top_p != config.llm.top_p or int(top_k) != config.llm.top_k
            or int(max_tokens) != int(config.llm.max_tokens)
            or db_path != config.database.path or rubrics_dir != config.paths.rubrics_dir):
        st.warning("⚠️ Cambios sin guardar — pulsa 💾 Guardar configuración para que la evaluación los use.")

    if st.button("💾 Guardar configuración", type="primary"):
        new_config = Config(
            llm=type(config.llm)(
                provider="openai_compatible" if "openai" in base_url.lower() else "local",
                base_url=base_url,
                model=model,
                api_key=api_key if api_key else None,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_tokens,
            ),
            email=config.email,
            database=type(config.database)(path=db_path),
            paths=type(config.paths)(rubrics_dir=rubrics_dir, data_dir=config.paths.data_dir),
        )
        new_config.save()
        st.success("✅ Configuración guardada. Recarga la página para aplicar cambios.")


def extract_student_name(student_dir: str) -> str:
    """Extract student name from Moodle-style directory name."""
    name = student_dir.split("_assignsubmission")[0]
    return name.replace("_", " ").strip()


def find_notebooks(folder_path: str) -> list[tuple[str, str, str]]:
    """Find all notebooks in a folder. Returns list of (student_name, filepath, student_dir)."""
    notebooks = []
    base = Path(folder_path)
    for item in sorted(base.iterdir()):
        if item.is_dir():
            student_name = extract_student_name(item.name)
            for nb in sorted(item.glob("*.ipynb")):
                notebooks.append((student_name, str(nb), item.name))
        elif item.suffix == ".ipynb":
            notebooks.append(("Desconocido", str(item), ""))
    return notebooks


def render_evaluate_tab():
    """Evaluation tab for uploading and grading notebooks."""
    st.header("📝 Evaluar")

    config = get_config()
    db = get_db()

    mode = st.radio("Modo", ["📁 Carpeta (lote)", "📄 Notebook individual"], horizontal=True)

    task_key = st.selectbox(
        "Tarea (auto-detectar si vacío)",
        ["", "numpy_i", "numpy_ii"],
        help="Selecciona la tarea o déjalo vacío para detección automática",
    )

    if mode == "📁 Carpeta (lote)":
        uploaded_zip = st.file_uploader(
            "Sube la carpeta comprimida (.zip) — estructura Moodle: una subcarpeta por alumno",
            type=["zip"],
            help="Desde el terminal: zip -r entrega.zip carpeta_entrega/",
        )

        if uploaded_zip is not None:
            with tempfile.TemporaryDirectory() as tmpdir:
                import zipfile
                zipfile.ZipFile(uploaded_zip).extractall(tmpdir)

                notebooks = find_notebooks(tmpdir)
                if not notebooks:
                    st.error("No se encontraron notebooks en el archivo ZIP.")
                    return

                st.info(f"📋 {len(notebooks)} notebook(s) encontrados en {len(set(n[0] for n in notebooks))} alumno(s)")

                with st.expander("Notebooks detectados"):
                    for student_name, filepath, _ in notebooks:
                        st.text(f"  {student_name:30} → {Path(filepath).name}")

                if st.button("🚀 Evaluar lote", type="primary"):
                    llm = LLMClient(config.llm)
                    ok, detail = llm.health_check()
                    if not ok:
                        st.error(
                            f"❌ No se pudo conectar con el endpoint LLM: {detail}\n\n"
                            "Revisa la URL y el modelo en ⚙️ Configuración, guarda e inténtalo de nuevo."
                        )
                        return
                    orchestrator = Orchestrator(db, llm, config.paths.rubrics_dir)

                    max_workers = 5
                    results = []
                    completed = 0
                    progress = st.progress(0, text="Iniciando...")
                    status = st.empty()

                    def evaluate_one(student_name, filepath):
                        try:
                            result = orchestrator.evaluate_local_notebook(
                                student_name, filepath, task_key or None
                            )
                            return {
                                "student": student_name,
                                "file": Path(filepath).name,
                                "grade": result.grade.value,
                                "numeric": result.numeric_grade,
                                "error": None,
                            }
                        except Exception as e:
                            return {
                                "student": student_name,
                                "file": Path(filepath).name,
                                "grade": "ERROR",
                                "numeric": 0,
                                "error": str(e)[:100],
                            }

                    notebook_order = {Path(fp).name: i for i, (_, fp, _) in enumerate(notebooks)}

                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = {
                            executor.submit(evaluate_one, student_name, filepath): (student_name, filepath)
                            for student_name, filepath, _ in notebooks
                        }

                        for future in as_completed(futures):
                            student_name, filepath = futures[future]
                            results.append(future.result())
                            completed += 1
                            progress.progress(completed / len(notebooks),
                                              text=f"{completed}/{len(notebooks)} completados")
                            status.text(f"✅ {completed}/{len(notebooks)} — último: {student_name} / {Path(filepath).name}")

                    results.sort(key=lambda r: notebook_order.get(r["file"], 999))
                    status.text("✅ Lote completado")
                    st.dataframe(pd.DataFrame(results), use_container_width=True)

                    ok = [r for r in results if r["error"] is None]
                    if ok:
                        grades = [r["grade"] for r in ok]
                        st.write(f"**Resumen:** {len(ok)} evaluados — "
                                 f"Excepcional: {grades.count('Excepcional')}, "
                                 f"Bien: {grades.count('Bien')}, "
                                 f"Regular: {grades.count('Regular')}, "
                                 f"Mal: {grades.count('Mal')}")
        else:
            st.info("Sube un archivo ZIP con la estructura de entrega de Moodle.")
    else:
        student_name = st.text_input("Nombre del alumno")
        uploaded_file = st.file_uploader("Sube un notebook (.ipynb)", type=["ipynb"])

        if uploaded_file is not None and student_name and st.button("🚀 Evaluar", type="primary"):
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir) / uploaded_file.name
                tmp_path.write_bytes(uploaded_file.getvalue())

                with st.spinner("Evaluando..."):
                    try:
                        llm = LLMClient(config.llm)
                        ok, detail = llm.health_check()
                        if not ok:
                            raise ConnectionError(
                                f"No se pudo conectar con el endpoint LLM: {detail}. "
                                "Revisa la URL y el modelo en ⚙️ Configuración."
                            )
                        orchestrator = Orchestrator(db, llm, config.paths.rubrics_dir)
                        result = orchestrator.evaluate_local_notebook(
                            student_name, str(tmp_path), task_key or None
                        )
                        st.success(f"✅ Evaluación completada")

                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Calificación:** {result.grade.value} ({result.numeric_grade}/10)")
                        with col2:
                            st.write(f"**Tarea:** {result.topic_key or 'auto'}")

                        st.subheader("Informe")
                        st.markdown(result.markdown_report)
                    except Exception as e:
                        st.error(f"❌ Error: {e}")


def render_evaluations_tab():
    """Review and approve evaluations tab."""
    st.header("📋 Evaluaciones")

    config = get_config()
    db = get_db()

    students = db.get_all_students()
    assignments = db.get_all_assignments()

    student_names = [s["name"] for s in students]
    assignment_names = [a["name"] for a in assignments]

    selected_student = st.sidebar.selectbox("Alumno", ["Todos"] + student_names)
    selected_assignment = st.sidebar.selectbox("Asignatura", ["Todas"] + assignment_names)
    selected_grade = st.sidebar.selectbox("Calificación", ["Todas", "Mal", "Regular", "Bien", "Excepcional"])

    evaluations = db.get_all_evaluations()

    if not evaluations:
        st.info("No hay evaluaciones en la base de datos.")
        return

    df = pd.DataFrame(evaluations)

    if selected_student != "Todos":
        student = next((s for s in students if s["name"] == selected_student), None)
        if student:
            df = df[df["student_id"] == student["id"]]

    if selected_assignment != "Todas":
        assignment = next((a for a in assignments if a["name"] == selected_assignment), None)
        if assignment:
            df = df[df["assignment_id"] == assignment["id"]]

    if selected_grade != "Todas":
        df = df[df["grade"] == selected_grade]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total evaluaciones", len(df))
    col2.metric("Mal (3)", len(df[df["grade"] == "Mal"]))
    col3.metric("Regular (5)", len(df[df["grade"] == "Regular"]))
    col4.metric("Bien (7)", len(df[df["grade"] == "Bien"]))
    st.metric("Excepcional (9)", len(df[df["grade"] == "Excepcional"]))

    if len(df) > 0:
        display_df = df.copy()
        display_df["student_name"] = display_df["student_id"].apply(
            lambda sid: next((s["name"] for s in students if s["id"] == sid), "Unknown")
        )
        display_df["assignment_name"] = display_df["assignment_id"].apply(
            lambda aid: next((a["name"] for a in assignments if a["id"] == aid), "Unknown")
        )

        st.dataframe(
            display_df[["student_name", "assignment_name", "grade", "numeric_grade", "filename", "evaluated_at"]],
            use_container_width=True,
        )

        selected_eval = st.selectbox("Ver detalle", df["id"].tolist())
        if selected_eval:
            eval_data = next((e for e in evaluations if e["id"] == selected_eval), None)
            if eval_data:
                st.subheader("Detalle de Evaluación")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Alumno:** {next((s['name'] for s in students if s['id'] == eval_data['student_id']), 'Unknown')}")
                    st.write(f"**Asignatura:** {next((a['name'] for a in assignments if a['id'] == eval_data['assignment_id']), 'Unknown')}")
                    st.write(f"**Archivo:** {eval_data['filename']}")
                with col2:
                    st.write(f"**Calificación:** {eval_data['grade']} ({eval_data['numeric_grade']}/10)")
                    st.write(f"**Ejercicios sin resolver:** {eval_data.get('unresolved_exercises', 0)}")
                    st.write(f"**Fecha:** {eval_data['evaluated_at']}")

                st.markdown(eval_data["markdown_report"])

                st.subheader("Modificar Calificación")
                new_grade = st.selectbox(
                    "Nueva calificación",
                    ["Mal", "Regular", "Bien", "Excepcional"],
                    index=["Mal", "Regular", "Bien", "Excepcional"].index(eval_data["grade"]),
                    key="override_grade",
                )
                override_reason = st.text_area("Motivo del cambio")
                if st.button("Aplicar cambio"):
                    if new_grade != eval_data["grade"]:
                        db.update_evaluation_grade(eval_data["id"], new_grade, override_reason)
                        st.success("Calificación actualizada")
                    else:
                        st.warning("La calificación no ha cambiado")


def main():
    st.set_page_config(
        page_title="The Evaluator — Teacher Dashboard",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 The Evaluator — Panel de Revisión Docente")

    tab_evaluations, tab_evaluate, tab_config = st.tabs([
        "📋 Evaluaciones", "📝 Evaluar", "⚙️ Configuración"
    ])

    with tab_evaluations:
        render_evaluations_tab()
    with tab_evaluate:
        render_evaluate_tab()
    with tab_config:
        render_config_tab()


if __name__ == "__main__":
    main()
