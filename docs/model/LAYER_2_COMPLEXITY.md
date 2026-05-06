# LAYER 2 — Complexity Scoring Engine

> **Role:** Compute global complexity tier + per-process complexity vector  
> **Called by:** `LAYER_1_INPUTS.md`  
> **Calls next:** `LAYER_3_TEMPLATES.md`

---

## Purpose

Layer 2 produces **two distinct outputs**:

1. **Global Complexity Tier** (C1/C2/C3) — used by Layer 3 (template selection) and Layer 8 (pricing adjustment)
2. **Per-process Complexity Vector** `[k₁...k₁₁]` — used by Layer 4 (process time and consumable lookup)

These are independent. A product can have a global tier of C1 but a C3-level process embedded in it (e.g., Basurero estándar: globally C1, Pulido = C3).

---

## Input — Received from Layer 1

| Variable          | Value |
|-------------------|-------|
| `subfamilia`      | e.g., basurero-simple |
| `geometry_score`  | 1 / 2 / 3 |
| `component_score` | 1 / 2 / 3 |
| `feature_score`   | 0–11 |
| Dimensions        | Length, Depth, Height (mm) |
| Feature flags     | [reinforcement, special_finish, custom_cuts, tight_tol, curved_geom, non_std_mat] |

---

## PART A — Global Complexity Tier

### Step A1 — Geometry Score

```
Area = Length × Depth  [mm²]
```

| Area Range (mm²)    | Score |
|---------------------|-------|
| < 500,000           | 1     |
| 500,000 – 1,500,000 | 2     |
| > 1,500,000         | 3     |

→ **Geometry Score:** `___`

---

### Step A2 — Component Score

| Component Count | Score |
|-----------------|-------|
| 1 – 3           | 1     |
| 4 – 7           | 2     |
| 8+              | 3     |

| Component Type       | Count |
|----------------------|-------|
| Puertas / tapas      |       |
| Cajones              |       |
| Estantes             |       |
| Paneles laterales    |       |
| Patas / ruedas       |       |
| Zócalo               |       |
| Refuerzos estructurales |    |
| Otros                |       |
| **TOTAL**            |       |

→ **Component Score:** `___`

---

### Step A3 — Feature Score

| Feature                          | Applied? | Score | Primary process affected |
|----------------------------------|----------|-------|--------------------------|
| Refuerzo estructural             |          | +2    | Plegado, Soldadura |
| Acabado especial                 |          | +2    | Pulido |
| Cortes personalizados            |          | +1    | Corte Láser, Corte Manual |
| Tolerancias ajustadas            |          | +2    | Soldadura, QC |
| Geometría curva                  |          | +2    | Cilindrado, Plegado |
| Material no estándar             |          | +2    | Corte Manual, Soldadura |
| Perforado / alta densidad corte  |          | +2    | Corte Láser (tostadores, tapas perforadas, celosías, rejillas) |
| Múltiples uniones                |          | +2    | Soldadura (productos con > 8 puntos de unión: celosías, rejillas, divisiones internas) |

→ **Feature Score (sum):** `___`

> **Note — formula scope:** The X driver (Characteristics) is used for **extrapolation** — estimating k-levels for products not previously measured. For **anchor products**, k-values in PROCESS_MATRIX.csv are authoritative (set by measurement, not derived from the formula). The formula gives a proxy; measurement overrides it. This is expected: some processes (e.g., Pulido for basureros, Soldadura for celosías) are driven by product-specific geometry that no single scalar X can fully capture. Those cases are resolved by chronometer calibration of the anchor.

---

### Step A4 — Total Score → Global Tier

```
Total Score = Geometry Score + Component Score + Feature Score
```

| Total Score | Global Tier  |
|-------------|--------------|
| 0 – 3       | C1 (LOW)     |
| 4 – 7       | C2 (MEDIUM)  |
| 8+          | C3 (HIGH)    |

| Driver     | Score |
|------------|-------|
| Geometry   |       |
| Components |       |
| Features   |       |
| **TOTAL**  |       |

→ **Global Tier:** `C1 / C2 / C3`  
→ **Template to apply:** `LAYER_3_TEMPLATES.md`

---

## PART B — Per-Process Complexity Vector

The subfamilia determines which processes are **active** (φᵢ = 1). For each active process, the complexity level kᵢ is derived automatically from the same 4 universal driver scores computed in Part A — no additional inputs required.

---

### Step B1 — Universal Driver Scores (already computed in Part A)

