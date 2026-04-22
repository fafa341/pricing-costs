"""
review.py — Dulox Product Categorization Review App
=====================================================
Streamlit app for human-in-the-loop validation of perfil_proceso + complejidad.

Run:
  streamlit run scripts/review.py

Views:
  🔍 Revisar Candidatos   — 76 flagged products from audit (sorted by confidence gap)
  📋 Por Perfil           — browse all products in a perfil × complejidad bucket
  🔎 Buscar Producto      — reclassify any product by handle/description search
  📊 Dashboard            — validation progress + ICM components
"""

import re
import json
import requests
import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT       = Path(__file__).resolve().parent.parent
DB         = ROOT / "dataset" / "products.db"
RULES_PATH = ROOT / "files-process" / "PROCESS_RULES.json"

# Fallback list — used if PROCESS_RULES.json is unavailable, and as module-level
# default so PERFILES is always defined before main() updates it dynamically.
_PERFILES_FALLBACK = [
    "p-basurero-cil", "p-basurero-rect", "p-campana", "p-carro-bandejero",
    "p-carro-traslado", "p-cilindrico", "p-cocina-gas", "p-custom",
    "p-electrico", "p-laminar-simple", "p-laser", "p-lavadero",
    "p-meson", "p-modulo", "p-rejilla", "p-sumidero", "p-tina",
]
PERFILES = _PERFILES_FALLBACK  # updated dynamically in main() after rules + df load
COMPLEJIDADES = ["C1", "C2", "C3"]
KNOWN_PROCESSES = [
    "laser", "corte_manual", "armado_trazado", "plegado", "cilindrado",
    "soldadura", "pulido", "qc", "grabado_laser", "refrigeracion", "pintura",
]

# ─── PROCESS_RULES.json helpers ──────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def load_rules() -> dict:
    try:
        return json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_rules(rules: dict):
    RULES_PATH.write_text(json.dumps(rules, indent=2, ensure_ascii=False))
    st.cache_data.clear()

def get_perfiles(rules: dict, df=None) -> list[str]:
    """
    Dynamic union: profiles declared in PROCESS_RULES.json + profiles used in DB.
    This means a new profile created via the form is immediately available everywhere,
    and profiles assigned in DB but not yet in JSON are also shown.
    """
    from_json = sorted(rules.get("profiles", {}).keys())
    from_db   = sorted(df["perfil_proceso"].dropna().unique().tolist()) if df is not None else []
    merged    = sorted(set(from_json + from_db + _PERFILES_FALLBACK) - {"p-importado", ""})
    return merged


# ─── Profile knowledge: what C1/C2/C3 means per perfil ───────────────────────
# Used to show context in candidate review cards.
# Falls back gracefully for profiles created after this file was last edited.

PROFILE_CONTEXT = {
    "p-meson": {
        "primary_driver": "C (componentes/mecanismo)",
        "secondary_driver": "G (área)",
        "driver_note": "El tamaño (G) NO es el driver principal. Lo que diferencia C1→C3 son los componentes: puertas, cajones, cajoneras.",
        "levels": {
            "C1": "Mesón abierto sin mecanismo. Repisa inferior o sin ella. Proceso: corte + plegado + soldadura básica.",
            "C2": "Mesón con puertas frontales o correderas. Mecanismo simple. Soldadura + bisagras.",
            "C3": "Mesón cerrado con cajonera + puertas correderas. Múltiples compartimientos. Mayor tiempo ensamble.",
        },
        "cost_implication": "C2 ≈ 1.4× costo C1 en HH. C3 ≈ 2× costo C1. El driver es tiempo de ensamble y número de componentes comprados.",
    },
    "p-cilindrico": {
        "primary_driver": "D (espesor) + G (diámetro/área)",
        "secondary_driver": "—",
        "driver_note": "Piezas cilíndricas: poruñas, baldes, recipientes. El espesor define cuántas pasadas de cilindrado. El diámetro define tiempo de corte y soldadura del fondo.",
        "levels": {
            "C1": "Pieza pequeña, espesor ≤1.5mm. Poruñas 100–500g, baldes pequeños. 1 pasada cilindrado.",
            "C2": "Pieza mediana o espesor >1.5mm. Baldes 5–40L, recipientes industriales. 2–3 pasadas.",
            "C3": "No definido aún — todos los cilíndricos actuales son C1 o C2.",
        },
        "cost_implication": "C2 ≈ 1.6× C1 en tiempo cilindrado. Las poruñas asignadas C2 pueden ser C1 si espesor=1mm.",
    },
    "p-basurero-rect": {
        "primary_driver": "G (área) + X (características/acabado)",
        "secondary_driver": "—",
        "driver_note": "Basureros rectangulares. El tamaño define el área a pulir. El acabado (tapa pedal, compartimientos reciclaje, mecanismo especial) define X.",
        "levels": {
            "C1": "Basurero simple, sin mecanismo. Rectangular básico. Solo corte + plegado + soldadura.",
            "C2": "Con tapa de pedal o 2 compartimientos. Mecanismo simple. Más piezas.",
            "C3": "Reciclaje multicompartimiento (3+), tapa especial, o acabado visible de alta calidad. Máximo tiempo pulido.",
        },
        "cost_implication": "C3 tiene pulido completo (superficie visible). Consumibles pulido = 8× costo material para piezas de este tipo.",
    },
    "p-basurero-cil": {
        "primary_driver": "D (espesor) + G + X (mecanismo)",
        "secondary_driver": "—",
        "driver_note": "Basureros cilíndricos. El cilindrado es siempre obligatorio — es el proceso diferenciador de este perfil. El espesor define dificultad. El mecanismo (tapa pedal, aros decorativos) define X.",
        "levels": {
            "C1": "Cilíndrico simple, espesor 1mm, sin mecanismo. Corte + cilindrado + soldadura fondo.",
            "C2": "Con tapa o mecanismo, o espesor >1mm. Más piezas. Posible doble pared.",
            "C3": "No asignado aún en catálogo actual.",
        },
        "cost_implication": "El cilindrado es el costo dominante. Múltiples pasadas sobre madera. Proceso de especialista.",
    },
    "p-campana": {
        "primary_driver": "G (área de captación)",
        "secondary_driver": "—",
        "driver_note": "Campanas murales o centrales. El área define todo: cantidad de lámina, tiempo de plegado (requiere 2 operadores si L>1m), longitud de soldadura.",
        "levels": {
            "C1": "No existe en catálogo actual — todas las campanas son C2 o C3.",
            "C2": "Campana estándar mural. Área típica 1000–1500×800mm. 2 operadores para plegado.",
            "C3": "Campana central (cuelga del techo) o tamaño extra-grande. Mayor complejidad de instalación de ductos.",
        },
        "cost_implication": "Campanas son productos de alto costo por área. Factor escala lineal con L×W. Sin C1 en catálogo.",
    },
    "p-carro-bandejero": {
        "primary_driver": "C (número de niveles/bandejas)",
        "secondary_driver": "G (área base)",
        "driver_note": "Carros para transporte de bandejas. Lo que diferencia C1→C3 es la cantidad de niveles y bandejas. Un carro C3 tiene más niveles → más soldadura, más tiempo ensamble.",
        "levels": {
            "C1": "Carro simple, pocos niveles (1–2). Estructura básica. Pequeño o mediano.",
            "C2": "Carro estándar con 3–5 niveles o mayor capacidad. Estructura más elaborada.",
            "C3": "Carro de alta capacidad (6+ niveles), gran tamaño, o estructura especial (bicicletero grande).",
        },
        "cost_implication": "Cada nivel adicional suma HH de soldadura y tubería. Driver C no está en DB — las sugerencias de reclasificación usan solo G.",
    },
    "p-electrico": {
        "primary_driver": "G (área) + C (componentes eléctricos)",
        "secondary_driver": "—",
        "driver_note": "Equipos con resistencias eléctricas integradas (baños maría, sartenes basculantes). El área define la estructura. Los componentes eléctricos (cantidad de resistencias, depósitos, termostatos) definen C.",
        "levels": {
            "C1": "Equipo pequeño, 1–2 depósitos o resistencias. Estructura simple.",
            "C2": "Equipo mediano, 3–4 depósitos. Más cableado interno.",
            "C3": "Equipo grande o de alta complejidad eléctrica. Generalmente área grande + múltiples circuitos.",
        },
        "cost_implication": "Los componentes comprados (resistencias, termostatos) son costo fijo por unidad. La HH escala con G.",
    },
    "p-cocina-gas": {
        "primary_driver": "C (número de quemadores)",
        "secondary_driver": "G (área)",
        "driver_note": "Cocinas industriales a gas. El quemador es la unidad de complejidad — cada quemador adicional suma tubería de gas, válvulas, parrillas, soldadura.",
        "levels": {
            "C1": "1–2 quemadores. Anafe simple. Mínima tubería de gas.",
            "C2": "3–6 quemadores. Cocina estándar. Más manifold de gas, más parrillas.",
            "C3": "7+ quemadores o equipo especial (plancha churrasquera con baño maría, cocina + freidora). Mayor tiempo ensamble.",
        },
        "cost_implication": "C no está en DB. Las sugerencias actuales usan solo G. Un anafe de 1 quemador con G=1 asignado C2 es probablemente C1.",
    },
    "p-laminar-simple": {
        "primary_driver": "G (área)",
        "secondary_driver": "—",
        "driver_note": "Piezas laminares simples: cubrejuntas, tapas, repisas. El proceso es corte + plegado. El área define directamente el tiempo.",
        "levels": {
            "C1": "Pieza pequeña o mediana. Área <500k mm². Pocos dobleces.",
            "C2": "Pieza grande. Área 500k–1.5M mm². Más dobleces o longitud de corte mayor.",
            "C3": "No asignado en catálogo actual.",
        },
        "cost_implication": "Perfil más directo: costo ∝ área. factor_escala = área_producto / área_ancla.",
    },
    "p-lavadero": {
        "primary_driver": "C (número de tazas)",
        "secondary_driver": "G (área)",
        "driver_note": "Lavaderos y lavamanos. El número de tazas define la complejidad: cada taza requiere corte del sobre, plegado del faldón, soldadura perimetral.",
        "levels": {
            "C1": "1 taza pequeña. Lavamanos simple.",
            "C2": "1–2 tazas estándar, o taza profunda. Lavadero típico de cocina industrial.",
            "C3": "3+ tazas o taza especial (quirúrgico, con desconche). No asignado aún.",
        },
        "cost_implication": "Driver C no en DB. Lavaderos con G=1 asignados C2 pueden ser C1 si tienen solo 1 taza pequeña.",
    },
    "p-modulo": {
        "primary_driver": "G (área) + X (características)",
        "secondary_driver": "—",
        "driver_note": "Módulos de equipamiento: exhibidores, muebles de servicio. El tamaño y características especiales (vidrio, iluminación, puertas especiales) definen la complejidad.",
        "levels": {
            "C1": "Módulo simple, área pequeña, sin accesorios especiales.",
            "C2": "Módulo estándar o con algún accesorio. Área mediana.",
            "C3": "No asignado en catálogo actual.",
        },
        "cost_implication": "X (características) no en DB. Separación C1/C2 actualmente débil — grupos solapados según Test 2.",
    },
    "p-sumidero": {
        "primary_driver": "G (área)",
        "secondary_driver": "D (espesor)",
        "driver_note": "Sumideros de piso. El área de captación define el tamaño de la tapa y el marco. El espesor define resistencia y proceso.",
        "levels": {
            "C1": "Sumidero pequeño, espesor estándar 1mm.",
            "C2": "Sumidero más grande o espesor >1.5mm (mayor resistencia).",
            "C3": "No asignado en catálogo actual.",
        },
        "cost_implication": "Los sumideros con D=3 (espesor >2mm) asignados C2 podrían ser C1 si área es pequeña — revisar.",
    },
    "p-tina": {
        "primary_driver": "C (capacidad/compartimientos) + G",
        "secondary_driver": "D",
        "driver_note": "Tinas y prensas queseras. La capacidad en litros y número de compartimientos define la complejidad del proceso de fabricación.",
        "levels": {
            "C1": "No asignado en catálogo actual.",
            "C2": "Tina estándar 100–500L, 1 compartimiento.",
            "C3": "Tina de gran capacidad o prensa para múltiples moldes.",
        },
        "cost_implication": "Perfil pequeño (7 productos). Las tinas C2 con driver scores bajos pueden necesitar revisión.",
    },
    "p-custom": {
        "primary_driver": "G + C (caso a caso)",
        "secondary_driver": "X",
        "driver_note": "Productos a medida sin perfil estándar. La complejidad se asigna por juicio: C1=estructura simple, C2=estructura elaborada, C3=proyecto especial o alta dificultad.",
        "levels": {
            "C1": "Estructura simple. Corte + plegado + soldadura básica. Sin mecanismos especiales.",
            "C2": "Estructura elaborada. Múltiples piezas. Mecanismo o acabado especial.",
            "C3": "Proyecto especial: múltiples materiales, alta visibilidad, mecanismo complejo, o largo tiempo de fabricación.",
        },
        "cost_implication": "p-custom es el perfil con mayor varianza — los drivers G/D capturan poco. Las sugerencias deben tomarse como señales, no como órdenes.",
    },
    "p-rejilla": {
        "primary_driver": "C (número de barras/varillas) + G",
        "secondary_driver": "—",
        "driver_note": "Rejillas y celosías. El número de varillas soldadas define el tiempo de soldadura (el proceso dominante).",
        "levels": {
            "C1": "Rejilla simple, pocas varillas.",
            "C2": "Rejilla estándar con más varillas o mayor área.",
            "C3": "No asignado en catálogo actual.",
        },
        "cost_implication": "C (varillas) no en DB. Sugerencias basadas solo en G.",
    },
    "p-laser": {
        "primary_driver": "X (características del grabado) + D (espesor)",
        "secondary_driver": "—",
        "driver_note": "Piezas con trabajo láser. El tipo y complejidad del grabado/corte láser define la complejidad. El espesor define velocidad de corte.",
        "levels": {
            "C1": "Corte láser simple, sin grabado decorativo. Geometría básica.",
            "C2": "No asignado en catálogo actual.",
            "C3": "No asignado en catálogo actual.",
        },
        "cost_implication": "Solo C1 en catálogo. Todos son laser-simple actualmente.",
    },
}

