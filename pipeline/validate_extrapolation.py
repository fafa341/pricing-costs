"""
validate_extrapolation.py — Dulox Extrapolation Cost Validation
================================================================
Only analyses products that have bom_materials filled in Supabase.
Compares extrapolated material cost (anchor BOM × factor_escala) against
each product's own real BOM cost.

Produces three CSVs in dataset/:

  1. extrapolation_validation.csv  — one row per product with BOM
       • extrapolated_mat_cost vs real_mat_cost
       • deviation (CLP + %) and accuracy tier
       • factor_escala, anchor handle, dims

  2. material_decomposition.csv    — one row per BOM line item
       • anchor line scaled vs real line (matched by material name)
       • identifies which materials diverge from linear assumption
       • flags materials absent from anchor as "línea nueva"

  3. linearity_report.csv          — one row per (profile, complexity) bucket
       • OLS regression of real_cost ~ factor_escala
       • R², slope vs theoretical slope (anchor cost), MAPE
       • linearity verdict

Credentials: reads from .env.local in project root.

Usage:
    python3 scripts/validate_extrapolation.py
"""

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

# ─── Credentials ──────────────────────────────────────────────────────────────

def _get_credentials():
    """Read SUPABASE_PROJECT_URL + SUPABASE_SERVICE_ROLE from .env.local."""
    env_path = ROOT / ".env.local"
    url = key = ""
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("SUPABASE_PROJECT_URL"):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("SUPABASE_SERVICE_ROLE"):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not url:
        url = os.environ.get("SUPABASE_URL", "")
    if not key:
        key = os.environ.get("SUPABASE_SERVICE_ROLE", "")
    return url, key


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _nan(v) -> float:
    if v is None:
        return 0.0
    try:
        f = float(v)
        return 0.0 if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return 0.0


def _pj(raw, default=None):
    d = default if default is not None else []
    if isinstance(raw, list):
        return raw
    if not raw:
        return d
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else d
    except Exception:
        return d


def _area(L, W, H) -> float | None:
    if not (L and W):
        return None
    return 2 * (L + W) * (H or 0) + L * W


def _factor(L, W, H, aL, aW, aH) -> float | None:
    a  = _area(L, W, H)
    aa = _area(aL, aW, aH)
    if not a or not aa:
        return None
    f = a / aa
    return round(f, 6) if math.isfinite(f) else None


def _mat_total(bom_rows: list) -> float:
    return sum(_nan(r.get("total")) for r in bom_rows)


def _cons_total(bom_rows: list) -> float:
    return sum(_nan(r.get("Total")) for r in bom_rows)


# ─── Load data ────────────────────────────────────────────────────────────────

def load_products(sb) -> tuple[list[dict], list[dict]]:
    """
    Returns (all_products, bom_products).
    all_products: every row (for anchor lookup even when they have no BOM).
    bom_products: only rows with bom_materials filled (the analysis set).
    """
    print("Loading products from Supabase...")
    rows = (
        sb.table("products")
        .select(
            "handle,descripcion_web,perfil_proceso,complejidad,familia,subfamilia,"
            "dim_l_mm,dim_w_mm,dim_h_mm,dim_espesor_mm,g_score,d_score,"
            "c_value,x_flags,bom_materials,bom_consumables,is_anchor"
        )
        .order("perfil_proceso,complejidad,handle")
        .execute()
        .data
        or []
    )

    bom_rows = []
    for p in rows:
        m = p.get("bom_materials")
        if not m or m in ["[]", "", "null", "None"]:
            continue
        try:
            parsed = json.loads(m) if isinstance(m, str) else m
            if parsed and len(parsed) > 0:
                bom_rows.append(p)
        except Exception:
            pass

    print(f"  {len(rows)} total products | {len(bom_rows)} with BOM materials")
    return rows, bom_rows


def load_rules(sb) -> dict:
    """Load PROCESS_RULES from Supabase app_settings (live), fallback to local JSON."""
    try:
        r = sb.table("app_settings").select("value").eq("key", "process_rules").single().execute()
        if r.data and r.data.get("value"):
            print("  PROCESS_RULES loaded from Supabase app_settings")
            return r.data["value"]
    except Exception:
        pass
    rules_path = ROOT / "data" / "PROCESS_RULES.json"
    if rules_path.exists():
        print("  PROCESS_RULES loaded from local JSON (fallback)")
        return json.loads(rules_path.read_text(encoding="utf-8"))
    return {}


