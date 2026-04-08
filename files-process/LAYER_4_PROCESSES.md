# LAYER 4 — Process Mapping

> **Role:** For each active process, look up template times and consumables, apply factor_escala, compute labor and consumable costs  
> **Called by:** `LAYER_3_TEMPLATES.md`  
> **Calls next:** `LAYER_5_DIRECT_COSTS.md`

---

## Purpose

Layer 4 converts the process complexity vector from Layer 2 into actual cost numbers.

For each active process i (φᵢ = 1):
1. Read level kᵢ from the Layer 2 output vector
2. Look up template(i, kᵢ) from `PROCESS_THRESHOLDS.md` → T_setup, T_exec_base, n_ops, machine_hrs_base, consumables
3. Apply factor_escala to execution time and consumables
4. Compute labor cost and consumable cost

---

## Input — Received from Layers 2 and 3

| Variable | Source | Value |
|----------|--------|-------|
| `process_vector` | Layer 2 | `[{active, score, level}]` for all 11 processes |
| `subfamilia` | Layer 2 | determines which processes are active |
| `factor_escala` | `PROCESS_MATRIX.csv` | `dim_product / dim_anchor` |
| `$/HH` per process | Payroll | $/hr per operator role |

---

## Cost Formula

```
For each active process i:

  T_exec_actual(i)    = T_exec_base(i, kᵢ) × factor_escala
  machine_hrs_actual(i) = machine_hrs_base(i, kᵢ) × factor_escala

  Labor_cost(i) = (T_setup(i, kᵢ) + T_exec_actual(i)) / 60
                  × $/HH(i)
                  × n_ops(i, kᵢ)

  Consumables_cost(i) = lookup flat package(i, kᵢ) × factor_escala
                        [exception: argón = flow_rate(kᵢ) × T_exec_actual(i)/60]
```

Setup time does **not** scale with factor_escala — it is fixed per job regardless of product size.

---

## Process Execution Table

Fill one row per active process. Skip inactive processes.

| # | Process | Level kᵢ | T_setup (min) | T_exec_base (min) | factor_escala | T_exec_actual (min) | n_ops | $/HH | Labor cost ($) | Consumables ($) | Total ($) |
|---|---------|----------|--------------|------------------|---------------|--------------------|----|------|---------------|-----------------|-----------|
| 1 | Trazado | | | | | | | | | — | |
| 2 | Corte Manual | | | | | | | | | discos | |
| 3 | Corte Láser | | | | | | | | | — / externo | |
| 4 | Grabado Láser | | | | | | | | | — / externo | |
| 5 | Plegado | | | | | | | | | — | |
| 6 | Cilindrado | | | | | | | | | — | |
| 7 | Soldadura | | | | | | | | | argón + barra | |
| 8 | Pulido | | | | | | | | | discos + rueda | |
| 9 | Pintura | | | | | | | | | pintura | |
| 10 | Refrigeración | | | | | | | | | componentes | |
| 11 | Control QC | | | | | | | | | embalaje | |
| | **TOTALS** | | | | | | | | | | |

---

## Totals for ABC Overhead Allocation

These totals feed directly into Layer 6 overhead allocation:

| Metric | Value |
|--------|-------|
| Total HH (labor hours) | Σ T_exec_actual / 60 across all active processes |
| Total machine hours | Σ machine_hrs_actual / 60 across all active processes |
| Total labor cost | Σ Labor_cost(i) |
| Total consumables cost | Σ Consumables_cost(i) |

> Layer 6 uses total HH and machine hours as the allocation base for MOH and operational overhead.

---

## factor_escala Reference

The factor_escala for each product is in `PROCESS_MATRIX.csv` (column `factor_escala`).

| Anchor | Reference dimension | factor_escala for anchor |
|--------|-------------------|--------------------------|
| Cubrejunta | 2.4m length | 1.00 |
| Moldura | standard length | 1.00 |
| Sumidero | 400×400mm planta | 1.00 |
| Poruña | 1kg model | 1.00 |
| Campana | standard width | 1.00 |
| Celosía | standard panel | 1.00 |
| Basurero std | standard model | 1.00 |

For extrapolated products:
```
factor_escala = dim_product / dim_anchor_reference
```

If `factor_escala` is `?` in the CSV, it must be measured or estimated before running Layer 4.

---

## Process Notes

- **Corte Láser C3** and **Grabado Láser C3**: these are externalized. Replace `Labor_cost` with the external quoted price. Do not apply the HH formula.
- **Refrigeración**: T_exec_base is in days, not minutes. Convert: 10 days × 8 hrs/day × 60 = 4,800 min reference. Apply factor_escala for different sizes.
- **Pintura**: SKIP until gap is filled (see PROCESS_THRESHOLDS.md section 9).
- For processes where `machine_hrs_actual = T_exec_actual` (machine runs with operator): confirm with Hernán which processes are truly machine-paced vs. operator-paced.

---

## Output Package — Passed to Layer 5

```
{
  active_processes: [
    {
      name:              trazado / corte_manual / ... / control_calidad
      level:             C1 / C2 / C3
      score:             ___
      factor_escala:     ___
      t_setup_min:       ___
      t_exec_actual_min: ___
      machine_hrs_actual: ___
      n_ops:             ___
      labor_cost:        ___
      consumables_cost:  ___
      process_total:     ___
    },
    ...
  ],

  totals: {
    labor_hours:        ___   ← feeds Layer 6 MOH allocation
    machine_hours:      ___   ← feeds Layer 6 MOH allocation
    total_labor_cost:   ___
    total_consumables:  ___
  }
}
```

---

> Next: [LAYER_5_DIRECT_COSTS.md](LAYER_5_DIRECT_COSTS.md)
