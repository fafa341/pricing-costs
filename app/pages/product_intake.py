"""
Product Intake from Drawing
============================
Full pipeline: upload engineering drawing → Claude Vision extracts technical data
→ Python scores G/D from PROCESS_RULES.json → review + edit classification
→ save to products.db.

This is the primary entry point for adding new products to the system.
Run: streamlit run scripts/review.py
"""

import io
import json
import base64
import os
import re
import sys
import numpy as np
from pathlib import Path
from datetime import datetime

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import anthropic

ROOT       = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "core"))
from db import load_rules, save_rules, get_sb, search_products, get_product, save_bom as _db_save_bom, handle_exists, log_change, load_material_prices
from bom_calc import compute_bom, erp_rows, DEFAULT_GLOBAL_PRICES

MODEL = "claude-opus-4-5"

# ─── Driver computation (deterministic, from PROCESS_RULES.json) ─────────────

def compute_G(l_mm, w_mm, rules) -> int | None:
    if l_mm is None or w_mm is None:
        return None
    area = l_mm * w_mm
    lo, hi = rules["driver_thresholds"]["G"]["breakpoints_mm2"] if rules else [500_000, 1_500_000]
    return 1 if area < lo else (2 if area < hi else 3)

def compute_D(espesor_mm, rules) -> int | None:
    if espesor_mm is None:
        return None
    lo, hi = rules["driver_thresholds"]["D"]["breakpoints_mm"] if rules else [1.5, 2.0]
    return 1 if espesor_mm <= lo else (2 if espesor_mm <= hi else 3)

def compute_complexity_points(G, D, perfil, x_flags_active, c_valor, rules) -> tuple[int, dict]:
    """
    Returns (total_points, breakdown_dict) using PROCESS_RULES.json weights.
    breakdown shows each driver's contribution for display.
    """
    if not rules or perfil not in rules.get("profiles", {}):
        return 0, {}

    profile = rules["profiles"][perfil]
    primary = profile.get("primary_drivers", [])
    breakdown = {}
    total = 0

    if "G" in primary and G is not None:
        breakdown["G"] = G
        total += G
    if "D" in primary and D is not None:
        breakdown["D"] = D
        total += D
    if "D" not in primary and "G" not in primary:
        # Both are secondary — add lower weight
        if G is not None:
            breakdown["G (sec)"] = 1
            total += 1
        if D is not None:
            breakdown["D (sec)"] = 1
            total += 1

    # X flags
    x_defs = profile.get("x_flags", {})
    for flag in x_flags_active:
        if flag in x_defs:
            pts = x_defs[flag].get("points", 1)
            breakdown[f"X:{flag}"] = pts
            total += pts

    # C driver
    c_driver = profile.get("c_driver")
    if c_driver and c_valor is not None:
        # Map c_valor to a 1/2/3 score heuristically
        # (proper mapping would require per-profile thresholds — using sensible defaults)
        C_RANGES = {
            "num_quemadores":   [(2, 1), (6, 2), (99, 3)],
            "num_niveles":      [(2, 1), (5, 2), (99, 3)],
            "num_tazas":        [(1, 1), (2, 2), (99, 3)],
            "num_componentes":  [(2, 1), (4, 2), (99, 3)],
            "capacidad_litros": [(100, 1), (300, 2), (99999, 3)],
            "num_varillas":     [(10, 1), (25, 2), (99, 3)],
        }
        ranges = C_RANGES.get(c_driver, [(2, 1), (5, 2), (99, 3)])
        c_score = 1
        for threshold, score in ranges:
            if c_valor <= threshold:
                c_score = score
                break
        breakdown[f"C:{c_driver}={c_valor}"] = c_score
        total += c_score

    return total, breakdown

def points_to_complexity(total_points, perfil, rules) -> str | None:
    """Return the complexity level for a given total points score."""
    if not rules or perfil not in rules.get("profiles", {}):
        return None
    thresholds = rules["profiles"][perfil].get("complexity_thresholds", {})
    for level in ["C1", "C2", "C3"]:
        if level in thresholds:
            lo = thresholds[level]["min_points"]
            hi = thresholds[level]["max_points"]
            if lo <= total_points <= hi:
                return level
    # Fallback: highest available level if above all thresholds
    for level in reversed(["C1", "C2", "C3"]):
        if level in thresholds:
            return level
    return None

# ─── Claude Vision extraction ─────────────────────────────────────────────────

EXTRACTION_SYSTEM = """You are an expert engineering drawing analyst for Dulox (Ingeniería en Aceros Ltda),
a Chilean stainless steel fabrication workshop (AISI 304 / 304-L, food-grade and industrial equipment).

Extract ALL technical information from the provided engineering drawing.
Return ONLY valid JSON — no markdown, no preamble, no explanation.

Schema:
{
  "drawing_title": "string — equipment name/description from the drawing",
  "dimensions": {
    "l_mm": number or null,
    "w_mm": number or null,
    "h_mm": number or null,
    "diameter_mm": number or null,
    "espesor_mm": number or null,
    "confidence": "high|medium|low",
    "notes": "string — any uncertainty or multi-espesor notes"
  },
  "material": "string — e.g. AISI 304-L 1.5mm",
  "components": [
    {"nombre": "string", "material": "string or null", "cantidad": number, "dims_raw": "string"}
  ],
  "special_features": {
    "has_mechanism": boolean,
    "mechanism_type": "string or null — pedal/vaiven/corredera/bisagra",
    "has_mirror_finish": boolean,
    "multiple_compartments": boolean,
    "num_compartments": number or null,
    "has_electrical": boolean,
    "num_quemadores": number or null,
    "num_niveles": number or null,
    "num_tazas": number or null,
    "capacidad_litros": number or null,
    "has_wheels": boolean,
    "has_handle": boolean
  },
  "suggested_perfil": "string — one of: p-meson, p-basurero-cil, p-basurero-rect, p-campana, p-carro-bandejero, p-carro-traslado, p-cocina-gas, p-electrico, p-laminar-simple, p-cilindrico, p-laser, p-lavadero, p-modulo, p-rejilla, p-sumidero, p-tina, p-custom",
  "suggested_razon_perfil": "string — in Spanish, 2-3 sentences explaining WHY this perfil",
  "fabrication_notes": "string — any notes about fabrication visible in the drawing",
  "scale": "string or null — scale indicated, e.g. 1:20",
  "bom_materials": [
    {
      "Subconjunto": "string — component name in Spanish (e.g. 'Cuerpo principal', 'Tapa superior', 'Pata')",
      "Dimensiones": "string — raw dimensions from drawing (e.g. '2400×600mm', 'Ø120×800mm')",
      "Material": "string — full material spec (e.g. 'Plancha AISI 304-L 1.5mm', 'Tubo cuadrado 304 30×30×1.5mm', 'Varilla 304 Ø8mm')",
      "kg_ml": number — estimated quantity: kg for sheet/plate (area_m2 × espesor_m × 7930), meters for bar/tube, units for hardware,
      "precio_kg": number — standard CLP price: 3600 for AISI 304 sheet/kg, 5500 for tube/kg, 4200 for bar/kg, 1200 for hardware unit
    }
  ]
}

Rules for bom_materials calculation:
- AISI 304 / 304-L plancha (sheet): kg_ml = (L_m × W_m × espesor_m × 7930). precio_kg = 3600
- Tubo cuadrado/rectangular 304: kg_ml = (perímetro_m × espesor_pared_m × length_m × 7930). precio_kg = 5500
- Tubo redondo (caño) 304: kg_ml = (π × D_m × espesor_m × length_m × 7930). precio_kg = 5500
- Varilla / barra 304: kg_ml = length_m. precio_kg = 4200
- Patas / pies (tubos cortos): treat as tube sections, estimate from standard dimensions
- Hardware (bisagras, ruedas, manillas, tornillos): kg_ml = count of units. precio_kg = unit price estimate
- If dims are unclear or missing, set kg_ml = 0 and add a note in Dimensiones

Rules for suggested_perfil:
- p-cilindrico: cylindrical pieces (poruñas, baldes, recipientes) — cilindrado process is mandatory
- p-basurero-cil: cylindrical/semi-cylindrical waste bins — cilindrado + welded base
- p-basurero-rect: rectangular waste bins — plegado body
- p-campana: extraction hoods (murales or centrales)
- p-meson: work tables/counters — flat working surface
- p-lavadero: sinks/washbasins — one or more tazas
- p-tina: cheese vats or large tanks — cylindrical or rectangular, industrial capacity
- p-cocina-gas: gas cooktops/kitchens — has quemadores
- p-electrico: electric equipment — has resistencias/calefactores
- p-carro-bandejero: carts with multiple trays/levels
- p-laminar-simple: simple sheet metal pieces (covers, shelves, spacers)
- p-custom: custom fabrication without a standard profile

Preserve Spanish component names as they appear in the drawing.
Always populate bom_materials with at least the main body/sheet even if other data is sparse."""

