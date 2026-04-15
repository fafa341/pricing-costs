# Audit Log — Dulox Modelo de Costeo
> Registro histórico de todas las auditorías del sistema de drivers G/D/C/X.  
> Una fila por auditoría. Ver reportes completos en `audit-reports/AUDIT_[FECHA].md`.

| Fecha | Modo | ICM | Perfiles auditados | Hallazgo principal | Acción tomada | Reporte |
|-------|------|-----|-------------------|--------------------|---------------|---------|
| 2026-04-14 | full | 31.6 | 17 perfiles | ICM=31.6: Driver C no testeable (falta en CSV). p-meson/carro-bandejero: G no es driver correcto (es C). Cobertura PROCESS_MATRIX vs catálogo solo 6%. Campana Mural es la única ancla representativa. | (1) Enriquecer CSV con num_componentes/quemadores/niveles. (2) Completar factor_escala en PROCESS_MATRIX. (3) Medir 3 anclas con cronómetro. | [AUDIT_2026-04-14.md](audit-reports/AUDIT_2026-04-14.md) |
