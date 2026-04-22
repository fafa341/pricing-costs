"""
bootstrap_chunks.py — Generate Layer 1 + Layer 2 knowledge chunks from PROCESS_RULES.json
===========================================================================================
Two kinds of chunks are generated:

  Layer 1 (physical):
    - driver_thresholds — the G/D/C breakpoint rules
    - process_assignment — which processes run at each (profile × level)
    - x_flag_definition  — what each X flag means and how many points it contributes
    - complexity_threshold — the point-range → level mapping for each profile

  Layer 2 (semantic):
    - semantic_mapping — term → concept mappings from semantic_mappings.json

All generated chunks are tagged:
  verified: false  ← these are STRUCTURAL claims, not empirically measured
  confianza: "estructural"

They still count toward ICM Layer 1 score as "model declared" knowledge —
but require a calibration session to upgrade to verified=true.

Run:
  python3 scripts/bootstrap_chunks.py          # append new chunks only
  python3 scripts/bootstrap_chunks.py --reset  # wipe and regenerate all
"""

import json
import sys
import uuid
from datetime import date
from pathlib import Path

ROOT         = Path(__file__).resolve().parent.parent
RULES_PATH   = ROOT / "files-process" / "PROCESS_RULES.json"
SEMANTIC_PATH = ROOT / "files-process" / "semantic_mappings.json"
CHUNKS_PATH  = ROOT / "files-process" / "process-measurements" / "knowledge-chunks.jsonl"


def load_rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def load_chunks() -> list[dict]:
    if not CHUNKS_PATH.exists():
        return []
    return [json.loads(l) for l in CHUNKS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def save_chunks(chunks: list[dict]):
    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHUNKS_PATH.write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + "\n",
        encoding="utf-8"
    )


def mk_id(tag: str) -> str:
    return f"bootstrap-{tag}-{date.today().isoformat()}"


# ─── Layer 1 generators ────────────────────────────────────────────────────────

def gen_driver_threshold_chunks(rules: dict) -> list[dict]:
    """One chunk per driver (G, D, C) documenting the breakpoints."""
    chunks = []
    dt = rules.get("driver_thresholds", {})

    g_bp = dt.get("G", {}).get("breakpoints_mm2", [500_000, 1_500_000])
    chunks.append({
        "chunk_id": mk_id("driver-G"),
        "texto": (
            f"Driver G (Geometría): el área proyectada L×W determina el score G. "
            f"G=1 si área < {g_bp[0]:,} mm², G=2 si entre {g_bp[0]:,}–{g_bp[1]:,} mm², "
            f"G=3 si área > {g_bp[1]:,} mm² (≈{g_bp[1]/1e6:.1f} m²). "
            f"Para piezas cilíndricas se usa Ø×Ø como área proyectada."
        ),
        "texto_embedding": (
            f"driver G geometria area mm2 breakpoints {g_bp[0]} {g_bp[1]} score 1 2 3"
        ),
        "metadata": {
            "layer": "physical", "tipo_umbral": "driver_breakpoints",
            "proceso": "clasificacion", "driver": "G",
            "tipo_dimension": "area_mm2",
            "valor_umbral": g_bp[0], "unidad_umbral": "mm2",
            "nivel_complejidad": "todos",
            "confianza": "estructural", "verified": False,
            "valid_from": str(date.today()), "valid_until": None,
            "superseded_by": None, "drivers_cited": ["G"],
            "fuente": "PROCESS_RULES.json", "fuente_id": "bootstrap",
            "fecha_sesion": str(date.today()),
            "perfil_proceso": "todos",
            "etiquetas": ["driver_G", "geometria", "area", "umbral"],
        }
    })

    d_bp = dt.get("D", {}).get("breakpoints_mm", [1.5, 2.0])
    chunks.append({
        "chunk_id": mk_id("driver-D"),
        "texto": (
            f"Driver D (Espesor/Densidad): el espesor de la plancha determina el score D. "
            f"D=1 si espesor ≤ {d_bp[0]}mm, D=2 si {d_bp[0]}–{d_bp[1]}mm, D=3 si > {d_bp[1]}mm. "
            f"Planchas de 1mm son estándar (D=1). Planchas de 2mm+ son categoría pesada (D=3)."
        ),
        "texto_embedding": (
            f"driver D espesor plancha mm breakpoints {d_bp[0]} {d_bp[1]} score 1 2 3"
        ),
        "metadata": {
            "layer": "physical", "tipo_umbral": "driver_breakpoints",
            "proceso": "clasificacion", "driver": "D",
            "tipo_dimension": "espesor_mm",
            "valor_umbral": d_bp[0], "unidad_umbral": "mm",
            "nivel_complejidad": "todos",
            "confianza": "estructural", "verified": False,
            "valid_from": str(date.today()), "valid_until": None,
            "superseded_by": None, "drivers_cited": ["D"],
            "fuente": "PROCESS_RULES.json", "fuente_id": "bootstrap",
            "fecha_sesion": str(date.today()),
            "perfil_proceso": "todos",
            "etiquetas": ["driver_D", "espesor", "plancha", "umbral"],
        }
    })

    c_bp = dt.get("C", {}).get("breakpoints", [3, 7])
    chunks.append({
        "chunk_id": mk_id("driver-C"),
        "texto": (
            f"Driver C (Componentes): el conteo del C-driver específico del perfil determina el score C. "
            f"C=1 si valor ≤ {c_bp[0]}, C=2 si {c_bp[0]}–{c_bp[1]}, C=3 si > {c_bp[1]}. "
            f"El C-driver varía por perfil: num_quemadores en cocinas, num_tazas en lavaderos, "
            f"num_niveles en carros bandejeros."
        ),
        "texto_embedding": (
            f"driver C componentes conteo breakpoints {c_bp[0]} {c_bp[1]} score 1 2 3 perfil"
        ),
        "metadata": {
            "layer": "physical", "tipo_umbral": "driver_breakpoints",
            "proceso": "clasificacion", "driver": "C",
            "tipo_dimension": "conteo",
            "valor_umbral": c_bp[0], "unidad_umbral": "conteo",
            "nivel_complejidad": "todos",
            "confianza": "estructural", "verified": False,
            "valid_from": str(date.today()), "valid_until": None,
            "superseded_by": None, "drivers_cited": ["C"],
            "fuente": "PROCESS_RULES.json", "fuente_id": "bootstrap",
            "fecha_sesion": str(date.today()),
            "perfil_proceso": "todos",
            "etiquetas": ["driver_C", "componentes", "conteo", "umbral"],
        }
    })
    return chunks


