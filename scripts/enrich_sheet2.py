"""
enrich_sheet2.py
Add 'tipo_fabricacion' and 'complejidad' columns to Sheet2.

Definitions:
  tipo_fabricacion:
    - 'fabricado'          → made by Dulox from raw materials; enters full ABC costing model
    - 'importado-resell'   → bought finished, sold as-is; margin-only pricing, no recipe
    - 'importado-material' → imported component integrated into a Dulox-fabricated structure;
                             enters recetario as a material cost input
    - 'importado-revisar'  → uncertain, needs manual classification by Miguel

  complejidad (aligned with LAYER_2 scoring):
    C1 = score 0–3 (LOW)   → +0% adjustment
    C2 = score 4–7 (MEDIUM) → +10% adjustment
    C3 = score 8+  (HIGH)  → +25% adjustment
    blank = importado-resell (not applicable)

Input:  'Productos-Categorizados2 - productos.csv'
Output: 'Sheet2-enriched.csv'
        'importado-revisar.txt'
"""

import pandas as pd
import re

INPUT  = "Productos-Categorizados2 - productos.csv"
OUTPUT = "Sheet2-enriched.csv"
REVIEW = "importado-revisar.txt"

# ---------------------------------------------------------------------------
# tipo_fabricacion rules
# ---------------------------------------------------------------------------

# Families that are 100% imported-for-resell (no Dulox manufacturing)
PURE_RESELL_FAMILIES = {
    "Vollrath",
    "Tramontina",
    "Kangkawe",
}

# Families where an imported product is very likely a component integrated
# into a Dulox-fabricated structure (importado-material)
LIKELY_MATERIAL_FAMILIES = {
    "Griferías",           # faucet bodies, pedal kits welded into lavaderos
    "Accesorios Gastronómicos",  # some mechanism parts for basureros / carros
}

def get_tipo_fabricacion(familia: str, subfamilia: str, importado: str) -> str:
    is_imported = str(importado).strip().upper() == "IMPORTADO"

    if not is_imported:
        return "fabricado"

    # Explicit resell: known brands
    if familia in PURE_RESELL_FAMILIES:
        return "importado-resell"

    # Explicit resell: subfamilia already flagged 'importado'
    if str(subfamilia).strip().lower() == "importado":
        return "importado-resell"

    # Likely material component
    if familia in LIKELY_MATERIAL_FAMILIES:
        return "importado-material"

    # Everything else imported → flag for manual review
    return "importado-revisar"


# ---------------------------------------------------------------------------
# complejidad rules (LAYER_2 aligned)
# ---------------------------------------------------------------------------

