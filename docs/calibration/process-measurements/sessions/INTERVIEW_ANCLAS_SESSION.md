# Interview Session — Anchor Product Selection & First-Principles Challenge
**Session ID:** anclas-challenge-2026-04-13  
**Expert:** Fabio Fuentes y Maria Ignacia 
**Facilitator:** Claude (knowledge-extractor agent)  
**Objective:** Validate perfil_proceso categories and select anchor products per category × complexity level  
**Status:** IN PROGRESS

---

## Session Rules
- One question at a time
- Push for first principles: WHY, not just WHAT
- Every assumption in FRAMEWORK_CATEGORIZATION.md is challengeable
- Decisions get logged here as Q&A → then structured as FRAMEWORK updates

---

## Q&A Log


---

### B1-Q1 ✅ CERRADA — ¿p-basurero-rect y p-basurero-cil deben ser perfiles separados?

**Pregunta:** El cilindrado de un basurero chico son ~20min — ¿justifica perfil separado o es un flag dentro de p-basurero?

**Respuesta (Fabio, 2026-04-13):**
Sí, son separados. Razones:

1. **Siempre pasa por cilindrado** — el material sale de bobina y obligatoriamente pasa por el proceso, no es opcional.
2. **Muchas pasadas con madera** — no es una pasada: se hacen múltiples pasadas usando planchas de madera como insumo/herramienta de apoyo.
3. **Plano de plantilla** — se dibuja un plano específico de cilindrado con plantillas antes de empezar.
4. **Insumo específico: madera** — planchas de madera son consumible de este proceso (no aparecen en otros perfiles).
5. **Máquina no-CNC, ajuste manual** — se mueven distancias de rodillos a mano, se prueba de a poco. Alta variabilidad según operador.
6. **Cuello de botella por maestro especialista** — hay un maestro que sabe dibujar el plano de cilindrado con plantillas. Si está ocupado, el proceso se detiene. Mismo patrón que el maestro soldador.

**Decisión:** p-basurero-rect y p-basurero-cil son perfiles SEPARADOS. El cilindrado no es un flag — es un proceso con setup propio, consumibles propios, especialista propio, y riesgo de bottleneck.

**Implicación para el framework:**
- Cilindrado tiene un costo de setup NO capturado actualmente: plano/plantilla + ajuste de rodillos + madera.
- El "tiempo de cilindrado" reportado por Hernán (~20min para basurero chico) es probablemente solo T_exec, no T_setup ni T_template.
- La disponibilidad del maestro es un factor de capacidad, no de complejidad — pero afecta lead time.

---

### B2-p-modulo, p-cocina-gas, p-tina, p-refrigerado ✅ CERRADAS

**p-modulo:**
- No lleva puertas ni mecanismo — el diseño/características es lo que sube el nivel
- Driver: complejidad del diseño (X) + largo (G)

| Nivel | Condición |
|-------|-----------|
| C1 | Diseño simple, largo estándar |
| C2 | Diseño con características especiales (formas, detalles) |
| C3 | Diseño complejo + largo grande |

**p-cocina-gas:**
- Driver principal: número de quemadores
- Horno = sube nivel (agrega proceso y componentes)
- Tipo de gas (natural vs licuado): cambia válvulas/diámetros pero impacto mínimo en complejidad de fabricación

| Nivel | Condición |
|-------|-----------|
| C1 | 1–2 quemadores, sin horno |
| C2 | 3–4 quemadores O con horno simple |
| C3 | 5+ quemadores O horno + quemadores múltiples |

**p-tina:**
- Driver: capacidad en litros
- Válvulas casi iguales en todos los modelos — no discriminan nivel

| Nivel | Condición |
|-------|-----------|
| C1 | Capacidad pequeña |
| C2 | Capacidad media |
| C3 | Capacidad grande |

*(Umbrales en litros pendientes — requieren medición)*

**p-refrigerado:**
- Sí es distinto entre niveles — diferente planificación y mecanismo más complejo
- No todos son C3: la complejidad del sistema de frío (circuitos, componentes) define el nivel

| Nivel | Condición |
|-------|-----------|
| C1 | ¿Existe? — pendiente validar con técnico frigorista |
| C2 | Sistema estándar, 1 circuito |
| C3 | Sistema complejo, múltiples circuitos, mayor planificación |

---

### B2-p-basurero-cil, p-lavadero, p-carro-bandejero, p-carro-traslado ✅ CERRADAS

**p-basurero-cil:**
| Nivel | Condición |
|-------|-----------|
| C1 | Sin mecanismo |
| C2 | Con mecanismo (pedal o vaivén) |
| C3 | ¿Existe? — pendiente |

**p-lavadero:**
| Nivel | Condición | Driver |
|-------|-----------|--------|
| C1 | 1 taza, profundidad estándar | Número de tazas + profundidad |
| C2 | 1 taza profunda O 2 tazas estándar | Ambos ejes suman |
| C3 | 2+ tazas profundas o configuración compleja | Máximo de ambos ejes |

**p-carro-bandejero:**
| Nivel | Condición | Driver |
|-------|-----------|--------|
| C1 | Pocos niveles, largo corto | Número de niveles + largo |
| C2 | Más niveles O mayor largo | Ambos ejes |
| C3 | Muchos niveles + largo grande | Máximo de ambos ejes |

