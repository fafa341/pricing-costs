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
import sqlite3
import numpy as np
from pathlib import Path
from datetime import datetime

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import anthropic

ROOT       = Path(__file__).resolve().parent.parent.parent
DB         = ROOT / "dataset" / "products.db"
RULES_FILE = ROOT / "files-process" / "PROCESS_RULES.json"

MODEL = "claude-opus-4-5"

# ─── Load PROCESS_RULES.json ──────────────────────────────────────────────────

@st.cache_data
def load_rules() -> dict:
    try:
        return json.loads(RULES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

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
  "scale": "string or null — scale indicated, e.g. 1:20"
}

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

Preserve Spanish component names as they appear in the drawing."""

def call_claude_vision(image_bytes: bytes, filename: str, rules: dict) -> dict | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error("**ANTHROPIC_API_KEY no configurado.** Configura la variable de entorno antes de iniciar Streamlit.")
        return None

    ext = filename.rsplit(".", 1)[-1].lower()
    media_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                  "png": "image/png", "webp": "image/webp"}.get(ext, "image/png")
    b64 = base64.standard_b64encode(image_bytes).decode()

    client = anthropic.Anthropic(api_key=api_key)

    try:
        with st.spinner("Analizando plano con Claude Vision…"):
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=EXTRACTION_SYSTEM,
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

# ─── DB operations ────────────────────────────────────────────────────────────

def handle_exists(handle: str) -> bool:
    conn = sqlite3.connect(DB)
    exists = conn.execute("SELECT id FROM products WHERE handle=?", (handle,)).fetchone() is not None
    conn.close()
    return exists

def save_to_db(product: dict, razon: str, source_file: str, force_update: bool = False) -> tuple[bool, str]:
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL")
    now = datetime.now().isoformat()
    handle = product["handle"]

    try:
        exists = conn.execute("SELECT perfil_proceso, complejidad FROM products WHERE handle=?", (handle,)).fetchone()

        if exists and not force_update:
            conn.close()
            return False, f"Handle `{handle}` ya existe. Activa 'Forzar actualización'."

        cols = ["handle","perfil_proceso","complejidad","k_num","familia","subfamilia",
                "descripcion_web","url","dim_l_mm","dim_w_mm","dim_h_mm","dim_diameter_mm",
                "dim_espesor_mm","dim_confidence","dim_notes","G","D",
                "validated","validated_by","validated_at","imported_at"]

        vals = [
            handle, product["perfil_proceso"], product["complejidad"],
            {"C1":1,"C2":2,"C3":3}.get(product["complejidad"]),
            product.get("familia",""), product.get("subfamilia",""),
            product.get("descripcion",""), product.get("url",""),
            product.get("dim_l_mm"), product.get("dim_w_mm"), product.get("dim_h_mm"),
            product.get("dim_diameter_mm"), product.get("dim_espesor_mm"),
            product.get("dim_confidence","high"), product.get("dim_notes",""),
            product.get("G"), product.get("D"),
            1, "drawing-intake", now, now,
        ]

        if exists:
            set_clause = ", ".join(f"{c}=?" for c in cols[1:])
            conn.execute(f"UPDATE products SET {set_clause} WHERE handle=?", vals[1:] + [handle])
            action = "updated"
        else:
            placeholders = ", ".join("?" * len(cols))
            conn.execute(f"INSERT INTO products ({', '.join(cols)}) VALUES ({placeholders})", vals)
            action = "inserted"

        conn.execute("""
            INSERT INTO categorization_history
              (handle, old_perfil, new_perfil, old_complejidad, new_complejidad,
               reason, changed_by, changed_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            handle,
            exists[0] if exists else None, product["perfil_proceso"],
            exists[1] if exists else None, product["complejidad"],
            f"[drawing-intake] {razon} | source: {source_file}",
            "drawing-intake", now,
        ))

        conn.commit()
        conn.close()
        return True, f"✅ Producto `{handle}` {action} en products.db"

    except Exception as e:
        conn.close()
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

# ─── Main page ────────────────────────────────────────────────────────────────

