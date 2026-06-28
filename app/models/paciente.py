from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text
from sqlalchemy.sql import func
from ..database import Base


class Paciente(Base):
    __tablename__ = "pacientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    dni = Column(String(20), nullable=True, unique=True)
    fecha_nacimiento = Column(Date, nullable=True)
    telefono = Column(String(30), nullable=True)
    whatsapp = Column(String(30), nullable=True)
    email = Column(String(150), nullable=True)
    notas = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def nombre_completo(self):
        return f"{self.apellido}, {self.nombre}"