**p-carro-traslado:**
| Nivel | Condición | Driver |
|-------|-----------|--------|
| C1 | Sin cajones, sin divisiones, sin mecanismo | Compartimentos base |
| C2 | Con divisiones internas | Más cajones/divisiones |
| C3 | Con cajones + divisiones + mecanismo con puertas | Mecanismo = salto definitivo |

---

### B2-p-campana, p-electrico, p-rejilla ✅ CERRADAS — complejidad agrupada

**p-campana — discriminantes C1/C2/C3:**

Dos ejes independientes:
1. **Componentes** — sin extractor (decorativa) vs con extractor (motor). El extractor es el salto C1→C2.
2. **Tamaño/largo** — a partir de cierto largo se necesitan más operadores. La forma es la misma pero el HH sube por límite de personas. Salto C2→C3.

| Nivel | Componentes | Tamaño | Operadores |
|-------|------------|--------|-----------|
| C1 | Sin extractor (accesorio/filtro, decorativa) | Cualquiera | 1 |
| C2 | Con extractor (motor) | Largo estándar | 2 |
| C3 | Con extractor + largo grande (requiere más operadores) | Grande — límite de personas | 3+ |

**p-electrico — discriminantes C1/C2/C3:**
- No existe "número de divisiones" como único discriminante
- La diferencia de potencia entre divisiones requiere **más planificación y diferenciación** de componentes
- Mayor dificultad por: diferente potencia por sección, termostatos distintos, cableado diferenciado

| Nivel | Condición | Driver |
|-------|-----------|--------|
| C1 | 1 circuito, 1 potencia uniforme | C=1, planeación simple |
| C2 | 2–3 circuitos o potencias distintas | C=2-3, planeación diferenciada |
| C3 | 4+ circuitos o múltiples potencias y termostatos individuales | C=3, alta complejidad de planeación eléctrica |

**p-rejilla — discriminantes C1/C2/C3:**
- Puntos de soldadura correlacionados con área del panel
- Más elementos = más puntos de soldar = más tiempo y consumibles
- **No son variables independientes** — el área determina la cantidad de elementos, que determina los puntos

| Nivel | Área panel | Elementos/varillas | Puntos soldadura |
|-------|-----------|-------------------|-----------------|
| C1 | Pequeña | Pocos | Pocos |
| C2 | Media | Medio | Medio |
| C3 | Grande o densidad alta | Muchos | Muchos |

---

### B2-p-laminar-simple, p-sumidero, p-laser ✅ CERRADAS — complejidad agrupada

**p-laminar-simple:**
- Siempre C1. No existe C2 ni C3 en este perfil.
- El tamaño escala con factor_escala dentro de C1, no sube nivel.

**p-sumidero — corrección importante:**
Hay dos tipos de tapa/rejilla con soldadura distinta:

| Tipo | Proceso | Soldadura | Nivel soldadura |
|------|---------|-----------|----------------|
| Tapa perforada (láser) | Corte láser, sin soldadura en tapa | Mínima — solo encaje | C1 |
| Rejilla de pletinas soldadas | Pletinas cortadas + soldadura de cada unión | Más complejo | C2 |

- El **cuerpo** del sumidero es siempre el mismo en complejidad (C1) — independiente del tamaño.
- La **tapa/rejilla** determina el nivel de soldadura: tapa perforada → C1, rejilla pletinas → C2.
- → p-sumidero tiene dos sub-variantes: con tapa láser (todo C1) y con rejilla soldada (soldadura C2).

**p-laser — discriminantes C1/C2/C3:**
Dos drivers independientes:

1. **Tiempo diseñador** — complejidad del diseño (formas no ortogonales, densidad, detalle). Es el driver principal del nivel.
2. **Espesor** — maneja tiempo de máquina + potencia requerida. Driver secundario de costo.

| Nivel | Tiempo diseñador | Espesor | Ejemplo |
|-------|-----------------|---------|---------|
| C1 | Diseño simple, DXF disponible | ≤1mm | Tapa perforada simple |
| C2 | Diseño complejo, DXF a crear | 1–3mm | Tostador (densidad + detalle) |
| C3 | Diseño muy complejo O externalizado por espesor | >3mm o diseño especial | Externo |

---

### B2-p-cilindrico ✅ CERRADA — C1/C2/C3 del cilíndrico

**Pregunta:** ¿El discriminante es espesor + diámetro, o hay algo más?

**Respuesta (Fabio, 2026-04-13):** Confirmado — espesor y diámetro son los discriminantes correctos.

| Nivel | Espesor | Diámetro / Tamaño | Ejemplo |
|-------|---------|------------------|---------|
| C1 | ≤1.5mm | ≤ ø500mm | Poruña, balde pequeño |
| C2 | 1.5–2mm | ø500–800mm | Balde grande, cilíndrico mediano |
| C3 | ≥2mm | >ø800mm o alto volumen | Estanque 1000L |

---

### B2-p-basurero-rect ✅ CERRADA — C1/C2/C3 del basurero rect

**Pregunta:** ¿Hay algo que diferencie un basurero rect simple de uno complejo más allá del tamaño?

