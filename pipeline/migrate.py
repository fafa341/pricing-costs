"""
migrate.py — CSV → SQLite migration for Dulox product catalog
==============================================================
Creates/updates dataset/products.db from dataset/Productos_Clasificaciones.csv

Tables:
  products               — all fabricado products + computed driver scores
  categorization_history — audit trail for every reclassification
  validation_sessions    — when a human reviewed a product

Usage:
  python3 scripts/migrate.py           # full migration (wipes + reloads products table)
  python3 scripts/migrate.py --sync    # upsert only (preserves categorization_history)
"""

import sqlite3
import pandas as pd
import numpy as np
import argparse
from pathlib import Path
from datetime import datetime

ROOT   = Path(__file__).resolve().parent.parent
CSV    = ROOT / "data" / "Productos_Clasificaciones.csv"
DB     = ROOT / "data" / "products.db"

# ─── Driver computation ───────────────────────────────────────────────────────

def compute_G(row):
    """Area score: L × W en mm²  →  1/2/3"""
    l = pd.to_numeric(row.get("dim_l_mm"), errors="coerce")
    w = pd.to_numeric(row.get("dim_w_mm"), errors="coerce")
    if pd.isna(l) or pd.isna(w) or l <= 0 or w <= 0:
        return None
    area = l * w
    if area < 500_000:    return 1
    if area < 1_500_000:  return 2
    return 3

def compute_D(row):
    """Espesor score: ≤1.5→1, ≤2→2, >2→3"""
    e = pd.to_numeric(row.get("dim_espesor_mm"), errors="coerce")
    if pd.isna(e) or e <= 0:
        return None
    if e <= 1.5: return 1
    if e <= 2.0: return 2
    return 3

def complexity_num(k):
    return {"C1": 1, "C2": 2, "C3": 3}.get(str(k))

# ─── Schema ───────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    handle              TEXT UNIQUE NOT NULL,
    perfil_proceso      TEXT,
    complejidad         TEXT,
    k_num               INTEGER,          -- 1/2/3 for C1/C2/C3
    familia             TEXT,
    subfamilia          TEXT,
    descripcion_web     TEXT,
    url                 TEXT,
    dim_l_mm            REAL,
    dim_w_mm            REAL,
    dim_h_mm            REAL,
    dim_diameter_mm     REAL,
    dim_espesor_mm      REAL,
    dim_confidence      TEXT,
    dim_notes           TEXT,
    G                   INTEGER,          -- geometry driver score 1-3
    D                   INTEGER,          -- density driver score 1-3
    validated           INTEGER DEFAULT 0, -- 1 = human reviewed
    validated_by        TEXT,
    validated_at        TEXT,
    imported_at         TEXT
);

