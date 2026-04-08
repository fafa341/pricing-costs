# Calibration Measurement Guide — 7 Anchor Products + 3 PHASE2

> **Purpose:** Capture measured data from production to validate and replace estimated thresholds in `PROCESS_THRESHOLDS.md`  
> **Method:** One standard reference size per product, measured during a normal production run  
> **Output:** Fills in actual T_setup, T_exec, consumables, and BOM → replaces interview estimates

---

## 1. Methodology

### 1.1 Tools Required

| Tool | Purpose |
|------|---------|
| Stopwatch (phone works) | Time each process independently |
| Cinta métrica / regla | Measure cut blanks before fabrication |
| Balanza de bodega | Weigh lámina before and scrap after |
| Notebook or this form | Record values during production |

### 1.2 What to Time

**Start:** First motion of the operator (picking up material, picking up tool)  
**Stop:** Piece leaves the station and operator moves to a different task

Record **setup** and **execution** separately:
- **Setup:** Calibrating machine, positioning jig, reading plano, measuring and marking
- **Execution:** Actual cutting, bending, welding, polishing

If the operator combines them: record total and note it — do not estimate.

### 1.3 What to Measure for Materials

For each product:
1. Measure dimensions of each cut blank **before** fabrication (length × width × espesor)
2. Calculate theoretical area and weight: `kg = L(m) × W(m) × espesor(mm) × 7.9 kg/dm³`
3. After production: weigh scrap pile for that job
4. **Waste Factor** = scrap weight / total material weight

### 1.4 What to Count for Consumables

Do a stock count before and after the job:
- Discos de corte 4.5"
- Discos de fibra (pulido)
- Disco de lija (pliego)
- Rueda traslapada
- Barra de aporte TIG (medir longitud usada)

For argón: note the pressure gauge reading before and after, or use flow meter reading × minutes.

### 1.5 When NOT to Measure

- Do not measure during rushed or atrasado orders — times will not be representative
- Do not measure on prototype or first-of-a-kind pieces — measure repetitive standard production
- Do not measure the first unit of a new batch — operators are still warming up
- If process is interrupted (phone call, material wait), note interruption and subtract

### 1.6 Reference Size Selection

For each product, we measure **one specific standard size** — the most frequently produced configuration. This becomes the **cost origin point** from which all other sizes scale.

```
Cost(size_new) = Cost(reference) × (dimension_new / dimension_ref)^α
```

Where α by process:
- Material cost: α = 1.0 (linear with area)
- Labor execution time: α ≈ 0.8–1.0 (sub-linear for large pieces due to fixed setup)
- Setup time: α = 0 (does not scale with size)
- Consumables: α ≈ 1.0 (scale with area or linear meters)

---

## 2. Measurement Cards

---

### PRODUCTO 1 — Cubrejunta

**Reference size to measure:** `2.4 m × ___mm ancho × ___mm espesor`  
**Why this size:** Standard sheet length, most frequently quoted  
**Global tier:** C1 | **Active processes:** Trazado, Corte Manual, Plegado, Pulido, Control Calidad  
**Priority:** 1 (simplest — validates the framework before moving to complex products)

#### Process Measurements

| Proceso | Aplica | Nivel esperado | T_setup medido (min) | T_exec medido (min) | T_total | n_ops | Observaciones |
|---------|--------|---------------|---------------------|---------------------|---------|-------|---------------|
| Trazado | ✅ | C1 | | | | 1 | |
| Corte Manual | ✅ | C1 | | | | 1 | metros lineales: ___ m |
| Corte Láser | ➖ | — | — | — | — | — | |
| Grabado Láser | ➖ | — | — | — | — | — | |
| Plegado | ✅ | C1 | | | | 1 | # dobleces: ___ |
| Cilindrado | ➖ | — | — | — | — | — | |
| Soldadura | ➖ | — | — | — | — | — | |
| Pulido | ✅ | C1 | — | | | 1 | |
| Pintura | ➖ | — | — | — | — | — | |
| Refrigeración | ➖ | — | — | — | — | — | |
| Control Calidad | ✅ | C1 | — | | | 1 | |

