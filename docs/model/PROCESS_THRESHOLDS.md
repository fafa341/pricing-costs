# Process Thresholds — Template Reference

**Fuente:** Entrevista Hernán (Jefe de Producción)  
**Estado:** Draft — pendiente validación con cronómetro en productos 80/20

> **Cómo usar:** Para cada proceso activo, leer el nivel kᵢ del vector en LAYER_2 Part B.
> Buscar la columna C1/C2/C3 en la tabla del proceso.
> Todos los tiempos son **tiempos base de referencia** (anchor product size, factor_escala = 1.0).
> `Costo(i) = (T_setup + T_exec_base × factor_escala) / 60 × $/HH × n_ops + Consumibles(kᵢ)`

---

## 1. Trazado

**Score drivers:** G + X (Geometry + Characteristics)  
**Unidad de referencia:** pieza de mesón 1.5m

| | C1 | C2 | C3 |
|---|---|---|---|
| **Score** | 1–2 | 3–4 | 5–6 |
| **Descripción** | Pieza plana, sin reborde, plano disponible | 2–3 dobleces, reborde simple | 4+ dobleces, reborde complejo, taza doble |
| T_setup (min) | 5–10 | 10–20 | 20–30 |
| T_exec_base (min) | 30 | 60 | 90 |
| n_ops | 1 | 1 | 1 |
| machine_hrs_base | 0 (manual) | 0 (manual) | 0 (manual) |
| **Consumibles** | — | — | — |
| **Ratio vs C1** | 1.00× | ~2.00× | ~3.00× |

**Nota:** Hernán reportó Trazado + Plegado combinados (mesón 1.5m = 2hrs C1, lavadero taza doble = 4hrs C3). Tiempos aislados de Trazado son estimados — separar con cronómetro.  
⚠️ **Gap:** Tiempo de trazado puro no confirmado.

---

## 2. Corte Manual

**Score drivers:** G + D (Geometry + Density)  
**Unidad de referencia:** pieza de mesón 1.5m (~3m lineales de corte)

| | C1 | C2 | C3 |
|---|---|---|---|
| **Score** | 2–3 | 4 | 5–6 |
| **Descripción** | < 3m lineales, ≤ 1.5mm, corte recto | 3–5m o lámina 1.5–2mm | > 5m o > 2mm, cortes curvos |
| T_setup (min) | 5–10 | 10–15 | 15–20 |
| T_exec_base (min) | 30 | 45 | 60 |
| n_ops | 1 | 1–2 | 2 |
| machine_hrs_base | 0 | 0 | 0 |
| **Consumibles** | 1 disco 4.5" | 3 discos 4.5" | 6 discos 4.5" |
| **Ratio vs C1** | 1.00× | ~1.50× | ~2.00× |

**Nota Hernán:** > 3m lineales = 2 personas automático. Para piezas largas: se rola primero (4–5 hrs) y después se corta.  
⚠️ **Gap:** Tiempo exacto por metro lineal no cronometrado — T_exec_base es estimado (~10 min/metro × 3m = 30 min C1).

---

## 3. Corte Láser

**Score drivers:** D + X (Density + Characteristics)  
**Unidad de referencia:** pieza estándar 1mm espesor con DXF disponible

| | C1 | C2 | C3 |
|---|---|---|---|
| **Score** | 1–2 | 3–4 | 5–6 |
| **Descripción** | ≤ 1mm, DXF disponible, geometría simple | 1–3mm o plano debe dibujarse | > 3mm interno; > 8mm → externalizado |
| T_setup (min) | 5–10 | 30+ | 30–60 + coordinación |
| T_exec_base (min) | 10 | 30–40 | externalizado — cotizar |
| n_ops | 1 | 1 | externo |
| machine_hrs_base | 10 | 30–40 | externo |
| **Consumibles** | interno | interno | precio externo $/pieza |
| **Ratio vs C1** | 1.00× | ~3–4× | externo |

**Nota Hernán:** El DXF es el cuello de botella — sin plano disponible, +30 min setup independiente del espesor.  
⚠️ **Gap:** Precio externo $/metro lineal o $/pieza no capturado.

---

## 4. Grabado Láser

