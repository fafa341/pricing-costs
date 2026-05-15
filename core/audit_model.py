"""
audit_model.py — Dulox Model Coherence Auditor
================================================
Tests whether the G/D/C/X driver system produces scores that are
mathematically consistent with assigned complexity levels (C1/C2/C3).

Key principle: Each perfil_proceso has DECLARED primary drivers.
We only test the drivers that are DECLARED primary for each profile.
If the primary driver isn't in the DB → "not testeable" (not a contradiction).

Usage:
  python3 scripts/audit_model.py                        # full audit
  python3 scripts/audit_model.py --test drivers
  python3 scripts/audit_model.py --test cohesion
  python3 scripts/audit_model.py --test outliers
  python3 scripts/audit_model.py --save
"""

import sqlite3
import pandas as pd
import numpy as np
import argparse
import json
from pathlib import Path
from datetime import date
from scipy.stats import spearmanr, f_oneway, mannwhitneyu

ROOT       = Path(__file__).resolve().parent.parent
DB         = ROOT / "data" / "products.db"
CHUNKS     = ROOT / "docs" / "calibration" / "process-measurements" / "knowledge-chunks.jsonl"
AUDIT_LOG  = ROOT / "files-process" / "process-measurements" / "AUDIT_LOG.md"
AUDIT_DIR  = ROOT / "files-process" / "process-measurements" / "audit-reports"
RULES_FILE = ROOT / "data" / "PROCESS_RULES.json"

# ─── Load driver thresholds from PROCESS_RULES.json ───────────────────────────
# Fallback constants are used only if the file is missing (offline/dev).

_G_BREAKPOINTS = [500_000, 1_500_000]   # mm² — fallback
_D_BREAKPOINTS = [1.5, 2.0]             # mm  — fallback

def _load_rules():
    """Load PROCESS_RULES.json. Returns parsed dict or {} on failure."""
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️  PROCESS_RULES.json not found or invalid ({e}). Using hardcoded fallback thresholds.")
        return {}

_RULES = _load_rules()

if _RULES:
    _G_BREAKPOINTS = _RULES["driver_thresholds"]["G"]["breakpoints_mm2"]
    _D_BREAKPOINTS = _RULES["driver_thresholds"]["D"]["breakpoints_mm"]

def g_score(area_mm2):
    """Compute G driver score (1/2/3) from area in mm². Uses PROCESS_RULES.json thresholds."""
    if area_mm2 is None or (isinstance(area_mm2, float) and np.isnan(area_mm2)):
        return np.nan
    lo, hi = _G_BREAKPOINTS
    return 1 if area_mm2 < lo else (2 if area_mm2 < hi else 3)

def d_score(espesor_mm):
    """Compute D driver score (1/2/3) from espesor in mm. Uses PROCESS_RULES.json thresholds."""
    if espesor_mm is None or (isinstance(espesor_mm, float) and np.isnan(espesor_mm)):
        return np.nan
    lo, hi = _D_BREAKPOINTS
    return 1 if espesor_mm <= lo else (2 if espesor_mm <= hi else 3)

# ─── Build PROFILE_DRIVERS from PROCESS_RULES.json ────────────────────────────
#
# Format: list of (driver_col, driver_name, available_in_db)
# available_in_db = True if the column exists and is populated in DB.
#
# G = geometry (area L×W)      — available as column G in DB
# D = density (espesor)        — available as column D in DB
# C = components (count)       — NOT in DB yet (num_componentes etc.)
# X = characteristics (flags)  — NOT in DB yet

# Static DB-availability map (update when new columns are added to products.db)
_DRIVER_DB_AVAILABLE = {"G": True, "D": True, "C": False, "X": False}

