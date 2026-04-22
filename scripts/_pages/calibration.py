"""
calibration.py — Dulox Cost Calibration Tool
=============================================
Valida el sistema de puntos G/D/C/X contra costos reales medidos en fábrica.
Compara dos productos del mismo perfil en distintas complejidades para testear:
  1. Si el salto de costos C2→C3 está justificado por los drivers
  2. Si los umbrales de complejidad están bien calibrados
  3. Cómo escala el costo con cada driver
  4. Si la extrapolación a productos nuevos es coherente

Perfil inicial: p-basurero-cil
  C2 Ancla:  BAPLA-0470 | Basurero Plaza con Cenicero
  C3:        BARE4-01300 | Basurero Reciclaje 4 Compartimientos

Run:  streamlit run scripts/review.py
"""

import json
import math
import sys
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import date, datetime

ROOT         = Path(__file__).resolve().parent.parent.parent
CHUNKS_PATH  = ROOT / "files-process" / "process-measurements" / "knowledge-chunks.jsonl"
sys.path.insert(0, str(ROOT / "scripts"))
from db import load_rules, save_rules, get_sb, load_profile_products as _load_profile_raw, save_bom as _save_bom_db


def _load_chunks() -> list[dict]:
    """Load all knowledge chunks from JSONL file."""
    if not CHUNKS_PATH.exists():
        return []
    chunks = []
    for line in CHUNKS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return chunks


def _write_chunk(chunk: dict):
    """Append a chunk to knowledge-chunks.jsonl, superseding any prior chunk with same chunk_id."""
    existing = _load_chunks()
    # Mark any old chunk with the same id as superseded
    for c in existing:
        if c.get("chunk_id") == chunk["chunk_id"]:
            c["metadata"]["superseded_by"] = chunk["chunk_id"] + "-new"
            c["metadata"]["valid_until"] = str(date.today())
    # Append new chunk
    existing.append(chunk)
    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHUNKS_PATH.write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in existing) + "\n",
        encoding="utf-8"
    )


@st.cache_data(ttl=15)
def _load_profile(profile_key: str) -> pd.DataFrame:
    rows = _load_profile_raw(profile_key)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # Sort: complejidad asc, anchors first
    if "is_anchor" in df.columns and "complejidad" in df.columns:
        df = df.sort_values(["complejidad", "is_anchor"], ascending=[True, False]).reset_index(drop=True)
    return df


@st.cache_data(ttl=15)
def _load_bucket(profile_key: str, complejidad: str) -> pd.DataFrame:
    df = _load_profile(profile_key)
    if df.empty or "complejidad" not in df.columns:
        return pd.DataFrame()
    return df[df["complejidad"] == complejidad].reset_index(drop=True)


def _save_bom_to_db(handle: str, mat_df: pd.DataFrame, cons_df: pd.DataFrame):
    """Persist BOM dataframes as JSON via Supabase."""
    mat_rows  = mat_df.to_dict("records")  if isinstance(mat_df,  pd.DataFrame) else []
    cons_rows = cons_df.to_dict("records") if isinstance(cons_df, pd.DataFrame) else []
    _save_bom_db(handle, mat_rows, cons_rows)
    _load_profile.clear()
    _load_bucket.clear()

