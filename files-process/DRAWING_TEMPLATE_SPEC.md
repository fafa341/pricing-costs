# Drawing Template Specification — Dulox Factory Floor
**Version:** 1.2 — 2026-05-05
**Status:** Draft for validation with operators
**Changes from v1.1:** Clarified actor model (jefe de producción, not operators); added `Notas` field per part square; fixed Tubo + Perfil Kg formulas; added template version footer; added observability section; added who-photographs flow; added silent failure handling for multi-sheet products.

---

## Purpose

A printed A3 template that fits how the jefe de producción and operators already work, adds minimal structure, and produces drawings that Claude Vision can reliably parse into structured BOM data. **No new workflow — just guided paper.**

---

## Actor Model — Who Fills This Out

**The template is NOT filled out by operators on the shop floor.**

The real workflow at Dulox:

1. **Vendor → Jefe de producción:** Sales vendor hands over a written quote with overall product dimensions.
2. **Jefe de producción → Operator:** Jefe decomposes the product in conversation with the assigned operator.
3. **Operator:** Makes their own sketch on blank paper — they own it. This is their reference to cut and request material. No standardization today.
4. **Jefe photographs operator sketch:** After the operator finishes their sketch, jefe takes a photo with their phone and uploads it to the system. This is the capture moment.

**The template intercepts step 3**: instead of blank paper, the operator gets a pre-structured sheet. It does NOT change what they draw — only the paper they draw on and the field labels around the sketch area.

**Why operators will accept it:** The template looks exactly like their existing paper, just pre-labeled. No new symbols required until they're comfortable. The operator's job is unchanged: sketch the parts and write dimensions. The jefe's job gains one step: photograph the completed sheet.

**Fallback (no operator buy-in):** Jefe photographs operator's existing blank-paper sketch anyway. Vision extraction still works — it just has less structure to anchor on. The template improves extraction accuracy; it's not required.

---

