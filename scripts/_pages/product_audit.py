"""
product_audit.py — Dulox Product Cost Audit View
==================================================
Per-product cost breakdown:
  • Universal driver scores (G / D / C / X) computed from dimensions
  • Profile + complexity assignment
  • BOM materials cost
  • Consumables grouped by process
  • Process time costs (HH) from templates
  • Total direct cost with section subtotals

Run:  streamlit run scripts/review.py  (loaded as a Streamlit page)
"""

import json
import math
import sys
import streamlit as st
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from db import load_rules, get_sb, load_all_products

# ─── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
<style>
html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"] { background-color:#0d1117 !important; color:#e6edf3 !important; }
[data-testid="stSidebar"] { background-color:#161b22 !important; border-right:1px solid #30363d; }
[data-testid="stSidebar"] * { color:#c9d1d9 !important; }
h1,h2,h3,h4 { color:#f0f6fc !important; }
.card { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.card-blue { background:#0d2137; border:1px solid #1f6feb; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.card-green { background:#0d2818; border:1px solid #238636; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.card-warn  { background:#2d1b00; border:1px solid #9e6a03; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.sec-label { font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:#768390; margin-bottom:0.3rem; }
.num-big { font-size:1.5rem; font-weight:700; color:#e6edf3; line-height:1.2; }
.num-med { font-size:1.1rem; font-weight:600; color:#cdd9e5; }
.driver-chip { display:inline-block; background:#1f2d3d; border:1px solid #2d4a6a; border-radius:6px;
               padding:4px 10px; margin:2px; font-size:0.82rem; font-weight:600; color:#79c0ff; }
.driver-chip.score1 { background:#0d3321; border-color:#238636; color:#3fb950; }
.driver-chip.score2 { background:#2d2000; border-color:#9e6a03; color:#e3b341; }
.driver-chip.score3 { background:#3d0c0c; border-color:#da3633; color:#f85149; }
.badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:700; }
.badge-c1 { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-c2 { background:#2d1b00; color:#e3b341; border:1px solid #9e6a03; }
.badge-c3 { background:#3d0c0c; color:#f85149; border:1px solid #da3633; }
.badge-ok  { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-warn { background:#2d1b00; color:#e3b341; border:1px solid #9e6a03; }
.badge-err  { background:#3d0c0c; color:#f85149; border:1px solid #da3633; }
.proc-header { font-size:0.88rem; font-weight:700; color:#cdd9e5; margin-bottom:0.4rem; }
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
    """NaN-safe float coerce."""
    if v is None or (isinstance(v, float) and v != v):
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

def _badge(comp: str) -> str:
    cls = {"C1": "badge-c1", "C2": "badge-c2", "C3": "badge-c3"}.get(comp, "badge")
    return f'<span class="badge {cls}">{comp}</span>'

def _driver_chip(label: str, score, value_str: str = "") -> str:
    sc = int(score) if score else 0
    cls = {1: "score1", 2: "score2", 3: "score3"}.get(sc, "")
    tip = f" ({value_str})" if value_str else ""
    return f'<span class="driver-chip {cls}">{label} = {sc}{tip}</span>'

# ─── Score functions (duplicated here to keep page self-contained) ─────────────

def _compute_G(L, W, H, rules):
    if not L or not W:
        return None, None
    area = 2 * (L + W) * (H or 0) + L * W
    bp = rules["driver_thresholds"]["G"]["breakpoints_mm2"]
    score = 1 if area < bp[0] else (2 if area < bp[1] else 3)
    return score, area

def _compute_D(e, rules):
    if not e:
        return None
    bp = rules["driver_thresholds"]["D"]["breakpoints_mm"]
    return 1 if e <= bp[0] else (2 if e <= bp[1] else 3)

def _compute_C(count, rules):
    if not count:
        return None
    bp = rules["driver_thresholds"].get("C", {}).get("breakpoints", [3, 7])
    return 1 if count <= bp[0] else (2 if count <= bp[1] else 3)

def _compute_X(x_flags_list, x_defs):
    pts = sum(x_defs.get(f, {}).get("points", 0) for f in x_flags_list)
    return pts

def _compute_total_score(G, D, C, X_pts, primary_drivers, secondary_drivers):
    active = set((primary_drivers or []) + (secondary_drivers or []))
    pts = 0
    if G and "G" in active: pts += G
    if D and "D" in active: pts += D
    if C and "C" in active: pts += C
    pts += X_pts
    return pts

def _assign_complexity(pts, thresholds):
    for comp in ["C1", "C2", "C3"]:
        t = thresholds.get(comp, {})
        lo = t.get("min_points", 0)
        hi = t.get("max_points", 99)
        if lo <= pts <= hi:
            return comp
    return "?"

# ─── Load helpers ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def _load_products_with_bom() -> list[dict]:
    """Return all products that have at least mat or cons BOM."""
    rows = get_sb().table("products").select(
        "handle,descripcion_web,perfil_proceso,complejidad,familia,subfamilia,"
        "dim_l_mm,dim_w_mm,dim_h_mm,dim_espesor_mm,g_score,d_score,"
        "c_value,x_flags,bom_materials,bom_consumables,is_anchor,image_url"
    ).order("perfil_proceso,handle").execute().data or []
    result = []
    for r in rows:
        mat  = _parse_json(r.get("bom_materials"),  [])
        cons = _parse_json(r.get("bom_consumables"), [])
        if mat or cons:
            r["_mat"]  = mat
            r["_cons"] = cons
            result.append(r)
    return result

def _parse_json(raw, default):
    if isinstance(raw, list):
        return raw
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default

def _parse_xflags(raw):
    if isinstance(raw, list): return raw
    try:
        v = json.loads(raw or "[]")
        return v if isinstance(v, list) else []
    except Exception:
        return []

# ─── Render sections ──────────────────────────────────────────────────────────

def render_identity(product: dict):
    """Header: image + basic identity."""
    col_img, col_info = st.columns([1, 4])
    with col_img:
        img = product.get("image_url")
        if img:
            st.image(img, width=110)
    with col_info:
        st.markdown(
            f'<div style="margin-bottom:0.2rem;">'
            f'<span style="font-size:1.25rem;font-weight:700;color:#f0f6fc;">'
            f'{product.get("descripcion_web") or product["handle"]}</span></div>'
            f'<div style="font-size:0.82rem;color:#768390;margin-bottom:0.5rem;">'
            f'<code style="color:#79c0ff;">{product["handle"]}</code>'
            f'  ·  {product.get("familia","—")} / {product.get("subfamilia","—")}</div>',
            unsafe_allow_html=True
        )


def render_drivers(product: dict, rules: dict):
    """Universal driver scores + complexity assignment."""
    L = _nan(product.get("dim_l_mm"))
    W = _nan(product.get("dim_w_mm"))
    H = _nan(product.get("dim_h_mm"))
    e = _nan(product.get("dim_espesor_mm"))
    c_raw   = product.get("c_value")
    c_count = int(_nan(c_raw))
    x_list  = _parse_xflags(product.get("x_flags"))

    profile_key   = product.get("perfil_proceso", "")
    profile_rules = rules.get("profiles", {}).get(profile_key, {})
    x_defs        = profile_rules.get("x_flags", {})
    thresholds    = profile_rules.get("complexity_thresholds", {})
    primary       = profile_rules.get("primary_drivers", [])
    secondary     = profile_rules.get("secondary_drivers", [])
    c_driver      = profile_rules.get("c_driver")

    G, area = _compute_G(L, W, H, rules)
    D       = _compute_D(e, rules)
    C       = _compute_C(c_count, rules) if (c_count and c_driver) else None
    X_pts   = _compute_X(x_list, x_defs)
    total_pts = _compute_total_score(G, D, C, X_pts, primary, secondary)
    model_comp = _assign_complexity(total_pts, thresholds)
    db_comp    = product.get("complejidad") or "?"
    match = model_comp == db_comp

    area_m2 = f"{area/1e6:.3f} m²" if area else "—"
    dims_str = f"L={int(L)} × W={int(W)} × H={int(H)} mm  ·  e={e} mm" if L else "Sin dimensiones"

    # Driver chips
    chips = ""
    if G is not None: chips += _driver_chip("G", G, area_m2)
    if D is not None: chips += _driver_chip("D", D, f"{e} mm")
    if C is not None: chips += _driver_chip("C", C, f"{c_count} {c_driver or ''}")
    if X_pts > 0:
        x_labels = ", ".join(x_defs.get(f, {}).get("label", f)[:18] for f in x_list if f in x_defs)
        chips += _driver_chip("X", min(X_pts, 3), x_labels)

    # X flags
    x_html = ""
    if x_list:
        x_html = "".join(
            f'<div style="font-size:0.78rem;color:#8b949e;margin-top:0.2rem;">'
            f'• {x_defs.get(f,{}).get("label", f)} <span style="color:#79c0ff;">+{x_defs.get(f,{}).get("points",0)}pts</span></div>'
            for f in x_list
        )

    match_html = (
        f'<span class="badge badge-ok">✅ Modelo coincide</span>'
        if match else
        f'<span class="badge badge-warn">⚠️ Modelo→{model_comp}  ·  DB→{db_comp}</span>'
    )

    st.markdown(
        f'<div class="card">'
        f'<div class="sec-label">DRIVERS UNIVERSALES</div>'
        f'<div style="font-size:0.78rem;color:#768390;margin-bottom:0.5rem;">{dims_str}</div>'
        f'<div style="margin-bottom:0.6rem;">{chips}</div>'
        f'{x_html}'
        f'<div style="margin-top:0.7rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;">'
        f'<span style="color:#8b949e;font-size:0.85rem;">Score total: '
        f'<b style="color:#79c0ff;">{total_pts} pts</b></span>'
        f'<span style="color:#8b949e;font-size:0.85rem;">→</span>'
        f'{_badge(model_comp)}'
        f'<span style="color:#8b949e;font-size:0.8rem;">DB:</span>{_badge(db_comp)}'
        f'<span style="margin-left:0.5rem;">{match_html}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    return {"G": G, "D": D, "C": C, "X_pts": X_pts, "total_pts": total_pts,
            "model_comp": model_comp, "db_comp": db_comp}


def render_profile_tier(product: dict, rules: dict):
    """Profile + complexity tier + assigned processes."""
    profile_key   = product.get("perfil_proceso") or "—"
    comp          = product.get("complejidad") or "?"
    profile_rules = rules.get("profiles", {}).get(profile_key, {})
    tier_desc     = profile_rules.get("complexity_thresholds", {}).get(comp, {}).get("description", "")
    primary       = profile_rules.get("primary_drivers", [])
    secondary     = profile_rules.get("secondary_drivers", [])
    c_driver      = profile_rules.get("c_driver") or "—"
    description   = profile_rules.get("description", "")

    # Process tiers (which processes are active at this complexity)
    process_tiers = profile_rules.get("process_tiers", {})

    # Determine active processes: any process that has a level for this comp
    active_processes = []
    for proc, tier_def in process_tiers.items():
        levels = tier_def if isinstance(tier_def, dict) else {}
        if comp in levels:
            active_processes.append((proc, levels[comp]))

    proc_pills = " ".join(
        f'<span style="background:#1f2d3d;border:1px solid #2d4a6a;border-radius:5px;'
        f'padding:2px 8px;font-size:0.75rem;color:#79c0ff;margin:2px;display:inline-block;">'
        f'{proc.replace("_"," ")}</span>'
        for proc, _ in active_processes
    ) or '<span style="color:#484f58;font-size:0.78rem;">Sin procesos configurados</span>'

    st.markdown(
        f'<div class="card">'
        f'<div class="sec-label">PERFIL DE PROCESO</div>'
        f'<div style="display:flex;align-items:center;gap:0.8rem;flex-wrap:wrap;margin-bottom:0.5rem;">'
        f'<span style="font-size:0.95rem;font-weight:700;color:#cdd9e5;">{profile_key}</span>'
        f'{_badge(comp)}'
        f'</div>'
        f'<div style="font-size:0.78rem;color:#8b949e;margin-bottom:0.4rem;">{description}</div>'
        f'<div style="font-size:0.78rem;color:#8b949e;margin-bottom:0.6rem;">'
        f'Complejidad <b style="color:#cdd9e5;">{comp}</b>: {tier_desc}</div>'
        f'<div style="font-size:0.75rem;color:#768390;margin-bottom:0.3rem;">'
        f'Drivers: primarios <b style="color:#79c0ff;">{", ".join(primary)}</b>  ·  '
        f'secundarios <b style="color:#79c0ff;">{", ".join(secondary) or "—"}</b>  ·  '
        f'driver-C <b style="color:#79c0ff;">{c_driver}</b></div>'
        f'<div class="sec-label" style="margin-top:0.6rem;">PROCESOS ACTIVOS EN {comp}</div>'
        f'<div style="margin-top:0.2rem;">{proc_pills}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    return active_processes


def render_materials(product: dict) -> int:
    """BOM materials table."""
    mat = product.get("_mat", [])
    if not mat:
        st.markdown(
            '<div class="card"><div class="sec-label">MATERIALES</div>'
            '<div style="color:#484f58;font-size:0.82rem;">Sin BOM de materiales guardado.</div></div>',
            unsafe_allow_html=True
        )
        return 0

    rows = []
    for r in mat:
        total = _nan(r.get("total"))
        if not total:
            # try compute from kg_ml × precio_kg × cantidad
            kg  = _nan(r.get("kg_ml"))
            prc = _nan(r.get("precio_kg"))
            qty = _nan(r.get("Cantidad", 1))
            total = kg * prc * qty
        rows.append({
            "Material":    r.get("Material", ""),
            "Dimensiones": r.get("Dimensiones", ""),
            "kg / ML / u": r.get("kg_ml", ""),
            "$/kg o $/u":  r.get("precio_kg", ""),
            "Cant.":       r.get("Cantidad", 1),
            "Total $":     int(total),
        })

    mat_total = sum(r["Total $"] for r in rows)
    df = pd.DataFrame(rows)

    st.markdown(
        f'<div class="card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">'
        f'<div class="sec-label">MATERIALES — {len(rows)} ítems</div>'
        f'<div class="num-med" style="color:#3fb950;">{_clp(mat_total)}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    st.dataframe(
        df, use_container_width=True, hide_index=True,
        column_config={
            "Total $": st.column_config.NumberColumn(format="$ %d"),
            "kg / ML / u": st.column_config.NumberColumn(format="%.4f"),
        }
    )
    st.markdown('</div>', unsafe_allow_html=True)
    return mat_total


def render_consumables(product: dict, rules: dict) -> int:
    """Consumables grouped by process."""
    cons = product.get("_cons", [])
    if not cons:
        st.markdown(
            '<div class="card"><div class="sec-label">CONSUMIBLES</div>'
            '<div style="color:#484f58;font-size:0.82rem;">Sin consumibles guardados.</div></div>',
            unsafe_allow_html=True
        )
        return 0

    # Group by process
    by_proc: dict[str, list] = {}
    for r in cons:
        proc = r.get("Proceso") or "Sin proceso"
        by_proc.setdefault(proc, []).append(r)

    cons_total = 0
    proc_totals = {}
    for proc, items in by_proc.items():
        t = sum(_nan(r.get("Total")) for r in items)
        proc_totals[proc] = t
        cons_total += t

    st.markdown(
        f'<div class="card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.6rem;">'
        f'<div class="sec-label">CONSUMIBLES POR PROCESO — {len(cons)} ítems</div>'
        f'<div class="num-med" style="color:#e3b341;">{_clp(cons_total)}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    for proc, items in by_proc.items():
        subtotal = proc_totals[proc]
        rows = []
        for r in items:
            total = _nan(r.get("Total"))
            rows.append({
                "Producto":  r.get("Producto", ""),
                "Cantidad":  r.get("Cantidad", ""),
                "Unidad":    r.get("Unidad", ""),
                "Precio u.": int(_nan(r.get("Precio_u"))),
                "Total $":   int(total),
            })
        df = pd.DataFrame(rows)
        proc_label = proc.replace("_", " ").title()
        with st.expander(f"**{proc_label}** — {_clp(subtotal)}", expanded=True):
            st.dataframe(
                df, use_container_width=True, hide_index=True,
                column_config={
                    "Total $":   st.column_config.NumberColumn(format="$ %d"),
                    "Precio u.": st.column_config.NumberColumn(format="$ %d"),
                    "Cantidad":  st.column_config.NumberColumn(format="%.3f"),
                }
            )

    st.markdown('</div>', unsafe_allow_html=True)
    return cons_total


def render_process_hh(product: dict, active_processes: list, rules: dict) -> int:
    """Process HH cost from templates × HH rates."""
    comp = product.get("complejidad") or "?"
    hh_rates = rules.get("process_costs", {}).get("hh_rates", {})
    templates = rules.get("process_costs", {}).get("process_templates", {})

    if not active_processes:
        st.markdown(
            '<div class="card"><div class="sec-label">COSTOS DE PROCESO (HH)</div>'
            '<div style="color:#484f58;font-size:0.82rem;">Sin procesos configurados para este perfil/nivel.</div></div>',
            unsafe_allow_html=True
        )
        return 0

    rows = []
    total_hh_cost = 0
    for proc, proc_comp in active_processes:
        tpl = templates.get(proc, {}).get(proc_comp, {})
        if not tpl:
            tpl = templates.get(proc, {}).get(comp, {})
        t_setup  = _nan(tpl.get("T_setup_min"))
        t_exec   = _nan(tpl.get("T_exec_min"))
        n_ops    = _nan(tpl.get("n_ops", 1)) or 1
        rate     = _nan(hh_rates.get(proc))
        t_total  = t_setup + t_exec
        hh_cost  = round((t_total / 60) * rate * n_ops) if (t_total and rate) else None
        if hh_cost:
            total_hh_cost += hh_cost
        rows.append({
            "Proceso":       proc.replace("_", " "),
            "Nivel proceso": proc_comp,
            "T_setup (min)": int(t_setup) if t_setup else "—",
            "T_exec (min)":  int(t_exec)  if t_exec  else "—",
            "Ops":           int(n_ops),
            "$/HH":          int(rate)    if rate    else "—",
            "Costo HH $":    hh_cost      if hh_cost else "—",
        })

    df = pd.DataFrame(rows)
    st.markdown(
        f'<div class="card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">'
        f'<div class="sec-label">COSTOS DE PROCESO (MANO DE OBRA)</div>'
        f'<div class="num-med" style="color:#79c0ff;">{_clp(total_hh_cost) if total_hh_cost else "—"}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    st.dataframe(
        df, use_container_width=True, hide_index=True,
        column_config={
            "$/HH":       st.column_config.NumberColumn(format="$ %d"),
            "Costo HH $": st.column_config.NumberColumn(format="$ %d"),
        }
    )
    st.markdown('</div>', unsafe_allow_html=True)
    return total_hh_cost


def render_total(mat_total: int, cons_total: int, hh_total: int):
    """Total cost summary card."""
    direct = mat_total + cons_total
    full   = direct + hh_total

    cols = st.columns(4)
    for col, (label, val, color) in zip(cols, [
        ("Materiales",     mat_total,  "#3fb950"),
        ("Consumibles",    cons_total, "#e3b341"),
        ("Mano de Obra",   hh_total,   "#79c0ff"),
        ("TOTAL DIRECTO",  full,       "#f0f6fc"),
    ]):
        col.markdown(
            f'<div class="card" style="text-align:center;">'
            f'<div class="sec-label">{label}</div>'
            f'<div class="num-big" style="color:{color};">{_clp(val)}</div>'
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

    rules = load_rules()
    products = _load_products_with_bom()

    if not products:
        st.warning("No hay productos con BOM guardado. Ve a Calibración → BOM + Importar para ingresar datos.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    filter_col, search_col = st.columns([2, 3])

    with filter_col:
        all_profiles = sorted({p.get("perfil_proceso") or "—" for p in products})
        selected_profile = st.selectbox("Filtrar por perfil", ["(Todos)"] + all_profiles, key="audit_profile")

    with search_col:
        search_q = st.text_input("Buscar por handle o descripción", placeholder="bapla, basurero plaza...", key="audit_search")

    # Apply filters
    filtered = products
    if selected_profile != "(Todos)":
        filtered = [p for p in filtered if p.get("perfil_proceso") == selected_profile]
    if search_q:
        q = search_q.lower()
        filtered = [p for p in filtered if q in p["handle"].lower() or q in (p.get("descripcion_web") or "").lower()]

    if not filtered:
        st.info("Ningún producto coincide con los filtros.")
        return

    # ── Product selector ──────────────────────────────────────────────────────
    def _label(p):
        comp = p.get("complejidad") or "?"
        mat  = sum(_nan(r.get("total"))  for r in p.get("_mat",  []))
        cons = sum(_nan(r.get("Total"))  for r in p.get("_cons", []))
        return f"[{p.get('perfil_proceso','—')} · {comp}]  {p['handle']}  —  mat {_clp(mat)}  cons {_clp(cons)}"

    options = [_label(p) for p in filtered]
    sel_idx = st.selectbox("Seleccionar producto", range(len(options)),
                           format_func=lambda i: options[i], key="audit_sel")
    product = filtered[sel_idx]

    st.divider()

    # ── Identity ──────────────────────────────────────────────────────────────
    render_identity(product)

    # ── Two-column layout: left = profile+drivers, right = cost sections ─────
    col_left, col_right = st.columns([1, 1])

    with col_left:
        scores        = render_drivers(product, rules)
        active_procs  = render_profile_tier(product, rules)

    with col_right:
        mat_total  = render_materials(product)
        cons_total = render_consumables(product, rules)

    # ── Process HH costs (full width) ────────────────────────────────────────
    hh_total = render_process_hh(product, active_procs, rules)

    # ── Total ─────────────────────────────────────────────────────────────────
    st.divider()
    render_total(mat_total, cons_total, hh_total)


if __name__ == "__main__":
    main()
