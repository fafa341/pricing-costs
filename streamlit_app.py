"""
streamlit_app.py — Dulox Pricing & Costs App
=============================================
Entry point for Streamlit Cloud deployment.
Routes to the four main pages of the app.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

import streamlit as st

st.set_page_config(
    page_title="Dulox — Pricing & Costs",
    page_icon="🏭",
    layout="wide",
)

pages = st.navigation([
    st.Page("scripts/review.py",                    title="Revisar Productos",    icon="🔍"),
    st.Page("scripts/_pages/product_intake.py",     title="Ingreso de Producto",  icon="📥"),
    st.Page("scripts/_pages/data_input.py",         title="Datos por Perfil",     icon="✏️"),
    st.Page("scripts/_pages/calibration.py",        title="Calibración",          icon="📊"),
    st.Page("scripts/_pages/process_costs.py",      title="Costos de Proceso",    icon="⚙️"),
    st.Page("scripts/_pages/product_audit.py",      title="Auditoría Producto",   icon="🔬"),
])

pages.run()
