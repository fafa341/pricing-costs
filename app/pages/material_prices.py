"""
material_prices.py — Global material price constants editor.

Shows all ERP catalog materials with their $/kg or $/ML price.
Prices here are the DEFAULT for new BOM rows — each row can still override.
Saved to Supabase app_settings key 'material_prices'.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "core"))

import streamlit as st
import pandas as pd
from db import load_material_prices, save_material_prices
from bom_calc import DEFAULT_GLOBAL_PRICES


def _get_prices() -> dict:
    """Load from Supabase; fall back to hardcoded defaults."""
    prices = load_material_prices()
    if not prices:
        return DEFAULT_GLOBAL_PRICES
    # Merge: ensure all default keys exist (for new materials added later)
    merged = {**DEFAULT_GLOBAL_PRICES}
    for k, v in prices.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v
    return merged


def main():
    st.markdown("## 💲 Precios Globales de Materiales")
    st.caption(
        "Estos precios son el valor por defecto para filas de BOM nuevas. "
        "Cada fila puede tener un precio distinto (override). "
        "Cambiar aquí no actualiza BOMs ya guardados."
    )

    prices = _get_prices()
    changed = False

    # ── Planchas ──────────────────────────────────────────────────────────────
    st.markdown("### Planchas y Coils — $/kg")
    st.caption("Precio por kg. Aplica a tipo=Plancha y tipo=Coil.")

    plancha_prices = prices.get("planchas", {})
    # Build display rows
    plancha_rows = []
    for calidad, esps in sorted(plancha_prices.items()):
        for esp, precio in sorted(esps.items(), key=lambda x: float(x[0])):
            plancha_rows.append({
                "Calidad": calidad,
                "Espesor (mm)": float(esp),
                "$/kg": int(precio),
            })

    if plancha_rows:
        pl_df = pd.DataFrame(plancha_rows)
        edited_pl = st.data_editor(
            pl_df,
            key="pl_prices_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "Calidad":       st.column_config.TextColumn("Calidad", disabled=True, width="small"),
                "Espesor (mm)":  st.column_config.NumberColumn("Espesor mm", disabled=True, format="%.1f", width="small"),
                "$/kg":          st.column_config.NumberColumn("$/kg", format="$ %d", step=50, min_value=0, width="medium"),
            }
        )
    else:
        edited_pl = pd.DataFrame(plancha_rows)

    # ── Perfiles ──────────────────────────────────────────────────────────────
    st.markdown("### Perfiles / Tubos / Macizos — $/ML")
    st.caption("Precio por metro lineal. Aplica a tipo=Perfil, Tubo, Macizo.")

    ml_rows = [
        {"Material":    "Perfil (default)",   "$/ML": int(prices.get("perfil_default",  3800)), "_key": "perfil_default"},
        {"Material":    "Tubo (default)",      "$/ML": int(prices.get("tubo_default",    4693)), "_key": "tubo_default"},
        {"Material":    "Macizo (default)",    "$/ML": int(prices.get("macizo_default",   950)), "_key": "macizo_default"},
    ]
    ml_df = pd.DataFrame(ml_rows)
    edited_ml = st.data_editor(
        ml_df[["Material", "$/ML"]],
        key="ml_prices_editor",
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "Material": st.column_config.TextColumn("Material", disabled=True, width="medium"),
            "$/ML":     st.column_config.NumberColumn("$/ML", format="$ %d", step=50, min_value=0, width="medium"),
        }
    )

    # ── ERP catalog reference ─────────────────────────────────────────────────
    with st.expander("📋 Catálogo ERP completo (referencia)"):
        erp_data = [
            # Planchas
            {"SKU": "PL-304-2B-3000x1000-08",   "Descripción": "Plancha 304 2B 3000×1000×0.8mm",    "Unidad": "KG", "Precio": 3000},
            {"SKU": "PL-304-T4-3000x1500-08",   "Descripción": "Plancha 304 T4 3000×1500×0.8mm",    "Unidad": "KG", "Precio": 3600},
            {"SKU": "PL-304-2B-3000x1000-10",   "Descripción": "Plancha 304 2B 3000×1000×1.0mm",    "Unidad": "KG", "Precio": 3600},
            {"SKU": "PL-304-2B-3000x1500-10",   "Descripción": "Plancha 304 2B 3000×1500×1.0mm",    "Unidad": "KG", "Precio": 3600},
            {"SKU": "PL-304-2B-3000x1000-15",   "Descripción": "Plancha 304 2B 3000×1000×1.5mm",    "Unidad": "KG", "Precio": 3600},
            {"SKU": "PL-304-2B-3000x1500-15",   "Descripción": "Plancha 304 2B 3000×1500×1.5mm",    "Unidad": "KG", "Precio": 3000},
            {"SKU": "PL-304-T4-3000x1500-15",   "Descripción": "Plancha 304 T4 3000×1500×1.5mm",    "Unidad": "KG", "Precio": 3600},
            {"SKU": "PL-304-2B-3000x1000-20",   "Descripción": "Plancha 304 2B 3000×1000×2.0mm",    "Unidad": "KG", "Precio": 3600},
            {"SKU": "PL-304-2B-3000x1000-30",   "Descripción": "Plancha 304 2B 3000×1000×3.0mm",    "Unidad": "KG", "Precio": 3600},
            {"SKU": "PL-201-2B-3000x1000-15",   "Descripción": "Plancha 201 2B 3000×1000×1.5mm",    "Unidad": "KG", "Precio": 3600},
            {"SKU": "PL-430-B-3000x1250-08",    "Descripción": "Plancha 430 B 3000×1250×0.8mm",     "Unidad": "KG", "Precio": 3600},
            {"SKU": "PL-430-BA-2000x1000-10",   "Descripción": "Plancha 430 BA 2000×1000×1.0mm",    "Unidad": "KG", "Precio": 3600},
            {"SKU": "PL-304-PERF4-3000x1000-08","Descripción": "Plancha 304 Perf 4mm 0.8mm",         "Unidad": "KG", "Precio": 2600},
            {"SKU": "PL-304-PERF6-3000x1000-08","Descripción": "Plancha 304 Perf 6mm 0.8mm",         "Unidad": "KG", "Precio": 2600},
            # Coils
            {"SKU": "CO-304-2B-1500-08",  "Descripción": "Coil 304 2B 1500mm×0.8mm",  "Unidad": "KG", "Precio": 4600},
            {"SKU": "CO-304-T4-1500-08",  "Descripción": "Coil 304 T4 1500mm×0.8mm",  "Unidad": "KG", "Precio": 4600},
            {"SKU": "CO-304-2B-1000-10",  "Descripción": "Coil 304 2B 1000mm×1.0mm",  "Unidad": "KG", "Precio": 1650},
            {"SKU": "CO-304-2B-1500-10",  "Descripción": "Coil 304 2B 1500mm×1.0mm",  "Unidad": "KG", "Precio": 3600},
            {"SKU": "CO-201-2B-1500-10",  "Descripción": "Coil 201 2B 1500mm×1.0mm",  "Unidad": "KG", "Precio": 3600},
            {"SKU": "CO-304-2B-750-15",   "Descripción": "Coil 304 2B 750mm×1.5mm",   "Unidad": "KG", "Precio": 1600},
            {"SKU": "CO-304-2B-1000-15",  "Descripción": "Coil 304 2B 1000mm×1.5mm",  "Unidad": "KG", "Precio": 2000},
            {"SKU": "CO-304-2B-1500-15",  "Descripción": "Coil 304 2B 1500mm×1.5mm",  "Unidad": "KG", "Precio": 2900},
            # Perfiles
            {"SKU": "PF-20x20-10",  "Descripción": "Perfil Cuadrado 20×20×1.0mm", "Unidad": "ML", "Precio": 16146},
            {"SKU": "PF-30x30-10",  "Descripción": "Perfil Cuadrado 30×30×1.0mm", "Unidad": "ML", "Precio": 3800},
            {"SKU": "PF-30x30-20",  "Descripción": "Perfil Cuadrado 30×30×2.0mm", "Unidad": "ML", "Precio": 7800},
            {"SKU": "PF-40x40-15",  "Descripción": "Perfil Cuadrado 40×40×1.5mm", "Unidad": "ML", "Precio": 5500},
            {"SKU": "PF-40x40-20",  "Descripción": "Perfil Cuadrado 40×40×2.0mm", "Unidad": "ML", "Precio": 62400},
            {"SKU": "PF-60x60-20",  "Descripción": "Perfil Cuadrado 60×60×2.0mm", "Unidad": "ML", "Precio": 15200},
            {"SKU": "PF-20x40-10",  "Descripción": "Perfil Rect 20×40×1.0mm",     "Unidad": "ML", "Precio": 0},
            {"SKU": "PF-20x40-15",  "Descripción": "Perfil Rect 20×40×1.5mm",     "Unidad": "ML", "Precio": 0},
            # Tubos
            {"SKU": "TB-112-10",  "Descripción": "Tubo 1½\"×1.0mm",   "Unidad": "ML", "Precio": 4693},
            {"SKU": "TB-12-15",   "Descripción": "Tubo ½\"×1.5mm",    "Unidad": "ML", "Precio": 0},
            {"SKU": "TB-2-15",    "Descripción": "Tubo 2\"×1.5mm",    "Unidad": "ML", "Precio": 9387},
            {"SKU": "TB-34-10",   "Descripción": "Tubo ¾\"×1.0mm",    "Unidad": "ML", "Precio": 2266},
            {"SKU": "TB-34-15",   "Descripción": "Tubo ¾\"×1.5mm",    "Unidad": "ML", "Precio": 3358},
            {"SKU": "TB-CAN-4",   "Descripción": "Cañería 4mm",        "Unidad": "ML", "Precio": 13038},
            {"SKU": "TB-CAN-10",  "Descripción": "Cañería 10mm",       "Unidad": "ML", "Precio": 15021},
            # Macizos
            {"SKU": "MA-14",       "Descripción": "Macizo 1/4\"",        "Unidad": "ML", "Precio": 950},
            {"SKU": "MA-BARRA-10", "Descripción": "Barra Maciza 10mm",   "Unidad": "ML", "Precio": 4200},
            {"SKU": "MA-BARRA-8",  "Descripción": "Barra Maciza 8mm",    "Unidad": "ML", "Precio": 4200},
            {"SKU": "MA-HEX-1",    "Descripción": "Hexagonal 1\"",        "Unidad": "ML", "Precio": 9000},
            {"SKU": "MA-HEX-112",  "Descripción": "Hexagonal 1½\"",       "Unidad": "ML", "Precio": 9000},
            {"SKU": "MA-HEX-34",   "Descripción": "Hexagonal ¾\"",        "Unidad": "ML", "Precio": 9000},
        ]
        st.dataframe(
            pd.DataFrame(erp_data),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Precio": st.column_config.NumberColumn("Precio ERP", format="$ %d"),
            }
        )

    # ── Save ──────────────────────────────────────────────────────────────────
    st.divider()
    if st.button("💾 Guardar precios globales", type="primary"):
        # Rebuild plancha prices from edited table
        new_planchas = {}
        for _, r in edited_pl.iterrows():
            cal = str(r["Calidad"])
            esp = f"{float(r['Espesor (mm)']):.1f}"
            new_planchas.setdefault(cal, {})[esp] = int(r["$/kg"])

        # Rebuild ML defaults
        ml_keys    = [row["_key"] for row in ml_rows]
        new_prices = {
            "planchas":       new_planchas,
            "perfil_default": int(edited_ml.iloc[0]["$/ML"]),
            "tubo_default":   int(edited_ml.iloc[1]["$/ML"]),
            "macizo_default": int(edited_ml.iloc[2]["$/ML"]),
        }
        save_material_prices(new_prices)
        st.success("✅ Precios globales guardados. Los próximos BOMs usarán estos valores.")
        st.rerun()

    st.info(
        "💡 Cambios aquí afectan solo filas nuevas o filas sin override. "
        "Para actualizar un BOM ya guardado, ábrelo y haz click en Guardar BOM."
    )


if __name__ == "__main__":
    main()
