"""
Drawing Analyzer — extract measurements from engineering drawings via Claude Vision.

Part of the Dulox categorization dashboard.
Run the main app with:  streamlit run scripts/review.py
"""

import io
import json
import base64
import os
import re
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

import anthropic

# ─── Constants ────────────────────────────────────────────────────────────────

MODEL      = "claude-opus-4-5"
DOT_RADIUS = 8
FONT_SIZE  = 13

COLOR_DEFAULT     = (0, 200, 180, 220)   # teal  — normal annotation dot
COLOR_SELECTED    = (160, 32, 240, 230)  # purple — highlighted annotation
COLOR_LABEL_BG    = (255, 255, 255, 200) # white with alpha
COLOR_LABEL_TEXT  = (30, 30, 30)

SYSTEM_PROMPT = """You are an engineering drawing analyzer.
Extract ALL labeled parts and measurements visible in the drawing.
Return ONLY valid JSON — no markdown, no preamble.
Format:
[
  {
    "id": 1,
    "label": "Total Length",
    "value": "393.00",
    "unit": "mm",
    "x_pct": 0.45,
    "y_pct": 0.12
  }
]
x_pct and y_pct are float values 0.0-1.0 representing
the approximate position of the annotation on the image."""

# ─── Claude Vision ─────────────────────────────────────────────────────────────