**Score drivers:** G (Geometry)  
**Unidad de referencia:** pieza pequeña con área ≤ 10×10cm

| | C1 | C3 (externo) |
|---|---|---|
| **Score** | 1 | 2–3 |
| **Descripción** | Área ≤ 10×10cm, diseño simple (interno) | > 10cm → externalizar |
| T_setup (min) | ~2 | externo |
| T_exec_base (min) | ~5 | externo — cotizar |
| n_ops | 1 (mismo operador láser) | externo |
| machine_hrs_base | 5 | externo |
| **Consumibles** | interno | precio externo |
| **Ratio vs C1** | 1.00× | externo |

**Nota Hernán:** Operador es el mismo que Corte Láser — no suma HH adicional si se hace en la misma sesión.  
No hay nivel C2 en este proceso — el umbral de externalización es binario (≤ 10cm / > 10cm).  
⚠️ **Gap:** Precio externo para grabados grandes no capturado.

---

## 5. Plegado

**Score drivers:** G + D + C (Geometry + Density + Components)  
**Unidad de referencia:** mesón 1.5m con 2 dobleces

| | C1 | C2 | C3 |
|---|---|---|---|
| **Score** | 3–4 | 5–6 | 7–9 |
| **Descripción** | 1–2 dobleces, ≤ 1.5m, ≤ 1.5mm | 3–4 dobleces o pieza > 1.5m | 4+ dobleces, reborde complejo, > 2m o > 2mm |
| T_setup (min) | ~10 | 15–20 | 20–30 |
| T_exec_base (min) | 30 | 50 | 80 |
| n_ops | 1 | 1–2 | 2–4 |
| machine_hrs_base | 30 | 50 | 80 |
| **Consumibles** | — | — | — |
| **Ratio vs C1** | 1.00× | ~1.67× | ~2.67× |

**Nota Hernán:** C1 ejemplo: mesón 1.5m con respaldo, 2 dobleces → 2hrs combinado trazado+plegado. C3 ejemplo: lavadero taza doble → 4hrs, 4 personas. T_exec_base estimado separando ~40% trazado / ~60% plegado del total combinado.  
⚠️ **Gap:** Tiempo de plegado puro (separado de trazado) no aislado — requiere cronómetro.

---

## 6. Cilindrado

**Score drivers:** D + G (Density + Geometry)  
**Unidad de referencia:** basurero chico 400–500mm diámetro, 1.5mm espesor

| | C1 | C2 | C3 |
|---|---|---|---|
| **Score** | 2–3 | 4 | 5–6 |
| **Descripción** | ≤ 1.5mm, ≤ 500mm diámetro | 1.5–2mm, 500–800mm diámetro | ≥ 2mm o > 800mm (estanques) |
| T_setup (min) | ~5 | ~15 | ~30 |
| T_exec_base (min) | 20 | 60 | 180 |
| n_ops | 1 | 2 | 4 |
| machine_hrs_base | 20 | 60 | 180 |
| **Consumibles** | — | — | — |
| **Ratio vs C1** | 1.00× | 3.00× | 9.00× |

**Nota Hernán:** C1: basurero chico 400–500mm, 1.5mm → 1 persona, 20 min. C3: estanque 1.000 litros, 2mm → 4 personas, 3 hrs. Espesor es el **primer discriminador**, luego el tamaño.  
⚠️ **Gap:** Rango C2 (1.5–2mm) no fue ejemplificado — estimado por interpolación.

---

## 7. Soldadura

**Score drivers:** C + X (Components + Characteristics)  
**Unidad de referencia:** lavadero 1.5m

| | C1 | C2 | C3 |
|---|---|---|---|
| **Score** | 1–2 | 3–4 | 5–6 |
| **Descripción** | Sin reborde, estructura oculta, pocas uniones | Con reborde o esquinas simples, 3–5 uniones visibles | Emplantilla completa, TIG visible, esquinas + respaldos + tapitas |
| T_setup (min) | ~5 | ~15 | ~30 |
| T_exec_base (min) | 40 | 60 | 90 |
| n_ops | 1 soldador | 1 soldador | 1 soldador |
| machine_hrs_base | 40 | 60 | 90 |
| **Consumibles** | Argón 6 m³/hr × T_exec_hr · Barra 1m | Argón 8 m³/hr × T_exec_hr · Barra 1m | Argón 10 m³/hr × T_exec_hr · Barra 1m |
| **Ratio vs C1** | 1.00× | 1.50× | 2.25× |

