"""
bom_calc.py — Deterministic BOM computation for Dulox pricing system
======================================================================
Converts per-part geometry (tipo, esp_mm, L_mm, A_mm, cant, simbolos) into:
  - kg_neto:      net Kg of finished part from geometry (no waste)
  - waste_factor: from waste_factors.json — determined by tipo + simbolos
  - kg_bruto:     Kg to pull from stock (kg_neto × waste_factor)
  - sku_material: ERP material code from inventory_map.json
  - precio_kg:    price per kg from inventory_map.json
  - total_clp:    kg_bruto × cant × precio_kg

Sheet optimization rule:
  Parts using the same material SKU share sheet consumption.
  For ERP import: GROUP BY sku_material → SUM(kg_bruto × cant).
  The factory optimizes sheet usage internally — the BOM only tracks total Kg.
  Remaining material from a sheet that is not used by another part = waste (already
  accounted in waste_factor). No need to track individual sheet IDs.

Default calidad: AISI 304. Only override when drawing or user explicitly specifies 201/316/430.

Waste factor selection (deterministic from tipo + simbolos — no manual input needed):
  Plancha + ⊙ in simbolos          → cilindrado_manto
  Plancha + A is diameter (es_diam) → corte_plancha_circular
  Plancha (other)                   → corte_plancha_rectangular
  Perfil                            → corte_perfil_tubo
  Tubo                              → corte_perfil_tubo
  Macizo                            → corte_macizo
  Unknown                           → default 1.05, flagged

Density constant: 8 kg/m² per mm espesor = 0.000008 kg/mm³ (all grades).
                  Empirical: 1mm sheet → ×8 kg/m², 2mm → ×16 kg/m². Proportionate for other thicknesses.
                  Validated against MP0001 (1mm) and MP0002 (1.5mm) inventory data.
"""

import json
import math
from pathlib import Path
from typing import Optional

ROOT            = Path(__file__).resolve().parent.parent
INVENTORY_FILE  = ROOT / "data" / "inventory_map.json"
WASTE_FILE      = ROOT / "data" / "waste_factors.json"

# ─── Constants ────────────────────────────────────────────────────────────────

DENSITY_304  = 0.000008     # kg/mm³  (AISI 304 / 316) — empirical: 1mm=×8, 2mm=×16 kg/m²
DENSITY_201  = 0.000008     # kg/mm³  (AISI 201 — same empirical rate as 304)
DENSITY_430  = 0.000008     # kg/mm³  (AISI 430 — same empirical rate as 304)

DEFAULT_CALIDAD       = "304"
DEFAULT_WASTE_FACTOR  = 1.05
DEFAULT_PRECIO_KG     = 3600  # CLP/kg fallback when SKU not found

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

# ─── Density by calidad ───────────────────────────────────────────────────────

def density(calidad: str) -> float:
    c = (calidad or DEFAULT_CALIDAD).strip()
    if c.startswith("201"):
        return DENSITY_201
    if c.startswith("430"):
        return DENSITY_430
    return DENSITY_304   # 304, 316, default

# ─── Kg formula — per tipo ───────────────────────────────────────────────────

def kg_neto(tipo: str, L_mm: Optional[float], A_mm: Optional[float],
            esp_mm: Optional[float], es_diametro: bool = False,
            calidad: str = DEFAULT_CALIDAD) -> Optional[float]:
    """
    Compute net Kg of one unit of a part (before waste).
    Returns None if required dimensions are missing.

    tipo:
      Plancha — L × A × esp × density
      Tubo    — π × Ø_ext × esp × L × density   (A_mm = outer diameter)
      Perfil  — L × kg_por_metro (lookup; returns None if not in inventory)
      Macizo  — not yet implemented (returns None)

    For cylindrical Plancha parts (manto):
      L_mm = unrolled length (= π × D if cut from flat sheet)
      A_mm = height of cylinder
      esp_mm = sheet thickness
      Kg formula is the same as flat Plancha — the unrolling is done by the operator.
      The ⊙ symbol only triggers a different waste_factor, not a different Kg formula.
    """
    t = (tipo or "").strip().lower()
    rho = density(calidad)

    if t == "plancha":
        if L_mm is None or A_mm is None or esp_mm is None:
            return None
        return L_mm * A_mm * esp_mm * rho

    elif t == "tubo":
        # A_mm = outer diameter (Ø), L_mm = length, esp_mm = wall thickness
        if L_mm is None or A_mm is None or esp_mm is None:
            return None
        diam = A_mm  # outer diameter
        return math.pi * diam * esp_mm * L_mm * rho

    elif t == "perfil":
        # Lookup kg_por_metro from inventory_map.json
        # A_mm is used as the section identifier (e.g. "30x30" — passed as string in notas_raw)
        # For now: return None (flag as kg_manual_requerido) until kg_por_metro is populated
        return None

    elif t in ("macizo", "barra"):
        return None  # not yet implemented

    return None