def _build_profile_drivers():
    """
    Build PROFILE_DRIVERS from PROCESS_RULES.json profiles section.
    Falls back to hardcoded table if rules file is missing.
    """
    if not _RULES or "profiles" not in _RULES:
        # Hardcoded fallback
        return {
            "p-meson":          [("G","G",True), ("C","C",False)],
            "p-modulo":         [("G","G",True), ("X","X",False)],
            "p-laminar-simple": [("G","G",True)],
            "p-cocina-gas":     [("C","C",False)],
            "p-cilindrico":     [("D","D",True), ("G","G",True)],
            "p-basurero-rect":  [("G","G",True), ("X","X",False)],
            "p-basurero-cil":   [("D","D",True), ("G","G",True), ("X","X",False)],
            "p-carro-bandejero":[("C","C",False), ("G","G",True)],
            "p-carro-traslado": [("G","G",True), ("C","C",False)],
            "p-sumidero":       [("G","G",True)],
            "p-lavadero":       [("C","C",False), ("G","G",True)],
            "p-laser":          [("X","X",False), ("D","D",True)],
            "p-electrico":      [("C","C",False), ("G","G",True)],
            "p-campana":        [("G","G",True)],
            "p-refrigerado":    [("C","C",False)],
            "p-rejilla":        [("C","C",False), ("G","G",True)],
            "p-tina":           [("C","C",False), ("G","G",True)],
            "p-custom":         [("G","G",True), ("C","C",False)],
        }

    result = {}
    for perfil, pdata in _RULES["profiles"].items():
        drivers = []
        # Primary drivers first, then secondary
        for d in pdata.get("primary_drivers", []):
            avail = _DRIVER_DB_AVAILABLE.get(d, False)
            drivers.append((d, d, avail))
        for d in pdata.get("secondary_drivers", []):
            if d not in pdata.get("primary_drivers", []):
                avail = _DRIVER_DB_AVAILABLE.get(d, False)
                drivers.append((d, d, avail))
        if drivers:
            result[perfil] = drivers
    return result

PROFILE_DRIVERS = _build_profile_drivers()

# Profiles where G alone is NOT the primary driver
# (G inversions in these are EXPECTED — don't flag as contradiction)
# Derived from PROCESS_RULES.json g_is_primary field when available.
def _build_g_not_primary():
    if _RULES and "profiles" in _RULES:
        return {p for p, d in _RULES["profiles"].items() if not d.get("g_is_primary", True)}
    return {"p-meson", "p-cocina-gas", "p-carro-bandejero",
            "p-lavadero", "p-electrico", "p-refrigerado",
            "p-rejilla", "p-tina", "p-custom"}

G_NOT_PRIMARY = _build_g_not_primary()

# ─── Load data ────────────────────────────────────────────────────────────────

def load_db():
    conn = sqlite3.connect(DB)
    df = pd.read_sql("""
        SELECT handle, perfil_proceso, complejidad, k_num,
               G, D, dim_l_mm, dim_w_mm, dim_espesor_mm,
               familia, subfamilia, descripcion_web, validated
        FROM products
        WHERE perfil_proceso != 'p-importado'
    """, conn)
    conn.close()
    return df

# ─── TEST 1: Declared-driver coherence ───────────────────────────────────────

