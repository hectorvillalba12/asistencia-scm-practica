from datetime import time

import pytest
from pydantic import ValidationError

from backend import schemas


def test_validar_dni_correcto():
    assert schemas.validar_dni(" 40123456 ") == "40123456"


@pytest.mark.parametrize("dni", ["123", "40123ABC", "123456789", ""])
def test_validar_dni_invalido(dni):
    with pytest.raises(ValueError):
        schemas.validar_dni(dni)


def test_alumno_nombre_vacio():
    with pytest.raises(ValidationError):
        schemas.AlumnoCreate(dni="40123456", nombre="  ", apellido="Pérez")


def test_password_corta_rechazada():
    with pytest.raises(ValidationError):
        schemas.AlumnoCreate(
            dni="40123456", nombre="Ana", apellido="Pérez", password="123"
        )


def test_horario_fin_anterior_al_inicio():
    with pytest.raises(ValidationError):
        schemas.HorarioCreate(
            curso_id=1, dia_semana=0, hora_inicio=time(20), hora_fin=time(19)
        )


def test_limite_faltas_negativo():
    with pytest.raises(ValidationError):
        schemas.CursoCreate(nombre="X", docente_id=1, limite_faltas=-1)