"""Carga inicial de tipos de ecografía. Ejecutar una sola vez."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.catalogo import TipoEcografia
from decimal import Decimal

DATOS = [
    ("CONSULTA", 25000),
    ("ABDOMINAL TOTAL", 32000),
    ("OBSTETRICA", 30000),
    ("OBSTETRICA GEMELAR", 45000),
    ("GINECOLOGICA", 30000),
    ("TV", 30000),
    ("MAMARIA", 33000),
    ("MAMARIA C/PROL AXILAR", 35000),
    ("ABDOMINAL", 30000),
    ("RENAL BILATERAL", 30000),
    ("HBP", 30000),
    ("VESICOPROSTATICA", 38000),
    ("TIROIDEA", 30000),
    ("TESTICULAR", 32000),
    ("PLEURAL", 30000),
    ("INGUINAL BILATERAL", 38000),
    ("INGUINAL", 32000),
    ("PARTES BLANDAS", 32000),
    ("MUSCULO ESQUELETICO", 35000),
    ("ARTICULAR", 37000),
    ("CADERAS", 32000),
    ("ECOFAST", 30000),
    ("VESICOPROSTATICA PRE Y POST", 38000),
    ("VESICAL C/MEDICION POST MICC", 35000),
    ("RVP", 42000),
    ("RVP PRE Y POST", 46000),
    ("RENAL VESICAL", 36000),
    ("RENOVESICAL PRE Y POST", 39000),
    ("VESICAL", 30000),
    ("TN", 50000),
    ("SCAN FETAL", 50000),
    ("CERVICOMETRIA", 30000),
    ("CEREBRAL", 42000),
    ("DOPPLER FETAL", 50000),
    ("DOPPLER DE VASOS DEL CUELLO", 44000),
    ("DOPPLER ARTERIAL RENAL BILATERAL", 45000),
    ("DOPPLER ABDOMINAL", 45000),
    ("DOPPLER PARTES BLANDAS", 40000),
    ("DOPPLER GINECOLOGICO", 45000),
    ("DOPPLER TIROIDEO", 45000),
    ("DOPPLER ARTERIAS UTERINAS", 45000),
    ("DOPPLER TESTICULAR", 48000),
    ("DOPPLER TV", 45000),
    ("DOPPLER ARTERIAL O VENOSO DE M.I.", 48000),
    ("DOPPLER ARTERIAL Y VENOSO M.I.", 60000),
    ("DOPPLER MAMARIO", 45000),
    ("DOPPLER RENAL BILATERAL", 60000),
    ("PIEL Y PARTES BLANDAS", 35000),
    ("PROSTATICA", 34000),
    ("RENAL", 30000),
]

db = SessionLocal()
insertados = 0
omitidos = 0

for nombre, precio in DATOS:
    existe = db.query(TipoEcografia).filter(TipoEcografia.nombre == nombre).first()
    if existe:
        omitidos += 1
        print(f"  omitido (ya existe): {nombre}")
        continue
    db.add(TipoEcografia(nombre=nombre, precio=Decimal(precio)))
    insertados += 1

db.commit()
db.close()
print(f"\nListo: {insertados} insertados, {omitidos} omitidos.")