def test_drivers(df, verbose=True):
    """
    For each profile, test ONLY the drivers declared as primary.
    Distinguishes:
      ✅ COHERENTE    — declared driver correlates with complexity
      ⚠️  MIXTO       — partial evidence (low n or p>0.10)
      ❌ CONTRADICCIÓN — declared driver INVERTS against complexity
      🔲 NO TESTEABLE — primary driver not in DB (gap, not contradiction)
    """
    lines = ["", "="*65,
             "TEST 1 — COHERENCIA DE DRIVERS DECLARADOS × COMPLEJIDAD",
             "="*65]
    results = {}

    perfiles = [p for p in sorted(df["perfil_proceso"].unique())
                if p in PROFILE_DRIVERS and p != "p-importado"]

    for perfil in perfiles:
        grp = df[df["perfil_proceso"] == perfil].copy()
        n_total = len(grp)
        if n_total < 3:
            continue

        levels = sorted(grp["complejidad"].dropna().unique(),
                        key=lambda k: {"C1":1,"C2":2,"C3":3}.get(k, 99))
        if len(levels) < 2:
            continue

        declared = PROFILE_DRIVERS[perfil]
        driver_results = []
        testeable_drivers = []
        gap_drivers = []

        for col, name, available in declared:
            if not available or col not in df.columns:
                gap_drivers.append(name)
                continue

            sub = grp[[col, "k_num"]].dropna()
            if len(sub) < 4:
                gap_drivers.append(f"{name}(n<4)")
                continue

            testeable_drivers.append(name)

            # Spearman correlation
            rho, p = spearmanr(sub[col], sub["k_num"])

            # Monotonicity: mean driver score per level
            means = grp.groupby("complejidad")[col].mean().reindex(
                [k for k in ["C1","C2","C3"] if k in grp["complejidad"].values]
            )
            vals = means.dropna().tolist()
            is_mono = all(vals[i] <= vals[i+1] for i in range(len(vals)-1)) if len(vals) >= 2 else None

            # If G is NOT the primary driver, don't flag inversion as contradiction
            is_primary = not (col == "G" and perfil in G_NOT_PRIMARY)

            if is_mono is False and is_primary:
                status = "INVERSION"
            elif is_mono and (pd.isna(p) or p < 0.10):
                status = "COHERENT"
            elif is_mono:
                status = "WEAK"  # monotone but not significant
            else:
                status = "INVERSION_EXPECTED"  # non-primary driver inversion

            driver_results.append({
                "driver": name, "col": col, "rho": rho, "p": p,
                "means": means.to_dict(), "is_mono": is_mono,
                "status": status, "n": len(sub), "is_primary": is_primary,
            })

        # Overall profile status
        if not testeable_drivers:
            overall = "🔲 NO TESTEABLE"
        elif any(r["status"] == "INVERSION" for r in driver_results):
            overall = "❌ CONTRADICCIÓN"
        elif any(r["status"] in ("COHERENT",) for r in driver_results):
            overall = "✅ COHERENTE"
        else:
            overall = "⚠️  MIXTO"

        results[perfil] = {
            "status": overall,
            "n_total": n_total,
            "testeable": testeable_drivers,
            "gaps": gap_drivers,
            "drivers": driver_results,
        }

        if verbose:
            lines.append(f"\n{overall}  {perfil}  (n={n_total})")
            for dr in driver_results:
                mono_sym = "↑" if dr["is_mono"] else ("↓!" if dr["is_mono"] is False else "—")
                rho_str = f"ρ={dr['rho']:.2f} p={dr['p']:.3f}" if not pd.isna(dr["rho"]) else "—"
                means_str = "  ".join(f"{k}:{v:.2f}" for k, v in dr["means"].items() if not pd.isna(v))
                lines.append(f"  {dr['driver']} {mono_sym}  {means_str}  [{rho_str}]")
            if gap_drivers:
                lines.append(f"  🔲 Sin datos para: {', '.join(gap_drivers)}")

            # Show outlier products when there's an inversion
            for dr in driver_results:
                if dr["status"] == "INVERSION":
                    lines.append(f"  ⚡ INVERSIÓN en {dr['driver']}: revisar productos:")
                    col = dr["col"]
                    # Find the level where the inversion happens
                    mean_vals = [(k, dr["means"][k]) for k in ["C1","C2","C3"]
                                 if k in dr["means"] and not pd.isna(dr["means"][k])]
                    for i in range(len(mean_vals)-1):
                        k1, v1 = mean_vals[i]
                        k2, v2 = mean_vals[i+1]
                        if v1 > v2:
                            # Show products in the higher level with lower driver score
                            prods = grp[grp["complejidad"] == k2].sort_values(col)
                            for _, pr in prods.head(5).iterrows():
                                g_val = pr.get(col)
                                lines.append(f"    {k2} [{col}={g_val}] {pr['handle'][:60]}")

    # Summary
    total = len(results)
    ok    = sum(1 for r in results.values() if "✅" in r["status"])
    mixed = sum(1 for r in results.values() if "⚠️" in r["status"])
    bad   = sum(1 for r in results.values() if "❌" in r["status"])
    nt    = sum(1 for r in results.values() if "🔲" in r["status"])

    coherence_pct = (ok / (total - nt) * 100) if (total - nt) > 0 else 0

    lines += ["", "─"*65, "RESUMEN TEST 1",
              f"  Perfiles:        {total}",
              f"  ✅ Coherentes:   {ok}",
              f"  ⚠️  Mixtos:       {mixed}",
              f"  ❌ Contradicción:{bad}",
              f"  🔲 No testeables:{nt}  (driver C/X no en DB — gaps documentados)",
              f"  Score (testeables): {coherence_pct:.0f}/100",
              "",
              "  Gaps que bloquean el test C:",
              "    num_componentes  → p-meson, p-carro-*, p-modulo, p-electrico, p-rejilla, p-tina",
              "    num_quemadores   → p-cocina-gas",
              "    num_tazas        → p-lavadero",
              "    num_niveles      → p-carro-bandejero",
              "    tiene_mecanismo  → p-basurero-cil",
              "  → Enriquecer DB con estas columnas = mayor impacto en ICM",
    ]

    if verbose:
        print("\n".join(lines))

    return results, coherence_pct, "\n".join(lines)