def _load_rag_context(rules: dict, perfil_hint: str | None = None) -> str:
    """
    Build a RAG context block from verified knowledge chunks + anchor BOMs.
    Injected into the Vision system prompt so Claude can classify with real factory data.
    """
    lines = []

    # ── Verified knowledge chunks ──────────────────────────────────────────────
    chunks_path = ROOT / "docs" / "calibration" / "process-measurements" / "knowledge-chunks.jsonl"
    if chunks_path.exists():
        raw = [json.loads(l) for l in chunks_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        # verified = measured or explicitly flagged
        verified = [c for c in raw if
                    c.get("metadata", {}).get("verified", False) or
                    c.get("metadata", {}).get("confianza") == "medido"]
        # prefer chunks for the hinted perfil
        if perfil_hint:
            relevant = [c for c in verified if c.get("metadata", {}).get("perfil_proceso") == perfil_hint]
            relevant = relevant or verified[:6]
        else:
            relevant = verified[:8]
        if relevant:
            lines.append("## Conocimiento calibrado de fábrica (mediciones reales):")
            for c in relevant[:6]:
                meta = c.get("metadata", {})
                perfil = meta.get("perfil_proceso", "?")
                nivel  = meta.get("nivel_complejidad", "?")
                proc   = meta.get("proceso", "?")
                lines.append(f"- [{perfil} / {nivel} / {proc}]: {c['texto'][:220]}")

    # ── Anchor product BOMs (real factory measurements) ────────────────────────
    try:
        sb = get_sb()
        q = sb.table("products").select(
            "handle,perfil_proceso,complejidad,descripcion_web,bom_materials,dim_l_mm,dim_w_mm,dim_espesor_mm"
        ).eq("is_anchor", 1).neq("bom_materials", "[]").order("perfil_proceso").order("complejidad").limit(6)
        if perfil_hint:
            q = q.eq("perfil_proceso", perfil_hint)
        anchor_rows = q.execute().data or []
        if anchor_rows:
            lines.append("\n## BOMs reales de productos ancla (referencia de materiales):")
            for row in anchor_rows:
                bom = json.loads(row["bom_materials"] or "[]")
                mat_items = "; ".join(
                    f"{r.get('Material','?')} {r.get('kg_ml',0):.2f}u @${r.get('precio_kg',0)}"
                    for r in bom[:4]
                )
                dims = f"L={row['dim_l_mm'] or '?'} W={row['dim_w_mm'] or '?'} e={row['dim_espesor_mm'] or '?'}mm"
                lines.append(
                    f"- {row['handle']} ({row['perfil_proceso']} {row['complejidad']}, {dims}): {mat_items}"
                )
    except Exception:
        pass

    if not lines:
        return ""
    return (
        "\n\n## KNOWLEDGE BASE — datos calibrados de la fábrica Dulox\n"
        "Usa esta información para mejorar la clasificación y el BOM estimado:\n"
        + "\n".join(lines)
    )


def call_claude_vision(image_bytes: bytes, filename: str, rules: dict, rag_context: str = "") -> dict | None:
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    except Exception:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error("**ANTHROPIC_API_KEY no configurado.** Configura la variable de entorno antes de iniciar Streamlit.")
        return None

    ext = filename.rsplit(".", 1)[-1].lower()
    media_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                  "png": "image/png", "webp": "image/webp"}.get(ext, "image/png")
    b64 = base64.standard_b64encode(image_bytes).decode()

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = EXTRACTION_SYSTEM + (rag_context if rag_context else "")

    try:
        with st.spinner("Analizando plano con Claude Vision…"):
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                        {"type": "text", "text": "Extrae toda la información técnica de este plano de ingeniería."},
                    ],
                }],
            )
    except anthropic.BadRequestError as e:
        if "credit" in str(e).lower():
            st.error("**Créditos insuficientes.** Recarga en [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing).")
        else:
            st.error(f"Error API: {e}")
        return None
    except Exception as e:
        st.error(f"Error inesperado: {e}")
        return None

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        st.error(f"Claude devolvió JSON inválido: {e}\n\nRespuesta:\n```\n{raw[:500]}\n```")
        return None

import pandas as pd

# ─── DB helpers (thin wrappers using db.py) ───────────────────────────────────

def save_bom_db(handle: str, mat_rows: list, cons_rows: list, otros_rows=None):
    _db_save_bom(handle, mat_rows, cons_rows, otros_rows)


def save_to_db(product: dict, razon: str, source_file: str, force_update: bool = False) -> tuple[bool, str]:
    handle = product["handle"]
    existing = get_product(handle)

    if existing and not force_update:
        return False, f"Handle `{handle}` ya existe. Activa 'Forzar actualización'."

    now = datetime.now().isoformat()
    row = {
        "handle":          handle,
        "perfil_proceso":  product["perfil_proceso"],
        "complejidad":     product["complejidad"],
        "k_num":           {"C1":1,"C2":2,"C3":3}.get(product["complejidad"]),
        "familia":         product.get("familia",""),
        "subfamilia":      product.get("subfamilia",""),
        "descripcion_web": product.get("descripcion",""),
        "url":             product.get("url",""),
        "dim_l_mm":        product.get("dim_l_mm"),
        "dim_w_mm":        product.get("dim_w_mm"),
        "dim_h_mm":        product.get("dim_h_mm"),
        "dim_diameter_mm": product.get("dim_diameter_mm"),
        "dim_espesor_mm":  product.get("dim_espesor_mm"),
        "dim_confidence":  product.get("dim_confidence","high"),
        "dim_notes":       product.get("dim_notes",""),
        "g_score":         product.get("G"),
        "d_score":         product.get("D"),
        "validated":       1,
        "validated_by":    "drawing-intake",
        "validated_at":    now,
        "imported_at":     now,
    }
    row = {k: v for k, v in row.items() if v is not None}

    try:
        get_sb().table("products").upsert(row, on_conflict="handle").execute()
        action = "actualizado" if existing else "creado"
        log_change(
            handle,
            existing.get("perfil_proceso") if existing else None,
            product["perfil_proceso"],
            existing.get("complejidad") if existing else None,
            product["complejidad"],
            f"[drawing-intake] {razon} | source: {source_file}",
            "drawing-intake",
        )
        load_rules.clear()
        return True, f"✅ Producto `{handle}` {action}."
    except Exception as e:
        return False, f"Error DB: {e}"

# ─── Image overlay ────────────────────────────────────────────────────────────

