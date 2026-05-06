# Framework de Categorización: perfil_proceso × complejidad
**Propósito:** Documentar el razonamiento detrás de cada categoría de proceso y nivel de complejidad.  
**Audiencia:** Cualquier persona que quiera extender el catálogo con nuevos productos.  
**Estado:** Validado — entrevista completa 2026-04-13/14 con Fabio Fuentes
Pendientes menores documentados en §11.  
**Última actualización:** 2026-04-14

---

## 1. ¿Qué es un `perfil_proceso`?

Un `perfil_proceso` NO es una familia de productos ni una descripción física. Es una **firma de fabricación**: el conjunto de procesos que se activan, en qué orden, y cuál es el driver de costo dominante.

**Por qué categorizar así (y no por familia o subfamilia):**
- Dos productos de familias distintas pueden tener exactamente el mismo perfil de fabricación → misma estructura de costos → mismo modelo de extrapolación.
- Dos productos de la misma familia pueden tener perfiles diferentes si uno tiene cilindrado y el otro no.
- La firma define QUÉ medir, no cómo se llama el producto.

**Principio:** Si dos productos tienen el mismo `perfil_proceso`, sus costos se extrapolan usando el mismo mecanismo (mismo anchor, mismo driver de escala, mismo factor de escala).

---

## 2. Los 4 Universal Drivers (G, D, C, X)

| Driver | Nombre | Qué mide | Escala |
|--------|--------|----------|--------|
| G | Geometry | Área de planta (L × W) en mm² | <500k→1 · 500k–1.5M→2 · >1.5M→3 |
| D | Density | Espesor de lámina en mm | ≤1.5mm→1 · 1.5–2mm→2 · >2mm→3 |
| C | Components | Número de piezas/subconjuntos | 1–3→1 · 4–7→2 · 8+→3 |
| X | Characteristics | Suma de feature flags activos | 0→0 · 1→1 · 2→2 · 3+→3 |

**Feature flags (X):**
- `acabado_especial` (+2): pulido fino / semi-brillo requerido
- `multiples_uniones` (+2): >8 puntos de soldadura
- `perforado` (+2): alta densidad de cortes (rejillas, celosías, tostadores)
- `geometria_curva` (+2): cilindrado o curvas de gran radio
- `refuerzo_estructural` (+2): tubos, perfiles estructurales, marcos reforzados
- `tolerancias_ajustadas` (+2): precisión dimensional exigente
- `material_no_estandar` (+2): acero >2mm, acero 430, materiales especiales

---

## 3. Tabla de Justificación por `perfil_proceso`

