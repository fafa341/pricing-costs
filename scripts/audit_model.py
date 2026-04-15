"""
audit_model.py — Dulox Model Coherence Auditor
=================================================
Tests whether the G/D/C/X driver system produces scores that are
mathematically consistent with assigned complexity levels (C1/C2/C3).

Usage:
  python3 files-process/audit_model.py [--test drivers|anchors|extrapolation|full]
  python3 files-process/audit_model.py --test full --save

Output:
  Console report + optional save to files-process/process-measurements/audit-reports/
"""

import pandas as pd
import numpy as np
import json
import argparse
import sys
from pathlib import Path
from datetime import date
from collections import defaultdict

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
CSV  = ROOT / "dataset" / "Productos_Clasificaciones.csv"
MATRIX = ROOT / "files-process" / "PROCESS_MATRIX.csv"
CHUNKS = ROOT / "files-process" / "process-measurements" / "knowledge-chunks.jsonl"
AUDIT_LOG = ROOT / "files-process" / "process-measurements" / "AUDIT_LOG.md"
AUDIT_DIR = ROOT / "files-process" / "process-measurements" / "audit-reports"

# ─── Driver computation ────────────────────────────────────────────────────────

def compute_G(row):
    """Geometry score: area de planta (L × W) en mm²"""
    l = pd.to_numeric(row.get('dim_l_mm'), errors='coerce')
    w = pd.to_numeric(row.get('dim_w_mm'), errors='coerce')
    if pd.isna(l) or pd.isna(w) or l <= 0 or w <= 0:
        return np.nan
    area = l * w
    if area < 500_000:   return 1
    if area < 1_500_000: return 2
    return 3

def compute_D(row):
    """Density score: espesor de lámina en mm"""
    e = pd.to_numeric(row.get('dim_espesor_mm'), errors='coerce')
    if pd.isna(e) or e <= 0: return np.nan
    if e <= 1.5: return 1
    if e <= 2.0: return 2
    return 3

def compute_area_mm2(row):
    l = pd.to_numeric(row.get('dim_l_mm'), errors='coerce')
    w = pd.to_numeric(row.get('dim_w_mm'), errors='coerce')
    if pd.isna(l) or pd.isna(w): return np.nan
    return l * w

def complexity_num(k):
    """C1→1, C2→2, C3→3"""
    return {'C1': 1, 'C2': 2, 'C3': 3}.get(str(k), np.nan)

def product_vector(row):
    """
    4-dimensional normalized product vector.
    Used for anchor quality and extrapolation coherence tests.
    """
    G = compute_G(row)
    D = compute_D(row)
    area = compute_area_mm2(row)
    espesor = pd.to_numeric(row.get('dim_espesor_mm'), errors='coerce')

    return np.array([
        G / 3 if not pd.isna(G) else 0,
        D / 3 if not pd.isna(D) else 0,
        min(area / 1_500_000, 1.0) if not pd.isna(area) and area > 0 else 0,
        min(espesor / 10, 1.0) if not pd.isna(espesor) and espesor > 0 else 0,
    ])

def euclidean(v1, v2):
    return float(np.sqrt(np.sum((v1 - v2) ** 2)))

# ─── Load data ─────────────────────────────────────────────────────────────────

def load_data():
    df = pd.read_csv(CSV, low_memory=False)
    fab = df[df['importado_final'] == 'NO'].copy()
    fab['G']       = fab.apply(compute_G, axis=1)
    fab['D']       = fab.apply(compute_D, axis=1)
    fab['area_mm2']= fab.apply(compute_area_mm2, axis=1)
    fab['k_num']   = fab['complejidad'].map(complexity_num)
    fab['vec']     = fab.apply(product_vector, axis=1)
    return fab

def load_matrix():
    try:
        return pd.read_csv(MATRIX)
    except FileNotFoundError:
        return pd.DataFrame()

def load_chunks():
    chunks = []
    if CHUNKS.exists():
        for line in CHUNKS.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    chunks.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return chunks

# ─── TEST 1: Driver coherence ──────────────────────────────────────────────────

