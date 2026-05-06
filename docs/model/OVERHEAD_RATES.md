# OVERHEAD_RATES.md — Tasas Vigentes de Costos Indirectos Dulox

> Archivo vivo. Actualizar con `/accounting setup` (inicial) o `/accounting update [componente]`.  
> **No editar manualmente** — usar el agente de contabilidad para mantener consistencia con Layer 6.  
> Historial de cambios al final del archivo.

---

## Estado actual

| Campo                  | Valor                     |
|------------------------|---------------------------|
| Última actualización   | `2026-04-15`              |
| Modo de captura        | `setup — CERRADO`         |
| Confianza general      | `parcial — 2 pendientes`  |

---

## BLOQUE A — Capacidad de producción (base de cálculo) — CERRADO

| Parámetro                        | Valor          | Fuente                              | Confianza  |
|----------------------------------|----------------|-------------------------------------|------------|
| N° operadores producción         | 27             | 26 generales + 1 especialista láser | medido     |
| HH mensual por operador          | 176,4 hrs/mes  | dato confirmado Layer 5             | medido     |
| Horas/día por operador           | 8,0 hrs/día    | estándar jornada legal              | calculado  |
| Días trabajados/mes              | 22,05 días/mes | 176,4 / 8 hrs                       | calculado  |
| Utilización temporada normal (%) | `pendiente`    | A4 — por confirmar                  | `pendiente`|
| Utilización alta temporada (%)   | `pendiente`    | A4 — por confirmar                  | `pendiente`|
| **Horas disponibles/mes**        | **4.762,8 hrs**| 27 × 176,4                          | medido     |
| **Horas productivas/mes**        | `pendiente`    | requiere utilización %              | `pendiente`|

```
horas_disponibles_mes = 27 × 176,4 = 4.762,8 hrs/mes
horas_productivas_mes = 4.762,8 × utilizacion_pct  [pendiente]
```

---

## BLOQUE B — Personal de producción y overhead — CERRADO

### B.1 — Personal producción (costo directo — Layer 5)

> Estos costos van a Layer 5 (costos directos), no a overhead.  
> Se documentan aquí para referencia del modelo completo.

| Rol                      | N° | Total/mes      | Confianza  |
|--------------------------|----|----------------|------------|
| Operarios generales      | 26 | —              | medido     |
| Especialista láser       |  1 | —              | medido     |
| **Total personal prod.** | 27 | **$22.431.036**| medido     |
| Rate MOD ponderado       |    | $4.710,21/hr   | medido     |

> Verificación de consistencia: $22.431.036 / 4.762,8 hrs = $4.710,21/hr OK

### B.2 — Personal overhead (costo indirecto — Tasa 3)

| Grupo                                                      | N° | CLP/mes         | Confianza  |
|------------------------------------------------------------|----|-----------------|------------|
| Gerencia (G. General + G. Proy/Prod)                      |  2 | $12.777.000     | medido     |
| Admin / RRHH (Jefe RRHH, Analista, Recepcionista, Secret.)|  4 | $6.663.354      | medido     |
| Ventas / Comercial — sueldos                              |  6 | $8.451.062      | medido     |
| **Total overhead RR.HH.**                                 | 12 | **$27.891.416** | medido     |

---

## BLOQUE C — Infraestructura y maquinaria — CERRADO

### C4 — Inventario maquinaria y depreciación

Vida útil SII Chile aplicada:
- Equipos láser / CNC: 10 años
- Guillotinas / Plegadoras / Prensas: 10 años
- Cilindradoras / Escantonadora / Máquina de soldar (medianas): 7 años
- Herramientas menores (taladro, serrucho, pulidoras): 5 años