# ─── Core analysis ────────────────────────────────────────────────────────────

def build_anchor_index(products: list[dict], rules: dict) -> dict:
    """
    Returns {(profile, comp): {handle, mat_rows, cons_rows, L, W, H, mat_total}}
    Priority: is_anchor=1 in DB > anchors dict in rules.
    """
    anchors: dict = {}

    # Pass 1: rule-defined anchors
    for pk, pv in rules.get("profiles", {}).items():
        for comp, handle in (pv.get("anchors") or {}).items():
            if handle:
                anchors[(pk, comp)] = {"handle": handle}

    # Pass 2: DB is_anchor=1
    for p in products:
        if p.get("is_anchor"):
            key = (p.get("perfil_proceso", ""), p.get("complejidad", ""))
            if key not in anchors:
                anchors[key] = {"handle": p["handle"]}

    # Enrich with BOM and dims
    prod_by_handle = {p["handle"]: p for p in products}
    for key, info in anchors.items():
        handle = info["handle"]
        row = prod_by_handle.get(handle)
        if not row:
            info["found"] = False
            continue
        mat_rows = _pj(row.get("bom_materials"), [])
        cons_rows = _pj(row.get("bom_consumables"), [])
        info.update({
            "found":      True,
            "mat_rows":   mat_rows,
            "cons_rows":  cons_rows,
            "mat_total":  _mat_total(mat_rows),
            "cons_total": _cons_total(cons_rows),
            "L": _nan(row.get("dim_l_mm")),
            "W": _nan(row.get("dim_w_mm")),
            "H": _nan(row.get("dim_h_mm")),
        })

    return anchors


ACCURACY_TIERS = [
    (0.05,  "✅ Exacto      (<5%)"),
    (0.10,  "🟢 Bueno       (<10%)"),
    (0.20,  "🟡 Aceptable   (<20%)"),
    (0.40,  "🟠 Desajuste   (<40%)"),
    (1e9,   "🔴 Error alto  (≥40%)"),
]


def classify_accuracy(real: float, extrap: float) -> tuple[str, float, float]:
    """Returns (tier_label, deviation_clp, deviation_pct)."""
    if not real:
        return "⚪ Sin datos reales", extrap, float("nan")
    dev_clp = extrap - real
    dev_pct = dev_clp / real
    for threshold, label in ACCURACY_TIERS:
        if abs(dev_pct) <= threshold:
            return label, dev_clp, dev_pct
    return "🔴 Error alto  (≥40%)", dev_clp, dev_pct


# ─── CSV 1: Product-level validation ─────────────────────────────────────────

def build_validation_rows(products: list[dict], anchors: dict) -> list[dict]:
    rows = []
    for p in products:
        pk    = p.get("perfil_proceso", "")
        comp  = p.get("complejidad", "")
        handle = p["handle"]
        anchor_info = anchors.get((pk, comp), {})
        anchor_handle = anchor_info.get("handle")

        L = _nan(p.get("dim_l_mm"))
        W = _nan(p.get("dim_w_mm"))
        H = _nan(p.get("dim_h_mm"))
        e = _nan(p.get("dim_espesor_mm"))

        aL = anchor_info.get("L", 0)
        aW = anchor_info.get("W", 0)
        aH = anchor_info.get("H", 0)

        factor = _factor(L, W, H, aL, aW, aH) if anchor_info.get("found") else None
        is_anchor = bool(p.get("is_anchor")) or (handle == anchor_handle)

        anchor_mat = anchor_info.get("mat_total", 0)
        extrap_mat = round(anchor_mat * factor) if (factor and anchor_mat) else None

        # Real BOM
        own_mat_rows = _pj(p.get("bom_materials"), [])
        real_mat = _mat_total(own_mat_rows) if own_mat_rows else None
        has_own_bom = bool(own_mat_rows)

        acc_label, dev_clp, dev_pct = ("—", None, None)
        if extrap_mat is not None and real_mat:
            acc_label, dev_clp, dev_pct = classify_accuracy(real_mat, extrap_mat)

        dev_pct_num = dev_pct * 100 if (dev_pct is not None and not math.isnan(dev_pct)) else None

        rows.append({
            "handle":              handle,
            "descripcion":         p.get("descripcion_web", ""),
            "perfil_proceso":      pk,
            "complejidad":         comp,
            "familia":             p.get("familia", ""),
            "es_ancla":            "⭐ Sí" if is_anchor else "",
            "anchor_handle":       anchor_handle or "",
            "L_mm":                L or "",
            "W_mm":                W or "",
            "H_mm":                H or "",
            "espesor_mm":          e or "",
            "area_mm2":            round(_area(L, W, H)) if _area(L, W, H) else "",
            "anchor_L_mm":         aL or "",
            "anchor_W_mm":         aW or "",
            "anchor_H_mm":         aH or "",
            "anchor_area_mm2":     round(_area(aL, aW, aH)) if _area(aL, aW, aH) else "",
            "factor_escala":       round(factor, 4) if factor is not None else "",
            "anchor_mat_cost_clp": int(anchor_mat) if anchor_mat else "",
            "extrap_mat_cost_clp": int(extrap_mat) if extrap_mat is not None else "",
            "real_mat_cost_clp":   int(real_mat) if real_mat is not None else "",
            "deviation_clp":       int(dev_clp) if dev_clp is not None else "",
            "deviation_pct":       f"{dev_pct_num:.1f}%" if dev_pct_num is not None else "",
            "deviation_pct_num":   round(dev_pct_num, 2) if dev_pct_num is not None else None,
            "accuracy_tier":       acc_label if (extrap_mat is not None and real_mat) else "⚪ Sin comparación",
            "n_mat_lines":         len(own_mat_rows),
        })
    return rows