## Layout: A3 Landscape (420 × 297 mm)

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ HOJA DE DESPIECE — DULOX   v1.2          SKU: ________  Fecha: ___________               │
│ Producto: ___________________________________     Dibujado por: ________________          │
│ N° piezas total: ___   Hoja: ___ / ___                                                   │
├───────────────────────────────────────────┬──────────────────────────────────────────────┤
│                                           │  PARTE 1                                     │
│                                           │  ┌──────────────────────────────────────┐   │
│                                           │  │                                      │   │
│                                           │  │   [dibujar aquí]                     │   │
│                                           │  │                                      │   │
│                                           │  └──────────────────────────────────────┘   │
│         DIBUJO PRINCIPAL                  │  Nombre: _______________________  Cant: __  │
│         (área libre — aprox.             │  □ Plancha  □ Perfil  □ Tubo                 │
│          210 × 190 mm)                    │  esp: ___ mm   L: ______  A: ______          │
│                                           │  Símbolo: ___________  Notas: ____________  │
│                                           ├──────────────────────────────────────────────┤
│                                           │  PARTE 2                                     │
│                                           │  ┌──────────────────────────────────────┐   │
│                                           │  │                                      │   │
│                                           │  │   [dibujar aquí]                     │   │
│                                           │  │                                      │   │
│                                           │  └──────────────────────────────────────┘   │
│                                           │  Nombre: _______________________  Cant: __  │
│                                           │  □ Plancha  □ Perfil  □ Tubo                 │
│                                           │  esp: ___ mm   L: ______  A: ______          │
│                                           │  Símbolo: ___________  Notas: ____________  │
├───────────────────────────────────────────┴──────────────────────────────────────────────┤
│  PARTE 3                        │  PARTE 4                   │  PARTE 5                  │
│  ┌─────────────────────────┐    │  ┌─────────────────────┐   │  ┌───────────────────┐   │
│  │                         │    │  │                     │   │  │                   │   │
│  │   [dibujar aquí]        │    │  │   [dibujar aquí]    │   │  │   [dibujar aquí]  │   │
│  │                         │    │  │                     │   │  │                   │   │
│  └─────────────────────────┘    │  └─────────────────────┘   │  └───────────────────┘   │
│  Nombre: ____________ Cant: __  │  Nombre: _________ Cant:__ │  Nombre: _______ Cant:__ │
│  □ Plancha □ Perfil □ Tubo      │  □ Plancha □ Perfil □ Tubo │  □ Plancha □ Tubo        │
│  esp: __ L: ____  A: ____       │  esp: __ L: ____  A: ____  │  esp: __ L: ____  A: ___ │
│  Símbolo: __________________    │  Símbolo: _________________│  Símbolo: _______________│
│  Notas: ____________________    │  Notas: _________________  │  Notas: ________________ │
└─────────────────────────────────┴────────────────────────────┴───────────────────────────┘
```

**Grid zones:**
- **Zone A (left):** Main assembly drawing, ~210 × 190 mm. Free-form. Full assembly, with overall dimensions. Operator draws exactly as today.
- **Zone B (right, stacked):** Parts 1–2. Each square ~195 × 85 mm. Larger squares — use for the most complex parts.
- **Zone C (bottom row):** Parts 3–5. Each square ~130 × 80 mm.

**Total squares: 5 per sheet.** Use a second sheet for products with more parts (mark `Hoja: 2 / 2`).

> **Go/no-go gate before printing:** Confirm with Hernán that 5 squares covers ≥80% of products. If most products have 6–8 parts, expand Zone B to 3 stacked squares (adds 1 square at the cost of Zone A height).

---

## Header Fields

| Field | Purpose | Notes |
|-------|---------|-------|
| SKU | ERP product code (e.g., PT0001) | Leave blank for new products |
| Producto | Full product name | |
| Fecha | Date drawn | |
| Dibujado por | Operator name or initials | |
| **N° piezas total** | Total count of distinct parts in this product | **Critical for multi-sheet detection** |
| **Hoja: ___ / ___** | Sheet number if product spans >1 sheet | e.g., "Hoja: 1 / 2" |
| **v1.2** (pre-printed) | Template version — pre-printed in corner | Lets extraction schema know which symbol vocabulary applies |

The `N° piezas total` + `Hoja` fields are the solution to the silent multi-sheet failure: if Vision extracts 5 parts from sheet 1 but `N° piezas total` = 9, the system flags the BOM as incomplete and prompts the user to upload the second sheet.

---

## What Goes in Each Part Square

Each square captures one distinct piece (flat blank, cut profile, bent part, tube, etc.).

### Fixed fields per square:

| Field | Description | How to fill |
|-------|-------------|-------------|
| **Nombre** | Part name in plain Spanish | e.g., "Costado izquierdo", "Tapa superior", "Base" |
| **Cant** | Quantity of this part in the assembly | e.g., `2`. **Default: 1 if blank.** |
| **Tipo** | Checkbox: Plancha / Perfil / Tubo | Tick one |
| **esp** | Thickness in mm | e.g., `1.5` |
| **L** | Length in mm (after cut) | e.g., `400` |
| **A** | Width in mm (after cut); for round parts: diameter (write `Ø`) | e.g., `300` or `Ø150` |
| **Símbolo** | Process/finish flags (see symbol legend below) | e.g., `P2 S`. Blank = no special process. |
| **Notas** | Free text — anything that doesn't fit the other fields | e.g., "doblar 90° en el centro". Vision logs this as `notas_raw`, does not use for cost computation. |
| **Dibujo** | Spider cross inside the square with dimension labels on arms | Same notation operators use today |

> **Cylindrical parts** (e.g., tina, tambor manto): write `A = Ø[diameter]`. e.g., `Ø600`.
> **Profiles (perfiles)**: `L = metros lineales`. Leave `A` blank or write section code (e.g., `30×30×1`).

---

## Spider Notation — Unchanged

Operators draw the spider cross exactly as they do today. No modification.

```
        [A = ancho / Ø]
             |
[L = largo]──+──[L = largo]
             |
        [H = alto]