**Respuesta (Fabio, 2026-04-13):**

Dos variables independientes que suben la complejidad:

**Variable 1 — Tipo de terminación (Pulido):**

| Terminación | Proceso | Velocidad | Insumos | Nivel Pulido |
|-------------|---------|-----------|---------|--------------|
| Vibrado | Lijadora más rápida | Rápido | Menos | C2 |
| Semi-brillante | Más pasadas, chascon + rodillo | Lento | Más | C3 |
| Brillante | No se hace — muy costoso, time-intensive, muchos insumos y escobillas | — | — | N/A (no aplica en Dulox) |

**Variable 2 — Mecanismo:**
- Sin mecanismo (tapa simple con bisagras): base
- Con mecanismo pedal o vaivén → sube complejidad en componentes (C sube) y en QC

**Regla emergente p-basurero-rect:**

| Nivel | Condición | Pulido | Mecanismo |
|-------|-----------|--------|-----------|
| **C1** | ¿Existe? | — | — |
| **C2** | Caja simple, terminación vibrado | Pulido vibrado (rápido) | Sin mecanismo |
| **C3** | Terminación semi-brillante O con mecanismo pedal/vaivén | Pulido semi-brillante (pasadas + rodillo) | Con mecanismo |

**Nuevo hallazgo — Dulox no hace brillante:** Por decisión comercial/operativa — demasiado costoso en tiempo e insumos (escobillas). No existe en el catálogo fabricado.

**Implicación:** La terminación es una variable de diseño que debe capturarse como flag en el producto, no derivarse solo de la subfamilia.

---

### B1-Q13 ✅ CERRADA — ¿El módulo neutro es p-meson?

**Pregunta:** ¿Módulo neutro, salad bar, módulo de servicio van en p-meson?

**Respuesta (Fabio, 2026-04-13):**
- Estructuralmente distinto al mesón
- Es como un **mueble de solo plegado** — el cuerpo es plegado dominante, no perfilería como el mesón
- La cubierta sí va soldada
- Tiene **más pasos de fabricación** que un mesón — el armado es diferente

**Decisión:** Crear **p-modulo** como perfil propio.

| Característica | p-meson | p-modulo |
|---|---|---|
| Estructura base | Perfilería (30×30mm) | Plegado dominante |
| Cubierta | Soldada | Soldada |
| Armado | Soldadura de estructura + cubierta | Más pasos — armado de cuerpo plegado + cubierta |
| Analogía | Mesa de trabajo | Mueble de cocina profesional |

**Driver de escala:** Largo × número de compartimentos  
**Productos:** Módulos neutros, módulos de servicio, salad bar (estructura)

---

### B1-Q11b ✅ CERRADA — Revisión de p-cilindrico, p-custom, p-laminar-simple

**Respuesta (Fabio, 2026-04-13):**

**p-custom:** Confirmado. Modelos que escalan completamente según el proyecto. No extrapolable con fórmula fija.

**Reclasificaciones desde p-cilindrico:**

| Producto | Perfil anterior | Perfil correcto | Razón |
|---------|----------------|----------------|-------|
| Escurridor de servicios | p-cilindrico | **p-importado** | No se fabrica en planta |
| Espátula | p-cilindrico | **p-laminar-simple** | Pieza plana, no cilíndrica |
| Hervidores de agua y leche | p-cilindrico | **p-importado** | No se fabrica en planta |
| Servilletero | p-cilindrico | **p-custom** | Depende mucho del modelo/proyecto |
| Tina quesera | p-cilindrico | **p-lavadero** (variante) | Es como un p-lavadero con fondo — taza fabricada en planta con fondo cerrado |
| Molde de queso cilíndrico | p-cilindrico | **p-cilindrico** ✅ | Correcto |
| Molde de queso cuadrado | p-cilindrico | **pendiente** | ¿p-sumidero? ¿p-meson? Forma cuadrada con fondo — definir |

**Hallazgo — tina quesera (CERRADO):**
- Rectangular, pero materiales distintos a todo lo anterior
- Lleva llaves (válvulas) + doble fondo + espesor especial + mayor intervención de proceso
- No es p-lavadero (sin desagüe estándar, con doble fondo), no es p-carro-traslado (no es mueble genérico), no es p-sumidero (materiales y proceso distintos)
- → **Crear perfil propio: p-tina** para tinas queseras y recipientes industriales con doble fondo, válvulas y movilidad
- Driver principal: capacidad (litros) + número de llaves/válvulas

**Hallazgo — molde de queso cuadrado (CORREGIDO):**
- NO es similar a p-sumidero — el sumidero tiene encaje y soldadura compleja
- Molde cuadrado = caja plegada simple + anillo con pinchazos + prensa simples
- Poca soldadura, sin acabado especial, ensamble mecánico simple
- → **Reclasificar a p-laminar-simple** (plegado simple + ensamble mínimo)

---

### B1-Q10 ✅ CERRADA — ¿Cuál es el límite entre p-laser y p-rejilla?

**Pregunta:** El tostador tiene perforaciones densas + rack de varillas soldadas. ¿p-laser o p-rejilla?