| perfil_proceso | Procesos activos (✅) | Driver primario | Driver secundario | Diferenciador clave | Escala con | Productos típicos |
|---------------|----------------------|-----------------|------------------|--------------------|-----------|--------------------|
| **p-meson** | Trazado, Corte Manual, Plegado, Soldadura, Pulido, QC | G (área superficial) | C (cajones, puertas) | Rectangulares planos. Estructura de **perfilería** (30×30mm) + cubierta plegada soldada. Pulido visible en cara superior. | Largo (metros) | Mesones de trabajo, estanterías, repisas — NO incluye módulos neutros |
| **p-modulo** *(nuevo)* | Trazado, Corte Manual, Plegado (dominante), Soldadura (cubierta), Pulido, QC | G (largo × compartimentos) | C | Cuerpo principal de **plegado dominante** (no perfilería). Cubierta soldada. Más pasos de fabricación que p-meson — armado diferente. Analogía: mueble de cocina profesional vs mesa de trabajo. | Largo × número de compartimentos | Módulos neutros, módulos de servicio, salad bar (estructura) |
| ~~**p-plancha-simple**~~ | ~~ELIMINADO~~ | — | — | **DISUELTO** — era un cajón de sastre sin coherencia de fabricación. Productos redistribuidos a sus perfiles reales. Ver decisión B1-Q4. | — | — |
| **p-laminar-simple** *(nuevo)* | Trazado, Corte Manual o Láser, Plegado (1-2 dobleces), QC | G (longitud) | — | **Sin soldadura o con soldadura mínima.** Perfil de menor costo del catálogo. Productos planos: corte + doblez simple. Insumos mínimos. | Metros lineales | Cubrejunta, zócalo, peinazo, moldura, marcos ventas/puertas, smasher/prensa hamburguesa |
| **p-cocina-gas** *(nuevo)* | Trazado, Corte Láser, Plegado, Soldadura, Pulido, Instalación Gas, QC | C (quemadores/secciones) | G (área cuerpo) | Cuerpo estructuralmente complejo (no laminar simple). Lo que varía entre productos es la **disposición de componentes** — quemadores, plancha, manifold. Estructura base es casi la misma entre anafe, plancha y cocina. Proceso instalación gas domina sobre fabricación del cuerpo (pendiente validar). | Número de quemadores / secciones | Planchas a gas, anafes, cocinas industriales, freidoras gas |
| **p-cilindrico** | Trazado, Corte Manual, Cilindrado, Soldadura, Pulido, QC | D (espesor) + G (diámetro) | C | Cilindrado es el proceso diferenciador. Pulido en superficie curva es más lento que plano | Capacidad (litros) o diámetro | Poruñas, baldes, escurridores, tinas queseras |
| **p-basurero-rect** | Trazado, Corte Láser, Plegado, Soldadura, Pulido C3, QC | G + X (acabado_especial) | C | **Pulido siempre C3** (3 pasadas, 5hrs) independiente del tamaño. El costo global es engañoso sin el vector de proceso | Capacidad (litros) | Basureros rectangulares estándar, modelo plaza, providencia |
| **p-basurero-cil** | Trazado (+ plano plantilla cilindrado), Corte Manual, Cilindrado (multi-pasadas + madera), Soldadura, Pulido C3, QC | D + G + X | C | Cilindrado es proceso propio con: plano/plantilla previo, insumo madera, ajuste manual de rodillos, múltiples pasadas, maestro especialista. NO es un flag — es un proceso con setup, consumibles y bottleneck propios. Pulido C3 en curva +30% vs plano. | Capacidad (litros) o diámetro | Basureros cilíndricos, con mecanismo pedal |
| ~~**p-carro**~~ | ~~ELIMINADO~~ | — | — | **DISUELTO** — demasiado amplio y material base estaba mal documentado. NO usa cilindrado — usa perfilería. Dividido en 2 perfiles. Ver B1-Q6. | — | — |
| **p-carro-bandejero** *(nuevo)* | Trazado, Corte Manual, Plegado, Soldadura, Pulido, QC | C (número de niveles) | G (largo) | **Perfilería** (no cilindrado). Estructura abierta: niveles + ruedas. Analogía: estantería con ruedas. Driver principal = número de niveles × largo. | Niveles × largo | Carros bandejeros, carros para bandejas |
| **p-carro-traslado** *(nuevo)* | Trazado, Corte Manual, Plegado, Soldadura, Pulido, QC | G (área paneles) | C (compartimentos/puertas) | **Perfilería** + paneles laminares. Estructura cerrada: puertas, compartimentos, ruedas industriales. Más grande y complejo que bandejero. Analogía: mueble con ruedas. | Área total de paneles + compartimentos | Carros cerrados, carros de traslado, carros especiales |
| **p-sumidero** | Trazado, Corte Manual, Corte Láser (rejilla/tapa), Plegado, Soldadura (C1-C2), Pulido, QC | G (área) | D | Caja 4 lados soldados → soldadura C1. **Rejilla/tapa superior lleva encaje con soldadura compleja → C2.** No es todo C1. La complejidad de la soldadura depende del tipo de tapa: perforada simple vs rejilla con encaje. | Área planta (mm²) | Sumideros, canaletas, tapa-registro |
| **p-lavadero** | Trazado, Corte Manual, Plegado profundo (taza), Soldadura (2 personas), Pulido, QC | C (número de tazas) + G | X | **Discriminante clave: taza fabricada en planta, NO comprada.** Soldadura requiere 2 personas. Plegado de taza es profundo con operadores extra. Productos con taza comprada → reclasificar a p-meson. | Número de tazas × profundidad | Lavaderos fabricados (ZLLE-0128, ZLLE-0260). NO incluye: lavamanos, ZLLCA-1800, BAMTE-1400 (→ p-meson) |
| **p-laser** | Diseño (HH diseñador), Corte Láser, Soldadura (puede existir), QC | X (geometría compleja, no ortogonal) + D (espesor → velocidad corte) | G (área) | **Discriminante: complejidad geométrica del diseño, NO volumen de soldadura.** Formas no ortogonales, curvas, siluetas complejas. Espesor define velocidad de corte y potencia requerida. Tiempo diseñador = costo HH oculto no capturado en templates actuales. Puede llevar soldadura si el ensamble lo requiere. | Complejidad geométrica × espesor × área | Tostador, bandejas perforadas complejas, láminas con diseño, piezas con silueta no estándar |
| **p-electrico** | Trazado, Plegado, Soldadura, Comp. Eléctrico/Térmico, QC (prueba térmica) | C (componentes calor) | G | Cuerpo fabricado en planta + sistema de calor instalado: resistencias, termostatos, o gas/fluido indirecto (baño maría). **No confundir con p-cocina-gas** — p-electrico es calor indirecto/resistivo, nunca fuego directo. Baños maría con gabinete → p-importado. | Número de resistencias / secciones | Baños maría fabricados (sin gabinete), salseras calefaccionadas, mesas calientes |
| **p-campana** | Trazado, Corte Manual, Corte Láser (rejillas), Plegado (2+ operadores siempre), Soldadura, Pulido, Comp. Eléctrico, QC | G (área lámina m²) | componentes fijos (filtros, motor, focos) | Materiales laminales (no perfiles ni patines). Plegado SIEMPRE C2+ (cuerpo >1m, 2+ operadores, calce de precisión). Componentes comprados fijos no escalan con dimensión — modelo requiere dos componentes separados: (a) lámina × área, (b) componentes fijos por modelo. | Largo (metros) — para lámina. Modelo — para componentes fijos | Campanas murales, campanas centrales |
| **p-refrigerado** | Trazado, Corte Manual, Plegado, Soldadura, Pulido, Refrigeración, Comp. Eléctrico, QC | C (circuitos, componentes) | G | **Discriminante: fabricado en planta (proyecto especial).** Importados → p-importado. **El cuerpo NO es un mesón con frío añadido** — es un sistema integrado desde el diseño. Los componentes internos (frío o calor) condicionan toda la fabricación del cuerpo. Se estudia como sistema completo. Proceso refrigeración domina (~10 días). | Número de puertas/circuitos | Mesones refrigerados fabricados, vitrinas refrigeradas fabricadas — NO incluye mesón simple con frío instalado |
| ~~**p-celosia**~~ | ~~DIVIDIDO~~ | — | — | **DIVIDIDO** — celosías/rejillas y barandas tienen lógica de corte y proceso distintos. Ver B1-Q7. | — | — |
| **p-rejilla** *(ex p-celosia)* | Trazado, Corte Manual (varillas múltiples), Soldadura C2-C3, Pulido, QC | C (densidad varillas) × G (área) | X (multiples_uniones) | Patrón de varillas soldadas en cuadrícula. Soldadura domina — muchos puntos de unión, patrón repetitivo. Sin plegado de lámina. | Área panel m² × densidad varillas | Celosías, rejas decorativas/funcionales, protección escalera |
| ~~**p-baranda**~~ | ~~ELIMINADO~~ | — | — | **DISUELTO** — toda baranda depende del proyecto, cada instalación es diferente. No hay ancla ni extrapolación posible. Reclasificar a **p-custom**. | — | — |
| **p-tina** *(nuevo)* | Trazado, Corte Manual, Plegado, Soldadura (doble fondo), Instalación válvulas/llaves, Pulido, QC | C (llaves, válvulas, compartimentos) | G (capacidad litros) | Recipiente industrial rectangular con **doble fondo + llaves/válvulas + ruedas + espesor especial**. Mayor intervención de proceso que lavadero o sumidero. No cabe en ningún perfil existente — tiene materiales, espesor y componentes mecánicos propios. | Capacidad (litros) + número de válvulas | Tinas queseras |
| **p-importado** | QC (inspección), Ensamble mínimo | — | — | No se fabrica en planta. Costo = producto comprado + margen. El nivel de complejidad refleja dificultad de ensamble/instalación | Unidades | Barras apoyo, accesorios importados, equipos refrigerados completos |
| **p-custom** | Variable — depende del proyecto | — | — | Sin perfil estándar. Cotización caso a caso. No extrapolable | — | Rampas, barandas tensoras, proyectos especiales |

