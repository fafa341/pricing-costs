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
import requests
import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
DB   = ROOT / "dataset" / "products.db"

PERFILES = [
    "p-basurero-cil", "p-basurero-rect", "p-campana", "p-carro-bandejero",
    "p-carro-traslado", "p-cilindrico", "p-cocina-gas", "p-custom",
    "p-electrico", "p-laminar-simple", "p-laser", "p-lavadero",
    "p-meson", "p-modulo", "p-rejilla", "p-sumidero", "p-tina",
]
COMPLEJIDADES = ["C1", "C2", "C3"]

# ─── Profile knowledge: what C1/C2/C3 means per perfil ───────────────────────
# Used to show context in candidate review cards.

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
               dim_confidence, G, D, validated, validated_by, validated_at
        FROM products
        WHERE perfil_proceso != 'p-importado'
        ORDER BY perfil_proceso, complejidad, handle
    """, conn)
    conn.close()
    return df

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
def fetch_product_image(url: str) -> str | None:
    """
    Fetch og:image URL from a Shopify product page.
    Returns the CDN image URL string, or None on failure.
    Cached for 1h per URL — only one HTTP request per product per session.
    """
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https://[^"\']+)["\']', resp.text)
        if not match:
            match = re.search(r'<meta[^>]+content=["\'](https://[^"\']+)["\'][^>]+property=["\']og:image["\']', resp.text)
        return match.group(1).split("?")[0] if match else None
    except Exception:
        return None


# ─── Audit candidates (replicate Test 3 logic) ────────────────────────────────

def compute_candidates(df):
    """Return list of products where another bucket is ≥40% closer.
    Includes reasoning: which driver is driving the suggestion and why."""
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
        context = PROFILE_CONTEXT.get(perfil, {})
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
        img_url = fetch_product_image(url)
        if img_url:
            st.image(img_url, use_container_width=True)
        else:
            st.markdown(
                '<div style="height:100px;display:flex;align-items:center;'
                'justify-content:center;color:#484f58;font-size:0.75rem;'
                'border:1px solid #30363d;border-radius:6px;">sin imagen</div>',
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

def candidate_context_card(c, df, reviewer_key):
    """Rich card for a single audit candidate showing full reasoning + bucket comparison."""
    row = df[df["handle"] == c["handle"]]
    if row.empty:
        return
    row = row.iloc[0].to_dict()

    handle      = c["handle"]
    perfil      = c["current_perfil"]
    curr_comp   = c["current_comp"]
    sugg_comp   = c["suggested_comp"]
    reasoning   = c["reasoning"]
    ctx         = PROFILE_CONTEXT.get(perfil, {})

    # ── Card header ───────────────────────────────────────────────────────────
    direction_emoji = "⬆️" if reasoning["upgrade"] else "⬇️"
    url = row.get("url", "")
    url_md = f' <a href="{url}" style="font-size:0.75rem;color:#58a6ff;" target="_blank">↗ dulox.cl</a>' if url else ""

    hdr_col, img_col = st.columns([4, 1])
    with hdr_col:
        st.markdown(
            f'<div class="dulox-card">'
            f'<div style="display:flex;align-items:center;gap:0.7rem;margin-bottom:0.5rem;">'
            f'{direction_emoji} '
            f'<code style="font-size:0.85rem;color:#79c0ff;background:#161b22;">{handle}</code>'
            f'{url_md}'
            f'</div>',
            unsafe_allow_html=True
        )
    with img_col:
        img_url = fetch_product_image(url)
        if img_url:
            st.image(img_url, use_container_width=True)

    desc = str(row.get("descripcion_web", "") or "")
    if desc:
        st.markdown(
            f'<p style="color:#8b949e;font-size:0.82rem;margin:0 0 0.8rem 0;">{desc[:280]}</p>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Current → suggested comparison ────────────────────────────────────────
    col1, col2, col3 = st.columns([5, 2, 5])
    with col1:
        cg = c['current_bucket'].get('g_mean')
        cd = c['current_bucket'].get('d_mean')
        cg_str = f"{cg:.2f}" if cg is not None else "—"
        cd_str = f"{cd:.2f}" if cd is not None else "—"
        level_txt = ctx.get("levels", {}).get(curr_comp, "")
        st.markdown(
            f'<div class="dulox-card">'
            f'<div class="dulox-section-label">CATEGORÍA ACTUAL</div>'
            f'<div style="display:flex;gap:0.5rem;align-items:center;margin:0.4rem 0;">'
            f'{profile_badge(perfil)} {complexity_badge(curr_comp)}'
            f'</div>'
            f'<div style="font-size:0.78rem;color:#768390;margin-top:0.4rem;">{level_txt}</div>'
            f'<div style="font-size:0.75rem;color:#484f58;margin-top:0.5rem;">'
            f'Centroide G={cg_str} D={cd_str} · n={c["current_bucket"]["n"]}'
            f'</div></div>',
            unsafe_allow_html=True
        )
    with col2:
        g_val = c["G"]
        d_val = c["D"]
        g_str = str(int(g_val)) if g_val is not None else "—"
        d_str = str(int(d_val)) if d_val is not None else "—"
        st.markdown(
            f'<div style="text-align:center;padding:1.2rem 0;">'
            f'<div style="font-size:1.6rem;">→</div>'
            f'<div style="font-size:0.75rem;color:#768390;margin-top:0.4rem;">Este producto</div>'
            f'<div style="font-family:monospace;font-size:0.88rem;color:#cdd9e5;margin-top:0.3rem;">'
            f'G=<b>{g_str}</b> D=<b>{d_str}</b></div>'
            f'<div class="dist-chip" style="margin-top:0.5rem;">Δ={c["gap"]:.3f}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with col3:
        g_m = c['suggested_bucket'].get('g_mean')
        d_m = c['suggested_bucket'].get('d_mean')
        g_m_str = f"{g_m:.2f}" if g_m is not None else "—"
        d_m_str = f"{d_m:.2f}" if d_m is not None else "—"
        sugg_level_txt = ctx.get("levels", {}).get(sugg_comp, "")
        st.markdown(
            f'<div class="dulox-card-accent">'
            f'<div class="dulox-section-label" style="color:#388bfd;">SUGERIDO</div>'
            f'<div style="display:flex;gap:0.5rem;align-items:center;margin:0.4rem 0;">'
            f'{profile_badge(perfil)} {complexity_badge(sugg_comp)}'
            f'</div>'
            f'<div style="font-size:0.78rem;color:#768390;margin-top:0.4rem;">{sugg_level_txt}</div>'
            f'<div style="font-size:0.75rem;color:#484f58;margin-top:0.5rem;">'
            f'Centroide G={g_m_str} D={d_m_str} · n={c["suggested_bucket"]["n"]}'
            f'</div></div>',
            unsafe_allow_html=True
        )

    st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)

    # Why this suggestion was made
    with st.expander("🧮 Por qué el modelo hace esta sugerencia", expanded=True):
        st.markdown("**Driver que genera la discrepancia:**")
        for r in reasoning["reasons"]:
            st.markdown(f"- {r}")

        if reasoning.get("driver_warning"):
            st.warning(reasoning["driver_warning"])

        st.markdown("**Driver primario declarado para este perfil:** "
                    f"`{ctx.get('primary_driver', '—')}`")
        if ctx.get("driver_note"):
            st.caption(ctx["driver_note"])

    # What changing implies
    with st.expander("💰 Qué implicaría el cambio"):
        st.markdown(reasoning.get("implication", "—"))

        # Show the level definitions side by side
        levels = ctx.get("levels", {})
        if curr_comp in levels and sugg_comp in levels:
            c1_, c2_ = st.columns(2)
            with c1_:
                st.markdown(f"**{curr_comp} (actual):**")
                st.markdown(levels[curr_comp])
            with c2_:
                st.markdown(f"**{sugg_comp} (sugerido):**")
                st.markdown(levels[sugg_comp])

    # Sample products from suggested bucket for comparison
    with st.expander(f"👀 Productos del grupo {sugg_comp} para comparar "
                     f"(n={c['suggested_bucket']['n']})"):
        bucket_products = df[
            (df["perfil_proceso"] == perfil) &
            (df["complejidad"] == sugg_comp)
        ][["handle", "G", "D", "dim_l_mm", "dim_w_mm", "dim_espesor_mm",
           "descripcion_web"]].head(8)

        if not bucket_products.empty:
            for _, bp in bucket_products.iterrows():
                g_ = int(bp["G"]) if pd.notna(bp["G"]) else "—"
                d_ = int(bp["D"]) if pd.notna(bp["D"]) else "—"
                desc_ = str(bp["descripcion_web"] or "")[:100]
                st.markdown(f"- **{bp['handle']}**  G={g_} D={d_}")
                if desc_:
                    st.caption(f"  {desc_}")

    # Action controls
    with st.expander("✏️ Decisión", expanded=not row.get("validated")):
        reviewer = st.session_state.get(reviewer_key, "")

        new_perfil = st.selectbox(
            "Perfil proceso", PERFILES,
            index=PERFILES.index(perfil) if perfil in PERFILES else 0,
            key=f"perfil_{handle}"
        )
        new_comp = st.selectbox(
            "Complejidad", COMPLEJIDADES,
            index=COMPLEJIDADES.index(curr_comp) if curr_comp in COMPLEJIDADES else 0,
            key=f"comp_{handle}"
        )
        reason = st.text_input(
            "Razón (obligatorio si cambia algo)",
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
                    st.success("Validado")
                    st.rerun()
        with cb:
            if st.button(f"💾 Mover a {sugg_comp}", key=f"quick_{handle}",
                         help=f"Aplica la sugerencia del modelo: {curr_comp} → {sugg_comp}"):
                if not reviewer:
                    st.error("Ingresa tu nombre en el sidebar")
                elif not reason.strip():
                    st.error("Escribe la razón")
                else:
                    save_reclassification(
                        handle, perfil, perfil, curr_comp, sugg_comp,
                        reason.strip(), reviewer
                    )
                    st.success(f"Movido a {sugg_comp}")
                    st.rerun()
        with cc:
            changed = (new_perfil != perfil) or (new_comp != curr_comp)
            if st.button("💾 Guardar personalizado", key=f"save_{handle}",
                         disabled=not changed):
                if not reviewer:
                    st.error("Ingresa tu nombre en el sidebar")
                elif not reason.strip():
                    st.error("Escribe la razón")
                else:
                    save_reclassification(
                        handle, perfil, new_perfil, curr_comp, new_comp,
                        reason.strip(), reviewer
                    )
                    st.success(f"Guardado")
                    st.rerun()

    # History
    hist = load_history(handle)
    if not hist.empty:
        with st.expander(f"Historial ({len(hist)} cambios)"):
            for _, h in hist.iterrows():
                st.markdown(
                    f"- `{h['changed_at'][:16]}` **{h['changed_by']}**: "
                    f"`{h['old_perfil']} {h['old_complejidad']}` → "
                    f"`{h['new_perfil']} {h['new_complejidad']}` — _{h['reason']}_"
                )

    if row.get("validated"):
        st.success("✅ Ya validado")


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

    for c in candidates:
        candidate_context_card(c, df, reviewer_key)
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
        f'<span style="color:#768390;font-size:0.88rem;">{len(bucket)} productos en</span>'
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
        f'<div style="font-size:2rem;font-weight:700;color:#e6edf3;">{total}</div>'
        f'<div class="dulox-section-label">TOTAL PRODUCTOS</div></div>'
        f'<div class="dulox-card" style="flex:1;min-width:120px;text-align:center;">'
        f'<div style="font-size:2rem;font-weight:700;color:#3fb950;">{val}</div>'
        f'<div class="dulox-section-label">VALIDADOS ({pct_val:.0f}%)</div></div>'
        f'<div class="dulox-card" style="flex:1;min-width:120px;text-align:center;">'
        f'<div style="font-size:2rem;font-weight:700;color:#e3b341;">{total-val}</div>'
        f'<div class="dulox-section-label">SIN VALIDAR</div></div>'
        f'<div class="dulox-card" style="flex:1;min-width:120px;text-align:center;">'
        f'<div style="font-size:2rem;font-weight:700;color:#f85149;">{no_dims}</div>'
        f'<div class="dulox-section-label">SIN DIMS G/D</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Complexity distribution
    st.markdown(
        f'<div class="dulox-card" style="margin-bottom:1.5rem;">'
        f'<div class="dulox-section-label">DISTRIBUCIÓN DE COMPLEJIDAD</div>'
        f'<div style="display:flex;gap:1.5rem;margin-top:0.6rem;">'
        f'<div>{complexity_badge("C1")} <span style="color:#cdd9e5;font-size:1.1rem;font-weight:600;margin-left:0.4rem;">{c1_n}</span></div>'
        f'<div>{complexity_badge("C2")} <span style="color:#cdd9e5;font-size:1.1rem;font-weight:600;margin-left:0.4rem;">{c2_n}</span></div>'
        f'<div>{complexity_badge("C3")} <span style="color:#cdd9e5;font-size:1.1rem;font-weight:600;margin-left:0.4rem;">{c3_n}</span></div>'
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

# ─── App ──────────────────────────────────────────────────────────────────────

CSS = """
<style>
/* ── Base ─────────────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0d1117;
    color: #e6edf3;
}
[data-testid="stSidebar"] {
    background-color: #161b22 !important;
    border-right: 1px solid #30363d;
}
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #58a6ff !important;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* ── Main title ───────────────────────────────────────────────────────── */
h1 { color: #f0f6fc !important; font-weight: 700; letter-spacing: -0.02em; }
h2 { color: #cdd9e5 !important; font-weight: 600; }
h3 { color: #adbac7 !important; }

/* ── Cards / containers ───────────────────────────────────────────────── */
.dulox-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.dulox-card-accent {
    background: #0d2137;
    border: 1px solid #1f6feb;
    border-radius: 10px;
    padding: 1rem 1.4rem;
    margin-bottom: 0.8rem;
}
.dulox-section-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #768390;
    margin-bottom: 0.3rem;
}

/* ── Complexity badges ────────────────────────────────────────────────── */
.badge { display:inline-block; padding:2px 10px; border-radius:12px;
         font-size:0.78rem; font-weight:700; letter-spacing:0.04em; }
.badge-c1 { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-c2 { background:#2d1b00; color:#e3b341; border:1px solid #9e6a03; }
.badge-c3 { background:#3d0c0c; color:#f85149; border:1px solid #da3633; }
.badge-profile { background:#1c2128; color:#79c0ff; border:1px solid #388bfd; }
.badge-ok  { background:#0d3321; color:#3fb950; border:1px solid #238636; }
.badge-warn{ background:#2d1b00; color:#e3b341; border:1px solid #9e6a03; }
.badge-gap { background:#3d0c0c; color:#f85149; border:1px solid #da3633; }

/* ── Metric overrides ─────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 0.75rem 1rem;
}
[data-testid="metric-container"] label { color: #768390 !important; font-size:0.75rem; }
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #e6edf3 !important; font-size: 1.5rem; font-weight: 700;
}

/* ── Expanders ────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    margin-bottom: 6px;
}
[data-testid="stExpander"] summary {
    color: #cdd9e5 !important;
    font-size: 0.9rem;
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] select {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    border-radius: 6px;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
[data-testid="stBaseButton-secondary"] {
    background: #21262d !important;
    border: 1px solid #30363d !important;
    color: #cdd9e5 !important;
    border-radius: 6px;
}
[data-testid="stBaseButton-secondary"]:hover {
    background: #30363d !important;
    border-color: #58a6ff !important;
}
[data-testid="stBaseButton-primary"] {
    background: #1f6feb !important;
    border: 1px solid #388bfd !important;
    color: #ffffff !important;
    border-radius: 6px;
    font-weight: 600;
}

/* ── Divider ──────────────────────────────────────────────────────────── */
hr { border-color: #21262d !important; }

/* ── Info / warning / success ─────────────────────────────────────────── */
[data-testid="stAlert"] { border-radius: 8px; }

/* ── Dataframe ────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border: 1px solid #30363d; border-radius: 8px; }

/* ── Caption / small text ─────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] p { color: #768390 !important; font-size:0.78rem; }

/* ── Candidate card header ────────────────────────────────────────────── */
.cand-arrow {
    display: flex; align-items: center; gap: 0.6rem;
    font-size: 0.88rem; color: #768390; margin-bottom: 0.4rem;
}
.dist-chip {
    background: #1c2128; border: 1px solid #30363d;
    border-radius: 6px; padding: 2px 8px;
    font-family: monospace; font-size: 0.78rem; color: #8b949e;
}
.dist-chip-good {
    background: #0d3321; border: 1px solid #238636;
    border-radius: 6px; padding: 2px 8px;
    font-family: monospace; font-size: 0.78rem; color: #3fb950;
}
</style>
"""

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
    st.markdown(CSS, unsafe_allow_html=True)

    st.markdown(
        '<h1 style="border-bottom:1px solid #21262d;padding-bottom:0.5rem;">'
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
                f'<div style="background:#0d3321;border:1px solid #238636;border-radius:6px;'
                f'padding:6px 12px;font-size:0.82rem;color:#3fb950;">✅ {reviewer}</div>',
                unsafe_allow_html=True
            )

        st.divider()
        st.markdown("### 🗂️ Navegación")
        page = st.radio("", [
            "🔍 Revisar Candidatos",
            "📋 Por Perfil",
            "🔎 Buscar Producto",
            "📊 Dashboard",
        ])

        st.divider()
        db_kb = DB.stat().st_size // 1024
        st.markdown(
            f'<div class="dulox-section-label">BASE DE DATOS</div>'
            f'<div style="font-size:0.82rem;color:#58a6ff;">products.db · {db_kb} KB</div>',
            unsafe_allow_html=True
        )
        st.markdown("")
        if st.button("🔄 Recargar datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    df = load_products()

    if page == "🔍 Revisar Candidatos":
        with st.spinner("Calculando candidatos..."):
            candidates = compute_candidates(df)
        page_candidates(df, candidates, "reviewer")

    elif page == "📋 Por Perfil":
        page_por_perfil(df, "reviewer")

    elif page == "🔎 Buscar Producto":
        page_buscar(df, "reviewer")

    elif page == "📊 Dashboard":
        page_dashboard(df)


if __name__ == "__main__":
    main()