# ─── TEST 2: Intra-group cohesion ─────────────────────────────────────────────

def test_cohesion(df, verbose=True):
    """
    For each (perfil_proceso × complejidad) bucket:
    1. Compute within-group variance of available driver scores (G, D)
    2. Test inter-group separation (Mann-Whitney between adjacent levels)
    3. Flag buckets where variance is suspiciously high (products may be miscategorized)

    High intra-group variance + low inter-group separation = weak categorization.
    """
    lines = ["", "="*65,
             "TEST 2 — COHESIÓN INTRA-GRUPO  (¿están bien agrupados?)",
             "="*65]
    results = {}

    perfiles = [p for p in sorted(df["perfil_proceso"].unique())
                if p != "p-importado"]

    for perfil in perfiles:
        grp = df[df["perfil_proceso"] == perfil]
        n_total = len(grp)
        if n_total < 4:
            continue

        levels = sorted(grp["complejidad"].dropna().unique(),
                        key=lambda k: {"C1":1,"C2":2,"C3":3}.get(k, 99))
        if len(levels) < 2:
            continue

        perfil_results = {"n_total": n_total, "levels": {}, "separations": []}

        for k in levels:
            sub = grp[grp["complejidad"] == k]
            g_vals = sub["G"].dropna()
            d_vals = sub["D"].dropna()

            level_info = {
                "n": len(sub),
                "g_mean": g_vals.mean() if len(g_vals) >= 2 else None,
                "g_std":  g_vals.std()  if len(g_vals) >= 2 else None,
                "d_mean": d_vals.mean() if len(d_vals) >= 2 else None,
                "d_std":  d_vals.std()  if len(d_vals) >= 2 else None,
                "outliers": [],
            }

            # Flag products whose G score is far from their level mean
            # (only for profiles where G is primary)
            if perfil not in G_NOT_PRIMARY and len(g_vals) >= 3:
                g_mean = g_vals.mean()
                g_std  = g_vals.std()
                if g_std > 0:
                    for _, row in sub.iterrows():
                        g = row.get("G")
                        if pd.notna(g):
                            z = abs(g - g_mean) / g_std
                            if z > 1.5:
                                level_info["outliers"].append({
                                    "handle": row["handle"],
                                    "G": g, "z": round(z, 2)
                                })

            perfil_results["levels"][k] = level_info

        # Inter-group separation: adjacent level pairs
        all_separated = True
        for i in range(len(levels)-1):
            k1, k2 = levels[i], levels[i+1]
            g1 = grp[grp["complejidad"] == k1]["G"].dropna()
            g2 = grp[grp["complejidad"] == k2]["G"].dropna()

            sep = {"pair": f"{k1}→{k2}", "driver": "G",
                   "n1": len(g1), "n2": len(g2),
                   "mean1": g1.mean() if len(g1) else None,
                   "mean2": g2.mean() if len(g2) else None,
                   "p": None, "separated": None}

            if len(g1) >= 3 and len(g2) >= 3 and perfil not in G_NOT_PRIMARY:
                try:
                    _, p = mannwhitneyu(g1, g2, alternative="less")
                    sep["p"] = round(p, 3)
                    sep["separated"] = p < 0.10
                    if not sep["separated"]:
                        all_separated = False
                except Exception:
                    pass

            perfil_results["separations"].append(sep)

        # Status
        n_outliers = sum(len(v["outliers"]) for v in perfil_results["levels"].values())
        outlier_rate = n_outliers / n_total if n_total > 0 else 0
        if outlier_rate > 0.25:
            status = "⚠️  ALTA VARIANZA"
        elif not all_separated and perfil not in G_NOT_PRIMARY:
            status = "⚠️  GRUPOS SOLAPADOS"
        else:
            status = "✅ COHESIVO"

        perfil_results["status"] = status
        perfil_results["n_outliers"] = n_outliers
        results[perfil] = perfil_results

        if verbose:
            lines.append(f"\n{status}  {perfil}  (n={n_total})")
            for k, info in perfil_results["levels"].items():
                g_str = f"G={info['g_mean']:.2f}±{info['g_std']:.2f}" if info["g_mean"] is not None else "G=—"
                d_str = f"D={info['d_mean']:.2f}±{info['d_std']:.2f}" if info["d_mean"] is not None else "D=—"
                lines.append(f"  {k} (n={info['n']}): {g_str}  {d_str}")
                for out in info["outliers"]:
                    lines.append(f"    ⚡ outlier G={out['G']} z={out['z']}  {out['handle'][:60]}")
            for sep in perfil_results["separations"]:
                if sep["p"] is not None:
                    sym = "✅" if sep["separated"] else "⚠️"
                    lines.append(f"  Separación {sep['pair']}: {sym} p={sep['p']:.3f}")

    cohesive = sum(1 for r in results.values() if "✅" in r["status"])
    total_t  = len(results)
    cohesion_pct = cohesive / total_t * 100 if total_t else 0

    lines += ["", "─"*65, "RESUMEN TEST 2",
              f"  Perfiles con ≥2 niveles: {total_t}",
              f"  ✅ Cohesivos:   {cohesive}",
              f"  ⚠️  Varianza alta o solapados: {total_t - cohesive}",
              f"  Score cohesión: {cohesion_pct:.0f}/100",
    ]

    if verbose:
        print("\n".join(lines))

    return results, cohesion_pct, "\n".join(lines)