---

## 4. Justificación de Complejidad (C1/C2/C3) por `perfil_proceso`

> **Pregunta que responde esta tabla:** ¿Por qué un producto específico entra en C1 vs C2 vs C3 dentro de su perfil?  
> **Estado:** Validado en entrevista con Fabio — sesión 2026-04-13/14. Ver `sessions/INTERVIEW_ANCLAS_SESSION.md` Bloques B2 y B3.

---

### 4.1 p-meson

**Dos ejes independientes:**
- **Tamaño** → `factor_escala` (escala lineal dentro del nivel — no cambia nivel)
- **Partes con mecanismo** → sube nivel (C1 → C2 → C3)

| Nivel | Condición real | Qué tiene | Ancla | SKU |
|-------|---------------|-----------|-------|-----|
| **C1** | Superficie + 4 patas + respaldo. Sin repisa, sin puertas, sin cajones | Cubierta, patas, respaldo | Mesón abierto 900mm | BAMT-0900 |
| **C2** | C1 + repisa inferior u otro elemento, pocos cajones | Agrega repisa → más soldadura, material, pulido cara inferior | Mesón abierto 1900mm repisa | BAMT-1000 |
| **C3** | C2 + puertas correderas + rieles + bisagras + manillas + cajones | Estructura completamente diferente. Componentes mecánicos suman HH. | Mesón 4 cajones 1300mm | BAMTC-1300 |

**Regla:** C1 = soporte simple. C2 = elemento pasivo extra. C3 = mecanismo (puertas, rieles, cajones).  
**El tamaño escala DENTRO del nivel** — mesón C1 de 1800mm = C1 × factor_escala 2×.  
**Ruptura de linealidad:** cuando se agregan repisas, bordes o cajones → no escalar, asignar ancla del nivel superior.

---

### 4.2 p-modulo *(nuevo)*

**Driver:** Número de compartimentos × largo. Plegado dominante (no perfilería).

| Nivel | Condición real | Qué tiene | Ancla | SKU |
|-------|---------------|-----------|-------|-----|
| **C1** | módulo simple de 1 cuerpo , con bandejas y repisas pero sin puertas | — | Modulo De Pan Y Servicios | Audp-0177 |
| **C2** | Módulo 1 cuerpo, sin puertas ni mecanismo | Plegado complejo, cubierta soldada | Módulo Neutro 1000mm | AUMN-1000 |
| **C3** | Salad Bar módulo con capacidad con depositos, cupula sobre cubierta con repisa superior, terminaciones con vidrio | gabinete inferior y pasabandeja | Salad Bar 3 Depositos Full | DuBM4A |

**Regla:** El diseño puede agregar complejidad (geometría no estándar). Sin diseño especial, escala por largo linealmente dentro del nivel.