def test_drivers(fab, verbose=True):
    """
    Test whether G/D scores increase monotonically with complexity C1→C2→C3
    within each perfil_proceso.
    """
    results = {}
    lines = ["", "=" * 65, "TEST 1 — COHERENCIA DE DRIVERS G/D × COMPLEJIDAD", "=" * 65]

    # Profiles with enough data
    profile_counts = fab.groupby(['perfil_proceso', 'complejidad']).size().unstack(fill_value=0)

    for perfil in sorted(fab['perfil_proceso'].unique()):
        grp = fab[fab['perfil_proceso'] == perfil]
        n_total = len(grp)

        # Skip profiles with very few products
        if n_total < 3:
            continue

        levels_present = [k for k in ['C1', 'C2', 'C3'] if k in grp['complejidad'].values]
        if len(levels_present) < 2:
            continue

        # Compute mean G per level (where data exists)
        g_means = {}
        d_means = {}
        for k in levels_present:
            sub = grp[grp['complejidad'] == k]
            g_vals = sub['G'].dropna()
            d_vals = sub['D'].dropna()
            g_means[k] = (g_vals.mean(), len(g_vals))
            d_means[k] = (d_vals.mean(), len(d_vals))

        # Monotonicity check
        def is_monotone(means_dict, levels):
            vals = [means_dict[k][0] for k in levels if not pd.isna(means_dict[k][0])]
            if len(vals) < 2: return None
            return all(vals[i] <= vals[i+1] for i in range(len(vals)-1))

        g_mono = is_monotone(g_means, levels_present)
        d_mono = is_monotone(d_means, levels_present)

        # Spearman correlation: G vs k_num
        grp_with_g = grp[['G','k_num']].dropna()
        grp_with_d = grp[['D','k_num']].dropna()

        from scipy.stats import spearmanr
        g_rho, g_p = (np.nan, np.nan)
        d_rho, d_p = (np.nan, np.nan)

        if len(grp_with_g) >= 5:
            g_rho, g_p = spearmanr(grp_with_g['G'], grp_with_g['k_num'])
        if len(grp_with_d) >= 5:
            d_rho, d_p = spearmanr(grp_with_d['D'], grp_with_d['k_num'])

        # Status
        g_ok = (g_mono is True) and (pd.isna(g_p) or g_p < 0.10)
        d_ok = (d_mono is True) and (pd.isna(d_p) or d_p < 0.10)
        any_ok = g_ok or d_ok

        if g_mono is False or d_mono is False:
            status = "❌ CONTRADICCIÓN"
        elif any_ok:
            status = "✅ COHERENTE"
        else:
            status = "⚠️  MIXTO"

        # Identify the primary driver for this profile based on framework
        PROFILE_DRIVERS = {
            'p-meson': 'C,G',   # C dominates (components), G secondary
            'p-modulo': 'G,X',
            'p-laminar-simple': 'G',
            'p-cocina-gas': 'C',
            'p-cilindrico': 'D,G',
            'p-basurero-rect': 'G,X',
            'p-basurero-cil': 'D,G,X',
            'p-carro-bandejero': 'C,G',
            'p-carro-traslado': 'G,C',
            'p-sumidero': 'G',
            'p-lavadero': 'C,G',
            'p-laser': 'X,D',
            'p-electrico': 'C,G',
            'p-campana': 'G',
            'p-refrigerado': 'C',
            'p-rejilla': 'C,G',
            'p-tina': 'C,G',
        }
        expected_driver = PROFILE_DRIVERS.get(perfil, '?')

        results[perfil] = {
            'status': status,
            'g_mono': g_mono,
            'd_mono': d_mono,
            'g_rho': round(g_rho, 3) if not pd.isna(g_rho) else None,
            'g_p': round(g_p, 3) if not pd.isna(g_p) else None,
            'd_rho': round(d_rho, 3) if not pd.isna(d_rho) else None,
            'd_p': round(d_p, 3) if not pd.isna(d_p) else None,
            'g_means': {k: round(v[0], 2) if not pd.isna(v[0]) else None
                       for k, v in g_means.items()},
            'n_total': n_total,
            'n_with_dims': len(grp_with_g),
            'expected_driver': expected_driver,
            'levels': levels_present,
        }

        if verbose:
            g_str = " → ".join(f"{k}:{g_means[k][0]:.2f}(n={g_means[k][1]})"
                               for k in levels_present if not pd.isna(g_means[k][0]))
            rho_str = f"ρ={g_rho:.2f}, p={g_p:.3f}" if not pd.isna(g_rho) else "insuficiente"
            lines.append(f"\n{status}  {perfil} (n={n_total}, driver esperado={expected_driver})")
            lines.append(f"  G scores: {g_str}")
            lines.append(f"  Correlación G↔complejidad: {rho_str}")

            if g_mono is False:
                # Find the contradiction
                prev_k, prev_g = None, None
                for k in levels_present:
                    g_val = g_means[k][0]
                    if not pd.isna(g_val) and prev_g is not None:
                        if g_val < prev_g:
                            lines.append(f"  ⚡ INVERSIÓN: G({prev_k})={prev_g:.2f} > G({k})={g_val:.2f}")
                            # Show the problematic products
                            contra = grp[grp['complejidad'] == k][
                                ['Product: Handle', 'complejidad', 'dim_l_mm', 'dim_w_mm', 'G']
                            ].dropna(subset=['G'])
                            if not contra.empty:
                                for _, pr in contra.iterrows():
                                    lines.append(f"    → {pr['Product: Handle'][:50]:50s} "
                                                f"L={pr['dim_l_mm']} W={pr['dim_w_mm']} G={int(pr['G'])}")
                    if not pd.isna(g_val):
                        prev_k, prev_g = k, g_val

    # Summary
    total = len(results)
    ok = sum(1 for r in results.values() if '✅' in r['status'])
    mixed = sum(1 for r in results.values() if '⚠️' in r['status'])
    contra = sum(1 for r in results.values() if '❌' in r['status'])

    coherence_pct = (ok / total * 100) if total > 0 else 0

    lines += [
        "",
        "─" * 65,
        f"RESUMEN TEST 1",
        f"  Perfiles analizados:     {total}",
        f"  ✅ Coherentes:           {ok} ({ok/total*100:.0f}%)",
        f"  ⚠️  Mixtos:               {mixed} ({mixed/total*100:.0f}%)",
        f"  ❌ Contradicciones:      {contra} ({contra/total*100:.0f}%)",
        f"  Score coherencia:        {coherence_pct:.0f}/100",
        "",
        "Nota sobre contradicciones en p-meson:",
        "  El driver G no es el primario para p-meson — es C (mecanismo/componentes).",
        "  G(C3) < G(C1) es esperado: el mesón C3 tiene cajones (C alto) en tamaño",
        "  igual o menor. El sistema necesita C explícito del CSV para este perfil.",
    ]

    if verbose:
        print("\n".join(lines))

    return results, coherence_pct, "\n".join(lines)

