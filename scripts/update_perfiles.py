"""
Update productos-master.csv with all perfil_proceso reclassifications from the interview session.
Run: python3 scripts/update_perfiles.py
"""

import csv
import shutil
from pathlib import Path

CSV_PATH = Path("dataset/productos-master.csv")
BACKUP_PATH = Path("dataset/productos-master.BACKUP.csv")

# ─── Backup ───────────────────────────────────────────────────────────────────
shutil.copy(CSV_PATH, BACKUP_PATH)
print(f"Backup saved → {BACKUP_PATH}")

# ─── Load ─────────────────────────────────────────────────────────────────────
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    fieldnames = reader.fieldnames

print(f"Loaded {len(rows)} rows")

# ─── Counter ──────────────────────────────────────────────────────────────────
changes = []

def update(row, new_perfil=None, new_complejidad=None, reason=""):
    h = row["Product: Handle"]
    old_p = row["perfil_proceso"]
    old_c = row["complejidad"]
    if new_perfil and new_perfil != old_p:
        row["perfil_proceso"] = new_perfil
        changes.append(f"  perfil: {h}: {old_p} → {new_perfil}  [{reason}]")
    if new_complejidad and new_complejidad != old_c:
        row["complejidad"] = new_complejidad
        changes.append(f"  complejidad: {h}: {old_c} → {new_complejidad}  [{reason}]")


# ─── Rules ────────────────────────────────────────────────────────────────────

for row in rows:
    h = row["Product: Handle"].lower()
    sub = row["subfamilia"].lower()
    perfil = row["perfil_proceso"]

    # ── 1. p-carro splits ────────────────────────────────────────────────────
    if perfil == "p-carro":
        # bandejeros
        if "bandejero" in h:
            update(row, "p-carro-bandejero", reason="carro-bandejero: driver=niveles bandejas")
        # limpiador de filtros → accesorio de bandejero
        elif "limpiador-de-filtros" in h:
            update(row, "p-carro-bandejero", reason="accesorio limpieza para carro bandejero")
        # módulos neutros / pan y servicios / salad bar / linea autoservicio
        elif sub in ("salad-bar", "modulo-neutro", "modulo-servicio") \
                or "modulo-neutro" in h or "modulo-pan" in h or "modulo-de-pan" in h \
                or "salad-bar" in h or "linea-de-autoservicio" in h \
                or "equipamiento-gastronomico" in h:
            update(row, "p-modulo", reason="módulo de servicio: plegado + estación, no ruedas")
        # carro para traslado / batea
        elif "traslado" in h or "batea" in h:
            update(row, "p-carro-traslado", reason="carro estructura tubular con ruedas industriales")
        # food carts, medico, tanatologia, muebles, sillas, atril — todo a p-custom
        else:
            update(row, "p-custom", reason="carro especial/proyecto: geometría no estándar")

    # ── 2. p-celosia → p-rejilla (all) ──────────────────────────────────────
    elif perfil == "p-celosia":
        update(row, "p-rejilla", reason="rejillas/barandas: perfilería + soldadura, no laminar")

    # ── 3. p-cilindrico reclassifications ───────────────────────────────────
    elif perfil == "p-cilindrico":
        if "espatula" in h or "plancha-acero-sobre-cubierta" in h or "pala-de-basura" in h:
            update(row, "p-laminar-simple", reason="pieza plana de corte y plegado simple")
        elif "escurridor-de-servicios" in h:
            update(row, "p-importado", reason="escurridor importado, no fabricado en planta")
        elif "delantal" in h or "jockey" in h:
            update(row, "p-importado", reason="artículo textil/importado")
        elif "servilletero" in h:
            update(row, "p-custom", reason="accesorio decorativo, geometría variable por modelo")
        elif "atril-para-pasteles" in h:
            update(row, "p-custom", reason="atril multinivel, estructura no cilíndrica estándar")
        elif "hervidor" in h or "calentador-de-leche" in h:
            update(row, "p-electrico", reason="cilindro con mecanismo eléctrico/resistencia")
        elif sub in ("tinas-lacteos",) or "tina-quesera" in h or "prensa-quesera" in h or "moldes-para-quesillo" in h:
            update(row, "p-tina", reason="equipo lácteo: tina/prensa con mecanismo y llaves")
        # baldes, porunas, moldes-queso, porta-* → stay p-cilindrico

    # ── 4. p-plancha-simple dissolution ─────────────────────────────────────
    elif perfil == "p-plancha-simple":
        # importados
        if any(x in h for x in ["perol", "griferia", "cortadora-de-fiambre", "cortadora-de-papas-pipp",
                                  "filtro-de-campana"]):
            update(row, "p-importado", reason="importado: no fabricado en planta (confirmado B1-Q4)")
        # eléctricos
        elif "tostador" in h:
            update(row, "p-electrico", reason="electrodoméstico con resistencia, ancla p-electrico C1")
        elif "calienta-platos" in h:
            update(row, "p-electrico", reason="calentador eléctrico de platos")
        # cilíndrico (como poruna)
        elif "dispensador" in h and "papas" in h:
            update(row, "p-cilindrico", reason="dispensador cilíndrico, estructura como poruna (B1-Q4)")
        # basureros mal clasificados
        elif "basurero" in h and "rect" in h:
            update(row, "p-basurero-rect", reason="basurero rectangular mal asignado a plancha-simple")
        elif "basurero" in h:
            update(row, "p-basurero-cil", reason="basurero cilíndrico mal asignado a plancha-simple")
        # repisas, mesas desueradoras → más similar a p-meson
        elif "repisa" in h or "mesa-desueradora" in h or "bebedero" in h:
            update(row, "p-meson", reason="mueble de servicio: repisas/mesas más cerca de p-meson (B1-Q4)")
        # mueble especial / banca
        elif "mueble-de-transferencia" in h or "banca" in h or "revestimiento-curvo" in h:
            update(row, "p-custom", reason="pieza especial/proyecto")
        # baldes mal asignados → p-cilindrico
        elif "balde" in h:
            update(row, "p-cilindrico", reason="balde = cilíndrico")
        # todo lo demás → p-laminar-simple
        else:
            update(row, "p-laminar-simple",
                   reason="laminar simple: cubrejunta/zócalo/moldura/peinazo/bandeja/soporte (B1-Q4)")

    # ── 5. p-lavadero: faucets and purchased-taza lavamanos ─────────────────
    elif perfil == "p-lavadero":
        if "columna-llave" in h or "llave-pre-wash" in h:
            update(row, "p-importado", reason="grifo importado, no fabricado")
        elif "lavamanos-fijo-a-muro" in h:
            update(row, "p-meson", reason="lavamanos con taza comprada (principio taza comprada → p-meson)")

    # ── 6. p-meson: cocinas y anafes → p-cocina-gas ─────────────────────────
    elif perfil == "p-meson":
        gas_keywords = ["anafe", "cocina-4-q", "cocina-industrial", "cocina-wok",
                        "cocina-de-4", "cocina-electrica", "cocina-8", "cocina-6",
                        "4pq", "3pq", "2pq", "1pq", "6pq", "8pq", "churrasquera",
                        "plancha-churrasquera"]
        if any(k in h for k in gas_keywords):
            update(row, "p-cocina-gas", reason="equipo de cocción: driver=quemadores (B1-Q5)")
        # meson-refrigerado
        elif "refriger" in h and "meson" in h:
            update(row, "p-refrigerado", reason="mesón refrigerado: sistema de frío activo")

    # ── 7. p-importado: ZLLE fabricados → p-lavadero ─────────────────────────
    elif perfil == "p-importado":
        if any(x in h for x in ["zlle-0126", "zlle-0128", "zlle-0260"]):
            update(row, "p-lavadero", reason="lavadero puestos de trabajo: fabricado en planta (ancla B3)")