#### Materials BOM

| Material | Dimensión blank | Cantidad | Peso teórico (kg) | Peso scrap (kg) | Waste % |
|----------|-----------------|----------|-------------------|-----------------|---------|
| Lámina AISI 304 | ___×___×___mm | 1 | | | |
| | | | | | |

#### Consumables

| Consumable | Cantidad usada | Observaciones |
|------------|---------------|---------------|
| Disco de fibra (pulido) | | |
| Disco de lija pliego | | |
| Rueda traslapada | | |
| Otros | | |

**Dimension driver for scaling:** metros lineales de longitud  
**Date measured:** _____ | **Measured by:** _____

---

### PRODUCTO 2 — Mesón Simple

**Reference size to measure:** `900mm largo × 600mm profundidad × 860mm alto × 1mm espesor`  
**Why this size:** Standard single-counter bench — anchor for the p-meson family (87 products)  
**Global tier:** C1 | **Active processes:** Trazado, Corte Manual, Plegado (C2), Soldadura (C1), Pulido (C2), Control Calidad  
**Note:** This is the highest-volume anchor in the catalog. Plegado and Pulido are C2 — use this to validate the C1→C2 boundary for those processes.

#### Process Measurements

| Proceso | Aplica | Nivel esperado | T_setup medido (min) | T_exec medido (min) | T_total | n_ops | Observaciones |
|---------|--------|---------------|---------------------|---------------------|---------|-------|---------------|
| Trazado | ✅ | C1 | | | | 1 | |
| Corte Manual | ✅ | C1 | | | | 1 | metros lineales: ___ m |
| Corte Láser | ➖ | — | — | — | — | — | |
| Grabado Láser | ➖ | — | — | — | — | — | |
| Plegado | ✅ | C2 | | | | 1–2 | # dobleces: ___, largo pieza: ___ m |
| Cilindrado | ➖ | — | — | — | — | — | |
| Soldadura | ✅ | C1 | | | | 1 | # uniones: ___ (esquinas + refuerzo) |
| Pulido | ✅ | C2 | — | | | 1 | superficie visible: top + frente |
| Pintura | ➖ | — | — | — | — | — | |
| Refrigeración | ➖ | — | — | — | — | — | |
| Control Calidad | ✅ | C1 | — | | | 1 | |

#### Materials BOM

| Material | Dimensión blank | Cantidad | Peso teórico (kg) | Peso scrap (kg) | Waste % |
|----------|-----------------|----------|-------------------|-----------------|---------|
| Lámina AISI 304 (cubierta / top) | ___×___×___mm | 1 | | | |
| Lámina AISI 304 (paneles laterales) | ___×___×___mm | 2 | | | |
| Lámina AISI 304 (frente / fondo) | ___×___×___mm | 2 | | | |
| Lámina AISI 304 (zócalo / refuerzo) | ___×___×___mm | | | | |

#### Consumables

| Consumable | Cantidad usada | Observaciones |
|------------|---------------|---------------|
| Gas Argón (m³/hr × tiempo hr) | | |
| Barra de aporte TIG (m) | | |
| Disco de fibra | | |
| Rueda traslapada | | |
| Otros | | |

**Dimension driver for scaling:** metros de largo del mesón  
**Date measured:** _____ | **Measured by:** _____

---

### PRODUCTO 3 — Sumidero

**Reference size to measure:** `___mm × ___mm (planta) × ___mm alto`  
**Why this size:** Most sold standard model  
**Global tier:** C1 | **Active processes:** Trazado, Corte Manual, Plegado, Soldadura, Pulido, Control Calidad

#### Process Measurements

