"""
data_input.py — Dulox Mass Data Input
======================================
Three tabs per profile:
  1. Drivers C + X  — bulk-edit c_value and X flags for every product in the profile.
                      Live complexity score recalculation shows impact immediately.
  2. Procesos por Nivel — define which processes are active at C1 / C2 / C3 for this profile.
  3. Anclas           — designate one anchor product per complexity level.

Run:  streamlit run scripts/review.py  (this file is loaded as a page)
"""

import json
import sys
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import load_rules, save_rules, load_profile_products as _load_profile_products_raw, save_product_batch, save_anchor as _db_save_anchor, get_sb

# ─── CSS (dark, matches review.py) ────────────────────────────────────────────

CSS = """
<style>
html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"] { background-color:#0d1117 !important; color:#e6edf3 !important; }
[data-testid="stSidebar"] { background-color:#161b22 !important; border-right:1px solid #30363d; }
[data-testid="stSidebar"] * { color:#c9d1d9 !important; }
h1,h2,h3 { color:#f0f6fc !important; }
.di-card {
    background:#161b22; border:1px solid #30363d; border-radius:10px;
    padding:1rem 1.2rem; margin-bottom:0.8rem;
}
.di-card-blue  { background:#0d2137; border:1px solid #1f6feb; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.di-card-green { background:#0d3321; border:1px solid #238636; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.di-card-amber { background:#2d1b00; border:1px solid #9e6a03; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.sec-label { font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:#768390; margin-bottom:0.3rem; }
.badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:700; }
.badge-c1 { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-c2 { background:#2d1b00; color:#e3b341; border:1px solid #9e6a03; }
.badge-c3 { background:#3d0c0c; color:#f85149; border:1px solid #da3633; }
hr { border-color:#21262d !important; }
[data-testid="stTabs"] [data-testid="stTab"] { color:#8b949e !important; }
[data-testid="stTabs"] [aria-selected="true"] { color:#58a6ff !important; border-bottom:2px solid #58a6ff; }
[data-testid="stDataFrameResizable"] { border:1px solid #30363d; border-radius:8px; }
</style>
"""

KNOWN_PROCESSES = [
    "laser", "corte_manual", "armado_trazado", "plegado", "cilindrado",
    "soldadura", "pulido", "qc", "grabado_laser", "refrigeracion", "pintura",
]

C_DRIVER_LABELS = {
    "num_componentes": "Componentes",
    "num_quemadores":  "Quemadores",
    "num_tazas":       "Tazas",
    "num_niveles":     "Niveles",
    "num_varillas":    "Varillas",
    "capacidad_litros": "Capacidad (L)",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=10)
def load_profile_products(profile_key: str) -> pd.DataFrame:
    rows = _load_profile_products_raw(profile_key)
    if not rows:
        return pd.DataFrame(columns=["handle","descripcion_web","complejidad","k_num",
                                     "dim_l_mm","dim_w_mm","dim_h_mm","dim_espesor_mm",
                                     "dim_diameter_mm","G","D","c_value","x_flags",
                                     "is_anchor","validated","image_url","url","x_flags_parsed"])
    df = pd.DataFrame(rows)
    # Ensure expected columns exist
    for col in ["k_num","dim_l_mm","dim_w_mm","dim_h_mm","dim_espesor_mm","dim_diameter_mm",
                "G","D","c_value","x_flags","is_anchor","validated","image_url","url"]:
        if col not in df.columns:
            df[col] = None
    df["x_flags_parsed"] = df["x_flags"].apply(
        lambda v: json.loads(v) if isinstance(v, str) and v.strip() else []
    )
    return df

