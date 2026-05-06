# Process Matrix — Mathematical Foundation

> **Companion to:** `PROCESS_MATRIX.csv`  
> **Calibration source:** `PROCESS_THRESHOLDS.md`  
> **Method:** Analogical Parametric Cost Estimation (NASA/DoD CER)

---

## 1. How to Read the Matrix

Each row is a product. Each process column holds one of four values:

| Value | Meaning |
|-------|---------|
| `C1` | Process active, LOW complexity → use T(i, C1) and Consumables(i, C1) from PROCESS_THRESHOLDS.md |
| `C2` | Process active, MEDIUM complexity → use T(i, C2) and Consumables(i, C2) |
| `C3` | Process active, HIGH complexity → use T(i, C3) and Consumables(i, C3) |
| `SKIP` | Process does not apply to this product |

**ANCHOR rows:** 7 measured reference products. `factor_escala = 1.00`.  
**EXTRAPOL rows:** inherit the process profile of their anchor and scale by dimension via `factor_escala`.

The k-values in EXTRAPOL rows are derived from the same 4 universal driver scores as the anchor, computed fresh for the new product's dimensions. They do not need to match the anchor's levels exactly.

---

## 2. The Core Cost Formula

For any active process `i` in product `p`:

```
T_exec_actual(i)     = T_exec_base(i, kᵢ) × factor_escala
machine_hrs_actual(i) = machine_hrs_base(i, kᵢ) × factor_escala

Labor_cost(i) = (T_setup(i, kᵢ) + T_exec_actual(i)) / 60
                × $/HH(i)
                × n_ops(i, kᵢ)

Consumables_cost(i) = flat_package(i, kᵢ) × factor_escala
    [exception: argón = flow_rate(kᵢ) × T_exec_actual(i)/60]

Cost(i) = Labor_cost(i) + Consumables_cost(i)
```

Total product cost:

```
C(p) = C_mat(p)
      + Σᵢ [ φᵢ · Cost(i) ]
      + C_overhead(p)
```

Where `φᵢ = 1` if process column is C1/C2/C3 and `φᵢ = 0` if SKIP.

**No multiplier is applied** — the C1/C2/C3 times in PROCESS_THRESHOLDS.md already encode the complexity variation. Empirical ratios per process (source: Hernán) are documented in PROCESS_THRESHOLDS.md.

---

## 3. The factor_escala — Definition and Flow

`factor_escala` is the single scaling parameter that connects an anchor product's measured costs to an extrapolated product's estimated costs.

```
factor_escala = dim_product / dim_anchor_reference
```

Where `dim` is the **driver_escala** column in PROCESS_MATRIX.csv (metros lineales, area_planta_mm2, capacidad_litros, etc.).

### What scales with factor_escala

| Component | Scales? | Rule |
|-----------|---------|------|
| T_exec | Yes | T_exec_actual = T_exec_base × factor_escala |
| machine_hrs | Yes | machine_hrs_actual = machine_hrs_base × factor_escala |
| Flat consumables | Yes | package × factor_escala |
| Argón | Yes (via T_exec) | flow_rate × T_exec_actual / 60 |
| T_setup | **No** | Fixed per job — does not scale with product size |
| Material cost | Yes | Scales with area × espesor × density |

### Setup time and batch size

Because setup does not scale, larger batches reduce per-unit cost:

```
Cost_per_unit(i) = [ T_setup(i, kᵢ)/batch_size + T_exec_actual(i) ] / 60
                   × $/HH × n_ops
                   + Consumables_cost(i)
```

Larger batch → T_setup is amortized → lower cost per unit.

---

## 4. How 4 Universal Drivers Produce Process Levels

The `factor_escala` adjusts magnitudes. The process level kᵢ is determined upstream in LAYER_2 Part B from the 4 universal driver scores:

```
User enters: L, W, H, espesor, # components, feature flags
                    ↓
Compute scores:
  G = Geometry score (1–3) from Area = L × W
  D = Density score (1–3) from espesor
  C = Component score (1–3) from # parts
  X = Characteristics score (0–3) from # flags
                    ↓
Per process i: sum selected drivers → score(i)
  threshold(score(i)) → kᵢ ∈ {C1, C2, C3}
                    ↓
PROCESS_THRESHOLDS.md lookup:
  template(i, kᵢ) → T_setup, T_exec_base, n_ops, machine_hrs_base, consumables
                    ↓
Apply factor_escala → T_exec_actual, machine_hrs_actual, consumables_actual
                    ↓
Cost(i) = Labor + Consumables
                    ↓
ABC outputs: total_HH, total_machine_hrs → LAYER_6 overhead allocation
```

---

## 5. The factor_escala Column — Filling in `?` Values

`factor_escala = ?` means the anchor has not been measured yet, or the extrapolated product's reference dimension has not been confirmed.

**To fill in an EXTRAPOL row:**

1. Confirm the anchor product has been measured (CALIBRATION_MEASUREMENT.md)
2. Record the anchor's reference dimension (e.g., Cubrejunta = 2.4m)
3. Enter the standard dimension for the extrapolated product (e.g., Peinazo = 1.8m)
4. Compute: `factor_escala = 1.8 / 2.4 = 0.75`
5. Update the `factor_escala` cell in PROCESS_MATRIX.csv

Every `?` in the matrix is a pricing uncertainty. Resolve them in order of sales volume.

---

## 6. Extrapolation Validity Rules

Extrapolation is valid when:

| Condition | Valid? |
|-----------|--------|
| Same SKIP/active pattern as anchor | Yes |
| Process levels within ±1 tier of anchor | Yes |
| Primary driver scales linearly (α = 1.0) | Yes |
| New process appears that was SKIP in anchor | **No** — treat as new anchor |
| Process jumps 2 tiers vs. anchor | **No** — measure directly |
| Driver is non-linear (e.g., refrigeration volume) | **No** — use own measurement |

### Error tolerance

After applying factor_escala, compare against any available actual data:

```
Error% = |Cost_extrapolated - Cost_actual| / Cost_actual × 100
```

| Error | Action |
|-------|--------|
| < 15% | Accept |
| 15–30% | Accept with flag — review driver_escala choice |
| > 30% | Reject — measure the product directly |

---

> **Key invariant:** The CSV matrix is the lookup table. The 4 driver scores determine levels. factor_escala scales magnitudes. These three things together produce cost for any product in the catalog without additional per-product inputs.
