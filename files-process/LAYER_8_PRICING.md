# 💲 LAYER 8 — Pricing Engine

> **Role:** Apply margin logic and dynamic pricing adjustments to compute the final price  
> **Called by:** `LAYER_7_ABC_ENGINE.md`  
> **Calls next:** `LAYER_9_OUTPUT.md`

---

## 🎯 Purpose

Transform the **total absorbed cost** into a **final quoted price** by:
1. Applying a base margin
2. Adjusting for complexity, volume, and client type
3. Enforcing margin floor rules

---

## 📥 Input — Received from Layers 2, 7 & MAIN

| Variable               | Source   | Value |
|------------------------|----------|-------|
| `total_absorbed_cost`  | Layer 7  |       |
| `complexity_tier`      | Layer 2  |       |
| `target_margin_pct`    | MAIN     |       |
| `order_volume`         | MAIN     |       |
| `client_type`          | MAIN     |       |

---

## ⚙️ STEP 1 — Base Price (No Adjustments)

```
Base Price = Total Absorbed Cost × (1 + Target Margin)
```

| Field                     | Value |
|---------------------------|-------|
| Total Absorbed Cost ($)   |       |
| Target Margin (%)         |       |
| **Base Price ($)**        |       |

---

## ⚙️ STEP 2 — Complexity Adjustment

| Complexity Tier | Adjustment |
|-----------------|------------|
| 🟢 LOW (C1)    | +0%        |
| 🟡 MEDIUM (C2) | +10%       |
| 🔴 HIGH (C3)   | +25%       |

| Field                         | Value |
|-------------------------------|-------|
| Assigned Complexity Tier      |       |
| Complexity Adjustment (%)     |       |
| Adjustment Amount ($)         |       |

---

## ⚙️ STEP 3 — Volume Adjustment

| Volume Level | Adjustment | Rationale                          |
|--------------|------------|------------------------------------|
| High         | −5%        | Economies of scale, repeat setups  |
| Medium       | 0%         | Baseline                           |
| Low          | +8%        | Small batch premium                |

| Field                       | Value |
|-----------------------------|-------|
| Order Volume Level          |       |
| Volume Adjustment (%)       |       |
| Adjustment Amount ($)       |       |

> 📌 Customize volume thresholds (e.g. High = > 10 units, Low = 1–2 units) based on your production reality.

---

## ⚙️ STEP 4 — Client Adjustment

| Client Type   | Adjustment | Rationale                                      |
|---------------|------------|------------------------------------------------|
| Strategic     | −5%        | Long-term relationship, preferred pricing      |
| Standard      | 0%         | Baseline                                       |
| At-risk       | +10%       | Higher administrative load, risk premium       |

| Field                         | Value |
|-------------------------------|-------|
| Client Type                   |       |
| Client Adjustment (%)         |       |
| Adjustment Amount ($)         |       |

---

## ⚙️ STEP 5 — Adjusted Margin Calculation

```
Total Adjustment (%) = Complexity Adj + Volume Adj + Client Adj

Adjusted Margin (%) = Target Margin (%) + Total Adjustment (%)
```

| Component                  | Adjustment (%) |
|----------------------------|----------------|
| Target Margin              |                |
| + Complexity Adjustment    |                |
| + Volume Adjustment        |                |
| + Client Adjustment        |                |
| **= Adjusted Margin (%)**  |                |

---

## ⚙️ STEP 6 — Margin Floor Check

Define the **minimum acceptable margin** to prevent pricing below cost:

| Rule                         | Value |
|------------------------------|-------|
| Absolute margin floor (%)    | 15% (adjust to your business) |
| Adjusted Margin (%)          |       |
| Floor violated?              | Yes / No |

> ❌ If adjusted margin falls below floor: **override to floor value** and flag for commercial review.

| Field                           | Value |
|---------------------------------|-------|
| Floor Override Applied?         | Yes / No |
| Final Margin Used (%)           |       |

---

## 🧮 STEP 7 — Final Price Calculation

```
Final Price = Total Absorbed Cost × (1 + Final Adjusted Margin)
```

| Field                      | Value ($) |
|----------------------------|-----------|
| Total Absorbed Cost        |           |
| Final Adjusted Margin (%)  |           |
| **Final Quoted Price ($)** |           |

---

## 📊 STEP 8 — Price Waterfall Summary

```
Base Cost
  → + Margin (target)
  = Base Price

Base Price
  → + Complexity Adjustment
  → + Volume Adjustment
  → + Client Adjustment
  = Final Price
```

| Step                         | Amount ($) | Running Total ($) |
|------------------------------|------------|-------------------|
| Total Absorbed Cost          |            |                   |
| + Base Margin                |            |                   |
| = Base Price                 |            |                   |
| + Complexity Adjustment      |            |                   |
| + Volume Adjustment          |            |                   |
| + Client Adjustment          |            |                   |
| = **Final Quoted Price**     |            |                   |

---

## 📊 STEP 9 — Margin Verification

```
Real Margin = (Final Price − Total Absorbed Cost) / Final Price × 100
```

| Metric                              | Value |
|-------------------------------------|-------|
| Final Price ($)                     |       |
| Total Absorbed Cost ($)             |       |
| Gross Profit ($)                    |       |
| **Real Margin (%)**                 |       |
| Target Margin (%)                   |       |
| Margin vs Target                    | ± %   |

---

## 📤 Output Package — Passed to Layer 9

```
{
  total_absorbed_cost:     ___
  base_price:              ___
  final_price:             ___

  margin: {
    target_pct:            ___
    complexity_adj_pct:    ___
    volume_adj_pct:        ___
    client_adj_pct:        ___
    adjusted_margin_pct:   ___
    real_margin_pct:       ___
    floor_applied:         true / false
  }

  price_waterfall: [
    { step: "Base Cost",            value: ___ },
    { step: "Base Price",           value: ___ },
    { step: "Complexity Adj",       value: ___ },
    { step: "Volume Adj",           value: ___ },
    { step: "Client Adj",           value: ___ },
    { step: "Final Price",          value: ___ }
  ]
}
```

---

## 📌 Pricing Notes

- **Never expose** the cost breakdown to the client — share price only
- Discount requests from clients should be evaluated against **real margin**, not base price
- If `floor_applied = true`, escalate to commercial director before quoting
- Revisit complexity adjustment percentages every quarter with real margin data

---

> ➡️ **Next Layer:** [`LAYER_9_OUTPUT.md`](LAYER_9_OUTPUT.md)
