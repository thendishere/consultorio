from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Time, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

# Tabla de asociación médico ↔ especialidad
medico_especialidad = Table(
    "medico_especialidad",
    Base.metadata,
    Column("medico_id", Integer, ForeignKey("medicos.id", ondelete="CASCADE"), primary_key=True),
    Column("especialidad_id", Integer, ForeignKey("especialidades.id", ondelete="CASCADE"), primary_key=True),
)


class Especialidad(Base):
    __tablename__ = "especialidades"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    duracion_turno = Column(Integer, nullable=False, default=20)  # minutos
    precio = Column(Numeric(10, 2), nullable=True)
    activa = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    medicos = relationship("Medico", secondary=medico_especialidad, back_populates="especialidades")
    disponibilidades = relationship("Disponibilidad", back_populates="especialidad", cascade="all, delete-orphan")
    procedimientos = relationship("TipoProcedimiento", back_populates="especialidad", cascade="all, delete-orphan")


class Medico(Base):
    __tablename__ = "medicos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    matricula = Column(String(50), nullable=True)
    es_ecografo = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="medico_perfil")
    especialidades = relationship("Especialidad", secondary=medico_especialidad, back_populates="medicos")
    disponibilidades = relationship("Disponibilidad", back_populates="medico", cascade="all, delete-orphan")


# Días de semana: 0=Lunes … 6=Domingo
class Disponibilidad(Base):
    __tablename__ = "disponibilidades"

    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id", ondelete="CASCADE"), nullable=False)
    especialidad_id = Column(Integer, ForeignKey("especialidades.id", ondelete="SET NULL"), nullable=True)
    es_ecografia = Column(Boolean, default=False)  # True cuando el turno es para ecografías
    dia_semana = Column(Integer, nullable=False)  # 0=Lunes … 6=Domingo
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    activa = Column(Boolean, default=True)

    medico = relationship("Medico", back_populates="disponibilidades")
    especialidad = relationship("Especialidad", back_populates="disponibilidades")


class TipoProcedimiento(Base):
    __tablename__ = "tipos_procedimiento"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    especialidad_id = Column(Integer, ForeignKey("especialidades.id", ondelete="CASCADE"), nullable=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    especialidad = relationship("Especialidad", back_populates="procedimientos")


class TipoEcografia(Base):
    __tablename__ = "tipos_ecografia"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False, unique=True)
    precio = Column(Numeric(10, 2), nullable=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