| Proceso | Aplica | Nivel esperado | T_setup medido (min) | T_exec medido (min) | T_total | n_ops | Observaciones |
|---------|--------|---------------|---------------------|---------------------|---------|-------|---------------|
| Trazado | ✅ | C1 | | | | 1 | |
| Corte Manual | ✅ | C1 | | | | 1 | metros lineales: ___ m |
| Corte Láser | ❓ | C1 | | | | 1 | ¿Se usa para perforaciones? |
| Grabado Láser | ➖ | — | — | — | — | — | |
| Plegado | ✅ | C1 | | | | 1 | # dobleces: ___ |
| Cilindrado | ➖ | — | — | — | — | — | |
| Soldadura | ✅ | C1 | | | | 1 | # uniones: ___ |
| Pulido | ✅ | C1 | — | | | 1 | |
| Pintura | ➖ | — | — | — | — | — | |
| Refrigeración | ➖ | — | — | — | — | — | |
| Control Calidad | ✅ | C1 | — | | | 1 | ¿prueba filtración? |

#### Materials BOM

| Material | Dimensión blank | Cantidad | Peso teórico (kg) | Peso scrap (kg) | Waste % |
|----------|-----------------|----------|-------------------|-----------------|---------|
| Lámina AISI 304 (cuerpo) | ___×___×___mm | | | | |
| Lámina AISI 304 (fondo / tapa) | ___×___×___mm | | | | |

#### Consumables

| Consumable | Cantidad usada | Observaciones |
|------------|---------------|---------------|
| Gas Argón (m³/hr × tiempo hr) | | |
| Barra de aporte TIG (m) | | |
| Disco de fibra | | |
| Otros | | |

**Dimension driver for scaling:** Área de planta (L × W mm²)  
**Date measured:** _____ | **Measured by:** _____

---

### PRODUCTO 4 — Poruña

**Reference size to measure:** `1 kg standard (o tamaño más vendido)`  
**Why this size:** Modal product in the salsera/recipiente cylindrical family  
**Global tier:** C1 | **Active processes:** Trazado, Corte Manual, Cilindrado, Soldadura, Pulido, Control Calidad  
**Measure as batch of 10** — small cylindrical parts have noisy single-unit measurements. Divide all totals by 10.

#### Process Measurements

| Proceso | Aplica | Nivel esperado | T_setup medido (min) | T_exec medido (min) | T_total | n_ops | Observaciones |
|---------|--------|---------------|---------------------|---------------------|---------|-------|---------------|
| Trazado | ✅ | C1 | | | | 1 | |
| Corte Manual | ✅ | C1 | | | | 1 | metros lineales: ___ m (batch de 10) |
| Corte Láser | ➖ | — | — | — | — | — | |
| Grabado Láser | ➖ | — | — | — | — | — | |
| Plegado | ➖ | — | — | — | — | — | forma cilíndrica no usa plegadora |
| Cilindrado | ✅ | C1 | | | | 1 | diámetro: ___mm, espesor: ___mm |
| Soldadura | ✅ | C1 | | | | 1 | # uniones: ___ |
| Pulido | ✅ | C1–C2 | — | | | 1 | tubular → +30 min según Hernán |
| Pintura | ➖ | — | — | — | — | — | |
| Refrigeración | ➖ | — | — | — | — | — | |
| Control Calidad | ✅ | C1 | — | | | 1 | |

#### Materials BOM (por unidad — batch ÷ 10)

| Material | Dimensión blank | Cantidad | Peso teórico (kg) | Peso scrap (kg) | Waste % |
|----------|-----------------|----------|-------------------|-----------------|---------|
| Lámina AISI 304 (cuerpo cilindro) | ___×___×___mm | | | | |
| Lámina AISI 304 (fondo) | ___×___mm | | | | |
| Handle / asa (si aplica) | | | | | |

#### Consumables (por unidad)

| Consumable | Cantidad / unidad | Observaciones |
|------------|------------------|---------------|
| Gas Argón | | |
| Barra de aporte TIG (m) | | |
| Disco de fibra | | |
| Otros | | |

