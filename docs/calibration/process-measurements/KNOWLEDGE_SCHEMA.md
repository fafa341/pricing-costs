# Knowledge Chunk Schema
## Dulox Manufacturing RAG System

> **Authoritative storage:** `files-process/process-measurements/knowledge-chunks.jsonl`  
> **One line per chunk.** Each line is a valid JSON object.  
> **Flat inspection view:** `knowledge-chunks-view.csv` (derived, auto-generated — do not edit directly)

---

## 1. Chunk Structure

```jsonc
{
  // === CONTENIDO ===
  "chunk_id": "uuid-v4",                    // identificador único y estable
  "texto": "string",                         // 1–3 oraciones en español, lenguaje natural, contexto completo
  "texto_embedding": "string",              // versión normalizada sin relleno — optimizada para embedding, en español

  // === METADATA CORE ===
  "metadata": {
    "proceso": "string",                    // ver Valores de Proceso abajo
    "perfil_proceso": "string | null",      // ver Valores de perfil_proceso — columna autoritativa de productos-master.csv. null si es regla general
    "driver": "string | null",             // G | D | C | X | GD | CX | GDC | etc. — null si no aplica

    // === DIMENSIÓN & UMBRAL ===
    "tipo_dimension": "string | null",      // ver Tipos de Dimensión abajo
    "valor_umbral": "number | null",        // el número real si se extrajo un umbral
    "unidad_umbral": "string | null",       // mm | m | m2 | conteo | litros | minutos | null
    "tipo_umbral": "string",               // ver Tipos de Umbral abajo

    // === COMPLEJIDAD ===
    "nivel_complejidad": "string | null",   // C1 | C2 | C3 | C1-C2 | C2-C3 | cualquiera | null

    // === IMPACTO ===
    "tipo_impacto": "string",              // ver Tipos de Impacto abajo
    "escalamiento": "string",              // ver Tipos de Escalamiento abajo
    "magnitud": "string | null",           // "~40%" | "2x" | "+30 min" | null si no se extrajo

    // === PROCEDENCIA ===
    "confianza": "string",                 // medido | estimacion_experto | heuristica
    "fuente": "string",                    // entrevista | cronometro | documento_bom | juicio_experto
    "fuente_id": "string",                 // ej. "hernan-2026-04-15" | "measurements-p1"
    "ref_producto": "string | null",       // SKU o nombre si es específico del producto — null si general
    "fecha_sesion": "YYYY-MM-DD",         // fecha de extracción

    // === ETIQUETAS ===
    "etiquetas": ["string"],              // lista libre para temas transversales

    // === VERSIONADO ===
    "activo": true,                       // false si fue supersedido — el RAG ignora chunks con activo=false
    "supersede": "uuid | null",          // chunk_id al que reemplaza (si este es una corrección)
    "supersedido_por": "uuid | null",    // chunk_id que lo reemplazó (se agrega al chunk viejo)
    "validado_en": "YYYY-MM-DD | null"   // última fecha en que un experto confirmó que sigue siendo correcto
  }
}
```

---

## 2. Vocabularios Controlados

### Valores de Proceso (`proceso`)
```
soldadura          Soldadura TIG
pulido             Pulido y terminación (hasta 3 pasadas)
corte_manual       Corte manual (amoladora, ruleta)
corte_laser        Corte láser (tercerizado)
grabado_laser      Grabado láser (logos, números)
plegado            Plegado en plegadora hidráulica
cilindrado         Cilindrado en roladora (formas cilíndricas)
trazado            Trazado y marcado
qc                 Control de calidad + embalaje
pintura            Pintura
refrigeracion      Ensamble unidad refrigerante
comp_electrico     Instalación componentes eléctricos (proceso 4.2)
instalacion_gas    Instalación sistema de gas (proceso 4.3)
multi              Regla aplica a múltiples procesos
material           Propiedad de material (no un proceso)
general            Regla general de fabricación
```

### Valores de `perfil_proceso` — columna autoritativa de `productos-master.csv`
> `subfamilia_p2` está deprecada. Usar siempre `perfil_proceso` como identificador de perfil de proceso.
```
p-meson              Mesones, estanterías, cocinas, módulos de trabajo (plegado C2 + soldadura C1-C2 + pulido C2)
p-plancha-simple     Accesorios planos sin soldadura estructural (corte + plegado + pulido C1)
p-cilindrico         Productos cilíndricos: poruñas, baldes, tinas (cilindrado + soldadura C1)
p-carro              Carros, módulos con ruedas, salad bars (tubos cilindrados + paneles plegados)
p-basurero-cil       Basureros cilíndricos, bicicleteros, reciclaje (cilindrado C2 + pulido C3)
p-basurero-rect      Basureros rectangulares y especiales (plegado C2 + soldadura C2 + pulido C3)
p-campana            Campanas murales y centrales (plegado C2 + soldadura C2 + pulido C2)
p-celosia            Celosías, escaleras piscina, protecciones (soldadura C3 múltiples uniones)
p-sumidero           Sumideros, canaletas (plegado C1 + soldadura C1 + laser tapa)
p-lavadero           Lavaderos, lavamanos (plegado C2 + soldadura C1-C2 + taza)
p-laser              Logos, letras armadas, tótems (solo corte/grabado láser)
p-electrico          Baños maría, calentadores con resistencias (procesos estándar + comp_electrico)
p-custom             Proyectos especiales, equipos industriales (perfil variable)
p-refrigerado        Productos con unidad refrigerante ensamblada (procesos estándar + refrigeracion)
p-importado          Productos revendidos sin fabricación Dulox
```

