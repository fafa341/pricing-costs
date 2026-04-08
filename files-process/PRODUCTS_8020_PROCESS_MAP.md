# Mapa de Proceso — Productos 80/20
**Propósito:** Calibrar el modelo de costeo con los productos más frecuentes, luego extrapolar al resto del catálogo.

> **Cómo leer este documento:**
> - Cada fila es un proceso. ✅ = aplica | ➖ = no aplica | ❓ = confirmar con producción
> - El nivel C1/C2/C3 en cada proceso es la sub-complejidad de *ese proceso* para *ese producto*
> - El nivel global (complejidad del producto) se mantiene del catálogo, pero el HH se aplica proceso a proceso

---

## 1. Poruña

**Complejidad global:** C1
**Descripción:** Cucharón/recipiente de acero inoxidable. Forma simple, pocas soldaduras, acabado cepillado.

| Proceso | Aplica | Nivel | Driver que determina el nivel |
|---------|--------|-------|-------------------------------|
| Trazado | ✅ | C1 | 1–2 líneas, pieza pequeña, sin reborde |
| Corte Manual | ✅ | C1 | < 1m lineal, 1mm espesor |
| Corte Láser | ➖ | — | Pieza pequeña, no justifica láser |
| Grabado Láser | ❓ | C1 | Solo si lleva logo (< 10cm) |
| Plegado | ✅ | C1 | 1–2 dobleces, pieza ≤ 300mm |
| Cilindrado | ✅ | C1 | Cuerpo cilíndrico pequeño, ≤ 1.5mm |
| Soldadura | ✅ | C1 | 1–2 uniones, sin emplantilla, acabado no visible |
| Pulido y Terminación | ✅ | C1 | Superficie pequeña, cepillado simple |
| Pintura | ➖ | — | Acero inoxidable, sin pintura |
| Refrigeración | ➖ | — | No aplica |
| Control de Calidad | ✅ | C1 | Pieza simple, ~10 min |

**Costo HH estimado:** Todos los procesos × multiplicador C1 (1.05)
**Extrapolación:** Salseras, baldes pequeños, tazas-accesorio

---

## 2. Campana Industrial

**Complejidad global:** C1–C2 (según si lleva motor)
**Descripción:** Campana mural o central de extracción. Cuerpo plegado, filtros, algunos accesorios.

| Proceso | Aplica | Nivel | Driver que determina el nivel |
|---------|--------|-------|-------------------------------|
| Trazado | ✅ | C1–C2 | 2–3 planos (cuerpo + alas), reborde simple |
| Corte Manual | ✅ | C1 | < 3m lineales por sección |
| Corte Láser | ✅ | C1 | Rejillas y filtros, ≤ 1mm |
| Grabado Láser | ➖ | — | No típico |
| Plegado | ✅ | C2 | 4–6 dobleces, pieza > 1m, ángulos de esquina |
| Cilindrado | ❓ | C1 | Solo si tiene ducto circular |
| Soldadura | ✅ | C2 | Esquinas visibles, uniones múltiples, acabado fino |
| Pulido y Terminación | ✅ | C2 | Zonas de difícil acceso (rincones), cepillado fino |
| Pintura | ➖ | — | Sin pintura normalmente |
| Refrigeración | ➖ | — | No aplica |
| Control de Calidad | ✅ | C1 | Visual de soldaduras, ~15 min |

**Costo HH estimado:** Mix C1/C2 según proceso
**Extrapolación:** Accesorio-campana, ductos de ventilación

---

## 3. Celosía

**Complejidad global:** C1
**Descripción:** Rejilla decorativa o funcional. Estructura de varillas soldadas en patrón.

| Proceso | Aplica | Nivel | Driver que determina el nivel |
|---------|--------|-------|-------------------------------|
| Trazado | ✅ | C1 | Patrón repetitivo, plantilla reutilizable |
| Corte Manual | ✅ | C1–C2 | Múltiples varillas cortas — número alto, no longitud |
| Corte Láser | ❓ | C1 | Si se cortan en lámina, posible nesting eficiente |
| Grabado Láser | ➖ | — | No aplica |
| Plegado | ➖ | — | No aplica (varillas rectas) |
| Cilindrado | ➖ | — | No aplica |
| Soldadura | ✅ | C2–C3 | Múltiples puntos de soldadura — es el proceso dominante |
| Pulido y Terminación | ✅ | C2 | Cada unión soldada requiere limpieza |
| Pintura | ❓ | — | Confirmar si aplica |
| Refrigeración | ➖ | — | No aplica |
| Control de Calidad | ✅ | C1 | Visual de uniones, ~10 min |

