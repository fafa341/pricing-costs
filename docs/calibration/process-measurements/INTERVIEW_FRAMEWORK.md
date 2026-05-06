# Expert Knowledge Interview Framework
## Dulox Manufacturing — Extracción y Validación de Conocimiento de Procesos

> **Propósito primario:** Extraer conocimiento tácito experto en reglas estructuradas y consultables.  
> **Propósito secundario:** Detectar y corregir cuando la realidad de producción diverge de los supuestos del modelo.  
> **Output:** RAG-ready chunks → `knowledge-chunks.jsonl` | Correcciones → chunks supersede  
> **A quién entrevistar:** Hernán (Jefe de Producción), operadores de soldadura, operador de pulido, técnico de frío

---

## Core Principle

You are not collecting opinions. You are extracting **decision rules** — the logic an expert applies when they decide:
- Which method to use
- How long a job will take
- What materials/consumables are needed
- When something becomes harder/more expensive

Every answer should convert to the form:

> **IF** [condition] **THEN** [consequence] [magnitude if possible]

---

## Five Question Types

### Type A — Trigger Questions
Uncover the conditions that activate a change in method or complexity.

| Pattern | Example |
|---------|---------|
| "When does X become necessary?" | "¿Cuándo es necesario hacer más de una pasada en pulido?" |
| "At what point do you change how you do this?" | "¿En qué punto cambias de corte manual a láser?" |
| "What conditions make this process harder?" | "¿Qué hace que una soldadura sea difícil?" |

**Goal:** Get a threshold (number, count, or category).

---

### Type B — Comparison Questions
Uncover what distinguishes low-complexity from high-complexity jobs.

| Pattern | Example |
|---------|---------|
| "Two similar products — what makes one cost more?" | "Dos mesones del mismo tamaño, ¿qué hace que uno tome el doble en soldar?" |
| "What's the difference between simple vs complex [process]?" | "¿Qué diferencia hay entre un pulido simple y uno complejo?" |
| "When is [product A] more expensive than [product B] despite being smaller?" | "¿Por qué una poruña puede costar más en consumibles que un mesón de 1.5m?" |

**Goal:** Identify the non-obvious cost drivers.

---

### Type C — Threshold Extraction
Push for specific numbers after a qualitative answer.

| Follow-up pattern | Example |
|------------------|---------|
| "You said thicker — at what mm?" | "Dijiste que el espesor afecta — ¿a partir de qué mm cambia la técnica?" |
| "How many [X] before it becomes complex?" | "¿Cuántos puntos de soldadura antes de que consideres el trabajo complejo?" |
| "What area/size is the cutoff?" | "¿Qué superficie es el punto donde necesitas 2 operadores en pulido?" |

**Goal:** Convert qualitative judgment into a number range for threshold calibration.

---

### Type D — Cause → Effect Mapping
Force explicit causal chains to capture non-linear relationships.

| Pattern | Example |
|---------|---------|
| "If X increases, what changes?" | "Si el espesor pasa de 1mm a 3mm, ¿qué cambia en soldadura? ¿Y en corte?" |
| "If you double [dimension], does cost double?" | "Si duplicas el largo de un mesón, ¿el tiempo de pulido se duplica también?" |
| "What's the relationship — proportional or worse?" | "¿El tiempo de soldadura crece proporcional al número de uniones, o más que eso?" |

**Goal:** Identify linear vs. non-linear scaling for each process × driver combination.

---

### Type E — Exception Probing
Capture the highest-value knowledge: when the normal rules break down.

| Pattern | Example |
|---------|---------|
| "When does your usual rule NOT apply?" | "¿Cuándo tu regla habitual para pulido no funciona?" |
| "What product surprised you with how long it took?" | "¿Qué producto te sorprendió porque tomó mucho más de lo esperado?" |
| "What looks simple but is actually complex? Why?" | "¿Qué producto parece simple pero es complicado de fabricar?" |
| "What's the worst case for [process]?" | "¿Cuál es el caso más difícil que has visto para soldadura?" |

**Goal:** Find the edge cases that would break a naive model.

---

## Process-Specific Question Banks

### Pulido y Terminación
*Key insight: most non-linear process. Consumables dominate, scale superlinearly with surface area.*

1. ¿Cuántas pasadas tiene un pulido estándar? ¿Y el máximo que has hecho?
2. ¿Cuándo necesitas 3 pasadas vs 1?
3. ¿Qué herramienta usas en cada pasada? (desbastes, gratas, traslapos, multifinic)
4. ¿Una superficie curva (cilindro) toma más o menos tiempo que una plana del mismo área?
5. ¿Qué pasa con zonas de difícil acceso — rincones, ángulos? ¿Cuánto tiempo extra?
6. ¿A qué área de superficie necesitas 2 operadores para el pulido?
7. ¿El logo o grabado afecta el pulido? ¿Cómo?
8. ¿Cuándo usas pasta de pulir vs disco seco?
9. Exception: ¿Qué producto parece fácil pero tiene un pulido difícil? ¿Por qué?
10. Si tienes un mesón 1.5m vs 3m, ¿el tiempo de pulido se duplica?

