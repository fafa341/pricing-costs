# LAYER 7 — ABC Engine (Cost Driver Assignment)

> **Role:** Assign all costs to 11 activity pools using cost drivers; compute cost per driver  
> **Called by:** `LAYER_6_INDIRECT_COSTS.md`  
> **Calls next:** `LAYER_8_PRICING.md`

---

## Purpose

Activity-Based Costing traces costs to the activities that cause them:

```
Cost → Activity Pools → Products
```

This produces a more accurate picture than absorption costing and reveals which specific activities (and which products) are consuming disproportionate resources.

---

## Input — Received from Layers 4, 5 and 6

| Variable                  | Source  | Value |
|---------------------------|---------|-------|
| Process summary table     | Layer 4 |       |
| Labor hours per process   | Layer 4 |       |
| Machine hours per process | Layer 4 |       |
| Consumables per process   | Layer 4 |       |
| Direct costs              | Layer 5 |       |
| Indirect costs            | Layer 6 |       |
| Total production cost     | Layer 6 |       |

---

## Step 1 — Cost Drivers

| # | Cost Driver          | Unit        | Applied to |
|---|----------------------|-------------|------------|
| 1 | Labor hours          | hrs         | All active processes |
| 2 | Machine hours        | hrs         | Plegado, Cilindrado, Corte Láser, Soldadura |
| 3 | Number of setups     | count       | All active processes |
| 4 | Weld length / joints | m or count  | Soldadura |
| 5 | Surface area         | m²          | Pulido, Pintura |
| 6 | Component count      | count       | Trazado, Plegado, Soldadura |
| 7 | Feature score        | points      | Pulido, Acabado especial |

---

## Step 2 — Activity Pool Assignment

Each of the 11 processes is its own activity pool. Overhead (from Layer 6) is distributed proportionally to labor hours.

| Activity Pool         | Primary Driver    | Costs Assigned |
|-----------------------|-------------------|----------------|
| Pool 1 — Trazado      | Labor hrs         | Operator time |
| Pool 2 — Corte Manual | Labor hrs         | Operator time, discos |
| Pool 3 — Corte Láser  | Machine hrs       | Machine use, programming time |
| Pool 4 — Grabado Láser| Machine hrs       | Machine use, operator time |
| Pool 5 — Plegado      | Labor hrs + setups| Operator time, machine time |
| Pool 6 — Cilindrado   | Labor hrs         | Operator time, machine time |
| Pool 7 — Soldadura    | Labor hrs + m weld| Operator time, argón, barra |
| Pool 8 — Pulido       | Labor hrs + m²    | Operator time, discos, rueda |
| Pool 9 — Pintura      | Labor hrs + m²    | Operator time, pintura |
| Pool 10 — Refrigeración| Days / unit      | Técnico time, components |
| Pool 11 — Control Cal.| Labor hrs         | Operator time, embalaje |
| Pool O — Overhead     | Total labor hrs   | MOH, Operational, Admin |

---

## Step 3 — Product Cost Assignment

For each active process, multiply Pool Rate by this product's driver volume:

```
Activity Cost = Pool Rate × Product's Driver Quantity
```

| Activity Pool     | Driver       | Product Volume | Pool Rate ($/unit) | Assigned Cost ($) |
|-------------------|--------------|----------------|-------------------|-------------------|
| Trazado           | Labor hrs    |                |                   |                   |
| Corte Manual      | Labor hrs    |                |                   |                   |
| Corte Láser       | Machine hrs  |                |                   |                   |
| Grabado Láser     | Machine hrs  |                |                   |                   |
| Plegado           | Labor hrs    |                |                   |                   |
| Cilindrado        | Labor hrs    |                |                   |                   |
| Soldadura         | Labor hrs    |                |                   |                   |
| Pulido            | Labor hrs    |                |                   |                   |
| Pintura           | Labor hrs    |                |                   |                   |
| Refrigeración     | Days         |                |                   |                   |
| Control Calidad   | Labor hrs    |                |                   |                   |
| Overhead (alloc.) | Total hrs    |                |                   |                   |
| **TOTAL**         |              |                |                   |                   |

---

## Step 4 — Total Absorbed Cost

```
Total Absorbed = Σ All Activity-Assigned Costs
```

| Metric                            | Value ($) |
|-----------------------------------|-----------|
| Direct costs (Layer 5)            |           |
| Indirect costs (Layer 6)          |           |
| **Total Production Cost (check)** |           |
| **Total ABC-Absorbed Cost**       |           |
| **Variance** (target: < 2%)       |           |

> ⚠️ If ABC total ≠ production total by > 2%: review pool assignments for double-counting or omission.

---

## Step 5 — Cost per Driver Summary

| Driver             | Total Volume | Total Cost ($) | Cost per Unit |
|--------------------|-------------|----------------|---------------|
| Labor hours (all)  |             |                |               |
| Machine hours      |             |                |               |
| Number of setups   |             |                |               |
| Component count    |             |                |               |
| m² surface (pulido)|             |                |               |
| m weld (soldadura) |             |                |               |

> The `Cost per driver unit` table is the key output for quoting similar products quickly.

---

## Step 6 — Cost by Activity Group

| Activity Group    | Cost ($) | % of Total |
|-------------------|----------|------------|
| Cutting (2+3+4)   |          |            |
| Forming (1+5+6)   |          |            |
| Joining (7)       |          |            |
| Finishing (8+9)   |          |            |
| Systems (10)      |          |            |
| QC (11)           |          |            |
| Materials         |          |            |
| Consumables       |          |            |
| Overhead          |          |            |
| **TOTAL**         |          | 100%       |

---

## Output Package — Passed to Layer 8

```
{
  total_absorbed_cost:   ___

  cost_by_activity: {
    trazado:         ___
    corte_manual:    ___
    corte_laser:     ___
    grabado_laser:   ___
    plegado:         ___
    cilindrado:      ___
    soldadura:       ___
    pulido:          ___
    pintura:         ___
    refrigeracion:   ___
    control_calidad: ___
    overhead:        ___
  }

  cost_per_driver: {
    per_labor_hr:     ___
    per_machine_hr:   ___
    per_setup:        ___
    per_component:    ___
    per_m2_surface:   ___
    per_m_weld:       ___
  }

  cost_breakdown_pct: {
    materials:    ___%
    labor:        ___%
    machine:      ___%
    consumables:  ___%
    overhead:     ___%
  }
}
```

---

## ABC Engine Notes

- Products with high pulido or soldadura time will be visibly expensive in the activity pool — this is the point. The pools expose what drives cost, not just what the total is.
- Compare ABC cost vs. historical quoted price quarterly. Products where `ABC cost > quoted price` are being sold at a loss.
- The `cost_per_driver` table enables fast parametric quoting: "how much does it cost to add 1 meter of soldadura?" — read directly from the pool rate.

---

> Next: [LAYER_8_PRICING.md](LAYER_8_PRICING.md)
