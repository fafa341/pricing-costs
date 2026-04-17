# LAYER 6 — Costos Indirectos (Overhead ABC)

> **Rol:** Calcular y asignar costos indirectos sobre los outputs de Layer 5  
> **Llamado por:** `LAYER_5_DIRECT_COSTS.md`  
> **Llama a:** `LAYER_7_ABC_ENGINE.md`  
> **Tasas vigentes:** `OVERHEAD_RATES.md` (archivo vivo — actualizar con `/accounting`)  
> **Estado setup:** CERRADO parcial — Tasa 1 y Tasa 3 operativas; Tasa 2 pendiente  
> **Última actualización:** 2026-04-15

---

## Principio de diseño

Dulox es una PYME que cambia: operadores entran y salen, arriendos suben, se compran máquinas, cambian proveedores. Un overhead rate único y estático se desfasa rápido.

**Solución: 3 tasas paralelas**, cada una con su naturaleza económica y su disparador de actualización.

```
Overhead_producto =
    Tasa1 × horas_disponibles_asignadas(producto)   [capacidad fija]
  + Tasa2 × horas_productivas(producto)             [operación variable]
  + Tasa3 × costo_directo(producto)                 [personal indirecto]
```

---

## Inputs recibidos desde Layer 5

| Variable               | Descripción                                       |
|------------------------|---------------------------------------------------|
| `costo_directo`        | Costo total de materiales + mano de obra directa  |
| `horas_hombre_total`   | Σ T_exec_actual de todos los procesos activos     |
| `horas_maquina_total`  | Σ machine_hrs_actual de todos los procesos activos|
| `costo_mo_directa`     | Costo de mano de obra directa (operadores)        |

---

## TASA 1 — Overhead de Capacidad Fija

**Naturaleza:** Costos que existen aunque la fábrica no produzca nada.  
**Base de asignación:** Hora disponible (no productiva) — el arriendo corre aunque la máquina esté parada.  
**Cuándo recalcular:** Solo en eventos (cambio de arriendo, compra/venta de máquina, cambio de seguros).

### Componentes de Tasa 1

| Ítem                              | CLP/mes        | Confianza  | Método de estimación                              |
|-----------------------------------|----------------|------------|---------------------------------------------------|
| Costo oportunidad inmueble        | $7.500.000     | estimado   | pendiente tasación real 6 propiedades referencia  |
| Gastos generales infraestructura  | $3.991.847     | estimado   | glosa agrupada — desglose pendiente               |
| Depreciación maquinaria (19 eq.)  | $1.529.557     | calculado  | inventario × vida útil SII                        |
| Seguros                           | $1.219.341     | medido     | prima anual confirmada                            |
| **Total Tasa 1 (CLP/mes)**        | **$14.240.745**|            |                                                   |

### Cálculo Tasa 1

```
horas_disponibles_mes = 27 operadores × 176,4 hrs/op = 4.762,8 hrs/mes

Tasa1 ($/hr_disponible) = $14.240.745 / 4.762,8 = $2.990/hr
```

| Campo                        | Valor           | Rango PYME     | Estado                                       |
|------------------------------|-----------------|----------------|----------------------------------------------|
| Total costos fijos/mes ($)   | $14.240.745     |                |                                              |
| Horas disponibles/mes        | 4.762,8 hrs     |                |                                              |
| **Tasa 1 ($/hr disponible)** | **$2.990/hr**   | $500–$2.000/hr | Sobre rango — inmueble 3.000 m² propio + 2 lásers |

> Nota importante: el rate sobre rango no es anomalía. Refleja una empresa con capital intensivo (inmueble propio + 2 lásers = 58% del activo fijo). En Layer 7, la depreciación de lásers ($865.000/mes = 56,6% del total) se debe asignar de forma diferenciada a procesos láser y no láser, no como rate plano.

---

## TASA 2 — Overhead de Operación Variable — PENDIENTE

**Naturaleza:** Costos que escalan con cuánto produce la fábrica.  
**Base de asignación:** Hora productiva (cuando la máquina está corriendo).  
**Cuándo recalcular:** Trimestralmente o cuando hay variación > 15% en utilización o en costos de servicios.

### Componentes de Tasa 2

| Ítem                          | CLP/mes    | Confianza   | Acción requerida                             |
|-------------------------------|------------|-------------|----------------------------------------------|
| Electricidad                  | `—`        | `pendiente` | Boleta promedio 3 meses                      |
| Agua / gas industrial         | `—`        | `pendiente` | Boleta promedio                              |
| Mantenimiento preventivo      | `—`        | `pendiente` | Contrato o estimado anual / 12               |
| Consumibles generales fábrica | `—`        | `pendiente` | Compras promedio (discos, guantes, lijas)    |
| **Total Tasa 2 (CLP/mes)**    | `—`        |             |                                              |

### Cálculo Tasa 2

```
horas_productivas_mes = 4.762,8 × utilizacion_pct   [utilización pendiente]

Tasa2 ($/hr_productiva) = Total_Tasa2_mes / horas_productivas_mes
```

