# 📥 LAYER 1 — Input Validation Agent

> **Role:** Receive, validate, and package all raw product inputs from `MAIN.md`  
> **Called by:** `MAIN.md → Step 2, Call [LAYER 1]`  
> **Calls next:** `LAYER_2_COMPLEXITY.md`

---

## 🎯 Purpose

This layer acts as the **data gateway** for the entire system.  
It ensures all inputs are present, logically valid, and formatted correctly before passing them downstream.

---

## 📦 Input Package — Received from MAIN.md

### A. Product Identification

| Field          | Value Received | Status |
|----------------|----------------|--------|
| Product ID     |                | ✅ / ❌ |
| Product Family |                | ✅ / ❌ |
| Product Type   |                | ✅ / ❌ |
| Description    |                | ✅ / ⚠️ optional |
| Date           |                | ✅ / ⚠️ optional |

---

### B. Geometry Validation

| Field   | Value | Unit | Check                      | Status |
|---------|-------|------|----------------------------|--------|
| Length  |       | mm   | > 0                        |        |
| Depth   |       | mm   | > 0                        |        |
| Height  |       | mm   | Optional, > 0 if entered   |        |

#### Auto-Calculation:

```
Area = Length × Depth (mm²)
```

| Calculated Field | Value | Geometry Tier     |
|------------------|-------|-------------------|
| Area (mm²)       |       | Small / Medium / Large |

**Geometry Scoring:**

| Area Range (mm²)      | Tier   | Score |
|-----------------------|--------|-------|
| < 500,000             | Small  | 1     |
| 500,000 – 1,500,000   | Medium | 2     |
| > 1,500,000           | Large  | 3     |

→ **Geometry Score:** `___`

---

### C. Materials Validation

| # | Material | Qty | Unit | Valid? |
|---|----------|-----|------|--------|
| 1 |          |     |      |        |
| 2 |          |     |      |        |
| 3 |          |     |      |        |

- **Total material lines:** `___`
- **Unique materials:** `___`

> ⚠️ Flag if: material name missing, quantity ≤ 0, unit not specified

---

### D. Component Validation

| # | Component | Qty | Valid? |
|---|-----------|-----|--------|
| 1 |           |     |        |
| 2 |           |     |        |
| 3 |           |     |        |
| 4 |           |     |        |
| 5 |           |     |        |

**Total Component Count:** `___`

**Component Scoring:**

| Count | Tier   | Score |
|-------|--------|-------|
| 1–3   | Low    | 1     |
| 4–7   | Medium | 2     |
| 8+    | High   | 3     |

→ **Component Score:** `___`

---

### E. Feature Validation

| Feature               | Applies? | Score |
|-----------------------|----------|-------|
| Reinforcement         |          | +2    |
| Special finish        |          | +2    |
| Custom cuts           |          | +1    |
| Tight tolerances      |          | +2    |
| Curved geometry       |          | +2    |
| Non-standard material |          | +2    |

**Total Feature Score:** `___`

> ⚠️ Flag if feature marked Y but no supporting detail provided in description

---

### F. Commercial Context Validation

| Field         | Value | Valid Options                         | Status |
|---------------|-------|---------------------------------------|--------|
| Order Volume  |       | Low / Medium / High                   |        |
| Client Type   |       | Standard / Strategic / At-risk        |        |
| Target Margin |       | % between 5%–80%                      |        |

---

## ✅ Validation Rules

| Rule | Check |
|------|-------|
| All required fields filled | Product ID, Family, Type, Length, Depth |
| Area > 0 | Length > 0 AND Depth > 0 |
| At least 1 component entered | Component count ≥ 1 |
| At least 1 material entered | Material count ≥ 1 |
| Features marked as Y or N (not blank) | All 6 feature rows completed |
| Commercial context complete | Volume, Client, Margin all present |

---

## 🚦 Validation Status

| Block | Status | Notes |
|-------|--------|-------|
| A — Identification   | ✅ / ❌ |       |
| B — Geometry         | ✅ / ❌ |       |
| C — Materials        | ✅ / ❌ |       |
| D — Components       | ✅ / ❌ |       |
| E — Features         | ✅ / ❌ |       |
| F — Commercial       | ✅ / ❌ |       |

> ❌ **If any block fails: STOP. Return to MAIN.md and correct inputs before proceeding.**

---

## 📤 Output Package — Passed to LAYER 2

```
{
  product_id:        ___
  product_family:    ___
  product_type:      ___

  area_mm2:          ___
  geometry_score:    ___     ← 1 / 2 / 3

  component_count:   ___
  component_score:   ___     ← 1 / 2 / 3

  feature_score:     ___     ← Sum of applied features

  materials:         [list]
  commercial:        { volume, client_type, target_margin }
}
```

---

> ➡️ **Next Layer:** [`LAYER_2_COMPLEXITY.md`](LAYER_2_COMPLEXITY.md)
