"""Carga procedimientos de Ginecología. Ejecutar una sola vez."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.catalogo import TipoProcedimiento, Especialidad
from decimal import Decimal

DATOS = [
    ("CONSULTA", 25000),
    ("PAP Y COLPO", 32000),
    ("EXTRACCION DE DIU", 32000),
    ("COLOCACION DE DIU", 45000),
    ("RECAMBIO DE DIU", 55000),
    ("EXTRACCION DE CHIP", 35000),
    ("COLOCACION DE PESARIO", 30000),
    ("COLOCACION DE CHIP", 30000),
    ("BIOPSIA DE UTERO-VAGINAL", 50000),
    ("BIOPSIA MAMARIA", 0),
    ("EXTIRPACION Y TOPICACION DE VERRUGA", 80000),
    ("CHIP", 300000),
    ("SIU", 400000),
]

db = SessionLocal()

esp = db.query(Especialidad).filter(Especialidad.nombre.ilike("%ginecolog%")).first()
if not esp:
    print("ERROR: No se encontró una especialidad de Ginecología.")
    print("Especialidades disponibles:")
    for e in db.query(Especialidad).order_by(Especialidad.nombre).all():
        print(f"  [{e.id}] {e.nombre}")
    db.close()
    sys.exit(1)

print(f"Especialidad encontrada: [{esp.id}] {esp.nombre}")
insertados = 0

for nombre, precio in DATOS:
    db.add(TipoProcedimiento(nombre=nombre, precio=Decimal(precio), especialidad_id=esp.id))
    insertados += 1

db.commit()
db.close()
print(f"Listo: {insertados} procedimientos cargados.")
