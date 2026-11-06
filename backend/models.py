from datetime import date, time

from sqlalchemy import Date, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Alumno(Base):
    __tablename__ = "alumnos"

    id: Mapped[int] = mapped_column(primary_key=True)
    dni: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    apellido: Mapped[str] = mapped_column(String(80))

    asistencias: Mapped[list["Asistencia"]] = relationship(
        back_populates="alumno", cascade="all, delete-orphan"
    )


class Asistencia(Base):
    __tablename__ = "asistencias"
    __table_args__ = (
        UniqueConstraint("alumno_id", "materia", "fecha", name="uq_alumno_materia_fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    alumno_id: Mapped[int] = mapped_column(ForeignKey("alumnos.id"))
    materia: Mapped[str] = mapped_column(String(100))
    fecha: Mapped[date] = mapped_column(Date)
    hora: Mapped[time | None] = mapped_column(Time, nullable=True)
    estado: Mapped[str] = mapped_column(String(10))  # presente | tardanza | ausente

    alumno: Mapped[Alumno] = relationship(back_populates="asistencias")