**Dimension driver for scaling:** capacidad en litros (o diámetro × altura)  
**Date measured:** _____ | **Measured by:** _____

---

### PRODUCTO 5 — Campana

**Reference size to measure:** `___mm ancho × ___mm profundidad × ___mm alto`  
**Why this size:** Standard width for commercial kitchen hood  
**Global tier:** C1–C2 | **Active processes:** Trazado, Corte Manual, Plegado (C2), Soldadura (C2), Pulido, Control Calidad

#### Process Measurements

| Proceso | Aplica | Nivel esperado | T_setup medido (min) | T_exec medido (min) | T_total | n_ops | Observaciones |
|---------|--------|---------------|---------------------|---------------------|---------|-------|---------------|
| Trazado | ✅ | C1–C2 | | | | 1 | |
| Corte Manual | ✅ | C1–C2 | | | | 1–2 | metros lineales: ___ m |
| Corte Láser | ❓ | C1 | | | | 1 | ¿se usa para la malla / perforaciones? |
| Grabado Láser | ➖ | — | — | — | — | — | |
| Plegado | ✅ | C2 | | | | 2 | # dobleces: ___, largo pieza: ___ m |
| Cilindrado | ➖ | — | — | — | — | — | |
| Soldadura | ✅ | C2 | | | | 1 | # esquinas / uniones: ___ |
| Pulido | ✅ | C1–C2 | — | | | 1 | exterior visible o solo cepillado? |
| Pintura | ➖ | — | — | — | — | — | |
| Refrigeración | ➖ | — | — | — | — | — | |
| Control Calidad | ✅ | C1–C2 | — | | | 1 | |

#### Materials BOM

| Material | Dimensión blank | Cantidad | Peso teórico (kg) | Peso scrap (kg) | Waste % |
|----------|-----------------|----------|-------------------|-----------------|---------|
| Lámina AISI 304 (cuerpo) | ___×___×___mm | | | | |
| Lámina AISI 304 (fondo / borde) | ___×___×___mm | | | | |
| Ducto / tubo salida (si aplica) | ___mm diám | | | | |

#### Consumables

| Consumable | Cantidad usada | Observaciones |
|------------|---------------|---------------|
| Gas Argón | | |
| Barra de aporte TIG (m) | | |
| Disco de fibra | | |
| Rueda traslapada | | |
| Otros | | |

**Dimension driver for scaling:** ancho de la campana (metros)  
**Date measured:** _____ | **Measured by:** _____

---

### PRODUCTO 6 — Celosía

**Reference size to measure:** `___mm × ___mm (panel estándar)`  
**Why this size:** Standard panel dimension for commercial kitchens  
**Global tier:** C1–C2 | **Active processes:** Trazado, Corte Manual, Corte Láser (si lleva perforaciones), Soldadura (C2–C3), Pulido, Control Calidad  
**Critical measurement:** Soldadura — Celosías represent maximum weld joint count → validates upper end of soldadura thresholds

#### Process Measurements

| Proceso | Aplica | Nivel esperado | T_setup medido (min) | T_exec medido (min) | T_total | n_ops | Observaciones |
|---------|--------|---------------|---------------------|---------------------|---------|-------|---------------|
| Trazado | ✅ | C1 | | | | 1 | |
| Corte Manual | ✅ | C1–C2 | | | | 1–2 | metros lineales: ___ m |
| Corte Láser | ❓ | C1 | | | | 1 | ¿se usa para celosía interna? |
| Grabado Láser | ➖ | — | — | — | — | — | |
| Plegado | ❓ | C1 | | | | 1 | ¿lleva doblez en marco? |
| Cilindrado | ➖ | — | — | — | — | — | |
| Soldadura | ✅ | C2–C3 | | | | 1 | # uniones / cruces: ___ (KEY: anotar) |
| Pulido | ✅ | C1–C2 | — | | | 1 | varillas → cepillado fino |
| Pintura | ➖ | — | — | — | — | — | |
| Refrigeración | ➖ | — | — | — | — | — | |
| Control Calidad | ✅ | C2 | — | | | 1 | |