# ─── CSV 2: Material decomposition ────────────────────────────────────────────

def build_decomposition_rows(products: list[dict], anchors: dict) -> list[dict]:
    """
    For each product with own BOM, expand every material line and compare
    it against the scaled anchor line (matched by Material name).
    """
    rows = []
    for p in products:
        pk    = p.get("perfil_proceso", "")
        comp  = p.get("complejidad", "")
        handle = p["handle"]
        anchor_info = anchors.get((pk, comp), {})
        if not anchor_info.get("found"):
            continue

        own_mat_rows = _pj(p.get("bom_materials"), [])
        if not own_mat_rows:
            continue

        anchor_handle = anchor_info["handle"]
        if handle == anchor_handle:
            continue   # skip anchor itself in decomposition

        aL = anchor_info.get("L", 0)
        aW = anchor_info.get("W", 0)
        aH = anchor_info.get("H", 0)
        L  = _nan(p.get("dim_l_mm"))
        W  = _nan(p.get("dim_w_mm"))
        H  = _nan(p.get("dim_h_mm"))
        factor = _factor(L, W, H, aL, aW, aH)
        if not factor:
            continue

        # Build anchor material index by name
        anchor_mat_idx = {
            r.get("Material", ""): r
            for r in anchor_info.get("mat_rows", [])
        }

        for r in own_mat_rows:
            mat_name    = r.get("Material", "")
            real_total  = _nan(r.get("total"))
            real_qty    = _nan(r.get("Cantidad", 1))
            real_kg_ml  = _nan(r.get("kg_ml"))
            price_kg    = _nan(r.get("precio_kg"))

            anchor_row  = anchor_mat_idx.get(mat_name)
            anchor_total = _nan(anchor_row.get("total")) if anchor_row else None
            extrap_total = round(anchor_total * factor) if anchor_total is not None else None
            extrap_qty   = round(_nan(anchor_row.get("Cantidad", 1)) * factor, 4) if anchor_row else None

            dev_clp = (extrap_total - real_total) if (extrap_total is not None and real_total) else None
            dev_pct = (dev_clp / real_total * 100) if (dev_clp is not None and real_total) else None

            rows.append({
                "handle":            handle,
                "perfil_proceso":    pk,
                "complejidad":       comp,
                "anchor_handle":     anchor_handle,
                "factor_escala":     factor,
                "material":          mat_name,
                "subconjunto":       r.get("Subconjunto", ""),
                "dimensiones":       r.get("Dimensiones", ""),
                "precio_kg_u":       int(price_kg) if price_kg else "",
                # Real (product's own BOM)
                "real_kg_ml":        real_kg_ml or "",
                "real_cantidad":     real_qty or "",
                "real_total_clp":    int(real_total) if real_total else "",
                # Extrapolated (anchor scaled by factor)
                "anchor_total_clp":  int(anchor_total) if anchor_total is not None else "(no en ancla)",
                "extrap_total_clp":  int(extrap_total) if extrap_total is not None else "(no en ancla)",
                "extrap_cantidad":   extrap_qty if extrap_qty is not None else "",
                # Delta
                "dev_clp":           int(dev_clp) if dev_clp is not None else "",
                "dev_pct":           f"{dev_pct:.1f}%" if dev_pct is not None else "",
                "in_anchor_bom":     "Sí" if anchor_row else "No — línea nueva",
            })
    return rows


