"""
migrate_bom.py — Migrate bom_materials from old schema to new schema in Supabase.

Old schema per row:
    Subconjunto, Dimensiones, Material, Cantidad, kg_ml, precio_kg, total

New schema per row:
    parte, tipo, calidad, esp_mm, L_mm, A_mm, cant, simbolos

Parsing rules:
    Dimensiones → L_mm + A_mm + cant override
    Material    → tipo + calidad + esp_mm

Run:
    python3 pipeline/migrate_bom.py            # dry-run, shows plan
    python3 pipeline/migrate_bom.py --apply    # writes to Supabase

Rows that cannot be parsed are flagged with needs_review=True and kept
with whatever could be extracted — no data is silently discarded.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

# ─── Supabase client (no Streamlit dependency here) ──────────────────────────

def _get_sb():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE", "")
    if not url or not key:
        secrets_path = ROOT / ".streamlit" / "secrets.toml"
        if secrets_path.exists():
            for line in secrets_path.read_text().splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip().strip('"')
                    if k == "SUPABASE_URL":
                        url = v
                    if k == "SUPABASE_SERVICE_ROLE":
                        key = v
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE not found")
    from supabase import create_client
    return create_client(url, key)


# ─── Dimension parser ─────────────────────────────────────────────────────────

def _parse_dimensiones(dim: str) -> dict:
    """
    Returns: {L_mm, A_mm, cant_override, es_diametro, simbolos, _dim_raw, _dim_note}
    cant_override is only set when the dimension string encodes a quantity (e.g. "(4)").
    """
    out = {
        "L_mm": None, "A_mm": None, "cant_override": None,
        "es_diametro": False, "simbolos": "",
        "_dim_raw": dim, "_dim_note": "",
    }
    if not dim or not dim.strip():
        return out

    s = dim.strip()

    # Extract trailing quantity in these forms ONLY:
    #   (4)  (x4)  (x 4)   — parenthesised
    #   x2   x4            — x directly adjacent to digit (no space), e.g. "80 x 735 mm x2"
    # NOT matched: " x 900" (space between x and digit = dimensional separator, not quantity)
    cant_m = re.search(r'(?:\(([xX]?\s*\d+)\)|[xX](\d+))\s*$', s)
    if cant_m:
        raw = cant_m.group(1) or cant_m.group(2)
        out["cant_override"] = int(re.search(r'\d+', raw).group())
        s = s[:cant_m.start()].strip().rstrip("(").strip()

    # Pure unit strings: "1 u", "2 u", "8 u", or bare integers
    if re.fullmatch(r'\d+\s*u?', s):
        out["cant_override"] = int(re.search(r'\d+', s).group())
        out["_dim_note"] = "unit-count-only"
        return out

    # Circular: "ø NNN mm", "ø NNN ext x ø NNN int x NNN mm" (ring/annular shape)
    if "ø" in s or s.lower().startswith("o "):
        out["es_diametro"] = True
        out["simbolos"] = "⊙"
        # Annular: ø 337 ext x ø 287 int x 25 mm  →  L_mm=25 (height), A_mm=337 (outer Ø)
        ann = re.search(r'ø\s*([\d.,]+)\s*ext.*?ø\s*([\d.,]+)\s*int.*?([\d.,]+)\s*mm', s, re.IGNORECASE)
        if ann:
            out["A_mm"] = _f(ann.group(1))   # outer diameter
            out["L_mm"] = _f(ann.group(3))   # height
            out["_dim_note"] = "annular-ring"
            return out
        # Simple circle: ø NNN mm
        circ = re.search(r'ø\s*([\d.,]+)', s)
        if circ:
            out["A_mm"] = _f(circ.group(1))  # A_mm = diameter
            out["_dim_note"] = "circular"
        return out

    # Tube diameter in dimensiones: "1200 x ø 3/4""
    if "ø" in s or "/" in s:
        # treat as linear, leave A_mm None, flag
        lin = re.search(r'([\d.,]+)\s*(?:x|X)', s)
        if lin:
            out["L_mm"] = _f(lin.group(1))
        out["_dim_note"] = "tube-or-pipe-dim, A_mm manual"
        return out

    # Normalise separators: "120x1305mm" → "120 x 1305 mm"
    s_norm = re.sub(r'(?<=[0-9])x(?=[0-9])', ' x ', s, flags=re.IGNORECASE)

    # Two-dimension: NNN x NNN [mm]  (with optional spaces / case)
    two = re.search(
        r'([\d.,]+)\s*(?:x|X)\s*([\d.,]+)',
        s_norm
    )
    if two:
        out["L_mm"] = _f(two.group(1))
        out["A_mm"] = _f(two.group(2))
        return out

    # Single dimension: NNN mm  or  just NNN
    single = re.search(r'([\d.,]+)', s_norm)
    if single:
        out["L_mm"] = _f(single.group(1))
        out["_dim_note"] = "single-dim, A_mm manual"
        return out

    out["_dim_note"] = "unparseable"
    return out


def _f(s: str) -> float | None:
    """Parse float from string, handling comma decimals."""
    try:
        return float(str(s).replace(",", "."))
    except (ValueError, TypeError):
        return None


# ─── Material parser ──────────────────────────────────────────────────────────

def _parse_material(mat: str) -> dict:
    """
    Returns: {tipo, calidad, esp_mm, _mat_note}
    """
    out = {"tipo": "Plancha", "calidad": "304", "esp_mm": None, "_mat_note": ""}
    if not mat or not mat.strip():
        out["_mat_note"] = "empty"
        return out

    s = mat.strip()

    # AISI 304-L / AISI 304 / AISI 201 etc.
    aisi_m = re.match(
        r'AISI\s+(\d+)(?:-L)?\s+([\d.,]+)\s*mm',
        s, re.IGNORECASE
    )
    if aisi_m:
        out["tipo"] = "Plancha"
        out["calidad"] = aisi_m.group(1)   # "304", "201", etc.
        out["esp_mm"] = _f(aisi_m.group(2))
        return out

    # Acero 430 Nmm
    a430 = re.match(r'Acero\s+430\s+([\d.,]+)\s*mm', s, re.IGNORECASE)
    if a430:
        out["tipo"] = "Plancha"
        out["calidad"] = "430"
        out["esp_mm"] = _f(a430.group(1))
        return out

    # Perfil NNxNN[xN] mm
    if re.match(r'Perfil', s, re.IGNORECASE):
        out["tipo"] = "Perfil"
        out["calidad"] = "304"
        esp = re.search(r'(\d+)\s*mm', s)
        if esp:
            out["esp_mm"] = float(esp.group(1))
        out["_mat_note"] = "perfil — verify section"
        return out

    # Tubo
    if re.match(r'Tubo', s, re.IGNORECASE):
        out["tipo"] = "Tubo"
        out["calidad"] = "304"
        esp = re.search(r'([\d.,]+)\s*mm', s)
        if esp:
            out["esp_mm"] = _f(esp.group(1))
        out["_mat_note"] = "tubo — verify diameter"
        return out

    # Macizo / Maciso
    if re.match(r'Maci[sz]o', s, re.IGNORECASE):
        out["tipo"] = "Macizo"
        out["calidad"] = "304"
        out["_mat_note"] = "macizo — verify section"
        return out

    # Acero Inoxidable / Acero Galvanizado (no thickness given)
    if re.match(r'Acero', s, re.IGNORECASE):
        out["tipo"] = "Plancha"
        out["_mat_note"] = "generic steel, esp_mm manual"
        return out

    # Everything else: hardware, components
    out["tipo"] = "Otro"
    out["calidad"] = ""
    out["_mat_note"] = "hardware/component"
    return out


# ─── Row migration ────────────────────────────────────────────────────────────

def migrate_row(old: dict) -> dict:
    """Convert a single old-schema row to new schema."""
    dim_data  = _parse_dimensiones(str(old.get("Dimensiones") or ""))
    mat_data  = _parse_material(str(old.get("Material") or ""))

    parte = str(old.get("Subconjunto") or "").strip()
    if not parte:
        # derive name from material + dimensions
        parte = str(old.get("Material") or "").strip() or "Pieza"

    # Quantity: Dimensiones can encode a multiplier; Cantidad is the BOM quantity
    cant_dim  = dim_data.pop("cant_override")
    cant_bom  = old.get("Cantidad") or old.get("cant") or 1
    try:
        cant_bom = int(float(cant_bom))
    except (ValueError, TypeError):
        cant_bom = 1
    cant = cant_dim if cant_dim is not None else cant_bom

    # Collect flags for review
    notes = [v for v in [dim_data.pop("_dim_note"), mat_data.pop("_mat_note")] if v]
    needs_review = any([
        mat_data["tipo"] in ("Otro", ""),
        mat_data["esp_mm"] is None and mat_data["tipo"] in ("Plancha",),
        dim_data["L_mm"] is None,
        "manual" in " ".join(notes),
        "unparseable" in " ".join(notes),
    ])

    row = {
        "parte":    parte,
        "tipo":     mat_data["tipo"],
        "calidad":  mat_data["calidad"],
        "esp_mm":   mat_data["esp_mm"],
        "L_mm":     dim_data["L_mm"],
        "A_mm":     dim_data["A_mm"],
        "cant":     cant,
        "simbolos": dim_data["simbolos"],
        "es_diametro": dim_data["es_diametro"],
    }
    if needs_review:
        row["needs_review"] = True
        if notes:
            row["_notes"] = "; ".join(notes)
    # Keep raw values for traceability
    row["_old_material"]   = str(old.get("Material") or "")
    row["_old_dimensiones"] = str(old.get("Dimensiones") or "")

    return row


def migrate_bom(rows: list[dict]) -> list[dict]:
    return [migrate_row(r) for r in rows]


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    apply = "--apply" in sys.argv
    sb = _get_sb()

    r = sb.table("products").select("handle, bom_materials").execute()
    products = [
        x for x in r.data
        if x.get("bom_materials") and x["bom_materials"] not in ("null", "[]", "", None)
    ]

    print(f"Products with BOM data: {len(products)}")
    print(f"Mode: {'APPLY (writing to Supabase)' if apply else 'DRY RUN (no writes)'}")
    print()

    total_rows = 0
    needs_review = 0

    for prod in products:
        handle = prod["handle"]
        mats = prod["bom_materials"]
        if isinstance(mats, str):
            mats = json.loads(mats)
        if not isinstance(mats, list):
            continue

        # Skip if already migrated (new schema has 'parte' key)
        if mats and "parte" in mats[0]:
            print(f"  SKIP (already new schema): {handle}")
            continue

        migrated = migrate_bom(mats)
        review_count = sum(1 for r in migrated if r.get("needs_review"))
        total_rows += len(migrated)
        needs_review += review_count

        print(f"  {handle}")
        for i, (old_r, new_r) in enumerate(zip(mats, migrated)):
            flag = "⚠️ " if new_r.get("needs_review") else "✅ "
            dim_str = f"L={new_r['L_mm']} A={new_r['A_mm']}"
            note = f"  [{new_r.get('_notes','')}]" if new_r.get('_notes') else ""
            print(f"    {flag} [{i}] {old_r.get('Dimensiones',''):20s} | {old_r.get('Material',''):30s}"
                  f"  →  {new_r['tipo']:8s} {new_r['calidad']:4s} esp={new_r['esp_mm']} "
                  f"{dim_str} cant={new_r['cant']}{note}")

        if apply:
            # Strip internal tracing keys before saving
            clean = []
            for row in migrated:
                r2 = {k: v for k, v in row.items() if not k.startswith("_")}
                clean.append(r2)
            sb.table("products").update({
                "bom_materials": json.dumps(clean, ensure_ascii=False)
            }).eq("handle", handle).execute()
            print(f"    → written to Supabase")

        print()

    print(f"Summary: {total_rows} rows across {len(products)} products")
    print(f"  ✅ Auto-migrated:  {total_rows - needs_review}")
    print(f"  ⚠️  Needs review:   {needs_review}")
    if not apply:
        print()
        print("Run with --apply to write changes to Supabase.")


if __name__ == "__main__":
    main()
