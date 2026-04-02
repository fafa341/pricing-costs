"""
04_consolidar.py
Combines Sheet1-enriched.csv and Sheet2-enriched.csv into a single master catalog.

Input:  'Sheet1-enriched.csv'   (from 05_enrich_sheet1.py)
        'Sheet2-enriched.csv'   (from enrich_sheet2.py)
Output: 'catalogo-maestro.csv'
"""

import pandas as pd
import os
import sys

SHEET1 = "Sheet1-enriched.csv"
SHEET2 = "Sheet2-enriched.csv"
OUTPUT = "catalogo-maestro.csv"


def load_sheet1(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Drop duplicate/junk columns before renaming
    drop_cols = ["ID", "Unnamed: 3", "Product: ID", "Parte importada",
                 "Variable dependiente1", "Variable dependiente 2",
                 "Variable dependiente 3", "subfamilia.1", "familia"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    df = df.rename(columns={
        "familia_normalizada": "familia",
        "subfamilia":          "subfamilia",
        "Product: Handle":     "handle",
        "Importado":           "importado_flag",
        "url":                 "url",
        "descripcion_web":     "descripcion_web",
        "scrape_status":       "scrape_status",
        "tipo_fabricacion":    "tipo_fabricacion",
        "complejidad":         "complejidad",
    })
    df["codigo"]   = ""
    df["producto"] = ""
    df["fuente"]   = "sheet1"
    keep = ["familia", "subfamilia", "codigo", "producto",
            "handle", "url", "descripcion_web", "scrape_status",
            "importado_flag", "tipo_fabricacion", "complejidad", "fuente"]
    return df[[c for c in keep if c in df.columns]]


def load_sheet2(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={
        "familia":          "familia",
        "sub-familia":      "subfamilia",
        "CÓDIGO":           "codigo",
        "PRODUCTO":         "producto",
        "IMPORTADO":        "importado_flag",
        "tipo_fabricacion": "tipo_fabricacion",
        "complejidad":      "complejidad",
    })
    df["handle"]         = ""
    df["url"]            = ""
    df["descripcion_web"]= ""
    df["scrape_status"]  = "n/a"
    df["fuente"]         = "sheet2"
    keep = ["familia", "subfamilia", "codigo", "producto",
            "handle", "url", "descripcion_web", "scrape_status",
            "importado_flag", "tipo_fabricacion", "complejidad", "fuente"]
    return df[[c for c in keep if c in df.columns]]


def main():
    for f in (SHEET1, SHEET2):
        if not os.path.exists(f):
            print(f"ERROR: {f} not found.")
            sys.exit(1)

    s1 = load_sheet1(SHEET1)
    s2 = load_sheet2(SHEET2)

    master = pd.concat([s1, s2], ignore_index=True)

    for col in ("subfamilia", "tipo_fabricacion", "complejidad",
                "descripcion_web", "codigo", "producto", "handle", "familia"):
        master[col] = master[col].fillna("").astype(str).str.strip()

    master.to_csv(OUTPUT, index=False)

    total   = len(master)
    fab     = (master["tipo_fabricacion"] == "fabricado").sum()
    resell  = (master["tipo_fabricacion"] == "importado-resell").sum()
    mat     = (master["tipo_fabricacion"] == "importado-material").sum()
    revisar = (master["tipo_fabricacion"] == "importado-revisar").sum()
    unclass = (master["tipo_fabricacion"] == "").sum()

    print(f"=== Catálogo Maestro ===")
    print(f"Total filas        : {total}")
    print(f"  Sheet1 (web)     : {len(s1)}")
    print(f"  Sheet2 (bodega)  : {len(s2)}")
    print()
    print(f"--- tipo_fabricacion ---")
    print(f"  fabricado          : {fab:>4}  ({fab/total*100:.1f}%)")
    print(f"  importado-resell   : {resell:>4}  ({resell/total*100:.1f}%)")
    print(f"  importado-material : {mat:>4}  ({mat/total*100:.1f}%)")
    print(f"  importado-revisar  : {revisar:>4}  ({revisar/total*100:.1f}%)")
    print(f"  sin clasificar     : {unclass:>4}  ({unclass/total*100:.1f}%)")
    print()
    print(f"--- complejidad (fabricados) ---")
    fab_df = master[master["tipo_fabricacion"].isin(["fabricado","importado-material"])]
    print(fab_df["complejidad"].value_counts().to_string())
    print()
    print(f"--- familias ({master['familia'].nunique()} distintas) ---")
    print(master["familia"].value_counts().head(20).to_string())
    print()
    print(f"Guardado en: {OUTPUT}")


if __name__ == "__main__":
    main()