# ─── Complejidad corrections (anchors confirmed in B3) ────────────────────────

anchor_complejidad = {
    # p-carro-bandejero
    "carro-bandejero-capacidad-12-bandejas-aucb-0178": "C1",
    "carro-bandejero-capacidad-para-22-bandejas-aucb-0670": "C2",
    "carro-bandejero-capacidad-22-bandejas-aucb-0670": "C2",
    "carro-bandejero-capacidad-24-bandejas-aucb-0810": "C2",
    "carro-bandejero-capacidad-para-24-bandejas-aucb-0810": "C2",
    "carro-bandejero-cerrado-capacidad-8-bandejas-aucb-0790": "C3",
    "carro-bandejero-cerrado-para-8-bandejas-aucb-0790": "C3",
    # p-lavadero
    "lavadero-de-2-puestos-de-trabajo-zlle-0126": "C1",
    "lavadero-de-4-puestos-de-trabajo-zlle-0128": "C2",
    "lavadero-de-8-puestos-de-trabajo-zlle-0260": "C3",
    # p-cilindrico (baldes)
    "balde-20lts-blds-300": "C2",
    # p-electrico (hervidor)
    "hervidor-electrico-20lts-auha-0157": "C3",
    # p-cocina-gas
    "cocina-industrial-de-6-quemadores-y-churrasquera-6pqch": "C3",
    "cocina-industrial-4-quemadores-sn-horno-4pqn": "C2",
    # p-meson
    "meson-abierto-de-trabajo-de-900mm-bamt-0900": "C1",
}

for row in rows:
    h = row["Product: Handle"]
    if h in anchor_complejidad:
        update(row, new_complejidad=anchor_complejidad[h], reason="ancla confirmada en entrevista B3")


# ─── Write ────────────────────────────────────────────────────────────────────
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\nApplied {len(changes)} changes:")
for c in changes:
    print(c)

# ─── Summary ──────────────────────────────────────────────────────────────────
from collections import Counter
final_counts = Counter(r["perfil_proceso"] for r in rows)
print("\nFinal perfil_proceso distribution:")
for k, v in sorted(final_counts.items()):
    print(f"  {k}: {v}")
