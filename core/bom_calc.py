"""
bom_calc.py — Deterministic BOM computation for Dulox pricing system
======================================================================
Two material types:

  TYPE 1 — Formula-based (materia prima from ERP catalog):
    KG types (Plancha, Coil):  qty_total = kg_bruto × cant
    ML types (Perfil, Tubo, Macizo): qty_total = L_mm / 1000 × cant
    valor_unit from global constants (editable per-row override)
    total_clp = qty_total × valor_unit

  TYPE 2 — Manual (hardware, fittings, components):
    tipo = "Otro" or anything not in formula types
    qty_total = cant  (unidades)
    valor_unit entered manually per row
    total_clp = cant × valor_unit
    kg fields are None / not computed

Density: 8 kg/m² per mm espesor = 8e-6 kg/mm³ (empirical, validated MP0001/MP0002).
  1mm → ×8 kg/m², 2mm → ×16 kg/m². Proportionate for all thicknesses.

Waste factor (deterministic from tipo + simbolos):
  Plancha + ⊙/CIL → cilindrado_manto
  Plancha + es_diametro → corte_plancha_circular
  Plancha → corte_plancha_rectangular
  Perfil / Tubo → corte_perfil_tubo
  Macizo → corte_macizo

Global prices: pass global_prices dict (from Supabase app_settings) to
  compute_part/compute_bom. Per-row valor_unit overrides the global.
"""

import json
import math
from pathlib import Path
from typing import Optional

ROOT            = Path(__file__).resolve().parent.parent
INVENTORY_FILE  = ROOT / "data" / "inventory_map.json"
WASTE_FILE      = ROOT / "data" / "waste_factors.json"

# ─── Constants ────────────────────────────────────────────────────────────────

DENSITY         = 0.000008      # kg/mm³ — 8 kg/m²/mm, all grades (empirical)

DEFAULT_CALIDAD       = "304"
DEFAULT_WASTE_FACTOR  = 1.05
DEFAULT_PRECIO_KG     = 3600    # CLP/kg fallback

# Material type classification
_KG_TYPES  = {"plancha", "coil"}
_ML_TYPES  = {"perfil", "tubo", "macizo", "barra"}
_ALL_FORMULA_TYPES = _KG_TYPES | _ML_TYPES

# ─── Load reference files ─────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

_INVENTORY  = _load_json(INVENTORY_FILE)
_WASTE      = _load_json(WASTE_FILE)

def reload():
    """Call to refresh in-memory data after files change."""
    global _INVENTORY, _WASTE
    _INVENTORY  = _load_json(INVENTORY_FILE)
    _WASTE      = _load_json(WASTE_FILE)


# ─── Material type ────────────────────────────────────────────────────────────

def mat_type(tipo: str) -> str:
    """
    Returns 'formula_kg' | 'formula_ml' | 'manual'.
    formula_kg: Plancha, Coil — kg formula applies
    formula_ml: Perfil, Tubo, Macizo — metro lineal
    manual:     Otro / hardware / empty
    """
    t = (str(tipo) if tipo is not None and not (isinstance(tipo, float) and math.isnan(tipo)) else "").strip().lower()
    if t in _KG_TYPES:
        return "formula_kg"
    if t in _ML_TYPES:
        return "formula_ml"
    return "manual"


# ─── Kg formula — Plancha / Coil ─────────────────────────────────────────────

def kg_neto(tipo: str, L_mm: Optional[float], A_mm: Optional[float],
            esp_mm: Optional[float], es_diametro: bool = False,
            calidad: str = DEFAULT_CALIDAD) -> Optional[float]:
    """
    Net Kg of one unit (before waste). Only valid for KG types.
    Plancha/Coil: L × A × esp × 8e-6
    Tubo:         π × Ø × esp × L × 8e-6  (A_mm = outer diameter)
    Perfil/Macizo: None — billed per ML, not kg
    """
    t = (str(tipo) if tipo is not None and not (isinstance(tipo, float) and math.isnan(tipo)) else "").strip().lower()

    if t in ("plancha", "coil"):
        if L_mm is None or A_mm is None or esp_mm is None:
            return None
        return L_mm * A_mm * esp_mm * DENSITY

    elif t == "tubo":
        if L_mm is None or A_mm is None or esp_mm is None:
            return None
        return math.pi * A_mm * esp_mm * L_mm * DENSITY

    return None  # Perfil, Macizo, Otro — not kg-based