**Respuesta (Fabio, 2026-04-13):**
El discriminante de p-laser NO es cuánta soldadura lleva — es la **complejidad geométrica del corte**.

**p-laser si:**
- Formas no ortogonales (curvas, ángulos no estándar, siluetas complejas)
- Diseños complejos → tiempo hora/hombre del diseñador
- La máquina láser se demora más por geometría o densidad de corte
- Espesor alto → reduce velocidad de corte y exige más potencia
- Ejemplo: Tostador (perforaciones densas + forma compleja) → **p-laser**

**p-rejilla si:**
- Patrón repetitivo ortogonal de varillas soldadas
- El tiempo está en soldadura de puntos, no en el diseño
- Geometría simple — cuadrícula o patrón estándar
- Ejemplo: Celosía de varillas → **p-rejilla**

**Regla para casos mixtos (tostador con rack):**
→ Asignar al perfil del **proceso que domina el costo y el tiempo de diseño**.
→ Tostador: la complejidad geométrica del láser + tiempo diseñador domina → **p-laser**

**Nuevo driver identificado para p-laser:**
- D (espesor) afecta directamente velocidad de corte y potencia → es un driver de costo real en p-laser, no solo en soldadura
- Tiempo diseñador = costo HH oculto que no aparece en ningún template actual → **gap crítico**

---

### B1-Q9 ✅ CERRADA — ¿p-refrigerado es coherente para vitrinas y mesones refrigerados?

**Pregunta:** ¿La vitrina refrigerada va en p-refrigerado o p-importado?

**Respuesta (Fabio, 2026-04-13):**
- Tanto vitrinas como mesones refrigerados pueden ser **importados O fabricados en planta** según el caso.
- La vitrina tiene vidrio, exhibición, iluminación — estructuralmente distinta al mesón refrigerado.
- Los fabricados en planta son generalmente **proyectos especiales**.

**Regla discriminante — igual que en p-lavadero:**

| Condición | Perfil |
|-----------|--------|
| Vitrina o mesón refrigerado **importado** | → **p-importado** |
| Vitrina o mesón refrigerado **fabricado en planta** (proyecto especial) | → **p-refrigerado** |

**Pregunta abierta que queda:** ¿Dentro de p-refrigerado, el cuerpo de una vitrina (vidrio, exhibición) es tan diferente al de un mesón que necesitan sub-perfiles? O ¿el proceso de refrigeración los unifica lo suficiente como para compartir ancla?

**Decisión provisional:** p-refrigerado se mantiene como perfil único para fabricados en planta. La variación entre vitrina y mesón se captura con el vector per-proceso (comp. eléctrico diferente, QC diferente). **Requiere validación con técnico frigorista.**

---

### B1-Q8 ✅ CERRADA — ¿Baños maría van en p-electrico o p-cocina-gas?

**Pregunta:** ¿Los baños maría a gas van en p-cocina-gas? ¿Los de gabinete son p-meson?

**Respuesta (Fabio, 2026-04-13):**
- Baño maría NO usa quemador de fuego directo. Usa **gas/fluido interno** para calentamiento indirecto del baño de agua. Proceso completamente distinto a una cocina a gas.
- No van en p-cocina-gas — se mantienen en **p-electrico** (mismo proceso de componentes de calor, distinto mecanismo).
- **Baño maría con gabinete = p-importado.** No se fabrica en planta.

**Decisión:**
- Baños maría fabricados (sin gabinete) → **p-electrico** ✅
- Baños maría con gabinete → **p-importado** ✅
- p-cocina-gas queda exclusivo para: planchas gas, anafes, cocinas con quemadores de fuego directo

**Corrección al framework:** p-electrico debe aclarar que incluye calentamiento indirecto (baño maría) además de resistencias directas.

---

### B1-Q7 ✅ CERRADA — ¿p-celosia es coherente para celosías y barandas?

**Pregunta:** ¿Celosía decorativa y baranda estructural van juntas o separadas?

**Respuesta (Fabio, 2026-04-13):**
- Celosías = rejillas. Patrón de varillas soldadas. Soldadura domina (muchos puntos, patrón repetitivo).
- Barandas = lógica de corte diferente. No es lo mismo que una rejilla. Elemento estructural con pasamanos, montantes, tensores — la geometría y el corte son distintos.

**Decisión:** Dividir p-celosia en 2 perfiles.

| Perfil | Qué es | Proceso dominante | Driver |
|--------|--------|------------------|--------|
| **p-celosia** *(renombrar a p-rejilla)* | Rejilla/celosía decorativa o funcional. Patrón de varillas en cuadrícula. | Soldadura C2-C3 (muchos puntos de unión) | Área panel × densidad de varillas |
| **p-baranda** *(nuevo)* | Baranda de seguridad. Pasamanos + montantes ± tensores. | Corte con lógica propia + soldadura estructural | Metros lineales × altura |

**Pendiente confirmar:** ¿El nombre correcto es p-rejilla o mantener p-celosia para la rejilla?

---

### B1-Q6 ✅ CERRADA — ¿p-carro es un perfil coherente o debe dividirse?

**Pregunta:** ¿Carro cerrado con puertas es p-carro con C más alto, o perfil separado?

**Respuesta (Fabio, 2026-04-13):**

