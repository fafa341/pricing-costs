# LAYER 9 — Output Report

> **Role:** Consolidate all layer results into a final pricing and cost report  
> **Called by:** `LAYER_8_PRICING.md`  
> **End of pipeline → Archive or quote**

---

## Purpose

The final, audit-traceable report. Every number here is derived from a specific layer. No estimates, no adjustments outside the model. If a number looks wrong, trace it back through the layer that produced it.

---

## Input — Received from All Layers

| Variable                | Source  |
|-------------------------|---------|
| Product identification  | Layer 1 |
| Global tier + score     | Layer 2 |
| Per-process complexity  | Layer 2 |
| Template used           | Layer 3 |
| Process summary (11)    | Layer 4 |
| Direct cost breakdown   | Layer 5 |
| Indirect cost breakdown | Layer 6 |
| ABC assignment          | Layer 7 |
| Pricing waterfall       | Layer 8 |

---

## SECTION A — Product Summary

| Field           | Value |
|-----------------|-------|
| Product ID      |       |
| Subfamilia      |       |
| Product Family  |       |
| Description     |       |
| Date            |       |
| Quoted by       |       |

---

## SECTION B — Complexity Report

| Field                   | Value |
|-------------------------|-------|
| Geometry Score          |       |
| Component Score         |       |
| Feature Score           |       |
| **Total Score**         |       |
| **Global Tier**         | C1 / C2 / C3 |
| Template Applied        | C1 / C2 / C3 |
| HH Multiplier (global)  | 1.05 / 1.26 / 1.89 |

### Feature Flags

| Feature               | Applied |
|-----------------------|---------|
| Refuerzo estructural  | Y / N   |
| Acabado especial      | Y / N   |
| Cortes personalizados | Y / N   |
| Tolerancias ajustadas | Y / N   |
| Geometría curva       | Y / N   |
| Material no estándar  | Y / N   |

---

## SECTION C — Process Profile

| # | Process | Active | Level | Adj. Time (min) | n_ops | Labor ($) | Consumables ($) |
|---|---------|--------|-------|-----------------|-------|-----------|-----------------|
| 1 | Trazado | ✅/➖ | | | | | |
| 2 | Corte Manual | ✅/➖ | | | | | |
| 3 | Corte Láser | ✅/➖ | | | | | |
| 4 | Grabado Láser | ✅/➖ | | | | | |
| 5 | Plegado | ✅/➖ | | | | | |
| 6 | Cilindrado | ✅/➖ | | | | | |
| 7 | Soldadura | ✅/➖ | | | | | |
| 8 | Pulido | ✅/➖ | | | | | |
| 9 | Pintura | ✅/➖ | | | | | |
| 10 | Refrigeración | ✅/➖ | | | | | |
| 11 | Control Calidad | ✅ | | | | | |
| | **TOTALS** | | | | | | |

---

## SECTION D — Cost Breakdown

### D1. Direct Costs

| Component          | Cost ($) | % of Direct |
|--------------------|----------|-------------|
| Materials          |          |             |
| Direct Labor       |          |             |
| Machine Use        |          |             |
| Consumables        |          |             |
| **Total Direct**   |          | 100%        |

### D2. Indirect Costs

| Component              | Cost ($) | % of Indirect |
|------------------------|----------|---------------|
| Manufacturing Overhead |          |               |
| Operational Overhead   |          |               |
| Admin Costs            |          |               |
| **Total Indirect**     |          | 100%          |

### D3. Grand Total

| Category               | Cost ($) | % of Total |
|------------------------|----------|------------|
| Total Direct           |          |            |
| Total Indirect         |          |            |
| **Total Absorbed Cost**|          | 100%       |

---

## SECTION E — Pricing Summary

### Price Waterfall

| Step                       | Amount ($) | Running Total ($) |
|----------------------------|------------|-------------------|
| Total Absorbed Cost        |            |                   |
| + Base Margin (target)     |            |                   |
| = Base Price               |            |                   |
| + Complexity Adjustment    |            |                   |
| + Volume Adjustment        |            |                   |
| + Client Adjustment        |            |                   |
| = **Final Quoted Price**   |            |                   |

### Margin Summary

| Metric                  | Value |
|-------------------------|-------|
| Target Margin (%)       |       |
| Complexity Adj (%)      |       |
| Volume Adj (%)          |       |
| Client Adj (%)          |       |
| **Adjusted Margin (%)** |       |
| **Real Margin (%)**     |       |
| Floor Applied?          | Yes / No |

---

## SECTION F — Cost Composition

| Driver                  | % of Final Price |
|-------------------------|------------------|
| Materials               |                  |
| Direct Labor            |                  |
| Machine Use             |                  |
| Consumables             |                  |
| Manufacturing Overhead  |                  |
| Operational Overhead    |                  |
| Admin                   |                  |
| **Margin**              |                  |
| **TOTAL**               | 100%             |

---

## SECTION G — Flags and Alerts

| Flag                                        | Status  | Notes |
|---------------------------------------------|---------|-------|
| All inputs validated (Layer 1)              | ✅ / ❌ |       |
| Cost within template range (Layer 3)        | ✅ / ⚠️ |       |
| Per-process levels verified (Layer 2)       | ✅ / ⚠️ |       |
| ABC total matches production total (Layer 7)| ✅ / ⚠️ |       |
| Margin floor applied (Layer 8)              | ✅ / ⚠️ |       |
| Any process with PENDING data (gaps)        | ✅ / ⚠️ |       |

> ⚠️ Flags require review before finalizing quote

---

## SECTION H — Extrapolation Notes

If this product was priced by extrapolation from an anchor product, document here:

| Field                    | Value |
|--------------------------|-------|
| Anchor product used      |       |
| Process profile match    | Exact / Approximate |
| Dimensions scaled        | Yes / No |
| Scale factor applied     |       |
| Deviation from anchor (%)| Acceptable (< 20%) / Review |

---

## SECTION I — Archive Record

| Field         | Value |
|---------------|-------|
| Quote ID      |       |
| Final Price ($)|      |
| Real Margin (%)|      |
| Global Tier   |       |
| Date Quoted   |       |
| Approved by   |       |
| Status        | Draft / Reviewed / Sent / Won / Lost |

---

## FINAL OUTPUT

```
┌──────────────────────────────────────────────────┐
│               FINAL QUOTED PRICE                 │
│                                                  │
│  Product:     ____________________________       │
│  Subfamilia:  ____________________________       │
│  Global Tier: C1 / C2 / C3                       │
│                                                  │
│  Total Cost:  $ ___________________________      │
│  Final Price: $ ___________________________      │
│  Real Margin:   ___________________________%     │
│                                                  │
│  Key cost driver: ________________________       │
│  (process with highest % of labor cost)          │
└──────────────────────────────────────────────────┘
```

---

> "We are not modeling reality perfectly. We are building a system that reacts correctly to change."

---

> Return to: [MAIN.md](MAIN.md) to start a new product quote.
