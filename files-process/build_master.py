"""
build_master.py
---------------
Merge Sheet1-enriched.csv (ecommerce, URLs, descriptions, dimensions)
with Productos-Categorizados2.csv (bodega, authoritative IMPORTADO flag,
granular sub-familia) and dimensions-extracted.csv (dim_l_mm, etc.).

Join logic:
  - Primary: P2.CÓDIGO appears as substring of S1.Product:Handle (67% hit rate)
  - Fallback: S1.subfamilia used directly when no code match

Output columns added:
  importado_final     — authoritative (P2 when matched, else S1 tipo_fabricacion)
  subfamilia_p2       — P2 sub-familia when matched (more granular), else blank
  perfil_proceso      — process activation profile (see PERFIL_MAP below)
  flag_proceso_pendiente — processes needed but not yet in PROCESS_THRESHOLDS.md
  dim_l_mm ... dim_notes — from dimensions-extracted.csv

Output: dataset/productos-master.csv
"""

import csv
import re
from pathlib import Path

REPO = Path(__file__).parent.parent

# ── load inputs ───────────────────────────────────────────────────────────────

def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

s1   = load_csv(REPO / "dataset" / "Sheet1-enriched.csv")
p2   = load_csv(REPO / "dataset" / "Productos-Categorizados2 - productos.csv")
dims = load_csv(REPO / "dataset" / "dimensions-extracted.csv")

# Index dimensions by handle (same order as s1, but keyed by handle)
dim_by_handle = {r["Product: Handle"]: r for r in dims}

# Index P2 by CÓDIGO (lowercase, stripped)
p2_by_code = {}
for r in p2:
    code = r["CÓDIGO"].lower().strip()
    if code:
        p2_by_code[code] = r

# ── perfil_proceso mapping ────────────────────────────────────────────────────
# Keys: sub-familia from P2 (preferred) or subfamilia from S1
# Values: (perfil_proceso, flag_proceso_pendiente)
#
# flag_proceso_pendiente values:
#   comp-electrico    — needs process 4.2 (not in PROCESS_THRESHOLDS.md yet)
#   instalacion-gas   — needs process 4.3 (not in PROCESS_THRESHOLDS.md yet)
#   comp-electrico|instalacion-gas — needs both
#   refrigeracion     — process 4.1 (in PROCESS_THRESHOLDS.md, gaps remain)
#   shape-ambiguous   — subfamilia mixes cylindrical & rectangular (needs split)
#   custom-quote      — no parametric profile; must be quoted individually