# ─── CSV 3: Linearity report per bucket ──────────────────────────────────────

def build_linearity_rows(validation_df: pd.DataFrame) -> list[dict]:
    """
    For each (perfil_proceso, complejidad) bucket with ≥3 products that have
    both factor_escala and real_mat_cost, run OLS regression of
    real_cost ~ factor_escala and report R², slope, MAPE.
    """
    rows = []
    df = validation_df.copy()

    # Filter to usable rows: numeric factor and real cost
    df = df[
        (df["factor_escala"] != "") &
        (df["real_mat_cost_clp"] != "") &
        (df["es_ancla"] != "⭐ Sí")
    ].copy()
    df["factor_escala"]     = pd.to_numeric(df["factor_escala"],     errors="coerce")
    df["real_mat_cost_clp"] = pd.to_numeric(df["real_mat_cost_clp"], errors="coerce")
    df["anchor_mat_cost_clp"] = pd.to_numeric(df["anchor_mat_cost_clp"], errors="coerce")
    df = df.dropna(subset=["factor_escala", "real_mat_cost_clp"])

    for (pk, comp), grp in df.groupby(["perfil_proceso", "complejidad"]):
        n = len(grp)
        if n < 2:
            rows.append({
                "perfil_proceso": pk, "complejidad": comp,
                "n_productos_con_bom": n,
                "anchor_mat_cost_clp": grp["anchor_mat_cost_clp"].iloc[0] if n else "",
                "nota": "Insuficientes datos (necesita ≥2)",
                "r2": "", "slope_clp_per_factor": "", "intercept_clp": "",
                "mape_pct": "", "max_abs_dev_pct": "",
                "linearity_verdict": "⚪ Sin datos",
            })
            continue

        x = grp["factor_escala"].values
        y = grp["real_mat_cost_clp"].values
        a_cost = grp["anchor_mat_cost_clp"].iloc[0]

        # OLS: y = slope*x + intercept
        x_mat = np.column_stack([x, np.ones_like(x)])
        try:
            result = np.linalg.lstsq(x_mat, y, rcond=None)
            slope, intercept = result[0]
        except Exception:
            slope, intercept = float("nan"), float("nan")

        # R²
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

        # MAPE using extrapolated (anchor * factor) as prediction
        extrap_preds = a_cost * x
        ape = np.abs((extrap_preds - y) / y) * 100
        mape = float(np.mean(ape))
        max_ape = float(np.max(ape))

        # Linearity verdict
        if math.isnan(r2):
            verdict = "⚪ No calculable"
        elif r2 >= 0.9 and mape <= 10:
            verdict = "✅ Muy lineal    (R²≥0.90, MAPE≤10%)"
        elif r2 >= 0.75 and mape <= 20:
            verdict = "🟢 Lineal        (R²≥0.75, MAPE≤20%)"
        elif r2 >= 0.50:
            verdict = "🟡 Parcialmente  (R²≥0.50)"
        else:
            verdict = "🔴 No lineal     (R²<0.50)"

        # Theoretical perfect-linear slope = anchor_mat_cost (since extrap = anchor × factor)
        slope_vs_theory_pct = (slope / a_cost - 1) * 100 if a_cost else float("nan")

        rows.append({
            "perfil_proceso":         pk,
            "complejidad":            comp,
            "n_productos_con_bom":    n,
            "anchor_mat_cost_clp":    int(a_cost) if a_cost else "",
            "theoretical_slope":      int(a_cost) if a_cost else "(sin ancla)",
            "empirical_slope":        f"{slope:.0f}",
            "slope_vs_theory_pct":    f"{slope_vs_theory_pct:.1f}%" if not math.isnan(slope_vs_theory_pct) else "",
            "intercept_clp":          f"{intercept:.0f}",
            "r2":                     f"{r2:.4f}" if not math.isnan(r2) else "",
            "mape_pct":               f"{mape:.1f}%",
            "max_abs_dev_pct":        f"{max_ape:.1f}%",
            "linearity_verdict":      verdict,
            "nota": (
                f"Intercept={intercept:.0f}: producto tiene {'costo base fijo' if intercept > 0 else 'sobreestimación en small'}"
                if not math.isnan(intercept) else ""
            ),
        })

    return rows


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    url, key = _get_credentials()
    if not url or not key:
        print("ERROR: SUPABASE_PROJECT_URL / SUPABASE_SERVICE_ROLE not found in .env.local")
        sys.exit(1)

    from supabase import create_client
    sb = create_client(url, key)

    all_products, bom_products = load_products(sb)
    rules = load_rules(sb)

    # ── Anchor index built from ALL products (anchors may not have own BOM yet)
    print("\nBuilding anchor index...")
    anchors = build_anchor_index(all_products, rules)
    n_found    = sum(1 for v in anchors.values() if v.get("found"))
    n_with_bom = sum(1 for v in anchors.values() if v.get("mat_total", 0) > 0)
    print(f"  {len(anchors)} anchor slots defined | {n_found} found in DB | {n_with_bom} with BOM data")
    for (pk, comp), info in sorted(anchors.items()):
        status = "✅ BOM" if info.get("mat_total",0) > 0 else ("⚠️ no BOM" if info.get("found") else "❌ not found")
        print(f"    [{pk} · {comp}]  {info.get('handle','—')}  {status}")

    # ── CSV 1: Validation — only BOM products ─────────────────────────────────
    print(f"\nBuilding validation table ({len(bom_products)} BOM products)...")
    val_rows = build_validation_rows(bom_products, anchors)
    val_df   = pd.DataFrame(val_rows)

    comparable = val_df[
        (val_df["extrap_mat_cost_clp"] != "") &
        (val_df["real_mat_cost_clp"] != "") &
        (val_df["es_ancla"] != "⭐ Sí")
    ]
    print(f"  {len(val_df)} BOM products in table")
    print(f"  {len(comparable)} non-anchor products with both extrap + real cost (comparable)")

    out_val = ROOT / "data" / "extrapolation_validation.csv"
    val_df.to_csv(out_val, index=False, encoding="utf-8-sig")
    print(f"  → {out_val.relative_to(ROOT)}")

    # ── CSV 2: Material decomposition ─────────────────────────────────────────
    print("\nBuilding material decomposition table...")
    decomp_rows = build_decomposition_rows(bom_products, anchors)
    decomp_df   = pd.DataFrame(decomp_rows)
    n_prods = decomp_df["handle"].nunique() if not decomp_df.empty else 0
    print(f"  {len(decomp_df)} line comparisons across {n_prods} non-anchor products")

    out_decomp = ROOT / "data" / "material_decomposition.csv"
    decomp_df.to_csv(out_decomp, index=False, encoding="utf-8-sig")
    print(f"  → {out_decomp.relative_to(ROOT)}")

    # ── CSV 3: Linearity ──────────────────────────────────────────────────────
    print("\nBuilding linearity report...")
    lin_rows = build_linearity_rows(val_df)
    lin_df   = pd.DataFrame(lin_rows)

    out_lin = ROOT / "data" / "linearity_report.csv"
    lin_df.to_csv(out_lin, index=False, encoding="utf-8-sig")
    print(f"  → {out_lin.relative_to(ROOT)}")

    # ── Console summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("ACCURACY SUMMARY  (non-anchor products with comparable costs)")
    print("=" * 70)
    if not comparable.empty:
        tier_counts = comparable["accuracy_tier"].value_counts()
        for tier, count in tier_counts.items():
            pct = count / len(comparable) * 100
            print(f"  {tier:40s}  {count:3d} ({pct:.0f}%)")
        print(f"\n  Median abs deviation: {comparable['deviation_pct_num'].abs().median():.1f}%")
        print(f"  Mean abs deviation:   {comparable['deviation_pct_num'].abs().mean():.1f}%")
        print(f"  Worst case:           {comparable['deviation_pct_num'].abs().max():.1f}%")
    else:
        print("  No comparable products found.")

    print("\nLINEARITY SUMMARY")
    print("=" * 70)
    if not lin_df.empty:
        for _, row in lin_df.iterrows():
            print(f"  {row['perfil_proceso']:30s} {row['complejidad']:4s}  "
                  f"n={row.get('n_productos_con_bom',0):2}  {row.get('linearity_verdict','')}")
    else:
        print("  Insufficient BOM data for linearity analysis.")

    print("\n" + "=" * 70)
    print("FILES WRITTEN:")
    print(f"  dataset/extrapolation_validation.csv  — {len(val_df)} rows")
    print(f"  dataset/material_decomposition.csv    — {len(decomp_df)} rows")
    print(f"  dataset/linearity_report.csv          — {len(lin_df)} rows")


if __name__ == "__main__":
    main()