# Default complexity per subfamilia.
# C1 = cut + fold (LOW), C2 = + welding (MEDIUM), C3 = + assembly / electrics (HIGH)
SUBFAMILY_DEFAULT: dict[str, str] = {
    # Mesones
    "meson-simple":       "C1",
    "meson-repisa":       "C1",
    "meson-cajones":      "C2",
    "meson-en-proyecto":  "C3",
    "meson-freezer":      "C2",
    "meson-refrigerado":  "C2",
    "meson":              "C1",
    # Lavaderos
    "lavadero-simple":    "C1",
    "lavadero-multiple":  "C2",
    "lavamanos":          "C1",
    "lavamopa":           "C1",
    "accesorio-clinico":  "C1",
    "cubierta-con-taza":  "C2",
    "taza-accesorio":     "C1",
    # Basureros
    "basurero-simple":        "C1",
    "basurero-con-mecanismo": "C2",
    "basurero-reciclaje":     "C2",
    "basurero-especial":      "C3",
    # Campanas
    "campana-mural":       "C1",
    "campana-central":     "C2",
    "accesorio-campana":   "C1",
    # Carros
    "carro-bandejero":     "C1",
    "carro-multiproposito":"C2",
    "carro-cerrado":       "C2",
    "carro-especial":      "C3",
    "carro-food":          "C2",
    # Estantes / repisas
    "estanteria-lisa":     "C1",
    "estanteria-parrilla": "C1",
    "estanteria-especial": "C2",
    "repisa-simple":       "C1",
    "repisa-doble":        "C1",
    "repisa-especial":     "C2",
    # Cocinas
    "cocina-gas":          "C2",
    "cocina-electrica":    "C2",
    "cocina-induccion":    "C2",
    "cocina-con-horno":    "C3",
    "cocina-con-plancha":  "C2",
    "cocina-wok":          "C2",
    "anafe":               "C1",
    # Hornos
    "horno-convector":     "C2",
    "horno-industrial":    "C3",
    "horno-asador":        "C2",
    "horno-pizza":         "C2",
    # Freidoras
    "freidora-gas":        "C2",
    "freidora-electrica":  "C2",
    "freidora-especial":   "C3",
    # Planchas
    "plancha-gas":         "C1",
    "plancha-electrica":   "C1",
    "plancha-con-bano-maria":  "C2",
    "plancha-con-lonchera":    "C2",
    "plancha-especial":        "C2",
    "plancha-churrasquera":    "C1",
    # Baño María
    "bano-maria-simple":       "C1",
    "bano-maria-electrico":    "C1",
    "bano-maria-encimera":     "C1",
    "bano-maria-con-gabinete": "C2",
    "bano-maria":              "C1",
    # Construccion / zócalos
    "peinazo":   "C1",
    "zocalo":    "C1",
    "canaleta":  "C1",
    "recta":     "C1",
    "en-angulo": "C1",
    "en-l":      "C1",
    "abatible":  "C1",
    "guia":      "C1",
    # Sumideros
    "sumidero-rejilla": "C1",
    "sumidero-tapa":    "C1",
    # Accesorios
    "accesorio-simple":       "C1",
    "accesorio-con-mecanismo":"C1",
    "accesorio-freidora":     "C1",
    "accesorio":              "C1",
    "hardware-accesorio":     "C1",
    # Herramientas
    "hervidor":       "C2",
    "calentador-leche":"C1",
    "chocolatera":    "C1",
    "marmita":        "C2",
    "olla":           "C1",
    # Módulos autoservicio / vitrinas
    "modulo-neutro":    "C2",
    "salad-bar":        "C2",
    "vitrina-caliente": "C2",
    "vitrina-refrigerada":"C3",
    "vitrina-pastelera": "C2",
    "vitrina-encimera":  "C2",
    "visicooler":       "C3",
    "refrigerador":     "C3",
    "freezer":          "C3",
    "muebles-refrigerados":"C3",
    # Salseras / ollas / poruñas
    "salsera-simple":  "C1",
    "salsera-grande":  "C1",
    "salsera-pizza":   "C1",
    "poruña-pequeña":  "C1",
    "poruña-mediana":  "C1",
    "poruña-grande":   "C1",
    # Otros fabricados
    "bicicletero-standard": "C1",
    "buzon":          "C1",
    "escalera-piscina":"C2",
    "soporte-extintor":"C1",
    "gabinete-extintor":"C2",
    "urinario":       "C2",
    "mudador":        "C1",
    "silla":          "C2",
    "banca":          "C1",
    "bandeja-simple": "C1",
    "bandeja":        "C1",
    "bandeja-carro":  "C1",
    "balde":          "C1",
    "tina-quesera":   "C2",
    "molde-queso":    "C1",
    "prensa-quesera": "C1",
    "lavabotas":      "C1",
    "numero":         "C1",
    "letra":          "C1",
    "puerta-acceso":  "C2",
    "anti-skate":     "C1",
    "proteccion-escalera":"C1",
    "armario":        "C2",
    "doble":          "C1",
    "grande":         "C1",
    "mediana":        "C1",
    "pequena":        "C1",
    # Always C3
    "especial":       "C3",
    "en-proyecto":    "C3",
    # Grifería (imported, but some are material)
    "griferia-simple":  "C1",
    "griferia-pedal":   "C1",
    "griferia-rodilla": "C1",
    "griferia-especial":"C2",
    "cuello-cisne":     "C1",
    "prewash":          "C1",
    "desague":          "C1",
    "valvula":          "C1",
    "estacion-agua":    "C2",
    # Lavavajillas
    "lavavajillas":     "C2",
    # Bandejas pasa valores
    "bandeja-pasavalores": "C2",
    # Depósitos GN (Vollrath-style, imported)
    "deposito-gn":      "C1",
    "tapa-accesorio":   "C1",
    "dispensador":      "C2",
    "cucharas":         "C1",
    "utensilio":        "C1",
    "sarten":           "C1",
    "cortador":         "C1",
}