# ─── TEST 3: Outlier products (candidates for reclassification) ───────────────

def test_outliers(df, verbose=True):
    """
    Identifies individual products that look like they belong in a different
    (perfil_proceso × complejidad) bucket based on available driver scores.

    For each product: compute how its driver scores compare to ALL buckets.
    If its scores are closer to a different bucket's centroid → flag it.
    """
    lines = ["", "="*65,
             "TEST 3 — PRODUCTOS CANDIDATOS A RECLASIFICACIÓN",
             "="*65]

    candidates = []

    # Build bucket centroids using G and D
    buckets = {}
    for (perfil, comp), grp in df.groupby(["perfil_proceso", "complejidad"]):
        g_vals = grp["G"].dropna()
        d_vals = grp["D"].dropna()
        if len(grp) >= 2:
            buckets[(perfil, comp)] = {
                "g_mean": g_vals.mean() if len(g_vals) else None,
                "d_mean": d_vals.mean() if len(d_vals) else None,
                "n": len(grp),
            }

    def bucket_distance(g, d, centroid):
        """Euclidean distance from product (G,D) to bucket centroid."""
        dims = []
        if g is not None and centroid["g_mean"] is not None:
            dims.append((g/3 - centroid["g_mean"]/3) ** 2)
        if d is not None and centroid["d_mean"] is not None:
            dims.append((d/3 - centroid["d_mean"]/3) ** 2)
        if not dims:
            return np.nan
        return float(np.sqrt(sum(dims)))

    for _, row in df.iterrows():
        perfil = row["perfil_proceso"]
        comp   = row["complejidad"]
        g      = row["G"] if pd.notna(row.get("G")) else None
        d      = row["D"] if pd.notna(row.get("D")) else None

        if g is None and d is None:
            continue  # no driver data — can't compare
        if (perfil, comp) not in buckets:
            continue

        current_key = (perfil, comp)
        current_dist = bucket_distance(g, d, buckets[current_key])

        # Find closest bucket within the same perfil
        same_perfil_buckets = {k: v for k, v in buckets.items()
                               if k[0] == perfil and k != current_key}
        if not same_perfil_buckets:
            continue

        best_key, best_dist = min(
            ((k, bucket_distance(g, d, v)) for k, v in same_perfil_buckets.items()
             if not np.isnan(bucket_distance(g, d, v))),
            key=lambda x: x[1],
            default=(None, np.nan),
        )

        if best_key is None or np.isnan(best_dist) or np.isnan(current_dist):
            continue

        # Flag if another bucket is meaningfully closer
        if best_dist < current_dist * 0.6:  # 40% closer = flag
            candidates.append({
                "handle":       row["handle"],
                "current":      f"{perfil} {comp}",
                "suggested":    f"{best_key[0]} {best_key[1]}",
                "current_dist": round(current_dist, 3),
                "best_dist":    round(best_dist, 3),
                "G": g, "D": d,
                "descripcion":  str(row.get("descripcion_web", ""))[:80],
            })

    lines.append(f"\n{len(candidates)} productos candidatos a revisar:\n")
    for c in sorted(candidates, key=lambda x: x["best_dist"] - x["current_dist"]):
        lines.append(f"  {c['handle'][:55]:55s}  {c['current']} → {c['suggested']}")
        lines.append(f"    G={c['G']}  D={c['D']}   dist_actual={c['current_dist']}  dist_sugerida={c['best_dist']}")
        if c["descripcion"]:
            lines.append(f"    \"{c['descripcion']}\"")

    lines += ["", "─"*65, "RESUMEN TEST 3",
              f"  Productos candidatos a reclasificación: {len(candidates)}",
              "  (Estos son candidatos — requieren validación humana en la app)",
    ]

    if verbose:
        print("\n".join(lines))

    return candidates, len(candidates), "\n".join(lines)

