# ABC Costing & Pricing Engine — Dulox

> **Architecture:** Time-Driven Activity-Based Costing (TDABC) with 11-process complexity model  
> **Reference:** `.claude/ARCHITECTURE.md` for mathematical foundations and design rationale

---

## System Flow

```
INPUT: Product ID + subfamilia + dimensions + materials + components + features
  │
  ▼
[LAYER 1] → Validate inputs → geometry_score, component_score, feature_score
  │
  ▼
[LAYER 2] → Complexity Scoring
    Part A: Global tier = Geometry + Component + Feature → C1 / C2 / C3
    Part B: Per-process vector [k₁...k₁₁] = C1/C2/C3 per active process
  │
  ▼
[LAYER 3] → Template Selection
    Global tier → cost structure template + HH multiplier (1.05 / 1.26 / 1.89)
  │
  ▼
[LAYER 4] → 11-Process Mapping
    Subfamilia → active process set (φᵢ ∈ {0,1})
    Per-process level → T_setup, T_exec, n_ops, consumables
    Labor cost = (T_setup + T_exec) × r_HH × m(kᵢ) × n_ops
  │
  ▼
[LAYER 5] → Direct Costs
    Materials + Direct Labor + Machine Use + Process Consumables
  │
  ▼
[LAYER 6] → Indirect Costs
    MOH ($/machine-hr) + Operational (% labor) + Admin (% total)
  │
  ▼
[LAYER 7] → ABC Engine
    Cost → 11 activity pools → cost per driver unit
  │
  ▼
[LAYER 8] → Pricing Engine
    Price = Cost × (1 + margin)
    Adjustments: complexity (+0/+10/+25%) + volume + client type
  │
  ▼
[LAYER 9] → Output Report
    Full audit trail: price, cost breakdown, real margin, flags
```

---

## The Two Outputs of Layer 2

Layer 2 produces two independent outputs that feed different downstream layers:

```
Layer 2 → Global Tier (C1/C2/C3) ──────────────→ Layer 3 (template + pricing adj)
         → Process Vector [k₁...k₁₁] ──────────→ Layer 4 (time lookup per process)
```

A product with global tier C1 can have individual processes at C2 or C3.
Example — Basurero estándar: Global=C1, Pulido=C3 (5 hrs, 3 passes).

---

## Step 1 — User Input Form

Fill all fields. Required fields marked `*`.

### A. Product Identification

| Field            | Input |
|------------------|-------|
| Product ID *     |       |
| Subfamilia *     | e.g., basurero-simple |
| Product Family * |       |
| Description      |       |
| Date             |       |

---

### B. Dimensions

| Field      | Value | Unit |
|------------|-------|------|
| Length *   |       | mm   |
| Depth *    |       | mm   |
| Height     |       | mm   |
| Area (auto)| Length × Depth | mm² |

---

### C. Materials

| # | Material | Qty | Unit |
|---|----------|-----|------|
| 1 | | | |
| 2 | | | |
| 3 | | | |

---

### D. Components / Parts

| # | Component | Qty |
|---|-----------|-----|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

### E. Special Features

| Feature               | Applies? (Y/N) | Score |
|-----------------------|----------------|-------|
| Refuerzo estructural  |                | +2    |
| Acabado especial      |                | +2    |
| Cortes personalizados |                | +1    |
| Tolerancias ajustadas |                | +2    |
| Geometría curva       |                | +2    |
| Material no estándar  |                | +2    |

---

### F. Commercial Context

| Field             | Input |
|-------------------|-------|
| Order Volume      | Low / Medium / High |
| Client Type       | Standard / Strategic / At-risk |
| Target Margin (%) |       |
| Margin Floor (%)  | 15% (default) |

---

## Step 2 — Layer Execution Sequence

Call each layer in order. Do not skip.

```
1. LAYER_1_INPUTS.md      → Validate + compute scores
2. LAYER_2_COMPLEXITY.md  → Global tier + process vector
3. LAYER_3_TEMPLATES.md   → Template + HH multiplier
4. LAYER_4_PROCESSES.md   → Process times + consumables per process
5. LAYER_5_DIRECT_COSTS.md → Total direct cost
6. LAYER_6_INDIRECT_COSTS.md → Overhead allocation
7. LAYER_7_ABC_ENGINE.md  → ABC assignment
8. LAYER_8_PRICING.md     → Final price
9. LAYER_9_OUTPUT.md      → Report
```

---

## Key Design Principles

1. **Two-axis model** — subfamilia (WHICH processes) × per-process complexity (HOW HARD each)
2. **HH multipliers are time scalars, not price markups** — m(C1)=1.05, m(C2)=1.26, m(C3)=1.89
3. **Calibrate on 7 anchor products, extrapolate to all 1,319** — see PRODUCTS_8020_PROCESS_MAP.md
4. **No false precision** — 3 tiers, not continuous. ±15% error is acceptable at this stage.
5. **Full traceability** — every number in Layer 9 traces back to a specific layer input

---

## File Reference

| File | Role |
|------|------|
| [LAYER_1_INPUTS.md](LAYER_1_INPUTS.md) | Input validation |
| [LAYER_2_COMPLEXITY.md](LAYER_2_COMPLEXITY.md) | Global scoring + process vector |
| [LAYER_3_TEMPLATES.md](LAYER_3_TEMPLATES.md) | Templates + HH multipliers |
| [LAYER_4_PROCESSES.md](LAYER_4_PROCESSES.md) | 11-process time and consumables lookup |
| [LAYER_5_DIRECT_COSTS.md](LAYER_5_DIRECT_COSTS.md) | Direct cost calculation |
| [LAYER_6_INDIRECT_COSTS.md](LAYER_6_INDIRECT_COSTS.md) | Overhead allocation |
| [LAYER_7_ABC_ENGINE.md](LAYER_7_ABC_ENGINE.md) | ABC cost driver assignment |
| [LAYER_8_PRICING.md](LAYER_8_PRICING.md) | Pricing engine |
| [LAYER_9_OUTPUT.md](LAYER_9_OUTPUT.md) | Final report |
| [PROCESS_THRESHOLDS.md](PROCESS_THRESHOLDS.md) | C1/C2/C3 thresholds (Hernán interview) |
| [PRODUCTS_8020_PROCESS_MAP.md](PRODUCTS_8020_PROCESS_MAP.md) | Process profiles for 7 anchor products |
| [.claude/ARCHITECTURE.md](../.claude/ARCHITECTURE.md) | Mathematical foundations |

---

> "We are not modeling reality perfectly. We are building a system that reacts correctly to change."
