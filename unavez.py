# Ejecutar una vez en la consola Python dentro de C:\consultorio
from app.database import SessionLocal
from app.models.user import User
from app.auth import hash_password
db = SessionLocal()
admin = User(username="admin", email="admin@consultorio.com", full_name="Administrador", hashed_password=hash_password("tu_password"), role="superadmin")
db.add(admin); db.commit()