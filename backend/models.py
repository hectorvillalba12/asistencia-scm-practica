"""Modelos de base de datos."""
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(10))  # admin | docente | alumno
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Sesion(Base):
    __tablename__ = "sesiones"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    expira: Mapped[datetime] = mapped_column(DateTime)

    usuario: Mapped[Usuario] = relationship()


class Alumno(Base):
    __tablename__ = "alumnos"

    id: Mapped[int] = mapped_column(primary_key=True)
    dni: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    apellido: Mapped[str] = mapped_column(String(80))

    asistencias: Mapped[list["Asistencia"]] = relationship(
        back_populates="alumno", cascade="all, delete-orphan"
    )


class Docente(Base):
    __tablename__ = "docentes"

    id: Mapped[int] = mapped_column(primary_key=True)
    dni: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    apellido: Mapped[str] = mapped_column(String(80))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), unique=True)


class Curso(Base):
    __tablename__ = "cursos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    docente_id: Mapped[int] = mapped_column(ForeignKey("docentes.id"))
    limite_faltas: Mapped[int] = mapped_column(default=5)

    horarios: Mapped[list["Horario"]] = relationship(
        cascade="all, delete-orphan"
    )


class Horario(Base):
    __tablename__ = "horarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    curso_id: Mapped[int] = mapped_column(ForeignKey("cursos.id"))
    dia_semana: Mapped[int]  # 0 = lunes ... 6 = domingo
    hora_inicio: Mapped[time] = mapped_column(Time)
    hora_fin: Mapped[time] = mapped_column(Time)


class Inscripcion(Base):
    __tablename__ = "inscripciones"
    __table_args__ = (
        UniqueConstraint("alumno_id", "curso_id", name="uq_alumno_curso"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    alumno_id: Mapped[int] = mapped_column(ForeignKey("alumnos.id"))
    curso_id: Mapped[int] = mapped_column(ForeignKey("cursos.id"))


class Asistencia(Base):
    __tablename__ = "asistencias"
    __table_args__ = (
        UniqueConstraint(
            "alumno_id", "curso_id", "fecha", name="uq_alumno_curso_fecha"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    alumno_id: Mapped[int] = mapped_column(ForeignKey("alumnos.id"))
    curso_id: Mapped[int] = mapped_column(ForeignKey("cursos.id"))
    fecha: Mapped[date] = mapped_column(Date)
    hora: Mapped[time | None] = mapped_column(Time, nullable=True)
    estado: Mapped[str] = mapped_column(String(10))  # presente|tardanza|ausente

    alumno: Mapped[Alumno] = relationship(back_populates="asistencias")
    curso: Mapped[Curso] = relationship()