def main():
    st.header("🔩 Ingreso de Producto desde Plano")
    st.markdown(
        "Sube un plano de ingeniería → Claude extrae las dimensiones y componentes → "
        "el sistema calcula los drivers G/D/C/X → tú confirmas la clasificación → "
        "guardamos en la base de datos."
    )

    rules = load_rules()
    if not rules:
        st.warning("⚠️ No se pudo cargar `PROCESS_RULES.json`. Los umbrales de clasificación usarán valores por defecto.")

    # ── Step 1: Upload ────────────────────────────────────────────────────────
    st.subheader("1 · Subir plano")
    uploaded = st.file_uploader(
        "Plano de ingeniería",
        type=["png", "jpg", "jpeg", "webp"],
        help="Plano técnico, sketch de fabricación, o CAD exportado"
    )

    if not uploaded:
        st.info("Sube un plano para comenzar.")
        return

    image_bytes = uploaded.read()
    filename    = uploaded.name
    cache_key   = f"intake_{filename}"

    # ── Step 2: Vision extraction ─────────────────────────────────────────────
    st.subheader("2 · Extracción técnica")

    col_img, col_extract = st.columns([3, 2])

    with col_img:
        # Show image with overlay (updates after extraction)
        extraction = st.session_state.get(cache_key)
        if extraction:
            annotated = render_dimension_overlay(image_bytes, extraction)
            st.image(annotated, use_container_width=True, caption=filename)
        else:
            st.image(image_bytes, use_container_width=True, caption=filename)

    with col_extract:
        if extraction is None:
            if st.button("🔍 Analizar plano con Claude Vision", type="primary",
                         use_container_width=True):
                result = call_claude_vision(image_bytes, filename, rules)
                if result:
                    st.session_state[cache_key] = result
                    st.rerun()
        else:
            st.success("✅ Extracción completada")
            if st.button("🔄 Re-analizar", use_container_width=True):
                del st.session_state[cache_key]
                st.rerun()

            # Show raw extraction summary
            dims = extraction.get("dimensions", {})
            sf   = extraction.get("special_features", {})

            st.markdown(f"**{extraction.get('drawing_title', filename)}**")
            st.markdown(f"Material: `{extraction.get('material', 'No especificado')}`")
            if extraction.get("scale"):
                st.caption(f"Escala: {extraction['scale']}")

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                for k, label in [("l_mm","L"), ("w_mm","W"), ("h_mm","H")]:
                    v = dims.get(k)
                    st.metric(f"{label} (mm)", v if v else "—")
            with col_d2:
                for k, label in [("diameter_mm","Ø"), ("espesor_mm","Espesor")]:
                    v = dims.get(k)
                    st.metric(f"{label} (mm)", v if v else "—")

            conf = dims.get("confidence","—")
            conf_color = {"high":"🟢","medium":"🟡","low":"🔴"}.get(conf,"⚪")
            st.caption(f"Confianza: {conf_color} {conf}")
            if dims.get("notes"):
                st.caption(dims["notes"])

            # Special features detected
            features = []
            if sf.get("has_mechanism"):   features.append(f"⚙️ Mecanismo: {sf.get('mechanism_type','sí')}")
            if sf.get("has_mirror_finish"): features.append("✨ Acabado espejo")
            if sf.get("multiple_compartments"): features.append(f"📦 {sf.get('num_compartments',3)}+ compartimientos")
            if sf.get("has_electrical"):  features.append("⚡ Eléctrico")
            if sf.get("num_quemadores"):  features.append(f"🔥 {sf['num_quemadores']} quemadores")
            if sf.get("num_niveles"):     features.append(f"📚 {sf['num_niveles']} niveles")
            if sf.get("num_tazas"):       features.append(f"🚿 {sf['num_tazas']} tazas")
            if sf.get("capacidad_litros"): features.append(f"💧 {sf['capacidad_litros']}L")
            if sf.get("has_wheels"):      features.append("🛞 Ruedas")
            if features:
                st.markdown("**Características:** " + "  ·  ".join(features))

            # Components
            comps = extraction.get("components", [])
            if comps:
                with st.expander(f"🔩 {len(comps)} componentes extraídos"):
                    for c in comps:
                        st.markdown(
                            f"- **{c.get('nombre','?')}** ×{c.get('cantidad',1)}  "
                            f"— {c.get('material') or '—'}  "
                            f"— {c.get('dims_raw') or '—'}"
                        )

    if extraction is None:
        return

    st.divider()

    # ── Step 3: Classification ────────────────────────────────────────────────
    st.subheader("3 · Clasificación G/D/C/X")

    dims = extraction.get("dimensions", {})
    sf   = extraction.get("special_features", {})

    # Python-computed G and D (deterministic — never from LLM)
    l_mm  = dims.get("l_mm")
    w_mm  = dims.get("w_mm")
    esp   = dims.get("espesor_mm")
    diam  = dims.get("diameter_mm")

    # For cylindrical products without L×W, approximate via diameter
    if (l_mm is None or w_mm is None) and diam:
        l_mm = diam
        w_mm = diam

    G = compute_G(l_mm, w_mm, rules)
    D = compute_D(esp, rules)

    col_g, col_d, col_c, col_x = st.columns(4)
    with col_g:
        st.markdown(driver_badge(G, "G (Geometría)"))
        if l_mm and w_mm:
            area = l_mm * w_mm
            st.caption(f"Área: {area:,.0f} mm²")
        else:
            st.caption("Sin L×W — G no calculable")
    with col_d:
        st.markdown(driver_badge(D, "D (Espesor)"))
        if esp:
            st.caption(f"Espesor: {esp} mm")
        else:
            st.caption("Espesor no encontrado")
    with col_c:
        c_val = (sf.get("num_quemadores") or sf.get("num_niveles") or
                 sf.get("num_tazas") or sf.get("capacidad_litros"))
        if c_val:
            st.markdown(f"⚙️ **C (Componentes)** = {c_val}")
        else:
            st.markdown("⚙️ **C (Componentes)** = —")
            st.caption("No detectado automáticamente")
    with col_x:
        x_list = []
        if sf.get("has_mechanism"):      x_list.append("mecanismo")
        if sf.get("has_mirror_finish"):  x_list.append("multifinic")
        if sf.get("multiple_compartments"): x_list.append("compartimientos")
        if x_list:
            st.markdown(f"🏷️ **X (Flags)** = {', '.join(x_list)}")
        else:
            st.markdown("🏷️ **X (Flags)** = ninguno")

    st.divider()

    # ── Step 4: Review & Edit form ────────────────────────────────────────────
    st.subheader("4 · Revisar y confirmar")

    suggested_perfil = extraction.get("suggested_perfil", "p-custom")
    suggested_razon  = extraction.get("suggested_razon_perfil", "")

    # Pre-compute complexity suggestion
    x_flags_active = [f for f, flag in [
        ("terminacion_multifinic", sf.get("has_mirror_finish")),
        ("tiene_mecanismo",        sf.get("has_mechanism")),
        ("multiples_compartimientos", sf.get("multiple_compartments")),
    ] if flag]

    c_driver_val = (sf.get("num_quemadores") or sf.get("num_niveles") or
                    sf.get("num_tazas") or sf.get("capacidad_litros"))

    pts, breakdown = compute_complexity_points(
        G, D, suggested_perfil, x_flags_active, c_driver_val, rules
    )
    suggested_comp = points_to_complexity(pts, suggested_perfil, rules) or "C1"

    # Show AI suggestion with reasoning
    with st.container(border=True):
        st.markdown("**Sugerencia del modelo:**")
        scol1, scol2 = st.columns(2)
        with scol1:
            st.markdown(f"Perfil: **`{suggested_perfil}`**")
            if suggested_razon:
                st.caption(suggested_razon)
        with scol2:
            st.markdown(f"Complejidad: **`{suggested_comp}`**  ({pts} puntos)")
            if breakdown:
                breakdown_str = "  +  ".join(f"{k}={v}" for k,v in breakdown.items())
                st.caption(f"Desglose: {breakdown_str}")

    st.markdown("**Editar clasificación:**")

    form_col1, form_col2 = st.columns(2)

    with form_col1:
        perfil = profile_selector(rules, default=suggested_perfil)

        # Recompute on perfil change
        pts2, breakdown2 = compute_complexity_points(
            G, D, perfil, x_flags_active, c_driver_val, rules
        )
        auto_comp = points_to_complexity(pts2, perfil, rules) or "C1"
        valid_comps = complexity_options_for(perfil, rules)
        comp_idx = valid_comps.index(auto_comp) if auto_comp in valid_comps else 0
        complejidad = st.selectbox("Complejidad", valid_comps, index=comp_idx)

        # Show complexity description
        if rules and perfil in rules.get("profiles", {}):
            comp_desc = rules["profiles"][perfil].get("complexity_thresholds", {}).get(complejidad, {}).get("description", "")
            if comp_desc:
                st.caption(f"ℹ️ {comp_desc}")

    with form_col2:
        # Build a handle suggestion from the drawing title
        raw_title = extraction.get("drawing_title", filename.rsplit(".",1)[0])
        handle_suggestion = re.sub(r'[^a-z0-9\-]', '-', raw_title.lower())
        handle_suggestion = re.sub(r'-+', '-', handle_suggestion).strip('-')[:50]

        handle = st.text_input(
            "Handle (identificador único)",
            value=handle_suggestion,
            help="Solo minúsculas, guiones y números. Ej: tina-quesera-200l-tq-0200"
        )

        nombre = st.text_input(
            "Nombre del producto",
            value=extraction.get("drawing_title", "")
        )

        familia = st.text_input("Familia", value="")
        subfamilia = st.text_input("Subfamilia", value="")

    descripcion = st.text_area(
        "Descripción técnica",
        value=extraction.get("drawing_title", "") + ". Material: " + extraction.get("material","AISI 304-L") + ".",
        height=80
    )

    razon_perfil = st.text_area(
        "Razón — perfil proceso *",
        value=suggested_razon or f"Perfil {perfil}: ",
        height=80,
        help="¿Por qué este producto pertenece a este perfil? Proceso dominante."
    )

    razon_comp = st.text_area(
        "Razón — complejidad *",
        value=f"{breakdown2}  →  {pts2} pts  →  {complejidad}" if breakdown2 else f"Complejidad {complejidad}.",
        height=60,
        help="¿Por qué esta complejidad? Citar los drivers."
    )

    fab_notes = extraction.get("fabrication_notes", "")
    dim_notes = dims.get("notes","")

    # ── Step 5: Save ──────────────────────────────────────────────────────────
    st.subheader("5 · Guardar en DB")

    force_update = st.checkbox("Forzar actualización si el handle ya existe")

    # Validate handle format
    handle_ok = bool(handle) and bool(re.match(r'^[a-z0-9][a-z0-9\-]+[a-z0-9]$', handle))
    razon_ok  = bool(razon_perfil.strip()) and bool(razon_comp.strip())

    if not handle_ok:
        st.warning("Handle inválido — solo minúsculas, guiones, números. Mínimo 3 caracteres.")
    if not razon_ok:
        st.warning("Completa las razones de perfil y complejidad antes de guardar.")

    # Check duplicate
    if handle_ok and handle_exists(handle) and not force_update:
        st.warning(f"⚠️ Handle `{handle}` ya existe en la DB. Activa 'Forzar actualización' para sobrescribir.")

    if st.button("💾 Guardar producto en base de datos", type="primary",
                 disabled=not (handle_ok and razon_ok),
                 use_container_width=True):

        # Final G/D recompute with user-confirmed dims
        final_G = compute_G(
            dims.get("l_mm") or (diam if diam else None),
            dims.get("w_mm") or (diam if diam else None),
            rules
        )
        final_D = compute_D(dims.get("espesor_mm"), rules)

        product = {
            "handle":          handle,
            "perfil_proceso":  perfil,
            "complejidad":     complejidad,
            "familia":         familia,
            "subfamilia":      subfamilia,
            "descripcion":     descripcion,
            "url":             "",
            "dim_l_mm":        dims.get("l_mm"),
            "dim_w_mm":        dims.get("w_mm"),
            "dim_h_mm":        dims.get("h_mm"),
            "dim_diameter_mm": dims.get("diameter_mm"),
            "dim_espesor_mm":  dims.get("espesor_mm"),
            "dim_confidence":  dims.get("confidence","medium"),
            "dim_notes":       f"{dim_notes} | {fab_notes}".strip(" |"),
            "G":               final_G,
            "D":               final_D,
        }

        razon = f"Perfil: {razon_perfil.strip()} | Complejidad: {razon_comp.strip()}"
        ok, msg = save_to_db(product, razon, filename, force_update=force_update)

        if ok:
            st.success(msg)
            st.balloons()
            # Clear cache so the product appears in other pages
            st.cache_data.clear()
            st.markdown(f"""
            **Próximos pasos:**
            - Verificar en **📋 Por Perfil** que el producto aparece correctamente
            - Correr `python3 scripts/audit_model.py --test outliers` para validar coherencia
            """)
        else:
            st.error(msg)


main()