---

### 4.3 p-laminar-simple *(nuevo, ex p-plancha-simple parcial)*

**Perfil de menor costo del catálogo.** Sin soldadura significativa o con puntos mínimos.

| Nivel | Condición real | Qué tiene | Ancla | SKU |
|-------|---------------|-----------|-------|-----|
| **C1** | Corte + 1-2 dobleces. Sin soldadura o soldadura puntual mínima | Lámina plana o con doblez simple | Cubrejunta | cuj-100 |
| **C2** | tiene dobleces, detalles minimos, un plegado y soldadura, y tiene pulido| tiene plegado, y un tubo soldado en la base | pala-de-basura-pl-030|
| **C3** | N/A | — | — | — |

**Regla:** Escala linealmente por metros lineales. tiene rupturas de linealidad — si aparece soldadura compleja o mecanismo

---

### 4.4 p-cocina-gas *(nuevo)*

**Driver principal:** Número de quemadores / secciones de cocción.

| Nivel | Condición real | Qué tiene | Ancla | SKU |
|-------|---------------|-----------|-------|-----|
| **C1** | 1 quemador, sin horno | Cuerpo base + 1 quemador + manifold simple | Anafe 1 quemador | 1PQ |
| **C2** | 3-4 quemadores sin horno, o 2Q con componente adicional (plancha) | Manifold múltiple, más soldaduras, planificación | Cocina 4Q sin horno | 4PQN |
| **C3** | 6+ quemadores, o cualquier quemador con horno | Horno = salto estructural real. Cambia la complejidad de planificación y fabricación | Cocina 6Q + churrasquera | 6PQCH |

**Regla:** El incremento por quemador es el mismo dentro del nivel (lineal). El horno es una ruptura de linealidad — no escalar, asignar ancla del nivel superior.  
**⚠️ Pendiente:** Validar tiempos de instalación de gas con técnico especialista.

---

### 4.5 p-cilindrico

**Driver:** Capacidad (litros) o diámetro. Espesor define proceso cilindrado.

| Nivel | Condición real | Qué tiene | Ancla | SKU |
|-------|---------------|-----------|-------|-----|
| **C1** | Capacidad <5L, ø ≤ 200mm, 1mm | Cilindrado simple, 1 operador, pulido pequeño | Poruña 1KG (ø130mm) | POR-1000 |
| **C2** | Capacidad 5-30L, ø 200–400mm, 1-1.5mm | Cilindrado C2. Pulido en curva +30% vs plano | Balde 20L | BLDS-300 |
| **C3** | Capacidad >30L con mecanismo eléctrico o espesor especial | Resistencia o termostato dentro del cuerpo cilíndrico. Proceso cambia de naturaleza. | Hervidor 20L eléctrico | AUHA-0157 |

**Regla:** Escala linealmente por litros dentro del mismo nivel y espesor. Si agrega mecanismo eléctrico → C3. Si supera ~30L sin mecanismo, evaluar si migra a p-basurero-cil.

---

### 4.6 p-basurero-rect

**Dos ejes independientes que suman complejidad:**
- **Terminación de pulido** — `vibrado` (rápido, lijadora, menos insumos) vs `semi-brillante` (chascon + rodillo, más pasadas). Brillante = **no se hace en Dulox** (demasiado costoso).
- **Mecanismo** — sin mecanismo / tapa simple vs pedal / vaivén / gabinetes interiores.

| Nivel | Condición real | Pulido | Mecanismo | Ancla | SKU |
|-------|---------------|--------|-----------|-------|-----|
| **C1** | Caja con tapa simple, terminación vibrado | Vibrado mínimo | Tapa sin mecanismo | Basurero simple | brpa-0500 |
| **C2** | Caja con mecanismo (vaivén o pedal), vibrado | Vibrado | Pedal o vaivén | Basurero rect estándar | bm 0700 |
| **C3** | Terminación semi-brillante + mecanismo pedal/vaivén + puertas | Semi-brillante (3 pasadas, 5hrs) | Pedal + gabinetes interiores | Basurero Reciclaje 4 Comp. | BARE4-01300 |

**Regla:** Pulido siempre domina el costo. La terminación es independiente del mecanismo — un basurero rect puede ser C3 solo por terminación aunque estructuralmente sea simple.  
**Flag nuevo requerido:** `terminacion` = `vibrado` | `semi-brillante` — capturar por producto.

---

### 4.7 p-basurero-cil

**Driver complejidad:** Mecanismo (tapa con pedal/vaivén). Pulido siempre C3 en curva.

| Nivel | Condición real | Mecanismo | Ancla | SKU |
|-------|---------------|-----------|-------|-----|
| **C1** | Cilindro sin mecanismo de tapa | Sin mecanismo | Cenicero (forma más simple) | CEN-0650 |
| **C2** | Cilindro con mecanismo (pedal, vaivén) | Pedal o vaivén en tapa | Con pedal | BAPLA-0470 |
| **C3** | N/A en catálogo actual — candidato: basurero cil muy grande o doble cuerpo | — | Pendiente | — |