# ─── Waste factor — from tipo + simbolos ─────────────────────────────────────

def waste_factor(tipo: str, simbolos: list, es_diametro: bool = False) -> tuple[float, str, bool]:
    """
    Returns (factor, operation_key, assumed).
    assumed=True means the operation was inferred from defaults — flag in UI.
    """
    ops = _WASTE.get("operaciones", {})
    t = (tipo or "").strip().lower()
    syms = [s.upper() for s in (simbolos or [])]

    if t == "plancha":
        if "⊙" in syms or "CIL" in syms or "CILINDRADO" in syms:
            key = "cilindrado_manto"
        elif es_diametro:
            key = "corte_plancha_circular"
        else:
            key = "corte_plancha_rectangular"
    elif t in ("perfil",):
        key = "corte_perfil_tubo"
    elif t in ("tubo",):
        key = "corte_perfil_tubo"
    elif t in ("macizo", "barra"):
        key = "corte_macizo"
    else:
        return DEFAULT_WASTE_FACTOR, "default", True

    entry  = ops.get(key, {})
    factor = entry.get("factor", DEFAULT_WASTE_FACTOR)
    assumed = key not in ops   # True if key wasn't in file
    return factor, key, assumed


# ─── SKU resolver ─────────────────────────────────────────────────────────────

def resolve_sku(tipo: str, calidad: str = DEFAULT_CALIDAD,
                esp_mm: Optional[float] = None) -> dict:
    """
    Look up material SKU + price from inventory_map.json.
    Returns dict with keys: sku_erp, precio_kg, disponible, assumed.
    assumed=True means we fell back to a default (e.g., calidad not specified → 304).
    """
    t = (tipo or "").strip().lower()
    c = (calidad or DEFAULT_CALIDAD).strip()
    assumed_calidad = not calidad or calidad.strip() == ""
    if assumed_calidad:
        c = DEFAULT_CALIDAD

    result = {
        "sku_erp":        None,
        "precio_kg":      DEFAULT_PRECIO_KG,
        "disponible":     False,
        "assumed_calidad": assumed_calidad,
        "assumed":        True,
    }

    if t == "plancha" and esp_mm is not None:
        key = str(esp_mm).rstrip("0").rstrip(".")   # "1.50" → "1.5", "1.0" → "1"
        # Try with decimal: "1.5" first, then integer "1"
        plancha_lookup = _INVENTORY.get("_plancha_lookup", {})
        entry = plancha_lookup.get(key) or plancha_lookup.get(str(int(esp_mm)) if esp_mm == int(esp_mm) else None)
        if entry:
            result.update({
                "sku_erp":    entry.get("sku_erp"),
                "precio_kg":  entry.get("precio_kg", DEFAULT_PRECIO_KG),
                "disponible": entry.get("disponible", False),
                "assumed":    assumed_calidad or entry.get("sku_erp") is None,
            })
        # If calidad != 304, try to find a specific entry
        if c != "304":
            # No separate lookup table for non-304 yet — flag
            result["assumed"] = True
            result["nota"] = f"Calidad {c} no en lookup — usando precio 304"

    elif t in ("perfil", "tubo", "macizo"):
        # No programmatic lookup yet — flag as manual
        result["nota"] = f"SKU para {tipo} pendiente — ingresar manualmente"

    return result


# ─── Full part computation ────────────────────────────────────────────────────