# ─── Waste factor ─────────────────────────────────────────────────────────────

def waste_factor(tipo: str, simbolos: list, es_diametro: bool = False) -> tuple[float, str, bool]:
    """Returns (factor, operation_key, assumed)."""
    ops = _WASTE.get("operaciones", {})
    t   = (tipo or "").strip().lower()
    syms = [s.upper() for s in (simbolos or [])]

    if t in ("plancha", "coil"):
        if "⊙" in syms or "CIL" in syms or "CILINDRADO" in syms:
            key = "cilindrado_manto"
        elif es_diametro:
            key = "corte_plancha_circular"
        else:
            key = "corte_plancha_rectangular"
    elif t == "perfil":
        key = "corte_perfil_tubo"
    elif t == "tubo":
        key = "corte_perfil_tubo"
    elif t in ("macizo", "barra"):
        key = "corte_macizo"
    else:
        return DEFAULT_WASTE_FACTOR, "default", True

    entry   = ops.get(key, {})
    factor  = entry.get("factor", DEFAULT_WASTE_FACTOR)
    assumed = key not in ops
    return factor, key, assumed


# ─── Global price lookup ──────────────────────────────────────────────────────

def _lookup_global_price(tipo: str, calidad: str, esp_mm: Optional[float],
                         global_prices: Optional[dict]) -> float:
    """
    Resolve valor_unit from global_prices catalog.
    global_prices shape: { "planchas": {"304": {"1.0": 3600, ...}}, "perfiles": {...}, ... }
    Falls back to DEFAULT_PRECIO_KG if not found.
    """
    if not global_prices:
        return DEFAULT_PRECIO_KG

    t = (str(tipo) if tipo is not None and not (isinstance(tipo, float) and math.isnan(tipo)) else "").strip().lower()
    c = (calidad or DEFAULT_CALIDAD).strip()

    if t in ("plancha", "coil"):
        esp_key = _esp_key(esp_mm)
        return (global_prices.get("planchas", {})
                              .get(c, {})
                              .get(esp_key, DEFAULT_PRECIO_KG))

    if t == "perfil":
        # No per-row section lookup yet — return category default
        return global_prices.get("perfil_default", DEFAULT_PRECIO_KG)

    if t == "tubo":
        return global_prices.get("tubo_default", DEFAULT_PRECIO_KG)

    if t in ("macizo", "barra"):
        return global_prices.get("macizo_default", DEFAULT_PRECIO_KG)

    return DEFAULT_PRECIO_KG


def _esp_key(esp_mm: Optional[float]) -> str:
    """Convert esp_mm float to lookup key: 1.0 → '1.0', 1.5 → '1.5'."""
    if esp_mm is None:
        return ""
    s = str(round(float(esp_mm), 2))
    # Ensure one decimal place minimum: "1" → "1.0"
    if "." not in s:
        s += ".0"
    return s


# ─── SKU resolver ─────────────────────────────────────────────────────────────

def resolve_sku(tipo: str, calidad: str = DEFAULT_CALIDAD,
                esp_mm: Optional[float] = None) -> dict:
    """Look up ERP SKU from inventory_map.json. Returns {sku_erp, assumed}."""
    t = (str(tipo) if tipo is not None and not (isinstance(tipo, float) and math.isnan(tipo)) else "").strip().lower()
    c = (calidad or DEFAULT_CALIDAD).strip()
    assumed_calidad = not calidad or calidad.strip() == ""
    if assumed_calidad:
        c = DEFAULT_CALIDAD

    result = {"sku_erp": None, "assumed": True}

    if t in ("plancha", "coil") and esp_mm is not None:
        key = _esp_key(esp_mm)
        plancha_lookup = _INVENTORY.get("_plancha_lookup", {})
        entry = plancha_lookup.get(key)
        if entry:
            result.update({
                "sku_erp": entry.get("sku_erp"),
                "assumed": assumed_calidad or entry.get("sku_erp") is None,
            })

    return result


# ─── Full part computation ────────────────────────────────────────────────────