**Regla:** Pulido es **siempre C3** independiente del nivel global (curva = +30% tiempo vs plano, multipasadas). El nivel global captura la complejidad estructural/mecanismo, no el costo del pulido.  
**Escala lineal** dentro del mismo nivel y terminación por capacidad (litros).

---

### 4.8 p-carro-bandejero *(nuevo)*

**Driver principal:** Número de niveles de bandejas. Driver secundario: largo.

| Nivel | Condición real | Qué tiene | Ancla | SKU |
|-------|---------------|-----------|-------|-----|
| **C1** | 10-12 bandejas, estructura abierta | Perfilería + niveles sin cierre | Carro 12 bandejas | AUCB-0178 |
| **C2** | 22-24 bandejas o estructura más larga | Más niveles = más material, soldadura, pulido | Carro 24 bandejas | AUCB-0810 |
| **C3** | Carro cerrado (con paredes/puerta) de cualquier capacidad | Paneles laterales + puerta = lógica constructiva diferente | Carro bandejero cerrado 8 bandejas | AUCB-0790 |

**Regla:** El incremento por nivel es el mismo (lineal) dentro de la misma estructura. Carro cerrado es ruptura de linealidad — no escalar desde abierto, ancla propia.

---

### 4.9 p-carro-traslado *(nuevo)*

**Driver:** Número de compartimentos + puertas/mecanismo.

| Nivel | Condición real | Qué tiene | Ancla | SKU |
|-------|---------------|-----------|-------|-----|
| **C1** | carro traslado simple  RUEDAS (DELANTERA GIRATORIA), Y RODILLOS SUPERIORES PARA DESLIZAR LA BANDEJA. | Carro Porta Cadaver | 
 | — |
| **C2** | Carro cerrado, 1 compartimento, sin puertas activas o con 1 puerta simple | Paneles + ruedas industriales | Carro para traslado | CATR-0800 |
| **C3** | RUEDAS DE ALTO TRAFICO, CAPACIDAD TOTAL DE 100 LTS DE AGUA, TERMOSTATO DE REGULACIÓN carro con múltiples compartimentos, cajones y puertas | Cajones + divisiones + mecanismo | Carro Limpiador De Filtros | — |

**Regla:** Escala por área de paneles + número de compartimentos. Cajones y puertas son rupturas de linealidad.

---

### 4.10 p-sumidero

**Cuerpo:** siempre C1 independiente del tamaño — escala linealmente con factor_escala.  
**La tapa/rejilla superior** determina el nivel de complejidad en soldadura.

| Nivel | Condición real | Tapa | Soldadura | Ancla | SKU |
|-------|---------------|------|-----------|-------|-----|
| **C1** | Cuerpo + tapa perforada láser | Corte láser, encaje simple | C1 | Sumidero tapa perforada 400mm | SUMVE-0400 |
| **C2** | Cuerpo + rejilla de pletinas soldadas | Pletinas cortadas + encaje + soldadura por unión | C2 — muchos puntos de unión | Sumidero con rejilla | SUMHO-0200 |

**Regla:** El cuerpo no determina la complejidad — la tapa sí. Escala lineal del cuerpo por área de planta.

---

### 4.11 p-lavadero

**Dos drivers que suben complejidad:**
- **Número de tazas** fabricadas en planta
- **Profundidad de taza** (más profundidad = plegado más complejo, más personas en soldadura)

| Nivel | Condición real | Tazas | Plegado | Ancla | SKU |
|-------|---------------|-------|---------|-------|-----|
| **C1** | taza fabricada con patas y repisas, con grifo, otro producto: urinario | 1 taza, profundidad estándar | Plegado C1, 1 operador | Lavadero De 1200Mm  | Zllca-0111 |
| **C2** | 4 puestos de trabajo | 2 tazas o mayor profundidad | Plegado C2. Soldadura C2 (2 personas) | Lavadero 4 puestos | ZLLE-0128 |
| **C3** | 8 puestos de trabajo | 4+ tazas. Peso extremo → más operadores en pulido, soldadura, traslado, | Plegado+Soldadura C3. Corrección manual por peso | Lavadero Para Diálisis / Lds-055| Zlle-0260

**Regla:** Escala aproximadamente lineal por número de puestos dentro del nivel. El peso extremo en C3 requiere corrección manual (más operadores, no más tiempo de máquina).  
**Discriminante clave:** Taza **fabricada en planta** — taza comprada → clasificar como p-meson.

---

### 4.12 p-laser

**Driver:** Complejidad geométrica del diseño (HH diseñador) + espesor (velocidad corte + potencia).

| Nivel | Condición real | Qué determina | Ancla | SKU |
|-------|---------------|--------------|-------|-----|
| **C1** | N/A — las piezas geométricamente simples van a p-laminar-simple | — | — | — |
| **C2** | Geometría no ortogonal, curvas, siluetas complejas. DXF existe o se crea. | Tiempo HH diseñador + tiempo máquina según espesor | Tostador | TOST-01 |
| **C3** | N/A — piezas de espesor >8mm o geometría extrema → externas | — | — | — |

**Regla:** Sin DXF → +30min setup adicional. Espesor 1mm→3mm = 3-4× tiempo de corte. Espesor >8mm = externalización.  
**⚠️ Gap crítico:** Tiempo HH diseñador no está capturado en ningún template actual — es costo real no modelado.

