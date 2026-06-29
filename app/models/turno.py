from sqlalchemy import Column, Integer, String, Date, Time, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False)
    medico_id = Column(Integer, ForeignKey("medicos.id", ondelete="CASCADE"), nullable=False)
    especialidad_id = Column(Integer, ForeignKey("especialidades.id", ondelete="SET NULL"), nullable=True)
    fecha = Column(Date, nullable=False)
    hora = Column(Time, nullable=False)
    estado = Column(String(20), nullable=False, default="pendiente")
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    paciente = relationship("Paciente", backref="turnos")
    medico = relationship("Medico", backref="turnos")
    especialidad = relationship("Especialidad", backref="turnos")