Dos correcciones simultáneas:

**Corrección 1 — Material base estaba MAL en el framework:**
- p-carro NO usa estructura tubular cilindrada
- Usa **perfilería** (perfiles estructurales) — mismo material base que mesón
- Eliminar "cilindrado" del perfil de carros completamente

**Corrección 2 — p-carro debe dividirse en 2:**

| Perfil | Descripción | Analogía |
|--------|------------|---------|
| **p-carro-bandejero** | Estructura de perfilería + bandejas/niveles + ruedas. Abierto. | Estantería con ruedas |
| **p-carro-traslado** | Más grande, con puertas/paneles, ruedas industriales. Cerrado. | Mueble con ruedas |

**Driver de escala:**
- p-carro-bandejero: número de niveles × largo
- p-carro-traslado: área total de paneles + número de compartimentos

**Decisión:** Eliminar p-carro. Crear p-carro-bandejero y p-carro-traslado.

---

### B1-Q5 ✅ CERRADA — ¿Las planchas/anafes/cocinas gas necesitan perfil propio?

**Pregunta:** ¿Van en un perfil existente o crean uno nuevo?

**Respuesta (Fabio, 2026-04-13):**
- NO es un cuerpo laminar simple — tiene complejidad estructural propia
- Sí justifican perfil propio: **p-cocina-gas**
- Lo que varía entre productos de esta familia es la **disposición de componentes** (quemadores, plancha, manifold) — no la estructura base del cuerpo
- Estructuralmente el cuerpo es casi el mismo entre anafe, plancha a gas y cocina industrial

**Decisión:** Crear `p-cocina-gas` como perfil nuevo.

**Driver de escala:** Número de quemadores / secciones (C)  
**Proceso dominante por confirmar:** ¿Instalación gas domina sobre fabricación del cuerpo? → Pendiente entrevista técnico gas  
**Productos:** Planchas a gas, anafes, cocinas industriales a gas, freidoras gas

---

### B1-Q4 ✅ CERRADA — ¿p-plancha-simple tiene sentido como perfil?

**Pregunta:** ¿p-plancha-simple aplica a planchas/anafes/cocinas, o cubre algo más amplio?

**Respuesta (Fabio, 2026-04-13):**

`p-plancha-simple` no tiene sentido como categoría. Es un cajón de sastre con productos de fabricación completamente distintos. Se disuelve.

**Redistribución de productos que estaban en p-plancha-simple:**

| Producto | Perfil correcto | Razón |
|---------|----------------|-------|
| Cubrejunta, zócalos, peinazo, molduras, smasher/prensa hamburguesa, marcos ventas y puertas | **p-laminar-simple** (nuevo nombre propuesto) | Lo único realmente laminar-plano. Corte + doblez mínimo, sin soldadura visible |
| Perol de sopas, grifería, cortadora de papas PIPP, filtros de campana | **p-importado** | No se fabrican en planta |
| Repisas, mesas desueradoras | **p-meson** | Misma lógica estructural que mesón simple |
| Guías de carros | Próximo a **p-celosia** o baranda fabricada | Estructura similar a barandas |
| Dispensador de papas fritas | **p-cilindrico** | Forma cilíndrica — familia poruña |
| Basureros (mal ubicados aquí) | **p-basurero-rect** o **p-basurero-cil** | Según forma |

**Lo que queda sin resolver:** ¿Dónde van las planchas a gas, anafes y cocinas industriales? El usuario no las mencionó — quedan como **pendiente de clasificar**.

**Decisión:** 
- `p-plancha-simple` se elimina como categoría
- Se propone `p-laminar-simple` para: cubrejunta, zócalo, peinazo, moldura, marcos, smasher — productos de corte + plegado mínimo, sin soldadura compleja
- Planchas gas, anafes, cocinas industriales → **pendiente** (ver B1-Q5)

**Implicaciones:**
- ~18 productos en el CSV asignados a p-plancha-simple necesitan reclasificación
- p-laminar-simple sería el perfil de menor costo del catálogo (sin soldadura = HH mínimo)
- Alinea con lo que ya documentamos en PRODUCTS_8020_PROCESS_MAP.md para Cubrejunta ("sin soldadura — costo HH mínimo del catálogo")

---

### B1-Q3 ✅ CERRADA — ¿p-meson y p-lavadero deben ser perfiles separados?

**Pregunta:** ¿El lavadero es un mesón con una taza, o necesita su propio modelo de extrapolación?

**Respuesta (Fabio, 2026-04-13):**

No es binario — hay tres niveles dentro de lo que hoy llamamos "meson" y "lavadero":

**Nivel 1 — Mesón simple:** Sin nada. Sin respaldo, sin cortagotas, sin repisa. → p-meson C1.

**Nivel 2 — Mesón complejo / lavadero-like:** Tiene respaldo, cortagotas, repisas. Se parece a un lavadero pero NO tiene taza fabricada en planta. Taza comprada/importada o sin taza. → p-meson C2-C3 o p-lavadero C1-C2.

Ejemplos que pertenecen acá (estructuralmente son p-meson con taza comprada):
- Lavamanos 1 taza
- Lavadero triple ZLLCA-1800
- Mesón lavadero BAMTE-1400
- ZLLCA-0103

