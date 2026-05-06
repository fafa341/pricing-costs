# LAYER 3 — Template Selection

> **Role:** Select cost structure template based on global complexity tier  
> **Called by:** `LAYER_2_COMPLEXITY.md`  
> **Calls next:** `LAYER_4_PROCESSES.md`

---

## Purpose

Layer 3 selects the **cost structure template** — expected % distribution of materials, labor, machine, overhead for this complexity tier. Used as a sanity check in Layer 5.

Complexity variation in cost is already encoded in the per-process C1/C2/C3 times in `PROCESS_THRESHOLDS.md`. Layer 3 does not add any multiplier on top of those times — that would double-count complexity.

---

## Input — Received from Layer 2

| Variable           | Value |
|--------------------|-------|
| `complexity_tier`  | C1 / C2 / C3 |
| `complexity_score` | numeric total |

---

## TEMPLATE C1 — LOW Complexity

**Applies when:** `complexity_score = 0–3`

### Expected Cost Structure

| Cost Category  | Expected % of Total Production Cost |
|----------------|-------------------------------------|
| Materials      | 50–60%                              |
| Direct Labor   | 20–25%                              |
| Machine Use    | 10–15%                              |
| Overhead       | 10–15%                              |

### Typical Process Profile

| Characteristic     | C1 Range |
|--------------------|----------|
| Setup time total   | < 30 min |
| Run time total     | < 2 hrs  |
| Operators          | 1–2      |
| Active processes   | 4–7 of 11 |
| Setups per job     | 1        |

### Pricing Adjustment (Layer 8)

```
C1 → +0% on final price
```

---

## TEMPLATE C2 — MEDIUM Complexity

**Applies when:** `complexity_score = 4–7`

### Expected Cost Structure

| Cost Category  | Expected % of Total Production Cost |
|----------------|-------------------------------------|
| Materials      | 40–55%                              |
| Direct Labor   | 25–30%                              |
| Machine Use    | 15–20%                              |
| Overhead       | 15–20%                              |

### Typical Process Profile

| Characteristic     | C2 Range |
|--------------------|----------|
| Setup time total   | 30–60 min |
| Run time total     | 2–4 hrs  |
| Operators          | 2–3      |
| Active processes   | 6–9 of 11 |
| Setups per job     | 2–3      |

### Pricing Adjustment (Layer 8)

```
C2 → +10% on final price
```

---

## TEMPLATE C3 — HIGH Complexity

**Applies when:** `complexity_score = 8+`

### Expected Cost Structure

| Cost Category  | Expected % of Total Production Cost |
|----------------|-------------------------------------|
| Materials      | 35–50%                              |
| Direct Labor   | 28–35%                              |
| Machine Use    | 15–25%                              |
| Overhead       | 15–20%                              |

### Typical Process Profile

| Characteristic     | C3 Range |
|--------------------|----------|
| Setup time total   | 60+ min  |
| Run time total     | 4–10 hrs |
| Operators          | 3–5      |
| Active processes   | 7–11 of 11 |
| Setups per job     | 4+       |

### Pricing Adjustment (Layer 8)

```
C3 → +25% on final price
```

---

## Important: Global tier vs. per-process complexity

The global template (C1/C2/C3) defines:
- Which cost structure to expect (for sanity check in Layer 5)
- Which price adjustment to apply (Layer 8)

The per-process complexity vector (from Layer 2 Part B) defines:
- Which T(i,k) times to look up in PROCESS_THRESHOLDS.md for Layer 4

These are independent. A globally C1 product can have individual processes at C3. Layer 4 uses the per-process times directly — no multiplier is applied on top.

```
Example — Basurero estándar:
  Global tier: C1  → template: 50-60% materials, pricing +0%
  Pulido level: C3  → Layer 4 looks up T_exec(pulido, C3) = 300 min
  Soldadura level: C1 → Layer 4 looks up T_exec(soldadura, C1) = 40 min
```

---

## Template Selection Result

| Field                   | Value |
|-------------------------|-------|
| Complexity Score        |       |
| Global Tier             | C1 / C2 / C3 |
| Pricing Adjustment      | +0% / +10% / +25% |
| Expected Materials %    |       |
| Expected Labor %        |       |

---

## Output Package — Passed to Layer 4

```
{
  template_id:              C1 / C2 / C3
  pricing_adjustment_pct:   0% / 10% / 25%

  expected_cost_structure: {
    materials_pct:   ___–___%
    labor_pct:       ___–___%
    machine_pct:     ___–___%
    overhead_pct:    ___–___%
  }
}
```

---

## Template Calibration Notes

- Templates represent expected ranges, not rigid constraints
- Flag outliers if actual cost split deviates > 15pp from template expectations
- Recalibrate after every 20–30 completed orders per tier
- HH multipliers should be updated as chronometer data from the 7 anchor products becomes available

---

> Next: [LAYER_4_PROCESSES.md](LAYER_4_PROCESSES.md)
