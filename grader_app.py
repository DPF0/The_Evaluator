import streamlit as st
import requests
import json
import time
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="AI Notebook Grader",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .grade-excepcional { background: #e3f2fd; border: 3px solid #2196f3; color: #1565c0; }
    .grade-bien { background: #e8f5e9; border: 3px solid #4caf50; color: #2e7d32; }
    .grade-regular { background: #fff3e0; border: 3px solid #ff9800; color: #ef6c00; }
    .grade-mal { background: #ffebee; border: 3px solid #f44336; color: #c62828; }
</style>
""", unsafe_allow_html=True)

# Config
DEFAULT_WEBHOOK = "http://192.168.0.37:5678/webhook/grader"

# Sidebar
with st.sidebar:
    st.markdown("### 📚 AI Notebook Grader")
    st.markdown("Automated evaluation for Data Science bootcamp assignments using RAG and LLMs.")
    
    st.divider()
    st.markdown("**Supported tasks:**")
    st.markdown("- ✅ NumPy I (Fundamentals)")
    st.markdown("- ✅ NumPy II (Advanced)")
    st.markdown("- 🔜 Pandas")
    st.markdown("- 🔜 Matplotlib")
    
    st.divider()
    webhook_url = st.text_input("🔗 Webhook URL", value=DEFAULT_WEBHOOK)
    timeout = st.slider("⏱️ Timeout (s)", 60, 300, 180)

# Header
st.markdown('<p class="main-header">🎓 AI Notebook Grader</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Upload a GitHub notebook URL → Get instant AI-powered grading</p>', unsafe_allow_html=True)

# Input form
col1, col2 = st.columns(2)
with col1:
    student_name = st.text_input("👤 Student Name", placeholder="Chiara López")
with col2:
    filename = st.text_input("📄 Filename", placeholder="Ejercicios_Numpy_I.ipynb")

github_url = st.text_input("🔗 GitHub URL (to the folder containing the notebook)", 
                           placeholder="https://github.com/user/repo/path/to/folder")

# Example button
if st.button("📋 Load Example", help="Loads test data for Chiara López"):
    student_name = "Chiara López"
    filename = "Ejercicios_Numpy_I.ipynb"
    github_url = "https://github.com/chiaralopez/2026-02-BILBAO-FT-Data-Science-1/2-Data_Analysis/1-Numpy/Practica"
    st.rerun()

# Submit
if st.button("🚀 Evaluate Notebook", type="primary", use_container_width=True):
    if not all([student_name, filename, github_url]):
        st.error("❌ Please fill all fields")
    else:
        with st.spinner("🔄 Evaluating notebook..."):
            payload = {"student_name": student_name, "filename": filename, "github_url": github_url}
            try:
                resp = requests.post(webhook_url, json=payload, timeout=timeout)
                if resp.status_code == 200 and resp.text:
                    data = resp.json()
                    
                    # Grade display
                    grade = data.get("categorical_grade", "N/A")
                    numeric = data.get("numeric_grade", "N/A")
                    grade_class = f"grade-{grade.lower()}" if grade in ["Mal","Regular","Bien","Excepcional"] else "grade-regular"
                    
                    st.markdown(f'<div class="{grade_class}" style="padding:2rem;border-radius:10px;text-align:center"><h1>{grade}</h1><h2>{numeric}/10</h2></div>', unsafe_allow_html=True)
                    
                    # Report
                    st.markdown(data.get("markdown_report", ""))
                    
                    # Download
                    st.download_button("📥 Download Report", data=data["markdown_report"], file_name=f"{student_name}_report.md", mime="text/markdown")
                else:
                    st.error("❌ Empty response from server. The workflow may have an error.")
                    st.info("Check the n8n workflow executions tab for error details.")
            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out")
            except Exception as e:
                st.error(f"❌ {e}")

st.divider()
st.caption("Built with Streamlit • Powered by n8n + Qwen3.6-MTP-27B")