#### Materials BOM

| Material | Dimensión blank | Cantidad | Peso teórico (kg) | Peso scrap (kg) | Waste % |
|----------|-----------------|----------|-------------------|-----------------|---------|
| Varilla o pletina AISI 304 | ___mm × ___ m | | | | |
| Lámina AISI 304 marco (si aplica) | ___×___×___mm | | | | |

#### Consumables

| Consumable | Cantidad usada | Observaciones |
|------------|---------------|---------------|
| Gas Argón (KEY: medir con cuidado) | m³/hr × ___ hr | mayor consumo por muchas uniones |
| Barra de aporte TIG (m) | | |
| Disco de fibra | | |
| Escobilla (pulido varillas) | | |

**Dimension driver for scaling:** área del panel (m²)  
**Date measured:** _____ | **Measured by:** _____

---

### PRODUCTO 7 — Basurero Estándar

**Reference size to measure:** `modelo estándar 50L (o modelo más vendido)`  
**Why this size:** The C3 pulido outlier — this is the most important calibration  
**Global tier:** C1 (global) BUT Pulido = C3 | **Active processes:** Trazado, Corte Manual, Cilindrado, Plegado, Soldadura, Pulido (C3), Control Calidad  
**Critical measurement:** PULIDO — 3 passes (esmerilado → cepillado → fino). Time each pass separately.

#### Process Measurements

| Proceso | Aplica | Nivel esperado | T_setup medido (min) | T_exec medido (min) | T_total | n_ops | Observaciones |
|---------|--------|---------------|---------------------|---------------------|---------|-------|---------------|
| Trazado | ✅ | C1 | | | | 1 | |
| Corte Manual | ✅ | C1 | | | | 1 | metros lineales: ___ m |
| Corte Láser | ❓ | — | | | | — | ¿se usa para tapa o mecanismo? |
| Grabado Láser | ➖ | — | — | — | — | — | |
| Plegado | ❓ | C1 | | | | 1 | ¿lleva tapa / faldón con doblez? |
| Cilindrado | ✅ | C1 | | | | 1 | diámetro: ___mm, espesor: ___mm |
| Soldadura | ✅ | C1–C2 | | | | 1 | |
| **Pulido — PASS 1 (esmerilado)** | ✅ | **C3** | — | | | | tiempo pass 1: ___ min |
| **Pulido — PASS 2 (cepillado)** | ✅ | **C3** | — | | | | tiempo pass 2: ___ min |
| **Pulido — PASS 3 (fino)** | ✅ | **C3** | — | | | | tiempo pass 3: ___ min |
| **Pulido TOTAL** | ✅ | **C3** | — | | | 1–3 | suma de 3 passes |
| Pintura | ➖ | — | — | — | — | — | |
| Refrigeración | ➖ | — | — | — | — | — | |
| Control Calidad | ✅ | C2 | — | | | 1 | |

#### Materials BOM

| Material | Dimensión blank | Cantidad | Peso teórico (kg) | Peso scrap (kg) | Waste % |
|----------|-----------------|----------|-------------------|-----------------|---------|
| Lámina AISI 304 (cuerpo cilindro) | ___×___×___mm | | | | |
| Lámina AISI 304 (fondo) | ___×___mm | | | | |
| Lámina AISI 304 (tapa) | ___×___mm | | | | |
| Mecanismo / bisagra (importado) | — | | — | — | — |

#### Consumables (KEY: desagregar por pass de pulido)

| Consumable | Pass 1 | Pass 2 | Pass 3 | Total | Observaciones |
|------------|--------|--------|--------|-------|---------------|
| Disco de fibra | | | | | |
| Rueda traslapada | | | | | |
| Multi-fily (semi-brillo) | — | — | | | último pass |
| Escobilla | — | | | | |
| Gas Argón (soldadura) | — | — | — | m³/hr × hr | |
| Barra de aporte TIG (m) | — | — | — | | |