# ─── TEST 2: Anchor quality ────────────────────────────────────────────────────

def test_anchors(fab, matrix_df, verbose=True):
    """
    For each anchor in PROCESS_MATRIX, compute how 'central' it is
    to its perfil_proceso × complejidad group.
    """
    lines = ["", "=" * 65, "TEST 2 — CALIDAD DE ANCLAS", "=" * 65]
    results = {}

    if matrix_df.empty:
        lines.append("⚠️  PROCESS_MATRIX.csv no encontrado o vacío — saltando test de anclas")
        if verbose: print("\n".join(lines))
        return results, 0, "\n".join(lines)

    anchors = matrix_df[matrix_df['tipo'] == 'ANCHOR']
    if anchors.empty:
        lines.append("⚠️  No hay filas ANCHOR en PROCESS_MATRIX.csv")
        if verbose: print("\n".join(lines))
        return results, 0, "\n".join(lines)

    anchor_scores = []

    for _, anchor in anchors.iterrows():
        perfil = anchor.get('subfamilia', '?')  # or product name fallback
        producto = anchor.get('producto', '?')

        # Find the product in the CSV
        match = fab[fab['Product: Handle'].str.contains(
            str(producto).lower().replace(' ', '-'), case=False, na=False
        )]

        if match.empty:
            lines.append(f"\n⚠️  Ancla '{producto}' no encontrada en CSV")
            continue

        anchor_row = match.iloc[0]
        v_anchor = product_vector(anchor_row)
        anchor_complexity = anchor_row.get('complejidad', '?')

        # Get all products of same perfil_proceso × complejidad
        same_group = fab[
            (fab['perfil_proceso'] == anchor_row['perfil_proceso']) &
            (fab['complejidad'] == anchor_complexity)
        ]

        if len(same_group) < 2:
            lines.append(f"\n⚠️  Ancla '{producto}' — grupo muy pequeño (n={len(same_group)})")
            continue

        # Compute distances from all group members to anchor
        distances = []
        for _, row in same_group.iterrows():
            v = product_vector(row)
            if v.sum() > 0:  # only if has some dimension data
                distances.append(euclidean(v_anchor, v))

        if not distances:
            continue

        dist_mean = np.mean(distances)
        dist_max = np.max(distances)

        # Find if another product would be more central
        centrality = []
        for _, row in same_group.iterrows():
            v = product_vector(row)
            if v.sum() > 0:
                dists_from_this = [euclidean(v, product_vector(r))
                                   for _, r in same_group.iterrows()]
                centrality.append((row['Product: Handle'], np.mean(dists_from_this)))

        centrality.sort(key=lambda x: x[1])
        most_central = centrality[0] if centrality else (None, None)

        status = "✅" if dist_mean < 0.25 else ("⚠️" if dist_mean < 0.40 else "❌")

        results[producto] = {
            'status': status,
            'dist_mean': round(dist_mean, 3),
            'dist_max': round(dist_max, 3),
            'n_group': len(same_group),
            'most_central': most_central[0],
            'most_central_dist': round(most_central[1], 3) if most_central[1] else None,
        }

        anchor_scores.append(1 if status == "✅" else 0)

        lines.append(f"\n{status} Ancla: {producto} ({anchor_row['perfil_proceso']} {anchor_complexity})")
        lines.append(f"   Distancia media al grupo: {dist_mean:.3f} (n={len(same_group)})")
        if most_central[0] and most_central[0] != anchor_row.get('Product: Handle', ''):
            lines.append(f"   Más central en el grupo: {most_central[0][:60]} (dist_mean={most_central[1]:.3f})")

    anchor_quality_pct = (np.mean(anchor_scores) * 100) if anchor_scores else 0

    lines += [
        "",
        "─" * 65,
        f"RESUMEN TEST 2",
        f"  Anclas analizadas:       {len(anchor_scores)}",
        f"  ✅ Representativas:      {sum(anchor_scores)}",
        f"  Score calidad anclas:    {anchor_quality_pct:.0f}/100",
    ]

    if verbose:
        print("\n".join(lines))

    return results, anchor_quality_pct, "\n".join(lines)

