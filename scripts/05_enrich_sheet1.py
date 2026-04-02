"""
05_enrich_sheet1.py
Normalizes Sheet1-scraped.csv by:
  1. Mapping Sheet1 family slugs → Sheet2 Spanish family names
  2. Reclassifying products inside broad catch-all families using subfamilia + description
  3. Assigning tipo_fabricacion from description signals
  4. Assigning complejidad (LAYER_2 aligned)

Input:  'Sheet1-scraped.csv'
Output: 'Sheet1-enriched.csv'
"""

import pandas as pd
import re

INPUT  = "Sheet1-scraped.csv"
OUTPUT = "Sheet1-enriched.csv"

# ---------------------------------------------------------------------------
# 1. FAMILY NAME NORMALIZATION (slug → Sheet2 Spanish name)
#    For direct 1:1 or close mappings.
# ---------------------------------------------------------------------------
FAMILY_MAP = {
    "mesones-de-trabajo":              "Mesones de Trabajo",
    "basureros":                       "Basureros",
    "lavaderos":                       "Lavaderos",
    "zona-de-lavado":                  "Lavaderos",
    "campanas":                        "Campanas Industriales y Domésticas",
    "hervidores":                      "Hervidores",
    "hornos":                          "Hornos",
    "freidoras":                       "Freidoras",
    "sumideros":                       "Sumideros",
    "baranda-y-pasamanos":             "Baranda y Pasamanos",
    "bicicleteros":                    "Bicicleteros",
    "tinas-queseras":                  "Tinas Queseras y Más",
    "muebles-refrigerados":            "Muebles refrigerados",
    "accesorios-gastronomicos":        "Accesorios Gastronómicos",
    "accesorios-bano":                 "Accesorios para Personas con Capacidades Diferentes",
    "barras-de-apoyo":                 "Accesorios para Personas con Capacidades Diferentes",
    "equipos-clinicos":                "Accesorios para Personas con Capacidades Diferentes",
    "cubrejuntas-peinazos-y-zocalos":  "Peinazo",
    "revestimientos-lisos-y-modulares":"Peinazo",
    "letreros-logotipos-y-numeros":    "Números y Letras",
    "mobiliario-urbano":               "Bicicleteros",
    "mobiliario-de-acero-y-madera":    "Sillas",
    "modulos-de-autoservicio":         "Módulo de Autoservicio",
    "vitrinas-exhibidoras-caliente":   "Muebles refrigerados",
    "camaras-desengrasadoras":         "Cámaras Desgrasadoras",
    "cocinas":                         "Cocinas Industriales",
    "urinarios":                       "Urinarios",
    "tazas-industriales":              "Tinas Queseras y Más",
    "salseras":                        "Salseras",
    "estanterias":                     "Estantes",
    "productos-especiales":            "Equipo Industrial",
    "tanatologia":                     "Equipo Industrial",
}

# ---------------------------------------------------------------------------
# 2. RECLASSIFY BROAD FAMILIES using (subfamilia, handle, description)
#    Families: gastronomica, otros-productos, construccion, coccion, preelaboracion
# ---------------------------------------------------------------------------

# gastronomica subfamilia → Sheet2 family
GASTRO_SUB_MAP = {
    "lavado":        "Lavaderos",
    "calentamiento": "Baño María",
    "mobiliario":    "Carros de Traslado",
    "coccion":       "Cocinas Industriales",
    "refrigeracion": "Muebles refrigerados",
    "importado":     "Accesorios Gastronómicos",
    "accesorio":     "Accesorios Gastronómicos",
}