**Nivel 3 — Lavadero complejo:** Fabrican la taza en planta (no importada). Soldadura requiere 2 personas. Más operadores en plegado. Producto verdaderamente distinto en fabricación.

Ejemplos:
- Lavadero 4 puestos de trabajo ZLLE-0128
- ZLLE-0260

**Decisión:** La separación p-meson / p-lavadero NO debe hacerse por nombre del producto. Debe hacerse por:

| Criterio | p-meson | p-lavadero |
|----------|---------|-----------|
| ¿Taza fabricada en planta? | No (o sin taza) | **Sí** |
| Soldadura | 1 soldador | **2 soldadores** |
| Plegado taza | SKIP | **Plegado profundo, operadores extra** |
| Extrapolación | Por largo (metros) | Por número de tazas × profundidad |

**Implicaciones críticas:**
- ZLLCA-1800, BAMTE-1400, ZLLCA-0103, lavamanos 1 taza → reclasificar como **p-meson** (taza comprada, no fabricada)
- ZLLE-0128, ZLLE-0260 → confirmar como **p-lavadero** (taza fabricada en planta, soldadura 2 personas)
- La variable discriminante NO es "tiene taza" sino "¿quién fabrica la taza?"

---

### B1-Q2 ✅ CERRADA — ¿p-campana y p-meson deben ser perfiles separados?

**Pregunta:** El cuerpo de la campana es un cajón plegado con soldadura y pulido — igual que un mesón. ¿Qué justifica el perfil separado?

**Respuesta (Fabio, 2026-04-13):**

Tres razones distintas, cada una suficiente por sí sola:

**1. Materiales diferentes y no-lineales**
- Mesón: perfiles estructurales (30×30mm), patines, tubería. Materiales de estructura.
- Campana: láminas (elementos laminales). Sin perfiles. Sin patines.
- Los materiales son categorías distintas con precios distintos — no son variantes del mismo BOM.
- Las partes y piezas extra de la campana (filtros, motor, focos) no escalan con las dimensiones.

**2. Número de operadores**
- Mesón ≤ 1m: 1 operador para plegado.
- Campana: cuerpo siempre >1m → plegado requiere 2+ operadores para sostener y calzar con precisión.
- "Para plegar cosas de más de 1 metro se necesitan más de un operador. Hay que ajustar planchas con el calce justo para que quede cuadrado el pliegue."
- Esto es un costo de HH que no existe en p-meson y no puede capturarse con el mismo template.

**3. Costos totalmente distintos**
- El valor de materiales de una campana vs un mesón del mismo largo no es comparable.
- La no-linealidad de componentes comprados (filtros, motor) hace que el modelo de extrapolación sea estructuralmente diferente.

**Decisión:** p-campana y p-meson son perfiles SEPARADOS.

**Implicaciones para el framework:**
- p-campana debe modelar materiales laminales (no perfiles) + componentes fijos (no escalables)
- El plegado en p-campana es SIEMPRE C2+ (pieza >1m, 2+ operadores) — no existe campana con plegado C1
- El modelo de extrapolación de p-campana necesita dos componentes separados: (a) costo lámina × área, (b) costo componentes fijos por modelo

---

---

## BLOQUE 4 — Reglas de Extrapolación ✅ COMPLETADO

### Reglas por perfil

| Perfil | Driver de escala | ¿Lineal? | Ruptura de linealidad |
|--------|-----------------|----------|-----------------------|
| **p-meson** | Dimensión (largo) | ✅ Lineal dentro del nivel | Sube de nivel al agregar repisa, bordes, cajones — no por tamaño |
| **p-campana** | Largo (lámina) | ✅ Lineal (lámina fabricada) | Componentes comprados (filtros, motor) = fijos por modelo — NO escalan |
| **p-basurero-rect** | Área superficial | ✅ Lineal (mismo estructural) | Pulido brillante (no se hace) o agregar mecanismo → rompe linealidad |
| **p-lavadero** | Número de puestos | ≈ Lineal | Más operadores a mayor tamaño/peso. Soldadura, plegado y pulido de taza se vuelven más complejos con el peso |
| **p-cocina-gas** | Número de quemadores | ✅ Lineal — mismo incremental por quemador | Horno = salto de nivel, no solo incremental |
| **p-carro-bandejero** | Número de niveles | ✅ Lineal — costo incremental por nivel | Sin ruptura identificada |

### Regla general de extrapolación

```
Costo(producto X) = Costo(ancla) × factor_escala(driver)

factor_escala = valor_driver(X) / valor_driver(ancla)

EXCEPCIONES que rompen linealidad:
1. Componentes comprados fijos (campana) → modelar separado
2. Cambio de nivel por partes/mecanismo (meson, basurero) → no escalar, subir ancla
3. Cambio de operadores por peso/tamaño (lavadero grande) → corrección manual
```

---

## BLOQUE 1 — COMPLETADO ✅
19 perfiles validados. 4 eliminados. 7 creados.

---

## BLOQUE 2 — Complejidad C1/C2/C3 por perfil

**Pregunta que responde este bloque:** ¿Qué condición concreta hace que un producto dentro de un perfil sea C1, C2 o C3? ¿El CSV lo tiene bien asignado?

