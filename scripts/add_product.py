"""
add_product.py — Insert a new product from a drawing extraction JSON into products.db
=======================================================================================
Validates the extraction schema, recomputes G/D from PROCESS_RULES.json thresholds
(never trusts agent-computed values), checks profile and complexity validity,
then inserts into the `products` table and records a `categorization_history` entry.

Usage:
  # Insert from a JSON file:
  python3 scripts/add_product.py --file extracted/tina-quesera-200l.json

  # Insert from stdin (pipe from drawing-extractor agent):
  cat extracted.json | python3 scripts/add_product.py --stdin

  # Dry-run (validate only, no DB write):
  python3 scripts/add_product.py --file extracted.json --dry-run

  # List all products added via this tool:
  python3 scripts/add_product.py --list

JSON schema (drawing-extract-v1):
  See .claude/agents/drawing-extractor.md for the full schema.
  Minimum required fields:
    producto.handle, producto.nombre
    dimensiones.dim_espesor_mm  (or dim_diameter_mm for cylindrical)
    clasificacion.perfil_proceso, clasificacion.complejidad
    clasificacion.razon_perfil, clasificacion.razon_complejidad
"""

import json
import sqlite3
import argparse
import sys
import re
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT         = Path(__file__).resolve().parent.parent
DB           = ROOT / "dataset" / "products.db"
RULES_FILE   = ROOT / "files-process" / "PROCESS_RULES.json"

# ─── Load rules ───────────────────────────────────────────────────────────────