def get_profile_context(perfil: str, rules: dict) -> dict:
    """
    Return PROFILE_CONTEXT entry for a perfil.
    Falls back to a generated context from PROCESS_RULES.json for new profiles.
    """
    if perfil in PROFILE_CONTEXT:
        return PROFILE_CONTEXT[perfil]
    # Auto-generate from rules for profiles created via the new-profile form
    if rules and perfil in rules.get("profiles", {}):
        p = rules["profiles"][perfil]
        drivers = " + ".join(p.get("primary_drivers", []) + p.get("secondary_drivers", []))
        thresholds = p.get("complexity_thresholds", {})
        levels = {lvl: t.get("description", f"{lvl} — sin descripción") for lvl, t in thresholds.items()}
        return {
            "primary_driver": drivers or "—",
            "secondary_driver": "—",
            "driver_note": p.get("description", "Perfil creado manualmente. Edita PROCESS_RULES.json para agregar contexto."),
            "levels": levels,
            "cost_implication": "Nuevo perfil — sin benchmarks de costo aún. Calibrar con calibration.py.",
        }
    return {
        "primary_driver": "desconocido",
        "secondary_driver": "—",
        "driver_note": "Perfil sin contexto registrado.",
        "levels": {"C1": "—", "C2": "—", "C3": "—"},
        "cost_implication": "Sin datos.",
    }