def gen_profile_chunks(rules: dict) -> list[dict]:
    """
    For each (profile × complexity level) with non-empty process_tiers:
      - One chunk for process assignment
      - One chunk for complexity threshold (point range)
    For each profile's X flags:
      - One chunk per x_flag definition
    """
    chunks = []
    templates   = rules.get("process_templates", {})
    consumables = rules.get("process_consumables", {})

    for pkey, prof in rules.get("profiles", {}).items():
        primary   = prof.get("primary_drivers", [])
        secondary = prof.get("secondary_drivers", [])
        all_d     = list(dict.fromkeys(primary + secondary))
        c_driver  = prof.get("c_driver")
        tiers     = prof.get("process_tiers", {})
        thresholds = prof.get("complexity_thresholds", {})
        x_flags   = prof.get("x_flags", {})
        desc      = prof.get("description", "")

        # ── Complexity threshold chunk ──────────────────────────────────────────
        if thresholds:
            thresh_txt = "; ".join(
                f"{lvl}: {v.get('min_points',0)}–{v.get('max_points',99)} pts ({v.get('description','')})"
                for lvl, v in sorted(thresholds.items())
            )
            chunks.append({
                "chunk_id": mk_id(f"thresholds-{pkey}"),
                "texto": (
                    f"Perfil {pkey}: umbrales de complejidad por puntos G+D+C+X. "
                    f"{thresh_txt}. "
                    f"Drivers primarios: {', '.join(primary)}. "
                    f"Driver C: {c_driver or 'no aplica'}. {desc}"
                ),
                "texto_embedding": (
                    f"umbrales complejidad perfil {pkey} C1 C2 C3 puntos "
                    f"{' '.join(all_d)} {c_driver or ''}"
                ),
                "metadata": {
                    "layer": "physical", "tipo_umbral": "complexity_thresholds",
                    "proceso": "clasificacion", "driver": ",".join(all_d),
                    "perfil_proceso": pkey,
                    "nivel_complejidad": "todos",
                    "confianza": "estructural", "verified": False,
                    "valid_from": str(date.today()), "valid_until": None,
                    "superseded_by": None, "drivers_cited": all_d,
                    "fuente": "PROCESS_RULES.json", "fuente_id": "bootstrap",
                    "fecha_sesion": str(date.today()),
                    "etiquetas": [pkey, "umbrales", "clasificacion"] + all_d,
                }
            })

        # ── Process assignment chunks (one per non-empty tier) ──────────────────
        for lvl, procs in sorted(tiers.items()):
            if not procs:
                continue
            # Build time summary from templates
            time_parts = []
            cons_parts = []
            for proc in procs:
                tmpl = templates.get(proc, {}).get(lvl, {})
                t_s  = tmpl.get("T_setup_min", 0)
                t_e  = tmpl.get("T_exec_min", 0)
                n_op = tmpl.get("n_ops", 1)
                if t_e:
                    time_parts.append(f"{proc}: setup {t_s}min + exec {t_e}min × {n_op}op")
                cons_lvl = consumables.get(proc, {}).get(lvl, [])
                for r in cons_lvl:
                    cons_parts.append(f"{r.get('Producto','?')} {r.get('Cantidad',0)}{r.get('Unidad','u')} ${r.get('Precio_u',0)}")

            time_txt = "; ".join(time_parts) if time_parts else "sin templates ingresados"
            cons_txt = "; ".join(cons_parts[:6]) if cons_parts else "sin consumibles ingresados"

            chunks.append({
                "chunk_id": mk_id(f"assign-{pkey}-{lvl}"),
                "texto": (
                    f"Perfil {pkey} nivel {lvl}: procesos activos = {', '.join(procs)}. "
                    f"Tiempos: {time_txt}. "
                    f"Consumibles estándar: {cons_txt}."
                ),
                "texto_embedding": (
                    f"procesos asignados perfil {pkey} nivel {lvl} "
                    f"{' '.join(procs)} tiempos consumibles"
                ),
                "metadata": {
                    "layer": "physical", "tipo_umbral": "process_assignment",
                    "proceso": "multi", "driver": ",".join(all_d),
                    "perfil_proceso": pkey,
                    "nivel_complejidad": lvl,
                    "tipo_impacto": "procesos",
                    "confianza": "estructural", "verified": False,
                    "valid_from": str(date.today()), "valid_until": None,
                    "superseded_by": None, "drivers_cited": all_d,
                    "fuente": "PROCESS_RULES.json", "fuente_id": "bootstrap",
                    "fecha_sesion": str(date.today()),
                    "etiquetas": [pkey, lvl, "process_assignment"] + procs,
                }
            })

        # ── X flag definition chunks ────────────────────────────────────────────
        for flag_key, flag_def in x_flags.items():
            scope = flag_def.get("process_scope", [])
            scope_txt = f"Afecta solo a: {', '.join(scope)}." if scope else "Afecta todos los procesos con driver X."
            chunks.append({
                "chunk_id": mk_id(f"xflag-{pkey}-{flag_key}"),
                "texto": (
                    f"Característica X '{flag_def.get('label', flag_key)}' del perfil {pkey}: "
                    f"+{flag_def.get('points', 1)} puntos al score de complejidad. "
                    f"{flag_def.get('description', '')} {scope_txt}"
                ),
                "texto_embedding": (
                    f"caracteristica X flag {flag_key} {flag_def.get('label','')} "
                    f"puntos {flag_def.get('points',1)} perfil {pkey} {' '.join(scope)}"
                ),
                "metadata": {
                    "layer": "physical", "tipo_umbral": "x_flag_definition",
                    "proceso": "clasificacion", "driver": "X",
                    "perfil_proceso": pkey,
                    "nivel_complejidad": "todos",
                    "tipo_impacto": "score",
                    "confianza": "estructural", "verified": False,
                    "valid_from": str(date.today()), "valid_until": None,
                    "superseded_by": None, "drivers_cited": ["X"],
                    "fuente": "PROCESS_RULES.json", "fuente_id": "bootstrap",
                    "fecha_sesion": str(date.today()),
                    "etiquetas": [pkey, "x_flag", flag_key],
                    "x_flag_key": flag_key,
                    "x_flag_points": flag_def.get("points", 1),
                    "x_flag_scope": scope,
                }
            })

    return chunks