| Campo                          | Valor       | Rango PYME  | Estado                            |
|--------------------------------|-------------|-------------|-----------------------------------|
| Total costos variables/mes ($) | `—`         |             |                                   |
| Utilización estimada (%)       | `pendiente` |             | Confirmar % temporada normal/alta |
| Horas productivas/mes          | `—`         |             |                                   |
| **Tasa 2 ($/hr productiva)**   | `—`         | $800–$2.500 | Sin datos suficientes             |

> NOTA: Los $3.991.847 de gastos generales infraestructura (Tasa 1) probablemente contienen electricidad y agua. Cuando se obtenga el desglose, reclasificar la parte variable aquí y reducir Tasa 1 en el mismo monto. El overhead total no cambia — cambia cómo se distribuye entre tasas.

---

## TASA 3 — Overhead de Personal Indirecto

**Naturaleza:** Sueldos de personas que no operan máquinas ni producen directamente, más gastos asociados.  
**Base de asignación:** % sobre costo directo del producto.  
**Cuándo recalcular:** Cada vez que hay cambio de headcount en roles admin/jefatura o cambio en gastos comerciales.

### Componentes de Tasa 3

| Grupo                                     | N° | CLP/mes         | Confianza  |
|-------------------------------------------|----|-----------------|------------|
| Gerencia (G. General + G. Proy/Prod)      |  2 | $12.777.000     | medido     |
| Admin / RRHH (4 personas)                 |  4 | $6.663.354      | medido     |
| Ventas / Comercial — sueldos (6 personas) |  6 | $8.451.062      | medido     |
| Comunicaciones (telefonía, internet)      |  — | $433.853        | medido     |
| Gastos de ventas adicionales              |  — | $9.037.692      | medido     |
| Contador externo                          |  — | $225.000        | estimado   |
| **Total Tasa 3 (CLP/mes)**                | 12 | **$37.587.961** | parcial    |

### Cálculo Tasa 3

```
Tasa3 (%) = Total_Tasa3_mes / costo_directo_mensual_total × 100

Tasa3 = $37.587.961 / $22.431.036 × 100 = 167,6%   [base MOD — materiales pendiente]
```

| Campo                              | Valor           | Rango PYME | Estado                                |
|------------------------------------|-----------------|------------|---------------------------------------|
| Costo personal indirecto/mes ($)   | $37.587.961     |            |                                       |
| Base: costo directo MOD/mes ($)    | $22.431.036     |            | Sin materiales (Layer 5 pendiente)    |
| **Tasa 3 (% sobre MOD)**           | **167,6%**      | 8–18%      | Muy sobre rango — ver alerta          |

> ALERTA: Costo comercial total $17.488.754/mes (sueldos ventas + gastos ventas) = 77,9% del MOD. Ver Resumen Ejecutivo.

---

## Aplicación por producto

```python
# Inputs desde Layer 5
horas_disponibles_asignadas = horas_maquina_total   # proxy: máquina ocupada = hora disponible usada
horas_productivas            = horas_maquina_total   # mismo valor si utilización ya en template
costo_directo                = costo_directo         # de Layer 5

# Tasas vigentes (2026-04-15)
tasa1 = 2990      # $/hr disponible    [estimado — tasación inmueble pendiente]
tasa2 = None      # pendiente          [boletas electricidad + utilización]
tasa3 = 1.676     # 167,6% del costo directo [parcial — contador estimado]

# Cálculo
overhead_capacidad  = tasa1 * horas_disponibles_asignadas
overhead_operacion  = tasa2 * horas_productivas     # = 0 hasta que se levante Tasa 2
overhead_personal   = tasa3 * costo_directo

overhead_total = overhead_capacidad + overhead_operacion + overhead_personal
```

---

## Resumen de tasas vigentes

```
TASA 1 — Capacidad fija:    $2.990 / hr disponible    [estimado — 2 pendientes]
TASA 2 — Operación var.:    PENDIENTE                  [boletas + utilización]
TASA 3 — Personal ind.:     167,6% del costo directo  [parcial — contador estimado]
```

---

## Resumen ejecutivo del setup — 2026-04-15

### Overhead total mensual capturado

| Componente             | CLP/mes         | % del overhead capturado | Confianza  |
|------------------------|-----------------|--------------------------|------------|
| Tasa 1 — fija          | $14.240.745     | 27,5%                    | estimado   |
| Tasa 2 — variable      | `—`             | `—`                      | pendiente  |
| Tasa 3 — personal ind. | $37.587.961     | 72,5%                    | parcial    |
| **Total overhead**     | **$51.828.706** | 100%                     | parcial    |

### Ratios clave vs benchmarks PYME metalmecánica Chile