# otros-productos subfamilia → Sheet2 family
OTROS_SUB_MAP = {
    "especial":           "Equipo Industrial",
    "equipo-industrial":  "Equipo Industrial",
    "carro-food":         "Carros de Traslado",
    "balde":              "Baldes",
    "mobiliario":         "Sillas",
    "tinas-lacteos":      "Tinas Queseras y Más",
    "tanatologia":        "Equipo Industrial",
    "modulo-servicio":    "Módulo de Autoservicio",
    "accesorio-piscina":  "Equipo Industrial",
    "mobiliario-especial":"Equipo Industrial",
    "equipos-clinicos":   "Accesorios para Personas con Capacidades Diferentes",
}

# construccion subfamilia → Sheet2 family
CONST_SUB_MAP = {
    "accesorio":             "Peinazo",
    "basurero-reciclaje":    "Basureros",
    "basurero-especial":     "Basureros",
    "basurero-con-mecanismo":"Basureros",
    "basurero-simple":       "Basureros",
    "liviano":               "Sumideros",
    "pesado":                "Sumideros",
    "en-proyecto":           "Equipo Industrial",
    "soporte-muro":          "Equipo Industrial",
}

# coccion subfamilia → Sheet2 family
COCCION_SUB_MAP = {
    "plancha-gas":         "Plancha Churrasquera",
    "plancha-con-integrado":"Plancha Churrasquera y Baño Maria",
    "cocina-gas":          "Cocinas Industriales",
    "cocina-wok":          "Cocinas Industriales",
    "cocina-con-horno":    "Cocinas Industriales",
    "anafe":               "Cocinas Industriales",
    "accesorio-coccion":   "Accesorios Gastronómicos",
    "calentamiento":       "Baño María",
    "horno":               "Hornos",
    "freidora":            "Freidoras",
    "parrilla":            "Cocinas Industriales",
}

# preelaboracion subfamilia → Sheet2 family
PREELABORACION_SUB_MAP = {
    "meson-trabajo": "Mesones de Trabajo",
    "estanteria":    "Estantes",
    "accesorio":     "Accesorios Gastronómicos",
    "carro":         "Carros de Traslado",
}

BROAD_FAMILY_MAPS = {
    "gastronomica":   GASTRO_SUB_MAP,
    "otros-productos":OTROS_SUB_MAP,
    "construccion":   CONST_SUB_MAP,
    "coccion":        COCCION_SUB_MAP,
    "preelaboracion": PREELABORACION_SUB_MAP,
}

def normalize_family(familia: str, subfamilia: str, handle: str, desc: str) -> str:
    # Direct map
    if familia in FAMILY_MAP:
        return FAMILY_MAP[familia]

    # Broad family: reclassify by subfamilia
    if familia in BROAD_FAMILY_MAPS:
        sub_map = BROAD_FAMILY_MAPS[familia]
        result = sub_map.get(subfamilia)
        if result:
            return result
        # Fallback: keyword scan on description
        d = desc.lower()
        h = handle.lower()
        if any(k in d+h for k in ["kangkawe","tramontina","vollrath"]):
            return "Accesorios Gastronómicos"
        if any(k in d for k in ["lavadero","lavafondo","lavamanos","pileta","taza"]):
            return "Lavaderos"
        if any(k in d for k in ["mesón","meson de trabajo","mesa de trabajo"]):
            return "Mesones de Trabajo"
        if any(k in d for k in ["basurero","basura","pedal"]):
            return "Basureros"
        if any(k in d for k in ["estante","repisa","estanteria"]):
            return "Estantes"
        if any(k in d for k in ["carro","bandejero"]):
            return "Carros de Traslado"
        if any(k in d for k in ["plancha","churrasquera"]):
            return "Plancha Churrasquera"
        if any(k in d for k in ["cocina","quemador","hornilla"]):
            return "Cocinas Industriales"
        if any(k in d for k in ["horno","convector"]):
            return "Hornos"
        if any(k in d for k in ["freidora","freído"]):
            return "Freidoras"
        if any(k in d for k in ["refriger","freezer","congelar"]):
            return "Muebles refrigerados"
        if any(k in d for k in ["baño maria","bano maria","calentamiento"]):
            return "Baño María"
        if any(k in d for k in ["sumidero","canaleta","rejilla"]):
            return "Sumideros"
        if any(k in d for k in ["cubrejunta","peinazo","zocalo","zócalo","revestimiento"]):
            return "Peinazo"
        # Last resort: keep original slug
        return familia.replace("-", " ").title()

    return familia.replace("-", " ").title()


