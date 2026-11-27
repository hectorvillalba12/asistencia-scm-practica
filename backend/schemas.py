"""Esquemas de entrada y salida de la API."""
from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from . import config

Estado = Literal["presente", "tardanza", "ausente"]
Rol = Literal["admin", "docente", "alumno"]
Regularidad = Literal["regular", "en_riesgo", "libre"]


def validar_dni(valor: str) -> str:
    valor = valor.strip()
    if not (valor.isdigit() and 7 <= len(valor) <= 8):
        raise ValueError("El DNI debe tener 7 u 8 dígitos numéricos")
    return valor


# ---------- entrada ----------
class ConDni(BaseModel):
    dni: str

    @field_validator("dni")
    @classmethod
    def dni_valido(cls, v: str) -> str:
        return validar_dni(v)


class Persona(ConDni):
    nombre: str
    apellido: str

    @field_validator("nombre", "apellido")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El campo no puede estar vacío")
        return v


class LoginIn(BaseModel):
    username: str
    password: str


class UsuarioCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    rol: Rol


class AlumnoCreate(Persona):
    # Si se informa, se crea un usuario (login = DNI) para que el alumno
    # pueda consultar su propio informe.
    password: str | None = Field(default=None, min_length=8)


class DocenteCreate(Persona):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)


class CursoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    docente_id: int
    limite_faltas: int = Field(default=config.LIMITE_FALTAS_DEFECTO, ge=0)


class HorarioCreate(BaseModel):
    curso_id: int
    dia_semana: int = Field(ge=0, le=6)
    hora_inicio: time
    hora_fin: time

    @model_validator(mode="after")
    def fin_posterior(self) -> "HorarioCreate":
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("La hora de fin debe ser posterior al inicio")
        return self


class InscripcionCreate(ConDni):
    curso_id: int


class AsistenciaCreate(ConDni):
    curso_id: int
    estado: Estado | None = None  # None = se calcula según el horario


class AusentesCreate(BaseModel):
    curso_id: int
    fecha: date | None = None  # None = hoy


# ---------- salida ----------
class UsuarioOut(BaseModel):
    id: int
    username: str
    rol: Rol

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    token: str
    username: str
    rol: Rol


class AlumnoOut(BaseModel):
    id: int
    dni: str
    nombre: str
    apellido: str

    model_config = {"from_attributes": True}


class DocenteOut(AlumnoOut):
    pass


class CursoOut(BaseModel):
    id: int
    nombre: str
    docente_id: int
    limite_faltas: int

    model_config = {"from_attributes": True}


class HorarioOut(BaseModel):
    id: int
    curso_id: int
    dia_semana: int
    hora_inicio: time
    hora_fin: time

    model_config = {"from_attributes": True}


class InscripcionOut(BaseModel):
    dni: str
    curso_id: int


class AsistenciaOut(BaseModel):
    id: int
    dni: str
    nombre: str
    apellido: str
    curso_id: int
    curso: str
    fecha: date
    hora: time | None
    estado: Estado


class ResumenOut(BaseModel):
    dni: str
    nombre: str
    apellido: str
    curso_id: int
    curso: str
    total_clases: int
    presentes: int
    tardanzas: int
    ausentes: int
    porcentaje_asistencia: float
    limite_faltas: int
    faltas_restantes: int
    regularidad: Regularidad


class InformeAlumnoOut(BaseModel):
    dni: str
    nombre: str
    apellido: str
    cursos: list[ResumenOut]
    detalle: list[AsistenciaOut]


class InformeTotalOut(BaseModel):
    total_registros: int
    presentes: int
    tardanzas: int
    ausentes: int
    porcentaje_asistencia: float
    alumnos_libres: int
    filas: list[ResumenOut]