# ─── TEST 4: Coverage ─────────────────────────────────────────────────────────

def test_coverage(df, verbose=True):
    """How well does the current categorization cover the catalog."""
    lines = ["", "="*65, "TEST 4 — COBERTURA Y ESTADO DE VALIDACIÓN", "="*65]

    total = len(df[df["perfil_proceso"] != "p-importado"])
    validated = df[(df["perfil_proceso"] != "p-importado") & (df["validated"] == 1)]
    no_perf = df[df["perfil_proceso"].isna() | (df["perfil_proceso"] == "")]
    no_comp  = df[df["complejidad"].isna() | (df["complejidad"] == "")]
    no_dims  = df[df["G"].isna() & df["D"].isna()]

    validated_pct = len(validated) / total * 100 if total else 0
    coverage_pct  = (1 - len(no_dims) / total) * 100 if total else 0

    lines += [
        f"\n  Total fabricado (sin importados): {total}",
        f"  Validados por humano:  {len(validated)} ({validated_pct:.0f}%)",
        f"  Sin perfil_proceso:    {len(no_perf)}",
        f"  Sin complejidad:       {len(no_comp)}",
        f"  Sin datos dimensiones: {len(no_dims)} ({100-coverage_pct:.0f}% sin G ni D)",
        f"",
        f"  Validación por perfil:",
    ]
    for perfil in sorted(df["perfil_proceso"].dropna().unique()):
        grp = df[df["perfil_proceso"] == perfil]
        val = grp[grp["validated"] == 1]
        lines.append(f"    {perfil:25s}  {len(val):3d}/{len(grp):3d} validados")

    lines += ["", "─"*65, "RESUMEN TEST 4",
              f"  Score cobertura dims:    {coverage_pct:.0f}/100",
              f"  Score validación humana: {validated_pct:.0f}/100  (actualmente 0 — primer run)",
    ]

    if verbose:
        print("\n".join(lines))

    return {"coverage_pct": coverage_pct, "validated_pct": validated_pct}, coverage_pct, "\n".join(lines)

# ─── ICM ──────────────────────────────────────────────────────────────────────

