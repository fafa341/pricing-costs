"""
extract_dimensions.py
---------------------
Extract L, W, H, diameter, espesor from descripcion_web in catalogo-maestro.csv.
Outputs: dataset/dimensions-extracted.csv

Extraction strategy — ordered by specificity (first match wins per dimension group):

  3D patterns (L × W × H):
    P1  "900 X 600 X 860MM"            — compact units-at-end
    P2  "DE 900MM DE LARGO X 600MM ... ANCHO X 860MM ... ALTURA"  — verbose Spanish
    P3  "900MM LARGO X 600MM ANCHO X 860MM ALTURA"  — suffix style

  Diameter patterns:
    P4  "400MM DIÁMETRO X 800MM ALTURA"   — compact
    P5  "400 MM DE DIÁMETRO (MAYOR)"      — verbose
    P6  "POR 800MM DE ALTO"               — paired with P5 for height

  1D fallbacks:
    P7  "1900MM DE LARGO"  /  "LARGO TOTAL DE 800MM"
    P8  "1000MM DE ALTURA" /  "DE ALTURA"

  Espesor (independent, always extracted separately):
    P9  "1MM ESPESOR", "EN 1 MM DE ESPESOR", "ESPESOR DE 1MM", "1,5MM"

  Variable / ambiguous markers:
    P10 "600/740MM" or "30 A 80 MM" → flag as VARIABLE, set dim_confidence = low

Output columns added to every row:
  dim_l_mm         — length (primary dimension, mm)
  dim_w_mm         — width / depth (mm)
  dim_h_mm         — height (mm)
  dim_diameter_mm  — diameter for cylindrical products (mm)
  dim_espesor_mm   — sheet thickness (mm)
  dim_pattern      — which pattern produced the primary dimension group
  dim_confidence   — high / medium / low / none
  dim_notes        — free-text flag for edge cases
"""

import csv
import re
import sys
from pathlib import Path

# ── helpers ──────────────────────────────────────────────────────────────────

def parse_num(s: str) -> float | None:
    """'1.5' or '1,5' or '1' → float"""
    if s is None:
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


NUM = r"(\d+(?:[.,]\d+)?)"   # capture group: a number
SP  = r"\s*"                  # optional whitespace
OPT = lambda s: f"(?:{s})?"  # make a fragment optional

# ── compiled patterns (order matters: most specific first) ────────────────────

# P1: 900 X 600 X 860MM  (units only at end, X as separator)
P1 = re.compile(
    rf"{NUM}{SP}[Xx×]{SP}{NUM}{SP}[Xx×]{SP}{NUM}{SP}MM\b",
    re.IGNORECASE,
)

# P2: DE 900 MM DE LARGO X 600 MM DE ANCHO X 860 MM DE ALTURA
P2 = re.compile(
    rf"(?:DE\s+)?{NUM}\s*MM\s*(?:DE\s+)?LARGO\s+X\s+{NUM}\s*MM\s*(?:DE\s+)?(?:ANCHO|FONDO)\s+X\s+{NUM}\s*MM",
    re.IGNORECASE,
)

# P3: 900MM LARGO X 600MM ANCHO X 860MM ALTURA (no DE)
P3 = re.compile(
    rf"{NUM}\s*MM\s+(?:DE\s+)?LARGO\s+X\s+{NUM}\s*MM\s+(?:DE\s+)?(?:ANCHO|FONDO)\s+X\s+{NUM}\s*MM",
    re.IGNORECASE,
)

# P4: 400MM DIÁMETRO X/POR 800MM [DE] ALTURA  (or DIÁMETRO POR NNNMM DE ALTO)
P4 = re.compile(
    rf"(?:"
    rf"{NUM}\s*MM\s+(?:DE\s+)?DIÁMETRO\s+(?:X|POR)\s+{NUM}\s*MM"
    rf"|{NUM}\s*MM\s+(?:DE\s+)?DIÁMETRO\s+(?:X|POR)\s+{NUM}\s*MM\s+(?:DE\s+)?ALT(?:O|URA)"
    rf")",
    re.IGNORECASE,
)