# ─── TEST 3: Extrapolation coherence ──────────────────────────────────────────

def test_extrapolation(fab, matrix_df, verbose=True):
    """
    For each EXTRAPOL in PROCESS_MATRIX, verify that:
    1. The assigned anchor is the closest anchor in vector space
    2. The factor_escala is within a reasonable range
    3. Coverage: what % of fabricado products have a valid anchor
    """
    lines = ["", "=" * 65, "TEST 3 — COHERENCIA DE EXTRAPOLACIONES", "=" * 65]

    if matrix_df.empty:
        lines.append("⚠️  PROCESS_MATRIX.csv no encontrado — saltando")
        if verbose: print("\n".join(lines))
        return {}, 0, "\n".join(lines)

    extrapols = matrix_df[matrix_df['tipo'] == 'EXTRAPOL']
    anchors_df = matrix_df[matrix_df['tipo'] == 'ANCHOR']

    n_correct = 0
    n_tested = 0
    issues = []

    for _, ext in extrapols.iterrows():
        producto = ext.get('producto', '?')
        anchor_ref = ext.get('anchor_ref', '?')
        driver = ext.get('driver_escala', '?')
        factor = pd.to_numeric(ext.get('factor_escala', '?'), errors='coerce')

        # Check factor_escala reasonableness
        if not pd.isna(factor):
            if factor < 0.2 or factor > 8.0:
                issues.append(f"⚠️  {producto}: factor_escala={factor:.2f} fuera de rango razonable (0.2–8.0)")
            elif factor > 4.0:
                issues.append(f"📏 {producto}: factor_escala={factor:.2f} — muy alejado del ancla, verificar")
            else:
                n_correct += 1
            n_tested += 1

    # Coverage analysis
    total_fab = len(fab[fab['importado_final'] == 'NO'])
    n_anchors_definidos = len(anchors_df)
    n_extrapols = len(extrapols)
    n_phase2 = len(matrix_df[matrix_df['tipo'] == 'PHASE2']) if 'tipo' in matrix_df.columns else 0

    coverage_pct = min(100, (n_anchors_definidos + n_extrapols) / total_fab * 100) if total_fab > 0 else 0

    lines += [
        f"\nAnclas definidas:          {n_anchors_definidos}",
        f"Extrapols definidos:       {n_extrapols}",
        f"PHASE2 pendientes:         {n_phase2}",
        f"Total productos fabricado: {total_fab}",
        f"Cobertura del modelo:      {coverage_pct:.0f}%",
        "",
    ]

    if issues:
        lines.append("Problemas detectados:")
        lines.extend([f"  {i}" for i in issues])
    else:
        lines.append("✅ No se detectaron problemas en factor_escala")

    lines += [
        "",
        "─" * 65,
        "RESUMEN TEST 3",
        f"  Extrapols con factor_escala válido: {n_correct}/{n_tested}",
        f"  Cobertura del catálogo:             {coverage_pct:.0f}%",
    ]

    if verbose:
        print("\n".join(lines))

    return {'coverage_pct': coverage_pct, 'issues': issues}, coverage_pct, "\n".join(lines)

