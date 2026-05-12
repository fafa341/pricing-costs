"""
product_audit.py — Dulox Product Cost Audit & Edit View
=========================================================
Template source logic:
  ⭐ Ancla       — this product IS the anchor; BOM is the reference
  🔵 Extrapolado — no own BOM; shows anchor BOM × factor_escala live
  🟡 Editado     — has own BOM (forked from anchor, possibly modified)
  ⚪ Sin datos   — no BOM and no anchor configured for this profile/level

Flow for extrapolated products:
  1. Load anchor product BOM from DB
  2. Scale each row by factor_escala (area_product / area_anchor)
  3. Display scaled rows as preview (read-only with yellow tint)
  4. "Fork template" button → saves scaled rows as product's own BOM
  5. After fork → product becomes 🟡 Editado and rows become fully editable
"""

import json
import math
import sys
import streamlit as st
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "core"))
from db import load_rules, get_sb, save_bom as _save_bom_db
from bom_calc import compute_bom, erp_rows

# ─── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
<style>
html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"] { background-color:#0d1117 !important; color:#e6edf3 !important; }
[data-testid="stSidebar"] { background-color:#161b22 !important; border-right:1px solid #30363d; }
[data-testid="stSidebar"] * { color:#c9d1d9 !important; }
h1,h2,h3,h4 { color:#f0f6fc !important; }
.card  { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.card-anchor { background:#0d2818; border:1px solid #238636; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.card-extrap { background:#0d1e33; border:1px solid #1f6feb; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.card-edited { background:#1e1800; border:1px solid #9e6a03; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.card-empty  { background:#161b22; border:1px solid #484f58; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.sec-label { font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:#768390; margin-bottom:0.3rem; }
.num-big   { font-size:1.5rem; font-weight:700; color:#e6edf3; line-height:1.2; }
.num-med   { font-size:1.1rem; font-weight:600; color:#cdd9e5; }
.badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:700; }
.badge-c1     { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-c2     { background:#2d1b00; color:#e3b341; border:1px solid #9e6a03; }
.badge-c3     { background:#3d0c0c; color:#f85149; border:1px solid #da3633; }
.badge-ok     { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-warn   { background:#2d2000; color:#e3b341; border:1px solid #9e6a03; }
.badge-anchor { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-extrap { background:#0d2137; color:#79c0ff; border:1px solid #1f6feb; }
.badge-edited { background:#2d2000; color:#e3b341; border:1px solid #9e6a03; }
.badge-empty  { background:#161b22; color:#8b949e; border:1px solid #484f58; }
.driver-chip { display:inline-block; background:#1f2d3d; border:1px solid #2d4a6a;
               border-radius:6px; padding:4px 10px; margin:2px 3px; font-size:0.82rem; font-weight:600; color:#79c0ff; }
.driver-1 { background:#0d3321; border-color:#238636; color:#3fb950; }
.driver-2 { background:#2d2000; border-color:#9e6a03; color:#e3b341; }
.driver-3 { background:#3d0c0c; border-color:#da3633; color:#f85149; }
[data-testid="stDataFrameResizable"] { border:1px solid #30363d; border-radius:8px; }
[data-testid="stExpander"] { background:#161b22 !important; border:1px solid #30363d !important; border-radius:8px !important; }
hr { border-color:#21262d !important; }
</style>
"""

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _clp(v) -> str:
    if v is None or (isinstance(v, float) and not math.isfinite(v)): return "—"
    return f"${int(v):,}".replace(",", ".")

def _nan(v) -> float:
    if v is None: return 0.0
    try:
        f = float(v)
        return 0.0 if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return 0.0

def _pj(raw, default=None):
    d = default if default is not None else []
    if isinstance(raw, list): return raw
    if not raw: return d
    try: return json.loads(raw)
    except: return d

def _badge(comp: str) -> str:
    cls = {"C1":"badge-c1","C2":"badge-c2","C3":"badge-c3"}.get(comp,"badge-empty")
    return f'<span class="badge {cls}">{comp or "?"}</span>'

def _chip(label, score, detail=""):
    cls = {1:"driver-1",2:"driver-2",3:"driver-3"}.get(score,"driver-chip")
    tip = f" <span style='color:#768390;font-size:0.72rem;'>({detail})</span>" if detail else ""
    return f'<span class="driver-chip {cls}">{label}={score}{tip}</span>'

# ─── Score functions ───────────────────────────────────────────────────────────

def _G(L, W, H, rules):
    if not L or not W: return None, None
    area = 2*(L+W)*(H or 0) + L*W
    bp   = rules["driver_thresholds"]["G"]["breakpoints_mm2"]
    return (1 if area < bp[0] else 2 if area < bp[1] else 3), area

def _D(e, rules):
    if not e: return None
    bp = rules["driver_thresholds"]["D"]["breakpoints_mm"]
    return 1 if e <= bp[0] else 2 if e <= bp[1] else 3

def _C(count, rules):
    if not count: return None
    bp = rules["driver_thresholds"].get("C",{}).get("breakpoints",[3,7])
    return 1 if count <= bp[0] else 2 if count <= bp[1] else 3

def _total_score(G, D, C, x_pts, primary, secondary):
    active = set((primary or []) + (secondary or []))
    pts = 0
    if G and "G" in active: pts += G
    if D and "D" in active: pts += D
    if C and "C" in active: pts += C
    return pts + x_pts

def _complexity(pts, thresholds):
    for comp in ["C1","C2","C3"]:
        t = thresholds.get(comp,{})
        if t.get("min_points",0) <= pts <= t.get("max_points",99):
            return comp
    return "?"


def _per_process_levels(
    proc_list: list, G, D, C_val, x_list: list, x_defs: dict, rules: dict
) -> dict:
    """
    Compute per-process complexity for each active process.

    Driver selection comes from process_templates[proc]["drivers"].
    Score-to-level thresholds from process_templates[proc]["score_thresholds"]
      — either a list [lo, hi] per comp, or omitted (returns None).
    X flags are filtered by process_scope:
      - empty scope  → flag applies to every process that has "X" as a driver
      - non-empty    → flag applies only to processes listed in scope

    Returns {proc: {level, score, used, x_breakdown, drivers}}
    """
    templates = rules.get("process_templates", {})
    result: dict = {}

    for proc in proc_list:
        tmpl        = templates.get(proc, {})
        proc_drivers = tmpl.get("drivers", [])
        thresholds  = tmpl.get("score_thresholds", {})

        score = 0
        used: dict = {}
        x_breakdown: list = []

        for d in proc_drivers:
            if d == "G":
                if G is not None:
                    score += G; used["G"] = G
                else:
                    used["G"] = "?"
            elif d == "D":
                if D is not None:
                    score += D; used["D"] = D
                else:
                    used["D"] = "?"
            elif d == "C":
                if C_val is not None:
                    score += C_val; used["C"] = C_val
                else:
                    used["C"] = "?"
            elif d == "X":
                x_pts = 0
                for flag in x_list:
                    flag_def = x_defs.get(flag, {})
                    # Normalise scope: process_scope list OR legacy primary_process string
                    scope = flag_def.get("process_scope") or (
                        [flag_def["primary_process"]] if flag_def.get("primary_process") else []
                    )
                    if not scope or proc in scope:
                        pts = flag_def.get("points", 0)
                        x_pts += pts
                        x_breakdown.append({
                            "flag":  flag,
                            "label": flag_def.get("label", flag),
                            "pts":   pts,
                            "scope": scope or ["(todos)"],
                        })
                score += x_pts
                used["X"] = x_pts

        # Map score → level
        level = None
        if thresholds:
            for comp in ["C1", "C2", "C3"]:
                rng = thresholds.get(comp)
                if rng is None:
                    continue
                lo, hi = (rng[0], rng[1]) if isinstance(rng, list) and len(rng) >= 2 else (rng, rng)
                if lo <= score <= hi:
                    level = comp
                    break

        result[proc] = {
            "level":       level,
            "score":       score,
            "used":        used,
            "x_breakdown": x_breakdown,
            "drivers":     proc_drivers,
        }

    return result

# ─── Data loading ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=20)
def _all_products() -> list[dict]:
    return get_sb().table("products").select(
        "handle,descripcion_web,perfil_proceso,complejidad,familia,subfamilia,"
        "dim_l_mm,dim_w_mm,dim_h_mm,dim_espesor_mm,g_score,d_score,"
        "c_value,x_flags,bom_materials,bom_consumables,is_anchor,image_url"
    ).order("perfil_proceso,handle").execute().data or []

@st.cache_data(ttl=20)
def _get_product(handle: str) -> dict | None:
    rows = get_sb().table("products").select(
        "handle,dim_l_mm,dim_w_mm,dim_h_mm,dim_espesor_mm,bom_materials,bom_consumables"
    ).eq("handle", handle).limit(1).execute().data
    return rows[0] if rows else None


def _factor_escala(L, W, H, aL, aW, aH) -> float | None:
    if not (L and W and aL and aW): return None
    area   = 2*(L+W)*(H or 0)  + L*W
    a_area = 2*(aL+aW)*(aH or 0) + aL*aW
    if not a_area: return None
    f = area / a_area
    return round(f, 4) if math.isfinite(f) else None


def _build_system_consumables(
    proc_list: list, per_proc: dict, rules: dict,
    factor: float = 1.0, prod_comp: str = "C1"
) -> list:
    """
    Build consumables from the process catalog (process_consumables[proc][level])
    for each active process, using its derived per-process complexity level.
    Each row is tagged with Proceso. Quantities and Totals are scaled by factor.

    Returns list of dicts with schema: {Producto, Proceso, Cantidad, Unidad, Precio_u, Total}
    """
    catalog = rules.get("process_consumables", {})
    rows: list = []
    for proc in proc_list:
        info  = per_proc.get(proc, {})
        level = info.get("level") or prod_comp   # fallback to product complexity
        items = catalog.get(proc, {}).get(level, [])
        for item in items:
            qty   = _nan(item.get("Cantidad", 1))
            price = _nan(item.get("Precio_u", 0))
            scaled_qty   = round(qty * factor, 4)
            scaled_total = round(scaled_qty * price)
            rows.append({
                "Producto":  item.get("Producto", ""),
                "Proceso":   proc,
                "Cantidad":  scaled_qty,
                "Unidad":    item.get("Unidad", "u"),
                "Precio_u":  int(price),
                "Total":     scaled_total,
            })
    return rows


def _scale_mat_rows(anchor_rows: list, factor: float) -> list:
    """Scale anchor material rows by factor_escala. Supports both old and new schema."""
    out = []
    for r in anchor_rows:
        row = dict(r)
        # New schema: scale L_mm and A_mm, then recompute kg via bom_calc
        if "L_mm" in row or "parte" in row:
            if row.get("L_mm"):
                row["L_mm"] = round(_nan(row.get("L_mm", 0)) * factor, 2)
            if row.get("A_mm"):
                row["A_mm"] = round(_nan(row.get("A_mm", 0)) * factor, 2)
            # Recompute kg + cost after scaling
            computed = compute_bom([row])
            row = computed[0] if computed else row
        else:
            # Old schema fallback: scale total + kg_ml directly
            t   = _nan(row.get("total"))
            kg  = _nan(row.get("kg_ml"))
            row["total"]  = round(t  * factor)
            row["kg_ml"]  = round(kg * factor, 4)
        out.append(row)
    return out


def _scale_cons_rows(anchor_rows: list, factor: float) -> list:
    """Scale anchor consumable rows by factor_escala."""
    out = []
    for r in anchor_rows:
        row = dict(r)
        t   = _nan(row.get("Total"))
        qty = _nan(row.get("Cantidad", 1))
        row["Total"]    = round(t   * factor)
        row["Cantidad"] = round(qty * factor, 3)
        out.append(row)
    return out


def _source(product: dict, anchor_handle: str | None) -> str:
    """
    Return source key:
      'anchor'      — this product is the anchor
      'extrapolado' — no own BOM, anchor has BOM we can scale
      'editado'     — has own BOM saved
      'empty'       — no own BOM and no usable anchor
    """
    handle   = product["handle"]
    mat_raw  = product.get("bom_materials")
    has_own  = bool(mat_raw and mat_raw not in ["[]",""])

    if handle == anchor_handle:
        return "anchor"
    if has_own:
        return "editado"
    if anchor_handle:
        return "extrapolado"
    return "empty"


SOURCE_LABELS = {
    "anchor":      ('⭐ Ancla',       'badge-anchor', 'card-anchor'),
    "extrapolado": ('🔵 Extrapolado', 'badge-extrap', 'card-extrap'),
    "editado":     ('🟡 Editado',     'badge-edited', 'card-edited'),
    "empty":       ('⚪ Sin datos',   'badge-empty',  'card-empty'),
}

# ─── Section renderers ────────────────────────────────────────────────────────

def render_header(product: dict, source: str, anchor_handle: str | None, factor: float | None):
    img = product.get("image_url")
    label, badge_cls, _ = SOURCE_LABELS[source]
    c1, c2 = st.columns([1, 5])
    if img:
        c1.markdown(f'<img src="{img}" style="width:100px;border-radius:4px;">', unsafe_allow_html=True)
    factor_str = f"factor_escala = {factor:.3f}×" if factor else ""
    anchor_str = f" · ancla: <code style='color:#3fb950;'>{anchor_handle}</code>" if (anchor_handle and source != "anchor") else ""
    c2.markdown(
        f'<div style="font-size:1.2rem;font-weight:700;color:#f0f6fc;margin-bottom:0.2rem;">'
        f'{product.get("descripcion_web") or product["handle"]}</div>'
        f'<div style="margin-bottom:0.3rem;">'
        f'<code style="color:#79c0ff;font-size:0.82rem;">{product["handle"]}</code>'
        f'<span style="margin-left:0.8rem;"><span class="badge {badge_cls}">{label}</span></span>'
        f'{"<span style=\"color:#8b949e;font-size:0.78rem;margin-left:0.8rem;\">"+factor_str+"</span>" if factor_str else ""}'
        f'{anchor_str}'
        f'</div>'
        f'<span style="color:#484f58;font-size:0.78rem;">'
        f'{product.get("familia","—")} / {product.get("subfamilia","—")}</span>',
        unsafe_allow_html=True
    )


def render_dims_editor(product: dict, rules: dict):
    handle = product["handle"]
    L0 = _nan(product.get("dim_l_mm"))
    W0 = _nan(product.get("dim_w_mm"))
    H0 = _nan(product.get("dim_h_mm"))
    e0 = _nan(product.get("dim_espesor_mm"))

    with st.form(f"dims_{handle}"):
        st.markdown('<div class="sec-label">DIMENSIONES</div>', unsafe_allow_html=True)
        c1,c2,c3,c4 = st.columns(4)
        L = c1.number_input("Largo mm",   value=L0, min_value=0.0, step=1.0, format="%.0f")
        W = c2.number_input("Ancho mm",   value=W0, min_value=0.0, step=1.0, format="%.0f")
        H = c3.number_input("Alto mm",    value=H0, min_value=0.0, step=1.0, format="%.0f")
        e = c4.number_input("Espesor mm", value=e0, min_value=0.0, step=0.1, format="%.1f")
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
            _get_product.clear()
            st.success("✅ Dimensiones guardadas")
            st.rerun()
    return L, W, H, e


def render_drivers(L, W, H, e, product, rules):
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
    pts     = _total_score(G, D, C, X_pts, primary, secondary)
    model_c = _complexity(pts, thresholds)
    db_c    = product.get("complejidad") or "?"
    match   = model_c == db_c

    area_str = f"{area/1e6:.3f}m²" if area else "—"
    chips = ""
    if G is not None: chips += _chip("G", G, area_str)
    if D is not None: chips += _chip("D", D, f"{e}mm")
    if C is not None: chips += _chip("C", C, f"{c_count}")
    if X_pts > 0:
        xl = ", ".join(x_defs.get(f,{}).get("label",f)[:15] for f in x_list if f in x_defs)
        chips += _chip("X", min(X_pts,3), xl)

    match_html = (
        '<span class="badge badge-ok">✅ Coincide</span>' if match else
        f'<span class="badge badge-warn">⚠️ Modelo→{model_c} · DB→{db_c}</span>'
    )

    st.markdown(
        f'<div class="card" style="margin-bottom:0.5rem;">'
        f'<div class="sec-label">DRIVERS G/D/C/X</div>'
        f'<div style="margin:0.3rem 0 0.5rem 0;">{chips}</div>'
        f'<div style="display:flex;gap:0.8rem;align-items:center;flex-wrap:wrap;">'
        f'<span style="color:#8b949e;font-size:0.85rem;">Score <b style="color:#79c0ff;">{pts}pts</b></span>'
        f'→ {_badge(model_c)} <span style="color:#768390;font-size:0.78rem;">DB:</span> {_badge(db_c)}'
        f'<span>{match_html}</span></div></div>',
        unsafe_allow_html=True
    )


def render_profile_tier(product, L, W, H, e, rules):
    """
    Show per-process complexity matrix:
    — which drivers each process uses
    — per-driver score contribution (with X scoping detail)
    — derived complexity level for each process
    — product-level summary at the top
    """
    profile_key   = product.get("perfil_proceso", "—")
    prod_comp     = product.get("complejidad", "?")
    profile_rules = rules.get("profiles", {}).get(profile_key, {})
    tier_desc     = profile_rules.get("complexity_thresholds", {}).get(prod_comp, {}).get("description", "")
    x_defs        = profile_rules.get("x_flags", {})
    x_list        = _pj(product.get("x_flags"), [])
    c_count       = int(_nan(product.get("c_value")))
    c_driver      = profile_rules.get("c_driver")

    G, area = _G(L, W, H, rules)
    D       = _D(e, rules)
    C_val   = _C(c_count, rules) if (c_count and c_driver) else None

    proc_list = profile_rules.get("process_tiers", {}).get(prod_comp, [])

    # ── Per-process complexity computation ────────────────────────────────────
    per_proc = _per_process_levels(proc_list, G, D, C_val, x_list, x_defs, rules)

    # ── Product-level summary card ────────────────────────────────────────────
    primary   = profile_rules.get("primary_drivers", [])
    secondary = profile_rules.get("secondary_drivers", [])
    st.markdown(
        f'<div class="card" style="margin-bottom:0.5rem;">'
        f'<div class="sec-label">PERFIL · NIVEL PRODUCTO</div>'
        f'<div style="display:flex;gap:0.7rem;align-items:center;margin-bottom:0.2rem;">'
        f'<b style="color:#cdd9e5;">{profile_key}</b>{_badge(prod_comp)}'
        f'<span style="color:#8b949e;font-size:0.75rem;">{tier_desc}</span></div>'
        f'<div style="font-size:0.75rem;color:#768390;">'
        f'Drivers perfil: <b style="color:#79c0ff;">{", ".join(primary+secondary) or "—"}</b>'
        f'{"  ·  Driver-C: <b style=\"color:#79c0ff;\">"+c_driver+"</b>" if c_driver else ""}'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # ── Per-process complexity matrix ─────────────────────────────────────────
    if not proc_list:
        st.markdown(
            '<div class="card"><span style="color:#484f58;font-size:0.82rem;">'
            'Sin procesos configurados para este perfil/nivel.</span></div>',
            unsafe_allow_html=True
        )
        return proc_list, prod_comp, per_proc

    LEVEL_COLOR = {"C1": "#3fb950", "C2": "#e3b341", "C3": "#f85149"}
    DRIVER_COLOR = {"G": "#79c0ff", "D": "#d2a8ff", "C": "#ffa657", "X": "#e3b341"}
    BADGE_CLS   = {"C1": "badge-c1", "C2": "badge-c2", "C3": "badge-c3"}

    st.markdown(
        '<div class="sec-label" style="margin-top:0.2rem;margin-bottom:0.3rem;">'
        'COMPLEJIDAD POR PROCESO</div>',
        unsafe_allow_html=True
    )

    for proc in proc_list:
        info    = per_proc.get(proc, {})
        level   = info.get("level")
        score   = info.get("score", 0)
        used    = info.get("used", {})
        xb      = info.get("x_breakdown", [])
        drivers = info.get("drivers", [])

        # Build driver score chips
        driver_chips = ""
        for d in drivers:
            val = used.get(d)
            if val == "?":
                driver_chips += (
                    f'<span style="display:inline-block;background:#1a1a2e;border:1px dashed #484f58;'
                    f'border-radius:5px;padding:2px 8px;font-size:0.73rem;color:#484f58;margin:1px 3px;">'
                    f'{d}=?</span>'
                )
            elif val is not None:
                c = DRIVER_COLOR.get(d, "#79c0ff")
                driver_chips += (
                    f'<span style="display:inline-block;background:#1a2a3a;border:1px solid {c}33;'
                    f'border-radius:5px;padding:2px 8px;font-size:0.73rem;color:{c};margin:1px 3px;">'
                    f'{d}={val}</span>'
                )
            else:
                driver_chips += (
                    f'<span style="display:inline-block;background:#1a1a2e;border:1px dashed #484f58;'
                    f'border-radius:5px;padding:2px 8px;font-size:0.73rem;color:#484f58;margin:1px 3px;">'
                    f'{d}=—</span>'
                )

        # X flag detail (only when X is a driver)
        x_detail = ""
        if "X" in drivers and xb:
            flag_strs = []
            for fx in xb:
                scope_note = ""
                if fx["scope"] and fx["scope"] != ["(todos)"]:
                    scope_note = f' <span style="color:#484f58;">[{", ".join(fx["scope"])}]</span>'
                flag_strs.append(
                    f'<span style="color:#e3b341;">{fx["label"]}</span>'
                    f' <span style="color:#768390;">+{fx["pts"]}pts</span>{scope_note}'
                )
            x_detail = (
                f'<div style="font-size:0.7rem;color:#768390;margin-left:0.3rem;margin-top:2px;">'
                f'X flags: {" · ".join(flag_strs)}</div>'
            ) if flag_strs else ""
        elif "X" in drivers:
            x_detail = (
                '<div style="font-size:0.7rem;color:#484f58;margin-left:0.3rem;margin-top:2px;">'
                'X=0 (sin características activas)</div>'
            )

        if level:
            lc = LEVEL_COLOR.get(level, "#8b949e")
            bc = BADGE_CLS.get(level, "badge-empty")
            level_html = (
                f'<span class="badge {bc}">{level}</span>'
                f'<span style="color:#768390;font-size:0.72rem;margin-left:0.4rem;">score {score}</span>'
            )
        else:
            level_html = (
                f'<span style="color:#484f58;font-size:0.78rem;">'
                f'Sin umbrales · score {score}</span>'
            )

        no_tmpl = not rules.get("process_templates", {}).get(proc, {}).get("drivers")
        tmpl_warn = (
            '<span style="color:#484f58;font-size:0.7rem;margin-left:0.5rem;">'
            '(sin template de drivers)</span>'
            if no_tmpl else ""
        )

        st.markdown(
            f'<div style="display:flex;align-items:flex-start;gap:0.6rem;'
            f'border-bottom:1px solid #21262d;padding:0.35rem 0.2rem;">'
            f'<div style="min-width:140px;font-size:0.8rem;font-weight:600;color:#cdd9e5;padding-top:2px;">'
            f'{proc.replace("_"," ")}{tmpl_warn}</div>'
            f'<div style="flex:1;">'
            f'<div style="margin-bottom:1px;">{driver_chips}</div>'
            f'{x_detail}</div>'
            f'<div style="min-width:110px;text-align:right;">{level_html}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown('<div style="height:0.4rem;"></div>', unsafe_allow_html=True)
    return proc_list, prod_comp, per_proc


def render_bom_extrapolated(
    anchor_mat: list, system_cons: list, factor: float, handle: str
):
    """
    Show extrapolated BOM:
    - Materials: anchor BOM × factor_escala (product-specific)
    - Consumables: process catalog × per-process levels × factor (system-derived)
    Both are read-only. Fork button saves them as the product's own BOM.
    """
    scaled_mat = _scale_mat_rows(anchor_mat, factor)
    mat_total  = sum(_nan(r.get("total")) for r in scaled_mat)
    cons_total = sum(_nan(r.get("Total")) for r in system_cons)

    st.markdown(
        f'<div style="background:#0a1929;border:1px dashed #1f6feb;border-radius:8px;'
        f'padding:0.6rem 1rem;margin-bottom:0.6rem;font-size:0.8rem;color:#79c0ff;">'
        f'🔵 Template extrapolado · factor = {factor:.3f}× · '
        f'mat <b>{_clp(mat_total)}</b> · cons <b>{_clp(cons_total)}</b> · '
        f'total <b style="color:#3fb950;">{_clp(mat_total+cons_total)}</b>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Materials preview (scaled from anchor)
    if scaled_mat:
        st.markdown(
            '<div class="sec-label">MATERIALES — ancla × factor_escala</div>',
            unsafe_allow_html=True
        )
        df_mat = pd.DataFrame([{
            "Material":    r.get("Material", ""),
            "Dimensiones": r.get("Dimensiones", ""),
            "kg/ML/u":     r.get("kg_ml", ""),
            "$/kg o $/u":  r.get("precio_kg", ""),
            "Cant.":       r.get("Cantidad", 1),
            "Total $":     int(_nan(r.get("total"))),
        } for r in scaled_mat])
        st.dataframe(df_mat, use_container_width=True, hide_index=True,
                     column_config={"Total $": st.column_config.NumberColumn(format="$ %d")})

    # Consumables preview — from process catalog, grouped by process
    st.markdown(
        '<div class="sec-label" style="margin-top:0.8rem;">'
        'CONSUMIBLES — catálogo de procesos × nivel × factor_escala</div>',
        unsafe_allow_html=True
    )
    if system_cons:
        by_proc: dict[str, list] = {}
        for r in system_cons:
            by_proc.setdefault(r.get("Proceso", "—"), []).append(r)
        for proc, rows in by_proc.items():
            sub = sum(_nan(r.get("Total")) for r in rows)
            with st.expander(
                f"{proc.replace('_',' ')} — {_clp(sub)}", expanded=True
            ):
                df_c = pd.DataFrame([{
                    "Producto":  r.get("Producto", ""),
                    "Cantidad":  r.get("Cantidad", ""),
                    "Unidad":    r.get("Unidad", ""),
                    "Precio u.": int(_nan(r.get("Precio_u"))),
                    "Total $":   int(_nan(r.get("Total"))),
                } for r in rows])
                st.dataframe(df_c, use_container_width=True, hide_index=True,
                             column_config={
                                 "Total $":   st.column_config.NumberColumn(format="$ %d"),
                                 "Precio u.": st.column_config.NumberColumn(format="$ %d"),
                             })
    else:
        st.caption("Sin consumibles configurados para los procesos activos.")

    # Fork button → saves as product's own editable BOM
    st.markdown('<div style="margin-top:0.8rem;"></div>', unsafe_allow_html=True)
    if st.button(
        "🍴 Fork template — guardar como BOM propio de este producto",
        key=f"fork_{handle}", type="primary", use_container_width=True
    ):
        _save_bom_db(handle, scaled_mat, system_cons)
        _all_products.clear()
        _get_product.clear()
        st.success("✅ BOM forkeado. Ahora puedes editarlo.")
        st.rerun()

    return mat_total, cons_total


_AUDIT_MAT_EDIT_COLS = ["parte", "tipo", "calidad", "esp_mm", "L_mm", "A_mm", "cant", "simbolos"]
_AUDIT_MAT_TIPO  = ["Plancha", "Perfil", "Tubo", "Macizo"]
_AUDIT_MAT_CAL   = ["304", "201", "316", "430"]

def _audit_mat_empty():
    return {"parte": "", "tipo": "Plancha", "calidad": "304",
            "esp_mm": None, "L_mm": None, "A_mm": None, "cant": 1, "simbolos": ""}

def _audit_migrate(r: dict) -> dict:
    if "parte" in r:
        return {**_audit_mat_empty(), **{k: r[k] for k in _AUDIT_MAT_EDIT_COLS if k in r}}
    new = _audit_mat_empty()
    new["parte"] = r.get("Subconjunto", "") or r.get("Material", "")
    return new


def render_bom_editable(product: dict, system_cons: list):
    """
    Editable BOM for anchor/editado products.
    Uses new schema: parte/tipo/calidad/esp_mm/L_mm/A_mm/cant/simbolos.
    Computed columns shown as read-only table below editor (no write-back loop).
    """
    handle    = product["handle"]
    saved_mat = _pj(product.get("bom_materials"),  [])
    saved_con = _pj(product.get("bom_consumables"), [])

    # ── Materials ─────────────────────────────────────────────────────────────
    mat_init = [_audit_migrate(r) for r in saved_mat] or [_audit_mat_empty()]
    ms, mh = f"aud_mat_{handle}", f"aud_mh_{handle}"
    mhash  = hash(str(mat_init))
    if st.session_state.get(mh) != mhash:
        st.session_state[ms] = pd.DataFrame(mat_init)
        st.session_state[mh] = mhash

    st.markdown('<div class="sec-label">MATERIALES</div>', unsafe_allow_html=True)
    st.caption("Completar: Parte · Tipo · Calidad · esp/L/A mm · Cant · Símbolos")

    edited_mat = st.data_editor(
        st.session_state[ms][_AUDIT_MAT_EDIT_COLS],
        key=f"aud_bomedit_{handle}",
        use_container_width=True, num_rows="dynamic", hide_index=True,
        column_config={
            "parte":    st.column_config.TextColumn("Parte", width="medium"),
            "tipo":     st.column_config.SelectboxColumn("Tipo", options=_AUDIT_MAT_TIPO, width="small"),
            "calidad":  st.column_config.SelectboxColumn("Calidad", options=_AUDIT_MAT_CAL, width="small"),
            "esp_mm":   st.column_config.NumberColumn("esp mm", format="%.1f", step=0.5, width="small"),
            "L_mm":     st.column_config.NumberColumn("L mm",   format="%.0f", step=1.0, width="small"),
            "A_mm":     st.column_config.NumberColumn("A/Ø mm", format="%.0f", step=1.0, width="small"),
            "cant":     st.column_config.NumberColumn("Cant",   format="%d",   step=1,   width="small"),
            "simbolos": st.column_config.TextColumn("Símbolos", help="P1 P2 T4 ⊙ S V M EXT", width="small"),
        },
    )

    # Computed display (read-only — no write-back loop)
    computed = []
    mat_total = 0
    if isinstance(edited_mat, pd.DataFrame) and not edited_mat.empty:
        computed = compute_bom(edited_mat.to_dict("records"))
        mat_total = sum(int(r.get("total_clp") or 0) for r in computed)
        comp_display = pd.DataFrame([{
            "Parte": r.get("parte",""), "SKU": r.get("sku_material","—"),
            "kg bruto/u": r.get("kg_bruto", 0), "Cant": r.get("cant",1),
            "$/kg": r.get("precio_kg",0), "Total $": r.get("total_clp",0),
        } for r in computed])
        st.dataframe(comp_display, use_container_width=True, hide_index=True,
            column_config={
                "kg bruto/u": st.column_config.NumberColumn(format="%.4f"),
                "$/kg":       st.column_config.NumberColumn(format="%.0f"),
                "Total $":    st.column_config.NumberColumn(format="$ %.0f"),
            })

    col_tot, col_save = st.columns([3,1])
    col_tot.markdown(
        f'<div style="font-size:0.85rem;padding:0.3rem 0;">'
        f'<span style="color:#768390;">Materiales: </span>'
        f'<span style="color:#3fb950;font-weight:700;">{_clp(mat_total)}</span></div>',
        unsafe_allow_html=True
    )
    if col_save.button("💾 Guardar materiales", key=f"aud_savmat_{handle}", type="primary"):
        save_rows = computed if computed else (
            edited_mat.to_dict("records") if isinstance(edited_mat, pd.DataFrame) else mat_init
        )
        _save_bom_db(handle, save_rows, saved_con)
        _all_products.clear(); _get_product.clear()
        st.session_state.pop(mh, None)  # bust hash so re-seeds from DB
        st.success("✅ Materiales guardados"); st.rerun()

    # ── Consumables (seeded from system algorithm) ────────────────────────────
    # Use saved_con if it exists, otherwise fall back to system_cons
    active_con = saved_con if saved_con else system_cons
    cons_total = int(sum(_nan(r.get("Total")) for r in active_con))

    # Source banner
    if not saved_con and system_cons:
        st.markdown(
            '<div style="background:#0d2a1a;border:1px dashed #238636;border-radius:6px;'
            'padding:0.4rem 0.8rem;margin-bottom:0.4rem;font-size:0.77rem;color:#3fb950;">'
            '⚙️ Consumibles del catálogo de procesos — guarda para fijar como propios de este producto.'
            '</div>',
            unsafe_allow_html=True
        )
    elif saved_con:
        # Show reset button outside the form
        rc, ic = st.columns([2, 5])
        with rc:
            if st.button(
                "↩️ Reset al template",
                key=f"reset_cons_{handle}",
                help="Reemplaza los consumibles guardados con los del catálogo de procesos"
            ):
                _save_bom_db(handle, saved_mat, system_cons)
                _all_products.clear(); _get_product.clear()
                st.session_state.pop(f"con_{handle}", None)
                st.session_state.pop(f"ch_{handle}", None)
                st.success("↩️ Consumibles reseteados al template del sistema")
                st.rerun()
        with ic:
            st.markdown(
                '<div style="font-size:0.75rem;color:#768390;padding-top:0.5rem;">'
                '🟡 Consumibles editados manualmente</div>',
                unsafe_allow_html=True
            )

    # System consumables summary banner
    if system_cons:
        sys_total = sum(_nan(r.get("Total")) for r in system_cons)
        by_proc_sys: dict[str, float] = {}
        for r in system_cons:
            p = r.get("Proceso", "—")
            by_proc_sys[p] = by_proc_sys.get(p, 0) + _nan(r.get("Total"))
        parts_sys = "  ·  ".join(
            f'<span style="color:#768390;">{p.replace("_"," ")}</span>'
            f' <span style="color:#e3b341;">{_clp(t)}</span>'
            for p, t in by_proc_sys.items()
        )
        st.markdown(
            f'<div style="font-size:0.73rem;color:#768390;margin-bottom:0.3rem;">'
            f'Sistema: {parts_sys}'
            f'<span style="color:#8b949e;margin-left:0.8rem;">→ total {_clp(sys_total)}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    PROCS = sorted({
        "laser", "corte_manual", "armado_trazado", "plegado", "cilindrado",
        "soldadura", "pulido", "qc", "grabado_laser", "refrigeracion", "pintura",
    } | {str(r.get("Proceso", "")) for r in active_con
         if r.get("Proceso") and isinstance(r.get("Proceso"), str)})

    cs, ch = f"con_{handle}", f"ch_{handle}"
    chash  = hash(str(active_con))
    if st.session_state.get(ch) != chash or cs not in st.session_state:
        st.session_state[cs] = pd.DataFrame(active_con) if active_con else pd.DataFrame(
            [{"Producto": "", "Proceso": "soldadura", "Cantidad": 1.0, "Unidad": "u", "Precio_u": 0, "Total": 0}]
        )
        st.session_state[ch] = chash

    with st.form(f"conf_{handle}"):
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">'
            f'<div class="sec-label">CONSUMIBLES — {len(active_con)} ítems</div>'
            f'<div class="num-med" style="color:#e3b341;">{_clp(cons_total)}</div></div>',
            unsafe_allow_html=True
        )
        edited_con = st.data_editor(
            st.session_state[cs], use_container_width=True, num_rows="dynamic", hide_index=True,
            column_config={
                "Precio_u": st.column_config.NumberColumn("Precio u.", format="%.0f", step=1),
                "Total":    st.column_config.NumberColumn("Total $",   format="%.0f", step=1),
                "Cantidad": st.column_config.NumberColumn("Cant.",      format="%.3f", step=0.001),
                "Proceso":  st.column_config.SelectboxColumn("Proceso", options=sorted(PROCS)),
            }
        )
        sc_btn = st.form_submit_button("💾 Guardar consumibles", use_container_width=True)

    if sc_btn:
        st.session_state[cs] = edited_con
        _save_bom_db(handle, saved_mat, edited_con.to_dict("records"))
        _all_products.clear(); _get_product.clear()
        st.session_state.pop(cs, None); st.session_state.pop(ch, None)
        st.success("✅ Consumibles guardados"); st.rerun()

    return mat_total, cons_total


def render_x_editor(product: dict, rules: dict):
    handle        = product["handle"]
    profile_key   = product.get("perfil_proceso","")
    profile_rules = rules.get("profiles",{}).get(profile_key,{})
    x_defs        = profile_rules.get("x_flags",{})
    c_driver      = profile_rules.get("c_driver")
    x_saved       = _pj(product.get("x_flags"), [])
    c_saved       = int(_nan(product.get("c_value")))

    if not x_defs and not c_driver:
        return

    with st.form(f"xf_{handle}"):
        st.markdown('<div class="sec-label">CARACTERÍSTICAS X + DRIVER C</div>', unsafe_allow_html=True)
        new_flags = []
        for flag, meta in x_defs.items():
            if st.checkbox(f'{meta["label"]}  (+{meta.get("points",0)} pts)',
                           value=(flag in x_saved), key=f"xf_{handle}_{flag}",
                           help=meta.get("description","")):
                new_flags.append(flag)
        new_c = c_saved
        if c_driver:
            new_c = st.number_input(
                f"{c_driver.replace('num_','').replace('_',' ').title()} (driver C)",
                value=c_saved, min_value=0, step=1
            )
        save_x = st.form_submit_button("💾 Guardar X + C", use_container_width=True)

    if save_x:
        get_sb().table("products").update(
            {"x_flags": json.dumps(new_flags), "c_value": int(new_c)}
        ).eq("handle", handle).execute()
        _all_products.clear()
        st.success("✅ Características guardadas"); st.rerun()


def render_hh_costs(proc_list: list, per_proc: dict, prod_comp: str, rules: dict) -> int:
    """
    Render HH labor cost table using per-process complexity levels.
    Each process looks up its own level (from per_proc) to select the right template row.
    Falls back to prod_comp if no per-process level could be derived.
    """
    hh_rates  = rules.get("hh_rates", {})
    templates = rules.get("process_templates", {})

    if not proc_list:
        st.markdown(
            '<div class="card"><div class="sec-label">MANO DE OBRA</div>'
            '<div style="color:#484f58;font-size:0.82rem;">'
            'Sin procesos configurados para este perfil/nivel.</div></div>',
            unsafe_allow_html=True
        )
        return 0

    rows     = []
    total_hh = 0

    for proc in proc_list:
        info       = per_proc.get(proc, {})
        proc_level = info.get("level") or prod_comp  # fallback to product complexity
        tpl        = templates.get(proc, {}).get(proc_level, {})
        t_setup    = _nan(tpl.get("T_setup_min"))
        t_exec     = _nan(tpl.get("T_exec_min"))
        n_ops      = max(_nan(tpl.get("n_ops", 1)), 1)
        rate       = _nan(hh_rates.get(proc))
        cost       = round(((t_setup+t_exec)/60)*rate*n_ops) if (t_setup+t_exec and rate) else None
        if cost:
            total_hh += cost

        # Flag when fallback is used
        used_fallback = (info.get("level") is None)
        level_tag = proc_level + ("*" if used_fallback else "")

        rows.append({
            "Proceso":   proc.replace("_", " "),
            "Nivel":     level_tag,
            "Setup min": int(t_setup) if t_setup else "—",
            "Exec min":  int(t_exec)  if t_exec  else "—",
            "Ops":       int(n_ops),
            "$/HH":      int(rate)    if rate    else "—",
            "Costo HH":  cost         if cost    else "—",
        })

    st.markdown(
        f'<div class="card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">'
        f'<div class="sec-label">MANO DE OBRA — templates × tarifas (por nivel de proceso)</div>'
        f'<div class="num-med" style="color:#79c0ff;">{_clp(total_hh) if total_hh else "—"}</div></div>',
        unsafe_allow_html=True
    )

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df, use_container_width=True, hide_index=True,
            column_config={
                "$/HH":     st.column_config.NumberColumn(format="$ %d"),
                "Costo HH": st.column_config.NumberColumn(format="$ %d"),
            }
        )

    any_fallback = any(per_proc.get(p, {}).get("level") is None for p in proc_list if p in per_proc)
    if any_fallback:
        st.caption("* Nivel fallback = complejidad del producto (proceso sin umbrales de driver configurados)")

    st.markdown("</div>", unsafe_allow_html=True)
    return total_hh


def render_totals(mat: int, cons: int, hh: int, source: str,
                  factor: float | None, anchor_mat: int | None, anchor_cons: int | None):
    full = mat + cons + hh

    exp_mat  = round((anchor_mat  or 0) * factor) if (factor and anchor_mat)  else None
    exp_cons = round((anchor_cons or 0) * factor) if (factor and anchor_cons) else None
    exp_full = (exp_mat or 0) + (exp_cons or 0) + hh if exp_mat is not None else None

    def _diff_html(val, exp):
        if exp is None or source == "anchor": return ""
        diff = val - exp
        pct  = round(diff/exp*100) if exp else 0
        color = "#3fb950" if abs(pct) < 5 else "#e3b341" if abs(pct) < 20 else "#f85149"
        return (f'<div style="font-size:0.7rem;color:#768390;margin-top:0.2rem;">ref: {_clp(exp)}</div>'
                f'<div style="font-size:0.7rem;color:{color};">{"+" if diff>=0 else ""}{_clp(diff)} ({pct:+d}%)</div>')

    cols = st.columns(4)
    for col, (lbl, val, exp, color) in zip(cols, [
        ("Materiales",   mat,  exp_mat,  "#3fb950"),
        ("Consumibles",  cons, exp_cons, "#e3b341"),
        ("Mano de Obra", hh,   None,     "#79c0ff"),
        ("TOTAL DIRECTO",full, exp_full, "#f0f6fc"),
    ]):
        col.markdown(
            f'<div class="card" style="text-align:center;">'
            f'<div class="sec-label">{lbl}</div>'
            f'<div class="num-big" style="color:{color};">{_clp(val)}</div>'
            f'{_diff_html(val, exp)}</div>',
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
        all_profiles = ["(Todos)"] + sorted({p.get("perfil_proceso") or "—" for p in products})
        sel_profile  = st.selectbox("Filtrar por perfil", all_profiles, key="aud_prof")
    with sc:
        search_q = st.text_input("Buscar handle / descripción", placeholder="bapla, basurero…", key="aud_srch")

    filtered = products
    if sel_profile != "(Todos)":
        filtered = [p for p in filtered if p.get("perfil_proceso") == sel_profile]
    if search_q:
        q = search_q.lower()
        filtered = [p for p in filtered if q in p["handle"].lower()
                    or q in (p.get("descripcion_web") or "").lower()]
    if not filtered:
        st.info("Ningún producto coincide.")
        return

    # ── Product selector ──────────────────────────────────────────────────────
    # Pre-compute source for each product to show indicator in label
    def _get_anchor_handle(p):
        pk = p.get("perfil_proceso","")
        comp = p.get("complejidad","?")
        return rules.get("profiles",{}).get(pk,{}).get("anchors",{}).get(comp)

    SOURCE_ICON = {"anchor":"⭐","extrapolado":"🔵","editado":"🟡","empty":"⚪"}

    def _lbl(p):
        ah  = _get_anchor_handle(p)
        src = _source(p, ah)
        icon = SOURCE_ICON[src]
        mat = _pj(p.get("bom_materials"),[])
        con = _pj(p.get("bom_consumables"),[])
        total = sum(_nan(r.get("total")) for r in mat) + sum(_nan(r.get("Total")) for r in con)
        total_str = f"  {_clp(total)}" if total else ""
        return f"{icon} [{p.get('perfil_proceso','—')} · {p.get('complejidad','?')}]  {p['handle']}{total_str}"

    opts = [_lbl(p) for p in filtered]
    idx  = st.selectbox("Producto", range(len(opts)), format_func=lambda i: opts[i], key="aud_sel")
    product = filtered[idx]

    # ── Compute context ───────────────────────────────────────────────────────
    profile_key = product.get("perfil_proceso","")
    comp        = product.get("complejidad","?")
    prof_rules  = rules.get("profiles",{}).get(profile_key,{})
    anchor_handle = prof_rules.get("anchors",{}).get(comp)
    bench       = prof_rules.get("cost_benchmarks",{}).get(comp,{})
    anchor_mat_total  = bench.get("material_total_clp")
    anchor_cons_total = bench.get("consumables_total_clp")
    anchor_dims = bench.get("dims",{})
    aL = _nan(anchor_dims.get("L_mm")); aW = _nan(anchor_dims.get("W_mm")); aH = _nan(anchor_dims.get("H_mm"))

    L0 = _nan(product.get("dim_l_mm"))
    W0 = _nan(product.get("dim_w_mm"))
    H0 = _nan(product.get("dim_h_mm"))
    factor = _factor_escala(L0, W0, H0, aL, aW, aH)
    source = _source(product, anchor_handle)

    st.divider()

    # ── Header ────────────────────────────────────────────────────────────────
    render_header(product, source, anchor_handle, factor)

    # ── Dims editor + drivers (left) | Profile tier (right) ──────────────────
    dc, pc = st.columns([3, 2])
    with dc:
        L, W, H, e = render_dims_editor(product, rules)
        render_drivers(L, W, H, e, product, rules)
    with pc:
        proc_list, comp, per_proc = render_profile_tier(product, L, W, H, e, rules)

    st.divider()

    # ── System consumables (derived from process catalog × per-process levels) ──
    eff_factor  = factor or 1.0
    system_cons = _build_system_consumables(proc_list, per_proc, rules, eff_factor, comp)

    # ── BOM section: depends on source ───────────────────────────────────────
    if source == "extrapolado":
        anchor_row = _get_product(anchor_handle) if anchor_handle else None
        if anchor_row and factor:
            anchor_mat_rows = _pj(anchor_row.get("bom_materials"), [])
            if anchor_mat_rows or system_cons:
                mat_total, cons_total = render_bom_extrapolated(
                    anchor_mat_rows, system_cons, factor, product["handle"]
                )
            else:
                st.info(f"Ancla `{anchor_handle}` no tiene BOM de materiales. Ingresa su BOM en Calibración.")
                mat_total, cons_total = 0, 0
        else:
            if not anchor_handle:
                st.warning(f"Sin ancla configurada para {profile_key} · {comp}. Configúrala en Datos por Perfil.")
            elif not factor:
                st.warning("Sin dimensiones — ingresa L/W/H para calcular el factor_escala.")
            mat_total, cons_total = 0, 0

    else:
        # anchor or editado: show editable BOM (materials + consumables)
        mat_total, cons_total = render_bom_editable(product, system_cons)

    # ── X flags editor ────────────────────────────────────────────────────────
    with st.expander("✏️ Editar características X + driver C", expanded=False):
        render_x_editor(product, rules)

    # ── HH costs ──────────────────────────────────────────────────────────────
    hh_total = render_hh_costs(proc_list, per_proc, comp, rules)

    # ── Totals ────────────────────────────────────────────────────────────────
    st.divider()
    render_totals(mat_total, cons_total, hh_total, source, factor, anchor_mat_total, anchor_cons_total)


if __name__ == "__main__":
    main()