def compute_score(row, profile_rules, rules):
    """Compute total complexity score from G, D, c_value, x_flags for a product row."""
    G = row.get("G")
    D = row.get("D")
    c_val = row.get("c_value")
    x_active_list = row.get("x_flags_parsed", [])

    primary = set(profile_rules.get("primary_drivers", []) + profile_rules.get("secondary_drivers", []))
    x_defs  = profile_rules.get("x_flags", {})
    c_bp    = rules.get("driver_thresholds", {}).get("C", {}).get("breakpoints", [3, 7])

    pts = 0
    parts = []

    if G and "G" in primary:
        pts += G
        parts.append(f"G={G}")
    if D and "D" in primary:
        pts += D
        parts.append(f"D={D}")
    if c_val and "C" in primary:
        c_score = 1 if c_val <= c_bp[0] else (2 if c_val <= c_bp[1] else 3)
        pts += c_score
        parts.append(f"C={c_score}({c_val}u)")
    for flag in x_active_list:
        if flag in x_defs:
            fp = x_defs[flag].get("points", 0)
            pts += fp
            parts.append(f"X:{flag.replace('_',' ')}+{fp}")

    thresholds = profile_rules.get("complexity_thresholds", {})
    level = "?"
    for comp in ["C1", "C2", "C3"]:
        if comp not in thresholds:
            continue
        t = thresholds[comp]
        if t["min_points"] <= pts <= t["max_points"]:
            level = comp
            break

    return pts, level, " + ".join(parts) if parts else "sin datos"

def save_anchor(handle: str, profile_key: str, complejidad: str, rules: dict):
    _db_save_anchor(handle, profile_key, complejidad, rules)
    load_profile_products.clear()

# ─── Tab 4: Manage X Flags ────────────────────────────────────────────────────

DRIVER_LABELS = {"G": "G — Geometría", "D": "D — Densidad/Espesor",
                 "C": "C — Componentes", "X": "X — Características"}

