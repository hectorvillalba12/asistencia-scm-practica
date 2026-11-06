from datetime import date, time
from typing import Literal

from pydantic import BaseModel, field_validator

Estado = Literal["presente", "tardanza", "ausente"]


def validar_dni(valor: str) -> str:
    valor = valor.strip()
    if not (valor.isdigit() and 7 <= len(valor) <= 8):
        raise ValueError("El DNI debe tener 7 u 8 dígitos numéricos")
    return valor


class AlumnoCreate(BaseModel):
    dni: str
    nombre: str
    apellido: str

    @field_validator("dni")
    @classmethod
    def dni_valido(cls, v: str) -> str:
        return validar_dni(v)

    @field_validator("nombre", "apellido")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El campo no puede estar vacío")
        return v


class AlumnoOut(BaseModel):
    id: int
    dni: str
    nombre: str
    apellido: str

    model_config = {"from_attributes": True}


class AsistenciaCreate(BaseModel):
    dni: str
    materia: str = "Programación III"
    estado: Estado | None = None  # None = se calcula según la hora

    @field_validator("dni")
    @classmethod
    def dni_valido(cls, v: str) -> str:
        return validar_dni(v)


class AusentesCreate(BaseModel):
    materia: str = "Programación III"
    fecha: date | None = None  # None = hoy


class AsistenciaOut(BaseModel):
    id: int
    dni: str
    nombre: str
    apellido: str
    materia: str
    fecha: date
    hora: time | None
    estado: Estado


class InformeOut(BaseModel):
    dni: str
    nombre: str
    apellido: str
    materia: str | None
    total_clases: int
    presentes: int
    tardanzas: int
    ausentes: int
    porcentaje_asistencia: float
    detalle: list[AsistenciaOut]