| ID | Máquina                     | Valor CLP      | Categoría         | Vida útil | Dep/mes    |
|----|-----------------------------|----------------|-------------------|-----------|------------|
| A  | Guillotina Haco             | $5.000.000     | Guillotina        | 10 años   | $41.667    |
| B  | Guillotina LVD 3000         | $8.000.000     | Guillotina        | 10 años   | $66.667    |
| C  | Plegadora LVD 4000          | $12.000.000    | Plegadora         | 10 años   | $100.000   |
| D  | Plegadora Ursviken          | $5.000.000     | Plegadora         | 10 años   | $41.667    |
| E  | Escantonadora               | $3.500.000     | Mediana           | 7 años    | $41.667    |
| F  | Cilindradora eléctrica 1500 | $1.500.000     | Cilindradora      | 7 años    | $17.857    |
| G  | Cilindradora manual 1200    | $800.000       | Cilindradora      | 7 años    | $9.524     |
| H  | Máquina de soldar           | $650.000       | Mediana           | 7 años    | $7.738     |
| I  | Pulidoras de pedestal       | $550.000       | Herramienta menor | 5 años    | $9.167     |
| J  | Guillotina 1,5 mt           | $1.200.000     | Guillotina        | 10 años   | $10.000    |
| K  | Plegadora 2 mts             | $10.000.000    | Plegadora         | 10 años   | $83.333    |
| L  | Máquina Laser Tubos         | $56.000.000    | Láser             | 10 años   | $466.667   |
| M  | Taladro de pedestal         | $150.000       | Herramienta menor | 5 años    | $2.500     |
| N  | Serrucho industrial         | $1.800.000     | Herramienta menor | 5 años    | $30.000    |
| O  | Máquina Laser Planchas      | $47.800.000    | Láser             | 10 años   | $398.333   |
| P  | Plegadora manual 3 mts      | $8.650.000     | Plegadora         | 10 años   | $72.083    |
| Q  | Prensa 25 TON #1            | $3.560.000     | Prensa            | 10 años   | $29.667    |
| R  | Prensa 25 TON #2            | $3.560.000     | Prensa            | 10 años   | $29.667    |
| S  | Plegadora 1000 hidráulica   | $8.562.300     | Plegadora         | 10 años   | $71.353    |
| **TOTAL** |                    | **$179.082.300**|                  |           | **$1.529.557** |

> Concentración del activo: Lásers (L+O) = $103.800.000 = 58% del activo fijo.  
> Depreciación lásers = $865.000/mes = 56,6% del total depreciación.  
> Implicación: la depreciación se debe asignar de forma diferenciada entre procesos láser y no láser al llegar a Layer 7.

### C1+C2+C3 — Componentes Bloque C

| Ítem                                  | CLP/mes        | Método                                            | Confianza  |
|---------------------------------------|----------------|---------------------------------------------------|------------|
| Costo oportunidad inmueble (3.000 m²) | $7.500.000     | estimado — pendiente tasación real 6 propiedades  | estimado   |
| Gastos generales infraestructura      | $3.991.847     | glosa agrupada — desglose pendiente               | estimado   |
| Depreciación maquinaria (19 equipos)  | $1.529.557     | inventario × vida útil SII                        | calculado  |
| **Total Bloque C**                    | **$13.021.404**|                                                   | estimado   |

---

## BLOQUE D — Gestión y ventas — CERRADO

| Ítem                          | CLP/mes        | Tasa     | Confianza  | Nota                                    |
|-------------------------------|----------------|----------|------------|-----------------------------------------|
| Seguros (prima mensual)       | $1.219.341     | Tasa 1   | medido     | Prima anual confirmada                  |
| Comunicaciones (tel./internet)| $433.853       | Tasa 3   | medido     | Dato confirmado                         |
| Gastos de ventas adicionales  | $9.037.692     | Tasa 3   | medido     | Confirmado no duplica sueldos ventas    |
| Contador externo              | $225.000       | Tasa 3   | estimado   | Rango $150k–$300k; usar punto medio     |
| Crédito bancario / leasing    | $0             | —        | medido     | Sin deuda por ahora                     |
| **Total Bloque D**            | **$10.915.886**|          | parcial    |                                         |

