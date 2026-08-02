"""Teacher dashboard for reviewing and approving evaluations."""
import streamlit as st
import pandas as pd
from pathlib import Path
from src.config import get_config
from src.db import Database
from src.models import Grade


def main():
    st.set_page_config(
        page_title="The Evaluator — Teacher Dashboard",
        page_icon="📊",
        layout="wide",
    )

    config = get_config()
    db = Database(config.database.path)

    st.title("📊 The Evaluator — Panel de Revisión Docente")

    # Sidebar with filters
    st.sidebar.header("Filtros")
    students = db.get_all_students()
    assignments = db.get_all_assignments()

    student_names = [s["name"] for s in students]
    assignment_names = [a["name"] for a in assignments]

    selected_student = st.sidebar.selectbox("Alumno", ["Todos"] + student_names)
    selected_assignment = st.sidebar.selectbox("Asignatura", ["Todas"] + assignment_names)
    selected_grade = st.sidebar.selectbox("Calificación", ["Todas", "Mal", "Regular", "Bien", "Excepcional"])

    # Get all evaluations
    evaluations = db.get_all_evaluations()

    if not evaluations:
        st.info("No hay evaluaciones en la base de datos.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(evaluations)

    # Apply filters
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

    # Stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total evaluaciones", len(df))
    col2.metric("Mal (3)", len(df[df["grade"] == "Mal"]))
    col3.metric("Regular (5)", len(df[df["grade"] == "Regular"]))
    col4.metric("Bien (7)", len(df[df["grade"] == "Bien"]))

    st.metric("Excepcional (9)", len(df[df["grade"] == "Excepcional"]))

    # Evaluations table
    st.subheader("Evaluaciones")
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

        # Detailed view
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

                # Override grade
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
                        db.update_evaluation_grade(
                            eval_data["id"],
                            new_grade,
                            override_reason,
                        )
                        st.success("Calificación actualizada")
                    else:
                        st.warning("La calificación no ha cambiado")

    db.close()


if __name__ == "__main__":
    main()