**Dimension driver for scaling:** capacidad en litros (volumen) o altura × diámetro  
**Date measured:** _____ | **Measured by:** _____

---

## 3. Extrapolation Group Map

Once each anchor product is measured, these are the products that inherit its cost structure:

| Anchor measured | Extrapolates to | Scaling driver | Expected accuracy |
|----------------|-----------------|----------------|-------------------|
| Cubrejunta | Peinazo, Tapa Registro, Bandeja Pasavalores | metros lineales / área planta | ±10% |
| Mesón Simple | Mesón Repisa, Mesón Cajones, Estantería | metros largos | ±15% |
| Sumidero | Canaleta, Sumidero Pequeño | metros lineales / área planta | ±15% |
| Poruña | Balde, Escurridor, Tina Quesera | capacidad (litros) | ±15% |
| Campana Mural | Campana Central, Campana Grande | metros largos (ancho) | ±20% |
| Celosía | Protección Escalera, Escalera Piscina | área panel (m²) | ±20% |
| Basurero Rect | Basurero Modelo Plaza, Basurero Modelo Providencia | volumen (litros) | ±25% — pulido C3 dominant |

---

## 4. How to Update PROCESS_THRESHOLDS.md

After measuring each anchor product, compare measured vs. estimated values:

```
For each process in each anchor product:

  Δ = (T_measured - T_estimated) / T_estimated × 100%

  If |Δ| < 15%:  → estimated threshold is acceptable, no change needed
  If |Δ| 15–30%: → update T_exec in PROCESS_THRESHOLDS.md with measured value
  If |Δ| > 30%:  → re-examine driver classification — product may be misclassified
```

### Update log

| Date | Product | Process | T_estimated (min) | T_measured (min) | Δ% | Action taken |
|------|---------|---------|-------------------|------------------|----|--------------|
| | | | | | | |
| | | | | | | |

---

## 5. Minimum Viable Calibration

If production scheduling makes it hard to measure all 7 products, this is the minimum set that covers the full complexity range:

| Priority | Product | What it validates |
|----------|---------|------------------|
| **Must** | Cubrejunta | C1 baseline — no soldadura, simplest product |
| **Must** | Mesón Simple | C1→C2 plegado + soldadura — anchor for 87 products (highest catalog coverage) |
| **Must** | Basurero Rect | C3 pulido outlier — the model's most critical assumption |
| **Must** | Sumidero | Soldadura C1 baseline |
| **Should** | Celosía | Soldadura C2–C3 upper bound (múltiples uniones flag) |
| **Should** | Poruña | Cilindrado C1 validation |
| Nice to have | Campana Mural | C2 trazado + plegado + soldadura validation |

With just the first 4, you can price ~70% of the catalog with confidence. The full 7 covers ~85%.

---

## 6. PHASE2 Anchors — Pending Measurement

These 3 products cover 83 additional products with no current anchor. They are not blocked but measurement should follow once the 7 main anchors are done.

| Product | Products covered | Profile | Reference size | Key process to validate |
|---------|-----------------|---------|----------------|-------------------------|
| Carro Bandejero | 39 | p-carro | 640×650×2000mm | Cilindrado (tubos) + Plegado C2 |
| Basurero Cilíndrico | 33 | p-basurero-cil | D=400mm × H=800mm × 1mm | Cilindrado C2 + Pulido C3 |
| Lavadero Simple | 11 | p-lavadero | TBD | Plegado C2 + Soldadura C1–C2 (taza) |

These appear as `PHASE2` rows in `PROCESS_MATRIX.csv`. Add full measurement cards here once reference sizes are confirmed with Hernán.

---

> **Next step after measurement:** Update `PROCESS_THRESHOLDS.md` with measured values, then run Layer 4 for each anchor product using measured data vs. estimated data — the cost difference is your model error to reduce over time.