# ─── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
<style>
html, body, [data-testid="stAppViewContainer"] { background-color:#0d1117; color:#e6edf3; }
[data-testid="stSidebar"] { background-color:#161b22 !important; border-right:1px solid #30363d; }
h1,h2,h3 { color:#f0f6fc !important; }
.cal-card {
    background:#161b22; border:1px solid #30363d; border-radius:10px;
    padding:1.1rem 1.3rem; margin-bottom:0.8rem;
}
.cal-card-blue  { background:#0d2137; border:1px solid #1f6feb; border-radius:10px; padding:1.1rem 1.3rem; margin-bottom:0.8rem; }
.cal-card-green { background:#0d3321; border:1px solid #238636; border-radius:10px; padding:1.1rem 1.3rem; margin-bottom:0.8rem; }
.cal-card-amber { background:#2d1b00; border:1px solid #9e6a03; border-radius:10px; padding:1.1rem 1.3rem; margin-bottom:0.8rem; }
.cal-card-red   { background:#3d0c0c; border:1px solid #da3633; border-radius:10px; padding:1.1rem 1.3rem; margin-bottom:0.8rem; }
.sec-label { font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:#768390; margin-bottom:0.3rem; }
.badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:700; letter-spacing:0.04em; }
.badge-c1 { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-c2 { background:#2d1b00; color:#e3b341; border:1px solid #9e6a03; }
.badge-c3 { background:#3d0c0c; color:#f85149; border:1px solid #da3633; }
.badge-ok   { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-warn { background:#2d1b00; color:#e3b341; border:1px solid #9e6a03; }
.badge-err  { background:#3d0c0c; color:#f85149; border:1px solid #da3633; }
.number-big { font-size:2.2rem; font-weight:700; color:#e6edf3; }
.number-sub { font-size:0.75rem; color:#768390; margin-top:2px; }
[data-testid="stMetricContainer"], [data-testid="metric-container"] {
    background:#161b22; border:1px solid #30363d; border-radius:8px; padding:0.75rem 1rem;
}
[data-testid="stTabs"] [data-testid="stTab"] { color:#8b949e !important; }
[data-testid="stTabs"] [aria-selected="true"] { color:#58a6ff !important; border-bottom:2px solid #58a6ff; }
hr { border-color:#21262d !important; }
[data-testid="stExpander"] { background:#161b22 !important; border:1px solid #30363d !important; border-radius:8px !important; }
[data-testid="stDataFrameResizable"] { border:1px solid #30363d; border-radius:8px; }
</style>
"""

# ─── Pre-populated BOM from measurements-p1.md ───────────────────────────────

BARE4_MATERIALS_DEFAULT = [
    {"Subconjunto": "Zócalo",                "Dimensiones": "275x1351mm",   "Material": "AISI 304-L 1.5mm", "kg_ml": 3.4,   "precio_kg": 3600, "total": 12240},
    {"Subconjunto": "Base inferior",         "Dimensiones": "120x1305mm",   "Material": "AISI 304-L 1.5mm", "kg_ml": 1.73,  "precio_kg": 3600, "total": 6228},
    {"Subconjunto": "Pletina base",          "Dimensiones": "158x1365mm",   "Material": "AISI 304-L 1.5mm", "kg_ml": 2.4,   "precio_kg": 3600, "total": 8640},
    {"Subconjunto": "Base",                  "Dimensiones": "228x1350mm",   "Material": "AISI 304-L 1.5mm", "kg_ml": 3.4,   "precio_kg": 3600, "total": 12240},
    {"Subconjunto": "Tapas laterales",       "Dimensiones": "788x286mm (2)","Material": "AISI 304-L 1.5mm", "kg_ml": 5.3,   "precio_kg": 3600, "total": 19080},
    {"Subconjunto": "Manto",                 "Dimensiones": "1543x769mm (2)","Material": "AISI 304-L 1.5mm","kg_ml": 25.9,  "precio_kg": 3600, "total": 93240},
    {"Subconjunto": "Zócalo base",           "Dimensiones": "600x1350mm",   "Material": "AISI 304-L 1.5mm", "kg_ml": 8.188, "precio_kg": 3600, "total": 29477},
    {"Subconjunto": "Refuerzo lateral",      "Dimensiones": "148x260mm (2)","Material": "AISI 304-L 1.5mm", "kg_ml": 0.72,  "precio_kg": 3600, "total": 2592},
    {"Subconjunto": "Tapa",                  "Dimensiones": "199x178mm (3)","Material": "AISI 304-L 1.5mm", "kg_ml": 1.14,  "precio_kg": 3600, "total": 4104},
    {"Subconjunto": "Pletina patín",         "Dimensiones": "120x350mm (2)","Material": "AISI 304-L 1.5mm", "kg_ml": 0.9,   "precio_kg": 3600, "total": 3240},
    {"Subconjunto": "Caluga",                "Dimensiones": "45x50mm (2)",  "Material": "AISI 304-L 1.5mm", "kg_ml": 0.04,  "precio_kg": 3600, "total": 144},
    {"Subconjunto": "Pletina manto",         "Dimensiones": "135x3400mm",   "Material": "AISI 304-L 1.5mm", "kg_ml": 5.52,  "precio_kg": 3600, "total": 19872},
    {"Subconjunto": "Basureros interiores",  "Dimensiones": "740x1156mm (4)","Material": "Acero 430 1mm",   "kg_ml": 27.44, "precio_kg": 3600, "total": 98784},
    {"Subconjunto": "Basureros base int.",   "Dimensiones": "288x323mm (4)","Material": "Acero 430 1mm",    "kg_ml": 2.96,  "precio_kg": 3600, "total": 10656},
    {"Subconjunto": "Patines (4)",           "Dimensiones": "ø40x60mm",     "Material": "Varios",           "kg_ml": 4.0,   "precio_kg": 1500, "total": 6000},
    {"Subconjunto": "Tuercas 3/8",           "Dimensiones": "8 u",          "Material": "Acero Galvanizado","kg_ml": 8.0,   "precio_kg": 94,   "total": 752},
    {"Subconjunto": "Pomeles 3/8 inox",      "Dimensiones": "2 u",          "Material": "Acero Inoxidable", "kg_ml": 2.0,   "precio_kg": 2600, "total": 5200},
    {"Subconjunto": "Manillas embutidas",    "Dimensiones": "2 u",          "Material": "Acero Inoxidable", "kg_ml": 2.0,   "precio_kg": 3720, "total": 7440},
    {"Subconjunto": "Logo",                  "Dimensiones": "1 u",          "Material": "Varios",           "kg_ml": 1.0,   "precio_kg": 3600, "total": 3600},
]

BARE4_CONSUMABLES_DEFAULT = [
    {"Producto": "Disco Desbaste Rolden 4.5\"", "Proceso": "pulido",          "Cantidad": 2, "Unidad": "u", "Precio_u": 2500,  "Total": 5000},
    {"Producto": "Disco de Lija Grano 80",      "Proceso": "pulido",          "Cantidad": 2, "Unidad": "u", "Precio_u": 460,   "Total": 920},
    {"Producto": "Disco Traslapado",             "Proceso": "pulido",          "Cantidad": 1, "Unidad": "u", "Precio_u": 1681,  "Total": 1681},
    {"Producto": "Grata Roja",                   "Proceso": "pulido",          "Cantidad": 2, "Unidad": "u", "Precio_u": 5800,  "Total": 11600},
    {"Producto": "Huaipe",                       "Proceso": "pulido",          "Cantidad": 1, "Unidad": "u", "Precio_u": 3500,  "Total": 3500},
    {"Producto": "Disco Multifinic",             "Proceso": "pulido",          "Cantidad": 1, "Unidad": "u", "Precio_u": 32400, "Total": 32400},
    {"Producto": "Traslapos pequeños 50x30",     "Proceso": "pulido",          "Cantidad": 1, "Unidad": "u", "Precio_u": 1100,  "Total": 1100},
    {"Producto": "Pasta de pulir (pomo)",        "Proceso": "pulido",          "Cantidad": 1, "Unidad": "u", "Precio_u": 3500,  "Total": 3500},
    {"Producto": "Spray limpiador inox",         "Proceso": "pulido",          "Cantidad": 1, "Unidad": "u", "Precio_u": 8072,  "Total": 8072},
    {"Producto": "Disco de corte 4 1/2\"",       "Proceso": "armado_trazado",  "Cantidad": 1, "Unidad": "u", "Precio_u": 548,   "Total": 548},
    {"Producto": "Lija Metal Grano 80",          "Proceso": "pulido",          "Cantidad": 1, "Unidad": "u", "Precio_u": 592,   "Total": 592},
    {"Producto": "Tungsteno 3/32",               "Proceso": "soldadura",       "Cantidad": 1, "Unidad": "u", "Precio_u": 2790,  "Total": 2790},
    {"Producto": "Argón",                        "Proceso": "soldadura",       "Cantidad": 256, "Unidad": "L","Precio_u": 7,    "Total": 1897},
]

BAPLA_MATERIALS_DEFAULT = [
    {"Subconjunto": "", "Dimensiones": "", "Material": "", "kg_ml": 0.0, "precio_kg": 3600, "total": 0},
]

BAPLA_CONSUMABLES_DEFAULT = [
    {"Producto": "", "Proceso": "pulido", "Cantidad": 0, "Unidad": "u", "Precio_u": 0, "Total": 0},
]

# ─── Process templates (hardcoded — immune to JSON formatter stripping) ───────
# Mirrors PROCESS_THRESHOLDS.md. Each process defines:
#   drivers          — which universal drivers contribute to THIS process's score
#   score_thresholds — {level: [lo, hi]} inclusive score ranges
#   descriptions     — human-readable description per level
#   C1/C2/C3         — T_setup_min, T_exec_min, n_ops for that level

PROCESS_TEMPLATES = {
    # Drivers: which universal scores sum to determine THIS process's level.
    # score_thresholds: inclusive [lo, hi] per level.
    # Descriptions are process-level, not product-specific.
    "armado_trazado": {
        "drivers": ["G", "X"],
        "score_thresholds": {"C1": [1,2], "C2": [3,4], "C3": [5,99]},
        "descriptions": {
            "C1": "Layout simple, pocas piezas, plano disponible",
            "C2": "Marcado perimetral, 2–3 subconjuntos, alguna característica especial",
            "C3": "Layout complejo, múltiples subconjuntos, geometría no-estándar + características especiales",
        },
        "C1": {"T_setup_min": 7,  "T_exec_min": 30, "n_ops": 1},
        "C2": {"T_setup_min": 15, "T_exec_min": 60, "n_ops": 1},
        "C3": {"T_setup_min": 25, "T_exec_min": 90, "n_ops": 1},
    },
    "corte_manual": {
        "drivers": ["G", "D"],
        "score_thresholds": {"C1": [2,3], "C2": [4,4], "C3": [5,99]},
        "descriptions": {
            "C1": "Pieza pequeña, ≤ 1.5mm, corte recto",
            "C2": "Pieza mediana o lámina 1.5–2mm",
            "C3": "Pieza grande o > 2mm, cortes curvos",
        },
        "C1": {"T_setup_min": 7,  "T_exec_min": 30, "n_ops": 1},
        "C2": {"T_setup_min": 12, "T_exec_min": 45, "n_ops": 2},
        "C3": {"T_setup_min": 18, "T_exec_min": 60, "n_ops": 2},
    },
    "laser": {
        "drivers": ["D", "X"],
        "score_thresholds": {"C1": [1,2], "C2": [3,4], "C3": [5,99]},
        "descriptions": {
            "C1": "≤ 1.5mm, DXF disponible, geometría estándar",
            "C2": "1.5–2mm o DXF requiere preparación, forma semi-especial",
            "C3": "Geometría compleja o > 2mm — cotizar externo, tiempo adicional",
        },
        "C1": {"T_setup_min": 7,  "T_exec_min": 10, "n_ops": 1},
        "C2": {"T_setup_min": 30, "T_exec_min": 35, "n_ops": 1},
        "C3": {"T_setup_min": 45, "T_exec_min": 0,  "n_ops": 0},
    },
    "plegado": {
        "drivers": ["G", "D", "C"],
        "score_thresholds": {"C1": [3,4], "C2": [5,6], "C3": [7,99]},
        "descriptions": {
            "C1": "1–2 dobleces, pieza pequeña, ≤ 1.5mm",
            "C2": "3–4 dobleces o pieza grande",
            "C3": "5+ dobleces, > 2mm o múltiples componentes",
        },
        "C1": {"T_setup_min": 10, "T_exec_min": 30, "n_ops": 1},
        "C2": {"T_setup_min": 17, "T_exec_min": 50, "n_ops": 2},
        "C3": {"T_setup_min": 25, "T_exec_min": 80, "n_ops": 3},
    },
    "cilindrado": {
        # D is primary discriminator (espesor drives rolling difficulty).
        # G (area proxy for diameter × height) adds secondary scale signal.
        # Threshold adjusted: score=2 → C1 (small thin), score=3 → C2 (medium),
        # score=4+ → C3 (large or thick). Matches Hernán: C3=estanques 4 personas.
        "drivers": ["D", "G"],
        "score_thresholds": {"C1": [2,2], "C2": [3,4], "C3": [5,99]},
        "descriptions": {
            "C1": "Espesor fino, diámetro pequeño — 1 persona, 1 pasada",
            "C2": "Espesor o diámetro moderado — 2 personas, 2–3 pasadas",
            "C3": "Espesor grueso o diámetro grande (estanques) — 4 personas",
        },
        "C1": {"T_setup_min": 5,  "T_exec_min": 20,  "n_ops": 1},
        "C2": {"T_setup_min": 15, "T_exec_min": 60,  "n_ops": 2},
        "C3": {"T_setup_min": 30, "T_exec_min": 180, "n_ops": 4},
    },
    "soldadura": {
        # C = component/union count. X = complexity flags (compartimientos, mecanismo).
        # When c_driver=null on profile, X flags alone drive the score (C silently skipped).
        # Thresholds calibrated for p-basurero-cil: multiples_compartimientos(+2) +
        # terminacion_multifinic(+2) = X=4 → C3; single flag (X≤2) → C2; none → C1.
        "drivers": ["C", "X"],
        "score_thresholds": {"C1": [0,1], "C2": [2,3], "C3": [4,99]},
        "descriptions": {
            "C1": "Pocas uniones, estructura simple, sin emplantillado",
            "C2": "Uniones visibles, reborde o esquinas, mecanismo integrado",
            "C3": "Emplantillado completo, TIG visible, múltiples compartimientos independientes",
        },
        "C1": {"T_setup_min": 5,  "T_exec_min": 40, "n_ops": 1},
        "C2": {"T_setup_min": 15, "T_exec_min": 60, "n_ops": 1},
        "C3": {"T_setup_min": 30, "T_exec_min": 90, "n_ops": 1},
    },
    "pulido": {
        "drivers": ["G", "X"],
        "score_thresholds": {"C1": [1,2], "C2": [3,4], "C3": [5,99]},
        "descriptions": {
            "C1": "Superficie plana accesible, 1 pasada, cepillado estándar",
            "C2": "Con varillas, rincones o geometría curva — cepillado fino",
            "C3": "3 pasadas completas, acabado espejo, geometría compleja",
        },
        "C1": {"T_setup_min": 0, "T_exec_min": 60,  "n_ops": 1},
        "C2": {"T_setup_min": 0, "T_exec_min": 90,  "n_ops": 2},
        "C3": {"T_setup_min": 0, "T_exec_min": 300, "n_ops": 2},
    },
    "qc": {
        "drivers": ["C", "X"],
        "score_thresholds": {"C1": [0,2], "C2": [3,4], "C3": [5,99]},
        "descriptions": {
            "C1": "Inspección visual, embalaje estándar",
            "C2": "Revisión dimensional, embalaje reforzado",
            "C3": "Control completo con registro fotográfico y embalaje especial",
        },
        "C1": {"T_setup_min": 5,  "T_exec_min": 15, "n_ops": 1},
        "C2": {"T_setup_min": 10, "T_exec_min": 30, "n_ops": 1},
        "C3": {"T_setup_min": 15, "T_exec_min": 60, "n_ops": 1},
    },
}

HH_RATES_DEFAULT = {
    "soldadura":      9000,
    "pulido":         7500,
    "cilindrado":     7500,
    "plegado":        7000,
    "corte_manual":   6500,
    "armado_trazado": 6500,
    "laser":          6500,
    "qc":             6000,
    "electrico":      8000,
    "refrigeracion":  8500,
}

# ─── Driver helpers ────────────────────────────────────────────────────────────

C_DRIVER_LABELS = {
    "num_componentes": "Componentes",
    "num_quemadores":  "Quemadores",
    "num_tazas":       "Tazas",
    "num_niveles":     "Niveles",
    "num_varillas":    "Varillas",
    "capacidad_litros":"Capacidad (L)",
}

def compute_G(L, W, H, rules):
    if not L or not W:
        return None, None
    H = H or 0
    area = 2 * (L + W) * H + L * W  # lateral surface + base footprint
    bp = rules["driver_thresholds"]["G"]["breakpoints_mm2"]
    if area < bp[0]:   return 1, area
    if area < bp[1]:   return 2, area
    return 3, area

def compute_D(e, rules):
    if not e:
        return None
    bp = rules["driver_thresholds"]["D"]["breakpoints_mm"]
    if e <= bp[0]:  return 1
    if e <= bp[1]:  return 2
    return 3

def compute_C(count, rules):
    """Compute C driver score (1/2/3) from component count."""
    if not count:
        return None
    bp = rules["driver_thresholds"].get("C", {}).get("breakpoints", [3, 7])
    if count <= bp[0]: return 1
    if count <= bp[1]: return 2
    return 3

def compute_points(G, D, C, x_flags_active, profile_rules):
    """Sum G + D + C + X points. Only add drivers declared for this profile."""
    primary = set(profile_rules.get("primary_drivers", []) +
                  profile_rules.get("secondary_drivers", []))
    pts = 0
    if G and "G" in primary: pts += G
    if D and "D" in primary: pts += D
    if C and "C" in primary: pts += C
    x_defs = profile_rules.get("x_flags", {})
    for flag, active in x_flags_active.items():
        if active and flag in x_defs:
            pts += x_defs[flag].get("points", 0)
    return pts

def assign_complexity(pts, thresholds):
    for comp in ["C1", "C2", "C3"]:
        if comp not in thresholds:
            continue
        t = thresholds[comp]
        if t["min_points"] <= pts <= t["max_points"]:
            return comp
    return "?"

def complexity_badge(comp):
    cls = {"C1": "badge-c1", "C2": "badge-c2", "C3": "badge-c3"}.get(comp, "badge-warn")
    return f'<span class="badge {cls}">{comp}</span>'

def fmt_clp(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"${int(v):,}".replace(",", ".")

# ─── Editable BOM table ────────────────────────────────────────────────────────

def bom_editor(label, default_rows, key):
    st.markdown(f'<div class="sec-label">{label}</div>', unsafe_allow_html=True)
    df = st.session_state.get(key)
    if df is None:
        df = pd.DataFrame(default_rows)
        st.session_state[key] = df

    edited = st.data_editor(
        df,
        key=f"editor_{key}",
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "total":     st.column_config.NumberColumn("Total $",     format="%.0f", step=1, min_value=0),
            "precio_kg": st.column_config.NumberColumn("$/kg o $/u",  format="%.0f", step=1),
            "kg_ml":     st.column_config.NumberColumn("kg o ML o u", format="%.4f", step=0.0001),
            "Cantidad":  st.column_config.NumberColumn("Cant. mat.",   format="%.3f", step=0.001),
            "Precio_u":  st.column_config.NumberColumn("Precio u.",   format="%.0f", step=1),
            "Total":     st.column_config.NumberColumn("Total $",      format="%.0f", step=1, min_value=0),
        },
        hide_index=True,
    )
    st.session_state[key] = edited
    return edited

# ─── Product input section ─────────────────────────────────────────────────────

def product_section(title, sku, comp_label, dims_defaults, mat_key, cons_key,
                    mat_defaults, cons_defaults, rules, profile_key, c_count_default=0):
    profile_rules = rules["profiles"].get(profile_key, {})
    x_defs        = profile_rules.get("x_flags", {})
    c_driver_field = profile_rules.get("c_driver")  # e.g. "num_cajones", None if not applicable

    st.markdown(
        f'<div class="sec-label">PRODUCTO</div>'
        f'<div style="display:flex;align-items:center;gap:0.7rem;margin-bottom:0.8rem;">'
        f'<span style="font-size:1.1rem;font-weight:700;color:#e6edf3;">{sku}</span>'
        f' {complexity_badge(comp_label)}</div>',
        unsafe_allow_html=True
    )

    # Dimensions + optional C count
    st.markdown('<div class="sec-label">DIMENSIONES</div>', unsafe_allow_html=True)
    if c_driver_field:
        d1, d2, d3, d4, d5 = st.columns(5)
    else:
        d1, d2, d3, d4 = st.columns(4)
        d5 = None

    L = d1.number_input("Largo mm",   value=dims_defaults[0], min_value=0,   key=f"L_{mat_key}")
    W = d2.number_input("Ancho mm",   value=dims_defaults[1], min_value=0,   key=f"W_{mat_key}")
    H = d3.number_input("Alto mm",    value=dims_defaults[2], min_value=0,   key=f"H_{mat_key}")
    e = d4.number_input("Espesor mm", value=dims_defaults[3], min_value=0.0, step=0.1, key=f"e_{mat_key}")

    c_count = 0
    if c_driver_field and d5:
        c_label = C_DRIVER_LABELS.get(c_driver_field, c_driver_field.replace("_", " ").title())
        c_count = d5.number_input(c_label, value=c_count_default, min_value=0, key=f"c_{mat_key}")

    G, area = compute_G(L, W, H, rules)
    D       = compute_D(e, rules)
    C       = compute_C(c_count, rules) if c_count > 0 else None

    # Driver scores shown inline
    g_label  = rules["driver_thresholds"]["G"]["scores"].get(str(G), {}).get("label", "—") if G else "—"
    d_label  = rules["driver_thresholds"]["D"]["scores"].get(str(D), {}).get("label", "—") if D else "—"
    c_label_val = rules["driver_thresholds"].get("C", {}).get("scores", {}).get(str(C), {}).get("label", "—") if C else "—"
    area_str = f"{area/1e6:.3f} m²" if area else "—"

    driver_html = (
        f'<div style="display:flex;gap:1.5rem;margin:0.5rem 0 0.8rem 0;flex-wrap:wrap;">'
        f'<div><span class="sec-label">G (sup. lateral)</span><br>'
        f'<b style="color:#79c0ff;">{G or "—"}</b> <span style="color:#768390;font-size:0.8rem;">{g_label} · {area_str}</span></div>'
        f'<div><span class="sec-label">D (espesor)</span><br>'
        f'<b style="color:#79c0ff;">{D or "—"}</b> <span style="color:#768390;font-size:0.8rem;">{d_label} · {e}mm</span></div>'
    )
    if c_driver_field:
        driver_html += (
            f'<div><span class="sec-label">C ({C_DRIVER_LABELS.get(c_driver_field,"conteo")})</span><br>'
            f'<b style="color:#79c0ff;">{C or "—"}</b> <span style="color:#768390;font-size:0.8rem;">{c_label_val} · {c_count} u</span></div>'
        )
    driver_html += '</div>'
    st.markdown(driver_html, unsafe_allow_html=True)

    # X flags checkboxes
    x_active = {}
    if x_defs:
        st.markdown('<div class="sec-label">CARACTERÍSTICAS (X)</div>', unsafe_allow_html=True)
        for flag, meta in x_defs.items():
            checked = st.checkbox(
                f"{meta['label']} (+{meta['points']} pts)",
                key=f"x_{mat_key}_{flag}",
                help=meta.get("description", "")
            )
            x_active[flag] = checked

    # BOM
    mat_df  = bom_editor("MATERIALES — BOM", mat_defaults,  mat_key)
    cons_df = bom_editor("CONSUMIBLES",      cons_defaults, cons_key)

    # Totals
    mat_total  = int(mat_df["total"].fillna(0).sum())  if "total"  in mat_df.columns else 0
    cons_total = int(cons_df["Total"].fillna(0).sum()) if "Total"  in cons_df.columns else 0

    st.markdown(
        f'<div style="display:flex;gap:1rem;margin-top:0.5rem;flex-wrap:wrap;">'
        f'<div class="cal-card" style="flex:1;min-width:120px;">'
        f'<div class="sec-label">TOTAL MATERIAL</div>'
        f'<div class="number-big">{fmt_clp(mat_total)}</div></div>'
        f'<div class="cal-card" style="flex:1;min-width:120px;">'
        f'<div class="sec-label">TOTAL CONSUMIBLES</div>'
        f'<div class="number-big">{fmt_clp(cons_total)}</div></div>'
        f'<div class="cal-card" style="flex:1;min-width:120px;">'
        f'<div class="sec-label">SUBTOTAL DIRECTO</div>'
        f'<div class="number-big">{fmt_clp(mat_total + cons_total)}</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    return {
        "G": G, "D": D, "C": C, "c_count": c_count,
        "area": area, "e": e, "L": L, "W": W, "H": H,
        "x_active": x_active,
        "mat_df": mat_df, "cons_df": cons_df,
        "mat_total": mat_total, "cons_total": cons_total,
        "total": mat_total + cons_total,
    }

# ─── Tab 2: Point system ───────────────────────────────────────────────────────

def render_point_system(products, rules, profile_key):
    st.markdown('<h3>Sistema de Puntos G/D/C/X → Complejidad</h3>', unsafe_allow_html=True)
    profile_rules = rules["profiles"].get(profile_key, {})
    x_defs        = profile_rules.get("x_flags", {})
    thresholds    = profile_rules.get("complexity_thresholds", {})

    # ── Universal driver breakpoints ──────────────────────────────────────────
    st.markdown(
        '<div class="cal-card">'
        '<div class="sec-label">DRIVERS UNIVERSALES — breakpoints valor → score (1/2/3)</div>'
        '<p style="color:#8b949e;font-size:0.82rem;margin-top:0.2rem;margin-bottom:0.6rem;">'
        'Cada driver convierte un valor físico en un score 1–3. '
        'Edita los breakpoints y guárdalos en PROCESS_RULES.json.</p>',
        unsafe_allow_html=True
    )

    g_bp = rules["driver_thresholds"]["G"]["breakpoints_mm2"]
    d_bp = rules["driver_thresholds"]["D"]["breakpoints_mm"]
    c_bp = rules["driver_thresholds"].get("C", {}).get("breakpoints", [3, 7])

    # Column headers
    hc = st.columns([1.2, 1.8, 1.8, 1.8, 3.5])
    for lbl, col in zip(["Driver", "Score 1", "Score 2", "Score 3", "Breakpoints"], hc):
        col.markdown(f'<div class="sec-label">{lbl}</div>', unsafe_allow_html=True)

    # G row
    gc = st.columns([1.2, 1.8, 1.8, 1.8, 3.5])
    gc[0].markdown('<b style="color:#79c0ff;">G</b> <span style="color:#768390;font-size:0.78rem;">sup. lateral</span>', unsafe_allow_html=True)
    gc[1].markdown('<span style="color:#3fb950;font-size:0.82rem;">< bp₁ mm²</span>', unsafe_allow_html=True)
    gc[2].markdown('<span style="color:#e3b341;font-size:0.82rem;">bp₁ – bp₂ mm²</span>', unsafe_allow_html=True)
    gc[3].markdown('<span style="color:#f85149;font-size:0.82rem;">≥ bp₂ mm²</span>', unsafe_allow_html=True)
    g_col1, g_col2 = gc[4].columns(2)
    new_g_bp0 = g_col1.number_input("G bp1 mm²", value=g_bp[0], min_value=1, step=50000,
                                     key="g_bp0", label_visibility="collapsed",
                                     help="Breakpoint 1 para G (mm²) — frontera score 1→2")
    new_g_bp1 = g_col2.number_input("G bp2 mm²", value=g_bp[1], min_value=1, step=100000,
                                     key="g_bp1", label_visibility="collapsed",
                                     help="Breakpoint 2 para G (mm²) — frontera score 2→3")

    # D row
    dc = st.columns([1.2, 1.8, 1.8, 1.8, 3.5])
    dc[0].markdown('<b style="color:#79c0ff;">D</b> <span style="color:#768390;font-size:0.78rem;">espesor</span>', unsafe_allow_html=True)
    dc[1].markdown('<span style="color:#3fb950;font-size:0.82rem;">≤ bp₁ mm</span>', unsafe_allow_html=True)
    dc[2].markdown('<span style="color:#e3b341;font-size:0.82rem;">bp₁ – bp₂ mm</span>', unsafe_allow_html=True)
    dc[3].markdown('<span style="color:#f85149;font-size:0.82rem;">> bp₂ mm</span>', unsafe_allow_html=True)
    d_col1, d_col2 = dc[4].columns(2)
    new_d_bp0 = d_col1.number_input("D bp1 mm", value=d_bp[0], min_value=0.1, step=0.1, format="%.1f",
                                     key="d_bp0", label_visibility="collapsed",
                                     help="Breakpoint 1 para D (mm) — frontera score 1→2")
    new_d_bp1 = d_col2.number_input("D bp2 mm", value=d_bp[1], min_value=0.1, step=0.1, format="%.1f",
                                     key="d_bp1", label_visibility="collapsed",
                                     help="Breakpoint 2 para D (mm) — frontera score 2→3")

    # C row
    cc = st.columns([1.2, 1.8, 1.8, 1.8, 3.5])
    cc[0].markdown('<b style="color:#79c0ff;">C</b> <span style="color:#768390;font-size:0.78rem;">componentes</span>', unsafe_allow_html=True)
    cc[1].markdown('<span style="color:#3fb950;font-size:0.82rem;">≤ bp₁ u</span>', unsafe_allow_html=True)
    cc[2].markdown('<span style="color:#e3b341;font-size:0.82rem;">bp₁+1 – bp₂ u</span>', unsafe_allow_html=True)
    cc[3].markdown('<span style="color:#f85149;font-size:0.82rem;">> bp₂ u</span>', unsafe_allow_html=True)
    c_col1, c_col2 = cc[4].columns(2)
    new_c_bp0 = c_col1.number_input("C bp1 u", value=c_bp[0], min_value=1, step=1,
                                     key="c_bp0", label_visibility="collapsed",
                                     help="Breakpoint 1 para C (conteo) — frontera score 1→2")
    new_c_bp1 = c_col2.number_input("C bp2 u", value=c_bp[1], min_value=1, step=1,
                                     key="c_bp1", label_visibility="collapsed",
                                     help="Breakpoint 2 para C (conteo) — frontera score 2→3")

    # X row — informational only (weights live in x_flags below)
    xc = st.columns([1.2, 1.8, 1.8, 1.8, 3.5])
    xc[0].markdown('<b style="color:#79c0ff;">X</b> <span style="color:#768390;font-size:0.78rem;">características</span>', unsafe_allow_html=True)
    xc[1].markdown('<span style="color:#3fb950;font-size:0.82rem;">0 flags activos</span>', unsafe_allow_html=True)
    xc[2].markdown('<span style="color:#e3b341;font-size:0.82rem;">1–2 pts sumados</span>', unsafe_allow_html=True)
    xc[3].markdown('<span style="color:#f85149;font-size:0.82rem;">3+ pts sumados</span>', unsafe_allow_html=True)
    xc[4].markdown(
        '<span style="color:#768390;font-size:0.78rem;">'
        'Suma de puntos de flags activos — pesos editables en sección X abajo</span>',
        unsafe_allow_html=True
    )

    st.markdown('<div style="margin-top:0.7rem;"></div>', unsafe_allow_html=True)
    if st.button("💾 Guardar breakpoints G/D/C en PROCESS_RULES.json"):
        rules["driver_thresholds"]["G"]["breakpoints_mm2"] = [new_g_bp0, new_g_bp1]
        rules["driver_thresholds"]["D"]["breakpoints_mm"]  = [new_d_bp0, new_d_bp1]
        if "C" not in rules["driver_thresholds"]:
            rules["driver_thresholds"]["C"] = {
                "description": "Conteo de componentes principales",
                "breakpoints": [new_c_bp0, new_c_bp1],
                "scores": {
                    "1": {"label": "Pocos",     "condition": f"count <= {new_c_bp0}"},
                    "2": {"label": "Moderado",  "condition": f"{new_c_bp0} < count <= {new_c_bp1}"},
                    "3": {"label": "Muchos",    "condition": f"count > {new_c_bp1}"},
                }
            }
        else:
            rules["driver_thresholds"]["C"]["breakpoints"] = [new_c_bp0, new_c_bp1]
        rules["meta"]["last_updated"] = str(date.today())
        save_rules(rules)
        st.success("✅ Breakpoints guardados. Los scores G/D/C se recalcularán con los nuevos umbrales.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Threshold editor ──────────────────────────────────────────────────────
    st.markdown(
        '<div class="cal-card">'
        '<div class="sec-label">UMBRALES DE COMPLEJIDAD (editable)</div>'
        '<p style="color:#8b949e;font-size:0.82rem;margin-top:0.3rem;">'
        'Ajusta los rangos de puntos para cada nivel. '
        'Los cambios se guardan en PROCESS_RULES.json.</p>',
        unsafe_allow_html=True
    )
    new_thresholds = {}
    for comp in ["C1", "C2", "C3"]:
        if comp not in thresholds:
            continue
        t = thresholds[comp]
        cols = st.columns([1, 2, 2, 3])
        cols[0].markdown(complexity_badge(comp), unsafe_allow_html=True)
        lo = cols[1].number_input(f"Min pts {comp}", value=t["min_points"], min_value=0, max_value=20, key=f"thresh_lo_{comp}")
        hi = cols[2].number_input(f"Max pts {comp}", value=t["max_points"], min_value=0, max_value=99, key=f"thresh_hi_{comp}")
        desc = cols[3].text_input(f"Descripción {comp}", value=t["description"], key=f"thresh_desc_{comp}")
        new_thresholds[comp] = {"min_points": lo, "max_points": hi, "description": desc}
    st.markdown('</div>', unsafe_allow_html=True)

    # ── X flag point editor ───────────────────────────────────────────────────
    if x_defs:
        st.markdown(
            '<div class="cal-card" style="margin-top:0.8rem;">'
            '<div class="sec-label">PESOS DE CARACTERÍSTICAS X</div>',
            unsafe_allow_html=True
        )
        new_x_defs = {}
        for flag, meta in x_defs.items():
            c1, c2, c3 = st.columns([3, 1, 3])
            c1.markdown(f'**{meta["label"]}**  \n<span style="color:#768390;font-size:0.78rem;">{meta.get("cost_impact_note","")}</span>', unsafe_allow_html=True)
            pts = c2.number_input(f"Pts {flag}", value=meta.get("points", 1), min_value=0, max_value=10, key=f"xpts_{flag}")
            c3.caption(f'Afecta proceso: `{meta.get("primary_process","—")}`')
            new_x_defs[flag] = {**meta, "points": pts}
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        new_x_defs = x_defs

    # ── Score cards for each product ──────────────────────────────────────────
    st.markdown('<div class="sec-label" style="margin:1rem 0 0.5rem 0;">PUNTUACIÓN POR PRODUCTO</div>', unsafe_allow_html=True)

    c_driver_field = profile_rules.get("c_driver")

    for pname, pdata in products.items():
        G = pdata.get("G")
        D = pdata.get("D")
        C = pdata.get("C")
        c_count = pdata.get("c_count", 0)
        x_active = pdata.get("x_active", {})
        pts = compute_points(G, D, C, x_active, {
            "primary_drivers": profile_rules.get("primary_drivers", []),
            "secondary_drivers": profile_rules.get("secondary_drivers", []),
            "x_flags": new_x_defs,
        })
        assigned = assign_complexity(pts, new_thresholds)
        expected_comp = pdata.get("expected_comp", "?")
        match = assigned == expected_comp

        status_html = (
            f'<span class="badge badge-ok">✅ Correcto</span>'
            if match else
            f'<span class="badge badge-err">❌ Desajuste — modelo dice {assigned}, producto es {expected_comp}</span>'
        )

        breakdown_parts = []
        if G and "G" in (profile_rules.get("primary_drivers",[]) + profile_rules.get("secondary_drivers",[])):
            breakdown_parts.append(f"G={G}")
        if D and "D" in (profile_rules.get("primary_drivers",[]) + profile_rules.get("secondary_drivers",[])):
            breakdown_parts.append(f"D={D}")
        if C and c_driver_field:
            breakdown_parts.append(f"C={C} ({c_count} {c_driver_field.replace('num_','')})")
        for flag, active in x_active.items():
            if active and flag in new_x_defs:
                breakdown_parts.append(f"X:{flag.replace('_',' ')}+{new_x_defs[flag]['points']}")

        st.markdown(
            f'<div class="cal-card" style="margin-bottom:0.6rem;">'
            f'<div style="display:flex;align-items:center;gap:0.8rem;flex-wrap:wrap;">'
            f'<b style="color:#e6edf3;">{pname}</b>'
            f' {complexity_badge(expected_comp)}'
            f'<span style="color:#768390;font-size:0.82rem;">→</span>'
            f'<span style="color:#79c0ff;font-weight:700;">{pts} puntos</span>'
            f' {complexity_badge(assigned)}'
            f'</div>'
            f'<div style="font-size:0.8rem;color:#768390;margin-top:0.3rem;">'
            f'{" + ".join(breakdown_parts) if breakdown_parts else "Sin datos dimensionales"}'
            f'</div>'
            f'<div style="margin-top:0.4rem;">{status_html}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # Save button
    st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)
    if st.button("💾 Guardar umbrales en PROCESS_RULES.json", type="primary"):
        rules["profiles"][profile_key]["complexity_thresholds"] = new_thresholds
        rules["profiles"][profile_key]["x_flags"] = new_x_defs
        rules["meta"]["last_updated"] = str(date.today())
        save_rules(rules)
        st.success("✅ PROCESS_RULES.json actualizado. Todos los agentes usarán los nuevos umbrales.")

# ─── Tab 3: Cost analysis ──────────────────────────────────────────────────────

def render_cost_analysis(products):
    st.markdown('<h3>Análisis de Costos C2 → C3</h3>', unsafe_allow_html=True)

    names   = list(products.keys())
    pdata   = list(products.values())

    if len(pdata) < 2:
        st.info("Ingresa datos para ambos productos para ver el análisis comparativo.")
        return

    c2 = next((p for p in pdata if p.get("expected_comp") == "C2"), pdata[0])
    c3 = next((p for p in pdata if p.get("expected_comp") == "C3"), pdata[1])
    c2_name = next((n for n, p in zip(names, pdata) if p.get("expected_comp") == "C2"), names[0])
    c3_name = next((n for n, p in zip(names, pdata) if p.get("expected_comp") == "C3"), names[1])

    mat_ratio  = c3["mat_total"]  / c2["mat_total"]  if c2["mat_total"]  > 0 else None
    cons_ratio = c3["cons_total"] / c2["cons_total"] if c2["cons_total"] > 0 else None
    tot_ratio  = c3["total"]      / c2["total"]       if c2["total"]      > 0 else None

    # ── Summary ratios ────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1.2rem;">',
        unsafe_allow_html=True
    )
    cards = [
        ("MATERIAL C3/C2", fmt_clp(c3["mat_total"]), fmt_clp(c2["mat_total"]),
         f"×{mat_ratio:.2f}" if mat_ratio else "—",
         "badge-warn" if mat_ratio and mat_ratio > 3 else "badge-ok"),
        ("CONSUMIBLES C3/C2", fmt_clp(c3["cons_total"]), fmt_clp(c2["cons_total"]),
         f"×{cons_ratio:.2f}" if cons_ratio else "—",
         "badge-err" if cons_ratio and cons_ratio > 5 else "badge-warn"),
        ("TOTAL DIRECTO C3/C2", fmt_clp(c3["total"]), fmt_clp(c2["total"]),
         f"×{tot_ratio:.2f}" if tot_ratio else "—",
         "badge-warn" if tot_ratio and tot_ratio > 3 else "badge-ok"),
    ]
    html = '<div style="display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1.2rem;">'
    for label, v3, v2, ratio, badge_cls in cards:
        html += (
            f'<div class="cal-card" style="flex:1;min-width:150px;">'
            f'<div class="sec-label">{label}</div>'
            f'<div class="number-big"><span class="badge {badge_cls}">{ratio}</span></div>'
            f'<div style="font-size:0.78rem;color:#768390;margin-top:0.4rem;">'
            f'C3: {v3}  ·  C2: {v2}</div></div>'
        )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    # ── Per-process consumables breakdown ─────────────────────────────────────
    st.markdown('<div class="sec-label" style="margin-bottom:0.5rem;">CONSUMIBLES POR PROCESO</div>', unsafe_allow_html=True)

    def agg_by_process(cons_df):
        if not isinstance(cons_df, pd.DataFrame) or cons_df.empty or "Proceso" not in cons_df.columns:
            return {}
        return cons_df.groupby("Proceso")["Total"].sum().to_dict()

    c2_proc = agg_by_process(c2["cons_df"])
    c3_proc = agg_by_process(c3["cons_df"])
    all_procs = sorted(set(list(c2_proc.keys()) + list(c3_proc.keys())))

    if all_procs:
        rows = []
        for proc in all_procs:
            v2 = c2_proc.get(proc, 0)
            v3 = c3_proc.get(proc, 0)
            ratio_p = v3 / v2 if v2 > 0 else None
            rows.append({
                "Proceso": proc,
                f"C2 {c2_name}": v2,
                f"C3 {c3_name}": v3,
                "Ratio C3/C2": f"×{ratio_p:.1f}" if ratio_p else "C3 solo",
                "Delta $": v3 - v2,
            })
        df_proc = pd.DataFrame(rows)
        st.dataframe(df_proc, use_container_width=True, hide_index=True)

    # ── Material breakdown comparison ─────────────────────────────────────────
    st.markdown('<div class="sec-label" style="margin:1rem 0 0.5rem 0;">MATERIALES POR SUBCONJUNTO</div>', unsafe_allow_html=True)

    if isinstance(c2["mat_df"], pd.DataFrame) and isinstance(c3["mat_df"], pd.DataFrame) and not c2["mat_df"].empty and not c3["mat_df"].empty:
        mat_compare = pd.DataFrame({
            "Subconjunto C2": c2["mat_df"]["Subconjunto"].tolist() if "Subconjunto" in c2["mat_df"].columns else [],
            "Total C2 $":     c2["mat_df"]["total"].tolist()       if "total"       in c2["mat_df"].columns else [],
        })
        st.markdown(f"**{c2_name} (C2) — {len(c2['mat_df'])} líneas  ·  Total: {fmt_clp(c2['mat_total'])}**")
        st.dataframe(c2["mat_df"][["Subconjunto","Material","kg_ml","total"]] if "Subconjunto" in c2["mat_df"].columns else c2["mat_df"],
                     use_container_width=True, hide_index=True)
        st.markdown(f"**{c3_name} (C3) — {len(c3['mat_df'])} líneas  ·  Total: {fmt_clp(c3['mat_total'])}**")
        st.dataframe(c3["mat_df"][["Subconjunto","Material","kg_ml","total"]] if "Subconjunto" in c3["mat_df"].columns else c3["mat_df"],
                     use_container_width=True, hide_index=True)

    # ── Driver-cost linearity test ────────────────────────────────────────────
    st.markdown('<div class="sec-label" style="margin:1rem 0 0.5rem 0;">TEST DE LINEALIDAD</div>', unsafe_allow_html=True)

    g2, g3   = c2.get("G"), c3.get("G")
    area2, area3 = c2.get("area"), c3.get("area")

    if area2 and area3 and c2["mat_total"] > 0:
        area_ratio = area3 / area2
        mat_ratio_actual = c3["mat_total"] / c2["mat_total"]
        linearity_pct = (mat_ratio_actual / area_ratio - 1) * 100

        verdict = "✅ Lineal" if abs(linearity_pct) < 20 else (
            "⚠️ Sobre-escala" if linearity_pct > 0 else "⚠️ Sub-escala"
        )
        badge_cls = "badge-ok" if abs(linearity_pct) < 20 else "badge-warn"

        st.markdown(
            f'<div class="cal-card">'
            f'<div style="font-size:0.88rem;">Área C2: <b>{area2/1e6:.3f} m²</b>  →  Área C3: <b>{area3/1e6:.3f} m²</b>'
            f'  ·  Ratio área: <b style="color:#79c0ff;">×{area_ratio:.2f}</b></div>'
            f'<div style="font-size:0.88rem;margin-top:0.3rem;">Ratio material real: <b style="color:#79c0ff;">×{mat_ratio_actual:.2f}</b>'
            f'  ·  Desviación de linealidad: <b>{linearity_pct:+.1f}%</b>'
            f'  <span class="badge {badge_cls}">{verdict}</span></div>'
            f'<div style="font-size:0.78rem;color:#768390;margin-top:0.4rem;">'
            f'Si la escala fuera perfectamente lineal con área, esperaríamos ×{area_ratio:.2f} en material. '
            f'{"El costo crece más rápido que el área — revisar si hay costos fijos dominantes." if linearity_pct > 20 else ""}'
            f'{"El costo crece más lento que el área — hay economías de escala." if linearity_pct < -20 else ""}'
            f'</div></div>',
            unsafe_allow_html=True
        )
    else:
        st.info("Ingresa dimensiones y costos para ambos productos para ver el test de linealidad.")

# ─── Process complexity helpers ───────────────────────────────────────────────

def get_effective_templates(rules=None):
    """
    Python constant PROCESS_TEMPLATES is the base.
    If rules contains a 'process_templates' key (saved from the Templates editor tab),
    those values override the constant — per process, per field.
    """
    if not rules:
        return PROCESS_TEMPLATES
    saved = rules.get("process_templates", {})
    if not saved:
        return PROCESS_TEMPLATES
    result = {}
    for proc, base in PROCESS_TEMPLATES.items():
        if proc not in saved:
            result[proc] = base
            continue
        s = saved[proc]
        merged = dict(base)
        if "score_thresholds" in s: merged["score_thresholds"] = s["score_thresholds"]
        if "descriptions"     in s: merged["descriptions"]     = s["descriptions"]
        for lvl in ["C1", "C2", "C3"]:
            if lvl in s: merged[lvl] = s[lvl]
        result[proc] = merged
    return result


def compute_process_complexity(proc, G, D, C, x_active, profile_rules, rules=None, templates=None):
    """
    Compute the complexity level of a SPECIFIC PROCESS from universal driver scores.
    Uses effective templates (JSON-saved overrides > Python constant PROCESS_TEMPLATES).

    Returns: (level, score, missing_drivers, used_dict)
      level           — "C1"/"C2"/"C3" or None if no template defined for this process
      score           — integer point sum (always an int, never None)
      missing_drivers — driver letters declared but unavailable (data gap)
      used_dict       — {driver: value} for drivers that contributed
    """
    if templates is None:
        templates = get_effective_templates(rules)
    tmpl = templates.get(proc)
    if not tmpl:
        return None, 0, [], {}

    proc_drivers = tmpl.get("drivers", [])
    thresholds   = tmpl.get("score_thresholds", {})
    x_defs       = profile_rules.get("x_flags", {}) if profile_rules else {}

    if not proc_drivers or not thresholds:
        return None, 0, [], {}

    score   = 0
    used    = {}
    missing = []

    for d in proc_drivers:
        if d == "G":
            if G is not None:
                score += G; used["G"] = G
            else:
                missing.append("G")
        elif d == "D":
            if D is not None:
                score += D; used["D"] = D
            else:
                missing.append("D")
        elif d == "C":
            if C is not None:
                score += C; used["C"] = C
            elif profile_rules and profile_rules.get("c_driver"):
                # C is declared for this profile but the value hasn't been entered yet
                missing.append("C")
            # else: profile has c_driver=null → C not applicable, skip silently
        elif d == "X":
            x_pts = sum(
                x_defs.get(flag, {}).get("points", 0)
                for flag, active in (x_active or {}).items() if active
            )
            score += x_pts
            used["X"] = x_pts  # always record, even if 0

    # Map score to level — find first matching range
    level = None
    for comp in ["C1", "C2", "C3"]:
        if comp not in thresholds:
            continue
        lo, hi = thresholds[comp]
        if lo <= score <= hi:
            level = comp
            break

    # If score is below all thresholds (e.g. all drivers missing),
    # don't assign a level — caller shows a "sin datos" warning.
    return level, score, missing, used


# ─── Tab 4: Process HH breakdown ──────────────────────────────────────────────

def render_process_breakdown(products, rules, profile_key):
    """
    For each active process in the profile, shows per-product labor cost:
      (T_setup + T_exec_base × factor_escala) / 60 × $/HH × n_ops

    Times are pre-filled from process_templates but editable so the user can
    enter real measured times and validate the template estimates.
    """
    st.markdown('<h3>Desglose de HH por Proceso</h3>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#8b949e;font-size:0.85rem;">'
        'Para cada proceso activo del perfil, compara el costo de mano de obra estimado '
        'por el modelo vs lo que tarda realmente. Edita los tiempos para validar los templates. '
        'Los tiempos son de referencia (factor_escala = 1.0 = anchor).</p>',
        unsafe_allow_html=True
    )

    profile_rules    = rules["profiles"].get(profile_key, {})
    active_processes = profile_rules.get("processes", [])
    templates        = get_effective_templates(rules)   # JSON overrides > Python constant
    hh_rates         = {**HH_RATES_DEFAULT, **{   # JSON rates override defaults if present
        k: v for k, v in rules.get("hh_rates_clp_per_hour", {}).items()
        if not k.startswith("_")
    }}

    if not active_processes:
        st.info("No hay procesos definidos para este perfil en PROCESS_RULES.json.")
        return

    product_list = [(n, p) for n, p in products.items() if p.get("mat_total", 0) >= 0]
    if not product_list:
        st.info("Ingresa datos en el tab 'Ingreso de Costos' primero.")
        return

    # ── HH rate editor ────────────────────────────────────────────────────────
    # Initialize rates from rules (these get overridden inside the expander)
    new_rates = {proc: hh_rates.get(proc, 6500) for proc in active_processes}

    with st.expander("⚙️ Tarifas HH por proceso (editar si cambió el sueldo)", expanded=False):
        st.markdown(
            '<div style="font-size:0.8rem;color:#768390;margin-bottom:0.5rem;">'
            'Fuente: estimado — validar con <code>/accounting setup</code>.</div>',
            unsafe_allow_html=True
        )
        rate_cols = st.columns(4)
        for i, proc in enumerate(active_processes):
            new_rates[proc] = rate_cols[i % 4].number_input(
                f"$/hr {proc}", value=new_rates[proc], step=500, min_value=0,
                key=f"hh_rate_{proc}"
            )
        if st.button("💾 Guardar tarifas en PROCESS_RULES.json"):
            for proc, rate in new_rates.items():
                rules["hh_rates_clp_per_hour"][proc] = rate
            rules["meta"]["last_updated"] = str(date.today())
            save_rules(rules)
            st.success("✅ Tarifas HH actualizadas.")

    st.markdown('<div style="height:0.8rem;"></div>', unsafe_allow_html=True)

    # ── Complexity summary across processes (before time inputs) ─────────────
    st.markdown(
        '<div class="sec-label" style="margin-bottom:0.5rem;">'
        'COMPLEJIDAD POR PROCESO — calculada desde los drivers de cada producto</div>',
        unsafe_allow_html=True
    )

    # Build summary rows: one row per process, columns = products
    summary_rows = []
    for proc in active_processes:
        tmpl = templates.get(proc, {})
        proc_drivers   = tmpl.get("drivers", [])
        descriptions   = tmpl.get("descriptions", {})
        score_ranges   = tmpl.get("score_thresholds", {})

        row = {"Proceso": proc, "Drivers": " + ".join(proc_drivers) if proc_drivers else "—"}

        for pname, pdata in product_list:
            level, score, _, used = compute_process_complexity(
                proc,
                pdata.get("G"), pdata.get("D"), pdata.get("C"),
                pdata.get("x_active", {}),
                profile_rules, rules
            )
            comp_badge_txt  = level or "?"
            score_str       = str(score) if score is not None else "—"
            desc            = descriptions.get(level, "") if level else "sin datos"
            used_str        = " + ".join(f"{k}={v}" for k, v in used.items()) if used else "—"
            row[f"  {pname}"] = f"{comp_badge_txt} ({score_str} pts) — {desc}" if level else f"? — {used_str}"

        summary_rows.append(row)

    # Show as styled HTML table (badges per cell)
    if product_list:
        pnames = [n for n, _ in product_list]
        # Header
        col_widths = [2, 1.2] + [3] * len(pnames)
        head_cols  = st.columns(col_widths)
        head_cols[0].markdown('<div class="sec-label">Proceso</div>', unsafe_allow_html=True)
        head_cols[1].markdown('<div class="sec-label">Drivers</div>', unsafe_allow_html=True)
        for i, pn in enumerate(pnames):
            pcomp = next((p.get("expected_comp","?") for n,p in product_list if n == pn), "?")
            head_cols[2+i].markdown(
                f'<div class="sec-label">{pn} {complexity_badge(pcomp)}</div>',
                unsafe_allow_html=True
            )
        st.markdown('<hr style="margin:0.2rem 0 0.4rem 0;">', unsafe_allow_html=True)

        for proc in active_processes:
            tmpl           = templates.get(proc, {})
            proc_drivers   = tmpl.get("drivers", [])
            descriptions   = tmpl.get("descriptions", {})
            score_ranges   = tmpl.get("score_thresholds", {})

            row_cols = st.columns(col_widths)
            row_cols[0].markdown(
                f'<div style="font-size:0.88rem;font-weight:700;color:#cdd9e5;padding-top:0.35rem;">{proc}</div>',
                unsafe_allow_html=True
            )
            # Drivers + score ranges tooltip
            ranges_str = "  ".join(
                f"{k}:{lo}–{hi}" for k,(lo,hi) in score_ranges.items()
            ) if score_ranges else "—"
            row_cols[1].markdown(
                f'<div style="font-size:0.8rem;color:#79c0ff;padding-top:0.35rem;" '
                f'title="Rangos de score: {ranges_str}">'
                f'{" + ".join(proc_drivers) if proc_drivers else "—"}</div>',
                unsafe_allow_html=True
            )

            for i, (pname, pdata) in enumerate(product_list):
                level, score, missing, used = compute_process_complexity(
                    proc,
                    pdata.get("G"), pdata.get("D"), pdata.get("C"),
                    pdata.get("x_active", {}),
                    profile_rules, rules
                )
                desc     = descriptions.get(level, "") if level else ""
                # Show which drivers contributed (skip X=0 to reduce noise)
                used_parts = [f"{k}={v}" for k, v in used.items() if not (k == "X" and v == 0)]
                used_str   = " + ".join(used_parts) if used_parts else "—"
                # Show missing drivers as a warning
                missing_html = (
                    f'<span style="color:#e3b341;font-size:0.7rem;"> ⚠️ falta {", ".join(missing)}</span>'
                    if missing else ""
                )
                # "sin datos" when no dims entered at all
                no_data = not pdata.get("G") and not pdata.get("D")
                if no_data:
                    cell_html = '<span style="color:#484f58;font-size:0.78rem;">ingresa dimensiones en Tab 1</span>'
                else:
                    cell_html = (
                        f'{complexity_badge(level) if level else "<span style=\"color:#768390\">?</span>"}'
                        f'<span style="color:#768390;font-size:0.75rem;margin-left:0.4rem;">'
                        f'{score} pts · {used_str}</span>'
                        f'{missing_html}'
                        f'<div style="font-size:0.74rem;color:#8b949e;margin-top:0.1rem;">{desc}</div>'
                    )
                row_cols[2+i].markdown(
                    f'<div style="padding-top:0.2rem;">{cell_html}</div>',
                    unsafe_allow_html=True
                )

        st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

    # ── Column headers for time inputs ────────────────────────────────────────
    st.markdown(
        '<div class="sec-label" style="margin-bottom:0.5rem;">'
        'TIEMPOS Y COSTO LABOR — edita para comparar con tiempos reales del taller</div>',
        unsafe_allow_html=True
    )
    hc1, hc2, hc3, hc4, hc5, hc6 = st.columns([2, 1, 1.2, 1.2, 1, 1.5])
    hc1.markdown('<div class="sec-label">Proceso</div>', unsafe_allow_html=True)
    hc2.markdown(
        '<div class="sec-label">Nivel proceso</div>',
        unsafe_allow_html=True
    )
    hc3.markdown(
        '<div class="sec-label" title="Preparación: plantilla, posicionado, ajuste. NO escala con tamaño.">T setup (min) ⓘ</div>',
        unsafe_allow_html=True
    )
    hc4.markdown(
        '<div class="sec-label" title="Ejecución base (anchor, factor_escala=1.0). Escala con dimensiones.">T ejecución (min) ⓘ</div>',
        unsafe_allow_html=True
    )
    hc5.markdown(
        '<div class="sec-label" title="Operadores simultáneos para este proceso en este nivel.">Ops ⓘ</div>',
        unsafe_allow_html=True
    )
    hc6.markdown(
        '<div class="sec-label" style="text-align:right;" title="= (T_setup + T_exec) ÷ 60 × $/hr × n_ops">Costo labor ⓘ</div>',
        unsafe_allow_html=True
    )
    st.markdown('<hr style="margin:0.2rem 0 0.5rem 0;">', unsafe_allow_html=True)

    # ── Per-product breakdown table ───────────────────────────────────────────
    for pname, pdata in product_list:
        prod_comp = pdata.get("expected_comp", "?")

        st.markdown(
            f'<div class="cal-card" style="margin-bottom:0.4rem;padding:0.6rem 0.9rem;">'
            f'<div style="display:flex;align-items:center;gap:0.7rem;">'
            f'<b style="color:#e6edf3;">{pname}</b> {complexity_badge(prod_comp)}'
            f'<span style="color:#768390;font-size:0.78rem;">— nivel del producto (global) vs nivel por proceso (abajo)</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )

        total_labor = 0

        for proc in active_processes:
            # Process-specific complexity
            proc_level, proc_score, proc_missing, _ = compute_process_complexity(
                proc,
                pdata.get("G"), pdata.get("D"), pdata.get("C"),
                pdata.get("x_active", {}),
                profile_rules, rules
            )
            # Use process-level complexity for template lookup; fall back to product level
            lookup_level = proc_level or prod_comp
            tmpl_level   = templates.get(proc, {}).get(lookup_level, {})
            t_setup_ref  = tmpl_level.get("T_setup_min", 0)
            t_exec_ref   = tmpl_level.get("T_exec_min", 0)
            n_ops_ref    = tmpl_level.get("n_ops", 1)
            hh_rate      = new_rates.get(proc, 6500)

            tc1, tc2, tc3, tc4, tc5, tc6 = st.columns([2, 1, 1.2, 1.2, 1, 1.5])
            tc1.markdown(
                f'<div style="padding-top:0.4rem;font-size:0.88rem;color:#cdd9e5;"><b>{proc}</b></div>',
                unsafe_allow_html=True
            )
            missing_note = (
                f'<div style="font-size:0.68rem;color:#e3b341;">⚠️ falta {", ".join(proc_missing)}</div>'
                if proc_missing else ""
            )
            tc2.markdown(
                f'<div style="padding-top:0.3rem;">'
                f'{complexity_badge(proc_level) if proc_level else "<span style=\"color:#768390;font-size:0.78rem;\">?</span>"}'
                f'{missing_note}'
                f'</div>',
                unsafe_allow_html=True
            )
            t_setup = tc3.number_input(
                "Setup", value=t_setup_ref, min_value=0,
                key=f"ts_{pname}_{proc}", label_visibility="collapsed",
                help=f"Modelo: {t_setup_ref} min (nivel {lookup_level})"
            )
            t_exec = tc4.number_input(
                "Exec", value=t_exec_ref, min_value=0,
                key=f"te_{pname}_{proc}", label_visibility="collapsed",
                help=f"Modelo: {t_exec_ref} min (nivel {lookup_level})"
            )
            n_ops = tc5.number_input(
                "Ops", value=n_ops_ref, min_value=0, max_value=10,
                key=f"no_{pname}_{proc}", label_visibility="collapsed",
                help=f"Modelo: {n_ops_ref} operadores"
            )

            labor = (t_setup + t_exec) / 60 * hh_rate * n_ops if n_ops > 0 else 0
            total_labor += labor

            delta_setup = t_setup - t_setup_ref
            delta_exec  = t_exec  - t_exec_ref
            delta_html  = (
                '<span style="color:#3fb950;font-size:0.72rem;">= modelo</span>'
                if delta_setup == 0 and delta_exec == 0 else
                f'<span style="color:#e3b341;font-size:0.72rem;">Δ {delta_setup:+d}/{delta_exec:+d} min</span>'
            )
            tc6.markdown(
                f'<div style="padding-top:0.3rem;text-align:right;">'
                f'<b style="color:#3fb950;">{fmt_clp(labor)}</b>'
                f'<div style="font-size:0.7rem;color:#768390;">({t_setup+t_exec}m·{n_ops}op·${hh_rate//1000}k/h)</div>'
                f'<div>{delta_html}</div></div>',
                unsafe_allow_html=True
            )

        pct = f"{(total_labor / pdata['total'] * 100):.0f}%" if pdata["total"] > 0 else "—"
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;gap:2rem;'
            f'margin:0.3rem 0 1.2rem 0;padding:0.45rem 0.8rem;'
            f'background:#0d2137;border-radius:8px;border:1px solid #1f6feb;">'
            f'<div><span class="sec-label">TOTAL HH LABOR</span><br>'
            f'<b style="font-size:1.2rem;color:#79c0ff;">{fmt_clp(total_labor)}</b></div>'
            f'<div><span class="sec-label">% sobre costo directo</span><br>'
            f'<b style="font-size:1.2rem;color:#79c0ff;">{pct}</b>'
            f'<span style="color:#768390;font-size:0.75rem;"> de {fmt_clp(pdata["total"])}</span></div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Side-by-side comparison ───────────────────────────────────────────────
    if len(product_list) == 2:
        st.markdown('<div class="sec-label" style="margin:0.5rem 0;">COMPARACIÓN ENTRE PRODUCTOS</div>', unsafe_allow_html=True)

        pn1, pd1 = product_list[0]
        pn2, pd2 = product_list[1]
        rows_compare = []

        for proc in active_processes:
            hh_rate = new_rates.get(proc, 6500)

            l1, s1, _, _ = compute_process_complexity(proc, pd1.get("G"), pd1.get("D"), pd1.get("C"), pd1.get("x_active",{}), profile_rules, rules)
            l2, s2, _, _ = compute_process_complexity(proc, pd2.get("G"), pd2.get("D"), pd2.get("C"), pd2.get("x_active",{}), profile_rules, rules)

            ts1 = st.session_state.get(f"ts_{pn1}_{proc}", templates.get(proc,{}).get(l1 or pd1.get("expected_comp","C1"),{}).get("T_setup_min",0))
            te1 = st.session_state.get(f"te_{pn1}_{proc}", templates.get(proc,{}).get(l1 or pd1.get("expected_comp","C1"),{}).get("T_exec_min",0))
            no1 = st.session_state.get(f"no_{pn1}_{proc}", templates.get(proc,{}).get(l1 or pd1.get("expected_comp","C1"),{}).get("n_ops",1))
            ts2 = st.session_state.get(f"ts_{pn2}_{proc}", templates.get(proc,{}).get(l2 or pd2.get("expected_comp","C2"),{}).get("T_setup_min",0))
            te2 = st.session_state.get(f"te_{pn2}_{proc}", templates.get(proc,{}).get(l2 or pd2.get("expected_comp","C2"),{}).get("T_exec_min",0))
            no2 = st.session_state.get(f"no_{pn2}_{proc}", templates.get(proc,{}).get(l2 or pd2.get("expected_comp","C2"),{}).get("n_ops",1))

            lab1 = (ts1+te1)/60*hh_rate*no1
            lab2 = (ts2+te2)/60*hh_rate*no2

            rows_compare.append({
                "Proceso":            proc,
                f"{pn1} nivel":       l1 or "?",
                f"{pn1} min":         ts1+te1,
                f"{pn1} labor $":     int(lab1),
                f"{pn2} nivel":       l2 or "?",
                f"{pn2} min":         ts2+te2,
                f"{pn2} labor $":     int(lab2),
                "Ratio labor":        f"×{lab2/lab1:.2f}" if lab1 > 0 else "—",
                "Δ nivel":            "—" if l1 == l2 else f"{l1}→{l2}",
            })

        st.dataframe(pd.DataFrame(rows_compare), use_container_width=True, hide_index=True)


# ─── Tab 5: Extrapolation ──────────────────────────────────────────────────────

def render_extrapolation(anchor_product, anchor_name, anchor_comp, rules, profile_key):
    st.markdown('<h3>Test de Extrapolación</h3>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#8b949e;font-size:0.85rem;">Ingresa un producto nuevo para ver si el costo extrapolado desde el ancla es coherente.</p>',
        unsafe_allow_html=True
    )

    if anchor_product["mat_total"] == 0:
        st.warning(f"Ingresa el BOM de {anchor_name} ({anchor_comp}) para activar la extrapolación.")
        return

    profile_rules = rules["profiles"].get(profile_key, {})
    x_defs = profile_rules.get("x_flags", {})

    st.markdown(
        f'<div class="cal-card-blue">'
        f'<div class="sec-label">ANCLA DE EXTRAPOLACIÓN</div>'
        f'<div style="display:flex;align-items:center;gap:0.7rem;margin-top:0.3rem;">'
        f'<b style="color:#e6edf3;">{anchor_name}</b>'
        f' {complexity_badge(anchor_comp)}</div>'
        f'<div style="font-size:0.8rem;color:#8b949e;margin-top:0.3rem;">'
        f'L={anchor_product["L"]}mm · W={anchor_product["W"]}mm · e={anchor_product["e"]}mm · '
        f'G={anchor_product["G"]} · D={anchor_product["D"]}'
        f'</div>'
        f'<div style="font-size:0.8rem;color:#8b949e;">'
        f'Material: {fmt_clp(anchor_product["mat_total"])}  ·  Consumibles: {fmt_clp(anchor_product["cons_total"])}'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # New product input
    st.markdown('<div class="sec-label" style="margin-top:1rem;">PRODUCTO A EXTRAPOLAR</div>', unsafe_allow_html=True)
    ec1, ec2, ec3, ec4 = st.columns(4)
    nL = ec1.number_input("Largo mm",    value=anchor_product["L"],  key="ext_L", min_value=0)
    nW = ec2.number_input("Ancho mm",    value=anchor_product["W"],  key="ext_W", min_value=0)
    nH = ec3.number_input("Alto mm",     value=anchor_product["H"],  key="ext_H", min_value=0)
    ne = ec4.number_input("Espesor mm",  value=anchor_product["e"],  key="ext_e", min_value=0.0, step=0.1)

    # X flags for new product
    new_x_active = {}
    if x_defs:
        st.markdown('<div class="sec-label">CARACTERÍSTICAS X (nuevo producto)</div>', unsafe_allow_html=True)
        for flag, meta in x_defs.items():
            checked = st.checkbox(meta["label"], key=f"ext_x_{flag}", help=meta.get("description",""))
            new_x_active[flag] = checked

    nG, nArea = compute_G(nL, nW, nH, rules)
    nD        = compute_D(ne, rules)

    if not anchor_product["area"] or not nArea:
        st.warning("Necesitas dimensiones L×W para ambos productos.")
        return

    # Scale factors
    area_scale  = nArea / anchor_product["area"]
    espesor_scale = ne / anchor_product["e"] if anchor_product["e"] > 0 else 1.0
    height_scale  = nH / anchor_product["H"] if anchor_product["H"] > 0 else 1.0

    # Material: scales with area (primary driver for rectangular products)
    mat_est = anchor_product["mat_total"] * area_scale

    # Consumables: base consumables scale with area, but X flags add fixed costs
    # Base (without Multifinic) scales with area
    cons_df = anchor_product["cons_df"]
    cons_base = 0
    cons_x_fixed = 0
    if "Proceso" in cons_df.columns and "Total" in cons_df.columns:
        # X-specific consumables don't scale
        x_process_flags = {meta["primary_process"] for meta in x_defs.values()}
        for flag, meta in x_defs.items():
            if anchor_product["x_active"].get(flag):
                proc = meta.get("primary_process", "")
                x_rows = cons_df[cons_df["Proceso"] == proc]["Total"].sum()
                cons_x_fixed += x_rows
        cons_base = anchor_product["cons_total"] - cons_x_fixed

    # Add X costs for new product
    new_x_costs = 0
    if x_defs:
        for flag, active in new_x_active.items():
            if active and flag in x_defs:
                meta = x_defs[flag]
                # Find the cost of this X in anchor consumables
                proc = meta.get("primary_process", "")
                x_cost_anchor = cons_df[cons_df["Proceso"] == proc]["Total"].sum() if "Proceso" in cons_df.columns else 0
                new_x_costs += x_cost_anchor if x_cost_anchor > 0 else 0

    cons_est = cons_base * area_scale + new_x_costs
    total_est = mat_est + cons_est

    # Point score
    nC = compute_C(st.session_state.get(f"c_ext", 0), rules)
    pts_new    = compute_points(nG, nD, nC, new_x_active, profile_rules)
    comp_new   = assign_complexity(pts_new, profile_rules.get("complexity_thresholds", {}))

    # Results
    st.markdown(
        f'<div class="cal-card-green" style="margin-top:1rem;">'
        f'<div class="sec-label">RESULTADO DE EXTRAPOLACIÓN</div>'
        f'<div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:0.5rem;">'
        f'<div><div class="sec-label">Complejidad asignada</div>'
        f'<div style="margin-top:4px;">{complexity_badge(comp_new)} '
        f'<span style="color:#768390;font-size:0.8rem;margin-left:0.4rem;">{pts_new} pts</span></div></div>'
        f'<div><div class="sec-label">Factor escala (área)</div>'
        f'<div style="font-size:1.3rem;font-weight:700;color:#3fb950;">×{area_scale:.3f}</div></div>'
        f'</div>'
        f'<div style="display:flex;gap:1rem;flex-wrap:wrap;margin-top:0.8rem;">'
        f'<div class="cal-card" style="flex:1;min-width:100px;">'
        f'<div class="sec-label">MATERIAL EST.</div>'
        f'<div class="number-big">{fmt_clp(mat_est)}</div>'
        f'<div class="number-sub">= ancla × {area_scale:.3f}</div></div>'
        f'<div class="cal-card" style="flex:1;min-width:100px;">'
        f'<div class="sec-label">CONSUMIBLES EST.</div>'
        f'<div class="number-big">{fmt_clp(cons_est)}</div>'
        f'<div class="number-sub">base×escala + X fijos</div></div>'
        f'<div class="cal-card" style="flex:1;min-width:100px;">'
        f'<div class="sec-label">TOTAL DIRECTO EST.</div>'
        f'<div class="number-big">{fmt_clp(total_est)}</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Driver comparison card ────────────────────────────────────────────────
    # Compute anchor raw physical values for display
    anc_area  = anchor_product.get("area", 0) or 0
    anc_e     = anchor_product.get("e", 0) or 0
    anc_x_pts = sum(
        x_defs.get(f, {}).get("points", 0)
        for f, a in anchor_product.get("x_active", {}).items() if a
    )
    new_x_pts = sum(
        x_defs.get(f, {}).get("points", 0)
        for f, a in new_x_active.items() if a
    )

    def driver_delta(anc_val, new_val, anc_score, new_score, unit):
        """Render anchor→new with delta color."""
        changed = anc_score != new_score
        arrow   = "↑" if new_score > anc_score else ("↓" if new_score < anc_score else "→")
        color   = "#f85149" if new_score > anc_score else ("#79c0ff" if new_score < anc_score else "#3fb950")
        score_html = (
            f'<span style="color:{color};font-weight:700;">'
            f'{complexity_badge(f"C{anc_score}")} {arrow} {complexity_badge(f"C{new_score}")}'
            f'</span>' if changed else
            f'{complexity_badge(f"C{anc_score}")} <span style="color:#3fb950;font-size:0.78rem;">= sin cambio</span>'
        )
        return (
            f'<div><div class="sec-label">score</div>{score_html}</div>'
            f'<div style="font-size:0.78rem;color:#768390;margin-top:0.3rem;">'
            f'ancla: {anc_val}  →  nuevo: {new_val} {unit}</div>'
        )

    g_label_a = rules["driver_thresholds"]["G"]["scores"].get(str(anchor_product.get("G")), {}).get("label", "—")
    g_label_n = rules["driver_thresholds"]["G"]["scores"].get(str(nG), {}).get("label", "—")
    d_label_a = rules["driver_thresholds"]["D"]["scores"].get(str(anchor_product.get("D")), {}).get("label", "—")
    d_label_n = rules["driver_thresholds"]["D"]["scores"].get(str(nD), {}).get("label", "—")

    st.markdown(
        '<div class="cal-card" style="margin-top:0.8rem;">'
        '<div class="sec-label" style="margin-bottom:0.5rem;">DRIVERS UNIVERSALES — ancla vs nuevo</div>'
        '<div style="display:flex;gap:2rem;flex-wrap:wrap;">',
        unsafe_allow_html=True
    )
    dc1, dc2, dc3 = st.columns(3)
    dc1.markdown(
        f'<div><b style="color:#79c0ff;">G</b> sup. lateral<br>'
        f'{driver_delta(f"{anc_area/1e6:.2f}m²", f"{nArea/1e6:.2f}m²", anchor_product.get("G",1), nG or 1, "")}'
        f'<div style="font-size:0.72rem;color:#586069;">'
        f'ancla: {g_label_a} · nuevo: {g_label_n}</div></div>',
        unsafe_allow_html=True
    )
    dc2.markdown(
        f'<div><b style="color:#79c0ff;">D</b> espesor<br>'
        f'{driver_delta(f"{anc_e}mm", f"{ne}mm", anchor_product.get("D",1), nD or 1, "")}'
        f'<div style="font-size:0.72rem;color:#586069;">'
        f'ancla: {d_label_a} · nuevo: {d_label_n}</div></div>',
        unsafe_allow_html=True
    )
    dc3.markdown(
        f'<div><b style="color:#79c0ff;">X</b> características<br>'
        f'<div style="font-size:0.85rem;margin-top:0.2rem;">'
        f'ancla: <b>{anc_x_pts} pts</b>  →  nuevo: <b>{new_x_pts} pts</b></div>'
        f'<div style="font-size:0.72rem;color:#768390;margin-top:0.2rem;">'
        + (f'{sum(1 for a in anchor_product.get("x_active",{}).values() if a)} flags activos ancla  ·  '
           f'{sum(1 for a in new_x_active.values() if a)} flags activos nuevo')
        + '</div></div>',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Per-process complexity: anchor vs new product ─────────────────────────
    st.markdown(
        '<div class="sec-label" style="margin:1rem 0 0.4rem 0;">'
        'COMPLEJIDAD POR PROCESO — ancla vs producto extrapolado</div>',
        unsafe_allow_html=True
    )

    active_processes = profile_rules.get("processes", [])
    templates        = get_effective_templates(rules)

    if active_processes:
        # Header
        hc = st.columns([2, 1, 1.5, 1.5, 1.5])
        hc[0].markdown('<div class="sec-label">Proceso</div>', unsafe_allow_html=True)
        hc[1].markdown('<div class="sec-label">Drivers</div>', unsafe_allow_html=True)
        hc[2].markdown(
            f'<div class="sec-label">Ancla {complexity_badge(anchor_comp)}</div>',
            unsafe_allow_html=True
        )
        hc[3].markdown(
            f'<div class="sec-label">Nuevo {complexity_badge(comp_new)}</div>',
            unsafe_allow_html=True
        )
        hc[4].markdown('<div class="sec-label">Δ nivel</div>', unsafe_allow_html=True)
        st.markdown('<hr style="margin:0.2rem 0 0.3rem 0;">', unsafe_allow_html=True)

        for proc in active_processes:
            tmpl = templates.get(proc, {})
            drivers = tmpl.get("drivers", [])
            descs   = tmpl.get("descriptions", {})

            # Anchor complexity (uses anchor product's stored drivers)
            anc_level, anc_score, _, anc_used = compute_process_complexity(
                proc,
                anchor_product.get("G"), anchor_product.get("D"), anchor_product.get("C"),
                anchor_product.get("x_active", {}),
                profile_rules, rules, templates
            )

            # New product complexity
            new_level, new_score, new_missing, new_used = compute_process_complexity(
                proc, nG, nD, nC, new_x_active,
                profile_rules, rules, templates
            )

            # Delta indicator
            if anc_level == new_level:
                delta_html = '<span style="color:#3fb950;font-size:0.78rem;">= sin cambio</span>'
            elif new_level and anc_level:
                levels = ["C1", "C2", "C3"]
                direction = "↑" if levels.index(new_level) > levels.index(anc_level) else "↓"
                color = "#f85149" if direction == "↑" else "#79c0ff"
                delta_html = f'<span style="color:{color};font-weight:700;">{direction} {anc_level}→{new_level}</span>'
            else:
                delta_html = '<span style="color:#768390;font-size:0.78rem;">—</span>'

            # Build physical value hints per driver for display
            # Maps driver letter → (anchor raw value string, new raw value string)
            phys = {
                "G": (f"{anc_area/1e6:.2f}m²", f"{nArea/1e6:.2f}m²"),
                "D": (f"{anc_e}mm",             f"{ne}mm"),
                "X": (f"{anc_x_pts}pts",        f"{new_x_pts}pts"),
                "C": ("—", "—"),
            }

            def proc_cell(level, score, used, missing, is_new=False):
                parts = []
                for k, v in used.items():
                    if k == "X" and v == 0:
                        continue
                    raw = phys.get(k, ("",""))[1 if is_new else 0]
                    parts.append(
                        f'<b style="color:#cdd9e5;">{k}</b>'
                        f'<span style="color:#79c0ff;font-size:0.78rem;">={v}</span>'
                        f'<span style="color:#586069;font-size:0.7rem;"> ({raw})</span>'
                    )
                used_str  = ' <span style="color:#484f58;">+</span> '.join(parts) if parts else "—"
                miss_html = (
                    f'<span style="color:#e3b341;font-size:0.7rem;"> ⚠️{",".join(missing)}</span>'
                    if missing else ""
                )
                desc = descs.get(level, "") if level else ""
                return (
                    f'{complexity_badge(level) if level else "<span style=\'color:#768390\'>?</span>"}'
                    f' <span style="color:#768390;font-size:0.72rem;">{score} pts</span><br>'
                    f'<span style="font-size:0.72rem;">{used_str}</span>'
                    f'{miss_html}'
                    f'<div style="font-size:0.71rem;color:#8b949e;margin-top:0.1rem;">{desc}</div>'
                )

            rc = st.columns([2, 1, 1.5, 1.5, 1.5])
            rc[0].markdown(
                f'<div style="padding-top:0.3rem;font-size:0.88rem;font-weight:700;color:#cdd9e5;">{proc}</div>',
                unsafe_allow_html=True
            )
            rc[1].markdown(
                f'<div style="font-size:0.8rem;color:#79c0ff;padding-top:0.35rem;">{" + ".join(drivers)}</div>',
                unsafe_allow_html=True
            )
            rc[2].markdown(f'<div style="padding-top:0.2rem;">{proc_cell(anc_level, anc_score, anc_used, [], is_new=False)}</div>', unsafe_allow_html=True)
            rc[3].markdown(f'<div style="padding-top:0.2rem;">{proc_cell(new_level, new_score, new_used, new_missing, is_new=True)}</div>', unsafe_allow_html=True)
            rc[4].markdown(f'<div style="padding-top:0.4rem;">{delta_html}</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:0.8rem;"></div>', unsafe_allow_html=True)

    # Assumptions shown explicitly
    with st.expander("📋 Supuestos de esta extrapolación"):
        st.markdown(f"""
**Driver primario:** área de planta (L × W)

**Escala material:** lineal con área → ×{area_scale:.3f}
&nbsp;&nbsp;Área ancla: {anchor_product['area']/1e6:.3f} m²  →  Área nueva: {nArea/1e6:.3f} m²

**Consumibles base:** escalan con área (pulido proporcional a superficie)
**Consumibles X:** se agregan como costo fijo según características activas

**Lo que NO se escala:**
- Piezas compradas (patines, pomeles, manillas) — se asumen iguales al ancla
- Componentes eléctricos o mecánicos — agregar manualmente si difieren
- Tiempo de ensamble — requiere cronómetro real para validar

**Confianza:** {'Alta — mismo perfil que ancla' if comp_new == anchor_comp else f'⚠️ Complejidad diferente al ancla ({anchor_comp} → {comp_new}) — revisar supuestos'}
        """)

# ─── Tab 5: Process templates editor ─────────────────────────────────────────

def render_templates_editor(rules):
    st.markdown('<h3>Templates de Complejidad por Proceso</h3>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#8b949e;font-size:0.85rem;">'
        'Edita los umbrales score→nivel (C1/C2/C3) y los tiempos de referencia para cada proceso. '
        'Los valores guardados aquí tienen prioridad sobre los defaults del código. '
        'Tab 4 (Desglose HH) usa los templates efectivos en tiempo real.</p>',
        unsafe_allow_html=True
    )

    eff_tmpls   = get_effective_templates(rules)
    saved_tmpls = rules.get("process_templates", {})

    # ── Overview matrix ───────────────────────────────────────────────────────
    st.markdown('<div class="sec-label" style="margin-bottom:0.5rem;">RESUMEN</div>', unsafe_allow_html=True)

    def fmt_range(thresholds, lvl):
        r = thresholds.get(lvl, ["-", "-"])
        hi_str = "∞" if r[1] >= 99 else str(r[1])
        return f"{r[0]}–{hi_str}"

    def fmt_time(tmpl, lvl):
        t = tmpl.get(lvl, {})
        ts = t.get("T_setup_min", 0)
        te = t.get("T_exec_min", 0)
        n  = t.get("n_ops", 1)
        return f"⚙{ts}+▶{te}m·{n}op"

    overview = []
    for proc, tmpl in eff_tmpls.items():
        thr = tmpl.get("score_thresholds", {})
        overview.append({
            "Proceso":    proc,
            "Drivers":    " + ".join(tmpl.get("drivers", [])),
            "C1 score":   fmt_range(thr, "C1"),
            "C2 score":   fmt_range(thr, "C2"),
            "C3 score":   fmt_range(thr, "C3"),
            "C1 tiempos": fmt_time(tmpl, "C1"),
            "C2 tiempos": fmt_time(tmpl, "C2"),
            "C3 tiempos": fmt_time(tmpl, "C3"),
            "Override":   "✅" if proc in saved_tmpls else "—",
        })
    st.dataframe(pd.DataFrame(overview), use_container_width=True, hide_index=True)

    # ── Per-process editors ───────────────────────────────────────────────────
    st.markdown(
        '<div class="sec-label" style="margin:1rem 0 0.5rem 0;">EDITAR PROCESO</div>',
        unsafe_allow_html=True
    )

    new_saved = dict(saved_tmpls)  # accumulate edits across all process expanders

    for proc, base_tmpl in PROCESS_TEMPLATES.items():
        eff = eff_tmpls[proc]
        is_overridden = proc in saved_tmpls
        label = f"{'✅ ' if is_overridden else ''}⚙️  {proc}   —   drivers: {' + '.join(base_tmpl['drivers'])}"

        with st.expander(label, expanded=False):

            # ── Score thresholds + descriptions ──────────────────────────────
            st.markdown('<div class="sec-label">UMBRALES  (score → nivel)</div>', unsafe_allow_html=True)
            hc = st.columns([0.8, 1, 1, 4])
            for lbl in ["Nivel", "Score min", "Score max", "Descripción"]:
                hc[["Nivel", "Score min", "Score max", "Descripción"].index(lbl)].markdown(
                    f'<div class="sec-label">{lbl}</div>', unsafe_allow_html=True
                )

            new_thresholds = {}
            new_descs      = {}
            for lvl in ["C1", "C2", "C3"]:
                rng      = eff["score_thresholds"].get(lvl, [0, 99])
                desc_val = eff.get("descriptions", {}).get(lvl, "")
                rc = st.columns([0.8, 1, 1, 4])
                rc[0].markdown(complexity_badge(lvl), unsafe_allow_html=True)
                lo = rc[1].number_input("min", value=rng[0], min_value=0, max_value=50,
                                        key=f"tmpl_lo_{proc}_{lvl}", label_visibility="collapsed")
                hi = rc[2].number_input("max", value=rng[1], min_value=0, max_value=99,
                                        key=f"tmpl_hi_{proc}_{lvl}", label_visibility="collapsed",
                                        help="Usa 99 para 'sin límite superior'")
                new_desc = rc[3].text_input("desc", value=desc_val,
                                            key=f"tmpl_desc_{proc}_{lvl}", label_visibility="collapsed")
                new_thresholds[lvl] = [lo, hi]
                new_descs[lvl]      = new_desc

            # ── Time templates ────────────────────────────────────────────────
            st.markdown(
                '<div class="sec-label" style="margin-top:0.9rem;">'
                'TIEMPOS DE REFERENCIA  (anchor, factor_escala = 1.0)</div>',
                unsafe_allow_html=True
            )
            th = st.columns([0.8, 1.2, 1.5, 1])
            for lbl in ["Nivel", "T setup (min)", "T ejecución (min)", "Operadores"]:
                th[["Nivel", "T setup (min)", "T ejecución (min)", "Operadores"].index(lbl)].markdown(
                    f'<div class="sec-label">{lbl}</div>', unsafe_allow_html=True
                )

            new_times = {}
            for lvl in ["C1", "C2", "C3"]:
                t_ref    = eff.get(lvl, {})
                ts_def   = t_ref.get("T_setup_min", 0)
                te_def   = t_ref.get("T_exec_min",  0)
                no_def   = t_ref.get("n_ops", 1)
                tc = st.columns([0.8, 1.2, 1.5, 1])
                tc[0].markdown(complexity_badge(lvl), unsafe_allow_html=True)
                ts = tc[1].number_input("setup", value=ts_def, min_value=0,
                                        key=f"tmpl_ts_{proc}_{lvl}", label_visibility="collapsed")
                te = tc[2].number_input("exec",  value=te_def, min_value=0,
                                        key=f"tmpl_te_{proc}_{lvl}", label_visibility="collapsed")
                no = tc[3].number_input("ops",   value=no_def, min_value=0, max_value=10,
                                        key=f"tmpl_no_{proc}_{lvl}", label_visibility="collapsed")
                new_times[lvl] = {"T_setup_min": ts, "T_exec_min": te, "n_ops": no}

            # ── Live preview ──────────────────────────────────────────────────
            st.markdown(
                '<div style="font-size:0.78rem;color:#768390;margin-top:0.5rem;">'
                'Costo labor estimado C1→C2→C3 con tarifa default '
                f'${HH_RATES_DEFAULT.get(proc, 6500)//1000}k/hr:</div>',
                unsafe_allow_html=True
            )
            rate = HH_RATES_DEFAULT.get(proc, 6500)
            prev_parts = []
            for lvl in ["C1", "C2", "C3"]:
                t = new_times[lvl]
                labor = (t["T_setup_min"] + t["T_exec_min"]) / 60 * rate * max(t["n_ops"], 1)
                prev_parts.append(f'{complexity_badge(lvl)} {fmt_clp(labor)}')
            st.markdown(
                f'<div style="display:flex;gap:1.5rem;margin-top:0.3rem;">{"".join(prev_parts)}</div>',
                unsafe_allow_html=True
            )

            # Accumulate for this process
            new_saved[proc] = {
                "drivers":          base_tmpl["drivers"],
                "score_thresholds": new_thresholds,
                "descriptions":     new_descs,
                **new_times,
            }

    # ── Global save ───────────────────────────────────────────────────────────
    st.markdown('<div style="margin-top:1.2rem;"></div>', unsafe_allow_html=True)
    if st.button("💾 Guardar todos los templates en PROCESS_RULES.json", type="primary"):
        rules["process_templates"] = new_saved
        rules["meta"]["last_updated"] = str(date.today())
        save_rules(rules)
        st.success(
            "✅ Templates guardados en PROCESS_RULES.json → process_templates. "
            "Tabs 4 y 2 usarán los nuevos umbrales en el próximo cálculo."
        )

    if st.button("↩️ Restaurar defaults del código", type="secondary"):
        if "process_templates" in rules:
            del rules["process_templates"]
            rules["meta"]["last_updated"] = str(date.today())
            save_rules(rules)
            st.success("✅ Overrides eliminados. Se usarán los defaults hardcodeados.")


# ─── Tab 5: Save findings ──────────────────────────────────────────────────────

def render_icm(rules: dict, profile_key: str):
    """
    ICM — Índice de Confianza del Modelo.
    Lean-inspired proof coverage metric:
      Layer 1 (physical):  40% — driver fill rates (G/D/C/X) per product
      Layer 2 (semantic):  60% — verified knowledge chunks per (process × level) combo

    A claim with no backing chunk is a "sorry" — used but unproven.
    Calibration converts sorrys into verified proofs.
    """
    profile_rules = rules.get("profiles", {}).get(profile_key, {})
    df = _load_profile(profile_key)
    chunks = _load_chunks()

    # Split chunks by layer
    profile_chunks  = [c for c in chunks
                       if c.get("metadata", {}).get("perfil_proceso") in (profile_key, "todos")]
    l1_chunks       = [c for c in profile_chunks if c.get("metadata", {}).get("layer") == "physical"]
    l2_chunks       = [c for c in chunks         if c.get("metadata", {}).get("layer") == "semantic"]

    # Empirically verified = measured by a person (not just bootstrapped from rules)
    verified_l1 = [c for c in l1_chunks if
                   c.get("metadata", {}).get("verified", False) and
                   c.get("metadata", {}).get("confianza") not in ("estructural",)]
    verified_l2 = [c for c in l2_chunks if c.get("metadata", {}).get("verified", False)]
    sorry_l2    = [c for c in l2_chunks if not c.get("metadata", {}).get("verified", False)]

    # ── Layer 1: driver fill rates ──────────────────────────────────────────────
    total = max(len(df), 1)
    has_c_driver = profile_rules.get("c_driver") is not None
    has_x_defs   = bool(profile_rules.get("x_flags"))

    g_pct = df["G"].notna().sum() / total * 100
    d_pct = df["D"].notna().sum() / total * 100
    c_pct = (df["c_value"].notna().sum() / total * 100) if has_c_driver else 100.0
    x_pct = (df["x_flags"].apply(lambda v: bool(v and v not in ("[]","null","")) if pd.notna(v) else False).sum()
             / total * 100) if has_x_defs else 100.0

    active_drivers = ["G", "D"]
    if has_c_driver: active_drivers.append("C")
    if has_x_defs:   active_drivers.append("X")
    driver_score = (g_pct + d_pct + c_pct + x_pct) / 4

    # ── Layer 2a: empirical chunk coverage per (process × level) ────────────────
    tiers = profile_rules.get("process_tiers", {})
    combos = [(proc, lvl)
              for lvl, procs in tiers.items()
              for proc in procs]
    total_combos = max(len(combos), 1)

    claim_rows = []
    covered = 0
    for proc, lvl in sorted(combos):
        # Only count empirically verified (calibration sessions), not structural bootstraps
        matching = [c for c in verified_l1
                    if (c.get("metadata", {}).get("proceso") == proc or
                        c.get("metadata", {}).get("proceso") == "calibracion")
                    and c.get("metadata", {}).get("nivel_complejidad") in (lvl, "C2→C3")]
        proven = len(matching) > 0
        if proven:
            covered += 1
        exp = (matching[0].get("metadata", {}).get("expert_id") or
               matching[0].get("metadata", {}).get("calibrado_por", "—")) if matching else "—"
        claim_rows.append({
            "Proceso": proc,
            "Nivel": lvl,
            "Estado": "✅ medido" if proven else "❌ sorry",
            "Expert": exp,
        })

    # ── Layer 2b: semantic mapping verification ──────────────────────────────────
    profile_sem   = [c for c in l2_chunks
                     if c.get("metadata", {}).get("perfil_proceso") in (profile_key, "todos")]
    verified_sem  = [c for c in profile_sem if c.get("metadata", {}).get("verified", False)]
    total_sem     = max(len(profile_sem), 1)
    sem_score     = len(verified_sem) / total_sem * 100

    # Chunk score = average of process coverage + semantic coverage
    chunk_score = (covered / total_combos * 100 * 0.6 + sem_score * 0.4)

    # ── ICM ─────────────────────────────────────────────────────────────────────
    icm = round(driver_score * 0.40 + chunk_score * 0.60)
    sorry_count = total_combos - covered

    if icm >= 80:
        card_cls, icm_color, status = "cal-card-green", "#3fb950", "Modelo calibrado"
    elif icm >= 50:
        card_cls, icm_color, status = "cal-card-amber", "#e3b341", "Modelo funcional"
    else:
        card_cls, icm_color, status = "cal-card-red",   "#f85149", "Modelo en construcción"

    st.markdown(
        f'<div class="{card_cls}">'
        f'<div class="sec-label">ICM — ÍNDICE DE CONFIANZA DEL MODELO</div>'
        f'<div style="font-size:3rem;font-weight:800;color:{icm_color};line-height:1.1;">'
        f'{icm}<span style="font-size:1.2rem;color:#768390;">/100</span></div>'
        f'<div style="font-size:0.85rem;color:#cdd9e5;margin-top:0.3rem;">{status}</div>'
        f'<div style="font-size:0.75rem;color:#768390;margin-top:0.5rem;">'
        f'Cálculo: Driver fill rate (40%) + Chunk coverage (60%)</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Breakdown ────────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="sec-label" style="margin-top:1rem;">LAYER 1 — DRIVERS FÍSICOS</div>',
                    unsafe_allow_html=True)
        st.caption(f"Score: {driver_score:.0f}/100  ·  {total} productos  ·  {len(active_drivers)} drivers activos")
        driver_table = [
            {"Driver": "G (Geometría)",  "Disponible": f"{g_pct:.0f}%", "Productos": f"{df['G'].notna().sum()}/{total}", "Estado": "✅" if g_pct > 80 else "⚠️"},
            {"Driver": "D (Espesor)",    "Disponible": f"{d_pct:.0f}%", "Productos": f"{df['D'].notna().sum()}/{total}", "Estado": "✅" if d_pct > 80 else "⚠️"},
            {"Driver": f"C ({profile_rules.get('c_driver','—')})",
             "Disponible": f"{c_pct:.0f}%" if has_c_driver else "N/A",
             "Productos":  f"{df['c_value'].notna().sum()}/{total}" if has_c_driver else "N/A",
             "Estado": ("✅" if c_pct > 80 else "⚠️") if has_c_driver else "—"},
            {"Driver": f"X ({len(profile_rules.get('x_flags',{}))} flags)",
             "Disponible": f"{x_pct:.0f}%" if has_x_defs else "N/A",
             "Productos": "—" if not has_x_defs else f"{df['x_flags'].apply(lambda v: bool(v and v not in ('[]','null',''))).sum()}/{total}",
             "Estado": ("✅" if x_pct > 80 else "⚠️") if has_x_defs else "—"},
        ]
        st.dataframe(pd.DataFrame(driver_table), use_container_width=True, hide_index=True)

        if total > 0 and not df.empty:
            worst_driver = min([("G", g_pct), ("D", d_pct)], key=lambda x: x[1])
            missing_g = df[df["G"].isna()]["handle"].tolist()
            if missing_g:
                with st.expander(f"⚠️ {len(missing_g)} productos sin G"):
                    st.code(", ".join(missing_g[:20]))

    with col2:
        st.markdown('<div class="sec-label" style="margin-top:1rem;">LAYER 2a — MEDICIONES EMPÍRICAS (proceso × nivel)</div>',
                    unsafe_allow_html=True)
        sorry_count = total_combos - covered
        st.caption(
            f"Score: {covered/total_combos*100:.0f}/100  ·  "
            f"{covered}/{total_combos} combos medidos  ·  {sorry_count} sorry"
        )
        if sorry_count > 0:
            st.markdown(
                f'<div class="cal-card-amber" style="padding:0.5rem 0.8rem;margin:0.3rem 0;">'
                f'<span style="font-size:0.82rem;color:#e3b341;font-weight:600;">'
                f'⚠️ {sorry_count} combos sin medición real</span><br>'
                f'<span style="font-size:0.72rem;color:#768390;">'
                f'Calibrar estos combos → cada uno sube ICM ~{60/total_combos*0.6:.1f} pts</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.dataframe(pd.DataFrame(claim_rows), use_container_width=True, hide_index=True)

        st.markdown('<div class="sec-label" style="margin-top:1rem;">LAYER 2b — MAPEOS SEMÁNTICOS (término → concepto)</div>',
                    unsafe_allow_html=True)
        st.caption(
            f"Score: {sem_score:.0f}/100  ·  "
            f"{len(verified_sem)}/{len(profile_sem)} mapeos verificados  ·  "
            f"{len(profile_sem) - len(verified_sem)} sorry"
        )
        sem_rows = []
        for c in profile_sem:
            meta = c.get("metadata", {})
            sem_rows.append({
                "Término": meta.get("sem_term", c.get("chunk_id","")),
                "Concepto": meta.get("sem_concept", "?"),
                "Tipo": meta.get("sem_concept_type", "?"),
                "Estado": "✅" if meta.get("verified") else "❌ sorry",
                "Expert": meta.get("expert_id", "—") or "—",
            })
        if sem_rows:
            st.dataframe(pd.DataFrame(sem_rows), use_container_width=True, hide_index=True)

        st.caption(
            f"Chunks totales: {len(chunks)}  ·  "
            f"Bootstrap L1: {len(l1_chunks)}  ·  "
            f"Empíricos L1: {len(verified_l1)}  ·  "
            f"Semánticos: {len(l2_chunks)} ({len(verified_l2)} verificados)"
        )

    # ── Actionable next step ────────────────────────────────────────────────────
    sorry_process_rows = [r for r in claim_rows if "sorry" in r["Estado"]]
    sorry_sem_rows     = [r for r in sem_rows if "sorry" in r.get("Estado","")]

    if sorry_process_rows:
        priority = sorry_process_rows[0]
        icm_gain = round(60 * 0.6 / total_combos, 1)
        st.info(
            f"**Acción de mayor impacto:** Calibra **{priority['Proceso']} × {priority['Nivel']}** "
            f"en la pestaña 💾 Guardar Hallazgos. "
            f"Cada combo medido sube el ICM ~{icm_gain} pts."
        )
    elif sorry_sem_rows:
        priority_sem = sorry_sem_rows[0]
        st.info(
            f"**Próxima acción:** Verifica el mapeo semántico "
            f"**'{priority_sem.get('Término','?')}' → {priority_sem.get('Concepto','?')}** "
            f"con Hernán y actualiza `semantic_mappings.json`."
        )
    elif icm < 100:
        low_driver = min([("G", g_pct), ("D", d_pct)], key=lambda x: x[1])
        st.info(
            f"**Acción de mayor impacto:** Completa el driver **{low_driver[0]}** "
            f"para los productos que lo tienen vacío."
        )


def render_save_findings(products, rules, profile_key):
    st.markdown('<h3>Guardar Hallazgos de Calibración</h3>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#8b949e;font-size:0.85rem;">'
        'Los hallazgos se guardan en PROCESS_RULES.json y se genera un chunk para '
        'knowledge-chunks.jsonl. El model-auditor usará estos datos en el próximo run.</p>',
        unsafe_allow_html=True
    )

    c2_data = next((p for p in products.values() if p.get("expected_comp") == "C2"), None)
    c3_data = next((p for p in products.values() if p.get("expected_comp") == "C3"), None)
    c2_name = next((n for n, p in products.items() if p.get("expected_comp") == "C2"), "C2")
    c3_name = next((n for n, p in products.items() if p.get("expected_comp") == "C3"), "C3")

    notes = st.text_area(
        "Notas de calibración (se guardan como chunk de conocimiento)",
        placeholder="ej: El salto C2→C3 está dominado por el Disco Multifinic ($32.400). "
                    "El material escala ×2.1 con área pero los consumibles escalan ×3.8 — "
                    "driven por el X flag terminacion_multifinic.",
        key="cal_notes"
    )

    calibrator = st.text_input("Tu nombre (calibrador)", key="cal_by", placeholder="ej: Fabio")

    if st.button("💾 Guardar calibración en PROCESS_RULES.json + knowledge-chunks.jsonl", type="primary"):
        if not calibrator:
            st.error("Ingresa tu nombre.")
            return

        # ── Update benchmarks in rules ──────────────────────────────────────────
        for comp, data in [("C2", c2_data), ("C3", c3_data)]:
            if data and data.get("mat_total", 0) > 0:
                rules["profiles"][profile_key]["cost_benchmarks"][comp]["material_total_clp"]    = data["mat_total"]
                rules["profiles"][profile_key]["cost_benchmarks"][comp]["consumables_total_clp"] = data["cons_total"]
                rules["profiles"][profile_key]["cost_benchmarks"][comp]["calibrated"]            = True
                rules["profiles"][profile_key]["cost_benchmarks"][comp]["calibration_date"]      = str(date.today())

        if c2_data and c3_data and c2_data.get("mat_total", 0) > 0 and c2_data.get("cons_total", 0) > 0:
            rules["profiles"][profile_key]["expected_cost_ratios"]["C2_to_C3"] = {
                "material":    round(c3_data["mat_total"] / c2_data["mat_total"], 3),
                "consumables": round(c3_data["cons_total"] / c2_data["cons_total"], 3),
                "notes":       notes or f"Calibrado {date.today()} por {calibrator}",
            }

        rules["meta"]["last_updated"]   = str(date.today())
        rules["meta"]["calibrated_by"]  = calibrator
        save_rules(rules)

        # ── Build ratios for chunk text ─────────────────────────────────────────
        mat_ratio_str = cons_ratio_str = ""
        if c2_data and c3_data and c2_data.get("mat_total", 0) > 0:
            mr = c3_data["mat_total"] / c2_data["mat_total"]
            cr = c3_data["cons_total"] / c2_data["cons_total"] if c2_data.get("cons_total", 0) > 0 else 0
            mat_ratio_str  = f"×{mr:.2f}"
            cons_ratio_str = f"×{cr:.2f}"

        # ── Determine which drivers are relevant to this profile ────────────────
        p_rules       = rules.get("profiles", {}).get(profile_key, {})
        primary_d     = p_rules.get("primary_drivers", [])
        secondary_d   = p_rules.get("secondary_drivers", [])
        all_d         = primary_d + secondary_d
        drivers_cited = list(dict.fromkeys(all_d))  # preserve order, deduplicate

        # ── Build enriched chunk (Lean-inspired: verified claim with context) ───
        chunk_id = f"cal-{profile_key}-c2c3-{str(date.today()).replace('-','')}"
        semantic_version = f"v{date.today().strftime('%Y-%m')}"

        chunk = {
            "chunk_id": chunk_id,
            "texto": (
                f"Calibración {profile_key} C2→C3 ({date.today()}, expert: {calibrator}). "
                f"Ancla C2: {c2_name} — material {fmt_clp(c2_data['mat_total'] if c2_data else 0)}, "
                f"consumibles {fmt_clp(c2_data['cons_total'] if c2_data else 0)}. "
                f"Ancla C3: {c3_name} — material {fmt_clp(c3_data['mat_total'] if c3_data else 0)}, "
                f"consumibles {fmt_clp(c3_data['cons_total'] if c3_data else 0)}. "
                f"Ratio material C2→C3: {mat_ratio_str}. Ratio consumibles: {cons_ratio_str}. "
                f"Drivers activos: {', '.join(drivers_cited)}. {notes}"
            ),
            "texto_embedding": (
                f"calibración costos {profile_key} C2 C3 ratio material consumibles "
                f"{c2_name} {c3_name} {mat_ratio_str} {cons_ratio_str} "
                f"drivers {' '.join(drivers_cited)} {notes}"
            ),
            "metadata": {
                # ── Lean Layer 1 (physical) ─────────────────────────────────────
                "layer":            "physical",
                "semantic_version": semantic_version,
                "expert_id":        calibrator,
                "verified":         True,
                "valid_from":       str(date.today()),
                "valid_until":      None,
                "superseded_by":    None,
                "drivers_cited":    drivers_cited,
                # ── Domain metadata ─────────────────────────────────────────────
                "proceso":          "calibracion",
                "perfil_proceso":   profile_key,
                "nivel_complejidad": "C2→C3",
                "tipo_impacto":     "costos_directos",
                "escalamiento":     f"material {mat_ratio_str}, consumibles {cons_ratio_str}",
                "confianza":        "medido",
                "fuente":           "calibration_tool",
                "fuente_id":        chunk_id,
                "fecha_sesion":     str(date.today()),
                "ref_producto":     f"{c2_name},{c3_name}",
                "etiquetas":        [profile_key, "calibracion", "C2_C3_ratio"] + drivers_cited,
                # ── Legacy fields (for audit_model.py compatibility) ────────────
                "activo":           True,
                "validado_en":      str(date.today()),
                "calibrado_por":    calibrator,
                "source":           "calibration_tool",
            }
        }

        # ── Write directly to knowledge-chunks.jsonl ────────────────────────────
        _write_chunk(chunk)
        st.cache_data.clear()

        st.success(
            f"✅ PROCESS_RULES.json actualizado y chunk `{chunk_id}` escrito en "
            f"`knowledge-chunks.jsonl`.\n\n"
            f"ICM actualizado — ve a la pestaña **🔬 ICM** para ver el impacto."
        )
        with st.expander("Ver chunk generado", expanded=False):
            st.code(json.dumps(chunk, indent=2, ensure_ascii=False), language="json")

# ─── Tab 1 (new): Dynamic BOM per anchor per complexity level ────────────────

def render_bom_entry(rules, profile_key):
    """
    Replacement for the hardcoded C2/C3 BAPLA/BARE4 Tab 1.
    For each complexity level (C1/C2/C3):
      - Anchor selector (products from DB in that bucket)
      - BOM editor (pre-populated from DB if saved, else blank)
      - Save BOM to DB
    Bottom section: extrapolation table for all products in same bucket.
    """
    profile_rules = rules["profiles"].get(profile_key, {})
    anchors = profile_rules.get("anchors", {})

    st.markdown(
        '<p style="color:#8b949e;font-size:0.85rem;margin-bottom:1rem;">'
        'Ingresa el BOM real para el producto ancla de cada nivel. '
        'El ancla se configura en <b>📊 Datos → Anclas</b>. '
        'Los costos se guardan en la DB y se extrapolán al resto del bucket.</p>',
        unsafe_allow_html=True
    )

    all_products = {}   # for downstream tabs

    for comp in ["C1", "C2", "C3"]:
        bucket_df = _load_bucket(profile_key, comp)
        anchor_handle = anchors.get(comp)

        badge_cls = {"C1":"badge-c1","C2":"badge-c2","C3":"badge-c3"}.get(comp,"badge-c1")
        n_prods = len(bucket_df)

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:0.7rem;margin:1.2rem 0 0.4rem 0;">'
            f'<span class="badge {badge_cls}">{comp}</span>'
            f'<span style="color:#cdd9e5;font-size:0.95rem;font-weight:600;">'
            f'{n_prods} productos</span>'
            f'{"<span style=\"color:#3fb950;font-size:0.78rem;\">⭐ ancla: " + anchor_handle + "</span>" if anchor_handle else "<span style=\"color:#f85149;font-size:0.78rem;\">sin ancla — configúrala en 📊 Datos → Anclas</span>"}'
            f'</div>',
            unsafe_allow_html=True
        )

        if bucket_df.empty:
            st.markdown(
                f'<div style="color:#484f58;font-size:0.82rem;margin-bottom:0.5rem;">'
                f'Sin productos {comp} en {profile_key}.</div>',
                unsafe_allow_html=True
            )
            continue

        # Anchor selector (override from anchor set in data_input.py)
        handles = bucket_df["handle"].tolist()
        default_idx = handles.index(anchor_handle) if anchor_handle in handles else 0
        selected_anchor = st.selectbox(
            f"Ancla {comp}",
            handles,
            index=default_idx,
            key=f"anchor_sel_{profile_key}_{comp}",
            format_func=lambda h: f"{'⭐ ' if h == anchor_handle else ''}{h}",
        )

        anchor_row = bucket_df[bucket_df["handle"] == selected_anchor].iloc[0]
        L = float(anchor_row.get("dim_l_mm") or 0)
        W = float(anchor_row.get("dim_w_mm") or 0)
        H = float(anchor_row.get("dim_h_mm") or 0)
        e = float(anchor_row.get("dim_espesor_mm") or 0)
        G_v = anchor_row.get("G")
        D_v = anchor_row.get("D")
        C_v = anchor_row.get("c_value")
        _xf_raw = anchor_row.get("x_flags", "[]") or "[]"
        x_flags_saved = json.loads(_xf_raw) if isinstance(_xf_raw, str) else (_xf_raw or [])

        # Load saved BOM from DB
        saved_mat_json  = anchor_row.get("bom_materials",  "[]") or "[]"
        saved_cons_json = anchor_row.get("bom_consumables","[]") or "[]"
        saved_mat  = json.loads(saved_mat_json)  if isinstance(saved_mat_json, str)  else []
        saved_cons = json.loads(saved_cons_json) if isinstance(saved_cons_json, str) else []

        # Default defaults from Python constants (p-basurero-cil only)
        if not saved_mat and profile_key == "p-basurero-cil" and comp == "C3":
            saved_mat  = BARE4_MATERIALS_DEFAULT
            saved_cons = BARE4_CONSUMABLES_DEFAULT

        _x_label = ", ".join(x_flags_saved) if x_flags_saved else "—"
        with st.expander(
            f"📦 BOM del ancla: {selected_anchor}  ·  G={G_v or '—'} D={D_v or '—'} C={C_v or '—'} X=[{_x_label}]",
            expanded=bool(anchor_handle == selected_anchor)
        ):
            # Dimension override row
            d1, d2, d3, d4 = st.columns(4)
            L = d1.number_input("Largo mm",  value=L, min_value=0.0, key=f"L_{profile_key}_{comp}")
            W = d2.number_input("Ancho mm",  value=W, min_value=0.0, key=f"W_{profile_key}_{comp}")
            H = d3.number_input("Alto mm",   value=H, min_value=0.0, key=f"H_{profile_key}_{comp}")
            e = d4.number_input("Espesor mm",value=e, min_value=0.0, step=0.1, key=f"e_{profile_key}_{comp}", format="%.1f")

            G_new, area = compute_G(L, W, H, rules)
            D_new = compute_D(e, rules)
            area_str = f"{area/1e6:.3f} m²" if area else "—"
            _profile_rules = rules["profiles"].get(profile_key, {})
            _x_defs = _profile_rules.get("x_flags", {})
            _c_driver_field = _profile_rules.get("c_driver")
            _c_label = C_DRIVER_LABELS.get(_c_driver_field, _c_driver_field or "C") if _c_driver_field else "C"
            _x_badges = " ".join(
                f'<span style="background:#1f3a5f;color:#79c0ff;border-radius:4px;padding:1px 6px;font-size:0.75rem;">'
                f'{_x_defs[xf]["label"] if xf in _x_defs else xf}</span>'
                for xf in x_flags_saved
            ) or '<span style="color:#484f58;font-size:0.78rem;">ninguna</span>'
            st.markdown(
                f'<div style="display:flex;gap:1.2rem;flex-wrap:wrap;margin-bottom:0.6rem;font-size:0.8rem;">'
                f'<span style="color:#79c0ff;">G={G_new or "—"} · D={D_new or "—"} · Área={area_str}</span>'
                f'<span style="color:#cdd9e5;">{_c_label}={C_v or "—"}</span>'
                f'<span>X: {_x_badges}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            # ── BOM editors wrapped in a form to prevent mid-edit reruns ──────
            _mat_skey  = f"mat_{profile_key}_{comp}"
            _cons_skey = f"cons_{profile_key}_{comp}"
            _mat_hkey  = f"h_{_mat_skey}"
            _cons_hkey = f"h_{_cons_skey}"
            _mat_default  = saved_mat  or [{"Subconjunto":"","Dimensiones":"","Material":"","Cantidad":1.0,"kg_ml":0.0,"precio_kg":3600,"total":0}]
            _cons_default = saved_cons or [{"Producto":"","Proceso":"soldadura","Cantidad":0,"Unidad":"u","Precio_u":0,"Total":0}]

            # Seed state from DB; invalidate when anchor changes
            _mat_hash = hash(str(_mat_default))
            _cons_hash = hash(str(_cons_default))
            if st.session_state.get(_mat_hkey) != _mat_hash or _mat_skey not in st.session_state:
                st.session_state[_mat_skey]  = pd.DataFrame(_mat_default)
                st.session_state[_mat_hkey]  = _mat_hash
            if st.session_state.get(_cons_hkey) != _cons_hash or _cons_skey not in st.session_state:
                st.session_state[_cons_skey] = pd.DataFrame(_cons_default)
                st.session_state[_cons_hkey] = _cons_hash

            with st.form(f"bom_form_{profile_key}_{comp}"):
                st.markdown('<div class="sec-label">MATERIALES — BOM</div>', unsafe_allow_html=True)
                mat_df = st.data_editor(
                    st.session_state[_mat_skey],
                    use_container_width=True, num_rows="dynamic", hide_index=True,
                    column_config={
                        "total":     st.column_config.NumberColumn("Total $",     format="%.0f", step=1, min_value=0),
                        "precio_kg": st.column_config.NumberColumn("$/kg o $/u",  format="%.0f", step=1),
                        "kg_ml":     st.column_config.NumberColumn("kg o ML o u", format="%.4f", step=0.0001),
                        "Cantidad":  st.column_config.NumberColumn("Cant. mat.",   format="%.3f", step=0.001),
                    },
                )
                st.markdown('<div class="sec-label" style="margin-top:0.6rem;">CONSUMIBLES</div>', unsafe_allow_html=True)
                cons_df = st.data_editor(
                    st.session_state[_cons_skey],
                    use_container_width=True, num_rows="dynamic", hide_index=True,
                    column_config={
                        "Precio_u": st.column_config.NumberColumn("Precio u.", format="%.0f", step=1),
                        "Total":    st.column_config.NumberColumn("Total $",   format="%.0f", step=1, min_value=0),
                        "Cantidad": st.column_config.NumberColumn("Cant.",     format="%.3f", step=0.001),
                    },
                )
                save_clicked = st.form_submit_button(
                    f"💾 Guardar BOM ({selected_anchor})",
                    use_container_width=True,
                )

            # Process form submission outside the form context
            if save_clicked:
                # Use user-entered totals directly — do not auto-compute over them
                mat_total  = int(mat_df["total"].fillna(0).sum())  if isinstance(mat_df, pd.DataFrame) and "total"  in mat_df.columns else 0
                cons_total = int(cons_df["Total"].fillna(0).sum()) if isinstance(cons_df, pd.DataFrame) and "Total"  in cons_df.columns else 0
                total      = mat_total + cons_total
                _save_bom_to_db(selected_anchor, mat_df, cons_df)
                if "cost_benchmarks" not in rules["profiles"][profile_key]:
                    rules["profiles"][profile_key]["cost_benchmarks"] = {}
                rules["profiles"][profile_key]["cost_benchmarks"][comp] = {
                    "anchor_sku": selected_anchor,
                    "short_name": selected_anchor,
                    "dims": {"L_mm": L, "W_mm": W, "H_mm": H, "espesor_mm": e},
                    "material_total_clp": mat_total,
                    "consumables_total_clp": cons_total,
                    "calibrated": total > 0,
                    "calibration_date": str(date.today()),
                    "notes": f"BOM ingresado {date.today()}",
                }
                rules["profiles"][profile_key]["anchors"][comp] = selected_anchor
                rules["meta"]["last_updated"] = str(date.today())
                save_rules(rules)
                # Clear state so next render re-seeds from fresh DB data
                for _k in [_mat_skey, _mat_hkey, _cons_skey, _cons_hkey]:
                    st.session_state.pop(_k, None)
                st.success(f"✅ BOM guardado — {selected_anchor} ({comp})")
                st.rerun()
            else:
                # Show last-saved totals (update after next save)
                mat_total  = int(mat_df["total"].fillna(0).sum())  if "total"  in mat_df.columns else 0
                cons_total = int(cons_df["Total"].fillna(0).sum()) if "Total"  in cons_df.columns else 0
                total      = mat_total + cons_total

            st.markdown(
                f'<div style="display:flex;gap:1rem;margin-top:0.5rem;flex-wrap:wrap;">'
                f'<div class="cal-card" style="flex:1;min-width:110px;text-align:center;">'
                f'<div class="sec-label">MATERIAL</div>'
                f'<div class="number-big">{fmt_clp(mat_total)}</div></div>'
                f'<div class="cal-card" style="flex:1;min-width:110px;text-align:center;">'
                f'<div class="sec-label">CONSUMIBLES</div>'
                f'<div class="number-big">{fmt_clp(cons_total)}</div></div>'
                f'<div class="cal-card" style="flex:1;min-width:110px;text-align:center;">'
                f'<div class="sec-label">TOTAL DIRECTO</div>'
                f'<div class="number-big" style="color:#3fb950;">{fmt_clp(total)}</div></div>'
                f'</div>',
                unsafe_allow_html=True
            )

        # Store for downstream tabs (use saved DB values for stability)
        _dn = lambda v: float(v) if v is not None and v == v else 0.0  # safe coerce, NaN → 0
        _saved_mat_total  = int(sum(_dn(r.get("total"))  for r in (saved_mat  or [])))
        _saved_cons_total = int(sum(_dn(r.get("Total"))  for r in (saved_cons or [])))
        all_products[f"{selected_anchor} ({comp})"] = {
            "G": G_new, "D": D_new, "area": area, "L": L, "W": W, "H": H, "e": e,
            "c_count": int(anchor_row.get("c_value") or 0),
            "C": compute_C(int(anchor_row.get("c_value") or 0), rules) if anchor_row.get("c_value") else None,
            "x_active": {},
            "mat_df":   mat_df  if isinstance(mat_df,  pd.DataFrame) else pd.DataFrame(),
            "cons_df":  cons_df if isinstance(cons_df, pd.DataFrame) else pd.DataFrame(),
            "mat_total":  _saved_mat_total,
            "cons_total": _saved_cons_total,
            "total":      _saved_mat_total + _saved_cons_total,
            "expected_comp": comp,
        }

    st.divider()

    # ── Extrapolation table — all products in profile, grouped by level ──────
    st.markdown('<div class="sec-label" style="margin-bottom:0.5rem;">EXTRAPOLACIÓN — TODOS LOS PRODUCTOS DEL PERFIL</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#8b949e;font-size:0.8rem;">Costo estimado para cada producto usando '
        'factor_escala = área_producto / área_ancla. '
        'Requiere BOM del ancla guardado.</p>',
        unsafe_allow_html=True
    )

    extrap_rows = []
    for comp in ["C1", "C2", "C3"]:
        bucket_df = _load_bucket(profile_key, comp)
        if bucket_df.empty:
            continue
        anchor_handle = (rules["profiles"].get(profile_key, {}).get("anchors") or {}).get(comp)
        bench = (rules["profiles"].get(profile_key, {}).get("cost_benchmarks") or {}).get(comp, {})
        anchor_mat  = bench.get("material_total_clp")
        anchor_cons = bench.get("consumables_total_clp")
        anchor_dims = bench.get("dims", {})
        aL = anchor_dims.get("L_mm", 0) or 0
        aW = anchor_dims.get("W_mm", 0) or 0
        aH = anchor_dims.get("H_mm", 0) or 0
        anchor_area = 2*(aL+aW)*aH + aL*aW if aL and aW else None

        for _, row in bucket_df.iterrows():
            L = row.get("dim_l_mm") or 0
            W = row.get("dim_w_mm") or 0
            H = row.get("dim_h_mm") or 0
            area = 2*(L+W)*H + L*W if L and W else None
            factor = round(area / anchor_area, 3) if (area and anchor_area) else None
            mat_est  = round(anchor_mat  * factor) if (anchor_mat  and factor and math.isfinite(anchor_mat))  else None
            cons_est = round(anchor_cons * factor) if (anchor_cons and factor and math.isfinite(anchor_cons)) else None
            total_est = (mat_est or 0) + (cons_est or 0)

            extrap_rows.append({
                "Nivel":   comp,
                "Handle":  row["handle"],
                "⭐ Ancla": "⭐" if row["handle"] == anchor_handle else "",
                "G": row.get("G"),
                "D": row.get("D"),
                "Área m²": f"{area/1e6:.3f}" if area else "—",
                "factor_escala": factor,
                "Mat. est.": mat_est,
                "Cons. est.": cons_est,
                "Total est. $": total_est if total_est > 0 else None,
                "BOM real": "✅" if (row.get("bom_materials","[]") not in [None,"[]","[{}]",""] ) else "—",
            })

    if extrap_rows:
        ex_df = pd.DataFrame(extrap_rows)
        st.dataframe(
            ex_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Mat. est.":    st.column_config.NumberColumn("Mat. est. $", format="%.0f"),
                "Cons. est.":   st.column_config.NumberColumn("Cons. est. $", format="%.0f"),
                "Total est. $": st.column_config.NumberColumn("Total est. $", format="%.0f"),
                "factor_escala":st.column_config.NumberColumn("f_escala", format="%.3f"),
            }
        )
    else:
        st.info("Sin productos en DB para este perfil. Importa el CSV primero.")

    return all_products


# ─── Main ──────────────────────────────────────────────────────────────────────

def main(key_suffix: str = ""):
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<h2 style="border-bottom:1px solid #21262d;padding-bottom:0.5rem;">'
        '⚖️ Calibración de Perfil</h2>',
        unsafe_allow_html=True
    )

    rules = load_rules()

    # Profile selector
    available_profiles = list(rules["profiles"].keys())
    col_prof, col_info = st.columns([2, 3])
    with col_prof:
        profile_key = st.selectbox("Perfil proceso", available_profiles,
                                   index=available_profiles.index("p-basurero-cil") if "p-basurero-cil" in available_profiles else 0,
                                   key=f"cal_profile_key{key_suffix}")
    profile_rules = rules["profiles"][profile_key]
    with col_info:
        primary = ", ".join(profile_rules.get("primary_drivers", []))
        c_driver = profile_rules.get("c_driver") or "no disponible en DB"
        st.markdown(
            f'<div class="cal-card" style="margin-top:0.3rem;">'
            f'<div class="sec-label">DRIVERS DECLARADOS</div>'
            f'<div style="font-size:0.88rem;color:#cdd9e5;">Primarios: <b style="color:#79c0ff;">{primary}</b>'
            f'  ·  Driver C: <b style="color:#79c0ff;">{c_driver}</b></div>'
            f'<div style="font-size:0.78rem;color:#768390;margin-top:0.2rem;">'
            f'{profile_rules.get("description","")}</div></div>',
            unsafe_allow_html=True
        )

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📦 Ingreso de Costos",
        "🎯 Sistema de Puntos",
        "📊 Análisis C2 → C3",
        "⚙️ Desglose HH",
        "🔧 Templates",
        "🔮 Extrapolación",
        "💾 Guardar Hallazgos",
        "🔬 ICM",
    ])

    # Default dims from PROCESS_RULES benchmarks
    benchmarks = profile_rules.get("cost_benchmarks", {})
    c2_bench = benchmarks.get("C2", {})
    c3_bench = benchmarks.get("C3", {})

    c2_dims_def = [
        c2_bench.get("dims", {}).get("L_mm", 470),
        c2_bench.get("dims", {}).get("W_mm", 240),
        c2_bench.get("dims", {}).get("H_mm", 1020),
        c2_bench.get("dims", {}).get("espesor_mm", 1.0),
    ]
    c3_dims_def = [
        c3_bench.get("dims", {}).get("L_mm", 1350),
        c3_bench.get("dims", {}).get("W_mm", 600),
        c3_bench.get("dims", {}).get("H_mm", 875),
        c3_bench.get("dims", {}).get("espesor_mm", 1.5),
    ]

    with tab1:
        all_products_from_tab1 = render_bom_entry(rules, profile_key)
        st.session_state[f"products_{profile_key}"] = all_products_from_tab1

    products = st.session_state.get(f"products_{profile_key}", {})
    # Re-attach expected_comp if loaded from state
    for name, p in products.items():
        if "expected_comp" not in p:
            p["expected_comp"] = "C2" if "c2" in name.lower() else ("C3" if "c3" in name.lower() else "C1")

    with tab2:
        render_point_system(products, rules, profile_key)

    with tab3:
        render_cost_analysis(products)

    with tab4:
        render_process_breakdown(products, rules, profile_key)

    with tab5:
        render_templates_editor(rules)

    with tab6:
        c2_prod = next((p for p in products.values() if p.get("expected_comp") == "C2"), None)
        c2_name_t6 = next((n for n, p in products.items() if p.get("expected_comp") == "C2"), "C2")
        if c2_prod:
            render_extrapolation(c2_prod, c2_name_t6, "C2", rules, profile_key)
        else:
            st.info("Ingresa datos en el tab 'Ingreso de Costos' para activar la extrapolación.")

    with tab7:
        render_save_findings(products, rules, profile_key)

    with tab8:
        render_icm(rules, profile_key)


if __name__ == "__main__":
    main()