**Método:** Para cada perfil, definir la condición de entrada a cada nivel desde primeros principios — no desde el CSV.

---

### B2-p-meson

**B2-meson-Q1:** ¿Qué hace más caro un mesón?

**Respuesta (Fabio, 2026-04-13):**
Dos ejes independientes que suben el costo:

1. **Tamaño** — si se dobla el tamaño: más soldaduras, más personas, más materia prima, más pulido. Escala proporcionalmente (lineal).

2. **Partes** — cajones y puertas suman materiales y procesos de forma no lineal. No es solo "más grande" — es una categoría diferente de fabricación.

**Unidad base del mesón:** superficie + patas. Eso es el mesón en su expresión más simple. Todo lo que se agrega sobre eso sube la complejidad.

**Implicación:** Los dos ejes deben ser independientes en el modelo:
- Tamaño → `factor_escala` (multiplica costo base)
- Partes (cajones/puertas) → sube el nivel de complejidad (C1 → C2 → C3)

**B2-meson-Q2:** Umbrales concretos C1/C2/C3

**Respuesta (Fabio, 2026-04-13):**

| Nivel | Condición real | Ejemplo ancla | Lo que tiene |
|-------|---------------|--------------|--------------|
| **C1** | Superficie + 4 patas + respaldo | BAMT-0900 | Cubierta, patas, respaldo. Sin repisa, sin puertas, sin cajones |
| **C2** | C1 + repisa inferior | Mesón con repisa | Agrega repisa → más soldadura, más material, más pulido de cara inferior |
| **C3** | C1/C2 + puertas correderas + rieles + bisagras + manilla + cajones | Mesón gabinete 900mm con puertas correderas + 3 cajones | Estructura completamente diferente — la base cambia, los componentes mecánicos suman HH |

**Regla emergente:**
- C1 = superficie + soporte. Sin componentes adicionales.
- C2 = agrega repisa u otro elemento pasivo (sin mecanismo).
- C3 = agrega mecanismo (puertas, rieles, bisagras, cajones). La estructura cambia.

**El tamaño escala DENTRO de cada nivel** — un mesón C1 de 1800mm es C1 con factor_escala 2× vs el de 900mm.

**Implicación crítica para el CSV:** Hay mesones en el CSV clasificados C2 y C3 solo por largo (ej. mesón abierto 1900mm = C1 en el CSV). Revisar si el largo sin componentes extra justifica subir nivel o solo factor_escala.

---

## Decisions Made

| # | Decisión | Justificación |
|---|---------|--------------|
| B1-Q1 | p-basurero-rect y p-basurero-cil son perfiles SEPARADOS | Cilindrado tiene plano/plantilla, insumo madera, ajuste manual de rodillos, múltiples pasadas, maestro especialista. No es un flag. |
| B1-Q2 | p-campana y p-meson son perfiles SEPARADOS | Ver Q2 abajo |
| B1-Q3 | p-meson y p-lavadero son perfiles SEPARADOS — pero la frontera es fabricación de taza, no nombre del producto | ZLLCA-1800, BAMTE-1400, ZLLCA-0103 → reclasificar a p-meson. ZLLE-0128, ZLLE-0260 → confirmar p-lavadero |
| B1-Q4 | **p-plancha-simple NO EXISTE como perfil válido** — es un cajón de sastre. Disolver y redistribuir. Ver Q4. | Productos reasignados a sus perfiles reales. Planchas/anafes/cocinas gas → p-cocina-gas |
| B1-Q5 | **p-cocina-gas** es un perfil propio y válido | Cuerpo estructuralmente complejo (no laminar simple). Lo que varía entre productos es la disposición de componentes (quemadores, plancha, manifold). Estructura base es casi la misma entre anafe, plancha y cocina. |
| B1-Q6 | **p-carro se divide en 2 perfiles separados** + corrección de material base | p-carro NO usa cilindrado — usa perfilería. p-carro-bandejero = estantería con ruedas. p-carro-traslado = mueble con ruedas, más grande y complejo. Ver Q6. |
| B1-Q7 | **p-celosia se divide en 2 perfiles separados** | Celosías = rejillas (soldadura dominante, patrón repetitivo). Barandas = lógica de corte diferente, elemento estructural de seguridad. Ver Q7. |
| B1-Q8 | **p-electrico se mantiene para baños maría** — no van en p-cocina-gas | Baño maría NO usa quemador de fuego directo — usa gas/fluido interno para calor indirecto. Sistema completamente distinto a cocina gas. Baño maría con gabinete = p-importado. |
| B1-Q9 | **p-refrigerado discriminante = fabricado en planta, NO el tipo de producto** | Vitrinas y mesones refrigerados pueden ser importados O fabricados. Si importado → p-importado. Si fabricado en planta (proyecto especial) → p-refrigerado. La vitrina refrigerada es estructuralmente distinta al mesón refrigerado — pero ambas comparten el proceso de refrigeración como dominante. Pendiente: ¿p-refrigerado debe dividirse en vitrina vs mesón o el proceso de frío los unifica? |
| B1-Q10 | **p-laser discriminante = complejidad geométrica del diseño, NO volumen de soldadura** | p-laser si: formas no ortogonales, diseños complejos, tiempo diseñador, máquina láser lenta por geometría o espesor. Tostador → p-laser (forma compleja + espesor define velocidad). p-rejilla si: patrón repetitivo ortogonal de varillas soldadas. |
| B1-Q11a | **p-sumidero corrección: soldadura NO es C1** — la rejilla superior lleva encaje con soldadura compleja | El sumidero tiene dos partes: (a) cuerpo caja 4 lados → soldadura C1. (b) rejilla/tapa superior → encaje con soldadura, NO trivial. Soldadura del sumidero = C1-C2 según tipo de rejilla. |
| B1-Q11b | **p-cilindrico tiene productos mal clasificados — reclasificación múltiple** | Escurridor servicios → p-importado. Espátula → p-laminar-simple. Hervidores agua y leche → p-importado. Servilletero → p-custom. Tina quesera → **p-tina (perfil nuevo)**: rectangular, doble fondo, llaves/válvulas, espesor especial, mayor intervención proceso. Molde queso cilíndrico → p-cilindrico ✅. Molde queso cuadrado → p-laminar-simple. |
| B1-Q12 | **p-baranda NO existe como perfil extrapolable — se fusiona con p-custom** | Toda baranda depende del proyecto. Cada instalación es diferente. No hay ancla ni extrapolación posible. |
| B1-Q13 | **Módulo neutro NO es p-meson — crear p-modulo** | Estructuralmente distinto: plegado dominante (cuerpo como mueble), cubierta soldada, más pasos de fabricación que un mesón. Lógica de armado diferente. |
| B1-Q14 | **Basurero reciclaje 4 compartimentos = p-basurero-rect** | Solo bisagras en tapa principal — sin mecanismo real. Simple estéticamente atractivo. La complejidad es Pulido C3, no mecanismos. ✅ Confirmado. |
| B1-Q15 | **Mesón refrigerado = p-refrigerado, NO p-meson** | La lógica de fabricación es distinta desde el diseño — no es un mesón con frío añadido. Los componentes internos (frío o calor) condicionan todo el cuerpo. Se estudia como sistema integrado. |