def render_dimension_overlay(image_bytes: bytes, extraction: dict) -> Image.Image:
    """Draw key dimensions on the image for quick visual confirmation."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    W, H = img.size
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except Exception:
        font = ImageFont.load_default()

    dims = extraction.get("dimensions", {})
    lines = []
    if dims.get("l_mm"):      lines.append(f"L = {dims['l_mm']} mm")
    if dims.get("w_mm"):      lines.append(f"W = {dims['w_mm']} mm")
    if dims.get("h_mm"):      lines.append(f"H = {dims['h_mm']} mm")
    if dims.get("diameter_mm"): lines.append(f"Ø = {dims['diameter_mm']} mm")
    if dims.get("espesor_mm"): lines.append(f"e = {dims['espesor_mm']} mm")

    perfil = extraction.get("suggested_perfil", "")
    if perfil:
        lines.append(f"Perfil: {perfil}")

    if lines:
        pad = 10
        line_h = 22
        box_h = len(lines) * line_h + pad * 2
        box_w = max(len(l) for l in lines) * 9 + pad * 2
        draw.rectangle([8, 8, 8 + box_w, 8 + box_h], fill=(0, 0, 0, 170))
        for i, line in enumerate(lines):
            color = (100, 240, 200) if "Perfil" not in line else (255, 200, 80)
            draw.text((8 + pad, 8 + pad + i * line_h), line, fill=color, font=font)

    return Image.alpha_composite(img, overlay).convert("RGB")

# ─── UI helpers ───────────────────────────────────────────────────────────────

def driver_badge(score: int | None, label: str) -> str:
    if score is None:
        return f"**{label}** = —"
    colors = {1: "🟢", 2: "🟡", 3: "🔴"}
    return f"{colors.get(score,'⚪')} **{label}** = {score}"

def profile_selector(rules: dict, default: str = "p-custom") -> str:
    profiles = sorted(rules.get("profiles", {}).keys()) if rules else []
    if not profiles:
        return st.text_input("perfil_proceso", value=default)
    idx = profiles.index(default) if default in profiles else 0
    return st.selectbox("perfil_proceso", profiles, index=idx)

def complexity_options_for(perfil: str, rules: dict) -> list[str]:
    if not rules or perfil not in rules.get("profiles", {}):
        return ["C1", "C2", "C3"]
    return sorted(rules["profiles"][perfil].get("complexity_thresholds", {}).keys())

# ─── BOM editor widget (new schema) ──────────────────────────────────────────

_BOM_EDIT_COLS    = ["parte", "tipo", "calidad", "esp_mm", "L_mm", "A_mm", "cant", "simbolos", "valor_unit"]
_BOM_TIPO_OPTIONS = ["Plancha", "Coil", "Perfil", "Tubo", "Macizo"]  # "Otro" → Table 2
_BOM_CAL_OPTIONS  = ["304", "201", "316", "430"]
_BOM_OTROS_COLS   = ["parte", "cant", "valor_unit"]

def _bom_empty_row() -> dict:
    return {"parte": "", "tipo": "Plancha", "calidad": "304",
            "esp_mm": float("nan"), "L_mm": float("nan"), "A_mm": float("nan"),
            "cant": 1, "simbolos": "", "valor_unit": float("nan")}

def _bom_otros_empty() -> dict:
    return {"parte": "", "cant": 1, "valor_unit": float("nan")}

def _normalize_mat_row(r: dict) -> dict:
    """Accept both old-schema and new-schema rows; always return new-schema."""
    if "parte" in r:
        base = _bom_empty_row()
        base.update({k: r[k] for k in _BOM_EDIT_COLS if k in r})
        # Ensure numeric columns are float (not None — causes object dtype)
        for c in ("esp_mm", "L_mm", "A_mm", "valor_unit"):
            if base[c] is None:
                base[c] = float("nan")
        return base
    # Old schema: Subconjunto/Dimensiones/Material/kg_ml/precio_kg
    base = _bom_empty_row()
    base["parte"]      = r.get("Subconjunto", "") or r.get("Material", "")
    base["valor_unit"] = float(r.get("precio_kg", float("nan")) or float("nan"))
    return base


def bom_editor_widget(handle: str, saved_mat: list, saved_cons: list, key_prefix: str,
                      saved_otros: list | None = None):
    """
    Inline BOM editor — two separate tables:
    Table 1 (formula): Plancha/Coil/Perfil/Tubo/Macizo — formula-computed qty.
    Table 2 (otros):   Hardware, accesorios — parte/cant/valor_unit → total.
    Returns (mat_rows, cons_rows, otros_rows, total_clp).
    """
    global_prices = load_material_prices() or DEFAULT_GLOBAL_PRICES

    CONS_CFG = {
        "Producto":  st.column_config.TextColumn("Producto", width="large"),
        "Proceso":   st.column_config.TextColumn("Proceso", width="medium"),
        "Cantidad":  st.column_config.NumberColumn("Cant.", min_value=0, step=0.001, format="%.3f"),
        "Unidad":    st.column_config.SelectboxColumn("Unidad", options=["u","kg","L","m","ml","hr"]),
        "Precio_u":  st.column_config.NumberColumn("Precio u. $", min_value=0, step=1, format="%.0f"),
    }

    # Filter "Otro" rows out of formula table (they move to Table 2)
    mat_formula  = [r for r in saved_mat if (r.get("tipo") or "Plancha").strip().lower() != "otro"]
    mat_default  = [_normalize_mat_row(r) for r in mat_formula] if mat_formula else [_bom_empty_row()]
    cons_default = saved_cons or [{"Producto":"","Proceso":"","Cantidad":0,"Unidad":"u","Precio_u":0}]

    # Seed otros: from explicit saved_otros, or migrate "Otro" rows from saved_mat
    if saved_otros:
        otros_default = saved_otros
    else:
        otros_default = [
            {"parte": r.get("parte",""), "cant": int(r.get("cant",1) or 1),
             "valor_unit": float(r.get("valor_unit") or 0) or float("nan")}
            for r in saved_mat if (r.get("tipo") or "").strip().lower() == "otro"
        ] or [_bom_otros_empty()]

    _mat_skey  = f"df_bom_mat_{key_prefix}"
    _mat_hkey  = f"hash_bom_mat_{key_prefix}"
    _cons_skey = f"df_bom_cons_{key_prefix}"
    _cons_hkey = f"hash_bom_cons_{key_prefix}"
    _otr_skey  = f"df_bom_otr_{key_prefix}"
    _otr_hkey  = f"hash_bom_otr_{key_prefix}"

    _mat_hash  = hash(str(mat_default))
    _cons_hash = hash(str(cons_default))
    _otr_hash  = hash(str(otros_default))

    if st.session_state.get(_mat_hkey) != _mat_hash or _mat_skey not in st.session_state:
        df = pd.DataFrame(mat_default)
        for c in ("esp_mm", "L_mm", "A_mm", "valor_unit"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["cant"] = pd.to_numeric(df["cant"], errors="coerce").fillna(1).astype(int)
        st.session_state[_mat_skey] = df
        st.session_state[_mat_hkey] = _mat_hash

    if st.session_state.get(_cons_hkey) != _cons_hash or _cons_skey not in st.session_state:
        st.session_state[_cons_skey] = pd.DataFrame(cons_default)
        st.session_state[_cons_hkey] = _cons_hash

    if st.session_state.get(_otr_hkey) != _otr_hash or _otr_skey not in st.session_state:
        _dfo = pd.DataFrame(otros_default)
        _dfo["cant"]       = pd.to_numeric(_dfo["cant"],       errors="coerce").fillna(1).astype(int)
        _dfo["valor_unit"] = pd.to_numeric(_dfo["valor_unit"], errors="coerce")
        st.session_state[_otr_skey] = _dfo
        st.session_state[_otr_hkey] = _otr_hash

    if "valor_unit" not in st.session_state[_mat_skey].columns:
        st.session_state[_mat_skey]["valor_unit"] = float("nan")

    # ── Table 1: Formula ──────────────────────────────────────────────────────
    st.caption("KG: Plancha/Coil → L×A×esp×8e-6 × waste. ML: Perfil/Tubo/Macizo → L/1000. $ / unit vacío = precio global.")

    mat_df = st.data_editor(
        st.session_state[_mat_skey][_BOM_EDIT_COLS],
        key=f"bom_mat_editor_{key_prefix}",
        use_container_width=True, num_rows="dynamic", hide_index=True,
        column_config={
            "parte":      st.column_config.TextColumn("Parte", width="medium"),
            "tipo":       st.column_config.SelectboxColumn("Tipo", options=_BOM_TIPO_OPTIONS, width="small"),
            "calidad":    st.column_config.SelectboxColumn("Calidad", options=_BOM_CAL_OPTIONS, width="small"),
            "esp_mm":     st.column_config.NumberColumn("esp mm", format="%.1f", step=0.5, min_value=0.1, width="small"),
            "L_mm":       st.column_config.NumberColumn("L mm", format="%.0f", step=1.0, width="small"),
            "A_mm":       st.column_config.NumberColumn("A / Ø mm", format="%.0f", step=1.0, width="small"),
            "cant":       st.column_config.NumberColumn("Cant", format="%d", step=1, min_value=1, width="small"),
            "simbolos":   st.column_config.TextColumn("Símbolos", help="P1 P2 T4 ⊙ S V M EXT", width="small"),
            "valor_unit": st.column_config.NumberColumn("$ / unit", help="Override precio global. Vacío = usa precio global.", format="$ %d", step=50, min_value=0, width="small"),
        },
    )

    computed = []
    mat_total = 0
    if isinstance(mat_df, pd.DataFrame) and not mat_df.empty:
        computed = compute_bom(mat_df.to_dict("records"), global_prices)
        mat_total = sum(int(r.get("total_clp") or 0) for r in computed)
        comp_df = pd.DataFrame([{
            "Parte":     r.get("parte", ""),
            "Unidad":    r.get("unidad", ""),
            "Qty total": r.get("qty_total", 0),
            "$ / unit":  r.get("valor_unit", 0),
            "Total $":   r.get("total_clp", 0),
        } for r in computed])
        st.dataframe(comp_df, use_container_width=True, hide_index=True,
            column_config={
                "Qty total": st.column_config.NumberColumn(format="%.4f"),
                "$ / unit":  st.column_config.NumberColumn(format="$ %.0f"),
                "Total $":   st.column_config.NumberColumn(format="$ %.0f"),
            })
        warns = [f"**{r.get('parte','?')}:** {w}" for r in computed for w in (r.get("warnings") or [])]
        if warns:
            st.warning("\n".join(f"- {w}" for w in warns))

    # ── Table 2: Otros ────────────────────────────────────────────────────────
    st.markdown("**🔩 Otros materiales** — Herrajes / Accesorios / Componentes")
    st.caption("Manual: parte / cantidad / $ por unidad. Total = cant × valor_unit.")

    otros_df = st.data_editor(
        st.session_state[_otr_skey][_BOM_OTROS_COLS],
        key=f"bom_otros_editor_{key_prefix}",
        use_container_width=True, num_rows="dynamic", hide_index=True,
        column_config={
            "parte":      st.column_config.TextColumn("Parte", width="large"),
            "cant":       st.column_config.NumberColumn("Cant", format="%d", step=1, min_value=1, width="small"),
            "valor_unit": st.column_config.NumberColumn("$ / unit", format="$ %d", step=50, min_value=0, width="medium"),
        },
    )

    otros_total = 0
    otros_rows  = otros_default
    if isinstance(otros_df, pd.DataFrame) and not otros_df.empty:
        _o = otros_df.copy()
        _o["cant"]       = pd.to_numeric(_o["cant"],       errors="coerce").fillna(1)
        _o["valor_unit"] = pd.to_numeric(_o["valor_unit"], errors="coerce").fillna(0)
        _o["Total $"]    = (_o["cant"] * _o["valor_unit"]).round().astype(int)
        otros_total = int(_o["Total $"].sum())
        _o_disp = _o[_o["parte"].fillna("").str.strip() != ""][["parte","cant","valor_unit","Total $"]]
        if not _o_disp.empty:
            st.dataframe(_o_disp, use_container_width=True, hide_index=True,
                column_config={
                    "valor_unit": st.column_config.NumberColumn("$ / unit", format="$ %.0f"),
                    "Total $":    st.column_config.NumberColumn(format="$ %.0f"),
                })
        otros_rows = _o[["parte","cant","valor_unit"]].to_dict("records")

    # ── Consumibles ───────────────────────────────────────────────────────────
    st.markdown("**🔩 Consumibles**")
    cons_df = st.data_editor(
        st.session_state[_cons_skey],
        key=f"bom_cons_editor_{key_prefix}",
        use_container_width=True, num_rows="dynamic",
        column_config=CONS_CFG, hide_index=True,
    )

    cons_total = 0
    cons_rows  = cons_default
    if isinstance(cons_df, pd.DataFrame) and not cons_df.empty:
        _c = cons_df.copy()
        _c["Total"] = (_c["Cantidad"].fillna(0) * _c["Precio_u"].fillna(0)).round().astype(int)
        cons_total = int(_c["Total"].sum())
        cons_rows  = _c.to_dict("records")

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Fórmula",    f"${mat_total:,}")
    col_b.metric("Otros",      f"${otros_total:,}")
    col_c.metric("Consumibles",f"${cons_total:,}")
    col_d.metric("Total directo", f"${mat_total + otros_total + cons_total:,}")

    mat_rows = computed if computed else mat_df.to_dict("records") if isinstance(mat_df, pd.DataFrame) else mat_default
    return mat_rows, cons_rows, otros_rows, mat_total + otros_total + cons_total


def show_process_panel(perfil: str, complejidad: str, rules: dict):
    """Show processes active at this complexity + standard consumables from templates."""
    if not rules or perfil not in rules.get("profiles", {}):
        return

    profile = rules["profiles"][perfil]
    tiers   = profile.get("process_tiers", {})
    procs   = tiers.get(complejidad, tiers.get("C2", []))  # fallback to C2
    templates  = rules.get("process_templates", {})
    consumables = rules.get("process_consumables", {})

    if not procs:
        st.caption("Sin procesos definidos para este nivel. Ve a 📥 Inputs → Procesos por Nivel.")
        return

    st.markdown(
        f'<div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.8rem;">',
        unsafe_allow_html=True
    )
    badges = "".join(
        f'<span style="background:#0d2137;border:1px solid #1f6feb;border-radius:12px;'
        f'padding:2px 10px;font-size:0.78rem;color:#79c0ff;font-weight:600;">{p}</span>'
        for p in procs
    )
    st.markdown(badges + '</div>', unsafe_allow_html=True)

    # Times summary
    hh = rules.get("hh_rates", {})
    rows = []
    for proc in procs:
        tmpl  = templates.get(proc, {}).get(complejidad, {})
        rate  = hh.get(proc, 6500)
        t_set = tmpl.get("T_setup_min", 0)
        t_ex  = tmpl.get("T_exec_min", 0)
        n_ops = tmpl.get("n_ops", 1)
        labor = round((t_set + t_ex) / 60 * rate * n_ops)
        cons_lvl = consumables.get(proc, {}).get(complejidad, [])
        cons_total = sum(r.get("Cantidad",0)*r.get("Precio_u",0) for r in cons_lvl)
        rows.append({
            "Proceso": proc,
            "Setup (min)": t_set,
            "Exec (min)": t_ex,
            "Ops": n_ops,
            "Costo HH $": labor,
            "Consumibles $": round(cons_total),
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ─── Main page ────────────────────────────────────────────────────────────────

# ─── Shared: image upload + vision extraction ─────────────────────────────────

def _upload_and_extract(rules: dict, tab_key: str) -> tuple[bytes | None, str, dict | None]:
    """Render upload + Claude Vision button. Returns (image_bytes, filename, extraction|None)."""
    uploaded = st.file_uploader(
        "Sube un plano o imagen del producto",
        type=["png","jpg","jpeg","webp"],
        help="Plano técnico, sketch, foto, o CAD exportado",
        key=f"uploader_{tab_key}",
    )
    if not uploaded:
        return None, "", None

    image_bytes = uploaded.read()
    filename    = uploaded.name
    cache_key   = f"extraction_{tab_key}_{filename}"
    extraction  = st.session_state.get(cache_key)

    col_img, col_ctrl = st.columns([3, 2])
    with col_img:
        if extraction:
            try:
                annotated = render_dimension_overlay(image_bytes, extraction)
                st.image(annotated, width='stretch', caption=filename)
            except Exception:
                st.image(image_bytes, width='stretch', caption=filename)
        else:
            st.image(image_bytes, width='stretch', caption=filename)

    with col_ctrl:
        if extraction is None:
            st.info("Imagen cargada. Analiza con Claude Vision para extraer dimensiones, o continúa manualmente.")
            if st.button("🔍 Analizar con Claude Vision", type="primary",
                         use_container_width=True, key=f"analyze_{tab_key}"):
                rag_ctx = _load_rag_context(rules)
                result = call_claude_vision(image_bytes, filename, rules, rag_context=rag_ctx)
                if result:
                    st.session_state[cache_key] = result
                    st.rerun()
        else:
            st.success("✅ Análisis completado")
            dims = extraction.get("dimensions", {})
            sf   = extraction.get("special_features", {})
            st.markdown(f"**{extraction.get('drawing_title', filename)}**")
            st.markdown(f"Material: `{extraction.get('material','—')}`")
            dc1, dc2 = st.columns(2)
            with dc1:
                for k, lbl in [("l_mm","L"),("w_mm","W"),("h_mm","H")]:
                    st.metric(f"{lbl} mm", dims.get(k) or "—")
            with dc2:
                for k, lbl in [("diameter_mm","Ø"),("espesor_mm","e")]:
                    st.metric(f"{lbl} mm", dims.get(k) or "—")
            conf = dims.get("confidence","—")
            _conf_icon = {"high":"🟢","medium":"🟡","low":"🔴"}.get(conf,"⚪")
            st.caption(f"Confianza: {_conf_icon} {conf}")
            features = []
            if sf.get("has_mechanism"):         features.append(f"⚙️ {sf.get('mechanism_type','mecanismo')}")
            if sf.get("has_mirror_finish"):     features.append("✨ Acabado espejo")
            if sf.get("multiple_compartments"): features.append(f"📦 {sf.get('num_compartments',3)}+ compartimientos")
            if sf.get("num_quemadores"):        features.append(f"🔥 {sf['num_quemadores']} quemadores")
            if sf.get("num_niveles"):           features.append(f"📚 {sf['num_niveles']} niveles")
            if sf.get("num_tazas"):             features.append(f"🚿 {sf['num_tazas']} tazas")
            if features:
                st.caption("  ·  ".join(features))
            comps = extraction.get("components",[])
            if comps:
                with st.expander(f"🔩 {len(comps)} componentes"):
                    for c in comps:
                        st.markdown(f"- **{c.get('nombre','?')}** ×{c.get('cantidad',1)} — {c.get('dims_raw') or '—'}")
            if st.button("🔄 Re-analizar", use_container_width=True, key=f"reanalyze_{tab_key}"):
                del st.session_state[cache_key]
                st.rerun()

    # ── Extracted BOM preview ──────────────────────────────────────────────────
    if extraction:
        bom_ext = extraction.get("bom_materials", [])
        if bom_ext:
            with st.expander(f"📋 Materiales extraídos por Vision — {len(bom_ext)} filas (se pre-cargarán abajo)", expanded=True):
                st.dataframe(
                    pd.DataFrame(bom_ext)[["Subconjunto","Dimensiones","Material","kg_ml","precio_kg"]],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "kg_ml":     st.column_config.NumberColumn("kg/ML/u", format="%.2f"),
                        "precio_kg": st.column_config.NumberColumn("$/kg o $/u", format="%.0f"),
                    }
                )
                st.caption("Consumibles: se cargan automáticamente según el perfil y complejidad asignados.")

    return image_bytes, filename, extraction


def _bom_from_extraction(extraction: dict | None) -> list:
    """Return mat_rows pre-populated from Vision extraction (new schema), or []."""
    if not extraction:
        return []
    mat = extraction.get("bom_materials", [])
    return [_normalize_mat_row(r) for r in mat]


def _cons_from_rules(perfil: str, complejidad: str, rules: dict) -> list:
    """Return consumables rows from process templates for the active processes at this level."""
    profile    = rules.get("profiles", {}).get(perfil, {})
    tiers      = profile.get("process_tiers", {})
    procs      = tiers.get(complejidad, [])
    cons_defs  = rules.get("process_consumables", {})
    rows = []
    for proc in procs:
        for r in cons_defs.get(proc, {}).get(complejidad, []):
            rows.append({
                "Producto":  r.get("Producto", ""),
                "Proceso":   proc,
                "Cantidad":  float(r.get("Cantidad", 0) or 0),
                "Unidad":    r.get("Unidad", "u"),
                "Precio_u":  int(r.get("Precio_u", 0) or 0),
            })
    return rows


def _driver_form(extraction: dict | None, rules: dict, perfil_key: str, comp_key: str) -> tuple[str, str, int | None, list, int, int, dict]:
    """
    Render editable driver form. Returns (perfil, complejidad, c_val, x_active_keys, G, D, dims).
    All values derived from extraction if available, fully overridable.
    """
    dims = extraction.get("dimensions", {}) if extraction else {}
    sf   = extraction.get("special_features", {}) if extraction else {}

    # ── Pre-populate dimension widget state from extraction (only when fresh) ──
    if extraction and dims:
        _ext_hash = hash(json.dumps(
            {k: dims.get(k) for k in ["l_mm","w_mm","h_mm","diameter_mm","espesor_mm"]},
            sort_keys=True
        ))
        _hash_key = f"_ext_hash_{perfil_key}"
        if st.session_state.get(_hash_key) != _ext_hash:
            for _wk, _dk in [("L","l_mm"),("W","w_mm"),("H","h_mm"),("D__","diameter_mm"),("e","espesor_mm")]:
                v = dims.get(_dk)
                if v is not None:
                    st.session_state[f"{_wk}_{perfil_key}"] = float(v)
            st.session_state[_hash_key] = _ext_hash

    # ── Dimensions (editable) ──
    st.markdown("**Dimensiones**")
    dc = st.columns(5)
    l_mm = dc[0].number_input("L mm", value=float(dims.get("l_mm") or 0), min_value=0.0, key=f"L_{perfil_key}")
    w_mm = dc[1].number_input("W mm", value=float(dims.get("w_mm") or 0), min_value=0.0, key=f"W_{perfil_key}")
    h_mm = dc[2].number_input("H mm", value=float(dims.get("h_mm") or 0), min_value=0.0, key=f"H_{perfil_key}")
    diam = dc[3].number_input("Ø mm", value=float(dims.get("diameter_mm") or 0), min_value=0.0, key=f"D__{perfil_key}")
    esp  = dc[4].number_input("e mm", value=float(dims.get("espesor_mm") or 0), min_value=0.0, step=0.1, format="%.1f", key=f"e_{perfil_key}")

    eff_l = l_mm or diam or None
    eff_w = w_mm or diam or None
    G = compute_G(eff_l, eff_w, rules)
    D = compute_D(esp or None, rules)
    area = (eff_l * eff_w) if (eff_l and eff_w) else None

    gc1, gc2, gc3 = st.columns(3)
    gc1.metric("G (Geometría)", G or "—", help="Área L×W vs umbrales")
    gc2.metric("D (Espesor)", D or "—", help="Espesor vs umbrales")
    if area:
        gc3.metric("Área", f"{area/1e6:.3f} m²")

    st.divider()

    # ── Perfil + complejidad ──
    st.markdown("**Clasificación**")
    profiles = sorted(rules.get("profiles", {}).keys())
    suggested_perfil = extraction.get("suggested_perfil","p-custom") if extraction else "p-custom"
    p_idx = profiles.index(suggested_perfil) if suggested_perfil in profiles else 0
    perfil = st.selectbox("Perfil proceso", profiles, index=p_idx, key=perfil_key)

    if extraction:
        razon = extraction.get("suggested_razon_perfil","")
        if razon:
            st.caption(f"Sugerencia Claude: {razon}")

    # ── C driver ──
    profile_rules = rules.get("profiles", {}).get(perfil, {})
    c_driver_field = profile_rules.get("c_driver")
    C_LABELS = {"num_quemadores":"Quemadores","num_niveles":"Niveles","num_tazas":"Tazas",
                "num_componentes":"Componentes","num_varillas":"Varillas","capacidad_litros":"Cap. (L)"}
    c_val = None
    if c_driver_field:
        c_auto = (sf.get("num_quemadores") or sf.get("num_niveles") or
                  sf.get("num_tazas") or sf.get("capacidad_litros") or 0)
        c_val = st.number_input(
            f"C — {C_LABELS.get(c_driver_field, c_driver_field)}",
            value=int(c_auto), min_value=0,
            help=f"Driver C de este perfil: {c_driver_field}",
            key=f"cval_{perfil_key}",
        )

    # ── X characteristics ──
    st.markdown("**Características X**")
    x_defs = profile_rules.get("x_flags", {})
    if not x_defs:
        st.caption("Este perfil no tiene características X definidas.")
        x_active = []
    else:
        # Auto-detect from extraction
        auto_x = set()
        if sf.get("has_mirror_finish"):     auto_x.add("terminacion_multifinic")
        if sf.get("has_mechanism"):         auto_x.add("tiene_mecanismo")
        if sf.get("multiple_compartments"): auto_x.add("multiples_compartimientos")

        x_active = []
        for flag_key, flag_def in x_defs.items():
            scope = flag_def.get("process_scope", [])
            scope_str = f" · solo {', '.join(scope)}" if scope else ""
            checked = st.checkbox(
                f"{flag_def['label']}  +{flag_def.get('points',1)} pts{scope_str}",
                value=(flag_key in auto_x),
                key=f"xflag_{perfil_key}_{flag_key}",
                help=flag_def.get("description",""),
            )
            if checked:
                x_active.append(flag_key)

    # ── Inline: add new X flag for this perfil ─────────────────────────────────
    with st.expander("➕ Agregar nueva característica X para este perfil", expanded=False):
        _rules_live = load_rules()  # fresh copy to avoid stale state
        _templates  = _rules_live.get("process_templates", {})
        _x_procs    = sorted(p for p, t in _templates.items() if "X" in t.get("drivers", []))
        with st.form(key=f"add_x_inline_{perfil_key}", clear_on_submit=True):
            _fc1, _fc2 = st.columns([3, 1])
            _new_key   = _fc1.text_input("Clave interna (sin espacios)",
                                          placeholder="ej: compartimiento_profundo")
            _new_label = _fc1.text_input("Nombre visible",
                                          placeholder="ej: Compartimiento profundo")
            _new_pts   = _fc2.number_input("Puntos (+)", value=1, min_value=1, max_value=5)
            _new_desc  = st.text_input("Descripción (opcional)")
            _new_scope = st.multiselect(
                "Afecta solo a estos procesos (vacío = todos con driver X)",
                options=_x_procs,
            )
            if st.form_submit_button("➕ Agregar", type="primary"):
                _safe = _new_key.strip().replace(" ", "_").lower()
                _existing = _rules_live.get("profiles", {}).get(perfil, {}).get("x_flags", {})
                if not _safe or not _new_label.strip():
                    st.error("Clave y nombre son obligatorios.")
                elif _safe in _existing:
                    st.error(f"Ya existe '{_safe}' en {perfil}.")
                else:
                    _existing[_safe] = {
                        "label": _new_label.strip(),
                        "description": _new_desc.strip(),
                        "points": int(_new_pts),
                        "process_scope": _new_scope,
                    }
                    _rules_live["profiles"][perfil]["x_flags"] = _existing
                    save_rules(_rules_live)
                    st.success(f"✅ '{_new_label.strip()}' agregada a {perfil}.")
                    st.rerun()

    # ── Compute score → complexity ──
    x_flags_active_for_score = x_active
    pts, breakdown = compute_complexity_points(G, D, perfil, x_flags_active_for_score, c_val, rules)
    auto_comp = points_to_complexity(pts, perfil, rules) or "C1"
    valid_comps = complexity_options_for(perfil, rules)
    comp_idx = valid_comps.index(auto_comp) if auto_comp in valid_comps else 0

    score_str = "  +  ".join(f"{k}={v}" for k,v in breakdown.items()) if breakdown else "sin datos"
    st.info(f"Score calculado: **{pts} pts** ({score_str})  →  nivel sugerido: **{auto_comp}**")

    complejidad = st.selectbox("Complejidad (override si necesitas)", valid_comps,
                                index=comp_idx, key=comp_key)

    return perfil, complejidad, c_val if c_val else None, x_active, G or 0, D or 0, {
        "l_mm": l_mm or None, "w_mm": w_mm or None, "h_mm": h_mm or None,
        "diameter_mm": diam or None, "espesor_mm": esp or None,
        "confidence": dims.get("confidence","medium") if dims else "medium",
        "notes": dims.get("notes","") if dims else "",
    }


def _cost_summary(perfil: str, complejidad: str, mat_total: int, cons_total: int,
                   bom_direct: int, rules: dict):
    """Show labor + process cost estimate + BOM total."""
    templates   = rules.get("process_templates", {})
    hh_rates    = rules.get("hh_rates", {})
    profile     = rules.get("profiles", {}).get(perfil, {})
    tiers       = profile.get("process_tiers", {})
    procs       = tiers.get(complejidad, [])
    consumables = rules.get("process_consumables", {})

    labor_total = 0
    std_cons_total = 0
    for proc in procs:
        tmpl  = templates.get(proc, {}).get(complejidad, {})
        rate  = hh_rates.get(proc, 6500)
        t_set = tmpl.get("T_setup_min", 0)
        t_ex  = tmpl.get("T_exec_min", 0)
        n_ops = tmpl.get("n_ops", 1)
        labor_total += round((t_set + t_ex) / 60 * rate * n_ops)
        std_cons_total += sum(
            r.get("Cantidad",0)*r.get("Precio_u",0)
            for r in consumables.get(proc, {}).get(complejidad, [])
        )

    grand = bom_direct + labor_total
    c1, c2 = st.columns(2)
    c1.metric("Mano de obra est.", f"${labor_total:,}", help=f"{len(procs)} procesos en {complejidad}")
    c2.metric("Total estimado (BOM + HH)", f"${grand:,}")


def main():
    st.header("🔩 Ingreso de Producto")

    rules = load_rules()
    if not rules:
        st.warning("⚠️ No se pudo cargar `PROCESS_RULES.json`.")

    tab_new, tab_derive, tab_bom = st.tabs([
        "✨ Producto nuevo",
        "🔀 Derivar de existente",
        "📦 BOM a existente",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Nuevo producto desde plano/imagen
    # Upload → Vision → edit all drivers (G/D/C/X) → processes → BOM → save new
    # ══════════════════════════════════════════════════════════════════════════
    with tab_new:
        st.caption("Sube un plano o imagen, extrae las dimensiones con Claude, completa todos los drivers, ingresa el BOM y guarda como producto nuevo.")
        st.divider()

        image_bytes, filename, extraction = _upload_and_extract(rules, "new")

        if not image_bytes:
            st.info("Sube un plano o imagen para continuar.")
        else:
            st.divider()
            st.subheader("Drivers y clasificación")

            perfil, complejidad, c_val, x_active, G, D, dims = _driver_form(
                extraction, rules, perfil_key="new_perfil", comp_key="new_comp"
            )

            st.divider()
            st.subheader("Procesos asignados")
            show_process_panel(perfil, complejidad, rules)

            st.divider()
            st.subheader("Identificación")
            nc1, nc2 = st.columns(2)
            raw_title = (extraction.get("drawing_title","") if extraction else "") or filename.rsplit(".",1)[0]
            handle_sug = re.sub(r'-+', '-', re.sub(r'[^a-z0-9\-]', '-', raw_title.lower())).strip('-')[:50]
            with nc1:
                handle     = st.text_input("Handle (único)", value=handle_sug, key="new_handle",
                                           help="Minúsculas, guiones, números. Ej: lavadero-2-tazas")
                familia    = st.text_input("Familia", value="", key="new_familia")
            with nc2:
                nombre     = st.text_input("Nombre", value=raw_title, key="new_nombre")
                subfamilia = st.text_input("Subfamilia", value="", key="new_subfamilia")
            descripcion = st.text_area("Descripción técnica",
                value=f"{raw_title}. Material: {extraction.get('material','AISI 304-L') if extraction else 'AISI 304-L'}.",
                height=60, key="new_desc")

            st.divider()
            st.subheader("BOM de costos directos")
            _ext_mat  = _bom_from_extraction(extraction)
            _proc_cons = _cons_from_rules(perfil, complejidad, rules)
            mat_rows, cons_rows, otros_rows, bom_total = bom_editor_widget(
                handle or "nuevo", _ext_mat, _proc_cons, key_prefix="new_product"
            )

            st.divider()
            st.subheader("Costo total estimado")
            _cost_summary(perfil, complejidad,
                          sum(r.get("total_clp", r.get("total", 0)) for r in mat_rows)
                          + sum(int(r.get("cant",1)) * float(r.get("valor_unit") or 0) for r in otros_rows),
                          sum(r.get("Total",0) for r in cons_rows),
                          bom_total, rules)

            st.divider()
            handle_ok = bool(handle) and bool(re.match(r'^[a-z0-9][a-z0-9\-]+[a-z0-9]$', handle))
            if not handle_ok:
                st.warning("Handle inválido.")
            if handle_ok and handle_exists(handle):
                st.warning(f"⚠️ `{handle}` ya existe — se actualizará si confirmas.")

            if st.button("💾 Guardar producto nuevo + BOM", type="primary",
                         disabled=not handle_ok, use_container_width=True, key="save_new"):
                product = {
                    "handle": handle, "perfil_proceso": perfil, "complejidad": complejidad,
                    "familia": familia, "subfamilia": subfamilia, "descripcion": descripcion, "url": "",
                    "dim_l_mm": dims.get("l_mm"), "dim_w_mm": dims.get("w_mm"),
                    "dim_h_mm": dims.get("h_mm"), "dim_diameter_mm": dims.get("diameter_mm"),
                    "dim_espesor_mm": dims.get("espesor_mm"),
                    "dim_confidence": dims.get("confidence","medium"),
                    "dim_notes": dims.get("notes",""), "G": G or None, "D": D or None,
                }
                ok, msg = save_to_db(product, f"Ingreso desde plano {filename}", filename, force_update=True)
                if ok:
                    save_bom_db(handle, mat_rows, cons_rows, otros_rows)
                    get_sb().table("products").update({
                        "c_value": c_val, "x_flags": json.dumps(x_active),
                    }).eq("handle", handle).execute()
                    st.success(f"{msg} · BOM ${bom_total:,}")
                    st.balloons()
                    st.cache_data.clear()
                else:
                    st.error(msg)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Derivar de existente
    # Upload image → pick base product → clone + modify drivers → new handle → BOM → save
    # ══════════════════════════════════════════════════════════════════════════
    with tab_derive:
        st.caption("Sube la imagen del nuevo producto, selecciona el producto existente más similar como base, ajusta los drivers y guárdalo como producto nuevo.")
        st.divider()

        image_bytes_d, filename_d, extraction_d = _upload_and_extract(rules, "derive")

        st.divider()
        st.subheader("Selecciona el producto base")
        qd = st.text_input("🔎 Buscar producto base", placeholder="ej: meson-recto…", key="derive_query")
        base_row = None
        if qd:
            results_d = search_products(qd)
            if results_d:
                opts_d = {f"{r['handle']}  —  {(r.get('descripcion_web') or '')[:55]}": r["handle"]
                          for r in results_d}
                sel_d = st.selectbox("Producto base", list(opts_d.keys()), key="derive_sel")
                base_row = get_product(opts_d[sel_d])
                if base_row:
                    bc1, bc2, bc3, bc4 = st.columns(4)
                    if base_row.get("image_url"):
                        bc1.markdown(f'<img src="{base_row["image_url"]}" style="width:100%;border-radius:4px;">', unsafe_allow_html=True)
                    bc2.metric("Perfil", base_row.get("perfil_proceso","—"))
                    bc3.metric("Complejidad", base_row.get("complejidad","—"))
                    bc4.metric("G/D", f"{base_row.get('G','—')}/{base_row.get('D','—')}")
                    saved_mat_base  = json.loads(base_row.get("bom_materials","[]") or "[]")
                    saved_cons_base = json.loads(base_row.get("bom_consumables","[]") or "[]")
                    if saved_mat_base:
                        st.caption(f"BOM base: {len(saved_mat_base)} materiales, {len(saved_cons_base)} consumibles — se pre-cargan para edición.")
            else:
                st.warning("Sin resultados.")

        if base_row:
            # Inject base dims into extraction if vision not run
            base_extraction = extraction_d or {
                "dimensions": {
                    "l_mm": base_row.get("dim_l_mm"), "w_mm": base_row.get("dim_w_mm"),
                    "h_mm": base_row.get("dim_h_mm"), "diameter_mm": base_row.get("dim_diameter_mm"),
                    "espesor_mm": base_row.get("dim_espesor_mm"), "confidence": "medium",
                },
                "special_features": {},
                "suggested_perfil": base_row.get("perfil_proceso","p-custom"),
            }

            st.divider()
            st.subheader("Drivers del nuevo producto")
            perfil_d, comp_d, c_val_d, x_active_d, G_d, D_d, dims_d = _driver_form(
                base_extraction, rules, perfil_key="derive_perfil", comp_key="derive_comp"
            )

            st.divider()
            st.subheader("Procesos asignados")
            show_process_panel(perfil_d, comp_d, rules)

            st.divider()
            st.subheader("Identidad del nuevo producto")
            dc1, dc2 = st.columns(2)
            with dc1:
                new_handle_d = st.text_input("Nuevo handle (único)", key="derive_handle",
                                             help="Distinto al del producto base")
                familia_d    = st.text_input("Familia", value=base_row.get("familia","") or "", key="derive_fam")
            with dc2:
                nombre_d     = st.text_input("Nombre", key="derive_nombre")
                subfamilia_d = st.text_input("Subfamilia", value=base_row.get("subfamilia","") or "", key="derive_sub")
            desc_d = st.text_area("Descripción", height=55, key="derive_desc")

            st.divider()
            st.subheader("BOM del nuevo producto")
            _ext_mat_d  = _bom_from_extraction(extraction_d)
            _init_mat_d = _ext_mat_d if _ext_mat_d else (saved_mat_base if base_row else [])
            _proc_cons_d = _cons_from_rules(perfil_d, comp_d, rules)
            if _ext_mat_d:
                st.caption("🔍 Materiales pre-cargados desde Vision. Consumibles según procesos asignados.")
            elif saved_mat_base:
                st.caption("Materiales del producto base. Consumibles según procesos asignados.")
            mat_rows_d, cons_rows_d, otros_rows_d, bom_total_d = bom_editor_widget(
                new_handle_d or "derivado",
                _init_mat_d, _proc_cons_d,
                key_prefix="derive_product"
            )

            st.divider()
            st.subheader("Costo total estimado")
            _cost_summary(perfil_d, comp_d,
                          sum(r.get("total_clp", r.get("total", 0)) for r in mat_rows_d)
                          + sum(int(r.get("cant",1)) * float(r.get("valor_unit") or 0) for r in otros_rows_d),
                          sum(r.get("Total",0) for r in cons_rows_d),
                          bom_total_d, rules)

            st.divider()
            handle_ok_d = bool(new_handle_d) and bool(re.match(r'^[a-z0-9][a-z0-9\-]+[a-z0-9]$', new_handle_d))
            if not handle_ok_d:
                st.warning("Handle inválido.")
            if handle_ok_d and handle_exists(new_handle_d):
                st.warning(f"⚠️ `{new_handle_d}` ya existe — se actualizará.")

            if st.button("💾 Guardar producto derivado + BOM", type="primary",
                         disabled=not handle_ok_d, use_container_width=True, key="save_derive"):
                product_d = {
                    "handle": new_handle_d, "perfil_proceso": perfil_d, "complejidad": comp_d,
                    "familia": familia_d, "subfamilia": subfamilia_d,
                    "descripcion": desc_d or nombre_d, "url": "",
                    "dim_l_mm": dims_d.get("l_mm"), "dim_w_mm": dims_d.get("w_mm"),
                    "dim_h_mm": dims_d.get("h_mm"), "dim_diameter_mm": dims_d.get("diameter_mm"),
                    "dim_espesor_mm": dims_d.get("espesor_mm"),
                    "dim_confidence": dims_d.get("confidence","medium"),
                    "dim_notes": f"Derivado de {base_row['handle']}",
                    "G": G_d or None, "D": D_d or None,
                }
                ok_d, msg_d = save_to_db(product_d,
                    f"Derivado de {base_row['handle']}",
                    filename_d or "derivado", force_update=True)
                if ok_d:
                    save_bom_db(new_handle_d, mat_rows_d, cons_rows_d, otros_rows_d)
                    get_sb().table("products").update({
                        "c_value": c_val_d, "x_flags": json.dumps(x_active_d),
                    }).eq("handle", new_handle_d).execute()
                    st.success(f"{msg_d} · BOM ${bom_total_d:,}")
                    st.balloons()
                    st.cache_data.clear()
                else:
                    st.error(msg_d)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Subir plano a existente + ingresar BOM real
    # Replaces extrapolated BOM with measured one. Works for anchors too.
    # ══════════════════════════════════════════════════════════════════════════
    with tab_bom:
        st.caption("Sube el plano de un producto ya existente (ancla u otro) e ingresa su BOM real medido, reemplazando los valores extrapolados.")
        st.divider()

        qb = st.text_input("🔎 Buscar producto existente", placeholder="ej: lavadero-2-tazas…", key="bom_query")
        if not qb:
            st.info("Busca el producto al que quieres ingresar el BOM real.")
            st.stop()

        results_b = search_products(qb)
        if not results_b:
            st.warning("Sin resultados.")
            st.stop()

        opts_b = {f"{r['handle']}  —  {(r.get('descripcion_web') or '')[:55]}": r["handle"]
                  for r in results_b}
        sel_b    = st.selectbox("Selecciona producto", list(opts_b.keys()), key="bom_sel")
        row_b    = get_product(opts_b[sel_b])

        if not row_b:
            st.stop()

        # ── Product header ─────────────────────────────────────────────────
        ic, fc = st.columns([1, 3])
        with ic:
            if row_b.get("image_url"):
                st.markdown(f'<img src="{row_b["image_url"]}" style="width:100%;border-radius:4px;">', unsafe_allow_html=True)
        with fc:
            is_anchor = bool(row_b.get("is_anchor"))
            st.markdown(
                f"**{row_b['handle']}**"
                + (" 🌟 ancla" if is_anchor else "")
            )
            st.caption(row_b.get("descripcion_web","") or "")
            m1, m2, m3 = st.columns(3)
            m1.metric("Perfil", row_b.get("perfil_proceso","—"))
            m2.metric("Complejidad", row_b.get("complejidad","—"))
            m3.metric("G / D", f"{row_b.get('G','—')} / {row_b.get('D','—')}")

        has_bom_b = bool(row_b.get("bom_materials") and row_b["bom_materials"] != "[]")
        if has_bom_b:
            st.info("✅ Este producto ya tiene BOM guardado. Edita abajo para actualizarlo.")
        elif is_anchor:
            st.warning("⭐ Este es un producto ancla sin BOM ingresado — sus datos se usan para extrapolar al resto del perfil.")

        # ── Optional: upload drawing ───────────────────────────────────────
        st.divider()
        st.subheader("Plano (opcional)")
        image_bytes_b, filename_b, extraction_b = _upload_and_extract(rules, f"bom_{row_b['handle']}")

        # ── Processes reference ────────────────────────────────────────────
        st.divider()
        st.subheader("Procesos para esta complejidad")
        show_process_panel(row_b.get("perfil_proceso",""), row_b.get("complejidad",""), rules)

        # ── BOM editor ─────────────────────────────────────────────────────
        st.divider()
        st.subheader("BOM real medido")
        saved_mat_b  = json.loads(row_b.get("bom_materials","[]") or "[]")
        saved_cons_b = json.loads(row_b.get("bom_consumables","[]") or "[]")
        _ext_mat_b   = _bom_from_extraction(extraction_b)
        # Materials: Vision overrides saved only if product has no BOM yet
        if _ext_mat_b and not saved_mat_b:
            st.caption("🔍 Materiales pre-cargados desde Vision (sin BOM previo). Verifica antes de guardar.")
            _init_mat_b = _ext_mat_b
        else:
            _init_mat_b = saved_mat_b
        # Consumibles: saved if available, else pull from process rules
        _init_cons_b = saved_cons_b if saved_cons_b else _cons_from_rules(
            row_b.get("perfil_proceso",""), row_b.get("complejidad",""), rules
        )

        mat_rows_b, cons_rows_b, otros_rows_b, bom_total_b = bom_editor_widget(
            row_b["handle"], _init_mat_b, _init_cons_b,
            key_prefix=f"bom_{row_b['handle']}",
            saved_otros=json.loads(row_b.get("bom_otros","[]") or "[]") if row_b.get("bom_otros") else None,
        )

        st.divider()
        st.subheader("Costo total")
        _cost_summary(row_b.get("perfil_proceso",""), row_b.get("complejidad",""),
                      sum(r.get("total_clp", r.get("total", 0)) for r in mat_rows_b),
                      sum(r.get("Total",0) for r in cons_rows_b),
                      bom_total_b, rules)

        st.divider()
        if st.button("💾 Guardar BOM real", type="primary",
                     use_container_width=True, key="save_bom_existing"):
            save_bom_db(row_b["handle"], mat_rows_b, cons_rows_b, otros_rows_b)
            anchor_note = " (ancla actualizada — los productos extrapolados se recalcularán)" if is_anchor else ""
            st.success(f"✅ BOM guardado para **{row_b['handle']}**  ·  Total: ${bom_total_b:,}{anchor_note}")
            st.cache_data.clear()


if __name__ == "__main__":
    main()
