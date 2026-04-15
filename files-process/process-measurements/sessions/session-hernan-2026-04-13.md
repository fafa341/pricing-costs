# Interview Session — Hernán (Jefe de Producción)
**Session ID:** hernan-2026-04-13  
**Expert:** Hernán — Jefe de Producción, Dulox  
**Date:** 2026-04-13  
**Format:** Verbal interview → transcribed to LAYER_PROCESS_COMPLEXITY.md  
**Status:** Complete (raw notes captured)

---

## Processes Covered

| # | Process | Coverage | Notes |
|---|---------|----------|-------|
| 1 | Trazado + Plegado | ✅ Combined | C1 = 1.5m mesón 2hrs; C3 = lavadero taza doble 4hrs (4 personas) |
| 2 | Corte Manual | ✅ | <3m = simple; >3m = 2 personas, 6 discos. ~4-5hrs para rodar primero |
| 3 | Corte Láser | ✅ | DXF = cuello de botella (+30min sin plano). 1mm→3mm = 3-4× más. >8mm = externo |
| 4 | Grabado Láser | ✅ | ≤10cm = ~5min. Misma persona. >10cm = externo |
| 5 | Plegado | ✅ Partial | Embedded in Trazado answer |
| 6 | Cilindrado | ✅ | 1.5mm, ø400-500mm = 20min, 1 persona. 2mm, 1000L estanque = 3hrs, 4 personas |
| 7 | Soldadura | ✅ | Simple (sin reborde) = 40min. Complejo (emplantilla) = 1.5hrs. 1 soldador always. Argón 6-8-10 m³/hr |
| 8 | Pulido | ✅ | 1.5m mesón = 1hr (1 disco fibra). Basurero = 5hrs, 3 pasadas. Multi-fily: piezas planas >400mm |
| 9 | Pintura | ❌ Not covered | Gap |
| 10 | Refrigeración | ✅ Partial | "Siempre es lo mismo" ~10 días. Aislación primero. C2/C3 not differentiated |
| 11 | Control de Calidad | ✅ | 1 mesón 1.5m = 10min. Máquinas, baños maría, filtraciones demoran más |

---

## Key Thresholds Extracted

| Process | Threshold | Unit | C-level boundary | Confidence |
|---------|-----------|------|-----------------|------------|
| Corte Manual | 3m lineal | metros | C1→C2 | expert_estimate |
| Corte Manual | 3m lineal | metros | requires 2nd person | expert_estimate |
| Corte Láser | DXF availability | flag | adds +30min setup | expert_estimate |
| Corte Láser | 1mm→3mm espesor | mm | 3-4× time increase | expert_estimate |
| Corte Láser | >8mm | mm | externalización | expert_estimate |
| Grabado Láser | 10cm | cm | internal→external switch | expert_estimate |
| Cilindrado | 400-500mm ø | mm | C1 reference | measured |
| Cilindrado | 1.5mm | mm | C1 espesor threshold | measured |
| Cilindrado | 2mm | mm | C3 espesor threshold | measured |
| Soldadura | reborde presence | flag | C1→C2 trigger | expert_estimate |
| Soldadura | emplantillado | flag | C2→C3 trigger | expert_estimate |
| Pulido | 400mm | mm | multi-fily trigger (flat surfaces) | expert_estimate |
| Pulido | 3 pasadas | count | C3 (basurero = 5hrs) | measured |
| Refrigeración | ~10 días | days | C1 baseline (all levels) | expert_estimate |

---

## Consumables Captured

| Process | C1 | C3 | Notes |
|---------|----|----|-------|
| Corte Manual | 1 disco 4.5" | 6 discos | Scales with length |
| Soldadura | Argón 6 m³/hr | Argón 10 m³/hr | 1m barra aporte stable |
| Pulido | 1 disco fibra (1.5m mesón = 1hr) | 3 pasadas, multi-fily, pasta, escobilla | Basurero = 5hrs |
| Pulido | Rueda traslapada: 1 per 5 mesones | — | Shared consumable across units |
| Refrigeración | Motor + condensador + ventilador + 2 planchas aislapol 1×2m | — | Fixed per unit |

---

## Gaps to Resolve in Next Session

| # | Gap | Priority |
|---|-----|----------|
| 1 | Trazado vs Plegado: tiempos no separados | High |
| 2 | Corte Manual: minutos exactos por metro lineal | High |
| 3 | Corte Láser: precio externo $/pieza | High |
| 4 | Pintura: no cubierto | High if applicable |
| 5 | Cilindrado C2 (1.5–2mm range): no ejemplificado | Medium |
| 6 | Refrigeración C2/C3: "siempre es lo mismo" — confirmar | Medium |
| 7 | Pulido: minutos por m² no aislados (combinado con producto) | High |
| 8 | QC embalaje: costo materiales embalaje por tipo | Low |

---

## Chunks Generated From This Session
See `knowledge-chunks.jsonl` — chunks extracted: 6 (from bom_document, not interview)

**Interview chunks pending extraction:** ~12 rules confirmed above need to be structured into chunks. Run knowledge-extractor to extract.