def analyze_image_with_claude(image_bytes: bytes, filename: str) -> list[dict]:
    """Send image to Claude Vision and return extracted parts list."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error(
            "**ANTHROPIC_API_KEY no configurado.**  "
            "Defínelo en tu terminal antes de iniciar Streamlit:\n\n"
            "```bash\nexport ANTHROPIC_API_KEY=sk-ant-...\n```"
        )
        return []

    client = anthropic.Anthropic(api_key=api_key)

    # Detect media type
    if filename.lower().endswith(".png"):
        media_type = "image/png"
    elif filename.lower().endswith((".jpg", ".jpeg")):
        media_type = "image/jpeg"
    elif filename.lower().endswith(".webp"):
        media_type = "image/webp"
    else:
        media_type = "image/png"

    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    try:
        with st.spinner(f"Analizando {filename} con Claude Vision…"):
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Extrae todas las medidas etiquetadas de este plano de ingeniería.",
                        },
                    ],
                }],
            )
    except anthropic.BadRequestError as e:
        msg = str(e)
        if "credit balance is too low" in msg or "402" in msg:
            st.error(
                "**Anthropic API — saldo insuficiente.**  \n"
                "Recarga en [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing) "
                "y vuelve a intentarlo."
            )
        else:
            st.error(f"**Error en la solicitud a la API:** {msg}")
        return []
    except anthropic.AuthenticationError:
        st.error(
            "**API key inválida.**  \n"
            "Verifica tu variable de entorno `ANTHROPIC_API_KEY`."
        )
        return []
    except anthropic.APIConnectionError:
        st.error("**No se pudo conectar con la API de Anthropic.** Verifica tu conexión a internet.")
        return []
    except anthropic.APIStatusError as e:
        st.error(f"**Error Anthropic API {e.status_code}:** {e.message}")
        return []

    raw = response.content[0].text.strip()

    # Strip markdown fences if model wraps in ```json ... ```
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        parts = json.loads(raw)
        # Ensure each part has required fields and sequential ids
        for i, p in enumerate(parts, 1):
            p.setdefault("id", i)
            p.setdefault("label", "")
            p.setdefault("value", "")
            p.setdefault("unit", "mm")
            p.setdefault("x_pct", 0.5)
            p.setdefault("y_pct", 0.5)
        return parts
    except json.JSONDecodeError as e:
        st.error(f"Claude devolvió JSON inválido: {e}\n\nRespuesta recibida:\n```\n{raw[:500]}\n```")
        return []

# ─── Annotation overlay ────────────────────────────────────────────────────────

def render_overlay(image_bytes: bytes, parts: list[dict], selected_id: int | None) -> Image.Image:
    """Draw annotation dots and labels on a copy of the image."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    W, H = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", FONT_SIZE)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", FONT_SIZE - 2)
    except Exception:
        font = ImageFont.load_default()
        font_small = font

    for part in parts:
        x = int(part.get("x_pct", 0.5) * W)
        y = int(part.get("y_pct", 0.5) * H)
        is_selected = part.get("id") == selected_id

        color = COLOR_SELECTED if is_selected else COLOR_DEFAULT
        r = DOT_RADIUS + (4 if is_selected else 0)

        # Dot
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)

        # Label text
        label_text = f"{part.get('label', '')}: {part.get('value', '')} {part.get('unit', '')}".strip()
        if label_text == ":":
            label_text = f"[{part.get('id', '?')}]"

        bbox = draw.textbbox((0, 0), label_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad = 4

        # Position label to the right, flip left if near edge
        lx = x + r + 6
        ly = y - th // 2
        if lx + tw + pad * 2 > W:
            lx = x - r - tw - pad * 2 - 6

        # Label background
        draw.rectangle(
            [lx - pad, ly - pad, lx + tw + pad, ly + th + pad],
            fill=COLOR_LABEL_BG,
        )
        draw.text((lx, ly), label_text, fill=COLOR_LABEL_TEXT, font=font)

    # Composite onto image
    result = Image.alpha_composite(img, overlay)
    return result.convert("RGB")

# ─── Session state helpers ─────────────────────────────────────────────────────

def get_state(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

def parts_key(filename):
    return f"parts_{filename}"

def selected_key(filename):
    return f"selected_{filename}"

# ─── Export helpers ────────────────────────────────────────────────────────────

def export_single(filename: str, parts: list[dict]) -> bytes:
    return json.dumps(parts, indent=2, ensure_ascii=False).encode("utf-8")

def export_all(analyzed: dict) -> bytes:
    return json.dumps(analyzed, indent=2, ensure_ascii=False).encode("utf-8")

# ─── Page ─────────────────────────────────────────────────────────────────────

DRAWING_CSS = """
<style>
html, body, [data-testid="stAppViewContainer"] { background-color:#0d1117; color:#e6edf3; }
[data-testid="stSidebar"] { background-color:#161b22 !important; border-right:1px solid #30363d; }
h1,h2,h3 { color:#f0f6fc !important; }
.da-card {
    background:#161b22; border:1px solid #30363d; border-radius:10px;
    padding:1rem 1.2rem; margin-bottom:0.8rem;
}
.da-panel {
    background:#0d1117; border:1px solid #21262d; border-radius:8px;
    padding:0.8rem 1rem; margin-bottom:0.5rem;
}
.da-label {
    font-size:0.68rem; font-weight:700; text-transform:uppercase;
    letter-spacing:0.1em; color:#768390; margin-bottom:0.25rem;
}
.da-badge {
    display:inline-block; background:#1c2128; border:1px solid #388bfd;
    color:#79c0ff; border-radius:12px; padding:2px 10px;
    font-size:0.75rem; font-weight:600;
}
[data-testid="metric-container"] {
    background:#161b22; border:1px solid #30363d; border-radius:8px; padding:0.75rem 1rem;
}
[data-testid="metric-container"] label { color:#768390 !important; font-size:0.75rem; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color:#e6edf3 !important; }
[data-testid="stExpander"] {
    background:#161b22 !important; border:1px solid #30363d !important;
    border-radius:8px !important; margin-bottom:4px;
}
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {
    background:#0d1117 !important; border:1px solid #30363d !important;
    color:#e6edf3 !important; border-radius:6px;
}
[data-testid="stBaseButton-secondary"] {
    background:#21262d !important; border:1px solid #30363d !important;
    color:#cdd9e5 !important; border-radius:6px;
}
[data-testid="stBaseButton-secondary"]:hover {
    background:#30363d !important; border-color:#58a6ff !important;
}
[data-testid="stBaseButton-primary"] {
    background:#1f6feb !important; border:1px solid #388bfd !important;
    color:#fff !important; font-weight:600; border-radius:6px;
}
hr { border-color:#21262d !important; }
[data-testid="stCaptionContainer"] p { color:#768390 !important; font-size:0.78rem; }
</style>
"""

def main():
    st.markdown(DRAWING_CSS, unsafe_allow_html=True)
    st.markdown(
        '<h2 style="border-bottom:1px solid #21262d;padding-bottom:0.5rem;">'
        '📐 Analizador de Planos</h2>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p style="color:#8b949e;font-size:0.9rem;margin-bottom:1.5rem;">'
        'Sube planos de ingeniería — Claude Vision extrae todas las medidas etiquetadas. '
        'Revisa, edita y exporta como JSON.</p>',
        unsafe_allow_html=True
    )

    # ── Upload ────────────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Subir planos",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        help="Sube uno o más planos de ingeniería",
    )

    if not uploaded:
        st.info("Sube al menos un plano de ingeniería para comenzar.")
        return

    # Build filename → bytes map (deduplicated by name)
    files: dict[str, bytes] = {f.name: f.read() for f in uploaded}

    # ── Image selector ────────────────────────────────────────────────────────
    filenames = list(files.keys())
    if len(filenames) == 1:
        active_name = filenames[0]
    else:
        active_name = st.selectbox(
            "Seleccionar plano", filenames,
            key="active_drawing"
        )

    active_bytes = files[active_name]
    p_key = parts_key(active_name)
    s_key = selected_key(active_name)

    # ── Re-upload guard: same filename, different content ─────────────────────
    existing_bytes_key = f"bytes_{active_name}"
    if existing_bytes_key in st.session_state:
        if st.session_state[existing_bytes_key] != active_bytes and p_key in st.session_state:
            st.warning(
                f"**{active_name}** ya fue analizado. "
                "El archivo subido parece diferente. ¿Volver a analizar?"
            )
            if st.button("🔄 Volver a analizar (descartar ediciones)", key=f"reanalyze_{active_name}"):
                del st.session_state[p_key]
                st.session_state[existing_bytes_key] = active_bytes
                st.rerun()
            return  # pause until user decides

    st.session_state[existing_bytes_key] = active_bytes

    # ── Auto-analyze if not yet done ─────────────────────────────────────────
    if p_key not in st.session_state:
        parts = analyze_image_with_claude(active_bytes, active_name)
        if not parts:
            return
        # Ensure ids are sequential integers
        for i, p in enumerate(parts, 1):
            p["id"] = i
        st.session_state[p_key] = parts
        st.session_state[s_key] = None

    parts: list[dict] = st.session_state[p_key]
    selected_id: int | None = st.session_state.get(s_key)

    # ── Two-column layout ─────────────────────────────────────────────────────
    col_img, col_panel = st.columns([3, 2])

    # ── Left: annotated image ─────────────────────────────────────────────────
    with col_img:
        annotated = render_overlay(active_bytes, parts, selected_id)
        st.image(annotated, width='stretch', caption=active_name)

        # Botones de exportación bajo la imagen
        st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="da-label">EXPORTAR</div>',
            unsafe_allow_html=True
        )
        ecol1, ecol2 = st.columns(2)
        stem = active_name.rsplit(".", 1)[0]
        with ecol1:
            st.download_button(
                "⬇️ Descargar JSON de este plano",
                data=export_single(active_name, parts),
                file_name=f"{stem}_medidas.json",
                mime="application/json",
                use_container_width=True,
            )
        with ecol2:
            analyzed_all = {
                name: st.session_state.get(parts_key(name), [])
                for name in filenames
                if parts_key(name) in st.session_state
            }
            st.download_button(
                "⬇️ Descargar todos los planos JSON",
                data=export_all(analyzed_all),
                file_name="todas_las_medidas.json",
                mime="application/json",
                use_container_width=True,
                disabled=len(analyzed_all) == 0,
            )

    # ── Right: editable parts panel ───────────────────────────────────────────
    with col_panel:
        st.markdown(
            f'<div class="da-label">MEDIDAS DETECTADAS</div>'
            f'<div style="font-size:1.4rem;font-weight:700;color:#e6edf3;margin-bottom:0.8rem;">'
            f'{len(parts)}</div>',
            unsafe_allow_html=True
        )

        changed = False

        for idx, part in enumerate(parts):
            pid = part.get("id", idx + 1)
            label_preview = part.get("label") or f"Parte {pid}"
            value_preview = part.get("value", "")
            unit_preview  = part.get("unit", "")
            header = f"**{pid}** · {label_preview}: {value_preview} {unit_preview}".strip()

            is_selected = pid == selected_id
            expander_label = ("🔵 " if is_selected else "") + header

            with st.expander(expander_label, expanded=is_selected):
                new_label = st.text_input(
                    "Etiqueta", value=part.get("label", ""),
                    key=f"label_{active_name}_{pid}"
                )
                c1, c2 = st.columns([2, 1])
                with c1:
                    new_value = st.text_input(
                        "Valor", value=part.get("value", ""),
                        key=f"value_{active_name}_{pid}"
                    )
                with c2:
                    new_unit = st.text_input(
                        "Unidad", value=part.get("unit", "mm"),
                        key=f"unit_{active_name}_{pid}"
                    )

                x_col, y_col = st.columns(2)
                with x_col:
                    new_x = st.number_input(
                        "Pos X (0–1)", min_value=0.0, max_value=1.0, step=0.01,
                        value=float(part.get("x_pct", 0.5)),
                        key=f"x_{active_name}_{pid}"
                    )
                with y_col:
                    new_y = st.number_input(
                        "Pos Y (0–1)", min_value=0.0, max_value=1.0, step=0.01,
                        value=float(part.get("y_pct", 0.5)),
                        key=f"y_{active_name}_{pid}"
                    )

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("🎯 Resaltar", key=f"hl_{active_name}_{pid}",
                                 use_container_width=True):
                        st.session_state[s_key] = pid
                        st.rerun()
                with btn_col2:
                    if st.button("🗑️ Eliminar", key=f"del_{active_name}_{pid}",
                                 use_container_width=True):
                        st.session_state[p_key] = [p for p in parts if p.get("id") != pid]
                        if st.session_state.get(s_key) == pid:
                            st.session_state[s_key] = None
                        st.rerun()

                # Apply edits back to state
                if (new_label != part.get("label") or
                        new_value != part.get("value") or
                        new_unit  != part.get("unit")  or
                        abs(new_x - part.get("x_pct", 0.5)) > 1e-4 or
                        abs(new_y - part.get("y_pct", 0.5)) > 1e-4):
                    part["label"] = new_label
                    part["value"] = new_value
                    part["unit"]  = new_unit
                    part["x_pct"] = new_x
                    part["y_pct"] = new_y
                    changed = True

        # ── Add part ──────────────────────────────────────────────────────────
        st.divider()
        if st.button("➕ Agregar medida", use_container_width=True):
            new_id = max((p.get("id", 0) for p in parts), default=0) + 1
            parts.append({
                "id": new_id, "label": "", "value": "", "unit": "mm",
                "x_pct": 0.5, "y_pct": 0.5
            })
            st.session_state[p_key] = parts
            st.session_state[s_key] = new_id
            st.rerun()

        if changed:
            st.session_state[p_key] = parts
            st.rerun()

    # ── Session summary (bottom) ──────────────────────────────────────────────
    analyzed_count = sum(
        1 for name in filenames if parts_key(name) in st.session_state
    )
    if len(filenames) > 1:
        total_m = sum(len(st.session_state.get(parts_key(n), [])) for n in filenames)
        st.markdown(
            f'<div style="margin-top:1rem;padding:0.6rem 1rem;background:#161b22;'
            f'border:1px solid #30363d;border-radius:8px;font-size:0.78rem;color:#768390;">'
            f'Sesión · {analyzed_count}/{len(filenames)} planos analizados · '
            f'<span style="color:#58a6ff;">{total_m} medidas totales</span></div>',
            unsafe_allow_html=True
        )


main()