# P4b: DE NNNMM DE DIAMETRO X/POR NNNMM DE ALTO  (verbose Spanish cylindrical)
P4b = re.compile(
    rf"(?:DE\s+)?{NUM}\s*MM\s+(?:DE\s+)?DIAMETRO\s+(?:X|POR)\s+{NUM}\s*MM\s+(?:DE\s+)?ALT(?:O|URA)",
    re.IGNORECASE,
)

# P5: DIÁMETRO [MAYOR] [/] [MENOR] 400MM  (standalone diameter declaration)
P5 = re.compile(
    rf"DIÁMETRO\s+(?:MAYOR\s*/\s*)?{NUM}\s*MM",
    re.IGNORECASE,
)

# P6: POR 800MM DE ALTO / DE ALTURA  (height companion to P5)
P6 = re.compile(
    rf"(?:X|POR)\s+{NUM}\s*MM\s*(?:DE\s+)?ALT(?:O|URA)",
    re.IGNORECASE,
)

# P7a: NNNN MM DE LARGO  |  LARGO [TOTAL] DE NNNN MM
P7a = re.compile(
    rf"(?:{NUM}\s*MM?\s+(?:DE\s+)?LARGO\b|LARGO\s+(?:TOTAL\s+)?(?:DE\s+)?{NUM}\s*MM?)",
    re.IGNORECASE,
)

# P7b: NNNN MM DE ALTURA / DE ALTO
P7b = re.compile(
    rf"{NUM}\s*MM\s+(?:DE\s+)?ALT(?:O|URA)\b",
    re.IGNORECASE,
)

# P8: Variable marker — slash or "A" between two numbers: 600/740MM  or  30 A 80 MM
P8_VAR = re.compile(
    rf"{NUM}\s*/\s*{NUM}\s*MM|{NUM}\s+A\s+{NUM}\s+MM",
    re.IGNORECASE,
)

# ESPESOR patterns (independent)
P_ESP = re.compile(
    rf"(?:"
    rf"EN\s+{NUM}\s*MM\s+(?:DE\s+)?ESPESOR"
    rf"|{NUM}\s*MM?\s+(?:DE\s+)?ESPESOR"
    rf"|ESPESOR\s+(?:DE\s+)?{NUM}"
    rf"|EN\s+{NUM}\s*MM?\b(?!\s*(?:DE\s+)?(?:LARGO|ANCHO|ALTO|ALTURA|FONDO|DIÁMETRO))"
    rf")",
    re.IGNORECASE,
)


# ── per-row extraction ────────────────────────────────────────────────────────

