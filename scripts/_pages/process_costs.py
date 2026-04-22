"""
process_costs.py — Dulox Process Cost Thresholds Editor
=========================================================
Three tabs:
  1. HH Rates       — CLP/hora per process (mano de obra)
  2. Templates       — T_setup / T_exec / n_ops per process per complexity level
  3. Consumibles     — Standard consumable catalog per (process, level):
                       quantities + unit prices that pre-populate BOM forms

All data saved to PROCESS_RULES.json — single source of truth.
Python constants in calibration.py serve as fallback if JSON key is missing.

Run:  streamlit run scripts/review.py  (loaded as a Streamlit page)
"""

import json
import sys
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# ─── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
<style>
html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"] { background-color:#0d1117 !important; color:#e6edf3 !important; }
[data-testid="stSidebar"] { background-color:#161b22 !important; border-right:1px solid #30363d; }
[data-testid="stSidebar"] * { color:#c9d1d9 !important; }
h1,h2,h3 { color:#f0f6fc !important; }
.pc-card { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.pc-card-blue { background:#0d2137; border:1px solid #1f6feb; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.sec-label { font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:#768390; margin-bottom:0.3rem; }
.badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:700; }
.badge-c1 { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-c2 { background:#2d1b00; color:#e3b341; border:1px solid #9e6a03; }
.badge-c3 { background:#3d0c0c; color:#f85149; border:1px solid #da3633; }
hr { border-color:#21262d !important; }
[data-testid="stTabs"] [data-testid="stTab"] { color:#8b949e !important; }
[data-testid="stTabs"] [aria-selected="true"] { color:#58a6ff !important; border-bottom:2px solid #58a6ff; }
[data-testid="stDataFrameResizable"] { border:1px solid #30363d; border-radius:8px; }
[data-testid="stExpander"] { background:#161b22 !important; border:1px solid #30363d !important; border-radius:8px !important; }
</style>
"""

# ─── Defaults (mirrors calibration.py constants — used if PROCESS_RULES.json has no override) ──

HH_RATES_DEFAULT = {
    "soldadura":      9000,
    "pulido":         7500,
    "cilindrado":     7500,
    "plegado":        7000,
    "corte_manual":   6500,
    "armado_trazado": 6500,
    "laser":          6500,
    "grabado_laser":  8000,
    "pintura":        6000,
    "refrigeracion":  8500,
    "qc":             6000,
}

PROCESS_TEMPLATES_DEFAULT = {
    "armado_trazado": {
        "drivers": ["G", "X"], "score_thresholds": {"C1":[1,2],"C2":[3,4],"C3":[5,99]},
        "descriptions": {"C1":"Layout simple","C2":"Marcado perimetral, 2–3 subconjuntos","C3":"Layout complejo, múltiples subconjuntos"},
        "C1":{"T_setup_min":7,"T_exec_min":30,"n_ops":1},
        "C2":{"T_setup_min":15,"T_exec_min":60,"n_ops":1},
        "C3":{"T_setup_min":25,"T_exec_min":90,"n_ops":1},
    },
    "corte_manual": {
        "drivers": ["G", "D"], "score_thresholds": {"C1":[2,3],"C2":[4,4],"C3":[5,99]},
        "descriptions": {"C1":"Pieza pequeña ≤1.5mm","C2":"Pieza mediana o 1.5–2mm","C3":"Pieza grande o >2mm"},
        "C1":{"T_setup_min":7,"T_exec_min":30,"n_ops":1},
        "C2":{"T_setup_min":12,"T_exec_min":45,"n_ops":2},
        "C3":{"T_setup_min":18,"T_exec_min":60,"n_ops":2},
    },
    "laser": {
        "drivers": ["D", "X"], "score_thresholds": {"C1":[1,2],"C2":[3,4],"C3":[5,99]},
        "descriptions": {"C1":"≤1.5mm, DXF listo","C2":"1.5–2mm o DXF requiere prep","C3":"Complejo o >2mm — externo"},
        "C1":{"T_setup_min":7,"T_exec_min":10,"n_ops":1},
        "C2":{"T_setup_min":30,"T_exec_min":35,"n_ops":1},
        "C3":{"T_setup_min":45,"T_exec_min":0,"n_ops":0},
    },
    "plegado": {
        "drivers": ["G","D","C"], "score_thresholds": {"C1":[3,4],"C2":[5,6],"C3":[7,99]},
        "descriptions": {"C1":"1–2 dobleces, ≤1.5mm","C2":"3–4 dobleces o pieza grande","C3":"5+ dobleces o >2mm"},
        "C1":{"T_setup_min":10,"T_exec_min":30,"n_ops":1},
        "C2":{"T_setup_min":17,"T_exec_min":50,"n_ops":2},
        "C3":{"T_setup_min":25,"T_exec_min":80,"n_ops":3},
    },
    "cilindrado": {
        "drivers": ["D","G"], "score_thresholds": {"C1":[2,2],"C2":[3,4],"C3":[5,99]},
        "descriptions": {"C1":"Fino, 1 persona, 1 pasada","C2":"Moderado, 2 personas","C3":"Grueso o grande, 4 personas"},
        "C1":{"T_setup_min":5,"T_exec_min":20,"n_ops":1},
        "C2":{"T_setup_min":15,"T_exec_min":60,"n_ops":2},
        "C3":{"T_setup_min":30,"T_exec_min":180,"n_ops":4},
    },
    "soldadura": {
        "drivers": ["C","X"], "score_thresholds": {"C1":[0,1],"C2":[2,3],"C3":[4,99]},
        "descriptions": {"C1":"Pocas uniones, simple","C2":"Uniones visibles, mecanismo","C3":"Emplantillado TIG, múltiples compartimientos"},
        "C1":{"T_setup_min":5,"T_exec_min":40,"n_ops":1},
        "C2":{"T_setup_min":15,"T_exec_min":60,"n_ops":1},
        "C3":{"T_setup_min":30,"T_exec_min":90,"n_ops":1},
    },
    "pulido": {
        "drivers": ["G","X"], "score_thresholds": {"C1":[1,2],"C2":[3,4],"C3":[5,99]},
        "descriptions": {"C1":"1 pasada, plano","C2":"Rincones o curva, cepillado fino","C3":"3 pasadas, acabado espejo"},
        "C1":{"T_setup_min":0,"T_exec_min":60,"n_ops":1},
        "C2":{"T_setup_min":0,"T_exec_min":90,"n_ops":2},
        "C3":{"T_setup_min":0,"T_exec_min":300,"n_ops":2},
    },
    "qc": {
        "drivers": ["C","X"], "score_thresholds": {"C1":[0,2],"C2":[3,4],"C3":[5,99]},
        "descriptions": {"C1":"Visual + embalaje","C2":"Dimensional + reforzado","C3":"Fotográfico + especial"},
        "C1":{"T_setup_min":5,"T_exec_min":15,"n_ops":1},
        "C2":{"T_setup_min":10,"T_exec_min":30,"n_ops":1},
        "C3":{"T_setup_min":15,"T_exec_min":60,"n_ops":1},
    },
    "grabado_laser": {
        "drivers": ["G"], "score_thresholds": {"C1":[1,1],"C2":[2,2],"C3":[3,99]},
        "descriptions": {"C1":"Grabado simple, 1 elemento","C2":"Grabado múltiple o decorativo","C3":"Grabado especial — cotizar"},
        "C1":{"T_setup_min":10,"T_exec_min":15,"n_ops":1},
        "C2":{"T_setup_min":20,"T_exec_min":30,"n_ops":1},
        "C3":{"T_setup_min":30,"T_exec_min":0,"n_ops":0},
    },
    "refrigeracion": {
        "drivers": ["C","D"], "score_thresholds": {"C1":[2,3],"C2":[4,4],"C3":[5,99]},
        "descriptions": {"C1":"Sistema simple, 1 circuito","C2":"2 circuitos o evaporadores","C3":"Sistema complejo industrial"},
        "C1":{"T_setup_min":30,"T_exec_min":120,"n_ops":2},
        "C2":{"T_setup_min":60,"T_exec_min":240,"n_ops":2},
        "C3":{"T_setup_min":120,"T_exec_min":480,"n_ops":3},
    },
    "pintura": {
        "drivers": ["X"], "score_thresholds": {"C1":[0,1],"C2":[2,2],"C3":[3,99]},
        "descriptions": {"C1":"Sin pintura o básico","C2":"Pintura estándar","C3":"Pintura especial multicapa"},
        "C1":{"T_setup_min":0,"T_exec_min":0,"n_ops":0},
        "C2":{"T_setup_min":15,"T_exec_min":60,"n_ops":1},
        "C3":{"T_setup_min":30,"T_exec_min":120,"n_ops":2},
    },
}

# ─── Default consumables catalog per (process, level) ──────────────────────────
# Format: { process: { level: [ {producto, unidad, cantidad, precio_u} ] } }

CONSUMABLES_DEFAULT = {
    "soldadura": {
        "C1": [
            {"Producto": "Tungsteno 3/32", "Unidad": "u", "Cantidad": 0.5, "Precio_u": 2790},
            {"Producto": "Argón", "Unidad": "L", "Cantidad": 128, "Precio_u": 7},
        ],
        "C2": [
            {"Producto": "Tungsteno 3/32", "Unidad": "u", "Cantidad": 1, "Precio_u": 2790},
            {"Producto": "Argón", "Unidad": "L", "Cantidad": 192, "Precio_u": 7},
        ],
        "C3": [
            {"Producto": "Tungsteno 3/32", "Unidad": "u", "Cantidad": 1, "Precio_u": 2790},
            {"Producto": "Argón", "Unidad": "L", "Cantidad": 256, "Precio_u": 7},
        ],
    },
    "pulido": {
        "C1": [
            {"Producto": "Disco Desbaste 4.5\"", "Unidad": "u", "Cantidad": 1, "Precio_u": 2500},
            {"Producto": "Disco Lija Grano 80", "Unidad": "u", "Cantidad": 1, "Precio_u": 460},
            {"Producto": "Grata Roja", "Unidad": "u", "Cantidad": 1, "Precio_u": 5800},
            {"Producto": "Huaipe", "Unidad": "u", "Cantidad": 0.5, "Precio_u": 3500},
        ],
        "C2": [
            {"Producto": "Disco Desbaste 4.5\"", "Unidad": "u", "Cantidad": 2, "Precio_u": 2500},
            {"Producto": "Disco Lija Grano 80", "Unidad": "u", "Cantidad": 2, "Precio_u": 460},
            {"Producto": "Grata Roja", "Unidad": "u", "Cantidad": 2, "Precio_u": 5800},
            {"Producto": "Disco Traslapado", "Unidad": "u", "Cantidad": 1, "Precio_u": 1681},
            {"Producto": "Huaipe", "Unidad": "u", "Cantidad": 1, "Precio_u": 3500},
            {"Producto": "Pasta de pulir", "Unidad": "u", "Cantidad": 1, "Precio_u": 3500},
        ],
        "C3": [
            {"Producto": "Disco Desbaste 4.5\"", "Unidad": "u", "Cantidad": 2, "Precio_u": 2500},
            {"Producto": "Disco Lija Grano 80", "Unidad": "u", "Cantidad": 2, "Precio_u": 460},
            {"Producto": "Grata Roja", "Unidad": "u", "Cantidad": 2, "Precio_u": 5800},
            {"Producto": "Disco Traslapado", "Unidad": "u", "Cantidad": 1, "Precio_u": 1681},
            {"Producto": "Disco Multifinic", "Unidad": "u", "Cantidad": 1, "Precio_u": 32400},
            {"Producto": "Traslapos pequeños 50x30", "Unidad": "u", "Cantidad": 1, "Precio_u": 1100},
            {"Producto": "Pasta de pulir", "Unidad": "u", "Cantidad": 1, "Precio_u": 3500},
            {"Producto": "Spray limpiador inox", "Unidad": "u", "Cantidad": 1, "Precio_u": 8072},
            {"Producto": "Huaipe", "Unidad": "u", "Cantidad": 1, "Precio_u": 3500},
        ],
    },
    "corte_manual": {
        "C1": [{"Producto": "Disco de corte 4.5\"", "Unidad": "u", "Cantidad": 1, "Precio_u": 548}],
        "C2": [
            {"Producto": "Disco de corte 4.5\"", "Unidad": "u", "Cantidad": 2, "Precio_u": 548},
            {"Producto": "Lija Metal Grano 80", "Unidad": "u", "Cantidad": 1, "Precio_u": 592},
        ],
        "C3": [
            {"Producto": "Disco de corte 4.5\"", "Unidad": "u", "Cantidad": 3, "Precio_u": 548},
            {"Producto": "Lija Metal Grano 80", "Unidad": "u", "Cantidad": 2, "Precio_u": 592},
        ],
    },
    "laser": {
        "C1": [{"Producto": "Preparación DXF", "Unidad": "u", "Cantidad": 0, "Precio_u": 0}],
        "C2": [{"Producto": "Preparación DXF especial", "Unidad": "u", "Cantidad": 1, "Precio_u": 5000}],
        "C3": [{"Producto": "Cotización externa laser", "Unidad": "u", "Cantidad": 1, "Precio_u": 0}],
    },
    "armado_trazado": {
        "C1": [{"Producto": "Disco de corte 4.5\"", "Unidad": "u", "Cantidad": 1, "Precio_u": 548}],
        "C2": [{"Producto": "Disco de corte 4.5\"", "Unidad": "u", "Cantidad": 1, "Precio_u": 548}],
        "C3": [{"Producto": "Disco de corte 4.5\"", "Unidad": "u", "Cantidad": 2, "Precio_u": 548}],
    },
    "plegado": {
        "C1": [], "C2": [], "C3": [],
    },
    "cilindrado": {
        "C1": [{"Producto": "Lija Metal Grano 80", "Unidad": "u", "Cantidad": 1, "Precio_u": 592}],
        "C2": [{"Producto": "Lija Metal Grano 80", "Unidad": "u", "Cantidad": 2, "Precio_u": 592}],
        "C3": [
            {"Producto": "Lija Metal Grano 80", "Unidad": "u", "Cantidad": 4, "Precio_u": 592},
            {"Producto": "Disco Desbaste 4.5\"", "Unidad": "u", "Cantidad": 1, "Precio_u": 2500},
        ],
    },
    "qc": {
        "C1": [],
        "C2": [{"Producto": "Cinta embalaje", "Unidad": "u", "Cantidad": 1, "Precio_u": 1200}],
        "C3": [
            {"Producto": "Cinta embalaje reforzada", "Unidad": "u", "Cantidad": 2, "Precio_u": 1800},
            {"Producto": "Film stretch", "Unidad": "m", "Cantidad": 3, "Precio_u": 400},
        ],
    },
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

from db import load_rules, save_rules

def get_hh_rates(rules: dict) -> dict:
    return rules.get("hh_rates", HH_RATES_DEFAULT)

def get_process_templates(rules: dict) -> dict:
    saved = rules.get("process_templates", {})
    result = dict(PROCESS_TEMPLATES_DEFAULT)
    for proc, s in saved.items():
        if proc in result:
            merged = dict(result[proc])
            for k in ["score_thresholds","descriptions","C1","C2","C3","drivers"]:
                if k in s:
                    merged[k] = s[k]
            result[proc] = merged
        else:
            result[proc] = s
    return result

def get_consumables_catalog(rules: dict) -> dict:
    saved = rules.get("process_consumables", {})
    result = dict(CONSUMABLES_DEFAULT)
    for proc, levels in saved.items():
        if proc not in result:
            result[proc] = {}
        result[proc].update(levels)
    return result

def fmt_clp(v):
    if v is None:
        return "—"
    return f"${int(v):,}".replace(",", ".")

# ─── Tab 1: HH Rates ──────────────────────────────────────────────────────────

def render_hh_rates(rules: dict):
    st.markdown(
        '<p style="color:#8b949e;font-size:0.85rem;">'
        'Costo de mano de obra por hora (CLP) para cada proceso. '
        'Se usa en el cálculo: (T_setup + T_exec) ÷ 60 × HH_rate × n_ops.</p>',
        unsafe_allow_html=True
    )

    current = get_hh_rates(rules)
    all_procs = sorted(set(list(HH_RATES_DEFAULT.keys()) + list(current.keys())))

    rows = [{"Proceso": p, "CLP/hora": current.get(p, HH_RATES_DEFAULT.get(p, 0))} for p in all_procs]

    _hh_skey = "df_hh_editor"
    _hh_hkey = "hash_hh_editor"
    _hh_hash = hash(str(rows))
    if st.session_state.get(_hh_hkey) != _hh_hash or _hh_skey not in st.session_state:
        st.session_state[_hh_skey] = pd.DataFrame(rows)
        st.session_state[_hh_hkey] = _hh_hash

    edited = st.data_editor(
        st.session_state[_hh_skey],
        column_config={
            "Proceso": st.column_config.TextColumn("Proceso", disabled=True, width="medium"),
            "CLP/hora": st.column_config.NumberColumn(
                "CLP / hora", min_value=0, max_value=100000, step=500,
                format="$ %d", width="medium",
                help="Tarifa real de mano de obra incluyendo leyes sociales"
            ),
        },
        use_container_width=False,
        hide_index=True,
        num_rows="dynamic",
        key="hh_editor",
    )
    st.session_state[_hh_skey] = edited  # write back so edits survive rerun

    # Reference card
    st.markdown(
        '<div class="pc-card-blue" style="margin-top:0.8rem;">'
        '<div class="sec-label">EJEMPLO DE CÁLCULO</div>'
        '<div style="font-size:0.82rem;color:#cdd9e5;">'
        'Soldadura C2: T_setup=15min + T_exec=60min = 75min = 1.25 HH × '
        + fmt_clp(current.get("soldadura", 9000))
        + '/HH × 1 ops = <b>'
        + fmt_clp(round(75/60 * current.get("soldadura", 9000)))
        + '</b></div></div>',
        unsafe_allow_html=True
    )

    if st.button("💾 Guardar tarifas HH en PROCESS_RULES.json", type="primary"):
        new_rates = {row["Proceso"]: int(row["CLP/hora"]) for _, row in edited.iterrows() if row["Proceso"]}
        rules["hh_rates"] = new_rates
        rules["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        save_rules(rules)
        st.success("✅ Tarifas HH guardadas.")


# ─── Tab 2: Process Templates ─────────────────────────────────────────────────

def render_templates(rules: dict):
    st.markdown(
        '<p style="color:#8b949e;font-size:0.85rem;">'
        'Tiempos de referencia por proceso y nivel de complejidad. '
        'T_exec_min es el tiempo BASE para el producto ancla (factor_escala=1). '
        'T_setup no escala con tamaño. n_ops = número de operarios.</p>',
        unsafe_allow_html=True
    )

    templates = get_process_templates(rules)
    all_procs = sorted(templates.keys())
    changed = {}

    for proc in all_procs:
        tmpl = templates[proc]
        drivers_str = " + ".join(tmpl.get("drivers", []))

        with st.expander(
            f"🔧 {proc}  ·  drivers: {drivers_str or '—'}",
            expanded=False
        ):
            # ── Driver selector ──────────────────────────────────────────────
            DRIVER_OPTIONS = ["G", "D", "C", "X"]
            DRIVER_LABELS  = {"G": "G — Geometría", "D": "D — Densidad/Espesor",
                              "C": "C — Componentes", "X": "X — Características"}
            selected_drivers = st.multiselect(
                "Drivers de complejidad",
                options=DRIVER_OPTIONS,
                default=tmpl.get("drivers", []),
                format_func=lambda k: DRIVER_LABELS[k],
                key=f"drivers_{proc}",
                help="Selecciona qué drivers suman al score de complejidad para este proceso.",
            )

            st.divider()
            cols = st.columns([2, 1, 1, 1, 1, 1, 1])
            cols[0].markdown('<div class="sec-label">NIVEL</div>', unsafe_allow_html=True)
            cols[1].markdown('<div class="sec-label">T_setup (min)</div>', unsafe_allow_html=True)
            cols[2].markdown('<div class="sec-label">T_exec base (min)</div>', unsafe_allow_html=True)
            cols[3].markdown('<div class="sec-label">n_ops</div>', unsafe_allow_html=True)
            cols[4].markdown('<div class="sec-label">Score lo</div>', unsafe_allow_html=True)
            cols[5].markdown('<div class="sec-label">Score hi</div>', unsafe_allow_html=True)
            cols[6].markdown('<div class="sec-label">Descripción</div>', unsafe_allow_html=True)

            new_levels = {}
            new_thresholds = {}
            new_descs = {}

            for lvl in ["C1", "C2", "C3"]:
                ldata = tmpl.get(lvl, {})
                thresh = tmpl.get("score_thresholds", {}).get(lvl, [0, 99])
                desc   = tmpl.get("descriptions", {}).get(lvl, "")

                badge_html = {"C1":"badge-c1","C2":"badge-c2","C3":"badge-c3"}.get(lvl,"")
                row_cols = st.columns([2, 1, 1, 1, 1, 1, 1])
                row_cols[0].markdown(f'<span class="badge {badge_html}">{lvl}</span>', unsafe_allow_html=True)

                t_setup = row_cols[1].number_input(
                    f"setup {proc} {lvl}", value=int(ldata.get("T_setup_min", 0)),
                    min_value=0, step=5, key=f"tset_{proc}_{lvl}",
                    label_visibility="collapsed"
                )
                t_exec = row_cols[2].number_input(
                    f"exec {proc} {lvl}", value=int(ldata.get("T_exec_min", 0)),
                    min_value=0, step=5, key=f"texec_{proc}_{lvl}",
                    label_visibility="collapsed"
                )
                n_ops = row_cols[3].number_input(
                    f"ops {proc} {lvl}", value=int(ldata.get("n_ops", 1)),
                    min_value=0, max_value=10, step=1, key=f"nops_{proc}_{lvl}",
                    label_visibility="collapsed"
                )
                sc_lo = row_cols[4].number_input(
                    f"lo {proc} {lvl}", value=int(thresh[0]),
                    min_value=0, max_value=30, key=f"lo_{proc}_{lvl}",
                    label_visibility="collapsed"
                )
                sc_hi = row_cols[5].number_input(
                    f"hi {proc} {lvl}", value=int(thresh[1]),
                    min_value=0, max_value=99, key=f"hi_{proc}_{lvl}",
                    label_visibility="collapsed"
                )
                new_desc = row_cols[6].text_input(
                    f"desc {proc} {lvl}", value=desc,
                    key=f"desc_{proc}_{lvl}",
                    label_visibility="collapsed"
                )

                new_levels[lvl]     = {"T_setup_min": t_setup, "T_exec_min": t_exec, "n_ops": n_ops}
                new_thresholds[lvl] = [sc_lo, sc_hi]
                new_descs[lvl]      = new_desc

            changed[proc] = {
                "drivers":          selected_drivers,
                "score_thresholds": new_thresholds,
                "descriptions":     new_descs,
                "C1": new_levels["C1"],
                "C2": new_levels["C2"],
                "C3": new_levels["C3"],
            }

            # HH cost summary row
            hh = get_hh_rates(rules)
            rate = hh.get(proc, 6500)
            st.markdown(
                '<div style="display:flex;gap:1.5rem;margin-top:0.5rem;">',
                unsafe_allow_html=True
            )
            cost_cols = st.columns(3)
            for i, lvl in enumerate(["C1","C2","C3"]):
                nl = new_levels[lvl]
                total_min = nl["T_setup_min"] + nl["T_exec_min"]
                cost = round(total_min / 60 * rate * nl["n_ops"])
                badge_cls = ["badge-c1","badge-c2","badge-c3"][i]
                cost_cols[i].markdown(
                    f'<div class="pc-card" style="padding:0.4rem 0.7rem;">'
                    f'<span class="badge {badge_cls}">{lvl}</span>'
                    f' <span style="color:#cdd9e5;font-size:0.88rem;font-weight:600;">'
                    f'{fmt_clp(cost)}</span>'
                    f'<span style="color:#768390;font-size:0.72rem;"> ({total_min}min × {nl["n_ops"]} ops)</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    if st.button("💾 Guardar templates en PROCESS_RULES.json", type="primary", key="save_templates"):
        if "process_templates" not in rules:
            rules["process_templates"] = {}
        rules["process_templates"].update(changed)
        rules["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        save_rules(rules)
        st.success("✅ Templates guardados. calibration.py los usará automáticamente.")


# ─── Tab 3: Standard Consumables ──────────────────────────────────────────────

def render_consumables(rules: dict):
    st.markdown(
        '<p style="color:#8b949e;font-size:0.85rem;">'
        'Consumibles estándar por proceso y nivel. '
        'Estos valores se pre-cargan al crear un BOM en Calibración. '
        'Edita cantidades y precios unitarios para cada proceso/nivel.</p>',
        unsafe_allow_html=True
    )

    catalog = get_consumables_catalog(rules)
    all_procs = sorted(catalog.keys())

    COL_CFG = {
        "Producto": st.column_config.TextColumn("Producto", width="large"),
        "Unidad":   st.column_config.SelectboxColumn("Unidad", options=["u","kg","L","m","ml","hr"], width="small"),
        "Cantidad": st.column_config.NumberColumn("Cant.",     min_value=0, step=0.001, format="%.3f", width="small"),
        "Precio_u": st.column_config.NumberColumn("Precio u. $", min_value=0, step=1,  format="$ %.0f", width="medium"),
    }

    for proc in all_procs:
        with st.expander(f"🔩 {proc}", expanded=False):
            new_levels = {}

            for lvl in ["C1", "C2", "C3"]:
                badge_cls = {"C1":"badge-c1","C2":"badge-c2","C3":"badge-c3"}[lvl]
                st.markdown(
                    f'<span class="badge {badge_cls}" style="margin:0.6rem 0 0.3rem 0;display:inline-block;">{lvl}</span>',
                    unsafe_allow_html=True
                )

                default_rows = catalog.get(proc, {}).get(lvl, [])
                # Strip any stale Total column from saved data before rendering
                df_rows = [
                    {"Producto": r.get("Producto",""), "Unidad": r.get("Unidad","u"),
                     "Cantidad": r.get("Cantidad", 0), "Precio_u": r.get("Precio_u", 0)}
                    for r in default_rows
                ] if default_rows else [{"Producto": "", "Unidad": "u", "Cantidad": 0, "Precio_u": 0}]

                _cons_ekey = f"cons_{proc}_{lvl}"
                _cons_skey = f"df_{_cons_ekey}"
                _cons_hkey = f"hash_{_cons_ekey}"
                _cons_hash = hash(str(df_rows))
                if st.session_state.get(_cons_hkey) != _cons_hash or _cons_skey not in st.session_state:
                    st.session_state[_cons_skey] = pd.DataFrame(df_rows)
                    st.session_state[_cons_hkey] = _cons_hash

                edited = st.data_editor(
                    st.session_state[_cons_skey],
                    key=_cons_ekey,
                    use_container_width=True,
                    num_rows="dynamic",
                    column_config=COL_CFG,
                    hide_index=True,
                )
                st.session_state[_cons_skey] = edited  # write back so edits survive rerun

                if isinstance(edited, pd.DataFrame):
                    cant  = edited["Cantidad"].fillna(0)
                    price = edited["Precio_u"].fillna(0)
                    total = int((cant * price).sum())
                    # Save with computed Total for downstream use
                    rows_to_save = edited.copy()
                    rows_to_save["Total"] = (cant * price).round().astype(int)
                    new_levels[lvl] = rows_to_save.to_dict("records")
                else:
                    total = 0
                    new_levels[lvl] = df_rows

                st.markdown(
                    f'<div style="font-size:0.8rem;color:#3fb950;text-align:right;margin-bottom:0.6rem;">'
                    f'Total {lvl}: <b>{fmt_clp(total)}</b></div>',
                    unsafe_allow_html=True
                )

            if st.button(f"💾 Guardar {proc}", key=f"save_cons_{proc}", type="primary"):
                if "process_consumables" not in rules:
                    rules["process_consumables"] = {}
                rules["process_consumables"][proc] = new_levels
                rules["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
                save_rules(rules)
                st.success(f"✅ Consumibles de {proc} guardados.")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    try:
        st.set_page_config(
            page_title="Dulox — Costos de Proceso",
            page_icon="⚙️",
            layout="wide",
        )
    except Exception:
        pass
    st.markdown(CSS, unsafe_allow_html=True)

    rules = load_rules()

    st.markdown(
        '<h2 style="border-bottom:1px solid #21262d;padding-bottom:0.5rem;">'
        '⚙️ Costos de Proceso — HH / Templates / Consumibles</h2>',
        unsafe_allow_html=True
    )

    with st.sidebar:
        hh = get_hh_rates(rules)
        tmpl = get_process_templates(rules)
        cons = get_consumables_catalog(rules)

        st.markdown(
            f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:0.8rem;">'
            f'<div class="sec-label">ESTADO</div>'
            f'<div style="font-size:0.82rem;color:#cdd9e5;">{len(hh)} procesos con HH rate</div>'
            f'<div style="font-size:0.82rem;color:#cdd9e5;">{len(tmpl)} templates definidos</div>'
            f'<div style="font-size:0.82rem;color:#cdd9e5;">{len(cons)} catálogos de consumibles</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.divider()
        if st.button("🔄 Recargar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    tab1, tab2, tab3 = st.tabs([
        "💰 Tarifas HH",
        "⏱️ Templates de Proceso",
        "🔩 Consumibles Estándar",
    ])

    with tab1:
        render_hh_rates(rules)

    with tab2:
        render_templates(rules)

    with tab3:
        render_consumables(rules)


main()