---

## Anchor Products — Final Selection

| perfil_proceso | C1 ancla | SKU/Handle | C2 ancla | SKU/Handle | C3 ancla | SKU/Handle |
|---------------|---------|-----------|---------|-----------|---------|-----------|
| p-meson | Mesón abierto 900mm | BAMT-0900 | Mesón abierto 1900mm repisa | BAMT-0197 | Mesón 4 cajones 1300mm | BAMTC-1300 |
| p-laminar-simple | Cubrejunta | pendiente SKU | N/A | — | N/A | — |
| p-modulo | pendiente | — | Módulo Neutro 1000mm | AUMN-1000 | pendiente | — |
| p-cocina-gas | Anafe 1 quemador | 1PQ | Cocina 4Q sin horno | 4PQN | Cocina 6Q + churrasquera | 6PQCH |
| p-campana | Filtro FIL-050 | FIL-050 | Campana mural 1500mm | CCCM-1510 | Campana central 3000mm | CCCI-3013 |
| p-cilindrico | Poruña 1KG | POR-1000 | Balde 20L | BLDS-300 | Hervidor 20L (fabricado) | AUHA-0157 |
| p-basurero-rect | N/A | — | Basurero simple BM-0700 | BM-0700 | Basurero Reciclaje 4 Comp. | BARE4-01300 |
| p-basurero-cil | Cenicero (sin mecanismo) | CEN-0650 | Con pedal | BAPLA-0470 | N/A | — |
| p-carro-bandejero | Carro 12 bandejas | AUCB-0178 | Carro 24 bandejas | AUCB-0810 | Carro bandejero cerrado 8 bandejas | AUCB-0790 |
| p-carro-traslado | pendiente | — | pendiente | — | pendiente | — |
| p-lavadero | Lavadero 1 puesto | ZLLE-0126 | Lavadero 4 puestos | ZLLE-0128 | Lavadero 8 puestos | ZLLE-0260 |
| p-tina | pendiente | — | pendiente | — | pendiente | — |
| p-sumidero | Sumidero 400×400 tapa perforada | SUMVE-0400 | Sumidero con rejilla | SUMHO-0200 | N/A | — |
| p-laser | N/A (no existe C1 en catálogo — lo simple va a p-laminar-simple) | — | Tostador | TOST-01 | N/A (externo) | — |
| p-rejilla | N/A (no existe aún en catálogo) | — | Celosía 500×200mm | CELL-0500 | N/A (no existe aún) | — |
| p-electrico | pendiente | — | Baño María 3 depósitos full | DUBM3 | Salsera (grande, puertas, gabinete, capacidad) | pendiente SKU |
| p-carro-traslado | pendiente | — | Carro traslado | CATR-0800 | pendiente | — |
| p-tina | pendiente | — | Tina quesera 100L | EITQ-0100 | pendiente | — |
| p-refrigerado | N/A (pendiente técnico) | — | pendiente | — | Mesón shop refrigerado | MPSC-1400 |
| p-importado | N/A | — | N/A | — | N/A | — |
| p-custom | N/A | — | N/A | — | N/A | — |
