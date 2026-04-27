"""
product_audit.py — Dulox Product Cost Audit & Edit View
=========================================================
Per-product auditable cost sheet with inline editing.

Each product shows:
  • Editable dimensions → live driver scores (G/D/C/X)
  • Profile + complexity tier + active processes
  • Extrapolation status: anchor / factor_escala / template source
  • Editable BOM materials (add / remove / modify)
  • Editable consumables (add / remove / modify)
  • Editable X characteristics
  • Process HH costs from global templates (read-only reference)
  • Total cost summary

Template source badge:
  🔵 Extrapolado  — costs match anchor × factor_escala (no manual edits)
  🟡 Editado      — product has its own BOM (diverges from extrapolation)
  ⚪ Sin datos    — no BOM saved, anchor not configured
"""

import json
import math
import sys
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import load_rules, save_rules, get_sb, save_bom as _save_bom_db

# ─── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
<style>
html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"] { background-color:#0d1117 !important; color:#e6edf3 !important; }
[data-testid="stSidebar"] { background-color:#161b22 !important; border-right:1px solid #30363d; }
[data-testid="stSidebar"] * { color:#c9d1d9 !important; }
h1,h2,h3,h4 { color:#f0f6fc !important; }
.card { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.card-blue  { background:#0d2137; border:1px solid #1f6feb; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.card-green { background:#0d2818; border:1px solid #238636; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.card-warn  { background:#2d2000; border:1px solid #9e6a03; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.card-red   { background:#200d0d; border:1px solid #6e3030; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.sec-label  { font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:#768390; margin-bottom:0.3rem; }
.num-big    { font-size:1.5rem; font-weight:700; color:#e6edf3; line-height:1.2; }
.num-med    { font-size:1.1rem; font-weight:600; color:#cdd9e5; }
.badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:700; }
.badge-c1   { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-c2   { background:#2d1b00; color:#e3b341; border:1px solid #9e6a03; }
.badge-c3   { background:#3d0c0c; color:#f85149; border:1px solid #da3633; }
.badge-ok   { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-warn { background:#2d2000; color:#e3b341; border:1px solid #9e6a03; }
.badge-err  { background:#3d0c0c; color:#f85149; border:1px solid #da3633; }
.badge-info { background:#0d2137; color:#79c0ff; border:1px solid #1f6feb; }
.badge-grey { background:#161b22; color:#8b949e; border:1px solid #30363d; }
.driver-chip { display:inline-block; background:#1f2d3d; border:1px solid #2d4a6a; border-radius:6px;
               padding:4px 10px; margin:2px 3px; font-size:0.82rem; font-weight:600; color:#79c0ff; }
.driver-1 { background:#0d3321; border-color:#238636; color:#3fb950; }
.driver-2 { background:#2d2000; border-color:#9e6a03; color:#e3b341; }
.driver-3 { background:#3d0c0c; border-color:#da3633; color:#f85149; }
.source-extrap { background:#0d2137; border:1px solid #1f6feb; border-radius:8px;
                 padding:6px 12px; font-size:0.82rem; color:#79c0ff; display:inline-block; }
.source-edited { background:#2d2000; border:1px solid #9e6a03; border-radius:8px;
                 padding:6px 12px; font-size:0.82rem; color:#e3b341; display:inline-block; }
.source-empty  { background:#161b22; border:1px solid #30363d; border-radius:8px;
                 padding:6px 12px; font-size:0.82rem; color:#8b949e; display:inline-block; }
[data-testid="stDataFrameResizable"] { border:1px solid #30363d; border-radius:8px; }
[data-testid="stExpander"] { background:#161b22 !important; border:1px solid #30363d !important; border-radius:8px !important; }
hr { border-color:#21262d !important; }
</style>
"""

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _clp(v) -> str:
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "—"
    return f"${int(v):,}".replace(",", ".")

def _nan(v) -> float:
    if v is None: return 0.0
    try:
        f = float(v)
        return 0.0 if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return 0.0

def _pj(raw, default=None):
    if default is None: default = []
    if isinstance(raw, list): return raw
    if not raw: return default
    try: return json.loads(raw)
    except: return default

def _badge(comp: str) -> str:
    cls = {"C1":"badge-c1","C2":"badge-c2","C3":"badge-c3"}.get(comp, "badge-grey")
    return f'<span class="badge {cls}">{comp or "?"}</span>'

def _chip(label, score, detail=""):
    cls = {1:"driver-1",2:"driver-2",3:"driver-3"}.get(score,"driver-chip")
    tip = f" <span style='color:#768390;font-size:0.72rem;'>({detail})</span>" if detail else ""
    return f'<span class="driver-chip {cls}">{label}={score}{tip}</span>'

# ─── Score functions ───────────────────────────────────────────────────────────

def _G(L, W, H, rules):
    if not L or not W: return None, None
    area = 2*(L+W)*(H or 0) + L*W
    bp = rules["driver_thresholds"]["G"]["breakpoints_mm2"]
    return (1 if area < bp[0] else 2 if area < bp[1] else 3), area

def _D(e, rules):
    if not e: return None
    bp = rules["driver_thresholds"]["D"]["breakpoints_mm"]
    return 1 if e <= bp[0] else 2 if e <= bp[1] else 3

def _C(count, rules):
    if not count: return None
    bp = rules["driver_thresholds"].get("C",{}).get("breakpoints",[3,7])
    return 1 if count <= bp[0] else 2 if count <= bp[1] else 3

def _score(G, D, C, x_pts, primary, secondary):
    active = set((primary or []) + (secondary or []))
    pts = 0
    if G and "G" in active: pts += G
    if D and "D" in active: pts += D
    if C and "C" in active: pts += C
    return pts + x_pts

def _complexity(pts, thresholds):
    for comp in ["C1","C2","C3"]:
        t = thresholds.get(comp, {})
        if t.get("min_points",0) <= pts <= t.get("max_points",99):
            return comp
    return "?"

# ─── Data loading ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=20)
def _all_products():
    rows = get_sb().table("products").select(
        "handle,descripcion_web,perfil_proceso,complejidad,familia,subfamilia,"
        "dim_l_mm,dim_w_mm,dim_h_mm,dim_espesor_mm,g_score,d_score,"
        "c_value,x_flags,bom_materials,bom_consumables,is_anchor,image_url"
    ).order("perfil_proceso,handle").execute().data or []
    return rows

def _anchor_data(profile_key: str, comp: str, rules: dict) -> dict:
    """Return anchor handle, dims, mat_total, cons_total for this profile+comp."""
    prof  = rules.get("profiles", {}).get(profile_key, {})
    bench = prof.get("cost_benchmarks", {}).get(comp, {})
    anch  = prof.get("anchors", {}).get(comp)
    dims  = bench.get("dims", {})
    return {
        "handle":     anch,
        "mat_total":  bench.get("material_total_clp"),
        "cons_total": bench.get("consumables_total_clp"),
        "L": _nan(dims.get("L_mm")), "W": _nan(dims.get("W_mm")),
        "H": _nan(dims.get("H_mm")), "e": _nan(dims.get("espesor_mm")),
    }

def _factor_escala(L, W, H, anchor) -> float | None:
    aL, aW, aH = anchor["L"], anchor["W"], anchor["H"]
    if not (L and W and aL and aW): return None
    area  = 2*(L+W)*(H or 0) + L*W
    a_area = 2*(aL+aW)*(aH or 0) + aL*aW
    if not a_area: return None
    f = area / a_area
    return round(f, 4) if math.isfinite(f) else None

def _source_badge(mat_rows, cons_rows, anchor, factor) -> tuple[str, str]:
    """Returns (html_badge, source_key: 'extrapolated'|'edited'|'empty')"""
    has_bom = bool(mat_rows or cons_rows)
    if not has_bom:
        return '<span class="source-empty">⚪ Sin datos — sin BOM guardado</span>', "empty"
    if not anchor.get("handle"):
        return '<span class="source-edited">🟡 BOM propio — sin ancla configurada</span>', "edited"
    if factor is None:
        return '<span class="source-edited">🟡 BOM propio — sin dimensiones para escalar</span>', "edited"

    # Compare mat total vs extrapolated expectation
    mat_total  = sum(_nan(r.get("total")) for r in mat_rows)
    cons_total = sum(_nan(r.get("Total")) for r in cons_rows)
    exp_mat  = (anchor["mat_total"]  or 0) * factor
    exp_cons = (anchor["cons_total"] or 0) * factor

    def _close(a, b, tol=0.15):  # within 15%
        if not b: return not a
        return abs(a-b)/b < tol

    if _close(mat_total, exp_mat) and _close(cons_total, exp_cons):
        return (f'<span class="source-extrap">🔵 Extrapolado — ancla: {anchor["handle"]} · factor {factor:.3f}×</span>',
                "extrapolated")
    return (f'<span class="source-edited">🟡 Editado — ancla ref: {anchor["handle"]} · factor {factor:.3f}×</span>',
            "edited")


# ─── Section renderers ────────────────────────────────────────────────────────

def render_header(product: dict):
    img = product.get("image_url")
    c1, c2 = st.columns([1, 5])
    if img:
        c1.image(img, width=100)
    c2.markdown(
        f'<div style="font-size:1.2rem;font-weight:700;color:#f0f6fc;margin-bottom:0.2rem;">'
        f'{product.get("descripcion_web") or product["handle"]}</div>'
        f'<code style="color:#79c0ff;font-size:0.82rem;">{product["handle"]}</code>'
        f'<span style="color:#484f58;font-size:0.78rem;margin-left:1rem;">'
        f'{product.get("familia","—")} / {product.get("subfamilia","—")}</span>',
        unsafe_allow_html=True
    )


def render_dimensions_editor(product: dict, rules: dict):
    """Editable dimensions + live driver scores."""
    handle = product["handle"]
    L0 = _nan(product.get("dim_l_mm"))
    W0 = _nan(product.get("dim_w_mm"))
    H0 = _nan(product.get("dim_h_mm"))
    e0 = _nan(product.get("dim_espesor_mm"))

    with st.form(f"dims_{handle}"):
        st.markdown('<div class="sec-label">DIMENSIONES</div>', unsafe_allow_html=True)
        c1,c2,c3,c4 = st.columns(4)
        L = c1.number_input("Largo mm",   value=L0, min_value=0.0, step=1.0, format="%.0f", key=f"L_{handle}")
        W = c2.number_input("Ancho mm",   value=W0, min_value=0.0, step=1.0, format="%.0f", key=f"W_{handle}")
        H = c3.number_input("Alto mm",    value=H0, min_value=0.0, step=1.0, format="%.0f", key=f"H_{handle}")
        e = c4.number_input("Espesor mm", value=e0, min_value=0.0, step=0.1, format="%.1f", key=f"e_{handle}")
        saved = st.form_submit_button("💾 Guardar dimensiones", use_container_width=True)

    if saved:
        G_new, _ = _G(L, W, H, rules)
        D_new    = _D(e, rules)
        payload  = {}
        if L > 0: payload["dim_l_mm"] = L
        if W > 0: payload["dim_w_mm"] = W
        if H > 0: payload["dim_h_mm"] = H
        if e > 0: payload["dim_espesor_mm"] = e
        if G_new: payload["g_score"] = int(G_new)
        if D_new: payload["d_score"] = int(D_new)
        if payload:
            get_sb().table("products").update(payload).eq("handle", handle).execute()
            _all_products.clear()
            st.success("✅ Dimensiones guardadas")
            st.rerun()
        L, W, H, e = L, W, H, e  # use new values for score display

    return L, W, H, e


def render_drivers(L, W, H, e, product, rules):
    """Live driver score panel."""
    profile_key   = product.get("perfil_proceso","")
    profile_rules = rules.get("profiles",{}).get(profile_key,{})
    x_defs        = profile_rules.get("x_flags",{})
    thresholds    = profile_rules.get("complexity_thresholds",{})
    primary       = profile_rules.get("primary_drivers",[])
    secondary     = profile_rules.get("secondary_drivers",[])
    c_driver      = profile_rules.get("c_driver")

    x_list  = _pj(product.get("x_flags"), [])
    c_count = int(_nan(product.get("c_value")))

    G, area = _G(L, W, H, rules)
    D       = _D(e, rules)
    C       = _C(c_count, rules) if (c_count and c_driver) else None
    X_pts   = sum(x_defs.get(f,{}).get("points",0) for f in x_list)
    pts     = _score(G, D, C, X_pts, primary, secondary)
    model_c = _complexity(pts, thresholds)
    db_c    = product.get("complejidad") or "?"
    match   = model_c == db_c

    area_str = f"{area/1e6:.3f} m²" if area else "—"
    chips = ""
    if G is not None: chips += _chip("G", G, area_str)
    if D is not None: chips += _chip("D", D, f"{e}mm")
    if C is not None: chips += _chip("C", C, f"{c_count} {c_driver or ''}")
    if X_pts > 0:
        xl = ", ".join(x_defs.get(f,{}).get("label",f)[:15] for f in x_list if f in x_defs)
        chips += _chip("X", min(X_pts,3), xl)

    match_html = (
        '<span class="badge badge-ok">✅ Coincide</span>'
        if match else
        f'<span class="badge badge-warn">⚠️ Modelo→{model_c} · DB→{db_c}</span>'
    )

    st.markdown(
        f'<div class="card" style="margin-bottom:0.5rem;">'
        f'<div class="sec-label">DRIVERS G/D/C/X</div>'
        f'<div style="margin:0.3rem 0;">{chips}</div>'
        f'<div style="display:flex;gap:0.8rem;align-items:center;margin-top:0.5rem;flex-wrap:wrap;">'
        f'<span style="color:#8b949e;font-size:0.85rem;">Score <b style="color:#79c0ff;">{pts}pts</b></span>'
        f'→ {_badge(model_c)} <span style="color:#8b949e;font-size:0.78rem;">DB:</span> {_badge(db_c)}'
        f'<span>{match_html}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )
    return {"G":G,"D":D,"C":C,"X_pts":X_pts,"pts":pts,"model_c":model_c}


def render_profile_tier(product, rules):
    """Profile name, complexity tier, active processes."""
    profile_key   = product.get("perfil_proceso","—")
    comp          = product.get("complejidad","?")
    profile_rules = rules.get("profiles",{}).get(profile_key,{})
    tier_desc     = profile_rules.get("complexity_thresholds",{}).get(comp,{}).get("description","")
    primary       = profile_rules.get("primary_drivers",[])
    secondary     = profile_rules.get("secondary_drivers",[])
    c_driver      = profile_rules.get("c_driver","—")
    proc_list     = profile_rules.get("process_tiers",{}).get(comp,[])

    pills = " ".join(
        f'<span style="background:#1f2d3d;border:1px solid #2d4a6a;border-radius:5px;'
        f'padding:2px 8px;font-size:0.75rem;color:#79c0ff;margin:2px;display:inline-block;">'
        f'{p.replace("_"," ")}</span>'
        for p in proc_list
    ) or '<span style="color:#484f58;font-size:0.78rem;">Sin procesos para este nivel</span>'

    st.markdown(
        f'<div class="card" style="margin-bottom:0.5rem;">'
        f'<div class="sec-label">PERFIL DE PROCESO</div>'
        f'<div style="display:flex;gap:0.7rem;align-items:center;margin-bottom:0.3rem;">'
        f'<b style="color:#cdd9e5;">{profile_key}</b>{_badge(comp)}</div>'
        f'<div style="font-size:0.78rem;color:#8b949e;margin-bottom:0.4rem;">{tier_desc}</div>'
        f'<div style="font-size:0.75rem;color:#768390;margin-bottom:0.5rem;">'
        f'Primarios: <b style="color:#79c0ff;">{", ".join(primary) or "—"}</b>  ·  '
        f'Secundarios: <b style="color:#79c0ff;">{", ".join(secondary) or "—"}</b>  ·  '
        f'Driver-C: <b style="color:#79c0ff;">{c_driver}</b></div>'
        f'<div class="sec-label">PROCESOS ACTIVOS EN {comp}</div>'
        f'<div style="margin-top:0.2rem;">{pills}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    return proc_list, comp


def render_extrap_status(product, rules, factor, anchor, source_html, source_key):
    """Extrapolation status card."""
    comp = product.get("complejidad","?")
    exp_mat  = round((anchor["mat_total"]  or 0) * factor) if (factor and anchor.get("mat_total"))  else None
    exp_cons = round((anchor["cons_total"] or 0) * factor) if (factor and anchor.get("cons_total")) else None

    lines = [source_html]
    if anchor.get("handle"):
        lines.append(
            f'<div style="font-size:0.78rem;color:#8b949e;margin-top:0.4rem;">'
            f'Ancla <b style="color:#cdd9e5;">{anchor["handle"]}</b> ({comp})  ·  '
            f'factor_escala = <b style="color:#79c0ff;">{factor:.3f}×</b></div>'
            if factor else
            f'<div style="font-size:0.78rem;color:#484f58;margin-top:0.4rem;">'
            f'Ancla: {anchor["handle"]}  ·  factor_escala: sin dimensiones</div>'
        )
    if exp_mat is not None:
        lines.append(
            f'<div style="font-size:0.78rem;color:#8b949e;margin-top:0.2rem;">'
            f'Costo esperado extrapolado: mat <b>{_clp(exp_mat)}</b>  ·  cons <b>{_clp(exp_cons)}</b>'
            f'  ·  total <b style="color:#3fb950;">{_clp((exp_mat or 0)+(exp_cons or 0))}</b></div>'
        )

    st.markdown(
        f'<div class="card" style="margin-bottom:0.5rem;">'
        f'<div class="sec-label">FUENTE DEL TEMPLATE</div>'
        + "".join(lines) +
        '</div>',
        unsafe_allow_html=True
    )


def render_materials_editor(product: dict):
    """Editable materials BOM."""
    handle = product["handle"]
    saved  = _pj(product.get("bom_materials"), [])

    default = saved or [{"Subconjunto":"","Dimensiones":"","Material":"","Cantidad":1.0,"kg_ml":0.0,"precio_kg":3600,"total":0}]
    skey  = f"mat_ed_{handle}"
    hkey  = f"mat_h_{handle}"
    dhash = hash(str(default))
    if st.session_state.get(hkey) != dhash or skey not in st.session_state:
        st.session_state[skey] = pd.DataFrame(default)
        st.session_state[hkey] = dhash

    mat_total = int(sum(_nan(r.get("total")) for r in saved))

    with st.form(f"mat_form_{handle}"):
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">'
            f'<div class="sec-label">MATERIALES — {len(saved)} ítems</div>'
            f'<div class="num-med" style="color:#3fb950;">{_clp(mat_total)}</div></div>',
            unsafe_allow_html=True
        )
        edited = st.data_editor(
            st.session_state[skey],
            use_container_width=True, num_rows="dynamic", hide_index=True,
            column_config={
                "total":     st.column_config.NumberColumn("Total $",   format="%.0f", step=1),
                "precio_kg": st.column_config.NumberColumn("$/kg o $/u",format="%.0f", step=1),
                "kg_ml":     st.column_config.NumberColumn("kg/ML/u",   format="%.4f", step=0.0001),
                "Cantidad":  st.column_config.NumberColumn("Cant.",      format="%.3f", step=0.001),
            }
        )
        save_mat = st.form_submit_button("💾 Guardar materiales", use_container_width=True)

    if save_mat:
        st.session_state[skey] = edited
        cons_saved = _pj(product.get("bom_consumables"), [])
        _save_bom_db(handle, edited.to_dict("records"), cons_saved)
        _all_products.clear()
        st.session_state.pop(skey, None); st.session_state.pop(hkey, None)
        st.success("✅ Materiales guardados")
        st.rerun()

    return int(sum(_nan(r.get("total")) for r in st.session_state[skey].to_dict("records")))


def render_consumables_editor(product: dict):
    """Editable consumables grouped by process."""
    handle = product["handle"]
    saved  = _pj(product.get("bom_consumables"), [])

    default = saved or [{"Producto":"","Proceso":"soldadura","Cantidad":1.0,"Unidad":"u","Precio_u":0,"Total":0}]
    skey  = f"cons_ed_{handle}"
    hkey  = f"cons_h_{handle}"
    dhash = hash(str(default))
    if st.session_state.get(hkey) != dhash or skey not in st.session_state:
        st.session_state[skey] = pd.DataFrame(default)
        st.session_state[hkey] = dhash

    cons_total = int(sum(_nan(r.get("Total")) for r in saved))

    # Group preview by process (read-only, outside form)
    by_proc: dict[str, int] = {}
    for r in saved:
        proc = r.get("Proceso") or "Sin proceso"
        by_proc[proc] = by_proc.get(proc, 0) + int(_nan(r.get("Total")))

    if by_proc:
        proc_parts = "  ·  ".join(
            f'<span style="color:#cdd9e5;">{p.replace("_"," ")}</span>'
            f' <span style="color:#e3b341;">{_clp(t)}</span>'
            for p, t in by_proc.items()
        )
        st.markdown(
            f'<div style="font-size:0.78rem;color:#768390;margin-bottom:0.3rem;">{proc_parts}</div>',
            unsafe_allow_html=True
        )

    with st.form(f"cons_form_{handle}"):
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">'
            f'<div class="sec-label">CONSUMIBLES — {len(saved)} ítems</div>'
            f'<div class="num-med" style="color:#e3b341;">{_clp(cons_total)}</div></div>',
            unsafe_allow_html=True
        )
        edited = st.data_editor(
            st.session_state[skey],
            use_container_width=True, num_rows="dynamic", hide_index=True,
            column_config={
                "Precio_u": st.column_config.NumberColumn("Precio u.", format="%.0f", step=1),
                "Total":    st.column_config.NumberColumn("Total $",   format="%.0f", step=1),
                "Cantidad": st.column_config.NumberColumn("Cant.",      format="%.3f", step=0.001),
                "Proceso":  st.column_config.SelectboxColumn(
                    "Proceso",
                    options=["laser","corte_manual","armado_trazado","plegado","cilindrado",
                             "soldadura","pulido","qc","grabado_laser","refrigeracion","pintura",
                             "Pulido","Soldadura","Armado/Trazado","Sin proceso"],
                ),
            }
        )
        save_cons = st.form_submit_button("💾 Guardar consumibles", use_container_width=True)

    if save_cons:
        st.session_state[skey] = edited
        mat_saved = _pj(product.get("bom_materials"), [])
        _save_bom_db(handle, mat_saved, edited.to_dict("records"))
        _all_products.clear()
        st.session_state.pop(skey, None); st.session_state.pop(hkey, None)
        st.success("✅ Consumibles guardados")
        st.rerun()

    return int(sum(_nan(r.get("Total")) for r in st.session_state[skey].to_dict("records")))


def render_x_flags_editor(product: dict, rules: dict):
    """Editable X characteristics + optional c_value."""
    handle        = product["handle"]
    profile_key   = product.get("perfil_proceso","")
    profile_rules = rules.get("profiles",{}).get(profile_key,{})
    x_defs        = profile_rules.get("x_flags",{})
    c_driver      = profile_rules.get("c_driver")

    if not x_defs and not c_driver:
        return

    x_saved  = _pj(product.get("x_flags"), [])
    c_saved  = int(_nan(product.get("c_value")))

    with st.form(f"x_form_{handle}"):
        st.markdown('<div class="sec-label">CARACTERÍSTICAS X + DRIVER C</div>', unsafe_allow_html=True)
        new_flags = []
        for flag, meta in x_defs.items():
            checked = st.checkbox(
                f'{meta["label"]}  (+{meta.get("points",0)} pts)',
                value=(flag in x_saved),
                key=f"xf_{handle}_{flag}",
                help=meta.get("description","")
            )
            if checked:
                new_flags.append(flag)

        new_c = c_saved
        if c_driver:
            new_c = st.number_input(
                f"{c_driver.replace('num_','').replace('_',' ').title()} (driver C)",
                value=c_saved, min_value=0, step=1,
                key=f"c_val_{handle}"
            )

        saved_btn = st.form_submit_button("💾 Guardar X + C", use_container_width=True)

    if saved_btn:
        payload = {"x_flags": json.dumps(new_flags), "c_value": int(new_c)}
        get_sb().table("products").update(payload).eq("handle", handle).execute()
        _all_products.clear()
        st.success("✅ Características guardadas")
        st.rerun()


def render_hh_costs(proc_list: list, comp: str, rules: dict) -> int:
    """Process HH costs from global templates."""
    hh_rates  = rules.get("hh_rates", {})
    templates = rules.get("process_templates", {})

    if not proc_list:
        st.markdown(
            '<div class="card-red"><div class="sec-label">COSTOS HH</div>'
            '<div style="color:#8b949e;font-size:0.82rem;">Sin procesos configurados para este perfil/nivel en PROCESS_RULES.</div></div>',
            unsafe_allow_html=True
        )
        return 0

    rows = []
    total_hh = 0
    for proc in proc_list:
        tpl     = templates.get(proc, {}).get(comp, {})
        t_setup = _nan(tpl.get("T_setup_min"))
        t_exec  = _nan(tpl.get("T_exec_min"))
        n_ops   = max(_nan(tpl.get("n_ops", 1)), 1)
        rate    = _nan(hh_rates.get(proc))
        t_total = t_setup + t_exec
        cost    = round((t_total / 60) * rate * n_ops) if (t_total and rate) else None
        if cost:
            total_hh += cost
        rows.append({
            "Proceso":   proc.replace("_"," "),
            "Nivel":     comp,
            "Setup min": int(t_setup) if t_setup else "—",
            "Exec min":  int(t_exec)  if t_exec  else "—",
            "Ops":       int(n_ops),
            "$/HH":      int(rate)    if rate    else "—",
            "Costo HH":  cost         if cost    else "—",
        })

    df = pd.DataFrame(rows)
    st.markdown(
        f'<div class="card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">'
        f'<div class="sec-label">MANO DE OBRA — templates × tarifas</div>'
        f'<div class="num-med" style="color:#79c0ff;">{_clp(total_hh) if total_hh else "—"}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    st.dataframe(
        df, use_container_width=True, hide_index=True,
        column_config={
            "$/HH":     st.column_config.NumberColumn(format="$ %d"),
            "Costo HH": st.column_config.NumberColumn(format="$ %d"),
        }
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return total_hh


def render_totals(mat: int, cons: int, hh: int, factor, anchor, source_key: str):
    """Total cost summary with extrapolation reference."""
    direct = mat + cons
    full   = direct + hh

    # Reference extrapolated costs
    exp_mat  = round((anchor["mat_total"]  or 0) * factor) if (factor and anchor.get("mat_total"))  else None
    exp_cons = round((anchor["cons_total"] or 0) * factor) if (factor and anchor.get("cons_total")) else None
    exp_full = (exp_mat or 0) + (exp_cons or 0) + hh if (exp_mat is not None) else None

    cols = st.columns(4)
    for col, (label, val, exp, color) in zip(cols, [
        ("Materiales",   mat,  exp_mat,  "#3fb950"),
        ("Consumibles",  cons, exp_cons, "#e3b341"),
        ("Mano de Obra", hh,   None,     "#79c0ff"),
        ("TOTAL DIRECTO",full, exp_full, "#f0f6fc"),
    ]):
        ref_html = ""
        if exp is not None and source_key != "empty":
            diff = val - exp
            diff_pct = round(diff / exp * 100) if exp else 0
            color_d = "#3fb950" if abs(diff_pct) < 5 else "#e3b341" if abs(diff_pct) < 20 else "#f85149"
            ref_html = (
                f'<div style="font-size:0.7rem;color:#768390;margin-top:0.2rem;">'
                f'Ref. extrap: {_clp(exp)}</div>'
                f'<div style="font-size:0.7rem;color:{color_d};margin-top:0.1rem;">'
                f'{"+" if diff >= 0 else ""}{_clp(diff)} ({diff_pct:+d}%)</div>'
            )
        col.markdown(
            f'<div class="card" style="text-align:center;">'
            f'<div class="sec-label">{label}</div>'
            f'<div class="num-big" style="color:{color};">{_clp(val)}</div>'
            f'{ref_html}'
            f'</div>',
            unsafe_allow_html=True
        )


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<h2 style="border-bottom:1px solid #21262d;padding-bottom:0.5rem;">'
        '🔬 Auditoría de Producto</h2>',
        unsafe_allow_html=True
    )

    rules    = load_rules()
    products = _all_products()

    if not products:
        st.warning("No hay productos en la base de datos.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    fc, sc = st.columns([2, 3])
    with fc:
        all_profiles  = ["(Todos)"] + sorted({p.get("perfil_proceso") or "—" for p in products})
        sel_profile   = st.selectbox("Filtrar por perfil", all_profiles, key="aud_prof")
    with sc:
        search_q = st.text_input("Buscar handle / descripción", placeholder="bapla, basurero…", key="aud_srch")

    filtered = products
    if sel_profile != "(Todos)":
        filtered = [p for p in filtered if p.get("perfil_proceso") == sel_profile]
    if search_q:
        q = search_q.lower()
        filtered = [p for p in filtered if q in p["handle"].lower() or q in (p.get("descripcion_web") or "").lower()]

    if not filtered:
        st.info("Ningún producto coincide.")
        return

    # ── Product selector ──────────────────────────────────────────────────────
    def _lbl(p):
        comp = p.get("complejidad") or "?"
        mat  = _pj(p.get("bom_materials"),  [])
        cons = _pj(p.get("bom_consumables"), [])
        mt   = sum(_nan(r.get("total")) for r in mat)
        ct   = sum(_nan(r.get("Total")) for r in cons)
        bom_indicator = "📋" if (mat or cons) else "⚪"
        return f"{bom_indicator} [{p.get('perfil_proceso','—')} · {comp}]  {p['handle']}  —  {_clp(mt+ct)}"

    opts = [_lbl(p) for p in filtered]
    idx  = st.selectbox("Producto", range(len(opts)), format_func=lambda i: opts[i], key="aud_sel")
    product = filtered[idx]

    st.divider()

    # ── Header ────────────────────────────────────────────────────────────────
    render_header(product)

    # ── Compute extrapolation context ─────────────────────────────────────────
    profile_key = product.get("perfil_proceso","")
    comp        = product.get("complejidad","?")
    anchor      = _anchor_data(profile_key, comp, rules)

    L0 = _nan(product.get("dim_l_mm"))
    W0 = _nan(product.get("dim_w_mm"))
    H0 = _nan(product.get("dim_h_mm"))
    e0 = _nan(product.get("dim_espesor_mm"))
    factor      = _factor_escala(L0, W0, H0, anchor)
    mat_rows    = _pj(product.get("bom_materials"),  [])
    cons_rows   = _pj(product.get("bom_consumables"), [])
    source_html, source_key = _source_badge(mat_rows, cons_rows, anchor, factor)

    # ── Top row: dims editor + extrap status ──────────────────────────────────
    dc, sc2 = st.columns([3, 2])
    with dc:
        L, W, H, e = render_dimensions_editor(product, rules)
    with sc2:
        render_extrap_status(product, rules, factor, anchor, source_html, source_key)
        render_drivers(L, W, H, e, product, rules)

    # ── Profile + tier ────────────────────────────────────────────────────────
    proc_list, comp = render_profile_tier(product, rules)

    # ── BOM editors: materials + consumables side by side ─────────────────────
    mc, cc = st.columns([1, 1])
    with mc:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        mat_total  = render_materials_editor(product)
        st.markdown('</div>', unsafe_allow_html=True)
    with cc:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        cons_total = render_consumables_editor(product)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── X flags editor ────────────────────────────────────────────────────────
    with st.expander("✏️ Editar características X + driver C", expanded=False):
        render_x_flags_editor(product, rules)

    # ── HH costs ──────────────────────────────────────────────────────────────
    hh_total = render_hh_costs(proc_list, comp, rules)

    # ── Totals ────────────────────────────────────────────────────────────────
    st.divider()
    render_totals(mat_total, cons_total, hh_total, factor, anchor, source_key)


if __name__ == "__main__":
    main()