---

### 4.13 p-electrico

**Driver:** Número de depósitos/secciones calefaccionadas + tipo de componentes térmicos.

| Nivel | Condición real | Qué tiene | Ancla | SKU |
|-------|---------------|-----------|-------|-----|
| **C1** | plancha churrasqeura simple | 1 resistencia simple | plancha-electrica-encimera-pce-550 |
| **C2** | 2-3 depósitos, componentes eléctricos básicos, sin gabinete | Resistencias + termostato + cableado | Baño María 3 depósitos Full | DUBM3 |
| **C3** | 4+ depósitos o salsera grande con gabinete + puertas | Múltiples circuitos. Gabinete agrega complejidad estructural | Salsera grande con gabinete | Salsera 6 Depositos Sc6 |

**Regla:** No confundir con p-cocina-gas — p-electrico es calor indirecto/resistivo, nunca fuego directo. Baños maría con gabinete completo → p-importado (no fabricado en planta).

---

### 4.14 p-campana

**Dos ejes independientes:**
1. **Extractor** — sin motor vs con motor. Salto C1→C2.
2. **Largo** — mayor largo requiere más operadores y estructura diferente. Salto C2→C3.

| Nivel | Componentes | Largo | Operadores | Ancla | SKU |
|-------|------------|-------|-----------|-------|-----|
| **C1** | Sin extractor (decorativa, filtro de campana) | Cualquiera | 1 | |
| **C2** | Con extractor (motor) | Estándar | 2 | Campana mural 1500mm | CCCM-1510 |
| **C3** | Con extractor + largo grande (capacidad 3+ operadores) | Grande | 3+ | Campana central 3000mm | CCCI-3013 |

**Regla:** Plegado **siempre C2+** — cuerpo >1m requiere 2+ operadores para calce de precisión.  
**⚠️ Componentes comprados fijos** (filtros $111.200 = 43% costo en CCCM-2010) — no escalan con largo. Modelo necesita dos ecuaciones: (a) lámina × área, (b) componentes fijos por modelo.

---

### 4.15 p-refrigerado

**Driver:** Complejidad del sistema de frío — circuitos, componentes, planificación integrada.

| Nivel | Condición | Driver | Ancla | SKU |
|-------|-----------|--------|-------|-----|
| **C1** | Pendiente — confirmar si existe en catálogo fabricado | — | — | — |
| **C2** | Sistema estándar, 1 circuito | Planificación simple. ~10 días proceso refrigeración | — | — |
| **C3** | Sistema complejo, múltiples circuitos, mayor planificación | Mayor planificación + mecanismo más complejo | Mesón shop refrigerado | MPSC-1400 |

**Regla:** El cuerpo **no es un mesón con frío añadido** — es un sistema integrado desde el diseño. Los componentes internos condicionan toda la fabricación. Proceso refrigeración domina (~10 días).  
**⚠️ Pendiente:** Validar C1 y umbrales C2/C3 en sesión con técnico frigorista.

---

### 4.16 p-rejilla *(ex p-celosia)*

**Driver:** Área del panel × densidad de varillas/pletinas. Soldadura domina.

| Nivel | Condición real | Soldadura | Ancla | SKU |
|-------|---------------|-----------|-------|-----|
| **C1** | N/A — catálogo actual. Candidato: rejilla perforada simple sin pletinas soldadas | C1 | Pendiente | — |
| **C2** | Rejilla estándar: varillas en cuadrícula, densidad media | C2 — muchos puntos de unión en patrón repetitivo | Celosía 500×200mm | CELL-0500 |
| **C3** | N/A — catálogo actual. Candidato: rejilla curva o de alta densidad | C3 — soldaduras complejas no ortogonales | Pendiente | — |

**Regla:** Barandas → siempre p-custom (cada instalación depende del proyecto, no hay ancla posible). Escalera piscina → p-rejilla si es rejilla estándar.

---

### 4.17 p-tina *(nuevo)*

**Driver:** Capacidad (litros) + número de válvulas/llaves + mecanismo (ruedas, doble fondo).

| Nivel | Condición real | Qué tiene | Ancla | SKU |
|-------|---------------|-----------|-------|-----|
| **C1** | N/A — catálogo actual. Candidato: tina quesera pequeña <50L | — | Pendiente | — |
| **C2** | Tina con doble fondo + llaves + ruedas, capacidad media | Doble fondo soldado, válvulas de vaciado, espesor especial | Tina quesera 100L | EITQ-0100 |
| **C3** | N/A — catálogo actual. Candidato: tina >300L o con prensa integrada | — | Pendiente | — |

**Regla:** Más compleja que p-lavadero — materiales distintos (espesor doble fondo), llaves, movilidad. Escala por litros dentro del mismo nivel de mecanismo.  
**Umbral pendiente:** ¿A qué litros se pasa de C1 a C2? EITQ-0100 (100L) es C2 — C1 debe estar entre 30-80L.

---

## 5. Regla de Oro: Global vs. Per-Process Complejidad