def compute_part(row: dict, global_prices: Optional[dict] = None) -> dict:
    """
    Compute all derived fields for a single BOM row.

    Input keys (editable): tipo, calidad, esp_mm, L_mm, A_mm, cant, simbolos,
                            valor_unit (optional per-row override)
    Output adds: mat_type, unidad, kg_neto, waste_factor, waste_op, kg_bruto,
                 qty_total, sku_material, valor_unit, total_clp, warnings
    """
    tipo    = row.get("tipo", "Plancha")
    calidad = row.get("calidad") or DEFAULT_CALIDAD
    esp_mm  = _to_float(row.get("esp_mm"))
    L_mm    = _to_float(row.get("L_mm"))
    A_mm    = _to_float(row.get("A_mm"))
    cant    = int(_to_float(row.get("cant")) or 1)
    es_diam = bool(row.get("es_diametro", False))

    syms_raw = row.get("simbolos", [])
    if isinstance(syms_raw, str):
        syms_raw = [s.strip() for s in syms_raw.replace(",", " ").split() if s.strip()]
    simbolos = syms_raw

    mtype    = mat_type(tipo)
    warnings = []
    out      = dict(row)

    # ── valor_unit: per-row override → global lookup → default ────────────────
    valor_unit_raw = _to_float(row.get("valor_unit"))
    if valor_unit_raw is not None and valor_unit_raw > 0:
        valor_unit = valor_unit_raw
    else:
        valor_unit = _lookup_global_price(tipo, calidad, esp_mm, global_prices)

    # ── KG formula (Plancha, Coil) ────────────────────────────────────────────
    if mtype == "formula_kg":
        kn = kg_neto(tipo, L_mm, A_mm, esp_mm, es_diam, calidad)
        if kn is None:
            warnings.append("kg_neto: dimensiones incompletas — ingresar L, A y esp")
            kn = 0.0
        wf, wop, assumed_wf = waste_factor(tipo, simbolos, es_diam)
        if assumed_wf:
            warnings.append(f"waste_factor: operación no identificada → usando {wf} (default)")
        kg_bruto_u = round(kn * wf, 6)
        qty_total  = round(kg_bruto_u * cant, 4)
        unidad     = "KG"
        sku_info   = resolve_sku(tipo, calidad, esp_mm)
        if sku_info["assumed"] and sku_info["sku_erp"] is None:
            warnings.append(f"SKU no encontrado para {tipo}/{calidad}/{esp_mm}mm")
        out.update({
            "mat_type":     mtype,
            "unidad":       unidad,
            "kg_neto":      round(kn, 4),
            "waste_factor": wf,
            "waste_op":     wop,
            "kg_bruto":     round(kg_bruto_u, 4),
            "qty_total":    qty_total,
            "sku_material": sku_info.get("sku_erp") or "",
            "valor_unit":   valor_unit,
            "total_clp":    round(qty_total * valor_unit),
            "warnings":     warnings,
        })

    # ── ML formula (Perfil, Tubo, Macizo) ─────────────────────────────────────
    elif mtype == "formula_ml":
        if L_mm is None:
            warnings.append("L_mm requerido para calcular metros lineales")
            qty_total = 0.0
        else:
            qty_total = round((L_mm / 1000) * cant, 4)
        unidad = "ML"
        out.update({
            "mat_type":     mtype,
            "unidad":       unidad,
            "kg_neto":      None,
            "waste_factor": None,
            "waste_op":     None,
            "kg_bruto":     None,
            "qty_total":    qty_total,
            "sku_material": "",
            "valor_unit":   valor_unit,
            "total_clp":    round(qty_total * valor_unit),
            "warnings":     warnings,
        })

    # ── Manual (Otro / hardware) ───────────────────────────────────────────────
    else:
        if valor_unit_raw is None or valor_unit_raw == 0:
            warnings.append("valor_unit: ingresar precio por unidad")
        out.update({
            "mat_type":     "manual",
            "unidad":       "U",
            "kg_neto":      None,
            "waste_factor": None,
            "waste_op":     None,
            "kg_bruto":     None,
            "qty_total":    cant,
            "sku_material": "",
            "valor_unit":   valor_unit_raw or 0,
            "total_clp":    round(cant * (valor_unit_raw or 0)),
            "warnings":     warnings,
        })

    out["cant"]    = cant
    out["calidad"] = calidad
    return out


