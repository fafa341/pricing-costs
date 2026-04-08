# 🏗️ LAYER 6 — Indirect Cost Allocation Agent

> **Role:** Calculate and allocate overhead, operational, and administrative indirect costs  
> **Called by:** `LAYER_5_DIRECT_COSTS.md`  
> **Calls next:** `LAYER_7_ABC_ENGINE.md`

---

## 🎯 Purpose

Identify and allocate all **indirect costs** that cannot be traced directly to a single product but must be included for accurate total costing:

```
Indirect Cost = Manufacturing Overhead + Operational Overhead + Admin Costs
```

---

## 📥 Input — Received from Layer 5

| Variable                | Value |
|-------------------------|-------|
| `total_direct_cost`     |       |
| `labor_cost`            |       |
| `machine_cost`          |       |
| `labor_hours_total`     |       |
| `machine_hours_total`   |       |

---

## 🏭 BLOCK A — Manufacturing Overhead (MOH)

Costs related to the **factory / production floor** not directly attributed to one product.

### A1. MOH Components

| Overhead Item           | Allocation Method | Monthly Total ($) | Per-Product Rate |
|-------------------------|-------------------|-------------------|------------------|
| Factory rent / lease    | Per machine-hr    |                   |                  |
| Electricity / utilities | Per machine-hr    |                   |                  |
| Equipment depreciation  | Per machine-hr    |                   |                  |
| Maintenance & repairs   | Per machine-hr    |                   |                  |
| Consumables (general)   | Per labor-hr      |                   |                  |
| Safety equipment        | Per labor-hr      |                   |                  |

### A2. MOH Allocation Calculation

**Method 1 — Machine Hour Rate:**
```
MOH Rate (machine) = Total MOH / Total Machine Hours Available
MOH Charge = MOH Rate × Product Machine Hours
```

| Field                         | Value |
|-------------------------------|-------|
| Total monthly MOH ($)         |       |
| Total available machine-hrs   |       |
| MOH rate ($/machine-hr)       |       |
| Product machine hours         |       |
| **MOH Charge — Machine ($)**  |       |

**Method 2 — Labor Hour Rate:**
```
MOH Rate (labor) = Total MOH / Total Labor Hours Available
MOH Charge = MOH Rate × Product Labor Hours
```

| Field                         | Value |
|-------------------------------|-------|
| Total monthly MOH ($)         |       |
| Total available labor-hrs     |       |
| MOH rate ($/labor-hr)         |       |
| Product labor hours           |       |
| **MOH Charge — Labor ($)**    |       |

→ **Total MOH (A):** `___`

> 📌 Use **Machine Hour Rate** as primary driver for capital-intensive shops.  
> Use **Labor Hour Rate** for labor-intensive operations. Mix if both apply.

---

## 🔧 BLOCK B — Operational Overhead

Costs related to running the **business operations** (beyond the factory floor).

### B1. Operational Overhead Items

| Item                    | Allocation Basis | Monthly Total ($) | Rate              |
|-------------------------|------------------|-------------------|--------------------|
| Supervision / QC staff  | % of labor cost  |                   |                    |
| Warehouse / logistics   | % of total cost  |                   |                    |
| Tooling amortization    | Per job          |                   |                    |
| R&D / prototype costs   | % of revenue     |                   |                    |
| IT / software licenses  | Flat per order   |                   |                    |

### B2. Operational Overhead Calculation

```
Operational Overhead = Σ (Rate × Base)
```

| Item                     | Base Value | Rate (%) | Charge ($) |
|--------------------------|------------|----------|------------|
| Supervision              |            |          |            |
| Warehouse                |            |          |            |
| Tooling                  |            |          |            |
| IT / Software            |            |          |            |
| **Total Operational (B)**|            |          |            |

→ **Total Operational Overhead (B):** `___`

---

## 🗂️ BLOCK C — Administrative Costs

General & administrative (G&A) costs allocated to each product.

### C1. Admin Cost Items

| Item                      | Allocation Basis    | Monthly Total ($) | Rate |
|---------------------------|---------------------|-------------------|------|
| Management salaries       | % of total cost     |                   |      |
| Sales & marketing         | % of revenue        |                   |      |
| Finance / accounting      | % of total cost     |                   |      |
| Legal / compliance        | Flat per order      |                   |      |
| Certifications / audits   | Per product family  |                   |      |

### C2. Admin Cost Calculation

```
Admin Rate = Total Monthly Admin / Total Monthly Revenue (or cost base)
Admin Charge = Admin Rate × Product's Direct Cost
```

| Field                        | Value |
|------------------------------|-------|
| Admin rate (%)               |       |
| Direct cost base ($)         |       |
| **Admin Charge (C)**         |       |

→ **Total Admin Cost (C):** `___`

---

## 🧮 BLOCK D — Total Indirect Cost Summary

```
Total Indirect Cost = A (MOH) + B (Operational) + C (Admin)
```

| Component                    | Cost ($) | % of Indirect Total |
|------------------------------|----------|----------------------|
| A — Manufacturing Overhead   |          |                      |
| B — Operational Overhead     |          |                      |
| C — Administrative Costs     |          |                      |
| **Total Indirect Cost**      |          | 100%                 |

---

## 📊 BLOCK E — Combined Cost Summary

| Layer                        | Cost ($) | % of Grand Total |
|------------------------------|----------|------------------|
| Direct Costs (Layer 5)       |          |                  |
| Indirect Costs (Layer 6)     |          |                  |
| **Total Production Cost**    |          | 100%             |

---

## ✅ Overhead Sanity Check

| Metric                         | Target Range | Actual | In Range? |
|--------------------------------|--------------|--------|-----------|
| Indirect / Direct ratio        | 20–40%       |        | ✅ / ⚠️   |
| Admin as % of total            | 5–15%        |        | ✅ / ⚠️   |
| MOH as % of machine cost       | 30–60%       |        | ✅ / ⚠️   |

> ⚠️ Outliers warrant review before passing to ABC Engine

---

## 📤 Output Package — Passed to Layer 7

```
{
  manufacturing_overhead:   ___
  operational_overhead:     ___
  admin_cost:               ___
  total_indirect_cost:      ___

  total_production_cost:    ___   ← Direct + Indirect

  overhead_detail: {
    moh_rate_per_machine_hr:  ___
    moh_rate_per_labor_hr:    ___
    admin_rate_pct:           ___
    operational_rate_pct:     ___
  }
}
```

---

> ➡️ **Next Layer:** [`LAYER_7_ABC_ENGINE.md`](LAYER_7_ABC_ENGINE.md)