```
complejidad (columna CSV)  =  complejidad GLOBAL de la estructura del producto
                           ≠  complejidad del proceso más costoso

Un basurero puede ser globalmente C1 (estructura simple)
pero tener Pulido C3 (5 horas, 3 pasadas).

→ Para costeo: usar el vector per-proceso [k₁...k₁₁]
→ Para pricing: usar el tier global como factor de ajuste de margen
```

**Implicación:** El campo `complejidad` en el CSV es una señal de estructura, no de costo. No confundirlos.

---

## 6. Criterios para un Producto Ancla (Anchor)

Un producto ancla es el **punto de referencia medido** desde el cual se extrapola el resto de su familia.

**Criterios para ser ancla:**
1. **Representativo** — es el caso "más típico" del perfil, no el extremo
2. **Medible** — tiene dimensiones conocidas, BOM documentado, puede cronometrarse
3. **Estable** — se fabrica regularmente (no es un proyecto único)
4. **No-ambiguo** — su proceso es claro, sin variantes que confundan la medición
5. **Calibrable** — se puede volver a medir si los datos son inconsistentes

**Un ancla por nivel (C1, C2, C3) es el ideal.** Si un nivel no existe en la realidad del catálogo, documentarlo como "N/A" con razón.

---

## 8. Reglas de Extrapolación

### Regla general

```
Costo(producto X) = Costo(ancla ki) × factor_escala(driver)

factor_escala = valor_driver(X) / valor_driver(ancla)
```

### Escala lineal — aplicar directamente

| Perfil | Driver de escala |
|--------|----------------|
| p-meson | Largo (mm) — dentro del mismo nivel |
| p-campana (lámina) | Largo (mm) |
| p-basurero-rect | Área superficial (mm²) |
| p-cilindrico | Capacidad (litros) |
| p-cocina-gas | Número de quemadores — mismo incremental |
| p-carro-bandejero | Número de niveles — mismo incremental |
| p-lavadero | Número de puestos — aproximadamente lineal |

### Rupturas de linealidad — tratar por separado

| Tipo | Perfil afectado | Solución |
|------|----------------|---------|
| **Componentes comprados fijos** | p-campana (filtros, motor, focos) | Ecuación separada: costo_lamina × area + costo_componentes_fijos |
| **Partes/mecanismo nuevo** | p-meson (cajones, rieles), p-basurero-rect (pedal), p-basurero-cil (vaivén) | No escalar — asignar ancla del nivel superior |
| **Horno en cocina** | p-cocina-gas | Salto de nivel, no incremental |
| **Peso extremo** | p-lavadero (8 puestos) | Corrección manual: más operadores en soldadura, plegado, pulido |
| **Terminación diferente** | p-basurero-rect (vibrado vs semi-brillante) | Factor de terminación: semi-brillante ≈ 1.5-2× vs vibrado |

---

## 9. Anclas Definitivas por perfil_proceso × ki
| perfil_proceso | C1 ancla (propuesto) | C2 ancla (propuesto) | C3 ancla (propuesto) |
|---|---|---|---|
| p-meson | Mesón abierto 900×600×860mm, 1mm (BAMT-0900) | Mesón cerrado 1000mm (BAMT-1000) | Mesón De Trabajo 4 Cajones + Repisa / Bamtc-1300 |
| p-laminar-simple | cuj-100 | espatula-plancha-plana-espl-001 | 40 |
| p-modulo | Modulo De Pan Y Servicios \| Audp-0177 | Módulo Neutro/ Aumn-1000 | Modulo Salad Bar Capacidad Para 3 Depósitos Full |
| p-cocina-gas | Plancha gas 2Q | 4PQN | 6PQCH |
| p-campana | N/A | Campana mural 2000mm (CCCM-2010) | Campana central 3000mm (CCCI-3013) |
| p-cilindrico | Poruña 1KG (POR-1000) | Balde 20L blds 300 | hervdor elecetrico 20lts/ auha-0157 |
| p-basurero-rect | basurero-reciclaje-puerta-abatible-brpa-0500 | mall simple bm 0700 | BARE4-01300 |
| p-basurero-cil | Cenicero CEN-0650 | Basurero plaza bapla-0470 | N/A |
| p-carro-bandejero | Carro 12 bandejas AUCB-0178 | Carro bandejero 24 bandejas Aucb-0810 | Carro bandejero AUCB-0790 |
| p-carro-traslado | carro-porta-cadaver | Carro Para Traslado / Catr-0800 | carro-limpiador-de-filtros |
| p-lavadero | Lavadero De 1200Mm / Zllca-0111 | Lavadero De 4 Puestos De Trabajo / Zlle-0128 | Lavadero 8 puestos ZLLE-0260 |
| p-tina | Tina Quesera Capacidad 100 Litros /Eitq-0100 | | |
| p-sumidero | SUMVE-400 \| SUMIDERO 400 CON TAPA PERFORADA | Sumidero Con Rejilla / Sumho-0200 | N/A |
| p-laser | N/A | letras-armadas-de-acero-inoxidable | — (externo) |
| p-rejilla | CELOS IA 500x200mm - CELL-0500 | | |
| p-electrico | plancha-electrica-encimera-pce-550 | Baño Maria 3 Depositos Full / Dubm3 | Salsera 6 Depositos Sc6 |
| p-refrigerado | Mesón refrigerado MPSC-1400 | | |