**Nota Hernán:** Siempre 1 soldador — no escala en personas, escala en tiempo. Argón sí varía: 6→8→10 m³/hr. Barra de aporte estable ~1m/pieza.  
**Argón es el único consumible que multiplica por T_exec** (flujo × tiempo = volumen). Todos los demás consumibles son fijos por nivel.

---

## 8. Pulido y Terminación

**Score drivers:** G + X (Geometry + Characteristics)  
**Unidad de referencia:** mesón 1.5m superficie plana

| | C1 | C2 | C3 |
|---|---|---|---|
| **Score** | 1–2 | 3–4 | 5–6 |
| **Descripción** | Superficie plana accesible, sin varillas, cepillado estándar | Con varillas/tubulares/rincones, cepillado fino | Múltiples pasadas (3 pulidas), semi-brillo, geometría compleja |
| T_setup (min) | — | — | — |
| T_exec_base (min) | 60 | 90 | 300 |
| n_ops | 1 | 1–2 | 1–3 |
| machine_hrs_base | 60 | 90 | 300 |
| **Consumibles** | 1 disco fibra · 1 pliego lija · (1/5) rueda traslapada | 1.5 disco fibra · (1/3) rueda traslapada · multi-fily si área > 400mm | 2+ disco fibra · rueda traslapada · multi-fily · escobilla |
| **Ratio vs C1** | 1.00× | 1.50× | 5.00× |

**Nota Hernán:** Basurero = caso extremo C3: 5 horas, 3 pasadas (esmerilado → cepillado → fino). Tubulares/estructura +30 min adicionales. Multi-fily para piezas planas > 400mm con acabado semi-brillo.  
**Consumibles son paquetes fijos por nivel** — no escalan con dimensión por separado; escalan vía factor_escala junto con T_exec.

---

## 9. Pintura

**Score drivers:** X (Characteristics)  
**Unidad de referencia:** superficie plana 1m²

| | C1 | C2 | C3 |
|---|---|---|---|
| **Score** | 0–1 | 2 | 3 |
| **Descripción** | 1 mano, superficie plana accesible | 2 manos o zonas difícil acceso | 3+ manos, geometría compleja, color especial |
| T_setup (min) | — | — | — |
| T_exec_base (min) | — | — | — |
| n_ops | 1 | 1 | 1 |
| machine_hrs_base | — | — | — |
| **Consumibles** | — | — | — |
| **Ratio vs C1** | — | — | — |

⚠️ **Gap completo — Hernán no cubrió Pintura.** No usar este proceso hasta sesión de seguimiento.  
La mayoría de productos Dulox en acero inoxidable no llevan pintura — SKIP por defecto.

---

## 10. Refrigeración

**Score drivers:** C + D (Components + Density)  
**Unidad de referencia:** mueble refrigerado mesón 1.5m (monobloque)

| | C1 | C2 | C3 |
|---|---|---|---|
| **Score** | 2–3 | 4 | 5–6 |
| **Descripción** | Mueble estándar, monobloque, aislación simple | Sección refrigerada + neutra, 2 circuitos | Cámara fría, múltiples circuitos, instalación eléctrica compleja |
| T_setup (min) | — | — | — |
| T_exec_base (días) | ~10 días | — | — |
| n_ops | 1 técnico frigorista | — | — |
| machine_hrs_base | — | — | — |
| **Consumibles** | 2 planchas aislapol 1×2m (alta densidad 30) · motor 1 · condensador 1 · ventilador 1 | — | — |
| **Ratio vs C1** | 1.00× | — | — |

**Nota Hernán:** Proceso siempre sigue el mismo orden: aislación → chassis/motor → ventilador → cañerías → cable eléctrico → tapas. Mueble 1.5m y salsera refrigerada = mismo tiempo (10 días), distinto tamaño.  
⚠️ **Gap:** C2 y C3 tiempos no diferenciados — "siempre es lo mismo" (requiere validar).

---

## 11. Control de Calidad y Embalaje

