"""
streamlit_app.py — Dulox Pricing & Costs App
=============================================
Entry point for Streamlit Cloud deployment.
Routes to the four main pages of the app.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "core"))

import streamlit as st

st.set_page_config(
    page_title="Dulox — Pricing & Costs",
    page_icon="🏭",
    layout="wide",
)

pages = st.navigation([
    st.Page("app/pages/review.py",           title="Revisar Productos",    icon="🔍"),
    st.Page("app/pages/product_intake.py",   title="Ingreso de Producto",  icon="📥"),
    st.Page("app/pages/data_input.py",       title="Datos por Perfil",     icon="✏️"),
    st.Page("app/pages/calibration.py",      title="Calibración",          icon="📊"),
    st.Page("app/pages/process_costs.py",    title="Costos de Proceso",    icon="⚙️"),
    st.Page("app/pages/product_audit.py",    title="Auditoría Producto",   icon="🔬"),
    st.Page("app/pages/material_prices.py", title="Precios de Materiales", icon="💲"),
])

pages.run()