def render_x_manager(profile_key: str, rules: dict):
    """Add / edit / delete X characteristic flags for a profile."""
    profile_rules = rules["profiles"].get(profile_key, {})
    x_defs = dict(profile_rules.get("x_flags", {}))

    # Processes that currently use X as a driver (from process_templates)
    templates = rules.get("process_templates", {})
    x_processes = sorted(p for p, t in templates.items() if "X" in t.get("drivers", []))

    st.markdown(
        '<p style="color:#8b949e;font-size:0.85rem;">'
        'Define las características X para este perfil. '
        'Cada flag suma puntos al score de complejidad del producto. '
        'Opcionalmente, limita qué procesos se ven afectados '
        '(vacío = afecta todos los procesos que usan driver X).</p>',
        unsafe_allow_html=True
    )

    if not x_defs:
        st.info("Este perfil no tiene características X definidas. Agrega la primera abajo.")
    else:
        st.markdown(
            f'<div class="sec-label" style="margin-bottom:0.5rem;">'
            f'{len(x_defs)} CARACTERÍSTICAS DEFINIDAS</div>',
            unsafe_allow_html=True
        )

    for key, flag in list(x_defs.items()):
        # Normalise legacy structure: primary_process → process_scope list
        scope = flag.get("process_scope") or (
            [flag["primary_process"]] if flag.get("primary_process") else []
        )
        scope_str = ", ".join(scope) if scope else "todos los procesos con driver X"
        with st.expander(
            f"✏️  {flag['label']}  ·  +{flag.get('points',1)} pts  ·  {scope_str}",
            expanded=False
        ):
            c1, c2 = st.columns([3, 1])
            new_label = c1.text_input("Nombre visible", value=flag.get("label",""),
                                      key=f"xlabel_{profile_key}_{key}")
            new_pts   = c2.number_input("Puntos (+)", value=int(flag.get("points",1)),
                                        min_value=1, max_value=5,
                                        key=f"xpts_{profile_key}_{key}")
            new_desc  = st.text_input("Descripción (opcional)", value=flag.get("description",""),
                                      key=f"xdesc_{profile_key}_{key}")
            new_scope = st.multiselect(
                "Afecta solo a estos procesos (vacío = todos con driver X)",
                options=x_processes,
                default=[s for s in scope if s in x_processes],
                key=f"xscope_{profile_key}_{key}",
                help="Deja vacío si esta característica aplica a todos los procesos que usan driver X. "
                     "Útil para flags como 'compartimiento profundo' que solo afectan soldadura."
            )
            col_save, col_del = st.columns(2)
            if col_save.button("💾 Guardar cambios", key=f"xupd_{profile_key}_{key}"):
                x_defs[key] = {
                    "label":         new_label.strip(),
                    "description":   new_desc.strip(),
                    "points":        int(new_pts),
                    "process_scope": new_scope,
                }
                rules["profiles"][profile_key]["x_flags"] = x_defs
                save_rules(rules)
                st.success(f"✅ '{new_label}' guardada.")
                st.rerun()
            if col_del.button("🗑️ Eliminar", type="secondary", key=f"xdel_{profile_key}_{key}"):
                del x_defs[key]
                rules["profiles"][profile_key]["x_flags"] = x_defs
                save_rules(rules)
                st.warning(f"🗑️ '{flag['label']}' eliminada.")
                st.rerun()

    # ── Add new flag ────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="sec-label" style="margin:1.5rem 0 0.5rem 0;">AGREGAR NUEVA CARACTERÍSTICA X</div>',
        unsafe_allow_html=True
    )
    with st.form(key=f"add_x_flag_{profile_key}", clear_on_submit=True):
        fc1, fc2 = st.columns([3, 1])
        new_key   = fc1.text_input("Clave interna (sin espacios, sin tildes)",
                                   placeholder="ej: compartimiento_profundo")
        new_label = fc1.text_input("Nombre visible",
                                   placeholder="ej: Compartimiento profundo")
        new_pts   = fc2.number_input("Puntos (+)", value=1, min_value=1, max_value=5)
        new_desc  = st.text_input("Descripción (opcional)",
                                  placeholder="Descripción para el equipo")
        new_scope = st.multiselect(
            "Afecta solo a estos procesos (vacío = todos con driver X)",
            options=x_processes,
            help="Ejemplo: si 'compartimiento profundo' solo afecta soldadura, selecciona soldadura aquí."
        )
        submitted = st.form_submit_button("➕ Agregar característica X", type="primary")
        if submitted:
            safe_key = new_key.strip().replace(" ", "_").lower()
            if not safe_key or not new_label.strip():
                st.error("Clave y nombre son obligatorios.")
            elif safe_key in x_defs:
                st.error(f"Ya existe una característica con clave '{safe_key}'.")
            else:
                x_defs[safe_key] = {
                    "label":         new_label.strip(),
                    "description":   new_desc.strip(),
                    "points":        int(new_pts),
                    "process_scope": new_scope,
                }
                rules["profiles"][profile_key]["x_flags"] = x_defs
                save_rules(rules)
                st.success(f"✅ '{new_label.strip()}' agregada al perfil {profile_key}.")
                st.rerun()

    if not x_processes:
        st.caption(
            "⚠️ Ningún proceso tiene driver X activo. "
            "Ve a ⚙️ Costos de Proceso → Templates para asignar driver X a procesos."
        )


# ─── Tab 1: Drivers C + X ──────────────────────────────────────────────────────