# ─── DB helpers ───────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@st.cache_data(ttl=5)
def load_products():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT id, handle, perfil_proceso, complejidad, k_num,
               familia, subfamilia, descripcion_web, url,
               dim_l_mm, dim_w_mm, dim_h_mm, dim_diameter_mm, dim_espesor_mm,
               dim_confidence, G, D, validated, validated_by, validated_at,
               image_url, bom_materials, bom_consumables
        FROM products
        WHERE perfil_proceso != 'p-importado'
        ORDER BY perfil_proceso, complejidad, handle
    """, conn)
    conn.close()
    return df


def save_bom(handle: str, mat_rows: list, cons_rows: list):
    conn = get_conn()
    conn.execute(
        "UPDATE products SET bom_materials=?, bom_consumables=? WHERE handle=?",
        (json.dumps(mat_rows, ensure_ascii=False),
         json.dumps(cons_rows, ensure_ascii=False),
         handle)
    )
    conn.commit()
    conn.close()
    st.cache_data.clear()


def product_bom_expander(row: dict, key_prefix: str = "bom"):
    """Inline BOM editor embedded inside a product card."""
    handle     = row.get("handle", "")
    saved_mat  = json.loads(row.get("bom_materials",  "[]") or "[]")
    saved_cons = json.loads(row.get("bom_consumables","[]") or "[]")

    mat_default  = saved_mat  or [{"Subconjunto":"","Dimensiones":"","Material":"","kg_ml":0.0,"precio_kg":3600,"total":0}]
    cons_default = saved_cons or [{"Producto":"","Proceso":"","Cantidad":0,"Unidad":"u","Precio_u":0,"Total":0}]

    prefix = f"{key_prefix}_{handle}"

    st.markdown('<div class="dulox-section-label" style="margin-bottom:0.35rem;">MATERIALES</div>', unsafe_allow_html=True)
    mat_df = st.data_editor(
        pd.DataFrame(mat_default),
        key=f"bomedit_mat_{prefix}",
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "total":     st.column_config.NumberColumn("Total $", format="$ %d"),
            "precio_kg": st.column_config.NumberColumn("$/kg o $/u", format="$ %d"),
            "kg_ml":     st.column_config.NumberColumn("kg / ML / u"),
        }
    )

    st.markdown('<div class="dulox-section-label" style="margin:0.5rem 0 0.35rem 0;">CONSUMIBLES</div>', unsafe_allow_html=True)
    cons_df = st.data_editor(
        pd.DataFrame(cons_default),
        key=f"bomedit_cons_{prefix}",
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Total":    st.column_config.NumberColumn("Total $", format="$ %d"),
            "Precio_u": st.column_config.NumberColumn("Precio u.", format="$ %d"),
            "Cantidad": st.column_config.NumberColumn("Cant."),
        }
    )

    mat_total  = int(mat_df["total"].fillna(0).sum())  if isinstance(mat_df, pd.DataFrame) and "total"  in mat_df.columns else 0
    cons_total = int(cons_df["Total"].fillna(0).sum()) if isinstance(cons_df, pd.DataFrame) and "Total"  in cons_df.columns else 0

    col_cost, col_btn = st.columns([3, 1])
    col_cost.markdown(
        f'<div style="font-size:0.88rem;padding:0.3rem 0;">'
        f'<span style="color:var(--text-dim);">Mat: </span>'
        f'<span style="color:var(--text);font-weight:600;">${mat_total:,}</span>'
        f'<span style="color:var(--text-dim);"> · Cons: </span>'
        f'<span style="color:var(--text);font-weight:600;">${cons_total:,}</span>'
        f'<span style="color:var(--text-dim);"> · Total: </span>'
        f'<span style="color:var(--green);font-weight:700;">${mat_total+cons_total:,}</span>'
        f'</div>',
        unsafe_allow_html=True
    )
    if col_btn.button("💾 Guardar BOM", key=f"savebom_{prefix}", type="primary"):
        save_bom(
            handle,
            mat_df.to_dict("records") if isinstance(mat_df, pd.DataFrame) else mat_default,
            cons_df.to_dict("records") if isinstance(cons_df, pd.DataFrame) else cons_default,
        )
        st.success(f"✅ BOM guardado — {handle}")

@st.cache_data(ttl=5)
def load_history(handle):
    conn = get_conn()
    df = pd.read_sql("""
        SELECT old_perfil, new_perfil, old_complejidad, new_complejidad,
               reason, changed_by, changed_at
        FROM categorization_history
        WHERE handle = ?
        ORDER BY changed_at DESC
    """, conn, params=(handle,))
    conn.close()
    return df

def save_reclassification(handle, old_perfil, new_perfil,
                           old_comp, new_comp, reason, reviewer):
    conn = get_conn()
    now = datetime.now().isoformat()

    conn.execute("""
        UPDATE products
        SET perfil_proceso = ?, complejidad = ?,
            k_num = ?,
            validated = 1, validated_by = ?, validated_at = ?
        WHERE handle = ?
    """, (new_perfil, new_comp,
          {"C1":1,"C2":2,"C3":3}.get(new_comp),
          reviewer, now, handle))

    conn.execute("""
        INSERT INTO categorization_history
          (handle, old_perfil, new_perfil, old_complejidad, new_complejidad,
           reason, changed_by, changed_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (handle, old_perfil, new_perfil, old_comp, new_comp, reason, reviewer, now))

    conn.commit()
    conn.close()
    st.cache_data.clear()

def mark_validated(handle, reviewer):
    conn = get_conn()
    now = datetime.now().isoformat()
    conn.execute("""
        UPDATE products SET validated=1, validated_by=?, validated_at=?
        WHERE handle=?
    """, (reviewer, now, handle))
    conn.commit()
    conn.close()
    st.cache_data.clear()

