# Proceso de Categorización de Productos — Dulox Ingeniería en Aceros

## Objetivo

Construir una base de datos estructurada de productos que permita:

1. **Costear con precisión** cada producto fabricado, usando el sistema de costeo ABC por capas (LAYER_1 a LAYER_9).
2. **Distinguir el origen del producto**: fabricado en planta, importado para reventa, o importado como componente de un producto fabricado.
3. **Clasificar la complejidad** de fabricación para aplicar los multiplicadores correctos de tiempo, mano de obra y máquina.
4. **Escalar el conocimiento experto**: pasar del conocimiento tácito de Miguel a una lógica estructurada y consultable.

---

## Fuentes de Datos

| Archivo | Descripción | Filas |
|---------|-------------|-------|
| `Productos-Categorizados - Sheet1.csv` | Catálogo extraído del sitio web dulox.cl. Contiene el `Product: Handle` (slug URL) de cada producto. | 1.084 (bruto) |
| `Productos-Categorizados2 - productos.csv` | Catálogo limpio con código de producto (`CÓDIGO`), nombre en español (`PRODUCTO`) y columna `IMPORTADO`. | 738 |

---

## Etapas del Proceso

### Etapa A — Limpieza y preparación de Sheet1

**Problema:** Sheet1 contenía 1.084 filas pero solo 587 productos únicos. Las 497 filas restantes eran duplicados del mismo `Product: Handle`.

#### A1 · Deduplicación
**Script:** `01_deduplicate.py`
- Elimina filas duplicadas basándose en la columna `Product: Handle` (identificador único de URL)
- Conserva la primera ocurrencia de cada producto
- **Resultado:** `Sheet1-dedup.csv` → 587 productos únicos

#### A2 · Construcción de URLs
**Script:** `02_add_urls.py`
- Agrega columna `url` concatenando `https://dulox.cl/products/` con el handle de cada producto
- **Resultado:** `Sheet1-with-urls.csv` → 587 filas con URL completa

Ejemplo:
```
handle: meson-abierto-de-trabajo-de-900mm-bamt-0900
url:    https://dulox.cl/products/meson-abierto-de-trabajo-de-900mm-bamt-0900
```

#### A3 · Scraping de descripciones
**Script:** `03_scrape_descriptions.py`
- Visita cada URL y extrae la descripción del producto desde el HTML de dulox.cl
- Fuente primaria: bloque `tab-popup-content` (descripción completa de la ficha de producto)
- Fuente secundaria: `<meta name="description">` (siempre presente, con especificaciones técnicas)
- Implementa sistema de checkpoint (`scrape_checkpoint.json`) para reanudar si se interrumpe
- Delay de 1,5 segundos entre requests para no sobrecargar el servidor
- **Resultado:** `Sheet1-scraped.csv` → agrega columnas `descripcion_web` y `scrape_status`

---

### Etapa B — Enriquecimiento de Sheet2

**Script:** `enrich_sheet2.py`

Sheet2 no requiere scraping porque contiene nombres descriptivos en español y la columna `IMPORTADO`. Se enriqueció con dos campos nuevos:

#### Campo `tipo_fabricacion`
Clasifica el origen del producto. Ver `importado-revisar.md` para detalle.

#### Campo `complejidad`
Clasifica la dificultad de fabricación en tres niveles (C1, C2, C3), alineado con el sistema LAYER_2 del ABC. Ver `criterios-subfamilia.md` para detalle.

**Resultado:** `Sheet2-enriched.csv`

---

### Etapa B.2 — Enriquecimiento de Sheet1 (normalización + clasificación)

**Script:** `05_enrich_sheet1.py`

Sheet1 usa nombres de familia basados en slugs de URL del sitio web (ej. `gastronomica`, `construccion`), que son categorías comerciales de navegación, no familias de producto. Este script:

1. **Normaliza familias:** mapea los 43 slugs de Sheet1 a los nombres estándar de Sheet2 (ej. `mesones-de-trabajo` → `Mesones de Trabajo`)
2. **Reclasifica familias amplas:** `gastronomica` (165 productos), `construccion`, `coccion`, `preelaboracion` y `otros-productos` eran catch-alls. Se reclasifican usando la subfamilia y palabras clave de la descripción scrapeada
3. **Asigna `tipo_fabricacion`:** usando señales en la descripción (ej. "FABRICADO ÍNTEGRAMENTE EN ACERO INOXIDABLE" → fabricado; marcas importadas → importado-resell)
4. **Asigna `complejidad`:** misma lógica LAYER_2 que Sheet2

**Resultado:** `Sheet1-enriched.csv`

---

### Etapa C — Consolidación en hoja única