PERFIL_MAP = {
    # ── Sheet metal, no welds (p-plancha-simple) ──────────────────────────────
    "cubrejunta":          ("p-plancha-simple",  ""),
    "peinazo":             ("p-plancha-simple",  ""),
    "moldura":             ("p-plancha-simple",  ""),
    "guia":                ("p-plancha-simple",  ""),
    "tapa-registro":       ("p-plancha-simple",  ""),
    "revestimiento-modular":("p-plancha-simple", ""),
    "revestimiento-curvo": ("p-plancha-simple",  ""),
    "bandeja":             ("p-plancha-simple",  ""),
    "bandeja-simple":      ("p-plancha-simple",  ""),
    "bandeja-pasavalores": ("p-plancha-simple",  ""),
    "bandeja-carro":       ("p-plancha-simple",  ""),
    "soporte-muro":        ("p-plancha-simple",  ""),
    "soporte":             ("p-plancha-simple",  ""),
    "repisa":              ("p-plancha-simple",  ""),
    "repisa-bano":         ("p-plancha-simple",  ""),
    "banca":               ("p-plancha-simple",  ""),

    # ── Sumidero / drains (p-sumidero) ────────────────────────────────────────
    "sumidero":            ("p-sumidero",  ""),
    "liviano":             ("p-sumidero",  ""),   # lightweight sumideros
    "pesado":              ("p-sumidero",  ""),   # heavy sumideros
    "canaleta":            ("p-sumidero",  ""),
    "tapa-accesorio":      ("p-sumidero",  ""),
    "desague":             ("p-sumidero",  ""),
    "accesorio-piscina":   ("p-sumidero",  ""),

    # ── Mesones (p-meson) ─────────────────────────────────────────────────────
    "meson-simple":        ("p-meson", ""),
    "meson-repisa":        ("p-meson", ""),
    "meson-cajones":       ("p-meson", ""),
    "meson-trabajo":       ("p-meson", ""),
    "meson-en-proyecto":   ("p-meson", ""),
    "meson":               ("p-meson", ""),
    "meson-especial":      ("p-meson", ""),
    "base-reforzada":      ("p-meson", ""),

    # ── Lavaderos / sinks (p-lavadero) ────────────────────────────────────────
    "lavadero-simple":     ("p-lavadero", ""),
    "lavadero-multiple":   ("p-lavadero", ""),
    "lavadero-clinico":    ("p-lavadero", ""),
    "cubierta-con-taza":   ("p-lavadero", ""),
    "taza-simple":         ("p-lavadero", ""),
    "lavamanos":           ("p-lavadero", ""),
    "lavamopa":            ("p-lavadero", ""),
    "lavado":              ("p-lavadero", ""),    # S1 coarse tag — most fabricado lavado = lavaderos

    # ── Campanas (p-campana) — always comp-electrico for motor ────────────────
    "campana-mural":       ("p-campana", "comp-electrico"),
    "campana-central":     ("p-campana", "comp-electrico"),
    "accesorio-campana":   ("p-campana", "comp-electrico"),

    # ── Carros / trolleys (p-carro) — cilindrado tubes + plegado panels ───────
    "carro-bandejero":     ("p-carro", ""),
    "carro-cerrado":       ("p-carro", ""),
    "carro-multiproposito":("p-carro", ""),
    "carro-especial":      ("p-carro", ""),
    "carro-food":          ("p-carro", ""),
    "carro":               ("p-carro", ""),
    "carro-medico":        ("p-carro", ""),
    "modulo-neutro":       ("p-carro", ""),
    "modulo-servicio":     ("p-carro", ""),
    "salad-bar":           ("p-carro", ""),

    # ── Estanterías (p-meson — flat shelf, plegado profile) ───────────────────
    "estanteria":          ("p-meson", ""),

    # ── Cilíndricos simples (p-cilindrico — poruña, balde, batea) ─────────────
    "accesorio-simple":    ("p-cilindrico", ""),   # poruñas, baldes, escurridores
    "balde":               ("p-cilindrico", ""),
    "tinas-lacteos":       ("p-cilindrico", ""),   # cylindrical tinas
    "deposito-agua":       ("p-cilindrico", ""),

    # ── Basureros rectangulares (p-basurero-rect) ────────────────────────────
    "basurero-especial":   ("p-basurero-rect", ""),
    "basurero-reciclaje":  ("p-basurero-cil",  ""),  # tubes per process.md
    "basurero-con-mecanismo": ("p-basurero-cil", ""), # tapa pedal per process.md
    "basurero-simple":     ("p-basurero-rect", "shape-ambiguous"),  # mixes cylindrical & rectangular

    # ── Bicicleteros — cilindradora de tubos per process.md ──────────────────
    "bicicletero":         ("p-basurero-cil", ""),
    "bicicletero-standard":("p-basurero-cil", ""),
    "anti-skate":          ("p-basurero-cil", ""),

    # ── Refrigerated (p-refrigerado) — sheet body + process 4.1 ─────────────
    "salsera-refrigerada": ("p-refrigerado", "refrigeracion"),
    "meson-refrigerado":   ("p-refrigerado", "refrigeracion"),

    # ── Electrical / heated (p-electrico) — body + process 4.2 ──────────────
    "bano-maria":          ("p-electrico",   "comp-electrico"),
    "bano-maria-simple":   ("p-electrico",   "comp-electrico"),
    "bano-maria-con-gabinete": ("p-electrico","comp-electrico"),
    "calentamiento":       ("p-electrico",   "comp-electrico"),  # S1 coarse
    "hervidor":            ("p-cilindrico",  "comp-electrico"),
    "calentador-leche":    ("p-cilindrico",  "comp-electrico"),

    # ── Gas-powered (p-gas) — body + process 4.3 ─────────────────────────────
    "plancha-gas":         ("p-meson",       "instalacion-gas"),
    "cocina-gas":          ("p-meson",       "instalacion-gas"),  # NOTE: check P2 — some are importado
    "cocina-con-plancha":  ("p-meson",       "instalacion-gas"),
    "coccion":             ("p-meson",       "instalacion-gas"),  # S1 coarse
    "parrilla":            ("p-meson",       "instalacion-gas"),
    "horno-asador":        ("p-meson",       "instalacion-gas"),
    "cocina-wok":          ("p-meson",       "instalacion-gas"),
    "plancha-con-integrado":("p-meson",      "instalacion-gas"),
    "accesorio-coccion":   ("p-meson",       "instalacion-gas"),

    # ── Laser / engraving (p-laser) ───────────────────────────────────────────
    "logo":                ("p-laser", ""),
    "letras-armadas":      ("p-laser", ""),
    "letrero-volumetrico": ("p-laser", ""),
    "serigrafia":          ("p-laser", ""),
    "numero":              ("p-laser", ""),
    "totem":               ("p-laser", ""),

    # ── Celosía (p-celosia) ───────────────────────────────────────────────────
    "celosia":             ("p-celosia", ""),
    "recta":               ("p-celosia", ""),   # barras de seguridad rectas
    "curva":               ("p-celosia", ""),   # barras curvas
    "en-l":                ("p-celosia", ""),
    "en-angulo":           ("p-celosia", ""),
    "abatible":            ("p-celosia", ""),

    # ── Mobiliario clínico / especial ─────────────────────────────────────────
    "mobiliario-clinico":  ("p-meson",   ""),
    "meson-clinico":       ("p-meson",   ""),
    "tanatologia":         ("p-meson",   ""),
    "equipos-clinicos":    ("p-meson",   "comp-electrico"),
    "accesorio-clinico":   ("p-plancha-simple", ""),
    "mobiliario-bano":     ("p-meson",   ""),
    "mobiliario-especial": ("p-meson",   ""),

    # ── Accesorios hardware (small machined / tube parts) ─────────────────────
    "accesorio":           ("p-plancha-simple", ""),  # flanches, tomas, tapas tube
    "accesorio-con-mecanismo": ("p-plancha-simple", ""),
    "hardware-accesorio":  ("p-importado", ""),   # P2 shows these are importado

    # ── Baranda / structural (p-celosia nearest) ──────────────────────────────
    "mobiliario":          ("p-carro",   ""),    # S1 coarse — carros+estanterías dominate
    "especial":            ("p-custom",  "custom-quote"),
    "equipo-industrial":   ("p-custom",  "custom-quote"),
    "mesa-especial":       ("p-custom",  "custom-quote"),
    "proyecto-completo":   ("p-custom",  "custom-quote"),

    # ── Custom / en-proyecto ──────────────────────────────────────────────────
    "en-proyecto":         ("p-custom",  "custom-quote"),
    "colgador":            ("p-plancha-simple", ""),
    "puerta-acceso":       ("p-custom",  "custom-quote"),

    # ── Importado (no fabrication) ────────────────────────────────────────────
    "importado":           ("p-importado", ""),
    "utensilio":           ("p-importado", ""),
    "deposito-gn":         ("p-importado", ""),
    "taza-accesorio":      ("p-importado", ""),
    "griferia":            ("p-importado", ""),
    "griferia-simple":     ("p-importado", ""),
    "griferia-pedal":      ("p-importado", ""),
    "griferia-rodilla":    ("p-importado", ""),
    "griferia-especial":   ("p-importado", ""),
    "cucharas":            ("p-importado", ""),
    "prewash":             ("p-importado", ""),
    "cuello-cisne":        ("p-importado", ""),
    "valvula":             ("p-importado", ""),
    "tapa-deposito":       ("p-importado", ""),
    "tapa-accesorio":      ("p-importado", ""),
    "lavavajillas":        ("p-importado", ""),
    "visicooler":          ("p-importado", ""),
    "refrigerador":        ("p-importado", ""),
    "freezer":             ("p-importado", ""),
    "meson-freezer":       ("p-importado", ""),
    "freidora":            ("p-importado", ""),
    "freidora-gas":        ("p-importado", ""),
    "freidora-electrica":  ("p-importado", ""),
    "horno":               ("p-importado", ""),
    "horno-convector":     ("p-importado", ""),
    "horno-pizza":         ("p-importado", ""),
    "vitrina-pastelera":   ("p-importado", ""),
    "vitrina-refrigerada": ("p-importado", ""),
    "vitrina-caliente":    ("p-importado", ""),
    "vitrina-encimera":    ("p-importado", ""),
    "salsera-pizza":       ("p-importado", ""),
    "salsera-grande":      ("p-importado", ""),
    "salsera-simple":      ("p-importado", ""),  # check with user — some may be fabricado
    "bano-maria-electrico":("p-importado", ""),
    "bano-maria-encimera": ("p-importado", ""),
    "chocolatera":         ("p-importado", ""),
    "cortador":            ("p-importado", ""),
    "dispensador":         ("p-importado", ""),
    "estacion-agua":       ("p-importado", ""),
    "cocina-induccion":    ("p-importado", ""),
    "cocina-electrica":    ("p-importado", ""),
    "cocina-con-horno":    ("p-importado", ""),  # P2 flags as IMPORTADO
    "gratinador":          ("p-importado", ""),
    "sarten":              ("p-importado", ""),
    "armario":             ("p-importado", ""),
    "buzon":               ("p-importado", ""),
    "accesorio-freidora":  ("p-importado", ""),
    "accesorio-coccion":   ("p-importado", ""),  # overridden above if fabricado
    "doble":               ("p-importado", ""),

    # ── P2 granular additions (resolved from p-unknown pass) ──────────────────
    # Estanterías / repisas — flat sheet, plegado
    "estanteria-lisa":     ("p-meson", ""),
    "estanteria-parrilla": ("p-meson", ""),
    "repisa-doble":        ("p-meson", ""),
    "repisa-simple":       ("p-meson", ""),
    "estanteria-especial": ("p-meson", ""),
    "repisa-especial":     ("p-meson", ""),

    # Anafes — gas burner module (sheet body + gas install)
    "anafe":               ("p-meson",   "instalacion-gas"),

    # Planchas con integrado (plancha + bain-marie integrated)
    "plancha-con-bano-maria": ("p-meson", "comp-electrico|instalacion-gas"),

    # Salseras por tamaño (calentamiento family — heated body)
    "mediana":             ("p-electrico", "comp-electrico"),
    "pequena":             ("p-electrico", "comp-electrico"),
    "grande":              ("p-electrico", "comp-electrico"),

    # Hornos industriales — fabricated body + gas/electric
    "horno-industrial":    ("p-meson",   "instalacion-gas"),

    # Sumideros con tapa / rejilla — same profile
    "sumidero-tapa":       ("p-sumidero", ""),
    "sumidero-rejilla":    ("p-sumidero", ""),

    # Protección escalera — tubular safety structure
    "proteccion-escalera": ("p-celosia",  ""),

    # Quesería / lácteos — cylindrical molds and presses
    "molde-queso":         ("p-cilindrico", ""),
    "tina-quesera":        ("p-cilindrico", ""),
    "prensa-quesera":      ("p-cilindrico", ""),

    # Poruñas por tamaño (P2 splits poruña-pequeña / poruña-grande)
    "poruña-pequeña":      ("p-cilindrico", ""),
    "poruña-grande":       ("p-cilindrico", ""),

    # Lavabotas — floor-level basin, sumidero profile
    "lavabotas":           ("p-sumidero", ""),

    # Escalera piscina — tubular structure
    "escalera-piscina":    ("p-celosia",  ""),

    # Accesorio especial — catch-all custom
    "accesorio-especial":  ("p-custom",   "custom-quote"),
}