```

The spider goes inside the drawing area of each part square.

---

## Symbol Language — 8 Symbols

Written in the **Símbolo** field. They encode what geometry alone cannot express.

| Symbol | Name | Meaning | How to write |
|--------|------|---------|--------------|
| `P1` | Pulido grano 180 | Brushed / satin finish | Write `P1` |
| `P2` | Pulido grano 400+ | Mirror / espejo finish | Write `P2` |
| `T4` | Terminación T4 | Scotch-brite finish | Write `T4` |
| `⊙` | Cilindrado | Part must be roll-bent into a cylinder | Draw circle-with-dot |
| `S` | Soldadura visible | Weld seam is visible — must be ground flat | Write `S` |
| `V` | Vidrio / visor | Includes glass panel or viewing window | Write `V` |
| `M` | Mecanismo | Includes hinge, latch, drain valve, pedal | Write `M` |
| `EXT` | Externo | Process is subcontracted (laser, turning) | Write `EXT` |

**Rules:**
- Multiple symbols: separate with space. e.g., `P2 S`.
- Unrecognized symbol written by operator: Vision logs it as `simbolo_desconocido`, flags for manual review — does not silently discard.
- If none apply: leave **Símbolo** blank.
- If something doesn't fit any symbol: write a free note in **Notas**.

**Normalization (handled in software, not by operator):**
- `p2`, `P2`, `Pulido 2`, `pulido espejo`, `espejo` → all normalize to `P2`
- `cilindrado`, `cil`, `⊙` → all normalize to `⊙`

---

## What the Template Does NOT Ask Anyone to Do

- ❌ No material SKU lookup (e.g., "MP0001") — system resolves from `esp` + `tipo` via `inventory_map.json`
- ❌ No Kg calculations on paper — Python computes from geometry
- ❌ No process time estimates
- ❌ No cost data

The template captures **geometry + finish + special flags only**.

---

## Derivation Chain

```
Paper template (completed by operator, photographed by jefe de producción)
  │
  ▼ (phone photo → upload to Streamlit ingreso-productos page)
  │
  ▼
DRAWING-EXTRACTOR AGENT  (.claude/agents/drawing-extractor.md)
  Input:  image + template_version (read from header)
  Output: { sku, fecha, n_piezas_total, hoja, partes: [{ nombre, tipo, esp, L, A, cant, simbolos[], notas_raw }] }
  Schema: dulox-bom-extract-v1  (see agent for full schema)
  │
  ▼ Multi-sheet check:
    IF len(partes) < n_piezas_total → flag BOM incomplete, prompt jefe to upload next sheet
  │
  ▼
KG CALCULATOR  (Python, deterministic)

  Plancha  → Kg = L_mm × A_mm × esp_mm × 0.00000793 × waste_factor
  Tubo     → Kg = π × Ø_mm × esp_mm × L_mm × 0.00000793 × waste_factor
  Perfil   → Kg = L_m × kg_por_metro[section_code]
               where kg_por_metro lives in inventory_map.json under the section entry
               (NOT derivable from geometry alone — must be a lookup)
  │
  ▼
INVENTORY_MAP.JSON  (dataset/inventory_map.json)
  Key: '{tipo}_{calidad}_{esp_mm}' → { sku_erp, precio_kg, unidad: 'kg', disponible: true/false }
  Key miss → flag part as 'precio_manual_requerido' — do NOT assume 0
  │
  ▼
MATERIAL COST  = Σ (Kg × cant × precio_kg) per part
  │
  ▼
ERP IMPORT ROW  (Articulo Consumo + Cantidad)
  + BOM row inserted into products.db bom_parts table
  + Extraction logged to bom_extraction_log table (see Observability below)