**Script:** `04_consolidar.py`

Combina `Sheet1-enriched.csv` y `Sheet2-enriched.csv` en un único archivo maestro con columnas estandarizadas:

```
familia | subfamilia | codigo | producto | handle | url | descripcion_web |
scrape_status | importado_flag | tipo_fabricacion | complejidad | fuente
```

---

## Modelo de Datos Final

### Columnas clave

| Columna | Valores posibles | Descripción |
|---------|-----------------|-------------|
| `familia` | 45 familias (Mesones de Trabajo, Basureros, etc.) | Agrupación comercial de productos |
| `subfamilia` | slug descriptivo (ej. `meson-cajones`) | Forma estructural del producto. Define los procesos involucrados y ancla el recetario BASE |
| `tipo_fabricacion` | `fabricado` \| `importado-resell` \| `importado-material` \| `importado-revisar` | Determina la ruta de costeo |
| `complejidad` | `C1` \| `C2` \| `C3` \| *(vacío)* | Multiplicador de dificultad sobre el costo base |
| `descripcion_web` | texto libre | Descripción técnica scraped de dulox.cl |

### Relación con el sistema ABC

```
subfamilia   →  define el recetario BASE (qué procesos y materiales)
complejidad  →  aplica el multiplicador LAYER_3:
                  C1 = ×1.00  (LOW, score 0–3)
                  C2 = +10%   (MEDIUM, score 4–7)
                  C3 = +25%   (HIGH, score 8+)
```

---

## Resultados Catálogo Maestro (`catalogo-maestro.csv`)

| Clasificación | Productos | % |
|---------------|-----------|---|
| `fabricado` | 851 | 64.5% |
| `importado-resell` | 179 | 13.6% |
| `importado-material` | 31 | 2.4% |
| `importado-revisar` | 258 | 19.6% ← **requiere revisión manual** |
| **Total** | **1.319** | |

| Complejidad | Productos (fabricado + importado-material) |
|-------------|-------------------------------------------|
| C1 | 467 |
| C2 | 259 |
| C3 | 156 |

**Familias únicas normalizadas:** 48

---

## Resultados Sheet2 solamente (fuente bodega — más confiable para importados)

| Clasificación | Productos | % |
|---------------|-----------|---|
| `fabricado` | 352 | 48.1% |
| `importado-resell` | 150 | 20.5% |
| `importado-material` | 31 | 4.2% |
| `importado-revisar` | 199 | 27.2% |
| **Total** | **732** | |

---

## Archivos Generados

| Archivo | Descripción | Estado |
|---------|-------------|--------|
| `Sheet1-dedup.csv` | Sheet1 sin duplicados (587 filas) | ✅ |
| `Sheet1-with-urls.csv` | Sheet1 con columna `url` | ✅ |
| `Sheet1-scraped.csv` | Sheet1 con descripciones web scrapeadas (587/587, 0 errores) | ✅ |
| `Sheet1-enriched.csv` | Sheet1 con familia normalizada, tipo_fabricacion y complejidad | ✅ |
| `Sheet2-enriched.csv` | Sheet2 con `tipo_fabricacion` y `complejidad` | ✅ |
| `catalogo-maestro.csv` | Hoja maestra unificada (1.319 filas, 48 familias) | ✅ |
| `importado-revisar.txt` | Lista de productos para revisión manual (Sheet2) | ✅ |
| `scrape_checkpoint.json` | Registro de scraping completado | ✅ |

---

## Scripts

| Script | Función | Estado |
|--------|---------|--------|
| `01_deduplicate.py` | Deduplicar Sheet1 por `Product: Handle` | ✅ |
| `02_add_urls.py` | Agregar columna `url` a Sheet1 | ✅ |
| `03_scrape_descriptions.py` | Scraping de dulox.cl | ✅ |
| `enrich_sheet2.py` | Enriquecer Sheet2 con tipo y complejidad | ✅ |
| `05_enrich_sheet1.py` | Normalizar familias Sheet1 y asignar tipo/complejidad | ✅ |
| `04_consolidar.py` | Consolidar ambas sheets en hoja maestra | ✅ |

---

## Próximos Pasos

1. **Revisión manual** de los 258 productos `importado-revisar` con Miguel → usar `importado-revisar.txt`
2. **Conectar con LAYER_1**: los productos `fabricado` con su `complejidad` asignada son los inputs directos al sistema de costeo ABC
3. **Ingresar dimensiones reales** al recetario para recalcular `complejidad` con LAYER_2 (hoy la asignación es por heurística de código/nombre)
4. **Alinear familias** entre Sheet1 y Sheet2 para los productos que aparecen en ambas fuentes (cross-reference por nombre/descripción)