> PENDIENTE D: Obtener factura real del contador para reemplazar estimado $225.000.

---

## TASAS VIGENTES — Resultado del setup

### TASA 1 — Capacidad Fija ($/hr disponible)

> Naturaleza: costos que existen aunque la fábrica no produzca nada.  
> Disparador de recálculo: cambio de arriendo, compra/venta de máquina, cambio de seguros.

| Componente                          | CLP/mes        | Confianza  |
|-------------------------------------|----------------|------------|
| Costo oportunidad inmueble          | $7.500.000     | estimado   |
| Gastos generales infraestructura    | $3.991.847     | estimado   |
| Depreciación maquinaria             | $1.529.557     | calculado  |
| Seguros                             | $1.219.341     | medido     |
| **Total Tasa 1/mes**                | **$14.240.745**|            |

| Campo                           | Valor           | Rango PYME     | Estado                                         |
|---------------------------------|-----------------|----------------|------------------------------------------------|
| Horas disponibles/mes           | 4.762,8 hrs     |                |                                                |
| **Tasa 1 ($/hr disponible)**    | **$2.990/hr**   | $500–$2.000/hr | Sobre rango — explicado por inmueble 3.000 m² propio + 2 lásers |
| Depreciación / hr disponible    | $321/hr         | $500–$2.000    | Bajo rango — activos ya amortizados en parte   |
| Infraestructura / hr disponible | $2.669/hr       |                |                                                |

---

### TASA 2 — Operación Variable ($/hr productiva) — PENDIENTE

> Naturaleza: costos que escalan con cuánto produce la fábrica.  
> Disparador de recálculo: trimestral o variación > 15% en utilización.

| Componente                    | CLP/mes    | Confianza   | Acción requerida                              |
|-------------------------------|------------|-------------|-----------------------------------------------|
| Electricidad                  | `—`        | `pendiente` | Traer boleta promedio 3 meses                 |
| Agua / gas industrial         | `—`        | `pendiente` | Traer boleta promedio                         |
| Mantenimiento preventivo      | `—`        | `pendiente` | Contrato o estimado anual / 12                |
| Consumibles generales fábrica | `—`        | `pendiente` | Compras promedio (discos, guantes, lijas)     |
| **Total Tasa 2/mes**          | `—`        |             |                                               |
| Utilización (%)               | `pendiente`|             | Confirmar % temporada normal y alta           |
| Horas productivas/mes         | `—`        |             | 4.762,8 × utilización%                       |
| **Tasa 2 ($/hr productiva)**  | `—`        | $800–$2.500 | Sin datos suficientes                         |

> NOTA: Los $3.991.847 de gastos generales infraestructura (Bloque C) probablemente contienen los componentes de Tasa 2.  
> Cuando se obtenga el desglose, reclasificar la parte variable aquí y reducir Tasa 1 en el mismo monto.

---

### TASA 3 — Personal Indirecto (% sobre costo directo)

> Naturaleza: costo de personas que no operan máquinas ni producen directamente.  
> Disparador de recálculo: cambio de headcount en roles admin / jefatura / ventas.

| Componente                            | CLP/mes         | Confianza  |
|---------------------------------------|-----------------|------------|
| Gerencia (2 personas)                 | $12.777.000     | medido     |
| Admin / RRHH (4 personas)             | $6.663.354      | medido     |
| Ventas / Comercial — sueldos (6 p.)   | $8.451.062      | medido     |
| Comunicaciones                        | $433.853        | medido     |
| Gastos de ventas adicionales          | $9.037.692      | medido     |
| Contador externo                      | $225.000        | estimado   |
| **Total Tasa 3/mes**                  | **$37.587.961** | parcial    |

| Campo                               | Valor       | Rango PYME | Estado                                      |
|-------------------------------------|-------------|------------|---------------------------------------------|
| Costo directo base (MOD)            | $22.431.036 |            |                                             |
| **Tasa 3 (% sobre MOD)**            | **167,6%**  | 8–18%      | Muy sobre rango — estructura admin+ventas robusta vs producción |
| Costo comercial total               | $17.488.754 |            | Sueldos ventas + gastos ventas              |
| Costo comercial / MOD               | 77,9%       |            | ALERTA — ver resumen ejecutivo              |