---

### Soldadura
*Key insight: joint count is primary driver. Visibility of weld determines finish quality requirement.*

1. ¿Cuántos puntos de unión considera una soldadura simple vs compleja?
2. ¿Qué diferencia hay entre soldar una esquina visible vs una esquina interior?
3. ¿Cuándo necesitas emplantillar (usar una plantilla de posicionamiento)?
4. ¿A qué espesor cambias de TIG a otro método?
5. ¿El argón que usas escala con el tiempo de arco, o hay otro factor?
6. ¿Qué es peor: 10 uniones simples o 3 uniones en zona de difícil acceso?
7. Para una celosía con 20 cruces de varilla, ¿cómo calculas el tiempo?
8. ¿Una soldadura de cierre (fondo de basurero) toma lo mismo que una de esquina?
9. Exception: ¿Cuándo la soldadura tarda mucho más de lo esperado?
10. ¿El calibre del tungsteno cambia según el espesor? ¿A qué punto?

---

### Plegado
*Key insight: number of bends × piece length × espesor combination. Long pieces need repositioning.*

1. ¿Cuántos dobleces tiene un plegado simple vs complejo?
2. ¿A qué largo de pieza necesitas reposicionar en la plegadora?
3. ¿El espesor afecta el tiempo de plegado? ¿O solo la fuerza necesaria?
4. ¿Cuándo necesitas verificar el ángulo con goniómetro vs a ojo?
5. ¿Piezas con dobleces de retorno (ángulos cerrados) toman más tiempo? ¿Cuánto más?
6. Exception: ¿Qué plegado te ha dado más problemas? ¿Por qué?

---

### Cilindrado
*Key insight: diameter + length + thickness. Thin material springs back.*

1. ¿Cuántas pasadas necesita un cilindrado estándar?
2. ¿A qué diámetro es más difícil — muy pequeño o muy grande?
3. ¿El espesor de la lámina afecta la cantidad de pasadas?
4. ¿Una campana cilíndrica toma lo mismo que un cuerpo de basurero?
5. Exception: ¿Cuándo el cilindrado sale mal y hay que rehacer?

---

### Corte Manual vs Corte Láser
*Key insight: method selection threshold based on geometry complexity and thickness.*

1. ¿Cuándo decides usar láser en lugar de corte manual?
2. ¿Hay un espesor máximo para láser?
3. ¿Para series pequeñas (1–2 piezas), cuándo vale la pena ir a láser?
4. ¿Cuánto tiempo tarda corte manual por metro lineal en 1mm? ¿En 3mm?
5. ¿Una perforación circular se corta con manual o láser? ¿A qué diámetro mínimo?
6. Exception: ¿Cuándo el láser falla o no sirve para el trabajo?

---

### Trazado
*Key insight: plano complexity + repetition. Templates reduce time dramatically.*

1. ¿Cuánto tiempo toma trazar un producto nuevo vs uno repetido?
2. ¿Cuándo usas plantilla vs mides desde cero?
3. ¿El trazado escala con el tamaño de la pieza?
4. ¿Qué producto tiene el trazado más complicado? ¿Por qué?

---

### Control de Calidad
*Key insight: what checks are done and for which products. When is a product rejected.*

1. ¿Qué verificas siempre en QC (para todos los productos)?
2. ¿Qué verificas solo para ciertos productos?
3. ¿Cuándo rechazas un producto y lo mandas a rehacer?
4. ¿Cuánto tiempo toma QC para el producto más complejo que has visto?
5. ¿El embalaje es parte de QC? ¿Cuánto tiempo agrega?

---

## Interview Output Template (per session)

At end of each interview session, record:

```
Session ID: [interviewer]-[date]  e.g. hernan-2026-04-15
Expert: [name, role]
Processes covered: [list]
Chunks generated: [count]
Flagged for verification: [list any contradictions or uncertain numbers]
Next session: [what's missing]
```

---

## Converting Raw Answers to Chunks

### Raw answer:
> "Cuando el producto tiene muchos puntos de soldadura, como más de 8 o 10, hay que emplantillar, eso toma más tiempo al inicio pero se compensa en la ejecución."

### Extracted chunks (2 from this one answer):

