from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend import informes, services
from backend.models import Asistencia, Usuario


def cargar(db, escenario, estados):
    """Carga un registro por día con los estados indicados."""
    for i, estado in enumerate(estados):
        db.add(
            Asistencia(
                alumno_id=escenario.alumno.id,
                curso_id=escenario.curso.id,
                fecha=date(2026, 11, 1) + timedelta(days=i),
                hora=None,
                estado=estado,
            )
        )
    db.commit()


# ---------- función pura ----------
def test_resumen_regular():
    r = informes.calcular_resumen({"presente": 3, "tardanza": 1, "ausente": 1}, 5)
    assert r["total_clases"] == 5
    assert r["porcentaje_asistencia"] == 80.0
    assert r["faltas_restantes"] == 4
    assert r["regularidad"] == "regular"


def test_resumen_en_riesgo():
    r = informes.calcular_resumen({"presente": 1, "ausente": 4}, 5)
    assert r["regularidad"] == "en_riesgo"
    assert r["faltas_restantes"] == 1


def test_resumen_en_el_limite_no_es_libre():
    r = informes.calcular_resumen({"ausente": 5}, 5)
    assert r["regularidad"] == "en_riesgo"


def test_resumen_libre_al_superar_limite():
    r = informes.calcular_resumen({"ausente": 3}, 2)
    assert r["regularidad"] == "libre"
    assert r["faltas_restantes"] == 0


def test_resumen_sin_clases():
    r = informes.calcular_resumen({}, 5)
    assert r["porcentaje_asistencia"] == 0.0
    assert r["regularidad"] == "regular"


def test_limite_cero_cualquier_falta_es_libre():
    assert informes.calcular_resumen({"ausente": 1}, 0)["regularidad"] == "libre"


# ---------- con base de datos ----------
def test_informe_alumno(db, admin, escenario):
    cargar(db, escenario, ["presente", "tardanza", "ausente"])
    inf = informes.informe_alumno(db, admin, "40123456")
    fila = inf["cursos"][0]
    assert fila["ausentes"] == 1
    assert fila["porcentaje_asistencia"] == 66.7
    assert fila["regularidad"] == "regular"
    assert len(inf["detalle"]) == 3


def test_informe_alumno_libre_por_limite(db, admin, escenario):
    cargar(db, escenario, ["ausente", "ausente", "ausente"])  # límite = 2
    inf = informes.informe_alumno(db, admin, "40123456")
    assert inf["cursos"][0]["regularidad"] == "libre"


def test_alumno_no_ve_informe_ajeno(db, escenario):
    usuario = services.crear_usuario(db, "99999999", "clave12345", "alumno")
    with pytest.raises(HTTPException) as e:
        informes.informe_alumno(db, usuario, "40123456")
    assert e.value.status_code == 403


def test_alumno_ve_su_informe(db, escenario):
    usuario = services.crear_usuario(db, "40123456", "clave12345", "alumno")
    assert informes.informe_alumno(db, usuario, "40123456")["dni"] == "40123456"


def test_informe_total(db, admin, escenario):
    luis = services.crear_alumno(db, "38111222", "Luis", "Gómez")
    services.inscribir(db, luis.dni, escenario.curso.id)
    cargar(db, escenario, ["presente", "ausente", "ausente", "ausente"])
    total = informes.informe_total(db, admin)
    assert total["total_registros"] == 4
    assert total["presentes"] == 1
    assert total["ausentes"] == 3
    assert total["porcentaje_asistencia"] == 25.0
    assert total["alumnos_libres"] == 1
    assert len(total["filas"]) == 2  # Ana y Luis (Luis sin registros)


def test_informe_total_docente_ve_solo_lo_suyo(db, escenario):
    docente = db.scalar(select(Usuario).where(Usuario.username == "mdiaz"))
    assert len(informes.informe_total(db, docente)["filas"]) == 1

    services.crear_docente(db, "30999888", "Luis", "Gómez", "lgomez", "clave12345")
    ajeno = db.scalar(select(Usuario).where(Usuario.username == "lgomez"))
    assert informes.informe_total(db, ajeno)["filas"] == []