# ── join logic ────────────────────────────────────────────────────────────────

def find_p2_match(handle: str) -> dict | None:
    """Return P2 row whose CÓDIGO appears as substring in the handle."""
    h = handle.lower()
    for code, row in p2_by_code.items():
        if code in h:
            return row
    return None


def resolve_importado(s1_row: dict, p2_row: dict | None) -> str:
    if p2_row:
        return "SI" if p2_row.get("IMPORTADO", "").strip() == "IMPORTADO" else "NO"
    # fallback: use S1 tipo_fabricacion
    tf = s1_row.get("tipo_fabricacion", "").strip()
    if tf in ("importado-resell", "importado-revisar"):
        return "SI"
    if tf == "fabricado":
        return "NO"
    return "?"


def resolve_perfil(s1_row: dict, p2_row: dict | None, importado: str) -> tuple[str, str]:
    if importado == "SI":
        return "p-importado", ""

    # prefer P2 sub-familia (more granular), fall back to S1 subfamilia
    sf = ""
    if p2_row:
        sf = p2_row.get("sub-familia", "").strip()
    if not sf:
        sf = s1_row.get("subfamilia", "").strip()

    if sf in PERFIL_MAP:
        return PERFIL_MAP[sf]

    # last resort: unknown
    return "p-unknown", "needs-manual-review"