def render_drivers_cx(df: pd.DataFrame, profile_key: str, rules: dict):
    profile_rules = rules["profiles"].get(profile_key, {})
    c_driver_field = profile_rules.get("c_driver")
    x_defs = profile_rules.get("x_flags", {})
    primary = profile_rules.get("primary_drivers", []) + profile_rules.get("secondary_drivers", [])

    # ── Info card ──
    c_label = C_DRIVER_LABELS.get(c_driver_field, c_driver_field.replace("_", " ").title()) if c_driver_field else None
    drivers_str = " + ".join(primary) or "—"
    x_list = ", ".join(f"{m['label']} (+{m['points']}pts)" for m in x_defs.values()) if x_defs else "ninguna"

    st.markdown(
        f'<div class="di-card-blue">'
        f'<div class="sec-label">PERFIL: {profile_key}</div>'
        f'<div style="font-size:0.88rem;color:#cdd9e5;margin-top:0.3rem;">'
        f'Drivers: <b style="color:#79c0ff;">{drivers_str}</b> &nbsp;·&nbsp; '
        f'Driver C: <b style="color:#79c0ff;">{c_label or "no aplica"}</b></div>'
        f'<div style="font-size:0.8rem;color:#768390;margin-top:0.2rem;">'
        f'Características X: {x_list}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    if df.empty:
        st.info("No hay productos en este perfil.")
        return

    # ── Build editable dataframe ──
    edit_df = df[["handle", "image_url", "descripcion_web", "complejidad", "G", "D", "c_value"]].copy()
    edit_df = edit_df.rename(columns={
        "image_url": "Img",
        "descripcion_web": "Descripción",
        "complejidad": "Comp.",
        "c_value": c_label or "C (conteo)" if c_driver_field else "C (N/A)",
    })

    # Add one boolean column per X flag
    flag_keys = list(x_defs.keys())
    for flag in flag_keys:
        flag_col = f"X: {x_defs[flag]['label'][:20]}"
        edit_df[flag_col] = df["x_flags_parsed"].apply(lambda lst: flag in lst)

    # Column config
    col_config = {
        "handle": st.column_config.TextColumn("Handle", disabled=True, width="medium"),
        "Img": st.column_config.ImageColumn("", width="small"),
        "Descripción": st.column_config.TextColumn("Descripción", disabled=True, width="large"),
        "Comp.": st.column_config.TextColumn("Comp.", disabled=True, width="small"),
        "G": st.column_config.NumberColumn("G", disabled=True, width="small"),
        "D": st.column_config.NumberColumn("D", disabled=True, width="small"),
    }
    c_col_name = c_label or "C (conteo)" if c_driver_field else "C (N/A)"
    if c_driver_field:
        col_config[c_col_name] = st.column_config.NumberColumn(
            c_col_name, min_value=0, max_value=999, width="small",
            help=f"Ingresa el valor real de {c_label} para este producto"
        )
    else:
        col_config[c_col_name] = st.column_config.NumberColumn(c_col_name, disabled=True, width="small")

    for flag in flag_keys:
        flag_col = f"X: {x_defs[flag]['label'][:20]}"
        col_config[flag_col] = st.column_config.CheckboxColumn(
            flag_col,
            help=f"{x_defs[flag].get('description', '')} (+{x_defs[flag]['points']} pts)"
        )

    _cx_skey = f"df_cx_editor_{profile_key}"
    _cx_hkey = f"hash_cx_editor_{profile_key}"
    _cx_hash = hash(str(edit_df.values.tolist()) + str(list(edit_df.columns)))
    if st.session_state.get(_cx_hkey) != _cx_hash or _cx_skey not in st.session_state:
        st.session_state[_cx_skey] = edit_df
        st.session_state[_cx_hkey] = _cx_hash

    with st.form(f"cx_form_{profile_key}"):
        st.markdown(
            f'<div class="sec-label" style="margin-bottom:0.4rem;">'
            f'{len(df)} PRODUCTOS — edita C y X inline, luego guarda</div>',
            unsafe_allow_html=True
        )
        form_edited = st.data_editor(
            st.session_state[_cx_skey],
            column_config=col_config,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
        )
        cx_submitted = st.form_submit_button("📊 Calcular score")

    if cx_submitted:
        st.session_state[_cx_skey] = form_edited

    edited = st.session_state[_cx_skey]

    # ── Live score preview ──
    st.markdown('<div class="sec-label" style="margin:0.8rem 0 0.4rem 0;">VISTA PREVIA — SCORE CALCULADO</div>', unsafe_allow_html=True)

    preview_rows = []
    for i, erow in edited.iterrows():
        handle = erow["handle"]
        orig = df[df["handle"] == handle].iloc[0]

        # Reconstruct x_flags list from boolean columns
        x_active = [flag for flag in flag_keys
                    if erow.get(f"X: {x_defs[flag]['label'][:20]}", False)]

        _raw_c = erow.get(c_col_name, 0)
        c_val = int(np.nan_to_num(_raw_c, nan=0.0)) if c_driver_field else None
        mock_row = {
            "G": orig["G"], "D": orig["D"],
            "c_value": c_val,
            "x_flags_parsed": x_active,
        }
        pts, level, breakdown = compute_score(mock_row, profile_rules, rules)
        orig_comp = orig["complejidad"]
        match = level == orig_comp

        preview_rows.append({
            "Handle": handle,
            "Comp. actual": orig_comp,
            "Score": pts,
            "Comp. calculada": level,
            "✓": "✅" if match else f"⚠️ modelo→{level}",
            "Desglose": breakdown,
        })

    st.dataframe(
        pd.DataFrame(preview_rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.NumberColumn("Score", width="small"),
        }
    )

    # ── Save ──
    col_save, col_info2 = st.columns([1, 3])
    with col_save:
        if st.button("💾 Guardar C + X en DB", type="primary", key=f"save_cx_{profile_key}"):
            updates = []
            for i, erow in edited.iterrows():
                handle = erow["handle"]
                x_active = [flag for flag in flag_keys
                            if erow.get(f"X: {x_defs[flag]['label'][:20]}", False)]
                _raw_c2 = erow.get(c_col_name, 0)
                c_val = int(np.nan_to_num(_raw_c2, nan=0.0)) if c_driver_field else None
                updates.append({"handle": handle, "c_value": c_val, "x_flags": x_active})
            save_product_batch(updates)
            st.success(f"✅ {len(updates)} productos actualizados.")

    with col_info2:
        matches = sum(1 for r in preview_rows if r["✓"].startswith("✅"))
        total = len(preview_rows)
        st.markdown(
            f'<div class="di-card" style="padding:0.5rem 0.8rem;">'
            f'<span style="color:#3fb950;font-weight:700;">{matches}/{total}</span>'
            f'<span style="color:#768390;font-size:0.82rem;"> productos con score que coincide con complejidad actual</span>'
            f'</div>',
            unsafe_allow_html=True
        )


# ─── Tab 2: Process Tiers ─────────────────────────────────────────────────────

def render_process_tiers(profile_key: str, rules: dict):
    profile_rules = rules["profiles"].get(profile_key, {})
    process_tiers = profile_rules.get("process_tiers", {"C1": [], "C2": [], "C3": []})
    all_procs_in_profile = profile_rules.get("processes", [])

    st.markdown(
        '<p style="color:#8b949e;font-size:0.85rem;">'
        'Define qué procesos se ejecutan en cada nivel de complejidad para este perfil. '
        'C1 suele ser el subconjunto mínimo. C3 incluye procesos adicionales (ej. pulido fino, laser externo).</p>',
        unsafe_allow_html=True
    )

    # Show profile processes as context
    st.markdown(
        f'<div class="di-card">'
        f'<div class="sec-label">PROCESOS DECLARADOS EN EL PERFIL</div>'
        f'<div style="font-size:0.88rem;color:#cdd9e5;">'
        f'{", ".join(all_procs_in_profile) if all_procs_in_profile else "ninguno aún"}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    new_tiers = {}
    badge_styles = {
        "C1": ("badge-c1", "#3fb950"),
        "C2": ("badge-c2", "#e3b341"),
        "C3": ("badge-c3", "#f85149"),
    }

    for comp in ["C1", "C2", "C3"]:
        badge_cls, color = badge_styles[comp]
        current = process_tiers.get(comp, all_procs_in_profile)

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:0.5rem;margin:0.8rem 0 0.2rem 0;">'
            f'<span class="badge {badge_cls}">{comp}</span>'
            f'<span style="color:{color};font-size:0.82rem;font-weight:600;">Procesos activos</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        selected = st.multiselect(
            f"Procesos en {comp}",
            options=KNOWN_PROCESSES,
            default=[p for p in current if p in KNOWN_PROCESSES],
            key=f"tiers_{profile_key}_{comp}",
            label_visibility="collapsed",
            help=f"Selecciona qué procesos se ejecutan en {comp} para {profile_key}"
        )
        new_tiers[comp] = selected

        # Visual diff vs C2 baseline
        if comp in ("C1", "C3") and "C2" in new_tiers:
            c2_set = set(new_tiers["C2"])
            sel_set = set(selected)
            removed = c2_set - sel_set
            added   = sel_set - c2_set
            notes = []
            if removed:
                notes.append(f'<span style="color:#f85149;">−{", ".join(removed)}</span>')
            if added:
                notes.append(f'<span style="color:#3fb950;">+{", ".join(added)}</span>')
            if notes:
                st.markdown(
                    f'<div style="font-size:0.78rem;color:#768390;margin-top:0.2rem;">vs C2: '
                    + " · ".join(notes) + "</div>",
                    unsafe_allow_html=True
                )

    st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)

    col_s, col_p = st.columns([1, 3])
    with col_s:
        if st.button("💾 Guardar process_tiers", type="primary", key=f"save_tiers_{profile_key}"):
            rules["profiles"][profile_key]["process_tiers"] = new_tiers
            # Also update the flat processes list (union of all tiers)
            all_procs = sorted(set(p for procs in new_tiers.values() for p in procs))
            rules["profiles"][profile_key]["processes"] = all_procs
            rules["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            save_rules(rules)
            st.success("✅ process_tiers guardado. El perfil ahora tiene procesos por nivel.")

    with col_p:
        total_c1 = len(new_tiers.get("C1", []))
        total_c2 = len(new_tiers.get("C2", []))
        total_c3 = len(new_tiers.get("C3", []))
        st.markdown(
            f'<div class="di-card" style="padding:0.5rem 0.8rem;">'
            f'<span style="color:#3fb950;">C1: {total_c1}</span> · '
            f'<span style="color:#e3b341;">C2: {total_c2}</span> · '
            f'<span style="color:#f85149;">C3: {total_c3}</span>'
            f'<span style="color:#768390;font-size:0.78rem;"> procesos por nivel</span>'
            f'</div>',
            unsafe_allow_html=True
        )


# ─── Tab 3: Anchors ───────────────────────────────────────────────────────────

def render_anchors(df: pd.DataFrame, profile_key: str, rules: dict):
    profile_rules = rules["profiles"].get(profile_key, {})
    current_anchors = profile_rules.get("anchors", {})

    st.markdown(
        '<p style="color:#8b949e;font-size:0.85rem;">'
        'Designa un producto representativo como ancla para cada nivel de complejidad. '
        'El ancla es el producto del que se medirán los costos reales (BOM) y a partir del cual '
        'se extrapolará el costo del resto del bucket usando factor_escala.</p>',
        unsafe_allow_html=True
    )

    badge_styles = {"C1": "badge-c1", "C2": "badge-c2", "C3": "badge-c3"}

    for comp in ["C1", "C2", "C3"]:
        bucket = df[df["complejidad"] == comp]
        current = current_anchors.get(comp)

        badge_cls = badge_styles.get(comp, "badge-c1")
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:0.6rem;margin:1rem 0 0.3rem 0;">'
            f'<span class="badge {badge_cls}">{comp}</span>'
            f'<span style="color:#cdd9e5;font-size:0.9rem;font-weight:600;">'
            f'{len(bucket)} productos en {comp}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        if bucket.empty:
            st.markdown(
                '<div style="color:#484f58;font-size:0.82rem;margin-bottom:0.5rem;">'
                'Sin productos en este nivel aún.</div>',
                unsafe_allow_html=True
            )
            continue

        handles = bucket["handle"].tolist()
        default_idx = handles.index(current) if current in handles else 0

        selected = st.selectbox(
            f"Ancla {comp}",
            options=handles,
            index=default_idx,
            key=f"anchor_{profile_key}_{comp}",
            label_visibility="collapsed",
            format_func=lambda h: f"{'⭐ ' if h == current else ''}{h}"
        )

        # Show selected product info
        sel_row = bucket[bucket["handle"] == selected].iloc[0]
        G_v = sel_row.get("G")
        D_v = sel_row.get("D")
        L = sel_row.get("dim_l_mm") or 0
        W = sel_row.get("dim_w_mm") or 0
        H = sel_row.get("dim_h_mm") or 0
        e = sel_row.get("dim_espesor_mm") or 0
        area = 2 * (L + W) * H + L * W if L and W else None
        area_str = f"{area/1e6:.3f} m²" if area else "sin dims"
        is_anchor_db = bool(sel_row.get("is_anchor", 0))
        desc = str(sel_row.get("descripcion_web", "") or "")[:100]

        anchor_pill = (
            ' <span style="background:#0d3321;color:#3fb950;border:1px solid #238636;'
            'border-radius:8px;padding:1px 8px;font-size:0.72rem;">⭐ ancla actual</span>'
            if is_anchor_db else ""
        )

        st.markdown(
            f'<div class="di-card" style="margin-top:0.3rem;padding:0.6rem 0.9rem;">'
            f'<div style="font-size:0.82rem;color:#cdd9e5;">'
            f'<b style="font-family:monospace;">{selected}</b>{anchor_pill}</div>'
            f'<div style="font-size:0.75rem;color:#768390;margin-top:0.2rem;">{desc}</div>'
            f'<div style="font-size:0.75rem;color:#79c0ff;margin-top:0.2rem;">'
            f'G={G_v or "—"}  D={D_v or "—"}  e={e}mm  Área={area_str}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        if st.button(
            f"⭐ Marcar como ancla {comp}",
            key=f"set_anchor_{profile_key}_{comp}",
            type="primary" if selected != current else "secondary",
        ):
            save_anchor(selected, profile_key, comp, rules)
            st.success(
                f"✅ {selected} marcado como ancla de {comp} en {profile_key}.\n\n"
                f"Ahora ingresa el BOM real en **⚖️ Calibración** → Tab 1."
            )
            st.rerun()

    # Summary table
    st.divider()
    st.markdown('<div class="sec-label">RESUMEN DE ANCLAS — {}</div>'.format(profile_key), unsafe_allow_html=True)

    summary_rows = []
    for comp in ["C1", "C2", "C3"]:
        handle = current_anchors.get(comp)
        bucket = df[df["complejidad"] == comp]
        bom_filled = False
        if handle:
            arow = bucket[bucket["handle"] == handle]
            if not arow.empty:
                bom = arow.iloc[0].get("bom_materials", "[]")
                bom_filled = bool(json.loads(bom) if isinstance(bom, str) else bom)
        summary_rows.append({
            "Nivel": comp,
            "Ancla": handle or "—",
            "BOM ingresado": "✅" if bom_filled else "—",
            "Productos en bucket": len(bucket),
        })
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    try:
        st.set_page_config(
            page_title="Dulox — Datos de Productos",
            page_icon="📊",
            layout="wide",
        )
    except Exception:
        pass
    st.markdown(CSS, unsafe_allow_html=True)

    rules = load_rules()
    available_profiles = sorted(rules.get("profiles", {}).keys())

    st.markdown(
        '<h2 style="border-bottom:1px solid #21262d;padding-bottom:0.5rem;">'
        '📊 Datos de Productos — C / X / Procesos / Anclas</h2>',
        unsafe_allow_html=True
    )

    with st.sidebar:
        st.markdown("### 📋 Perfil")
        profile_key = st.selectbox(
            "Perfil proceso",
            available_profiles,
            label_visibility="collapsed",
            key="di_profile_key",
        )
        profile_rules = rules.get("profiles", {}).get(profile_key, {})
        n_prods = load_profile_products(profile_key)
        n_total = len(n_prods)
        n_cx = int((n_prods["c_value"].notna() | (n_prods["x_flags"] != "[]")).sum())

        st.markdown(
            f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;'
            f'padding:0.6rem 0.9rem;margin-top:0.4rem;">'
            f'<div style="font-size:0.82rem;color:#cdd9e5;">{n_total} productos</div>'
            f'<div style="font-size:0.75rem;color:#3fb950;">{n_cx} con C/X ingresado</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.divider()
        if st.button("🔄 Recargar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    df = load_profile_products(profile_key)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Drivers C + X",
        "⚙️ Procesos por Nivel",
        "⭐ Anclas",
        "🏷️ Gestionar X",
    ])

    with tab1:
        render_drivers_cx(df, profile_key, rules)

    with tab2:
        render_process_tiers(profile_key, rules)

    with tab3:
        render_anchors(df, profile_key, rules)

    with tab4:
        render_x_manager(profile_key, rules)


main()