| Métrica                      | Rango PYME     | Valor Dulox | Estado                                              |
|------------------------------|----------------|-------------|-----------------------------------------------------|
| Overhead total / MOD         | 25–45%         | 230,9%      | Muy sobre rango — estructura admin + ventas pesada  |
| Tasa 1 / hr disponible       | $500–$2.000/hr | $2.990/hr   | Sobre rango — justificado por inmueble + lásers     |
| Depreciación / hr disponible | $500–$2.000    | $321/hr     | Bajo rango — activos parcialmente amortizados       |
| Tasa 2 / hr productiva       | $800–$2.500    | pendiente   | Sin datos                                           |
| Costo oportunidad / m²       | $5.000–$15.000 | $2.500/m²   | Bajo rango — estimado conservador                   |
| Tasa 3 / MOD                 | 8–18%          | 167,6%      | Muy sobre rango — ver alerta comercial              |

### Ítems pendientes que afectan la precisión

| Pendiente                               | Impacto en el modelo                          | Urgencia |
|-----------------------------------------|-----------------------------------------------|----------|
| Utilización % fábrica (normal / alta)   | Tasa 2 incalculable sin este dato             | Alta     |
| Desglose $3.991.847 gastos generales    | Separar parte fija (Tasa 1) de variable (Tasa 2) | Alta  |
| Boletas electricidad promedio 3 meses   | Componente principal de Tasa 2                | Alta     |
| Tasación inmueble 6 propiedades         | Reemplaza estimado $7.500.000                 | Media    |
| Factura contador externo real           | Reemplaza estimado $225.000                   | Baja     |

### ALERTA — Estructura de costos comerciales

El costo comercial total de Dulox es **$17.488.754/mes**:
- Sueldos equipo ventas (6 personas): $8.451.062
- Gastos adicionales de ventas: $9.037.692

Equivale al **77,9% del MOD** ($22.431.036). El rango típico PYME es 15–25%.

Dos lecturas posibles — a validar con gerencia en Layer 7:
1. **Inversión estratégica correcta:** Dulox compite en contratos/licitaciones y la fuerza comercial genera el backlog. El ratio es una decisión deliberada.
2. **Riesgo de subcotización:** Si el costo comercial no se absorbe correctamente en los precios, los márgenes reales son menores a lo estimado.

El modelo ABC en Layer 7 resolverá cuál aplica al cruzar overhead con margen por producto.

---

## Check de consistencia

| Métrica                          | Rango PYME     | Valor actual | Estado                                              |
|----------------------------------|----------------|--------------|-----------------------------------------------------|
| Overhead / Costo directo (MOD)   | 25–45%         | 230,9%       | Sobre rango — estructura admin + ventas             |
| Depreciación / hr disponible     | $500–$2.000    | $321/hr      | Bajo rango — activos parcialmente amortizados       |
| Tasa 1 / hr disponible           | $500–$2.000/hr | $2.990/hr    | Sobre rango — inmueble propio + 2 lásers            |
| Electricidad / hr productiva     | $800–$2.500    | pendiente    | Requiere boletas + utilización                      |
| Costo oportunidad / m²/mes       | $5.000–$15.000 | $2.500/m²    | Bajo rango — estimado conservador                   |

> Si overhead/directo > 60%: verificar si la base de costo directo incluye materiales. En Dulox, la base actual es solo MOD ($22.431.036). Al incorporar materiales desde Layer 5, el ratio bajará significativamente.

---

## Disparadores de actualización de tasas

| Evento                                          | Tasa afectada | Urgencia     |
|-------------------------------------------------|---------------|--------------|
| Cambio de arriendo                              | Tasa 1        | Inmediata    |
| Compra / venta de máquina                       | Tasa 1        | Inmediata    |
| Contratación / salida personal producción       | Tasa 2        | Próximo mes  |
| Contratación / salida personal admin/jefatura   | Tasa 3        | Próximo mes  |
| Cambio de tarifa eléctrica                      | Tasa 2        | Trimestral   |
| Cambio de utilización > 15 pp                   | Tasa 2        | Inmediata    |
| Nuevo proceso (tercerización, nuevo equipo)     | Tasa 1 + 2    | Inmediata    |

Para registrar un cambio: `/accounting what-changed`  
Para actualizar un ítem específico: `/accounting update [componente]`  
Para revisar consistencia vs benchmarks: `/accounting review`

---

## Output a Layer 7

```json
{
  "overhead_capacidad_fija":  14240745,
  "overhead_operacion_var":   null,
  "overhead_personal_ind":    37587961,
  "overhead_total_parcial":   51828706,

  "tasas_aplicadas": {
    "tasa1_hr_disponible":    2990,
    "tasa2_hr_productiva":    null,
    "tasa3_pct_directo":      1.676
  },

  "confianza_tasas":    "parcial",
  "pendientes":         ["tasa2_completa", "utilizacion_pct", "desglose_gastos_generales"],
  "fecha_tasas":        "2026-04-15"
}
```

---

> **Siguiente capa:** [`LAYER_7_ABC_ENGINE.md`](LAYER_7_ABC_ENGINE.md)  
> **Tasas vigentes:** [`OVERHEAD_RATES.md`](OVERHEAD_RATES.md)