---

## RESUMEN EJECUTIVO DEL SETUP

### Overhead total mensual capturado

| Componente             | CLP/mes         | % del overhead | Confianza  |
|------------------------|-----------------|----------------|------------|
| Tasa 1 — fija          | $14.240.745     | 27,5%          | estimado   |
| Tasa 2 — variable      | `—`             | `—`            | pendiente  |
| Tasa 3 — personal ind. | $37.587.961     | 72,5%          | parcial    |
| **Total overhead**     | **$51.828.706** | **100%**       | parcial    |

> Tasa 2 no incluida: cuando se levante, el overhead total subirá. Estimado referencial: $1.500–$4.000/hr productiva (a definir con boletas reales).

### Ratios clave

| Métrica                             | Valor Dulox  | Rango PYME  | Estado                                                       |
|-------------------------------------|--------------|-------------|--------------------------------------------------------------|
| Overhead total / MOD                | 230,9%       | 25–45%      | Fuertemente sobre rango — estructura administrativa pesada   |
| Tasa 1 / hr disponible              | $2.990/hr    | $500–$2.000 | Sobre rango — justificado por inmueble propio + 2 lásers     |
| Tasa 3 / MOD                        | 167,6%       | 8–18%       | Muy sobre rango — ver alerta comercial                       |
| Depreciación / hr disponible        | $321/hr      | $500–$2.000 | Bajo rango — activos en proceso de amortización              |
| Costo comercial total / MOD         | 77,9%        | —           | ALERTA — ver nota                                            |

### Ítems pendientes que afectan la precisión del modelo

| Pendiente                                       | Impacto                                 | Urgencia   |
|-------------------------------------------------|-----------------------------------------|------------|
| Utilización % fábrica (temporada normal / alta) | Sin esto, Tasa 2 es incalculable        | Alta       |
| Desglose $3.991.847 gastos generales            | Permite separar Tasa 1 fija vs Tasa 2 variable | Alta  |
| Boletas electricidad promedio 3 meses           | Componente principal de Tasa 2          | Alta       |
| Tasación inmueble (6 propiedades referencia)    | Reemplaza estimado $7.500.000 en Tasa 1 | Media      |
| Factura contador externo real                   | Reemplaza estimado $225.000 en Tasa 3   | Baja       |

### ALERTA — Gasto comercial

El costo comercial total de Dulox es **$17.488.754/mes**, compuesto por:
- Sueldos equipo ventas (6 personas): $8.451.062
- Gastos adicionales de ventas: $9.037.692

Esto equivale al **77,9% del costo de mano de obra de producción** (MOD $22.431.036).

En una PYME metalmecánica estándar, el gasto comercial suele ser 15–25% del MOD. Dulox está 3–5 veces sobre ese rango.

Dos interpretaciones posibles — requiere validación con la gerencia:
1. **El gasto de ventas es el motor del negocio:** Dulox compite por contratos y licitaciones, y la inversión comercial es lo que genera el backlog. En ese caso el ratio es una decisión estratégica, no un problema.
2. **El gasto de ventas no se está recuperando en el precio:** Si el costo comercial no está siendo absorbido correctamente en los precios de venta, Dulox puede estar subcotizando. Este es el riesgo que el modelo ABC debe revelar.

La respuesta a cuál de los dos aplica depende del margen bruto real por producto — que se calcula en Layer 7.

---

## Verificación de consistencia