```

**waste_factor defaults (pending Hernán confirmation):**

| Operation | Factor | Notes |
|-----------|--------|-------|
| Corte plancha rectangular | 1.05 | 5% cutting waste |
| Corte plancha circular | 1.22 | Corner waste from sheet |
| Cilindrado (manto) | 1.08 | Edge trim + alignment |
| Plegado | 1.05 | Bend allowance |
| Corte perfil/tubo | 1.10 | End cuts + kerf |

> **These are placeholders. Confirm with Hernán before Phase 2.**

---

## Observability — What We Track Per Extraction

Each extraction logs to a `bom_extraction_log` table in `products.db`:

| Column | Value |
|--------|-------|
| `sku` | Product SKU from header |
| `fecha_foto` | Date on the template header |
| `fecha_extraccion` | Datetime of extraction |
| `n_partes_extraidas` | Count of parts Vision returned |
| `n_partes_declaradas` | `N° piezas total` from header |
| `campos_corregidos` | Count of fields user edited in validation screen |
| `campos_totales` | Total editable fields in extraction |
| `template_version` | Version string from header (e.g., `v1.2`) |
| `operador` | `Dibujado por` field from header |
| `incompleto` | Boolean — true if n_partes_extraidas < n_partes_declaradas |

**Aggregate metric to monitor:** `campos_corregidos / campos_totales` per week. If this rises above 10%, either photo quality has dropped or the template needs adjustment.

---

## Who Photographs and Uploads

**Photographer:** Jefe de producción (or you, during Phase 1).

**Flow:**
1. Operator finishes their decomposition sketch on the template sheet.
2. Jefe takes a photo with their phone — flat surface, good light, no shadow over fields.
3. Jefe uploads to Streamlit app → `ingreso-productos` page.
4. System runs Vision extraction → shows validation screen.
5. Jefe reviews, corrects any misread fields, confirms.
6. BOM is committed to `products.db`.

**Operators do not interact with the Streamlit app.** Their friction is zero.

**Lighting note for jefe:** Place sheet on a flat surface under fluorescent/natural light. Avoid using flash directly (creates glare on pencil). Phone should be directly overhead (not angled). One photo per sheet — do not crop.

---

## Photo → Extraction Failure Modes

| Field | Failure mode | Recovery |
|-------|-------------|---------|
| Photo quality | Shadow / glare obscures field | Retake photo — one sentence instruction in Streamlit |
| `esp` (handwritten) | `1.5` reads as `1.6` or `1.S` | Jefe corrects in validation screen |
| `L` / `A` (numbers) | `400` reads as `100` (phone angle) | Jefe corrects |
| `Símbolo` | `P2` reads as `P3` or blank | Jefe corrects |
| `Cant` blank | null → system defaults to 1 | No action needed |
| `Tipo` checkbox | Faint pencil → misread | Jefe corrects |
| **Multi-sheet** | Second sheet never uploaded | `N° piezas` field triggers warning: "Declared 9 parts, extracted 5 — upload sheet 2" |
| `inventory_map` key miss | New material not in map | Part flagged "precio_manual_requerido" — does not block the rest of the BOM |
| Unknown Símbolo | Operator writes `XX` | Logged as `simbolo_desconocido`, flagged for manual review |

All failures are recoverable in the validation screen except the multi-sheet case, which is handled by the `N° piezas total` check.

---

## Printing and Distribution

- Print A3 landscape. Version number pre-printed in header (`v1.2`).
- Laminate one completed example sheet per workstation as reference (use a real product people know).
- Keep stack of blank sheets at each workstation.
- Completed sheets go in the job folder as today. Jefe photographs before filing.

---

## Open Questions for Hernán (Before Phase 2 Print Run)

| # | Question | Why it matters |
|---|----------|----------------|
| Q1 | Is 5 part squares enough for ≥80% of products? | Go/no-go for Zone B layout (expand to 3 squares if needed) |
| Q2 | Do operators always know `esp` at drawing time, or do they look it up? | If they look it up: add a "consultar a jefe" cue next to `esp` field |
| Q3 | Is `Símbolo` a natural word for operators, or should it be `Acabado` / `Proceso especial`? | Blank fill rate |
| Q4 | For profiles: metros lineales or pieces × length per piece? | Kg formula input |
| Q5 | Waste factors — validate the 5 values in the table above | Correct Kg computation |
| Q6 | Should the `Notas` field be labeled `Observación` in the factory context? | Operator familiarity |

---

## Next Steps

### Phase 1 — Observe and validate (this week)
1. Print 3 hand-labeled A3 mock-ups (no printer needed — fold + label)
2. Walk jefe through 3 products using mock-ups — observe, don't instruct
3. Photograph completed sheets → run through drawing-extractor agent
4. **Validation gate:** 10+ products before Phase 2
   - Pass: extracted Kg wrong by <20% vs ground truth on all parts
   - Measure: Símbolo fill rate (if blank >20%, activate symbol legend on template)
   - Measure: `N° piezas total` fill rate (if blank >50%, make it bolder / mandatory-looking)

### Phase 2 — Deploy small (next week)
- Print 20 sheets + 2 laminated reference cards (use real product as example)
- Deploy to 2 workstations via jefe
- Collect for 1 week, review all extractions in ingreso-productos
- Target: <5% field error rate per extraction

### Phase 3 — Full deployment (month 1)
- Print 200 sheets + 5 laminated cards
- Full deployment
- BOM pipeline live — every job generates a BOM row and ERP import row

---

## Template Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-04-18 | Initial layout — 5 squares, no Cant field |
| v1.1 | 2026-05-04 | Added Cant; expanded to 7 squares; per-tipo Kg formulas |
| v1.2 | 2026-05-05 | Actor model clarified (jefe, not operators); added Notas field; fixed Tubo/Perfil Kg formulas; added N° piezas + Hoja header fields; added observability, failure modes, who-photographs; version pre-printed on template |