**Chunk 1:**
```
TEXT: "For products with more than 8–10 weld joints, fixturing (emplantillado) becomes necessary. This increases setup time but reduces execution variance."
EMBEDDING_TEXT: "Weld joint count above 8-10 requires fixturing, increasing setup time."
METADATA: { process: "soldadura", threshold_type: "complexity_boundary", dimension_type: "count", complexity_level: "C2", impact_type: "time", scaling: "step_function", confidence: "expert_estimate" }
```

**Chunk 2:**
```
TEXT: "Emplantillado adds significant T_setup to soldadura but reduces execution time per joint and improves repeatability."
EMBEDDING_TEXT: "Soldadura fixturing increases setup time, reduces per-joint execution time."
METADATA: { process: "soldadura", threshold_type: "rule", impact_type: "time", scaling: "fixed", confidence: "expert_estimate" }
```

**Rule:** One answer → multiple chunks if it contains multiple independent facts.

---

## Quality Checklist per Chunk

Before marking a chunk as `confianza: "estimacion_experto"` (vs `"heuristica"`), verify:

- [ ] The expert gave a specific number OR confirmed a range
- [ ] The answer was about their own shop (not general industry knowledge)
- [ ] No hedging like "I think" or "usually" without qualification
- [ ] If a number was given, ask once: "¿Ese número es de medición o estimado?"

---

## Metodología de Validación y Limpieza de Supuestos

> **El problema:** Los chunks iniciales se generan de entrevistas y estimaciones. Con el tiempo, los procesos se optimizan, cambian herramientas, llegan nuevos materiales, o simplemente el supuesto original era incorrecto. Este framework define cómo detectar y corregir esa deriva.

---

### Tipos de evidencia que invalidan un chunk

| Tipo | Ejemplo | Prioridad de corrección |
|------|---------|------------------------|
| **Medición cronómetro** contradice tiempo estimado | BOM muestra 45 min en soldadura, chunk dice C1=20 min | **Inmediata** — actualizar umbral |
| **BOM real** contradice consumibles estimados | Argón real=2L, chunk dice 0.5L para ese perfil | **Inmediata** — chunk supersede |
| **Cambio de proceso** — nueva herramienta o método | Compraron roladora nueva, cilindrado C1 bajó de 20 a 12 min | **Próxima sesión** — versionar |
| **Optimización** — operador mejoró técnica | Pulido ahora 2 pasadas donde antes 3 | **Próxima sesión** — versionar |
| **Contradicción entre expertos** | Hernán dice X, operador dice Y | **Investigar** — ambos pueden ser correctos en contextos distintos |
| **Producto nuevo** no encaja en ningún perfil | Producto con características que el modelo no anticipó | **Nuevo chunk** — no supersede, agrega |

---

### Protocolo de validación: 3 niveles según frecuencia

#### Nivel 1 — Validación por BOM (cada vez que hay datos reales)

Cuando se procesa un BOM nuevo (measurements-p1.md o similar), comparar contra chunks existentes:

```
Para cada ítem en el BOM:
  1. Buscar en knowledge-chunks.jsonl los chunks con mismo proceso + perfil_proceso
  2. Comparar valor real vs magnitud del chunk
  3. Calcular desviación: Δ% = (real - estimado) / estimado × 100

  Si |Δ%| < 20%  → chunk válido, no cambiar
  Si |Δ%| 20–50% → chunk necesita actualización de magnitud
  Si |Δ%| > 50%  → chunk puede estar fundamentalmente errado — verificar con experto
  Si el ítem BOM no tiene chunk correspondiente → crear chunk nuevo
```

**Registro:** Anotar en la sesión de validación cuáles chunks fueron confirmados, actualizados, o supersedidos.

---

#### Nivel 2 — Sesión de revisión con experto (trimestral o después de cambio relevante)

**Disparadores para una sesión de revisión:**
- Se incorporó una máquina nueva o herramienta nueva
- Un operador nuevo reemplazó al anterior (diferente técnica)
- Se cambia el proveedor de materiales (consumibles o lámina)
- El modelo de costeo sistemáticamente sobre o sub-estima en > 20% para cierta categoría
- Han pasado más de 6 meses sin validar un proceso

**Formato de la sesión de revisión** (distinto a la sesión de extracción inicial):

```
MODO: VALIDACIÓN — no extracción nueva
OBJETIVO: Confirmar, corregir o versionar chunks existentes

Estructura:
1. Mostrar al experto el chunk actual (texto natural, sin mostrar metadata)
2. Preguntar: "¿Esto sigue siendo correcto hoy?"
3. Si sí → marcar chunk como validado (agregar campo "validado_en": "YYYY-MM-DD")
4. Si no → preguntar qué cambió y por qué
5. Crear chunk nuevo que supersede el anterior
```

**Preguntas de revisión por proceso:**