| Métrica                          | Rango PYME     | Valor Dulox  | Estado                                              |
|----------------------------------|----------------|--------------|-----------------------------------------------------|
| Overhead / Costo directo (MOD)   | 25–45%         | 230,9%       | Sobre rango — ver alerta                            |
| Depreciación / hr disponible     | $500–$2.000    | $321/hr      | Bajo rango — activos en amortización                |
| Tasa 1 / hr disponible           | $500–$2.000/hr | $2.990/hr    | Sobre rango — justificado por inmueble + lásers     |
| Electricidad / hr productiva     | $800–$2.500    | pendiente    | Requiere boletas + utilización                      |
| Costo oportunidad m²             | $5.000–$15.000 | $2.500/m²/mes| Bajo rango — estimado conservador; tasación pendiente|

---

## Historial de cambios

| Fecha      | Componente                    | Valor anterior    | Valor nuevo          | Motivo                                     | Tasa afectada |
|------------|-------------------------------|-------------------|----------------------|--------------------------------------------|---------------|
| 2026-04-15 | Capacidad — operadores        | pendiente         | 26 operadores        | setup inicial                              | Tasa 1 + 2    |
| 2026-04-15 | Capacidad — HH/mes            | pendiente         | 183,18 hrs/op        | setup inicial — Layer 5                    | Tasa 1 + 2    |
| 2026-04-15 | Total sueldos producción      | pendiente         | $21.079.682/mes      | setup inicial — Layer 5                    | referencia    |
| 2026-04-15 | Rate MOD                      | pendiente         | $4.596,13/hr         | setup inicial — Layer 5                    | referencia    |
| 2026-04-15 | Operadores producción         | 26                | 27 (+ esp. láser)    | corrección setup — Bloque A                | Tasa 1+2      |
| 2026-04-15 | MOD total/mes                 | $21.079.682       | $22.431.036          | corrección setup — Bloque A                | referencia    |
| 2026-04-15 | Rate MOD ponderado            | $4.596,13/hr      | $4.710,21/hr         | corrección setup — Bloque A                | referencia    |
| 2026-04-15 | Bloque B overhead RR.HH.      | pendiente         | $27.891.416/mes      | setup B — 12 personas                      | Tasa 3        |
| 2026-04-15 | Costo oportunidad inmueble    | pendiente         | $7.500.000/mes       | setup C1 — estimado, tasación pendiente    | Tasa 1        |
| 2026-04-15 | Gastos gral. infraestructura  | pendiente         | $3.991.847/mes       | setup C2/C3 — glosa agrupada               | Tasa 1+2      |
| 2026-04-15 | Inventario maquinaria         | pendiente         | $179.082.300         | setup C4 — inventario completo             | Tasa 1        |
| 2026-04-15 | Depreciación total/mes        | $1.499.796        | $1.529.557/mes       | setup C4 — reclasificación vida útil SII   | Tasa 1        |
| 2026-04-15 | Seguros                       | pendiente         | $1.219.341/mes       | setup D — dato confirmado                  | Tasa 1        |
| 2026-04-15 | Tasa 1 total/mes              | $13.021.404       | $14.240.745/mes      | agregado seguros D                         | Tasa 1        |
| 2026-04-15 | Tasa 1 rate                   | $2.733/hr         | $2.990/hr disp.      | agregado seguros D                         | Tasa 1        |
| 2026-04-15 | Comunicaciones                | pendiente         | $433.853/mes         | setup D — dato confirmado                  | Tasa 3        |
| 2026-04-15 | Gastos de ventas adicionales  | pendiente         | $9.037.692/mes       | setup D — confirmado no duplicación        | Tasa 3        |
| 2026-04-15 | Contador externo              | pendiente         | $225.000/mes         | setup D — estimado punto medio $150k–$300k | Tasa 3        |
| 2026-04-15 | Tasa 3 total/mes              | $27.891.416       | $37.587.961/mes      | setup D cerrado — comunicaciones + ventas + contador | Tasa 3 |
| 2026-04-15 | Tasa 3 % sobre MOD            | pendiente         | 167,6%               | setup D cerrado — cálculo final            | Tasa 3        |
| 2026-04-15 | Setup Bloque D                | en curso          | CERRADO              | todos los ítems D capturados               | todas         |