### Valores de Driver (`driver`)
```
G        Geometría (área de superficie)
D        Densidad (espesor / grosor del material)
C        Componentes (conteo de piezas)
X        Características (suma de flags activos)
GD       Combinación G + D
CX       Combinación C + X
GDC      Combinación G + D + C
GX       Combinación G + X
DC       Combinación D + C
```

### Tipos de Dimensión (`tipo_dimension`)
```
espesor        espesor del material en mm
largo          dimensión lineal en mm o m
area           área de superficie en mm² o m²
diametro       diámetro circular en mm
conteo         conteo entero (uniones, dobleces, piezas)
volumen        capacidad en litros o cm³
peso           kg
angulo         grados
```

### Tipos de Umbral (`tipo_umbral`)
```
limite_complejidad    marca el punto de transición C1→C2 o C2→C3
cambio_metodo         dispara un cambio en cómo se hace el proceso (ej. TIG vs MIG)
driver_costo          identifica qué impulsa principalmente el costo de este proceso
excepcion             caso donde las reglas normales no aplican
regla                 principio operativo general
observacion           observación factual sin regla de decisión
relacion_escala       describe cómo una variable escala con otra
```

### Tipos de Impacto (`tipo_impacto`)
```
tiempo          afecta tiempo de ejecución o setup
consumibles     afecta consumo de materiales (discos, argón, etc.)
materiales      afecta uso de materia prima (lámina)
metodo          cambia qué técnica se usa
calidad         afecta calidad del output / tasa de rechazo
multi           afecta tiempo + consumibles simultáneamente
```

### Tipos de Escalamiento (`escalamiento`)
```
lineal           el costo se duplica cuando el driver se duplica
sublineal        el costo crece más lento que el driver (economías de escala)
superlineal      el costo crece más rápido que el driver (dificultad compuesta)
fijo             no escala con el tamaño (tiempo de setup, componentes fijos)
funcion_escalon  constante dentro de un rango, salta en el umbral
exponencial      el costo crece exponencialmente con el driver
```

### Niveles de Confianza (`confianza`)
```
medido              valor viene de cronómetro / peso / conteo real
estimacion_experto  el experto dio un número de memoria, confirmado como de experiencia
heuristica          regla empírica sin número específico confirmado, o conocimiento general
```

---

## 3. Ejemplos de Chunks

### Ejemplo 1 — Umbral con magnitud
```json
{
  "chunk_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "texto": "Cuando un producto tiene más de 8 uniones soldadas, el emplantillado se vuelve necesario. Esto incrementa el T_setup aproximadamente 15–20 minutos, pero reduce el tiempo de ejecución por unión y mejora la precisión dimensional.",
  "texto_embedding": "Soldadura con más de 8 uniones requiere emplantillado, agregando 15-20 min de setup, reduciendo tiempo de ejecución por unión.",
  "metadata": {
    "proceso": "soldadura",
    "subfamilia": null,
    "driver": "C",
    "tipo_dimension": "conteo",
    "valor_umbral": 8,
    "unidad_umbral": "conteo",
    "tipo_umbral": "limite_complejidad",
    "nivel_complejidad": "C2",
    "tipo_impacto": "tiempo",
    "escalamiento": "funcion_escalon",
    "magnitud": "+15-20 min setup",
    "confianza": "estimacion_experto",
    "fuente": "entrevista",
    "fuente_id": "hernan-2026-04-15",
    "ref_producto": null,
    "fecha_sesion": "2026-04-15",
    "etiquetas": ["soldadura", "conteo_uniones", "emplantillado", "tiempo_setup"]
  }
}
```