*Pulido:*
- "La última vez nos dijiste que pulido C3 toma 3 pasadas. ¿Sigue siendo así, o encontraste una forma más rápida?"
- "¿Cambió el set de consumibles desde la última vez? ¿Nuevo disco, nueva herramienta?"
- "¿El costo de los discos cambió significativamente?"

*Soldadura:*
- "La última vez dijiste que más de 8 uniones requiere emplantillado. ¿Sigue siendo ese el número?"
- "¿Cambiaste de equipo de soldadura o de técnica? ¿Afecta los tiempos?"
- "¿El precio del argón cambió? ¿Cambiaste de proveedor?"

*General:*
- "¿Hay algún proceso que ahora es más rápido de lo que era hace 6 meses? ¿Por qué?"
- "¿Algún producto que antes estimábamos bien y ahora cuesta diferente?"

---

#### Nivel 3 — Auditoría de supuestos heredados (una vez, al inicio del sistema real)

> **Contexto:** Los primeros chunks del sistema se generaron de entrevistas donde las preguntas eran abiertas y las respuestas eran estimaciones. Antes de usar el sistema para pricing en producción, hay que auditar esos chunks con datos reales.

**Proceso:**

```
1. Exportar todos los chunks con confianza = "heuristica" o "estimacion_experto"
2. Agrupar por proceso
3. Para cada proceso, identificar qué chunks tienen datos de BOM que los pueden validar
4. Hacer una sesión de medición enfocada en los chunks sin validación

Prioridad de auditoría:
  Alta:   pulido (consumibles dominan), soldadura (argón + tiempo)
  Media:  plegado, cilindrado (tiempos de setup)
  Baja:   trazado, QC (menor impacto económico)
```

**Checklist de limpieza inicial:**

- [ ] Todos los chunks de pulido validados contra al menos 1 BOM real
- [ ] Todos los chunks de soldadura con magnitud de argón confirmada
- [ ] Umbrales C1→C2 y C2→C3 para los 4 procesos principales verificados con cronómetro
- [ ] Ningún chunk con `confianza: "heuristica"` en procesos de alto impacto (pulido, soldadura, plegado)
- [ ] Chunks de productos anchor (Poruña, Campana, Basurero) tienen ref_producto correcto

---

### Cómo versionar un chunk que cambió

**Regla:** nunca borrar. Siempre supersede.

```
Chunk viejo (a1b2c3...):
  magnitud: "C1 pulido = 60 min"
  confianza: "estimacion_experto"

Chunk nuevo (x9y8z7...):
  magnitud: "C1 pulido = 45 min (optimizado con nueva roleta 2026)"
  confianza: "medido"
  supersede: "a1b2c3..."   ← apunta al viejo

Chunk viejo actualizado:
  ... (mismo contenido)
  supersedido_por: "x9y8z7..."   ← apunta al nuevo
  activo: false                   ← el sistema RAG ignora chunks con activo=false
```

Agregar campo `"activo": true` a todos los chunks nuevos. El campo `"activo": false` marca chunks supersedidos. El sistema RAG solo consulta chunks con `activo = true` (o donde el campo no existe, para compatibilidad retroactiva).

---

### Registro de sesiones de validación

Agregar al final de este archivo después de cada sesión:

```
## Log de Validaciones

| Fecha | Experto | Modo | Chunks revisados | Actualizados | Nuevos | Trigger |
|-------|---------|------|-----------------|--------------|--------|---------|
| YYYY-MM-DD | [nombre] | extraccion/validacion | N | N | N | [motivo] |
```

---

### Señales de alerta que deberían disparar una revisión

Monitorear en producción una vez el sistema de costeo esté activo:

| Señal | Umbral | Acción |
|-------|--------|--------|
| Costo estimado vs real para un perfil | > 25% sistemático en > 3 trabajos | Revisión del proceso dominante |
| Nuevo producto no encuentra ancla similar | distancia euclidiana > 0.4 a cualquier ancla | Puede necesitar nuevo ancla o chunk nuevo |
| Consumible no aparece en lista de chunks | Primer BOM que lo registra | Crear chunk nuevo |
| Tiempo real > 2× tiempo estimado para proceso | 1 vez | Investigar; puede ser outlier |
| Tiempo real > 2× tiempo estimado para proceso | 3 veces mismo proceso | Actualizar umbral — no es outlier |

---

## Log de Validaciones

| Fecha | Experto | Modo | Chunks revisados | Actualizados | Nuevos | Trigger |
|-------|---------|------|-----------------|--------------|--------|---------|
| 2026-04-13 | fabio (BOM) | extraccion | 0 | 0 | 6 | Seed inicial desde measurements-p1.md |



urinarios es como un lavadero complejo como una taza. 

mesone refirgerados, freidora, sooperas
usualmente son refrigerados ya que son mas complejos de hacer
el euqipo es muy tecnico para realizar esto