def compute_ICM(coherence_pct, cohesion_pct, coverage_pct, drift_pct=None):
    """
    Índice de Confianza del Modelo — 0 to 100.

    Weights:
      35% coherencia de drivers (declared drivers correlate with complexity)
      25% cohesión intra-grupo (products within bucket are similar)
      15% cobertura (dimension data + human validation)
      25% drift real vs estimado (only when chronometer data exists)
    """
    w_coh  = 0.35
    w_gru  = 0.25
    w_cov  = 0.15
    w_drif = 0.25

    if drift_pct is None:
        total_w = w_coh + w_gru + w_cov
        ICM = (w_coh/total_w * coherence_pct +
               w_gru/total_w * cohesion_pct  +
               w_cov/total_w * coverage_pct)
    else:
        ICM = (w_coh  * coherence_pct +
               w_gru  * cohesion_pct  +
               w_cov  * coverage_pct  +
               w_drif * drift_pct)

    return round(ICM, 1)

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", default="full",
                        choices=["drivers","cohesion","outliers","coverage","full"])
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    print(f"\n{'='*65}")
    print(f"DULOX MODEL AUDITOR — {date.today()}")
    print(f"DB: {DB.name}")
    rules_src = f"PROCESS_RULES.json v{_RULES['meta']['version']}" if _RULES else "fallback hardcoded"
    print(f"Reglas: {rules_src}  |  G≥{_G_BREAKPOINTS}mm²  D≥{_D_BREAKPOINTS}mm")
    print(f"{'='*65}")

    df = load_db()
    print(f"Productos cargados: {len(df)}")
    print(f"Perfiles únicos:    {df['perfil_proceso'].nunique()}")

    all_output = [f"# Reporte de Auditoría — {date.today()}\n"]

    coherence_pct = 50
    cohesion_pct  = 50
    coverage_pct  = 50

    if args.test in ("drivers", "full"):
        _, coherence_pct, txt = test_drivers(df)
        all_output.append(txt)

    if args.test in ("cohesion", "full"):
        _, cohesion_pct, txt = test_cohesion(df)
        all_output.append(txt)

    if args.test in ("outliers", "full"):
        _, _, txt = test_outliers(df)
        all_output.append(txt)

    if args.test in ("coverage", "full"):
        _, coverage_pct, txt = test_coverage(df)
        all_output.append(txt)

    ICM = compute_ICM(coherence_pct, cohesion_pct, coverage_pct)

    icm_block = [
        "", "="*65,
        f"ÍNDICE DE CONFIANZA DEL MODELO (ICM): {ICM}/100",
        "="*65,
        f"  Coherencia drivers:     {coherence_pct:.0f}/100  (peso 35%)",
        f"  Cohesión intra-grupo:   {cohesion_pct:.0f}/100  (peso 25%)",
        f"  Cobertura catálogo:     {coverage_pct:.0f}/100  (peso 15%)",
        f"  Drift real vs est.:     sin datos   (peso 25% — requiere cronometrajes)",
        "",
        "Interpretación:",
        "  80–100: Modelo bien calibrado",
        "  60–79:  Modelo funcional — gaps documentados",
        "  40–59:  Modelo en construcción",
        "  <40:    Modelo inconsistente — recalibración necesaria",
        "",
        f"Estado: {'Modelo en construcción' if ICM < 60 else ('Modelo funcional' if ICM < 80 else 'Modelo calibrado')}",
        "",
        "Acción de mayor impacto en ICM:",
        "  1. Agregar num_componentes/quemadores/niveles/tazas a DB  → +15–25 pts coherencia",
        "  2. Validar humano 50+ productos en review app             → +coverage",
        "  3. Medir 3 anclas con cronómetro                         → +25 pts drift",
    ]

    print("\n".join(icm_block))
    all_output.extend(icm_block)

    if args.save:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = AUDIT_DIR / f"AUDIT_{date.today()}.md"
        report_path.write_text("\n".join(all_output))
        print(f"\n✅ Reporte guardado en: {report_path}")

        log_line = (f"| {date.today()} | {args.test} | {ICM} | "
                    f"Ver reporte | — | "
                    f"[AUDIT_{date.today()}.md](audit-reports/AUDIT_{date.today()}.md) |")
        print(f"→ Agregar a AUDIT_LOG.md:\n  {log_line}")

if __name__ == "__main__":
    main()
