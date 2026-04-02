# Productos `importado-revisar` — Guía de Revisión Manual

## ¿Qué es `importado-revisar`?

Es una categoría temporal asignada a productos que tienen la columna `IMPORTADO = "IMPORTADO"` en el catálogo, pero cuya **ruta de costeo no puede determinarse automáticamente** sin conocimiento del proceso real de Dulox.

Estos productos necesitan ser clasificados manualmente por alguien con conocimiento operativo (Miguel u otra persona de producción o comercial) en una de dos categorías definitivas:

| Clasificación final | Significado |
|--------------------|-------------|
| `importado-resell` | Dulox compra el producto terminado y lo vende tal cual, con margen. **No entra al sistema ABC.** |
| `importado-material` | Dulox importa el ítem como componente y lo integra (suelda, ensamble) en una estructura fabricada en planta. **Entra al recetario como costo de material.** |

---

## ¿Por qué existe esta distinción?

La diferencia no es solo semántica — define **cómo se costea el producto**:

### `importado-resell` → Margen solamente
```
Precio de compra (factura proveedor)
        +
  Margen comercial (%)
        =
  Precio de venta
```
No hay receta. No hay cálculo de mano de obra ni tiempo de fabricación. Es un producto de reventa.

### `importado-material` → Entra al recetario
```
Costo del componente importado
        +
  Mano de obra de integración (soldadura / armado)
        +
  Materiales propios (acero, pernos, etc.)
        +
  Gastos indirectos (overhead)
        =
  Costo total del producto fabricado
```
El componente importado es una línea dentro del recetario del producto final. Dulox agrega valor sobre él.

---

## Ejemplo práctico

**Basurero con pedal** (`basurero-con-mecanismo`):
- El cuerpo del basurero es fabricado en planta → `fabricado`
- El mecanismo de pedal es importado → ¿`importado-resell` o `importado-material`?
  - Si Dulox lo integra (monta y suelda) al cuerpo del basurero → **`importado-material`** (entra al recetario del basurero)
  - Si Dulox lo vende como accesorio separado → **`importado-resell`**

---

## Productos en revisión — 199 productos

Los 199 productos marcados como `importado-revisar` pertenecen a las siguientes familias:

| Familia | Lógica probable |
|---------|----------------|
| **Baño María** | Algunos son fabricados con componentes eléctricos importados (baño maría eléctrico). Otros pueden ser unidades importadas completas. |
| **Cocinas Industriales** | Cocinas a gas importadas (resell) vs. cocinas con cuerpo fabricado en Dulox (material). |
| **Depósitos Gastronómicos** | Recipientes GN (Gastronorm) probablemente son todos importados para reventa (similar a Vollrath). |
| **Equipo Industrial** | Casos específicos. Requiere revisión por producto. |
| **Freidoras** | Algunas son importadas completas (resell), otras tienen cuerpo fabricado en Dulox con componentes importados (material). |
| **Hornos** | Similar a freidoras. |
| **Módulo de Autoservicio** | Estructura probablemente fabricada, componentes calefactores o refrigerantes importados. |
| **Muebles Refrigerados** | El mueble puede ser fabricado pero el sistema de frío es importado. |
| **Planchas** | Algunas son importadas completas, otras tienen plancha importada sobre estructura fabricada. |

---

## Cómo hacer la revisión

Para cada producto en `importado-revisar.txt`, responder la siguiente pregunta:

> **¿Dulox agrega trabajo de fabricación sobre este ítem antes de venderlo?**

- **SÍ** → `importado-material` (entra al recetario)
- **NO** → `importado-resell` (solo margen)

### Heurística rápida

| Señal | Clasificación probable |
|-------|----------------------|
| El producto tiene una estructura de acero inoxidable fabricada en Dulox | `importado-material` (el componente importado se integra a esa estructura) |
| El producto llega en caja del proveedor y se despacha sin modificación | `importado-resell` |
| El producto tiene código de proveedor extranjero visible | `importado-resell` |
| El producto es un componente eléctrico/mecánico integrado a algo fabricado | `importado-material` |
| El producto se vende como accesorio independiente | `importado-resell` |

---

## Impacto de no resolver esta clasificación

Mientras un producto permanezca como `importado-revisar`:

1. **No puede ingresar al sistema de costeo ABC** → no tiene precio de costo calculado
2. **No puede tener recetario** → si es material, su costo no se refleja en el producto final
3. **El precio de venta queda sin base** → el vendedor cotiza "a ojo"
4. **El margen real es desconocido** → no se puede saber si la venta es rentable

---

## Acción requerida

**Responsable:** Miguel (o jefe de producción)
**Archivo de trabajo:** `importado-revisar.txt`
**Formato de respuesta:** Para cada ítem, indicar `R` (resell) o `M` (material)

Una vez resueltos, actualizar la columna `tipo_fabricacion` en `Sheet2-enriched.csv` y volver a ejecutar `enrich_sheet2.py` para recalcular la complejidad de los que resulten `importado-material`.

---

## Lista completa de productos a revisar

Ver archivo: [`importado-revisar.txt`](../importado-revisar.txt)
