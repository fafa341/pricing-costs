"""
import_boms.py — Parse measurements-p2.md and push BOMs to Supabase.

Usage:
    python scripts/import_boms.py [--overwrite]

By default only writes products that have no bom_materials saved yet.
Pass --overwrite to replace existing BOMs.

Handle matching: the short codes in measurements-p2 (e.g. BAPLA-0470) are
matched against DB handles that contain the lowercased code as a substring.
If multiple DB handles match, the most specific one is chosen (shortest slug
that still contains the code).
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEASUREMENTS_PATH = ROOT / "docs" / "calibration" / "process-measurements" / "measurements-p2.md"


def _price(s: str) -> float:
    if not s:
        return 0.0
    try:
        return float(re.sub(r"[$,\s]", "", s.strip()))
    except ValueError:
        return 0.0


def parse_measurements() -> list[dict]:
    text = MEASUREMENTS_PATH.read_text(encoding="utf-8")
    results = []
    for section in re.split(r"\n(?=# )", text):
        header = re.match(r"# ([A-Z][A-Z0-9\-]*)(\s+[^\n]*)?", section)
        if not header:
            continue
        # Extract the product code: first word of the header (all caps + digits + dashes)
        first_token = header.group(1).strip()
        rest        = (header.group(2) or "").strip()
        # name comes after "|" if present, else from rest
        if "|" in rest:
            name = rest.split("|", 1)[1].strip()
        else:
            name = rest.strip()
        handle_raw = first_token
        handle_key = handle_raw.lower()   # used for DB lookup

        # dimensions
        dims: dict = {}
        dm = re.search(r"## Dimensions\s*\n[^\n]*\n([^\n]*)", section)
        if dm:
            for label, val in zip(["L_mm", "W_mm", "H_mm"], dm.group(1).split(",")[:3]):
                try:
                    v = float(re.sub(r"[^0-9.]", "", val.strip()))
                    if v:
                        dims[label] = v
                except ValueError:
                    pass

        # materials
        mat_rows: list = []
        mm = re.search(r"## Material cost breakdown\s*\n(.*?)(?=##|\Z)", section, re.DOTALL)
        if mm:
            for line in mm.group(1).splitlines():
                if not line.startswith("|") or "---" in line or "Material" in line:
                    continue
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) < 7 or not cells[0] or cells[0].startswith("---"):
                    continue
                kg_ml = _price(cells[4])
                total = _price(cells[6])
                if not total and not kg_ml:
                    continue
                mat_rows.append({
                    "Subconjunto": "", "Dimensiones": cells[1],
                    "Material": cells[0], "Cantidad": 1.0,
                    "kg_ml": kg_ml, "precio_kg": _price(cells[2]),
                    "total": int(total),
                })

        # consumables
        cons_rows: list = []
        cm = re.search(r"## Consumables.*?\n(.*?)(?=\n---|\Z)", section, re.DOTALL)
        if cm:
            for line in cm.group(1).splitlines():
                if not line.startswith("|") or "---" in line or "Producto" in line:
                    continue
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) < 7 or not cells[0] or not cells[1]:
                    continue
                try:
                    cant = float(cells[2].replace(",", "."))
                except ValueError:
                    cant = 0.0
                total_c = _price(cells[6])
                cons_rows.append({
                    "Producto": cells[0], "Proceso": cells[1],
                    "Cantidad": cant, "Unidad": cells[3],
                    "Precio_u": int(_price(cells[4])), "Total": int(total_c),
                })

        if mat_rows or cons_rows:
            results.append({
                "handle_key": handle_key,
                "handle_raw": handle_raw,
                "name": name,
                "dims": dims,
                "mat_rows": mat_rows,
                "cons_rows": cons_rows,
            })
    return results


# Manual overrides for codes where the file format differs from the DB slug
MANUAL_MAP = {
    "sumve-400":  "sumidero-con-tapa-perforada-400-sumve-0400",
    "sumho-200":  "sumidero-con-rejilla-sumho-0200",
    "bacon-410":  "basurero-conico-bacon-0410",
    "batp-300":   "basurero-tapa-pedal-rectangular-batp-0300",
    "cel-0500":   "celosia-500x200mm-cell-0500",
    "tost-01":    "tostador-de-pan",
}


def resolve_handle(handle_key: str, all_db_handles: list[str]) -> str | None:
    """
    Find the DB handle that best matches the short product code.
    1. Check MANUAL_MAP first.
    2. Exact substring match.
    3. Strip leading zeros from numeric suffix and retry.
       e.g. 'sumho-200' → also try 'sumho-0200' (DB zero-pads numbers).
    """
    if handle_key in MANUAL_MAP:
        return MANUAL_MAP[handle_key]

    candidates = [h for h in all_db_handles if handle_key in h]
    if candidates:
        return min(candidates, key=len)

    # Try zero-padding the numeric suffix: 'bacon-410' → 'bacon-0410'
    m = re.match(r"^([a-z][a-z0-9]*-)(\d+)$", handle_key)
    if m:
        padded = f"{m.group(1)}{int(m.group(2)):04d}"
        candidates = [h for h in all_db_handles if padded in h]
        if candidates:
            return min(candidates, key=len)

    return None


def get_client():
    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase-py not installed.")
        sys.exit(1)
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE", "")
    if not url or not key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE env vars.")
        sys.exit(1)
    return create_client(url, key)


def main():
    overwrite = "--overwrite" in sys.argv

    print(f"Parsing {MEASUREMENTS_PATH.name} ...")
    parsed = parse_measurements()
    print(f"Found {len(parsed)} products with BOM data.\n")

    sb = get_client()
    rows = sb.table("products").select("handle,bom_materials,dim_l_mm,dim_w_mm,dim_h_mm").execute().data
    all_db_handles = [r["handle"] for r in rows]
    db_map = {r["handle"]: r for r in rows}

    imported, skipped, not_found = 0, 0, []

    for p in parsed:
        db_handle = resolve_handle(p["handle_key"], all_db_handles)

        if not db_handle:
            not_found.append(p["handle_raw"])
            continue

        existing_bom = db_map[db_handle].get("bom_materials") or "[]"
        has_bom = existing_bom not in ["[]", "", None]

        if has_bom and not overwrite:
            print(f"  SKIP  {p['handle_raw']:20s} → {db_handle} (BOM exists)")
            skipped += 1
            continue

        payload = {
            "bom_materials":   json.dumps(p["mat_rows"],   ensure_ascii=False),
            "bom_consumables": json.dumps(p["cons_rows"],  ensure_ascii=False),
        }
        db_row = db_map[db_handle]
        if p["dims"].get("L_mm") and not db_row.get("dim_l_mm"):
            payload["dim_l_mm"] = p["dims"]["L_mm"]
        if p["dims"].get("W_mm") and not db_row.get("dim_w_mm"):
            payload["dim_w_mm"] = p["dims"]["W_mm"]
        if p["dims"].get("H_mm") and not db_row.get("dim_h_mm"):
            payload["dim_h_mm"] = p["dims"]["H_mm"]

        sb.table("products").update(payload).eq("handle", db_handle).execute()
        mat_total  = sum(r["total"] for r in p["mat_rows"])
        cons_total = sum(r["Total"] for r in p["cons_rows"])
        print(f"  OK    {p['handle_raw']:20s} → {db_handle}")
        print(f"         mat={len(p['mat_rows'])} rows  ${mat_total:>10,}  |  cons={len(p['cons_rows'])} rows  ${cons_total:>8,}")
        imported += 1

    print(f"\n{'='*60}")
    print(f"Imported:  {imported}")
    print(f"Skipped:   {skipped} (already had BOM — use --overwrite to replace)")
    if not_found:
        print(f"No match:  {len(not_found)}")
        for h in not_found:
            print(f"           {h}  (no DB handle contains '{h.lower()}')")


if __name__ == "__main__":
    main()