def load_rules() -> dict:
    try:
        return json.loads(RULES_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️  Cannot load PROCESS_RULES.json: {e}")
        return {}

RULES = load_rules()

# ─── Driver computation (source of truth = PROCESS_RULES.json) ───────────────

def compute_G(l_mm, w_mm) -> int | None:
    if l_mm is None or w_mm is None:
        return None
    area = l_mm * w_mm
    if not RULES:
        lo, hi = 500_000, 1_500_000
    else:
        lo, hi = RULES["driver_thresholds"]["G"]["breakpoints_mm2"]
    return 1 if area < lo else (2 if area < hi else 3)

def compute_D(espesor_mm) -> int | None:
    if espesor_mm is None:
        return None
    if not RULES:
        lo, hi = 1.5, 2.0
    else:
        lo, hi = RULES["driver_thresholds"]["D"]["breakpoints_mm"]
    return 1 if espesor_mm <= lo else (2 if espesor_mm <= hi else 3)

# ─── Validation ───────────────────────────────────────────────────────────────

VALID_COMPLEJIDADES = {"C1", "C2", "C3"}

class ValidationError(Exception):
    pass

def validate(data: dict, rules: dict) -> dict:
    """
    Validate extraction JSON. Returns a cleaned, DB-ready dict.
    Raises ValidationError with a clear message on any failure.
    """
    errors = []

    # ── Schema version ────────────────────────────────────────────────────────
    schema = data.get("_schema", "")
    if not schema.startswith("dulox-drawing-extract"):
        errors.append(f"_schema must start with 'dulox-drawing-extract', got: '{schema}'")

    # ── producto ──────────────────────────────────────────────────────────────
    prod = data.get("producto", {})
    handle = prod.get("handle", "").strip()
    nombre = prod.get("nombre", "").strip()

    if not handle:
        errors.append("producto.handle is required")
    elif not re.match(r'^[a-z0-9][a-z0-9\-]+[a-z0-9]$', handle):
        errors.append(
            f"producto.handle must be lowercase slug (letters, digits, hyphens): got '{handle}'"
        )
    if not nombre:
        errors.append("producto.nombre is required")

    # ── dimensiones ───────────────────────────────────────────────────────────
    dims = data.get("dimensiones", {})

    def _float(key):
        v = dims.get(key)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            errors.append(f"dimensiones.{key} must be a number, got: {v!r}")
            return None

    l_mm   = _float("dim_l_mm")
    w_mm   = _float("dim_w_mm")
    h_mm   = _float("dim_h_mm")
    diam   = _float("dim_diameter_mm")
    esp    = _float("dim_espesor_mm")

    if esp is None and diam is None:
        errors.append(
            "At least one of dimensiones.dim_espesor_mm or dim_diameter_mm is required"
        )

    # ── clasificacion ─────────────────────────────────────────────────────────
    clas = data.get("clasificacion", {})
    perfil = clas.get("perfil_proceso", "").strip()
    comp   = clas.get("complejidad", "").strip()
    razon_perfil   = clas.get("razon_perfil", "").strip()
    razon_comp     = clas.get("razon_complejidad", "").strip()

    if not perfil:
        errors.append("clasificacion.perfil_proceso is required")
    elif rules and perfil not in rules.get("profiles", {}):
        valid = sorted(rules.get("profiles", {}).keys())
        errors.append(
            f"clasificacion.perfil_proceso '{perfil}' not in PROCESS_RULES.json. "
            f"Valid profiles: {valid}"
        )

    if not comp:
        errors.append("clasificacion.complejidad is required")
    elif comp not in VALID_COMPLEJIDADES:
        errors.append(f"clasificacion.complejidad must be C1/C2/C3, got: '{comp}'")
    elif rules and perfil in rules.get("profiles", {}):
        valid_levels = set(rules["profiles"][perfil].get("complexity_thresholds", {}).keys())
        if comp not in valid_levels:
            errors.append(
                f"Complejidad '{comp}' not defined for profile '{perfil}'. "
                f"Valid levels for this profile: {sorted(valid_levels)}"
            )

    if not razon_perfil:
        errors.append("clasificacion.razon_perfil is required (explain WHY this perfil)")
    if not razon_comp:
        errors.append("clasificacion.razon_complejidad is required (explain WHY this level)")

    if errors:
        raise ValidationError("\n".join(f"  ❌ {e}" for e in errors))

    # ── Recompute G and D from rules (override agent values) ──────────────────
    G = compute_G(l_mm, w_mm)
    D = compute_D(esp)
    k_num = {"C1": 1, "C2": 2, "C3": 3}[comp]

    # ── Warn if agent's G/D differ from recomputed ────────────────────────────
    agent_drivers = clas.get("drivers", {})
    agent_G = agent_drivers.get("G_score")
    agent_D = agent_drivers.get("D_score")
    warnings = []
    if agent_G is not None and G is not None and int(agent_G) != G:
        warnings.append(
            f"⚠️  Agent said G={agent_G}, recomputed G={G} — using recomputed value"
        )
    if agent_D is not None and D is not None and int(agent_D) != D:
        warnings.append(
            f"⚠️  Agent said D={agent_D}, recomputed D={D} — using recomputed value"
        )

    return {
        "clean": {
            "handle":          handle,
            "perfil_proceso":  perfil,
            "complejidad":     comp,
            "k_num":           k_num,
            "familia":         prod.get("familia", ""),
            "subfamilia":      prod.get("subfamilia", ""),
            "descripcion_web": prod.get("descripcion") or prod.get("nombre", ""),
            "url":             prod.get("url", ""),
            "dim_l_mm":        l_mm,
            "dim_w_mm":        w_mm,
            "dim_h_mm":        h_mm,
            "dim_diameter_mm": diam,
            "dim_espesor_mm":  esp,
            "dim_confidence":  dims.get("dim_confidence", "high"),
            "dim_notes":       dims.get("dim_notes", ""),
            "G":               G,
            "D":               D,
            "validated":       1,      # came from a real drawing — pre-validated
            "validated_by":    "drawing-extractor",
            "validated_at":    datetime.now().isoformat(),
        },
        "razon": f"Perfil: {razon_perfil} | Complejidad: {razon_comp}",
        "warnings": warnings,
        "agent_drivers": agent_drivers,
        "source_file": data.get("_source_file", "unknown"),
    }

# ─── DB operations ────────────────────────────────────────────────────────────

def check_duplicate(conn, handle: str) -> bool:
    row = conn.execute(
        "SELECT id FROM products WHERE handle = ?", (handle,)
    ).fetchone()
    return row is not None

def insert_product(conn, clean: dict, razon: str, source_file: str):
    now = datetime.now().isoformat()

    conn.execute("""
        INSERT INTO products
          (handle, perfil_proceso, complejidad, k_num,
           familia, subfamilia, descripcion_web, url,
           dim_l_mm, dim_w_mm, dim_h_mm, dim_diameter_mm,
           dim_espesor_mm, dim_confidence, dim_notes,
           G, D, validated, validated_by, validated_at, imported_at)
        VALUES
          (:handle, :perfil_proceso, :complejidad, :k_num,
           :familia, :subfamilia, :descripcion_web, :url,
           :dim_l_mm, :dim_w_mm, :dim_h_mm, :dim_diameter_mm,
           :dim_espesor_mm, :dim_confidence, :dim_notes,
           :G, :D, :validated, :validated_by, :validated_at, :imported_at)
    """, {**clean, "imported_at": now})

    conn.execute("""
        INSERT INTO categorization_history
          (handle, old_perfil, new_perfil, old_complejidad, new_complejidad,
           reason, changed_by, changed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        clean["handle"],
        None, clean["perfil_proceso"],
        None, clean["complejidad"],
        f"[drawing-extractor] {razon} | source: {source_file}",
        "drawing-extractor",
        now,
    ))

    conn.commit()

def update_product(conn, clean: dict, razon: str, source_file: str):
    """Update an existing product's dimensions + re-classification."""
    now = datetime.now().isoformat()

    # Get current values for history
    old = conn.execute(
        "SELECT perfil_proceso, complejidad FROM products WHERE handle = ?",
        (clean["handle"],)
    ).fetchone()

    conn.execute("""
        UPDATE products SET
            perfil_proceso=:perfil_proceso, complejidad=:complejidad, k_num=:k_num,
            familia=:familia, subfamilia=:subfamilia,
            descripcion_web=:descripcion_web,
            dim_l_mm=:dim_l_mm, dim_w_mm=:dim_w_mm, dim_h_mm=:dim_h_mm,
            dim_diameter_mm=:dim_diameter_mm, dim_espesor_mm=:dim_espesor_mm,
            dim_confidence=:dim_confidence, dim_notes=:dim_notes,
            G=:G, D=:D,
            validated=1, validated_by=:validated_by, validated_at=:validated_at
        WHERE handle=:handle
    """, clean)

    conn.execute("""
        INSERT INTO categorization_history
          (handle, old_perfil, new_perfil, old_complejidad, new_complejidad,
           reason, changed_by, changed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        clean["handle"],
        old[0] if old else None, clean["perfil_proceso"],
        old[1] if old else None, clean["complejidad"],
        f"[drawing-extractor update] {razon} | source: {source_file}",
        "drawing-extractor",
        now,
    ))

    conn.commit()

# ─── Report ───────────────────────────────────────────────────────────────────

def print_summary(validated: dict, action: str):
    c = validated["clean"]
    print(f"\n{'─'*60}")
    print(f"  Handle:     {c['handle']}")
    print(f"  Nombre:     {c['descripcion_web'][:60]}")
    print(f"  Perfil:     {c['perfil_proceso']}   Complejidad: {c['complejidad']}  (k={c['k_num']})")
    print(f"  Dims:       L={c['dim_l_mm']}  W={c['dim_w_mm']}  H={c['dim_h_mm']}  "
          f"Ø={c['dim_diameter_mm']}  esp={c['dim_espesor_mm']}mm")
    print(f"  Drivers:    G={c['G']}  D={c['D']}")
    print(f"  Source:     {validated['source_file']}")
    if validated["warnings"]:
        for w in validated["warnings"]:
            print(f"  {w}")
    print(f"  Razon:      {validated['razon'][:100]}")
    print(f"{'─'*60}")
    print(f"  → {action}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Insert drawing extraction into products.db")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--file",  help="Path to extraction JSON file")
    group.add_argument("--stdin", action="store_true", help="Read JSON from stdin")
    group.add_argument("--list",  action="store_true",
                       help="List products added via drawing-extractor")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate only — do not write to DB")
    parser.add_argument("--force-update", action="store_true",
                        help="Update if handle already exists (default: skip)")
    args = parser.parse_args()

    # ── List mode ─────────────────────────────────────────────────────────────
    if args.list:
        conn = sqlite3.connect(DB)
        rows = conn.execute("""
            SELECT p.handle, p.perfil_proceso, p.complejidad, p.validated_at, h.reason
            FROM products p
            LEFT JOIN categorization_history h ON h.handle = p.handle
              AND h.changed_by = 'drawing-extractor'
            WHERE p.validated_by = 'drawing-extractor'
            ORDER BY p.validated_at DESC
        """).fetchall()
        conn.close()
        if not rows:
            print("No products added via drawing-extractor yet.")
            return
        print(f"\n{'Handle':50s} {'Perfil':20s} {'Comp':4s} {'Date':20s}")
        print("─" * 100)
        for h, p, c, d, r in rows:
            print(f"{h[:50]:50s} {p:20s} {c:4s} {(d or '')[:19]:20s}")
        return

    # ── Load JSON ─────────────────────────────────────────────────────────────
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"❌ File not found: {path}")
            sys.exit(1)
        data = json.loads(path.read_text(encoding="utf-8"))
    elif args.stdin:
        data = json.loads(sys.stdin.read())
    else:
        parser.print_help()
        sys.exit(1)

    # ── Validate ──────────────────────────────────────────────────────────────
    print(f"\nValidating extraction JSON…")
    try:
        validated = validate(data, RULES)
    except ValidationError as e:
        print(f"\n❌ Validation failed:\n{e}")
        sys.exit(1)

    print("✅ Validation passed")

    if args.dry_run:
        print_summary(validated, "DRY RUN — no changes written")
        return

    # ── DB write ──────────────────────────────────────────────────────────────
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL")
    handle = validated["clean"]["handle"]

    if check_duplicate(conn, handle):
        if args.force_update:
            print_summary(validated, f"Updating existing product: {handle}")
            update_product(conn, validated["clean"], validated["razon"], validated["source_file"])
            print(f"✅ Updated in {DB.name}")
        else:
            print_summary(validated,
                f"⚠️  Handle '{handle}' already exists in DB. "
                f"Use --force-update to overwrite.")
            conn.close()
            sys.exit(0)
    else:
        print_summary(validated, f"Inserting new product: {handle}")
        insert_product(conn, validated["clean"], validated["razon"], validated["source_file"])
        print(f"\n✅ Inserted into {DB.name}")
        print(f"   Run `python3 scripts/audit_model.py --test outliers` to check classification.")

    conn.close()

if __name__ == "__main__":
    main()