# ─── Layer 2 generator ─────────────────────────────────────────────────────────

def gen_semantic_chunks(semantic: dict) -> list[dict]:
    """One chunk per term→concept mapping in semantic_mappings.json."""
    chunks = []
    for mapping in semantic.get("mappings", []):
        term    = mapping.get("term", "")
        concept = mapping.get("concept", "")
        concept_type = mapping.get("concept_type", "")
        perfil  = mapping.get("perfil_proceso", "todos")
        pts     = mapping.get("points")
        expert  = mapping.get("expert_id", "unknown")
        verified = mapping.get("verified", False)
        version  = mapping.get("semantic_version", "v2026")

        pts_txt = f" (+{pts} pts)" if pts else ""
        chunks.append({
            "chunk_id": mk_id(f"sem-{concept_type}-{concept}"),
            "texto": (
                f"Mapeo semántico [{version}]: '{term}' → {concept}{pts_txt}. "
                f"Tipo: {concept_type}. Perfil: {perfil}. "
                f"{'Verificado por ' + expert + '.' if verified else 'No verificado (sorry).'} "
                f"{mapping.get('notes', '')}"
            ),
            "texto_embedding": (
                f"mapeo semantico termino {term} concepto {concept} "
                f"perfil {perfil} {concept_type} {version}"
            ),
            "metadata": {
                "layer": "semantic",
                "semantic_version": version,
                "expert_id": expert,
                "verified": verified,
                "valid_from": mapping.get("valid_from", str(date.today())),
                "valid_until": mapping.get("valid_until"),
                "superseded_by": None,
                "drivers_cited": mapping.get("drivers_cited", []),
                "proceso": "clasificacion",
                "driver": ",".join(mapping.get("drivers_cited", [])) or "—",
                "perfil_proceso": perfil,
                "nivel_complejidad": "todos",
                "tipo_umbral": "semantic_mapping",
                "confianza": "verificado" if verified else "sorry",
                "fuente": "semantic_mappings.json", "fuente_id": "bootstrap",
                "fecha_sesion": str(date.today()),
                "etiquetas": ["semantico", concept_type, concept, perfil],
                # Semantic-specific fields
                "sem_term": term,
                "sem_concept": concept,
                "sem_concept_type": concept_type,
            }
        })
    return chunks


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    reset = "--reset" in sys.argv
    rules    = load_rules()
    semantic = json.loads(SEMANTIC_PATH.read_text(encoding="utf-8")) if SEMANTIC_PATH.exists() else {"mappings": []}

    print(f"Bootstrapping knowledge chunks from PROCESS_RULES.json + semantic_mappings.json")
    print(f"Mode: {'RESET (wipe all bootstrap chunks)' if reset else 'APPEND new only'}")
    print()

    new_chunks: list[dict] = []
    new_chunks += gen_driver_threshold_chunks(rules)
    new_chunks += gen_profile_chunks(rules)
    new_chunks += gen_semantic_chunks(semantic)
    print(f"  Generated: {len(new_chunks)} chunks")
    print(f"    Layer 1 (physical): {sum(1 for c in new_chunks if c['metadata'].get('layer')=='physical')}")
    print(f"    Layer 2 (semantic): {sum(1 for c in new_chunks if c['metadata'].get('layer')=='semantic')}")

    existing = [] if reset else load_chunks()
    existing_bootstrap_ids = {c["chunk_id"] for c in existing if c["chunk_id"].startswith("bootstrap-")}
    new_bootstrap_ids      = {c["chunk_id"] for c in new_chunks}

    if reset:
        # Keep only non-bootstrap (empirical) chunks, then add all new
        empirical = [c for c in load_chunks() if not c["chunk_id"].startswith("bootstrap-")]
        final = empirical + new_chunks
        print(f"  Kept {len(empirical)} empirical chunks, replaced all bootstrap chunks")
    else:
        # Remove old bootstrap chunks with same IDs, add new ones
        kept     = [c for c in existing if c["chunk_id"] not in new_bootstrap_ids]
        final    = kept + new_chunks
        replaced = len(existing) - len(kept)
        print(f"  Replaced {replaced} existing bootstrap chunks, kept {len(kept)} empirical")

    save_chunks(final)
    print(f"\nTotal chunks written: {len(final)}")
    print(f"File: {CHUNKS_PATH}")

    # Summary by type
    by_type: dict[str, int] = {}
    for c in final:
        t = c["metadata"].get("tipo_umbral", "other")
        by_type[t] = by_type.get(t, 0) + 1
    print("\nBy type:")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t:35s}  {n}")


if __name__ == "__main__":
    main()