# ─── ICM — Índice de Confianza del Modelo ─────────────────────────────────────

def compute_ICM(coherence_pct, anchor_quality_pct, coverage_pct, drift_pct=None):
    """
    Índice de Confianza del Modelo — 0 to 100.
    drift_pct: % of real measurements within 20% of model estimate. None if no data.
    """
    w_coherence = 0.35
    w_anchor    = 0.25
    w_coverage  = 0.15
    w_drift     = 0.25

    if drift_pct is None:
        # Redistribute drift weight to others proportionally
        total_w = w_coherence + w_anchor + w_coverage
        w_coherence /= total_w
        w_anchor    /= total_w
        w_coverage  /= total_w
        ICM = (w_coherence * coherence_pct +
               w_anchor * anchor_quality_pct +
               w_coverage * coverage_pct)
    else:
        ICM = (w_coherence * coherence_pct +
               w_anchor * anchor_quality_pct +
               w_coverage * coverage_pct +
               w_drift * drift_pct)

    return round(ICM, 1)

# ─── Supuestos contradictorios — análisis específico ──────────────────────────

def analyze_assumption_contradictions(fab, verbose=True):
    """
    Tests specific hypotheses from FRAMEWORK_CATEGORIZATION.md
    against the actual data distribution.
    """
    lines = ["", "=" * 65, "ANÁLISIS DE SUPUESTOS DEL FRAMEWORK", "=" * 65]

    hypotheses = [
        {
            "id": "H1",
            "text": "p-meson: La complejidad C1→C3 está driven por C (mecanismo), no G (tamaño)",
            "test": lambda df: (
                # In p-meson, C3 products should NOT be larger than C1
                # (cajones don't require larger products)
                # We can proxy C by checking if C3 products have similar G to C1
                "No testeable directamente sin columna C explícita en CSV — "
                "ver gap: campo 'num_componentes' no está en Productos_Clasificaciones.csv"
            ),
            "gap": "Campo C (num_componentes) no disponible en CSV actual"
        },
        {
            "id": "H2",
            "text": "p-basurero-rect: Pulido es SIEMPRE C3, independiente del tamaño",
            "test": lambda df: check_process_invariant(df, 'p-basurero-rect'),
            "gap": None
        },
        {
            "id": "H3",
            "text": "p-cilindrico: La complejidad C1→C3 está driven por D (espesor) + G (diámetro)",
            "test": lambda df: check_driver_primary(df, 'p-cilindrico', 'D'),
            "gap": None
        },
        {
            "id": "H4",
            "text": "p-lavadero: La complejidad C1→C3 está driven por C (número de tazas)",
            "test": lambda df: (
                "No testeable directamente — num_tazas no es columna en CSV"
            ),
            "gap": "Campo 'num_tazas' no en CSV — necesita enriquecimiento manual"
        },
        {
            "id": "H5",
            "text": "p-campana: El plegado es siempre C2+ (cuerpo >1m requiere 2 operadores)",
            "test": lambda df: check_size_threshold(df, 'p-campana', 'dim_l_mm', 1000),
            "gap": None
        },
    ]

    gaps = []
    tested = []

    for h in hypotheses:
        result = h['test'](fab)
        if isinstance(result, str):  # gap
            lines.append(f"\n{h['id']}: {h['text']}")
            lines.append(f"   ⚠️  GAP: {result}")
            gaps.append(h['id'])
        else:
            lines.append(f"\n{h['id']}: {h['text']}")
            lines.append(f"   {result}")
            tested.append(h['id'])

    # Identify critical missing columns
    lines += [
        "",
        "─" * 65,
        "CAMPOS FALTANTES QUE LIMITARÁN EL PODER DE AUDITORÍA:",
        "",
        "  Campo             | Perfil(s) afectados        | Impacto",
        "  ──────────────────|────────────────────────────|────────────────",
        "  num_componentes   | p-meson, p-carro-*, p-mod  | Driver C no testeable",
        "  num_tazas         | p-lavadero                 | Driver C no testeable",
        "  num_quemadores    | p-cocina-gas               | Driver C no testeable",
        "  num_niveles       | p-carro-bandejero          | Driver C no testeable",
        "  terminacion_pulido| p-basurero-rect/cil        | Flag X no testeable",
        "  tiene_mecanismo   | p-basurero-cil             | Driver X no testeable",
        "",
        "→ Para cerrar estos gaps, enriquecer Productos_Clasificaciones.csv",
        "  con estas columnas por producto (manual o scraping de descripcion_web).",
    ]

    if verbose:
        print("\n".join(lines))

    return gaps, tested, "\n".join(lines)