CREATE TABLE IF NOT EXISTS categorization_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    handle              TEXT NOT NULL,
    old_perfil          TEXT,
    new_perfil          TEXT,
    old_complejidad     TEXT,
    new_complejidad     TEXT,
    reason              TEXT,
    changed_by          TEXT DEFAULT 'system',
    changed_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_date        TEXT NOT NULL,
    reviewed_by         TEXT,
    products_reviewed   INTEGER DEFAULT 0,
    products_changed    INTEGER DEFAULT 0,
    notes               TEXT
);
"""

# ─── Migration ────────────────────────────────────────────────────────────────

def load_csv():
    df = pd.read_csv(CSV, low_memory=False)
    fab = df[df["importado_final"] == "NO"].copy()
    fab["G"]     = fab.apply(compute_G, axis=1)
    fab["D"]     = fab.apply(compute_D, axis=1)
    fab["k_num"] = fab["complejidad"].map(complexity_num)
    return fab

def migrate_full(conn, fab):
    """Wipe and reload the products table. Preserves categorization_history."""
    now = datetime.now().isoformat()
    conn.execute("DELETE FROM products")

    rows = []
    for _, row in fab.iterrows():
        rows.append({
            "handle":          row.get("Product: Handle"),
            "perfil_proceso":  row.get("perfil_proceso"),
            "complejidad":     row.get("complejidad"),
            "k_num":           row.get("k_num") if not pd.isna(row.get("k_num", None) or np.nan) else None,
            "familia":         row.get("familia"),
            "subfamilia":      row.get("subfamilia"),
            "descripcion_web": row.get("descripcion_web"),
            "url":             row.get("url"),
            "dim_l_mm":        row.get("dim_l_mm") if not pd.isna(row.get("dim_l_mm", None) or np.nan) else None,
            "dim_w_mm":        row.get("dim_w_mm") if not pd.isna(row.get("dim_w_mm", None) or np.nan) else None,
            "dim_h_mm":        row.get("dim_h_mm") if not pd.isna(row.get("dim_h_mm", None) or np.nan) else None,
            "dim_diameter_mm": row.get("dim_diameter_mm") if not pd.isna(row.get("dim_diameter_mm", None) or np.nan) else None,
            "dim_espesor_mm":  row.get("dim_espesor_mm") if not pd.isna(row.get("dim_espesor_mm", None) or np.nan) else None,
            "dim_confidence":  row.get("dim_confidence"),
            "dim_notes":       row.get("dim_notes"),
            "G":               int(row["G"]) if row.get("G") is not None and not pd.isna(row["G"]) else None,
            "D":               int(row["D"]) if row.get("D") is not None and not pd.isna(row["D"]) else None,
            "validated":       0,
            "imported_at":     now,
        })

    conn.executemany("""
        INSERT INTO products
          (handle, perfil_proceso, complejidad, k_num, familia, subfamilia,
           descripcion_web, url, dim_l_mm, dim_w_mm, dim_h_mm, dim_diameter_mm,
           dim_espesor_mm, dim_confidence, dim_notes, G, D, validated, imported_at)
        VALUES
          (:handle, :perfil_proceso, :complejidad, :k_num, :familia, :subfamilia,
           :descripcion_web, :url, :dim_l_mm, :dim_w_mm, :dim_h_mm, :dim_diameter_mm,
           :dim_espesor_mm, :dim_confidence, :dim_notes, :G, :D, :validated, :imported_at)
    """, rows)

    conn.commit()
    return len(rows)

def migrate_sync(conn, fab):
    """Upsert: add new products, update dimensions/drivers for existing ones.
    Never touches perfil_proceso / complejidad / validated fields on existing rows."""
    now = datetime.now().isoformat()
    updated = inserted = 0

    for _, row in fab.iterrows():
        handle = row.get("Product: Handle")
        existing = conn.execute(
            "SELECT id FROM products WHERE handle = ?", (handle,)
        ).fetchone()

        if existing:
            conn.execute("""
                UPDATE products SET
                    dim_l_mm=?, dim_w_mm=?, dim_h_mm=?, dim_diameter_mm=?,
                    dim_espesor_mm=?, dim_confidence=?, dim_notes=?, G=?, D=?
                WHERE handle=?
            """, (
                row.get("dim_l_mm") if not pd.isna(row.get("dim_l_mm", None) or np.nan) else None,
                row.get("dim_w_mm") if not pd.isna(row.get("dim_w_mm", None) or np.nan) else None,
                row.get("dim_h_mm") if not pd.isna(row.get("dim_h_mm", None) or np.nan) else None,
                row.get("dim_diameter_mm") if not pd.isna(row.get("dim_diameter_mm", None) or np.nan) else None,
                row.get("dim_espesor_mm") if not pd.isna(row.get("dim_espesor_mm", None) or np.nan) else None,
                row.get("dim_confidence"),
                row.get("dim_notes"),
                int(row["G"]) if row.get("G") is not None and not pd.isna(row["G"]) else None,
                int(row["D"]) if row.get("D") is not None and not pd.isna(row["D"]) else None,
                handle,
            ))
            updated += 1
        else:
            conn.execute("""
                INSERT INTO products
                  (handle, perfil_proceso, complejidad, k_num, familia, subfamilia,
                   descripcion_web, url, dim_l_mm, dim_w_mm, dim_h_mm, dim_diameter_mm,
                   dim_espesor_mm, dim_confidence, dim_notes, G, D, validated, imported_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)
            """, (
                handle,
                row.get("perfil_proceso"),
                row.get("complejidad"),
                int(row["k_num"]) if row.get("k_num") is not None and not pd.isna(row["k_num"]) else None,
                row.get("familia"),
                row.get("subfamilia"),
                row.get("descripcion_web"),
                row.get("url"),
                row.get("dim_l_mm") if not pd.isna(row.get("dim_l_mm", None) or np.nan) else None,
                row.get("dim_w_mm") if not pd.isna(row.get("dim_w_mm", None) or np.nan) else None,
                row.get("dim_h_mm") if not pd.isna(row.get("dim_h_mm", None) or np.nan) else None,
                row.get("dim_diameter_mm") if not pd.isna(row.get("dim_diameter_mm", None) or np.nan) else None,
                row.get("dim_espesor_mm") if not pd.isna(row.get("dim_espesor_mm", None) or np.nan) else None,
                row.get("dim_confidence"),
                row.get("dim_notes"),
                int(row["G"]) if row.get("G") is not None and not pd.isna(row["G"]) else None,
                int(row["D"]) if row.get("D") is not None and not pd.isna(row["D"]) else None,
                now,
            ))
            inserted += 1

    conn.commit()
    return inserted, updated

# ─── Export back to CSV ───────────────────────────────────────────────────────

def export_csv(conn):
    """Export current DB state back to CSV (for git / Excel compatibility)."""
    df = pd.read_sql("SELECT * FROM products ORDER BY perfil_proceso, complejidad, handle", conn)
    out = ROOT / "data" / "Productos_Clasificaciones_reviewed.csv"
    df.to_csv(out, index=False)
    print(f"✅ Exported {len(df)} products → {out.name}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync",   action="store_true", help="Upsert only — preserve manual categorizations")
    parser.add_argument("--export", action="store_true", help="Export DB → CSV after migration")
    args = parser.parse_args()

    print(f"Loading CSV: {CSV.name}")
    fab = load_csv()
    print(f"  {len(fab)} fabricado products loaded")

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)

    if args.sync:
        inserted, updated = migrate_sync(conn, fab)
        print(f"  Sync complete: {inserted} inserted, {updated} updated")
    else:
        n = migrate_full(conn, fab)
        print(f"  Full migration: {n} products written to {DB.name}")

    # Stats
    rows = conn.execute("SELECT perfil_proceso, complejidad, COUNT(*) FROM products GROUP BY 1,2 ORDER BY 1,2").fetchall()
    print(f"\nProducts per (perfil, complejidad):")
    cur_perfil = None
    for perfil, comp, cnt in rows:
        if perfil != cur_perfil:
            print(f"  {perfil}")
            cur_perfil = perfil
        print(f"    {comp}: {cnt}")

    g_coverage = conn.execute("SELECT COUNT(*) FROM products WHERE G IS NOT NULL").fetchone()[0]
    d_coverage = conn.execute("SELECT COUNT(*) FROM products WHERE D IS NOT NULL").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    print(f"\nDriver coverage: G={g_coverage}/{total} ({100*g_coverage//total}%)  D={d_coverage}/{total} ({100*d_coverage//total}%)")

    if args.export:
        export_csv(conn)

    conn.close()
    print(f"\n✅ Done — {DB}")

if __name__ == "__main__":
    main()