# ---------------------------------------------------------------------------
# 3. TIPO_FABRICACION from description + handle signals
# ---------------------------------------------------------------------------
RESELL_BRANDS = ["kangkawe", "tramontina", "vollrath"]

# Signals that strongly indicate Dulox fabrication
FABRICADO_SIGNALS = [
    "fabricado íntegramente en acero inoxidable",
    "fabricado integramente en acero inoxidable",
    "fabricada integramente en acero inoxidable",
    "fabricada íntegramente en acero inoxidable",
    "soporte en perfil",
    "lámina de acero inoxidable",
    "lamina de acero inoxidable",
    "soldado",
    "soldada",
    "perfil 30x30",
    "patines regulables",
    "aisi 304",
]

def get_tipo_fabricacion(subfamilia: str, handle: str, desc: str) -> str:
    h = handle.lower()
    d = desc.lower()

    # Subfamilia already flagged as imported
    if subfamilia.strip().lower() == "importado":
        return "importado-resell"

    # Brand signals → resell
    if any(b in h or b in d for b in RESELL_BRANDS):
        return "importado-resell"

    # Strong fabrication signals → fabricado
    if any(s in d for s in FABRICADO_SIGNALS):
        return "fabricado"

    # No description or too short → uncertain
    if len(desc.strip()) < 40:
        return "importado-revisar"

    # If description looks like a Shopify page title only (no specs)
    if "dulox tienda" in d and len(desc.strip()) < 100:
        return "importado-revisar"

    # Default: assume fabricado (Dulox is primarily a manufacturer)
    return "fabricado"


# ---------------------------------------------------------------------------
# 4. COMPLEJIDAD (same LAYER_2 logic as enrich_sheet2.py)
# ---------------------------------------------------------------------------
SUBFAMILY_DEFAULT: dict[str, str] = {
    "meson-simple": "C1", "meson-repisa": "C1", "meson-cajones": "C2",
    "meson-en-proyecto": "C3", "meson-freezer": "C2", "meson-refrigerado": "C2",
    "meson-trabajo": "C1", "meson": "C1",
    "lavadero-simple": "C1", "lavadero-multiple": "C2", "lavamanos": "C1",
    "lavamopa": "C1", "lavadero": "C1", "lavado": "C1",
    "accesorio-clinico": "C1", "cubierta-con-taza": "C2", "taza-accesorio": "C1",
    "basurero-simple": "C1", "basurero-con-mecanismo": "C2",
    "basurero-reciclaje": "C2", "basurero-especial": "C3",
    "campana-mural": "C1", "campana-central": "C2", "accesorio-campana": "C1",
    "carro-bandejero": "C1", "carro-multiproposito": "C2", "carro-cerrado": "C2",
    "carro-especial": "C3", "carro-food": "C2", "carro": "C1",
    "estanteria-lisa": "C1", "estanteria-parrilla": "C1", "estanteria-especial": "C2",
    "estanteria": "C1", "repisa-simple": "C1", "repisa-doble": "C1", "repisa-especial": "C2",
    "cocina-gas": "C2", "cocina-electrica": "C2", "cocina-induccion": "C2",
    "cocina-con-horno": "C3", "cocina-con-plancha": "C2", "cocina-wok": "C2", "anafe": "C1",
    "horno-convector": "C2", "horno-industrial": "C3", "horno-asador": "C2",
    "horno-pizza": "C2", "horno": "C2",
    "freidora-gas": "C2", "freidora-electrica": "C2", "freidora-especial": "C3", "freidora": "C2",
    "plancha-gas": "C1", "plancha-electrica": "C1", "plancha-con-bano-maria": "C2",
    "plancha-con-integrado": "C2", "plancha-especial": "C2",
    "bano-maria-simple": "C1", "bano-maria-electrico": "C1",
    "bano-maria-encimera": "C1", "bano-maria-con-gabinete": "C2",
    "calentamiento": "C1",
    "peinazo": "C1", "zocalo": "C1", "canaleta": "C1",
    "accesorio": "C1", "liviano": "C1", "pesado": "C2",
    "sumidero-rejilla": "C1", "sumidero-tapa": "C1",
    "accesorio-simple": "C1", "accesorio-con-mecanismo": "C1",
    "modulo-servicio": "C2", "mobiliario": "C1", "refrigeracion": "C3",
    "especial": "C3", "en-proyecto": "C3",
    "balde": "C1", "tinas-lacteos": "C2", "accesorio-coccion": "C1",
    "coccion": "C2", "parrilla": "C2",
}