# ── dim columns to carry over ────────────────────────────────────────────────
DIM_COLS = ["dim_l_mm", "dim_w_mm", "dim_h_mm", "dim_diameter_mm",
            "dim_espesor_mm", "dim_pattern", "dim_confidence", "dim_notes"]

# ── build output rows ─────────────────────────────────────────────────────────

NEW_COLS = ["importado_final", "subfamilia_p2",
            "perfil_proceso", "flag_proceso_pendiente"] + DIM_COLS

s1_fieldnames = list(s1[0].keys())
all_fieldnames = s1_fieldnames + NEW_COLS

stats = {
    "p2_matched": 0, "p2_unmatched": 0,
    "importado": 0, "fabricado": 0, "unknown_importado": 0,
    "unknown_perfil": 0,
}
perfil_counts = {}
flag_counts = {}

out_rows = []
for row in s1:
    handle = row.get("Product: Handle", "")
    p2_row = find_p2_match(handle)

    if p2_row:
        stats["p2_matched"] += 1
    else:
        stats["p2_unmatched"] += 1

    importado = resolve_importado(row, p2_row)
    perfil, flag = resolve_perfil(row, p2_row, importado)

    if importado == "SI":   stats["importado"] += 1
    elif importado == "NO": stats["fabricado"] += 1
    else:                   stats["unknown_importado"] += 1
    if perfil == "p-unknown": stats["unknown_perfil"] += 1

    perfil_counts[perfil] = perfil_counts.get(perfil, 0) + 1
    if flag:
        flag_counts[flag] = flag_counts.get(flag, 0) + 1

    dim_row = dim_by_handle.get(handle, {})

    out_row = dict(row)
    out_row["importado_final"]         = importado
    out_row["subfamilia_p2"]           = p2_row["sub-familia"] if p2_row else ""
    out_row["perfil_proceso"]          = perfil
    out_row["flag_proceso_pendiente"]  = flag
    for col in DIM_COLS:
        out_row[col] = dim_row.get(col, "")

    out_rows.append(out_row)