def compute_bom(rows: list[dict], global_prices: Optional[dict] = None) -> list[dict]:
    """Compute all rows. Pass global_prices for automatic price lookup."""
    return [compute_part(r, global_prices) for r in rows]


def erp_rows(bom: list[dict]) -> list[dict]:
    """
    Collapse BOM into ERP import rows grouped by sku_material.
    Returns: [{ sku_material, unidad, qty_total, valor_unit, total_clp, partes }]
    """
    from collections import defaultdict
    groups  = defaultdict(lambda: {"qty": 0.0, "clp": 0, "partes": [], "valor_unit": 0, "unidad": ""})
    pending = []

    for r in bom:
        sku   = r.get("sku_material", "")
        qty   = r.get("qty_total", 0.0) or 0.0
        clp   = r.get("total_clp", 0) or 0
        valor = r.get("valor_unit", 0) or 0
        uni   = r.get("unidad", "")
        if not sku:
            pending.append(r.get("parte", "?"))
            continue
        groups[sku]["qty"]        += qty
        groups[sku]["clp"]        += clp
        groups[sku]["valor_unit"]  = valor
        groups[sku]["unidad"]      = uni
        groups[sku]["partes"].append(r.get("parte", ""))

    result = []
    for sku, g in sorted(groups.items()):
        result.append({
            "sku_material": sku,
            "unidad":       g["unidad"],
            "qty_total":    round(g["qty"], 3),
            "valor_unit":   g["valor_unit"],
            "total_clp":    round(g["clp"]),
            "partes":       ", ".join(p for p in g["partes"] if p),
        })

    if pending:
        result.append({
            "sku_material": "PENDIENTE",
            "unidad":       "—",
            "qty_total":    None,
            "valor_unit":   None,
            "total_clp":    None,
            "partes":       ", ".join(pending),
        })

    return result


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _to_float(v) -> Optional[float]:
    if v is None or v == "" or (isinstance(v, float) and math.isnan(v)):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ─── Default global prices (fallback if Supabase unavailable) ─────────────────

DEFAULT_GLOBAL_PRICES = {
    "planchas": {
        "304": {"0.8": 3600, "1.0": 3600, "1.5": 3600, "2.0": 3600, "3.0": 3600, "5.0": 3600, "6.0": 3600},
        "201": {"1.0": 3600, "1.5": 3600},
        "430": {"0.8": 3600, "1.0": 3600},
        "316": {"0.8": 3600, "1.0": 3600, "1.5": 3600},
    },
    "perfil_default":  3800,
    "tubo_default":    4693,
    "macizo_default":  950,
}


# ─── CLI smoke test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from pprint import pprint

    prices = DEFAULT_GLOBAL_PRICES
    test_parts = [
        {"parte": "Manto cilindrado", "tipo": "Plancha",  "calidad": "304", "esp_mm": 0.8,
         "L_mm": 628.3, "A_mm": 400.0, "cant": 1, "simbolos": ["⊙", "T4"]},
        {"parte": "Tapa superior",    "tipo": "Plancha",  "calidad": "304", "esp_mm": 1.5,
         "L_mm": 200.0, "A_mm": 200.0, "cant": 1, "simbolos": [], "es_diametro": True},
        {"parte": "Pata cuadrada",    "tipo": "Perfil",   "calidad": "304", "esp_mm": 1.0,
         "L_mm": 400.0, "cant": 4},
        {"parte": "Tubo estructural", "tipo": "Tubo",     "calidad": "304", "esp_mm": 1.0,
         "L_mm": 600.0, "A_mm": 38.1, "cant": 2},
        {"parte": "Llave de bola 1/2\"", "tipo": "Otro",  "calidad": "",
         "cant": 4, "valor_unit": 1990},
    ]

    bom = compute_bom(test_parts, prices)
    print(f"{'Parte':<25} {'Tipo':<8} {'Unit':<4} {'qty_total':>10} {'valor':>7} {'total':>10}")
    print("-" * 72)
    for r in bom:
        print(f"  {r['parte']:<23} {r['mat_type']:<12} {r['unidad']:<4} "
              f"{str(r['qty_total']):>10}  ${r['valor_unit']:>6,.0f}  ${r['total_clp']:>8,.0f}")
        for w in (r.get("warnings") or []):
            print(f"    ⚠️  {w}")

    print("\nERP rows:")
    for row in erp_rows(bom):
        print(f"  {row}")