### Ejemplo 2 — Regla de excepción
```json
{
  "chunk_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "texto": "Para superficies cilíndricas (tubos, cuerpos de basurero cilíndrico), el pulido toma aproximadamente un 30% más de tiempo por m² que superficies planas de la misma área, porque el operador debe reposicionar continuamente y la geometría curva dificulta la presión uniforme.",
  "texto_embedding": "Pulido en superficies cilíndricas toma ~30% más tiempo por m² que superficies planas, por necesidad de reposicionamiento y geometría curva.",
  "metadata": {
    "proceso": "pulido",
    "subfamilia": "basurero-con-mecanismo",
    "driver": "G",
    "tipo_dimension": "area",
    "valor_umbral": null,
    "unidad_umbral": null,
    "tipo_umbral": "excepcion",
    "nivel_complejidad": "C2-C3",
    "tipo_impacto": "tiempo",
    "escalamiento": "superlineal",
    "magnitud": "+30% por m²",
    "confianza": "estimacion_experto",
    "fuente": "entrevista",
    "fuente_id": "hernan-2026-04-15",
    "ref_producto": null,
    "fecha_sesion": "2026-04-15",
    "etiquetas": ["pulido", "cilindrico", "penalizacion_geometria", "superlineal"]
  }
}
```

### Ejemplo 3 — Observación producto específico (de measurements-p1.md)
```json
{
  "chunk_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "texto": "Para la Poruña 1KG (405×130×130mm, 1mm AISI 304), los consumibles de pulido totalizan $25.500 CLP contra un costo de material de $3.081 CLP — una relación de 8,3×. Esto valida que los consumibles de pulido dominan el costo fabricado para productos cilíndricos pequeños con terminación.",
  "texto_embedding": "Consumibles de pulido Poruña 1KG ($25.500) son 8,3 veces el costo de material ($3.081), confirmando que pulido domina el costo en productos cilíndricos pequeños.",
  "metadata": {
    "proceso": "pulido",
    "subfamilia": "poruña",
    "driver": "GX",
    "tipo_dimension": "area",
    "valor_umbral": null,
    "unidad_umbral": null,
    "tipo_umbral": "driver_costo",
    "nivel_complejidad": "C1",
    "tipo_impacto": "consumibles",
    "escalamiento": "superlineal",
    "magnitud": "8,3x costo material",
    "confianza": "medido",
    "fuente": "documento_bom",
    "fuente_id": "measurements-p1",
    "ref_producto": "POR-1000",
    "fecha_sesion": "2026-04-13",
    "etiquetas": ["pulido", "consumibles_dominan", "cilindrico", "poruña", "relacion_costo"]
  }
}
```

---

## 4. Diseño de Almacenamiento y Recuperación

### Estructura de archivos
```
files-process/process-measurements/
├── knowledge-chunks.jsonl        ← almacén autoritativo (solo se agrega, nunca se edita en lugar)
├── KNOWLEDGE_SCHEMA.md           ← este archivo
└── INTERVIEW_FRAMEWORK.md        ← metodología de entrevistas
```

### Cómo agregar chunks nuevos
Siempre agregar al final — nunca editar chunks existentes. Si un chunk necesita corrección:
1. Agregar nuevo chunk con contenido corregido
2. Agregar `"supersede": "<chunk_id_viejo>"` al metadata del nuevo
3. Agregar `"supersedido_por": "<chunk_id_nuevo>"` al chunk viejo (editar esa línea)

---

### Estrategia RAG — Consultas de conocimiento de procesos

Para consultas sobre reglas de proceso (uso actual — durante desarrollo del modelo de costos):

```
Consulta: "¿Cuánto argón usa una soldadura de 10 puntos en espesor 1.5mm?"

Búsqueda semántica → top-K chunks por similitud coseno en texto_embedding

Filtros de metadata a aplicar:
  proceso = "soldadura" OR "multi"
  perfil_proceso IN ["p-meson", "p-cilindrico", null]   ← null = regla general, siempre incluir
  tipo_dimension IN ["conteo", "espesor", null]

Resultado: chunks rankeados + filtrados → contexto al LLM → respuesta
```

**Regla clave:** siempre incluir chunks con `perfil_proceso = null` (reglas generales) además del perfil específico.

---

### Representación matemática por producto — Product Vector

> **Objetivo futuro:** Cada producto tiene un vector numérico que lo ubica en el espacio de fabricación. Permite encontrar el ancla más similar a un producto nuevo por distancia matemática, no solo por texto.

Cada producto en `productos-master.csv` se representa como un vector de 9 dimensiones:

```
v(P) = [G, D, C, X, area_mm2_norm, espesor_norm, n_componentes_norm, φ_activos, complejidad_num]
```

| Dimensión | Cálculo | Rango | Qué captura |
|-----------|---------|-------|-------------|
| G | área_superficie / 1.500.000 | 0–1 | tamaño geométrico normalizado |
| D | espesor_mm / 10 | 0–1 | densidad de material |
| C | n_componentes / 20 | 0–1 | complejidad de ensamble |
| X | flags_activos / 5 | 0–1 | características especiales |
| area_mm2_norm | L×W / 1.500.000 | 0–1 | área planta real |
| espesor_norm | espesor_mm / 10 | 0–1 | espesor real (igual a D, puede refinarse) |
| n_componentes_norm | conteo / 20 | 0–1 | conteo real |
| φ_activos | procesos_activos / 11 | 0–1 | fracción del proceso total activo |
| complejidad_num | C1→0.33, C2→0.66, C3→1.0 | 0–1 | nivel global |