def compute_part(row: dict) -> dict:
    """
    Given a BOM row dict with raw fields, compute all derived fields.
    Input keys: tipo, calidad, esp_mm, L_mm, A_mm, cant, simbolos (list or str), es_diametro
    Output: same dict + kg_neto, waste_factor, waste_op, kg_bruto, sku_material,
                       precio_kg, total_clp, warnings (list)
    """
    tipo        = row.get("tipo", "Plancha")
    calidad     = row.get("calidad") or DEFAULT_CALIDAD
    esp_mm      = _to_float(row.get("esp_mm"))
    L_mm        = _to_float(row.get("L_mm"))
    A_mm        = _to_float(row.get("A_mm"))
    cant        = int(row.get("cant") or 1)
    es_diam     = bool(row.get("es_diametro", False))

    # Normalise simbolos to list
    syms_raw = row.get("simbolos", [])
    if isinstance(syms_raw, str):
        syms_raw = [s.strip() for s in syms_raw.replace(",", " ").split() if s.strip()]
    simbolos = syms_raw

    warnings = []

    # ── Kg neto ───────────────────────────────────────────────────────────────
    kn = kg_neto(tipo, L_mm, A_mm, esp_mm, es_diam, calidad)
    if kn is None:
        warnings.append("kg_neto: dimensiones incompletas — ingresar manualmente")
        kn = 0.0

    # ── Waste factor ──────────────────────────────────────────────────────────
    wf, wop, assumed_wf = waste_factor(tipo, simbolos, es_diam)
    if assumed_wf:
        warnings.append(f"waste_factor: operación no identificada → usando {wf} (default)")

    kg_bruto_unit = round(kn * wf, 6)
    kg_bruto_total = round(kg_bruto_unit * cant, 4)

    # ── SKU + price ───────────────────────────────────────────────────────────
    sku_info = resolve_sku(tipo, calidad, esp_mm)
    if sku_info.get("assumed"):
        if sku_info.get("nota"):
            warnings.append(sku_info["nota"])
        elif sku_info["sku_erp"] is None:
            warnings.append(f"sku_material: no encontrado para {tipo}/{calidad}/{esp_mm}mm — verificar")

    precio = sku_info["precio_kg"]
    total  = round(kg_bruto_total * precio)

    out = dict(row)
    out.update({
        "calidad":       calidad,
        "cant":          cant,
        "kg_neto":       round(kn, 4),
        "waste_factor":  wf,
        "waste_op":      wop,
        "kg_bruto":      round(kg_bruto_unit, 4),
        "sku_material":  sku_info.get("sku_erp") or "",
        "precio_kg":     precio,
        "total_clp":     total,
        "warnings":      warnings,
    })
    return out


def compute_bom(rows: list[dict]) -> list[dict]:
    """Compute all rows and return with derived fields."""
    return [compute_part(r) for r in rows]


def erp_rows(bom: list[dict]) -> list[dict]:
    """
    Collapse BOM into ERP import rows: one row per material SKU.
    Returns: [{ sku_material, descripcion, total_kg_bruto, precio_kg, total_clp }]

    Sheet optimization rule applied here: parts sharing the same sku_material
    are assumed to share sheet usage (factory optimizes internally).
    Total Kg is the sum — ERP gets one line per material, not one line per part.
    """
    from collections import defaultdict
    groups = defaultdict(lambda: {"kg": 0.0, "clp": 0, "partes": [], "precio_kg": 0})
    unknown = []

    for r in bom:
        sku = r.get("sku_material", "")
        kg  = r.get("kg_bruto", 0.0) * int(r.get("cant", 1))
        clp = r.get("total_clp", 0)
        precio = r.get("precio_kg", 0)
        if not sku:
            unknown.append(r.get("parte", "?"))
            continue
        groups[sku]["kg"]  += kg
        groups[sku]["clp"] += clp
        groups[sku]["precio_kg"] = precio   # same for all rows of same SKU
        groups[sku]["partes"].append(r.get("parte", ""))

    result = []
    for sku, g in sorted(groups.items()):
        result.append({
            "sku_material":   sku,
            "total_kg_bruto": round(g["kg"], 3),
            "precio_kg":      g["precio_kg"],
            "total_clp":      round(g["clp"]),
            "partes":         ", ".join(p for p in g["partes"] if p),
        })

    if unknown:
        result.append({
            "sku_material":   "PENDIENTE",
            "total_kg_bruto": None,
            "precio_kg":      None,
            "total_clp":      None,
            "partes":         ", ".join(unknown),
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


# ─── CLI smoke test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_parts = [
        {"parte": "Manto cilindrado", "tipo": "Plancha", "calidad": "304", "esp_mm": 0.8,
         "L_mm": 628.3, "A_mm": 400.0, "cant": 1, "simbolos": ["⊙", "T4"]},
        {"parte": "Tapa superior",    "tipo": "Plancha", "calidad": "304", "esp_mm": 1.5,
         "L_mm": 200.0, "A_mm": 200.0, "cant": 1, "simbolos": [], "es_diametro": True},
        {"parte": "Patas",            "tipo": "Perfil",  "calidad": "304", "esp_mm": 1.5,
         "L_mm": 400.0, "A_mm": None,  "cant": 4, "simbolos": []},
    ]

    bom = compute_bom(test_parts)
    for r in bom:
        print(f"  {r['parte']:25s} kg_neto={r['kg_neto']:7.4f}  "
              f"× waste {r['waste_factor']}  = {r['kg_bruto']:7.4f} kg/u  "
              f"× {r['cant']} u  = {r['kg_bruto']*r['cant']:.4f} kg  "
              f"SKU={r['sku_material']:8s}  "
              f"${r['total_clp']:>8,.0f} CLP")
        for w in r["warnings"]:
            print(f"    ⚠️  {w}")

    print("\nERP rows:")
    for row in erp_rows(bom):
        print(f"  {row}")