TIER_ORDER = ["C1", "C2", "C3"]

def upgrade(t):
    return TIER_ORDER[min(TIER_ORDER.index(t) + 1, 2)] if t in TIER_ORDER else "C2"

def downgrade(t):
    return TIER_ORDER[max(TIER_ORDER.index(t) - 1, 0)] if t in TIER_ORDER else "C1"

UPGRADE_KW = [
    "multiple", "triple", "cuadruple", "cajones", "cajonera",
    "motor", "electrico", "eléctrico", "electrica", "eléctrica",
    "refriger", "cilindrado", "curvo", "curva",
    "refuerzo", "especial", "extractor", "armado",
    "con horno", "con motor", "con plancha", "con lonchera",
    "lavabotas", "con mecanismo", "tres tazas", "dos tazas", "cuatro",
]
DOWNGRADE_KW = ["mini", "pequeño", "pequeña", "chico", "chica"]
DIM_RE = re.compile(r"\b(\d{3,4})\b")

def get_complejidad(subfamilia: str, handle: str, desc: str) -> str:
    sub = subfamilia.strip().lower()
    h   = handle.strip().lower()
    d   = desc.strip().lower()

    base = SUBFAMILY_DEFAULT.get(sub, "C1")

    dims = [int(m) for m in DIM_RE.findall(h + " " + d[:200])]
    geo_upgrade = max(dims) >= 1800 if dims else False

    text = d + " " + h
    feature_upgrade  = any(k in text for k in UPGRADE_KW)
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

    new_familia   = []
    new_tipo      = []
    new_complejidad = []

    for _, row in df.iterrows():
        familia   = str(row.get("familia",   "")).strip()
        subfamilia= str(row.get("subfamilia","")).strip()
        handle    = str(row.get("Product: Handle", "")).strip()
        desc      = str(row.get("descripcion_web", "")).strip()

        fam_norm = normalize_family(familia, subfamilia, handle, desc)
        tipo     = get_tipo_fabricacion(subfamilia, handle, desc)
        comp     = "" if tipo == "importado-resell" else get_complejidad(subfamilia, handle, desc)

        new_familia.append(fam_norm)
        new_tipo.append(tipo)
        new_complejidad.append(comp)

    df["familia_normalizada"] = new_familia
    df["tipo_fabricacion"]    = new_tipo
    df["complejidad"]         = new_complejidad

    df.to_csv(OUTPUT, index=False)

    print("=== tipo_fabricacion ===")
    print(df["tipo_fabricacion"].value_counts().to_string())
    print()
    print("=== complejidad (non-resell) ===")
    print(df[df["tipo_fabricacion"] != "importado-resell"]["complejidad"].value_counts().to_string())
    print()
    print("=== familia_normalizada (top 20) ===")
    print(df["familia_normalizada"].value_counts().head(20).to_string())
    print()
    print(f"Saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