**Distancia entre producto nuevo y ancla:**
```python
distancia(P_nuevo, P_ancla) = √( Σᵢ wᵢ × (vᵢ_nuevo - vᵢ_ancla)² )

# Pesos sugeridos (a calibrar):
w = [0.25, 0.15, 0.20, 0.15, 0.10, 0.05, 0.05, 0.05, 0.00]
#    G      D      C      X    area  esp   comp  φ    cplx
# G y C tienen más peso porque dominan las diferencias de costo entre anclas
```

El ancla con menor distancia al producto nuevo es el template de costo más apropiado.

Este vector se calcula automáticamente desde `productos-master.csv` — no necesita datos adicionales.

---

### Herramienta administrativa — Onboarding de producto nuevo (FUTURO)

> **Objetivo:** El equipo administrativo puede ingresar un producto nuevo (personalizado, nunca fabricado antes) y el sistema encuentra el ancla de costo más similar + genera una plantilla de costeo.

**Flujo de la herramienta:**

```
1. ENTRADA DEL USUARIO (formulario o chat NLP)
   ├── Descripción en lenguaje natural: "mesón de trabajo con cajones y ruedas, 1.8m, acero 1.5mm"
   ├── Dimensiones: L × W × H × espesor
   ├── Características: flags activos (perforado, múltiples_uniones, acabado_especial, etc.)
   └── (Opcional) plano o foto → extracción automática de dimensiones

2. PROCESAMIENTO
   ├── NLP → extrae drivers G, D, C, X desde descripción + dimensiones
   ├── Calcula vector v(P_nuevo)
   ├── Busca top-3 anclas por distancia euclidiana en productos-master
   └── RAG query → recupera chunks de conocimiento relevantes para ese perfil

3. SALIDA
   ├── Top-3 anclas sugeridas con % de similitud y diferencias clave
   ├── Perfil de proceso propuesto (cuáles procesos activos, nivel C1/C2/C3 estimado)
   ├── Plantilla de costo pre-llenada con factor_escala calculado desde el ancla
   └── Preguntas de confirmación al usuario si hay ambigüedad (ej. "¿lleva soldadura visible?")
```

**Ejemplo de consulta NLP:**
```
Input: "necesito costear una campana mural de 3 metros, acero 1mm, con filtros y motor"

→ perfil detectado: p-campana
→ ancla más cercana: Campana Mural 2000×1000×400mm (distancia = 0.18)
→ factor_escala: 3000/2000 = 1.50 (metros largos)
→ alerta: "componentes comprados (filtros, motor) son costo fijo — no escalan con factor_escala"
→ chunks recuperados: 3 reglas sobre soldadura campana + 2 sobre componentes fijos
```

**Por qué RAG y no solo lógica de reglas:**
- Los productos son altamente personalizados — no hay tabla de precios fija
- Las reglas de excepción viven en el conocimiento experto, no en el catálogo
- Nuevos materiales, espesores atípicos, o combinaciones inusuales necesitan razonamiento, no lookup

**Stack tecnológico recomendado (cuando implementar):**
| Componente | Opción simple | Opción producción |
|------------|--------------|-------------------|
| Embeddings | `sentence-transformers` (local) | OpenAI `text-embedding-3-small` |
| Vector store | JSONL + numpy (ya existe) | Supabase pgvector |
| Búsqueda ancla | distancia euclidiana en numpy | mismo, con índice |
| UI administrativa | Claude Code con formulario md | webapp Next.js + Supabase |

**No construir esto ahora.** El prerequisito es tener todos los anclas medidos y `knowledge-chunks.jsonl` con ≥50 chunks de calidad `confianza: medido` o `estimacion_experto`.

---

## 5. Seeding from Existing Data

The following existing files should be converted to chunks as a first pass:

| Source file | What to extract | Priority |
|-------------|----------------|----------|
| `measurements-p1.md` | BOM costs, consumables ratios, process lists per product | **High** |
| `PROCESS_THRESHOLDS.md` | All C1/C2/C3 time values as chunks | **High** |
| `PRODUCTS_8020_PROCESS_MAP.md` | Per-process level assignments + driver reasoning | **High** |
| `LAYER_2_COMPLEXITY.md` | Driver scoring rules + feature flag definitions | Medium |
| `PROCESS_MATRIX.csv` | Anchor product profiles + factor_escala reasoning | Medium |
| `CALIBRATION_MEASUREMENT.md` | Measurement methodology rules | Low |

Run `knowledge-extractor` agent with `source: "existing_document"` for these.