**⚠️ Proceso dominante:** Soldadura (muchos puntos = tiempo alto aunque cada uno sea simple)
**Extrapolación:** Estantería-parrilla, rejas, separadores

---

## 4. Sumidero

**Complejidad global:** C1
**Descripción:** Receptor de agua de piso con tapa. Cuerpo rectangular soldado, tapa perforada o rejilla.

| Proceso | Aplica | Nivel | Driver que determina el nivel |
|---------|--------|-------|-------------------------------|
| Trazado | ✅ | C1 | Pieza simple, plano estándar |
| Corte Manual | ✅ | C1 | < 2m lineales, 1mm |
| Corte Láser | ✅ | C1 | Tapa perforada → láser más eficiente |
| Grabado Láser | ➖ | — | No aplica |
| Plegado | ✅ | C1 | 4 lados del cuerpo, dobleces rectos |
| Cilindrado | ➖ | — | No aplica (forma rectangular) |
| Soldadura | ✅ | C1 | 4 esquinas, soldadura de estructura, no visible |
| Pulido y Terminación | ✅ | C1 | Exterior visible, cepillado simple |
| Pintura | ➖ | — | Sin pintura |
| Refrigeración | ➖ | — | No aplica |
| Control de Calidad | ✅ | C1 | Visual + prueba de encaje de tapa, ~10 min |

**Costo HH estimado:** Todos los procesos C1 × 1.05
**Extrapolación:** Canaletas, tapa-registro, sumidero-rejilla

---

## 5. Cubrejunta

**Complejidad global:** C1
**Descripción:** Perfil plano metálico para cubrir juntas entre materiales. Solo corte y plegado, sin soldadura.

| Proceso | Aplica | Nivel | Driver que determina el nivel |
|---------|--------|-------|-------------------------------|
| Trazado | ✅ | C1 | 1 línea de doblez, pieza plana |
| Corte Manual | ✅ | C1 | ≤ 3m lineales, 1mm |
| Corte Láser | ❓ | C1 | Si se hacen en serie, nesting eficiente |
| Grabado Láser | ➖ | — | No aplica |
| Plegado | ✅ | C1 | 1–2 dobleces, perfil simple |
| Cilindrado | ➖ | — | No aplica |
| Soldadura | ➖ | — | **No aplica — clave del costo bajo** |
| Pulido y Terminación | ✅ | C1 | Superficie plana accesible, mínimo |
| Pintura | ➖ | — | Sin pintura |
| Refrigeración | ➖ | — | No aplica |
| Control de Calidad | ✅ | C1 | Visual rápido, ~5 min |

**⚠️ Característica clave:** Sin soldadura → es el producto de menor HH del catálogo
**Extrapolación:** Peinazo, zócalo, moldura, revestimiento-liso, canaleta

---

## 6. Moldura

**Complejidad global:** C1
**Descripción:** Perfil de terminación decorativa. Similar a cubrejunta pero con forma más elaborada.

| Proceso | Aplica | Nivel | Driver que determina el nivel |
|---------|--------|-------|-------------------------------|
| Trazado | ✅ | C1 | Perfil estándar, medidas repetitivas |
| Corte Manual | ✅ | C1 | ≤ 3m, 1mm |
| Corte Láser | ❓ | C1 | Si tiene perforaciones decorativas |
| Grabado Láser | ➖ | — | No aplica |
| Plegado | ✅ | C1–C2 | 2–4 dobleces (perfil complejo tiene más pasos) |
| Cilindrado | ❓ | C1 | Si la moldura es curva (revestimiento-curvo) |
| Soldadura | ➖ | — | No aplica en moldura estándar |
| Pulido y Terminación | ✅ | C1 | Superficie accesible, acabado fino |
| Pintura | ➖ | — | Sin pintura |
| Refrigeración | ➖ | — | No aplica |
| Control de Calidad | ✅ | C1 | Visual, ~5 min |