def extract(desc: str) -> dict:
    result = dict(
        dim_l_mm=None, dim_w_mm=None, dim_h_mm=None,
        dim_diameter_mm=None, dim_espesor_mm=None,
        dim_pattern=None, dim_confidence="none", dim_notes="",
    )

    if not desc:
        return result

    # --- variable-range flag (check early, does not block other extraction) ---
    if P8_VAR.search(desc):
        result["dim_notes"] = "variable-range"
        result["dim_confidence"] = "low"

    # --- espesor (always independent) ---
    for m in P_ESP.finditer(desc):
        raw = next((g for g in m.groups() if g is not None), None)
        val = parse_num(raw)
        if val and 0.3 <= val <= 10:   # sanity: 0.3–10 mm plausible for sheet metal
            result["dim_espesor_mm"] = val
            break

    # --- 3D dimension groups ---
    m = P1.search(desc)
    if m:
        result.update(dim_l_mm=parse_num(m.group(1)),
                      dim_w_mm=parse_num(m.group(2)),
                      dim_h_mm=parse_num(m.group(3)),
                      dim_pattern="P1_compact",
                      dim_confidence="high")
        return result

    m = P2.search(desc)
    if m:
        result.update(dim_l_mm=parse_num(m.group(1)),
                      dim_w_mm=parse_num(m.group(2)),
                      dim_h_mm=parse_num(m.group(3)),
                      dim_pattern="P2_verbose",
                      dim_confidence="high")
        return result

    m = P3.search(desc)
    if m:
        result.update(dim_l_mm=parse_num(m.group(1)),
                      dim_w_mm=parse_num(m.group(2)),
                      dim_h_mm=parse_num(m.group(3)),
                      dim_pattern="P3_suffix",
                      dim_confidence="high")
        return result

    # --- diameter group ---
    m4b = P4b.search(desc)
    if m4b:
        result.update(dim_diameter_mm=parse_num(m4b.group(1)),
                      dim_h_mm=parse_num(m4b.group(2)),
                      dim_pattern="P4b_diameter_verbose",
                      dim_confidence="high")
        return result

    m4 = P4.search(desc)
    if m4:
        # P4 has 4 groups due to alternation; take first two non-None
        grps = [g for g in m4.groups() if g is not None]
        result.update(dim_diameter_mm=parse_num(grps[0]) if grps else None,
                      dim_h_mm=parse_num(grps[1]) if len(grps) > 1 else None,
                      dim_pattern="P4_diameter_compact",
                      dim_confidence="high")
        return result

    m5 = P5.search(desc)
    if m5:
        result["dim_diameter_mm"] = parse_num(m5.group(1))
        result["dim_pattern"] = "P5_diameter_verbose"
        result["dim_confidence"] = "medium"
        m6 = P6.search(desc)
        if m6:
            result["dim_h_mm"] = parse_num(m6.group(1))
            result["dim_confidence"] = "high"
        return result

    # --- 1D fallbacks ---
    m7a = P7a.search(desc)
    if m7a:
        raw = m7a.group(1) or m7a.group(2)
        val = parse_num(raw)
        if val and val > 50:  # sanity: > 50mm = plausible product dimension
            result["dim_l_mm"] = val
            result["dim_pattern"] = "P7a_largo_only"
            result["dim_confidence"] = "medium"
            m7b = P7b.search(desc)
            if m7b:
                result["dim_h_mm"] = parse_num(m7b.group(1))
            return result

    # --- truly unextractable ---
    if result["dim_notes"] == "":
        # classify why
        if any(kw in desc.upper() for kw in ["LLAVE", "GRIFO", "MANGUERA", "CAÑO", "ROSCA", "CARTUCHO"]):
            result["dim_notes"] = "griferia-no-dims"
        elif any(kw in desc.upper() for kw in ["EXPERTOS EN ACERO", "CONFÍE EN NOSOTROS"]):
            result["dim_notes"] = "marketing-placeholder"
        elif any(kw in desc.upper() for kw in ["DIVERSAS GEOMÉTRICAS", "SEGÚN PEDIDO", "SEGÚN MEDIDA"]):
            result["dim_notes"] = "custom-on-demand"
        else:
            result["dim_notes"] = "no-dim-found"

    return result


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    repo = Path(__file__).parent.parent
    infile  = repo / "dataset" / "Sheet1-enriched.csv"
    outfile = repo / "dataset" / "dimensions-extracted.csv"

    with open(infile, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames + [
            "dim_l_mm", "dim_w_mm", "dim_h_mm",
            "dim_diameter_mm", "dim_espesor_mm",
            "dim_pattern", "dim_confidence", "dim_notes",
        ]
        rows = list(reader)

    out_rows = []
    stats = {"high": 0, "medium": 0, "low": 0, "none": 0}
    pattern_counts = {}

    for row in rows:
        ext = extract(row.get("descripcion_web", ""))
        out_row = dict(row) | ext
        out_rows.append(out_row)
        conf = ext["dim_confidence"]
        stats[conf] = stats.get(conf, 0) + 1
        pat = ext["dim_pattern"] or "none"
        pattern_counts[pat] = pattern_counts.get(pat, 0) + 1

    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    total = len(out_rows)
    usable = stats["high"] + stats["medium"]
    print(f"Input : {total} rows")
    print(f"Output: {outfile}")
    print()
    print("Confidence breakdown:")
    for k in ["high", "medium", "low", "none"]:
        pct = stats[k] / total * 100
        print(f"  {k:8s}  {stats[k]:4d}  ({pct:.0f}%)")
    print(f"  {'usable':8s}  {usable:4d}  ({usable/total*100:.0f}%)")
    print()
    print("By pattern:")
    for pat, n in sorted(pattern_counts.items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {pat}")

    # print sample failures by note type
    from collections import Counter
    note_counts = Counter(r["dim_notes"] for r in out_rows if r["dim_notes"])
    if note_counts:
        print()
        print("Failure notes:")
        for note, n in note_counts.most_common():
            print(f"  {n:4d}  {note}")


if __name__ == "__main__":
    main()