TIER_ORDER = ["C1", "C2", "C3"]

def upgrade(tier: str) -> str:
    idx = TIER_ORDER.index(tier) if tier in TIER_ORDER else 0
    return TIER_ORDER[min(idx + 1, 2)]

def downgrade(tier: str) -> str:
    idx = TIER_ORDER.index(tier) if tier in TIER_ORDER else 2
    return TIER_ORDER[max(idx - 1, 0)]

# Keywords that push complexity UP
UPGRADE_KW = [
    "multiple", "triple", "cuadruple", "cajones", "cajonera",
    "motor", "electrico", "eléctrico", "electrica", "eléctrica",
    "refriger", "cilindrado", "curvo", "curva",
    "refuerzo", "especial", "extractor", "armado",
    "con horno", "con motor", "con plancha", "con lonchera",
    "lavabotas", "con mecanismo",
]
# Keywords that push complexity DOWN
DOWNGRADE_KW = ["mini", "pequeño", "pequeña", "chico", "chica"]

# Dimension regex: 4-digit numbers like 1800, 2400, etc.
DIM_RE = re.compile(r"\b(\d{3,4})\b")


def get_complejidad(subfamilia: str, codigo: str, producto: str) -> str:
    sub = str(subfamilia).strip().lower()
    cod = str(codigo).strip().lower()
    prod = str(producto).strip().lower()

    base = SUBFAMILY_DEFAULT.get(sub)
    if base is None:
        base = "C1"  # safe default

    # Geometry signal: extract largest dimension from code
    dims = [int(m) for m in DIM_RE.findall(cod)]
    max_dim = max(dims) if dims else 0
    geo_upgrade = max_dim >= 1800

    # Feature signals from product name
    text = prod + " " + cod
    feature_upgrade = any(k in text for k in UPGRADE_KW)
    feature_downgrade = any(k in text for k in DOWNGRADE_KW)

    tier = base
    if geo_upgrade or feature_upgrade:
        tier = upgrade(tier)
    if feature_downgrade:
        tier = downgrade(tier)

    return tier


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    df = pd.read_csv(INPUT)

    tipo_list = []
    comp_list = []

    for _, row in df.iterrows():
        familia   = str(row.get("familia", "")).strip()
        subfamilia= str(row.get("sub-familia", "")).strip()
        codigo    = str(row.get("CÓDIGO", "")).strip()
        producto  = str(row.get("PRODUCTO", "")).strip()
        importado = str(row.get("IMPORTADO", "")).strip()

        tipo = get_tipo_fabricacion(familia, subfamilia, importado)
        tipo_list.append(tipo)

        if tipo in ("importado-resell",):
            comp_list.append("")
        else:
            comp_list.append(get_complejidad(subfamilia, codigo, producto))

    df["tipo_fabricacion"] = tipo_list
    df["complejidad"]      = comp_list

    df.to_csv(OUTPUT, index=False)

    # Summary
    print("=== tipo_fabricacion ===")
    print(df["tipo_fabricacion"].value_counts().to_string())
    print()
    print("=== complejidad (fabricado only) ===")
    fab = df[df["tipo_fabricacion"] != "importado-resell"]
    print(fab["complejidad"].value_counts().to_string())
    print()

    # Write review list
    revisar = df[df["tipo_fabricacion"] == "importado-revisar"][
        ["familia", "sub-familia", "CÓDIGO", "PRODUCTO"]
    ]
    with open(REVIEW, "w", encoding="utf-8") as f:
        f.write("Products flagged for manual tipo_fabricacion classification\n")
        f.write("Classify each as: importado-resell OR importado-material\n")
        f.write("=" * 60 + "\n\n")
        for _, r in revisar.iterrows():
            f.write(f"[{r['familia']}] {r['CÓDIGO']} — {r['PRODUCTO']}\n")

    print(f"Review list: {len(revisar)} products → {REVIEW}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