**Diferencia con cubrejunta:** más dobleces, acabado más fino
**Extrapolación:** Revestimiento-modular, revestimiento-curvo, molduras esquineras

---

## 7. Basurero Estándar

**Complejidad global:** C1–C2
**Descripción:** Contenedor rectangular o cilíndrico estándar, con o sin tapa. Acabado cepillado.

| Proceso | Aplica | Nivel | Driver que determina el nivel |
|---------|--------|-------|-------------------------------|
| Trazado | ✅ | C1 | Pieza estándar, plano fijo |
| Corte Manual | ✅ | C1 | < 3m lineales |
| Corte Láser | ✅ | C1 | Lámina 1mm, forma rectangular simple |
| Grabado Láser | ❓ | C1 | Solo si lleva logo del cliente |
| Plegado | ✅ | C1–C2 | 4 lados, dobleces rectos, largo ≤ 1m |
| Cilindrado | ❓ | C1 | Solo si es basurero cilíndrico |
| Soldadura | ✅ | C1–C2 | 4 esquinas, fondo, tapa opcional |
| Pulido y Terminación | ✅ | **C3** | **5 horas, pasa por 3 pulidas** — es el proceso más costoso |
| Pintura | ➖ | — | Sin pintura normalmente |
| Refrigeración | ➖ | — | No aplica |
| Control de Calidad | ✅ | C1 | Visual, ~10 min |

**⚠️ Insight crítico:** El basurero tiene complejidad global C1 pero el proceso de **Pulido es C3**.
Esto valida exactamente por qué necesitamos complejidad por proceso y no solo global.
**Extrapolación:** Basurero-reciclaje (más compartimentos → soldadura C2), basurero-con-mecanismo (+ cilindrado C1)

---

## Resumen de perfiles de proceso

| Producto | Trazado | Corte | Láser | Plegado | Cilindrado | Soldadura | Pulido | QC |
|---------|---------|-------|-------|---------|-----------|---------|-------|-----|
| Poruña | C1 | C1 | ➖ | C1 | C1 | C1 | C1 | C1 |
| Campana | C1-C2 | C1 | C1 | C2 | ❓ | C2 | C2 | C1 |
| Celosía | C1 | C1-C2 | ❓ | ➖ | ➖ | **C2-C3** | C2 | C1 |
| Sumidero | C1 | C1 | C1 | C1 | ➖ | C1 | C1 | C1 |
| Cubrejunta | C1 | C1 | ❓ | C1 | ➖ | **➖** | C1 | C1 |
| Moldura | C1 | C1 | ❓ | C1-C2 | ❓ | ➖ | C1 | C1 |
| Basurero std | C1 | C1 | C1 | C1-C2 | ❓ | C1-C2 | **C3** | C1 |

---

## Lógica de extrapolación

Una vez calibrados los 7 productos con tiempos reales, las reglas de extrapolación son:

```
Nuevo producto X de subfamilia Y:
  1. Identificar qué procesos aplican (de la tabla de subfamilia)
  2. Para cada proceso activo: asignar nivel C1/C2/C3 según drivers
  3. Costo_proceso = Tiempo_base × HH_nivel × Costo_HH_hora
  4. Costo_total = Σ (todos los procesos activos)
  5. Ajustar por dimensiones (fórmula metod.md: rendimiento × dimensión)
```

**Grupos de extrapolación naturales:**

| Grupo ancla | Se extrapola a |
|-------------|---------------|
| Cubrejunta (sin soldadura, C1 todo) | Peinazo, zócalo, moldura liso |
| Sumidero (4 lados soldados, C1) | Canaleta, tapa-registro |
| Basurero std (pulido C3) | Basurero-reciclaje, basurero-con-mecanismo |
| Campana (plegado C2, soldadura C2) | Campana-central, accesorio-campana |
| Poruña (cilindrado C1, soldadura C1) | Salsera, balde, taza-accesorio |