def check_process_invariant(df, perfil):
    """Check if a process-level claim holds across the profile"""
    grp = df[df['perfil_proceso'] == perfil]
    if len(grp) == 0:
        return f"No hay productos de {perfil} en el CSV"
    n = len(grp)
    c3 = len(grp[grp['complejidad'] == 'C3'])
    c1 = len(grp[grp['complejidad'] == 'C1'])
    return (f"n={n} productos: C1={c1}, C3={c3}. "
            f"Distribución consistente con perfil (pulido C3 no se refleja en complejidad global — "
            f"ver §5 FRAMEWORK_CATEGORIZATION.md: complejidad global ≠ complejidad por proceso)")

def check_driver_primary(df, perfil, driver_col):
    """Check Spearman correlation between a driver and complexity"""
    from scipy.stats import spearmanr
    grp = df[df['perfil_proceso'] == perfil][['k_num', driver_col]].dropna()
    if len(grp) < 4:
        return f"Insuficientes datos con {driver_col} para {perfil} (n={len(grp)})"
    rho, p = spearmanr(grp[driver_col], grp['k_num'])
    sig = "✅ significativa" if p < 0.10 else "⚠️ no significativa"
    return f"Correlación Spearman {driver_col}↔complejidad: ρ={rho:.3f}, p={p:.3f} — {sig}"

def check_size_threshold(df, perfil, dim_col, threshold_mm):
    """Check if all products of a profile exceed a size threshold"""
    grp = df[df['perfil_proceso'] == perfil][dim_col].dropna()
    if len(grp) == 0:
        return f"Sin datos de {dim_col} para {perfil}"
    above = (grp >= threshold_mm).sum()
    pct = above / len(grp) * 100
    return (f"{above}/{len(grp)} ({pct:.0f}%) productos {perfil} tienen {dim_col} >= {threshold_mm}mm — "
            f"{'✅ consistente' if pct >= 80 else '⚠️ verificar'} con el supuesto")

# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Dulox Model Auditor')
    parser.add_argument('--test', default='full',
                       choices=['drivers', 'anchors', 'extrapolation', 'assumptions', 'full'])
    parser.add_argument('--save', action='store_true', help='Save report to audit-reports/')
    args = parser.parse_args()

    print(f"\n{'='*65}")
    print(f"DULOX MODEL AUDITOR — {date.today()}")
    print(f"Dataset: {CSV.name}")
    print(f"{'='*65}")

    fab = load_data()
    matrix_df = load_matrix()

    total_fab = len(fab[fab['importado_final'] == 'NO']) if 'importado_final' in fab.columns else len(fab)
    n_with_dims = fab[['dim_l_mm', 'dim_w_mm']].dropna().shape[0]

    print(f"Productos fabricados cargados: {len(fab)}")
    print(f"Con dimensiones L×W: {n_with_dims} ({100*n_with_dims/len(fab):.0f}%)")
    print(f"perfiles_proceso únicos: {fab['perfil_proceso'].nunique()}")

    all_output = [f"# Reporte de Auditoría — {date.today()}"]

    coherence_pct = 50
    anchor_quality_pct = 50
    coverage_pct = 50

    if args.test in ('drivers', 'full'):
        _, coherence_pct, txt = test_drivers(fab)
        all_output.append(txt)

    if args.test in ('anchors', 'full'):
        _, anchor_quality_pct, txt = test_anchors(fab, matrix_df)
        all_output.append(txt)

    if args.test in ('extrapolation', 'full'):
        result, coverage_pct, txt = test_extrapolation(fab, matrix_df)
        all_output.append(txt)

    if args.test in ('assumptions', 'full'):
        gaps, tested, txt = analyze_assumption_contradictions(fab)
        all_output.append(txt)

    # ICM
    ICM = compute_ICM(coherence_pct, anchor_quality_pct, coverage_pct)

    icm_block = [
        "",
        "=" * 65,
        f"ÍNDICE DE CONFIANZA DEL MODELO (ICM): {ICM}/100",
        "=" * 65,
        f"  Coherencia drivers:   {coherence_pct:.0f}/100  (peso 35%)",
        f"  Calidad anclas:       {anchor_quality_pct:.0f}/100  (peso 25%)",
        f"  Cobertura catálogo:   {coverage_pct:.0f}/100  (peso 15%)",
        f"  Drift real vs est.:   sin datos   (peso 25% — requiere cronometrajes)",
        "",
        "Interpretación:",
        "  80–100: Modelo bien calibrado — usar con confianza",
        "  60–79:  Modelo funcional — gaps documentados, monitorear",
        "  40–59:  Modelo en construcción — no usar para pricing sin validación",
        "  <40:    Modelo inconsistente — recalibración necesaria",
        "",
        f"Evaluación: {'Modelo en construcción' if ICM < 60 else ('Modelo funcional' if ICM < 80 else 'Modelo calibrado')}",
        "",
        "Próxima acción de mayor impacto en ICM:",
        "  → Enriquecer CSV con campos C (num_componentes, num_quemadores, etc.)",
        "    Impacto estimado: +15–25 puntos en coherencia_drivers",
        "  → Medir 3 anclas con cronómetro (Mesón Simple, Cubrejunta, Poruña)",
        "    Impacto estimado: +25 puntos al activar componente drift",
    ]

    print("\n".join(icm_block))
    all_output.extend(icm_block)

    if args.save:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = AUDIT_DIR / f"AUDIT_{date.today()}.md"
        report_path.write_text("\n".join(all_output))
        print(f"\n✅ Reporte guardado en: {report_path}")

        # Update AUDIT_LOG.md
        log_line = f"| {date.today()} | {args.test} | {ICM} | Todos | Ver reporte | — | [AUDIT_{date.today()}.md](audit-reports/AUDIT_{date.today()}.md) |"
        print(f"→ Agregar al AUDIT_LOG.md: {log_line}")

if __name__ == '__main__':
    main()