# ─── Product image fetcher ───────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _scrape_product_image(url: str) -> str | None:
    """
    Fetch og:image:secure_url (or og:image) from a Shopify product page.
    Returns the CDN image URL string (always https), or None on failure.
    Cached 1h per URL — only one HTTP request per product per session.
    """
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        text = resp.text
        # Prefer og:image:secure_url (always https)
        m = re.search(r'<meta[^>]+property=["\']og:image:secure_url["\'][^>]+content=["\'](https://[^"\']+)["\']', text)
        if not m:
            m = re.search(r'<meta[^>]+content=["\'](https://[^"\']+)["\'][^>]+property=["\']og:image:secure_url["\']', text)
        # Fall back to og:image (may be http or https)
        if not m:
            m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)["\']', text)
        if not m:
            m = re.search(r'<meta[^>]+content=["\'](https?://[^"\']+)["\'][^>]+property=["\']og:image["\']', text)
        if m:
            img = m.group(1).split("?")[0].replace("http://", "https://", 1)
            return img
        return None
    except Exception:
        return None


def get_product_image(row: dict) -> str | None:
    """
    Return the image URL for a product row.
    1. Use DB-cached image_url if present (populated by fetch_images.py).
    2. Fall back to live scrape and save result to DB.
    """
    img = row.get("image_url")
    if img:
        return img
    url = row.get("url", "")
    if not url:
        return None
    # Live scrape (cached in memory for 1h)
    img = _scrape_product_image(url)
    if img:
        # Persist to DB so next load from DB will have it
        try:
            conn = get_conn()
            conn.execute("UPDATE products SET image_url = ? WHERE handle = ?",
                         (img, row.get("handle", "")))
            conn.commit()
            conn.close()
            st.cache_data.clear()  # invalidate load_products cache
        except Exception:
            pass
    return img


# ─── Audit candidates (replicate Test 3 logic) ────────────────────────────────

def compute_candidates(df, rules=None):
    """Return list of products where another bucket is ≥40% closer.
    Includes reasoning: which driver is driving the suggestion and why."""
    # Build G_NOT_PRIMARY from PROCESS_RULES.json — profiles where g_is_primary=false
    if rules and "profiles" in rules:
        G_NOT_PRIMARY = {p for p, d in rules["profiles"].items() if not d.get("g_is_primary", True)}
    else:
        G_NOT_PRIMARY = {"p-meson", "p-cocina-gas", "p-carro-bandejero",
                         "p-lavadero", "p-electrico", "p-refrigerado",
                         "p-rejilla", "p-tina", "p-custom"}

    # Build bucket centroids + stats
    buckets = {}
    for (perfil, comp), grp in df.groupby(["perfil_proceso", "complejidad"]):
        g_vals = grp["G"].dropna()
        d_vals = grp["D"].dropna()
        if len(grp) >= 2:
            buckets[(perfil, comp)] = {
                "g_mean": float(g_vals.mean()) if len(g_vals) else None,
                "d_mean": float(d_vals.mean()) if len(d_vals) else None,
                "g_std":  float(g_vals.std())  if len(g_vals) >= 2 else 0,
                "d_std":  float(d_vals.std())  if len(d_vals) >= 2 else 0,
                "n":      len(grp),
                "sample_handles": list(grp["handle"].head(3)),
            }

    def dist(g, d, centroid):
        dims = []
        if g is not None and centroid["g_mean"] is not None:
            dims.append((g/3 - centroid["g_mean"]/3) ** 2)
        if d is not None and centroid["d_mean"] is not None:
            dims.append((d/3 - centroid["d_mean"]/3) ** 2)
        if not dims:
            return np.nan
        return float(np.sqrt(sum(dims)))

    def build_reasoning(g, d, perfil, current_comp, suggested_comp, current_bucket, suggested_bucket):
        """Generate a human-readable explanation of why the model flagged this product."""
        reasons = []
        context = get_profile_context(perfil, rules or {})
        primary = context.get("primary_driver", "G/D")

        k_order = {"C1": 1, "C2": 2, "C3": 3}
        direction = "arriba" if k_order.get(suggested_comp, 0) > k_order.get(current_comp, 0) else "abajo"
        upgrade = k_order.get(suggested_comp, 0) > k_order.get(current_comp, 0)

        # Which driver is driving the discrepancy?
        driving_driver = None
        if g is not None and current_bucket.get("g_mean") is not None and suggested_bucket.get("g_mean") is not None:
            g_diff_current  = abs(g/3 - current_bucket["g_mean"]/3)
            g_diff_suggested = abs(g/3 - suggested_bucket["g_mean"]/3)
            if g_diff_suggested < g_diff_current:
                driving_driver = "G"
                reasons.append(
                    f"**G (geometría/área):** Este producto tiene G={g}. "
                    f"El grupo {current_comp} tiene G medio={current_bucket['g_mean']:.2f}, "
                    f"pero el grupo {suggested_comp} tiene G medio={suggested_bucket['g_mean']:.2f} "
                    f"— este producto se parece más al grupo {suggested_comp}."
                )

        if d is not None and current_bucket.get("d_mean") is not None and suggested_bucket.get("d_mean") is not None:
            d_diff_current   = abs(d/3 - current_bucket["d_mean"]/3)
            d_diff_suggested = abs(d/3 - suggested_bucket["d_mean"]/3)
            if d_diff_suggested < d_diff_current:
                if driving_driver is None:
                    driving_driver = "D"
                reasons.append(
                    f"**D (espesor):** Este producto tiene D={d}. "
                    f"El grupo {current_comp} tiene D medio={current_bucket['d_mean']:.2f}, "
                    f"pero el grupo {suggested_comp} tiene D medio={suggested_bucket['d_mean']:.2f}."
                )

        if not reasons:
            reasons.append(
                f"Los scores disponibles (G={g}, D={d}) son más cercanos al centroide "
                f"del grupo {suggested_comp} que al grupo {current_comp}."
            )

        # Is G even the primary driver for this profile?
        driver_warning = None
        if perfil in G_NOT_PRIMARY:
            driver_warning = (
                f"⚠️ **Limitación importante:** El driver primario de `{perfil}` es **{primary}**, "
                f"que actualmente NO está en la base de datos. "
                f"Esta sugerencia usa solo G y D como proxy. "
                f"**Puede ser incorrecta.** Valida mirando la descripción del producto."
            )

        # What moving implies
        implication = None
        if upgrade:
            implication = (
                f"**Si se sube a {suggested_comp}:** Se usará un template de costo más alto. "
                f"Más HH, posiblemente más operadores o consumibles. "
                f"{context.get('cost_implication', '')}"
            )
        else:
            implication = (
                f"**Si se baja a {suggested_comp}:** Se usará un template de costo más bajo. "
                f"Menos HH. Verifica que la descripción no tenga componentes/mecanismos que justifiquen el nivel actual. "
                f"{context.get('cost_implication', '')}"
            )

        return {
            "direction": direction,
            "upgrade": upgrade,
            "driving_driver": driving_driver,
            "reasons": reasons,
            "driver_warning": driver_warning,
            "implication": implication,
            "primary_driver": primary,
        }

    candidates = []
    for _, row in df.iterrows():
        perfil = row["perfil_proceso"]
        comp   = row["complejidad"]
        g = row["G"] if pd.notna(row.get("G")) else None
        d = row["D"] if pd.notna(row.get("D")) else None
        if g is None and d is None:
            continue
        if (perfil, comp) not in buckets:
            continue

        current_dist = dist(g, d, buckets[(perfil, comp)])
        same = {k: v for k, v in buckets.items()
                if k[0] == perfil and k != (perfil, comp)}
        if not same:
            continue

        best = min(
            ((k, dist(g, d, v)) for k, v in same.items()
             if not np.isnan(dist(g, d, v))),
            key=lambda x: x[1],
            default=(None, np.nan),
        )
        if best[0] is None or np.isnan(best[1]) or np.isnan(current_dist):
            continue

        if best[1] < current_dist * 0.6:
            reasoning = build_reasoning(
                g, d, perfil, comp, best[0][1],
                buckets[(perfil, comp)], buckets[best[0]]
            )
            candidates.append({
                "handle":            row["handle"],
                "current_perfil":    perfil,
                "current_comp":      comp,
                "suggested_perfil":  best[0][0],
                "suggested_comp":    best[0][1],
                "current_dist":      round(current_dist, 3),
                "best_dist":         round(best[1], 3),
                "gap":               round(current_dist - best[1], 3),
                "G": g, "D": d,
                "descripcion":       str(row.get("descripcion_web", "") or "")[:200],
                "validated":         row.get("validated", 0),
                "reasoning":         reasoning,
                "current_bucket":    buckets[(perfil, comp)],
                "suggested_bucket":  buckets[best[0]],
            })

    candidates.sort(key=lambda x: -x["gap"])
    return candidates

# ─── UI components ────────────────────────────────────────────────────────────

def product_card(row, reviewer_key="reviewer"):
    """Render a full product card with reclassification controls."""
    reviewer = st.session_state.get(reviewer_key, "")

    handle       = row["handle"] if isinstance(row, dict) else row.get("handle", "")
    perfil       = row.get("perfil_proceso", "")
    comp         = row.get("complejidad", "")
    desc         = str(row.get("descripcion_web", "") or "")
    g_val        = row.get("G")
    d_val        = row.get("D")
    validated    = row.get("validated", 0)

    url = row.get("url", "")
    url_md = f"[↗ dulox.cl]({url})" if url else ""

    img_col, info_col = st.columns([1, 3])
    with img_col:
        img_url = get_product_image(row if isinstance(row, dict) else row.to_dict())
        if img_url:
            st.image(img_url, use_container_width=True)
        else:
            st.markdown(
                '<div style="height:100px;display:flex;align-items:center;'
                'justify-content:center;color:var(--text-muted);font-size:0.75rem;'
                'border:1px solid var(--border);border-radius:6px;">sin imagen</div>',
                unsafe_allow_html=True
            )

    with info_col:
        st.markdown(f"**{handle}**  {url_md}")
        if desc:
            st.caption(desc[:200])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Perfil actual", perfil)
    with col2:
        st.metric("Complejidad", comp)
    with col3:
        g_str = str(int(g_val)) if g_val is not None and not (isinstance(g_val, float) and np.isnan(g_val)) else "—"
        d_str = str(int(d_val)) if d_val is not None and not (isinstance(d_val, float) and np.isnan(d_val)) else "—"
        st.metric("Drivers", f"G={g_str}  D={d_str}")

    if validated:
        st.success("✅ Validado")
    else:
        st.warning("⏳ Sin validar")

    with st.expander("✏️ Reclasificar / Confirmar"):
        new_perfil = st.selectbox(
            "Perfil proceso", PERFILES,
            index=PERFILES.index(perfil) if perfil in PERFILES else 0,
            key=f"perfil_{handle}"
        )
        new_comp = st.selectbox(
            "Complejidad", COMPLEJIDADES,
            index=COMPLEJIDADES.index(comp) if comp in COMPLEJIDADES else 0,
            key=f"comp_{handle}"
        )
        reason = st.text_input(
            "Razón del cambio (obligatorio si cambia algo)",
            placeholder="ej: Descripción indica 3 cajones → driver C alto → C3",
            key=f"reason_{handle}"
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Confirmar sin cambios", key=f"ok_{handle}"):
                if not reviewer:
                    st.error("Ingresa tu nombre arriba")
                else:
                    mark_validated(handle, reviewer)
                    st.success("Marcado como validado")
                    st.rerun()

        with col_b:
            changed = (new_perfil != perfil) or (new_comp != comp)
            if st.button("💾 Guardar cambio", key=f"save_{handle}",
                         disabled=not changed):
                if not reviewer:
                    st.error("Ingresa tu nombre arriba")
                elif not reason.strip():
                    st.error("Escribe la razón del cambio")
                else:
                    save_reclassification(
                        handle, perfil, new_perfil, comp, new_comp,
                        reason.strip(), reviewer
                    )
                    st.success(f"Guardado: {perfil} {comp} → {new_perfil} {new_comp}")
                    st.rerun()

    # BOM editor
    bom_mat  = row.get("bom_materials",  "") or ""
    bom_cons = row.get("bom_consumables","") or ""
    has_bom  = bool(bom_mat and bom_mat != "[]") or bool(bom_cons and bom_cons != "[]")
    bom_label = "📦 BOM de costos ✅" if has_bom else "📦 BOM de costos"
    with st.expander(bom_label):
        product_bom_expander(row if isinstance(row, dict) else row, reviewer_key)

    # History
    hist = load_history(handle)
    if not hist.empty:
        with st.expander(f"Historial ({len(hist)} cambios)"):
            for _, h in hist.iterrows():
                st.markdown(
                    f"- `{h['changed_at'][:16]}` por **{h['changed_by']}**:  "
                    f"`{h['old_perfil']} {h['old_complejidad']}` → "
                    f"`{h['new_perfil']} {h['new_complejidad']}`  \n"
                    f"  _{h['reason']}_"
                )

# ─── Pages ────────────────────────────────────────────────────────────────────

def candidate_context_card(c, df, reviewer_key, index=0):
    """Compact candidate card — image + pill row + inline decision controls."""
    row = df[df["handle"] == c["handle"]]
    if row.empty:
        return
    row = row.iloc[0].to_dict()

    handle    = c["handle"]
    perfil    = c["current_perfil"]
    curr_comp = c["current_comp"]
    sugg_comp = c["suggested_comp"]
    reasoning = c["reasoning"]
    rules     = load_rules()
    ctx       = get_profile_context(perfil, rules)
    url       = row.get("url", "")
    desc      = str(row.get("descripcion_web", "") or "")
    validated = row.get("validated", 0)
    reviewer  = st.session_state.get(reviewer_key, "")

    # Accent color: upgrade = amber, downgrade = blue, validated = green
    if validated:
        accent = "#238636"
    elif reasoning["upgrade"]:
        accent = "#9e6a03"
    else:
        accent = "#1f6feb"

    direction_label = "subir" if reasoning["upgrade"] else "bajar"
    g_str = str(int(c["G"])) if c["G"] is not None else "—"
    d_str = str(int(c["D"])) if c["D"] is not None else "—"

    # ── Row: number + image + info block ─────────────────────────────────────
    n_col, img_col, main_col = st.columns([0.3, 1, 6])

    with n_col:
        st.markdown(
            f'<div style="padding-top:0.6rem;font-size:1.4rem;font-weight:700;'
            f'color:var(--text-label);text-align:right;">{index + 1}</div>',
            unsafe_allow_html=True
        )

    with img_col:
        img_url = get_product_image(row)
        if img_url:
            st.image(img_url, use_container_width=True)
        else:
            st.markdown(
                '<div style="height:72px;display:flex;align-items:center;justify-content:center;'
                'color:var(--border);font-size:0.7rem;border:1px solid var(--border-subtle);border-radius:4px;">—</div>',
                unsafe_allow_html=True
            )

    with main_col:
        # Handle + link + validated pill on one line
        val_pill = (
            ' <span style="background:var(--green-bg);color:var(--green);border:1px solid var(--green-border);'
            'border-radius:10px;padding:1px 7px;font-size:0.7rem;">✅ validado</span>'
            if validated else ""
        )
        url_link = (
            f' <a href="{url}" style="color:var(--text-faint);font-size:0.75rem;" target="_blank">↗</a>'
            if url else ""
        )
        st.markdown(
            f'<div style="border-left:3px solid {accent};padding-left:0.75rem;">'
            f'<div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">'
            f'<span style="font-family:monospace;font-size:0.88rem;color:var(--text-dim);font-weight:600;">'
            f'{handle}</span>{url_link}{val_pill}'
            f'</div>'
            # Pill row: perfil · curr_comp → sugg_comp · drivers · gap
            f'<div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.35rem;flex-wrap:wrap;">'
            f'{profile_badge(perfil)}'
            f'{complexity_badge(curr_comp)}'
            f'<span style="color:{accent};font-weight:700;font-size:0.88rem;">→ {sugg_comp}</span>'
            f'<span style="color:var(--text-faint);font-size:0.78rem;">({direction_label})</span>'
            f'<span style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:4px;'
            f'padding:1px 6px;font-family:monospace;font-size:0.72rem;color:var(--text-label);">'
            f'G={g_str} D={d_str} · Δ={c["gap"]:.2f}</span>'
            f'</div>'
            # Description (trimmed, muted)
            + (f'<div style="font-size:0.78rem;color:var(--text-faint);margin-top:0.3rem;'
               f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:700px;">'
               f'{desc[:180]}</div>' if desc else "")
            + f'</div>',
            unsafe_allow_html=True
        )

    # ── Detail expanders (collapsed by default — click to dig in) ────────────
    with st.expander("📋 Razonamiento + decisión", expanded=False):

        # Reasoning summary
        reason_lines = reasoning.get("reasons", [])
        if reason_lines:
            st.markdown(
                '<div style="font-size:0.82rem;color:var(--text-muted);margin-bottom:0.5rem;">'
                + "<br>".join(f"• {r}" for r in reason_lines)
                + "</div>",
                unsafe_allow_html=True
            )
        if reasoning.get("driver_warning"):
            st.warning(reasoning["driver_warning"])

        # Current vs suggested side by side — compact
        levels = ctx.get("levels", {})
        lc, lsep, ls = st.columns([5, 0.3, 5])
        cg = c['current_bucket'].get('g_mean')
        cd = c['current_bucket'].get('d_mean')
        sg = c['suggested_bucket'].get('g_mean')
        sd = c['suggested_bucket'].get('d_mean')
        _fmt = lambda v: f"{v:.2f}" if v is not None else "—"
        lc.markdown(
            f'<div style="border:1px solid var(--border);border-radius:6px;padding:0.6rem 0.8rem;">'
            f'<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;color:var(--text-label);margin-bottom:0.3rem;">ACTUAL</div>'
            f'{complexity_badge(curr_comp)}'
            f'<div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.3rem;">'
            f'{levels.get(curr_comp,"—")}</div>'
            f'<div style="font-size:0.7rem;color:var(--text-faint);margin-top:0.3rem;">'
            f'G̅={_fmt(cg)} D̅={_fmt(cd)} n={c["current_bucket"]["n"]}'
            f'</div></div>',
            unsafe_allow_html=True
        )
        lsep.markdown('<div style="text-align:center;padding-top:1.5rem;color:var(--text-faint);">→</div>', unsafe_allow_html=True)
        ls.markdown(
            f'<div style="border:1px solid {accent};border-radius:6px;padding:0.6rem 0.8rem;">'
            f'<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;color:{accent};margin-bottom:0.3rem;">SUGERIDO</div>'
            f'{complexity_badge(sugg_comp)}'
            f'<div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.3rem;">'
            f'{levels.get(sugg_comp,"—")}</div>'
            f'<div style="font-size:0.7rem;color:var(--text-faint);margin-top:0.3rem;">'
            f'G̅={_fmt(sg)} D̅={_fmt(sd)} n={c["suggested_bucket"]["n"]}'
            f'</div></div>',
            unsafe_allow_html=True
        )

        st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)

        # Decision controls
        new_perfil = st.selectbox(
            "Perfil", PERFILES,
            index=PERFILES.index(perfil) if perfil in PERFILES else 0,
            key=f"perfil_{handle}"
        )
        new_comp = st.selectbox(
            "Complejidad", COMPLEJIDADES,
            index=COMPLEJIDADES.index(curr_comp) if curr_comp in COMPLEJIDADES else 0,
            key=f"comp_{handle}"
        )
        reason_in = st.text_input(
            "Razón del cambio",
            placeholder="ej: Descripción indica 1 quemador → C1 correcto",
            key=f"reason_{handle}"
        )

        ca, cb, cc = st.columns(3)
        with ca:
            if st.button(f"✅ Confirmar {curr_comp}", key=f"ok_{handle}"):
                if not reviewer:
                    st.error("Ingresa tu nombre en el sidebar")
                else:
                    mark_validated(handle, reviewer)
                    st.rerun()
        with cb:
            if st.button(f"→ Mover a {sugg_comp}", key=f"quick_{handle}", type="primary"):
                if not reviewer:
                    st.error("Ingresa tu nombre en el sidebar")
                elif not reason_in.strip():
                    st.error("Escribe la razón")
                else:
                    save_reclassification(handle, perfil, perfil, curr_comp, sugg_comp,
                                          reason_in.strip(), reviewer)
                    st.rerun()
        with cc:
            changed = (new_perfil != perfil) or (new_comp != curr_comp)
            if st.button("💾 Personalizado", key=f"save_{handle}", disabled=not changed):
                if not reviewer:
                    st.error("Ingresa tu nombre en el sidebar")
                elif not reason_in.strip():
                    st.error("Escribe la razón")
                else:
                    save_reclassification(handle, perfil, new_perfil, curr_comp, new_comp,
                                          reason_in.strip(), reviewer)
                    st.rerun()

        # History inline
        hist = load_history(handle)
        if not hist.empty:
            st.markdown(
                '<div style="font-size:0.72rem;color:var(--text-faint);margin-top:0.5rem;">'
                + " · ".join(
                    f'{h["changed_at"][:10]} {h["old_complejidad"]}→{h["new_complejidad"]} ({h["changed_by"]})'
                    for _, h in hist.iterrows()
                )
                + "</div>",
                unsafe_allow_html=True
            )


def page_candidates(df, candidates, reviewer_key):
    st.markdown('<h2>🔍 Revisar Candidatos</h2>', unsafe_allow_html=True)
    st.markdown(
        f"**{len(candidates)} productos** donde el modelo sugiere otra categoría. "
        "Ordenados por mayor discrepancia de distancia entre categoría actual y sugerida. "
        "Cada tarjeta explica **por qué** el modelo hace la sugerencia y **qué implicaría** cambiar."
    )

    col1, col2 = st.columns(2)
    with col1:
        show_validated = st.checkbox("Mostrar ya validados", value=False)
    with col2:
        filter_perfil = st.selectbox("Filtrar por perfil", ["Todos"] + PERFILES)

    if not show_validated:
        candidates = [c for c in candidates if not c["validated"]]
    if filter_perfil != "Todos":
        candidates = [c for c in candidates if c["current_perfil"] == filter_perfil]

    # Summary metrics
    m1, m2, m3, m4 = st.columns(4)
    upgrades   = sum(1 for c in candidates if c["reasoning"]["upgrade"])
    downgrades = len(candidates) - upgrades
    g_driven   = sum(1 for c in candidates if c["reasoning"]["driving_driver"] == "G")
    limited    = sum(1 for c in candidates if c["reasoning"].get("driver_warning"))
    m1.metric("Candidatos", len(candidates))
    m2.metric("⬆️ Subir complejidad", upgrades)
    m3.metric("⬇️ Bajar complejidad", downgrades)
    m4.metric("⚠️ Driver primario no en DB", limited,
              help="Sugerencias basadas solo en G/D — el driver real (C/X) no está disponible")

    st.divider()

    for i, c in enumerate(candidates):
        candidate_context_card(c, df, reviewer_key, index=i)
        st.divider()


def page_por_perfil(df, reviewer_key):
    st.markdown('<h2>📋 Por Perfil</h2>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        perfil = st.selectbox("Perfil proceso", PERFILES)
    with col2:
        comp = st.selectbox("Complejidad", COMPLEJIDADES)

    bucket = df[(df["perfil_proceso"] == perfil) & (df["complejidad"] == comp)]

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:0.6rem;margin:0.5rem 0 1rem 0;">'
        f'<span style="color:var(--text-label);font-size:0.88rem;">{len(bucket)} productos en</span>'
        f'{profile_badge(perfil)} {complexity_badge(comp)}'
        f'</div>',
        unsafe_allow_html=True
    )

    if not bucket.empty:
        g_vals = bucket["G"].dropna()
        d_vals = bucket["D"].dropna()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", len(bucket))
        with col2:
            st.metric("Validados", int(bucket["validated"].sum()))
        with col3:
            st.metric("G medio", f"{g_vals.mean():.2f}" if len(g_vals) else "—")
        with col4:
            st.metric("D medio", f"{d_vals.mean():.2f}" if len(d_vals) else "—")

        st.divider()
        for _, row in bucket.iterrows():
            product_card(row.to_dict(), reviewer_key)
            st.divider()


def page_buscar(df, reviewer_key):
    st.markdown('<h2>🔎 Buscar Producto</h2>', unsafe_allow_html=True)

    query = st.text_input("Buscar por handle o descripción", placeholder="ej: meson-abierto")

    if query:
        mask = (
            df["handle"].str.contains(query, case=False, na=False) |
            df["descripcion_web"].str.contains(query, case=False, na=False)
        )
        results = df[mask]

        st.markdown(f"**{len(results)} resultados**")
        st.divider()

        for _, row in results.iterrows():
            product_card(row.to_dict(), reviewer_key)
            st.divider()


def page_dashboard(df):
    st.markdown('<h2>📊 Dashboard</h2>', unsafe_allow_html=True)

    total   = len(df)
    val     = int(df["validated"].sum())
    pct_val = val / total * 100 if total else 0
    no_dims = int((df["G"].isna() & df["D"].isna()).sum())
    c1_n    = int((df["complejidad"] == "C1").sum())
    c2_n    = int((df["complejidad"] == "C2").sum())
    c3_n    = int((df["complejidad"] == "C3").sum())

    # Top stat bar
    st.markdown(
        f'<div style="display:flex;gap:1rem;margin-bottom:1.5rem;flex-wrap:wrap;">'
        f'<div class="dulox-card" style="flex:1;min-width:120px;text-align:center;">'
        f'<div style="font-size:2rem;font-weight:700;color:var(--text);">{total}</div>'
        f'<div class="dulox-section-label">TOTAL PRODUCTOS</div></div>'
        f'<div class="dulox-card" style="flex:1;min-width:120px;text-align:center;">'
        f'<div style="font-size:2rem;font-weight:700;color:var(--green);">{val}</div>'
        f'<div class="dulox-section-label">VALIDADOS ({pct_val:.0f}%)</div></div>'
        f'<div class="dulox-card" style="flex:1;min-width:120px;text-align:center;">'
        f'<div style="font-size:2rem;font-weight:700;color:var(--yellow);">{total-val}</div>'
        f'<div class="dulox-section-label">SIN VALIDAR</div></div>'
        f'<div class="dulox-card" style="flex:1;min-width:120px;text-align:center;">'
        f'<div style="font-size:2rem;font-weight:700;color:var(--red);">{no_dims}</div>'
        f'<div class="dulox-section-label">SIN DIMS G/D</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Complexity distribution
    st.markdown(
        f'<div class="dulox-card" style="margin-bottom:1.5rem;">'
        f'<div class="dulox-section-label">DISTRIBUCIÓN DE COMPLEJIDAD</div>'
        f'<div style="display:flex;gap:1.5rem;margin-top:0.6rem;">'
        f'<div>{complexity_badge("C1")} <span style="color:var(--text-dim);font-size:1.1rem;font-weight:600;margin-left:0.4rem;">{c1_n}</span></div>'
        f'<div>{complexity_badge("C2")} <span style="color:var(--text-dim);font-size:1.1rem;font-weight:600;margin-left:0.4rem;">{c2_n}</span></div>'
        f'<div>{complexity_badge("C3")} <span style="color:var(--text-dim);font-size:1.1rem;font-weight:600;margin-left:0.4rem;">{c3_n}</span></div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="dulox-section-label" style="margin-bottom:0.5rem;">PROGRESO POR PERFIL</div>', unsafe_allow_html=True)
    progress = (
        df.groupby("perfil_proceso")
        .agg(total=("handle", "count"), validados=("validated", "sum"))
        .reset_index()
    )
    progress["pct"] = (progress["validados"] / progress["total"] * 100).round(0)
    progress = progress.sort_values("pct")

    st.dataframe(
        progress.rename(columns={
            "perfil_proceso": "Perfil",
            "total": "Total",
            "validados": "Validados",
            "pct": "% Validado",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown('<div class="dulox-section-label" style="margin:1.5rem 0 0.5rem 0;">DISTRIBUCIÓN POR PERFIL × COMPLEJIDAD</div>', unsafe_allow_html=True)
    pivot = df.groupby(["perfil_proceso", "complejidad"]).size().unstack(fill_value=0)
    st.dataframe(pivot, use_container_width=True)

    st.markdown('<div class="dulox-section-label" style="margin:1.5rem 0 0.5rem 0;">ÚLTIMAS RECLASIFICACIONES</div>', unsafe_allow_html=True)
    conn = get_conn()
    hist = pd.read_sql("""
        SELECT handle, old_perfil, old_complejidad, new_perfil, new_complejidad,
               reason, changed_by, changed_at
        FROM categorization_history
        ORDER BY changed_at DESC
        LIMIT 20
    """, conn)
    conn.close()

    if hist.empty:
        st.info("Ninguna reclasificación aún — empieza revisando los candidatos.")
    else:
        st.dataframe(hist, use_container_width=True, hide_index=True)

# ─── New profile creation ─────────────────────────────────────────────────────

def page_nuevo_perfil(rules: dict):
    st.markdown('<h2>➕ Nuevo Perfil Proceso</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:var(--text-label);font-size:0.88rem;">'
        'Crea un nuevo <code>perfil_proceso</code>. Se escribe en <code>PROCESS_RULES.json</code> '
        '— la única fuente de verdad. Una vez guardado, el perfil estará disponible '
        'inmediatamente en <b>todos los selectores</b> del sistema '
        '(review.py, calibration.py, product_intake.py, audit_model.py).</p>',
        unsafe_allow_html=True
    )

    existing = sorted(rules.get("profiles", {}).keys())

    with st.form("nuevo_perfil_form"):
        st.markdown("#### Identificación")
        fc1, fc2 = st.columns(2)
        raw_name = fc1.text_input(
            "Nombre del perfil",
            placeholder="ej: campana-extraccion",
            help="Se añade el prefijo 'p-' automáticamente si no lo tiene. Solo minúsculas y guiones."
        )
        description = fc2.text_input("Descripción corta", placeholder="ej: Campanas de extracción industriales")

        st.markdown("#### Drivers")
        dc1, dc2, dc3 = st.columns(3)
        primary_drivers   = dc1.multiselect("Drivers primarios",   ["G","D","C","X"], default=["G"])
        secondary_drivers = dc2.multiselect("Drivers secundarios", ["G","D","C","X"], default=["X"])
        g_is_primary      = dc3.checkbox("G es driver primario", value=True,
                                          help="Desmarcar si el tamaño NO diferencia la complejidad (ej. mesones)")
        c_driver = st.text_input(
            "Campo C en DB (opcional)",
            placeholder="ej: num_cajones, num_quemadores — dejar vacío si C no aplica",
            help="Nombre del campo numérico en products.db que representa el conteo de componentes."
        )

        st.markdown("#### Procesos activos")
        processes = st.multiselect(
            "Procesos que aplican a este perfil",
            KNOWN_PROCESSES,
            default=["armado_trazado", "soldadura", "pulido"]
        )

        st.markdown("#### Umbrales de complejidad")
        st.caption("Puntos totales (suma de scores G+D+C+X) que definen cada nivel.")
        uc1, uc2, uc3 = st.columns(3)
        with uc1:
            c1_lo   = st.number_input("C1 mín", value=1,  min_value=0, key="np_c1lo")
            c1_hi   = st.number_input("C1 máx", value=2,  min_value=0, key="np_c1hi")
            c1_desc = st.text_input("C1 descripción", value="Simple, sin mecanismo", key="np_c1d")
        with uc2:
            c2_lo   = st.number_input("C2 mín", value=3,  min_value=0, key="np_c2lo")
            c2_hi   = st.number_input("C2 máx", value=5,  min_value=0, key="np_c2hi")
            c2_desc = st.text_input("C2 descripción", value="Estándar, algún mecanismo o característica", key="np_c2d")
        with uc3:
            c3_lo   = st.number_input("C3 mín", value=6,  min_value=0, key="np_c3lo")
            c3_hi   = st.number_input("C3 máx", value=99, min_value=0, key="np_c3hi")
            c3_desc = st.text_input("C3 descripción", value="Alta complejidad, acabado especial o múltiples componentes", key="np_c3d")

        submitted = st.form_submit_button("💾 Crear perfil en PROCESS_RULES.json", type="primary")

    if submitted:
        # Normalize name
        name = raw_name.strip().lower().replace(" ", "-")
        if not name.startswith("p-"):
            name = f"p-{name}"

        # Validate
        if not name or name == "p-":
            st.error("Ingresa un nombre de perfil.")
            return
        if name in existing:
            st.error(f"El perfil `{name}` ya existe en PROCESS_RULES.json.")
            return
        if not re.match(r'^p-[a-z0-9-]+$', name):
            st.error("Nombre inválido. Usa solo minúsculas, números y guiones (ej. p-tina-industrial).")
            return

        new_profile = {
            "description":        description or f"Perfil {name}",
            "primary_drivers":    primary_drivers,
            "secondary_drivers":  secondary_drivers,
            "c_driver":           c_driver.strip() or None,
            "g_is_primary":       g_is_primary,
            "processes":          processes,
            "x_flags":            {},
            "complexity_thresholds": {
                "C1": {"min_points": c1_lo, "max_points": c1_hi, "description": c1_desc},
                "C2": {"min_points": c2_lo, "max_points": c2_hi, "description": c2_desc},
                "C3": {"min_points": c3_lo, "max_points": c3_hi, "description": c3_desc},
            },
            "cost_benchmarks": {
                "C2": {
                    "anchor_sku": None, "short_name": None,
                    "dims": {"L_mm": None, "W_mm": None, "H_mm": None, "espesor_mm": None},
                    "material_total_clp": None, "consumables_total_clp": None,
                    "calibrated": False, "calibration_date": None,
                    "notes": "Pendiente: ingresar BOM en calibration.py"
                },
                "C3": {
                    "anchor_sku": None, "short_name": None,
                    "dims": {"L_mm": None, "W_mm": None, "H_mm": None, "espesor_mm": None},
                    "material_total_clp": None, "consumables_total_clp": None,
                    "calibrated": False, "calibration_date": None,
                    "notes": "Pendiente: ingresar BOM en calibration.py"
                }
            },
            "expected_cost_ratios": {
                "C2_to_C3": {"material": None, "consumables": None, "notes": "Pendiente calibración"}
            }
        }

        rules["profiles"][name] = new_profile
        rules["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        save_rules(rules)

        # Store in session state — st.success before st.rerun() is discarded
        st.session_state["_perfil_created"] = name
        st.rerun()

    # Show success banner after rerun (stored before rerun so it survives)
    if "_perfil_created" in st.session_state:
        created_name = st.session_state.pop("_perfil_created")
        st.success(
            f"✅ Perfil `{created_name}` creado correctamente.\n\n"
            f"Ya disponible en todos los selectores del sistema.\n\n"
            f"**Próximos pasos:**  \n"
            f"1. Asigna productos en 📋 Por Perfil o 🔎 Buscar Producto  \n"
            f"2. Agrega X flags si aplica → calibration.py Tab 2  \n"
            f"3. Calibra costos → calibration.py Tab 1 → 💾 Guardar Hallazgos  \n"
            f"4. Ejecuta `/model-auditor full` para incluirlo en el ICM"
        )

    # Show existing profiles summary
    if existing:
        st.divider()
        st.markdown(f'<div class="dulox-section-label">{len(existing)} PERFILES EN PROCESS_RULES.JSON</div>', unsafe_allow_html=True)
        rows = []
        for p in existing:
            pd_data = rules["profiles"][p]
            rows.append({
                "Perfil": p,
                "Drivers primarios": " + ".join(pd_data.get("primary_drivers", [])),
                "Procesos": len(pd_data.get("processes", [])),
                "X flags": len(pd_data.get("x_flags", {})),
                "C2 calibrado": "✅" if pd_data.get("cost_benchmarks", {}).get("C2", {}).get("calibrated") else "—",
                "C3 calibrado": "✅" if pd_data.get("cost_benchmarks", {}).get("C3", {}).get("calibrated") else "—",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ─── App ──────────────────────────────────────────────────────────────────────

# ─── Theme CSS ────────────────────────────────────────────────────────────────

DARK_VARS = """
    --bg:           #0d1117;
    --bg-surface:   #161b22;
    --bg-input:     #0d1117;
    --bg-subtle:    #1c2128;
    --bg-hover:     #30363d;
    --border:       #30363d;
    --border-subtle:#21262d;
    --text:         #e6edf3;
    --text-dim:     #cdd9e5;
    --text-muted:   #8b949e;
    --text-faint:   #484f58;
    --text-label:   #768390;
    --accent:       #58a6ff;
    --green:        #3fb950;
    --green-bg:     #0d3321;
    --green-border: #238636;
    --yellow:       #e3b341;
    --yellow-bg:    #2d1b00;
    --yellow-border:#9e6a03;
    --red:          #f85149;
    --red-bg:       #3d0c0c;
    --red-border:   #da3633;
    --blue:         #79c0ff;
    --blue-bg:      #1c2128;
    --blue-border:  #388bfd;
    --link:         #1f6feb;
    --link-border:  #388bfd;
"""

LIGHT_VARS = """
    --bg:           #ffffff;
    --bg-surface:   #f6f8fa;
    --bg-input:     #ffffff;
    --bg-subtle:    #eaeef2;
    --bg-hover:     #d0d7de;
    --border:       #d0d7de;
    --border-subtle:#eaeef2;
    --text:         #1f2328;
    --text-dim:     #24292f;
    --text-muted:   #57606a;
    --text-faint:   #8c959f;
    --text-label:   #6e7781;
    --accent:       #0969da;
    --green:        #1a7f37;
    --green-bg:     #dafbe1;
    --green-border: #2da44e;
    --yellow:       #9a6700;
    --yellow-bg:    #fff8c5;
    --yellow-border:#bf8700;
    --red:          #cf222e;
    --red-bg:       #ffebe9;
    --red-border:   #cf222e;
    --blue:         #0969da;
    --blue-bg:      #ddf4ff;
    --blue-border:  #0969da;
    --link:         #0969da;
    --link-border:  #0969da;
"""

# Static CSS using CSS variables — works for both themes.
# Variables are injected as a separate <style>:root{} block in build_css().
CSS_STATIC = """
<style>
/* ── Base ─────────────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
}
/* Override Streamlit's own paragraph / markdown text color */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
[data-testid="stText"] {
    color: var(--text) !important;
}
[data-testid="stSidebar"] {
    background-color: var(--bg-surface) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] * { color: var(--text-dim) !important; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: var(--accent) !important;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="stMain"] { background-color: var(--bg) !important; }
section[data-testid="stMain"] > div { background-color: var(--bg) !important; }
/* Radio / checkbox labels */
[data-testid="stRadio"] label span,
[data-testid="stCheckbox"] label span { color: var(--text) !important; }
/* Selectbox / text input labels */
label[data-testid="stWidgetLabel"] { color: var(--text) !important; }

/* ── Main title ───────────────────────────────────────────────────────── */
h1 { color: var(--text) !important; font-weight: 700; letter-spacing: -0.02em; }
h2 { color: var(--text-dim) !important; font-weight: 600; }
h3 { color: var(--text-muted) !important; }

/* ── Cards / containers ───────────────────────────────────────────────── */
.dulox-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.dulox-card-accent {
    background: var(--blue-bg);
    border: 1px solid var(--link);
    border-radius: 10px;
    padding: 1rem 1.4rem;
    margin-bottom: 0.8rem;
}
.dulox-section-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-label);
    margin-bottom: 0.3rem;
}

/* ── Complexity badges ────────────────────────────────────────────────── */
.badge { display:inline-block; padding:2px 10px; border-radius:12px;
         font-size:0.78rem; font-weight:700; letter-spacing:0.04em; }
.badge-c1 { background:var(--green-bg); color:var(--green); border:1px solid var(--green-border); }
.badge-c2 { background:var(--yellow-bg); color:var(--yellow); border:1px solid var(--yellow-border); }
.badge-c3 { background:var(--red-bg); color:var(--red); border:1px solid var(--red-border); }
.badge-profile { background:var(--blue-bg); color:var(--blue); border:1px solid var(--blue-border); }
.badge-ok   { background:var(--green-bg); color:var(--green); border:1px solid var(--green-border); }
.badge-warn { background:var(--yellow-bg); color:var(--yellow); border:1px solid var(--yellow-border); }
.badge-gap  { background:var(--red-bg); color:var(--red); border:1px solid var(--red-border); }

/* ── Metric overrides ─────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem 1rem;
}
[data-testid="metric-container"] label { color: var(--text-label) !important; font-size:0.75rem; }
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--text) !important; font-size: 1.5rem; font-weight: 700;
}

/* ── Expanders ────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    margin-bottom: 6px;
}
[data-testid="stExpander"] summary {
    color: var(--text-dim) !important;
    font-size: 0.9rem;
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] select {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 6px;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
[data-testid="stBaseButton-secondary"] {
    background: var(--bg-subtle) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-dim) !important;
    border-radius: 6px;
}
[data-testid="stBaseButton-secondary"]:hover {
    background: var(--bg-hover) !important;
    border-color: var(--accent) !important;
}
[data-testid="stBaseButton-primary"] {
    background: var(--link) !important;
    border: 1px solid var(--link-border) !important;
    color: #ffffff !important;
    border-radius: 6px;
    font-weight: 600;
}

/* ── Divider ──────────────────────────────────────────────────────────── */
hr { border-color: var(--border-subtle) !important; }

/* ── Info / warning / success ─────────────────────────────────────────── */
[data-testid="stAlert"] { border-radius: 8px; }

/* ── Dataframe ────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 8px; }

/* ── Caption / small text ─────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] p { color: var(--text-label) !important; font-size:0.78rem; }

/* ── Candidate card chips ─────────────────────────────────────────────── */
.cand-arrow {
    display: flex; align-items: center; gap: 0.6rem;
    font-size: 0.88rem; color: var(--text-label); margin-bottom: 0.4rem;
}
.dist-chip {
    background: var(--bg-subtle); border: 1px solid var(--border);
    border-radius: 6px; padding: 2px 8px;
    font-family: monospace; font-size: 0.78rem; color: var(--text-muted);
}
.dist-chip-good {
    background: var(--green-bg); border: 1px solid var(--green-border);
    border-radius: 6px; padding: 2px 8px;
    font-family: monospace; font-size: 0.78rem; color: var(--green);
}
</style>
"""

def build_css(dark: bool) -> str:
    vars_block = DARK_VARS if dark else LIGHT_VARS
    # Force vars on :root, html, and body so Streamlit's own theme can't win
    var_injection = (
        f"<style>:root, html, body {{ {vars_block} }}</style>"
    )
    return var_injection + CSS_STATIC
def complexity_badge(comp):
    cls = {"C1":"badge-c1","C2":"badge-c2","C3":"badge-c3"}.get(comp,"badge-profile")
    return f'<span class="badge {cls}">{comp}</span>'

def profile_badge(perfil):
    short = perfil.replace("p-","")
    return f'<span class="badge badge-profile">{short}</span>'


def main():
    st.set_page_config(
        page_title="Dulox — Revisión de Categorización",
        page_icon="🏭",
        layout="wide",
    )

    # Theme state — persisted in session
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = True
    dark = st.session_state["dark_mode"]
    st.markdown(build_css(dark), unsafe_allow_html=True)

    # Load rules + patch PERFILES BEFORE any widget renders
    # so all selectboxes see the full dynamic profile list on first render
    rules = load_rules()
    df    = load_products()
    perfiles = get_perfiles(rules, df)
    global PERFILES
    PERFILES = perfiles

    st.markdown(
        '<h1 style="border-bottom:1px solid var(--border-subtle);padding-bottom:0.5rem;">'
        '🏭 Dulox — Revisión de Categorización</h1>',
        unsafe_allow_html=True
    )

    # Reviewer identity (persisted in session)
    with st.sidebar:
        st.markdown("### 👤 Identificación")
        reviewer = st.text_input(
            "Tu nombre", value=st.session_state.get("reviewer", ""),
            placeholder="ej: Fabio"
        )
        st.session_state["reviewer"] = reviewer
        if reviewer:
            st.markdown(
                f'<div style="background:var(--green-bg);border:1px solid var(--green-border);'
                f'border-radius:6px;padding:6px 12px;font-size:0.82rem;color:var(--green);">✅ {reviewer}</div>',
                unsafe_allow_html=True
            )

        st.divider()
        st.markdown("### 🗂️ Navegación")
        page = st.radio("", [
            "🔍 Revisar Candidatos",
            "📋 Por Perfil",
            "🔎 Buscar Producto",
            "📊 Dashboard",
            "➕ Nuevo Perfil",
            "📥 Inputs (C/X/Procesos/Anclas)",
            "⚙️ Costos de Proceso",
            "🎯 Calibración",
            "🖼️ Analizador de Planos",
            "➕ Ingreso de Producto",
        ])

        st.divider()
        # Theme toggle
        theme_label = "☀️ Modo claro" if dark else "🌙 Modo oscuro"
        if st.button(theme_label, use_container_width=True):
            st.session_state["dark_mode"] = not dark
            st.rerun()

        st.divider()
        db_kb = DB.stat().st_size // 1024
        st.markdown(
            f'<div class="dulox-section-label">BASE DE DATOS</div>'
            f'<div style="font-size:0.82rem;color:var(--accent);">products.db · {db_kb} KB</div>',
            unsafe_allow_html=True
        )
        st.markdown("")
        if st.button("🔄 Recargar datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if page == "🔍 Revisar Candidatos":
        with st.spinner("Calculando candidatos..."):
            candidates = compute_candidates(df, rules)
        page_candidates(df, candidates, "reviewer")

    elif page == "📋 Por Perfil":
        page_por_perfil(df, "reviewer")

    elif page == "🔎 Buscar Producto":
        page_buscar(df, "reviewer")

    elif page == "📊 Dashboard":
        page_dashboard(df)

    elif page == "➕ Nuevo Perfil":
        page_nuevo_perfil(rules)

    elif page == "📥 Inputs (C/X/Procesos/Anclas)":
        from _pages.data_input import main as data_input_main
        data_input_main()

    elif page == "⚙️ Costos de Proceso":
        from _pages.process_costs import main as process_costs_main
        process_costs_main()

    elif page == "🎯 Calibración":
        from _pages.calibration import main as calibration_main
        calibration_main()

    elif page == "🖼️ Analizador de Planos":
        from _pages.drawing_analyzer import main as drawing_analyzer_main
        drawing_analyzer_main()

    elif page == "➕ Ingreso de Producto":
        from _pages.product_intake import main as product_intake_main
        product_intake_main()


if __name__ == "__main__":
    main()