# ── write output ──────────────────────────────────────────────────────────────

outfile = REPO / "dataset" / "productos-master.csv"
with open(outfile, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=all_fieldnames)
    writer.writeheader()
    writer.writerows(out_rows)

# ── report ────────────────────────────────────────────────────────────────────

total = len(out_rows)
print(f"Input rows : {total}")
print(f"Output     : {outfile}")
print()
print("P2 join:")
print(f"  matched   {stats['p2_matched']:4d}  ({stats['p2_matched']/total*100:.0f}%)")
print(f"  unmatched {stats['p2_unmatched']:4d}  ({stats['p2_unmatched']/total*100:.0f}%)")
print()
print("Importado resolution:")
print(f"  importado {stats['importado']:4d}  ({stats['importado']/total*100:.0f}%)")
print(f"  fabricado {stats['fabricado']:4d}  ({stats['fabricado']/total*100:.0f}%)")
print(f"  unknown   {stats['unknown_importado']:4d}")
print()
print("Perfil proceso distribution:")
for p, n in sorted(perfil_counts.items(), key=lambda x: -x[1]):
    print(f"  {n:4d}  {p}")
print()
print("Flag proceso pendiente:")
for f, n in sorted(flag_counts.items(), key=lambda x: -x[1]):
    print(f"  {n:4d}  {f}")
if stats["unknown_perfil"]:
    print(f"\n  ⚠  {stats['unknown_perfil']} rows with p-unknown — check PERFIL_MAP")