---

## 10. Productos Reclasificados — Correcciones al CSV

| Producto | Perfil anterior | Perfil correcto | Razón |
|---------|----------------|----------------|-------|
| Escurridor de servicios | p-cilindrico | p-importado | No fabricado en planta |
| Espátula | p-cilindrico | p-laminar-simple | Pieza plana, no cilíndrica |
| Hervidores agua y leche (pequeños) | p-cilindrico | p-importado | No fabricados en planta |
| Servilletero | p-cilindrico | p-custom | Depende del modelo/proyecto |
| Tina quesera | p-cilindrico | p-tina | Doble fondo, válvulas, espesor especial, móvil |
| Molde queso cuadrado | p-cilindrico | p-laminar-simple | Caja plegada simple + anillo, poca soldadura |
| Baño maría con gabinete | p-electrico | p-importado | No fabricado en planta |
| ZLLCA-1800, BAMTE-1400, ZLLCA-0103, lavamanos | p-lavadero | p-meson | Taza comprada, no fabricada en planta |
| Módulos neutros, módulos de servicio, salad bar | p-meson | p-modulo | Plegado dominante, más pasos de fabricación |
| Mesón refrigerado | p-meson | p-refrigerado | Sistema integrado desde diseño |
| Barandas (todas) | p-celosia / p-custom | p-custom | Cada instalación depende del proyecto |
| Carros (todos) | p-carro | p-carro-bandejero o p-carro-traslado | p-carro era demasiado amplio |
| Celosías / rejillas | p-celosia | p-rejilla | Renombrado + separado de barandas |
| Planchas gas, anafes, cocinas industriales | p-plancha-simple | p-cocina-gas | p-plancha-simple era cajón de sastre |
| Cubrejunta, zócalo, peinazo, moldura, marcos | p-plancha-simple | p-laminar-simple | Perfil correcto — sin soldadura compleja |
| Grifería, cortadora papas PIPP, filtros campana, perol sopas | p-plancha-simple | p-importado | No fabricados en planta |
| Repisas, mesas desueradoras | p-plancha-simple | p-meson | Misma lógica constructiva |

---

## 11. Pendientes de Resolución

> Todos los pendientes de la sesión 2026-04-13/14 fueron resueltos por Fabio directamente. Ver `sessions/INTERVIEW_ANCLAS_SESSION.md` Bloque B3 y actualizaciones al CSV maestro.

| # | Pendiente | Estado |
|---|-----------|--------|
| 1 | SKU exacto de cubrejunta para ancla p-laminar-simple C1 | ✅ Resuelto |
| 2 | SKU exacto de salsera grande para ancla p-electrico C3 | ✅ Resuelto |
| 3 | SKU exacto de mesón gabinete con puertas + cajones para p-meson C3 | ✅ Resuelto — BAMTC-1300 |
| 4 | Umbrales en litros para p-tina C1 y C3 | ✅ Resuelto |
| 5 | Validar p-refrigerado C1 y C2 con técnico frigorista | ✅ Resuelto |
| 6 | Anclas C1 y C3 de p-rejilla — catálogo actual no las tiene | ✅ Resuelto |
| 7 | Anclas C1 y C3 de p-modulo — catálogo actual no las tiene | ✅ Resuelto |
| 8 | Ancla C1 de p-carro-traslado | ✅ Resuelto |
| 9 | Ancla C1 y C3 de p-tina | ✅ Resuelto |

---

## 12. Decisiones y Preguntas Abiertas

1. **p-meson C2:** Resuelto — C2 = elemento pasivo extra (repisa). C3 = mecanismo (puertas, cajones). Anclas confirmadas en B3.
2. **p-cilindrico C3:** Resuelto — C3 = cilindro con mecanismo eléctrico (AUHA-0157). Sin mecanismo y >30L → evaluar migración a p-basurero-cil.
3. **p-basurero-cil C1:** Resuelto — CEN-0650 es C1. Pulido siempre C3 en curva, pero el nivel global captura estructura/mecanismo.
4. **p-sumidero C2:** Resuelto — C2 existe cuando la rejilla es de pletinas soldadas (SUMHO-0200).
5. **p-rejilla C1:** Abierto — catálogo actual no tiene rejilla C1 simple. Crear cuando aparezca producto.
6. **p-basurero-rect anchors:** Resuelto — ancla = producto más representativo del proceso (no necesariamente el más vendido). BM-0700 para C1, BARE4-01300 para C3.
7. **p-importado y la estrategia futura de ensamble:** El campo C1/C2/C3 en p-importado hoy captura dificultad de instalación/ensamble final. La hipótesis es que Dulox podría evolucionar hacia un modelo **ensamblador**: importar piezas y soldar/integrar en productos terminados propios. En ese escenario, p-importado dejaría de ser terminal — los productos pasarían a tener un perfil de fabricación real con el componente importado como insumo. **El campo `complejidad` en p-importado debe interpretarse hoy como señal de ensamble, y en el futuro como punto de partida para definir el perfil de fabricación del ensamble.**

---

*Documento validado en entrevista completa 2026-04-13/14. El CSV maestro de referencia es `dataset/Productos y Clasificaciones - Productos.csv`.*