| Driver | Value entered | Score |
|--------|--------------|-------|
| Geometry (Area mm²) | < 500,000 → **1** · 500k–1.5M → **2** · > 1.5M → **3** | `G =` ___ |
| Density (espesor mm) | ≤ 1.5mm → **1** · 1.5–2mm → **2** · > 2mm → **3** | `D =` ___ |
| Components (# piezas) | 1–3 → **1** · 4–7 → **2** · 8+ → **3** | `C =` ___ |
| Characteristics (# flags activos) | 0 → **0** · 1 → **1** · 2 → **2** · 3+ → **3** | `X =` ___ |

---

### Step B2 — Per-Process Score → Level

Each process uses a subset of the 4 drivers. Sum their scores → look up the level in the threshold column.

| # | Process | Drivers used | Score formula | C1 | C2 | C3 | SKIP condition |
|---|---------|-------------|--------------|----|----|-----|----------------|
| 1 | Trazado | G + X | G + X | 1–2 | 3–4 | 5–6 | — |
| 2 | Corte Manual | G + D | G + D | 2–3 | 4 | 5–6 | — |
| 3 | Corte Láser | D + X | D + X | 1–2 | 3–4 | 5–6 | SKIP if subfamilia doesn't use laser |
| 4 | Grabado Láser | G | G | 1 | — | 2–3 (externo) | SKIP if no logo/marca |
| 5 | Plegado | G + D + C | G + D + C | 3–4 | 5–6 | 7–9 | SKIP if cilindrado (forma cilíndrica) |
| 6 | Cilindrado | D + G | D + G | 2–3 | 4 | 5–6 | SKIP if no forma cilíndrica |
| 7 | Soldadura | C + X | C + X | 1–2 | 3–4 | 5–6 | SKIP if subfamilia no requiere uniones |
| 8 | Pulido | G + X | G + X | 1–2 | 3–4 | 5–6 | — |
| 9 | Pintura | X | X | 0–1 | 2 | 3 | SKIP if no pintura (default para acero inox) |
| 10 | Refrigeración | C + D | C + D | 2–3 | 4 | 5–6 | SKIP if no sistema refrigeración |
| 11 | Control QC | C + X | C + X | 1–2 | 3–4 | 5–6 | — (siempre activo) |

> **Rule:** `k(i) = threshold(score(i))` using the ranges above.  
> Trazado and Pulido use the same formula (G + X) — this is intentional: both scale with surface area and finishing requirements.  
> Soldadura and Control QC use the same formula (C + X) — both scale with number of joints/parts and quality standards.

---

### Step B3 — Fill in Process Vector

Apply Step B2 for each active process:

| # | Process | Active? | Score | Level kᵢ |
|---|---------|---------|-------|----------|
| 1 | Trazado | ✅/➖ | G+X = | C1/C2/C3 |
| 2 | Corte Manual | ✅/➖ | G+D = | C1/C2/C3 |
| 3 | Corte Láser | ✅/➖ | D+X = | C1/C2/C3 |
| 4 | Grabado Láser | ✅/➖ | G = | C1/C3 |
| 5 | Plegado | ✅/➖ | G+D+C = | C1/C2/C3 |
| 6 | Cilindrado | ✅/➖ | D+G = | C1/C2/C3 |
| 7 | Soldadura | ✅/➖ | C+X = | C1/C2/C3 |
| 8 | Pulido | ✅/➖ | G+X = | C1/C2/C3 |
| 9 | Pintura | ✅/➖ | X = | C1/C2/C3 |
| 10 | Refrigeración | ✅/➖ | C+D = | C1/C2/C3 |
| 11 | Control QC | ✅ | C+X = | C1/C2/C3 |

---

## Output Package — Passed to Layer 3 and Layer 4

```
PART A → Layer 3 (template + pricing adjustment):
{
  complexity_score:  ___          ← G + C + X total
  complexity_tier:   C1 / C2 / C3
}

PART B → Layer 4 (process time + consumable lookup):
{
  subfamilia:  ___
  G: ___, D: ___, C: ___, X: ___    ← the 4 scores

  process_vector: {
    trazado:         { active: T/F, score: ___, level: C1/C2/C3 }
    corte_manual:    { active: T/F, score: ___, level: C1/C2/C3 }
    corte_laser:     { active: T/F, score: ___, level: C1/C2/C3 }
    grabado_laser:   { active: T/F, score: ___, level: C1/C3 }
    plegado:         { active: T/F, score: ___, level: C1/C2/C3 }
    cilindrado:      { active: T/F, score: ___, level: C1/C2/C3 }
    soldadura:       { active: T/F, score: ___, level: C1/C2/C3 }
    pulido:          { active: T/F, score: ___, level: C1/C2/C3 }
    pintura:         { active: T/F, score: ___, level: C1/C2/C3 }
    refrigeracion:   { active: T/F, score: ___, level: C1/C2/C3 }
    control_calidad: { active: true, score: ___, level: C1/C2/C3 }
  }
}
```

---

## Scoring Notes

- Global tier (Part A) and per-process levels (Part B) are computed from the same 4 scores but with different formulas — they are independent outputs.
- SKIP means the process does not apply to this subfamilia (φᵢ = 0). Do not compute a score for SKIP processes.
- Threshold boundaries are provisional. Calibrate against anchor product chronometer data — if a measured product lands in the wrong level, adjust the boundary for that process only.
- Grabado Láser has no C2 tier: anything above the internal size limit (Geometry ≥ 2) routes to external pricing, not a higher internal level.

---

> Next: [LAYER_3_TEMPLATES.md](LAYER_3_TEMPLATES.md)