**Score drivers:** C + X (Components + Characteristics)  
**Unidad de referencia:** mesón simple 1.5m

| | C1 | C2 | C3 |
|---|---|---|---|
| **Score** | 1–2 | 3–4 | 5–6 |
| **Descripción** | Pieza plana sin mecanismos, visual rápido | Con soldaduras visibles o pulidos a revisar | Máquinas, baño maría, cámara — prueba filtración |
| T_setup (min) | — | — | — |
| T_exec_base (min) | 10 | 20 | 30+ |
| n_ops | 1 | 1 | 1 |
| machine_hrs_base | 0 | 0 | 0 |
| **Consumibles** | cartón + plástico burbuja (básico) | cartón + plástico burbuja + suncho | cartón reforzado + suncho + espuma |
| **Ratio vs C1** | 1.00× | 2.00× | 3.00× |

**Nota Hernán:** Se hace por pedido completo, no pieza a pieza. Revisión enfocada en soldaduras, pulidos, filtraciones.  
⚠️ **Gap:** Costo de embalaje por tipo no capturado en $/unidad.

---

## Gaps Críticos — Próxima Sesión

| # | Proceso | Gap | Impacto |
|---|---------|-----|---------|
| 1 | Trazado / Plegado | Tiempos no separados — vienen mezclados | Alto |
| 2 | Corte Manual | Tiempo por metro lineal no cronometrado | Alto |
| 3 | Corte Láser | Precio externo $/pieza no capturado | Alto |
| 4 | Grabado Láser | Precio externo piezas grandes | Medio |
| 5 | Cilindrado | Rango C2 no ejemplificado | Medio |
| 6 | Pintura | Sin datos — proceso no cubierto | Alto si aplica |
| 7 | Refrigeración | C2/C3 sin diferenciar en tiempo | Medio |
| 8 | QC / Embalaje | Costo embalaje por tipo no capturado | Bajo |

---

## Procesos Documentados en process.md — Pendientes de Incorporar

Estos procesos existen en producción pero no tienen template en este archivo todavía.
Se identificaron en el catálogo: **55 productos con `flag_proceso_pendiente`**.

### Proceso 4.2 — Componentes Eléctricos

**Definición (fuente: process.md):** Montaje de termostatos, luz piloto, resistencias, motores de campanas, agitadores e iluminación industrial.

**Operario:** Técnico de frío y eléctrico (mismo que Refrigeración — 1 persona en planta).

**Productos afectados (flag: `comp-electrico`):**
- Campanas murales y centrales (motor)
- Baños maría (resistencias, termostato)
- Salseras calefaccionadas (resistencias)
- Equipos de cocina eléctricos

**Template pendiente:**

| | C1 | C2 | C3 |
|---|---|---|---|
| **Descripción** | 1 componente eléctrico simple | 2–3 componentes, cableado | Sistema complejo, múltiples circuitos |
| T_setup (min) | — | — | — |
| T_exec_base (min) | — | — | — |
| n_ops | 1 técnico eléctrico | 1 técnico eléctrico | 1 técnico eléctrico |
| **Consumibles** | — | — | — |

⚠️ **Gap total — requiere sesión con técnico de frío/eléctrico.**

---

### Proceso 4.3 — Instalación y Conexión de Equipos de Gas

**Definición (fuente: process.md):** Montaje de quemadores, llaves de paso, parrillas, perillas, pilotos, inyectores y manifold.

**Operario:** Técnico gas (1 persona en planta).

**Productos afectados (flag: `instalacion-gas`):**
- Cocinas industriales (gas)
- Anafes
- Freidoras a gas (fabricadas)
- Planchas a gas
- Hornos industriales a gas

**Template pendiente:**

| | C1 | C2 | C3 |
|---|---|---|---|
| **Descripción** | 1–2 quemadores, sin manifold | 3–4 quemadores, manifold simple | 5+ quemadores o doble circuito |
| T_setup (min) | — | — | — |
| T_exec_base (min) | — | — | — |
| n_ops | 1 técnico gas | 1 técnico gas | 1 técnico gas |
| **Consumibles** | quemadores + llaves + piloto | ídem + manifold | ídem + múltiple |

⚠️ **Gap total — requiere sesión con técnico gas.**
