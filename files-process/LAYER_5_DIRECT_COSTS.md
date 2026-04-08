# LAYER 5 — Direct Cost Calculation

> **Role:** Calculate all direct costs: materials, labor, machine use, process consumables  
> **Called by:** `LAYER_4_PROCESSES.md`  
> **Calls next:** `LAYER_6_INDIRECT_COSTS.md`

---

## Purpose

```
Direct Cost = Materials + Direct Labor + Machine Use + Process Consumables
```

All four components are traceable to a specific product. Nothing here is allocated — these are costs that exist only because this product is being made.

---

## Input — Received from Layers 1 and 4

| Variable              | Source   | Value |
|-----------------------|----------|-------|
| Materials list        | Layer 1  |       |
| Process summary table | Layer 4  |       |
| Labor cost per process| Layer 4  |       |
| Consumables per process | Layer 4 |       |

---

## BLOCK A — Material Costs

### A1. Raw Material Inventory

| # | Material | Qty | Unit | Unit Cost ($) | Waste Factor | Adjusted Cost ($) |
|---|----------|-----|------|---------------|--------------|-------------------|
| 1 | Lámina AISI 304 |  |  m² |  | 5–8% | |
| 2 | Tubo / perfil |  | m |  | 3% | |
| 3 | Varilla |  | m |  | 3% | |
| 4 | |  |  |  |  | |
| 5 | |  |  |  |  | |

> Waste Factor accounts for off-cuts and material loss. Typical: 5% plate, 3% tube/rod.

### A2. Material Cost Summary

```
Material Cost = Σ (Qty × Unit Cost × (1 + Waste Factor))
```

| Metric                      | Value ($) |
|-----------------------------|-----------|
| Raw material subtotal       |           |
| Total waste allowance       |           |
| **Total Material Cost (A)** |           |

---

## BLOCK B — Direct Labor Cost

Labor cost is computed per process in Layer 4 and summed here.

### B1. Labor Rate Reference

| Role                  | $/hr | Notes |
|-----------------------|------|-------|
| Operario general      |      | Pending payroll data |
| Soldador TIG          |      | Pending payroll data |
| Técnico frigorista    |      | Pending payroll data |
| Pulidor especialista  |      | Pending payroll data |

> Rates must be loaded from payroll. Use total labor cost per worker (salary + provisions + AFP + previsión) ÷ productive hours per month.

### B2. Labor Cost per Process

| Process | Level | Adj. Time (hr) | Role | $/hr | n_ops | Labor Cost ($) |
|---------|-------|----------------|------|------|-------|----------------|
| Trazado | | | | | | |
| Corte Manual | | | | | | |
| Corte Láser | | | | | | |
| Grabado Láser | | | | | | |
| Plegado | | | | | | |
| Cilindrado | | | | | | |
| Soldadura | | | | | | |
| Pulido | | | | | | |
| Pintura | | | | | | |
| Refrigeración | | | | | | |
| Control Calidad | | | | | | |

### B3. Labor Cost Summary

```
Labor Cost = Σ (Adj_time_hr × $/hr × n_ops)  per process
```

| Metric                   | Value |
|--------------------------|-------|
| Total labor hours        |       |
| Weighted avg $/hr        |       |
| **Total Labor Cost (B)** |       |

---

## BLOCK C — Machine Use Cost

| Machine / Equipment        | Process | Hrs | $/hr | Cost ($) |
|----------------------------|---------|-----|------|----------|
| Plegadora                  | Plegado | | | |
| Roladora (cilindrado)      | Cilindrado | | | |
| Equipo soldadura TIG       | Soldadura | | | |
| Corte láser (interno)      | Corte Láser | | | |
| Esmeriladora / orbitadora  | Pulido | | | |

> Machine $/hr = (depreciation + energy + maintenance) ÷ available monthly hours. Use 0 until machine rates are established.

| Metric                      | Value |
|-----------------------------|-------|
| **Total Machine Cost (C)**  |       |

---

## BLOCK D — Process Consumables

Consumables directly consumed by specific processes (not general shop supplies — those are in Layer 6 overhead).

| Process | Consumable | Qty | Unit Cost | Total ($) |
|---------|------------|-----|-----------|-----------|
| Corte Manual | Discos 4.5" | | | |
| Soldadura | Gas Argón | ___ m³ × ___ hrs | $/m³ | |
| Soldadura | Barra de aporte TIG | ~1m/pieza | $ | |
| Pulido | Disco de fibra | | | |
| Pulido | Disco de lija (pliego) | | | |
| Pulido | Rueda traslapada | | | |
| Pulido | Multi-fily (si aplica) | | | |
| Refrigeración | Aislapol alta densidad | 2 planchas 1×2m | $ | |
| QC / Embalaje | Cartón, plástico burbuja, suncho | | | |

| Metric                          | Value |
|---------------------------------|-------|
| **Total Consumables Cost (D)**  |       |

---

## BLOCK E — Total Direct Cost

```
Total Direct Cost = A (Materials) + B (Labor) + C (Machine) + D (Consumables)
```

| Component               | Cost ($) | % of Direct Total |
|-------------------------|----------|-------------------|
| A — Materials           |          |                   |
| B — Direct Labor        |          |                   |
| C — Machine Use         |          |                   |
| D — Consumables         |          |                   |
| **Total Direct Cost**   |          | 100%              |

---

## Sanity Check — Compare to Template (from Layer 3)

| Metric        | Template Range | Actual % | In Range? |
|---------------|----------------|----------|-----------|
| Materials %   |                |          | ✅ / ⚠️   |
| Labor %       |                |          | ✅ / ⚠️   |
| Machine %     |                |          | ✅ / ⚠️   |

> ⚠️ If any metric deviates > 15pp from template range: flag for review. Likely cause: misclassified complexity level or missing process.

---

## Output Package — Passed to Layer 6

```
{
  material_cost:       ___
  labor_cost:          ___
  machine_cost:        ___
  consumables_cost:    ___
  total_direct_cost:   ___

  breakdown: {
    materials_pct:     ___%
    labor_pct:         ___%
    machine_pct:       ___%
    consumables_pct:   ___%
  }

  labor_hours_total:   ___
  machine_hours_total: ___
}
```

---

> Next: [LAYER_6_INDIRECT_COSTS.md](LAYER_6_INDIRECT_COSTS.md)
