from datetime import date, datetime, timedelta

import pytest
from fastapi import HTTPException

from backend import services

LUNES_1910 = datetime(2026, 11, 23, 19, 10)  # lunes, dentro de la tolerancia
LUNES_1930 = datetime(2026, 11, 23, 19, 30)  # lunes, pasada la tolerancia
MARTES = datetime(2026, 11, 24, 19, 10)  # sin clase


# ---------- usuarios y sesiones ----------
def test_crear_usuario_duplicado(db):
    services.crear_usuario(db, "ana", "clave12345", "docente")
    with pytest.raises(HTTPException) as e:
        services.crear_usuario(db, "ana", "clave12345", "docente")
    assert e.value.status_code == 409


def test_rol_invalido(db):
    with pytest.raises(HTTPException) as e:
        services.crear_usuario(db, "ana", "clave12345", "rey")
    assert e.value.status_code == 422


def test_asegurar_admin_es_idempotente(db):
    services.asegurar_admin(db)
    services.asegurar_admin(db)
    sesion = services.iniciar_sesion(db, "admin", "admin1234")
    assert sesion.usuario.rol == "admin"


def test_login_incorrecto(db, admin):
    with pytest.raises(HTTPException) as e:
        services.iniciar_sesion(db, "admin", "mala-clave")
    assert e.value.status_code == 401


def test_sesion_vence(db, admin):
    ahora = datetime(2026, 11, 23, 10, 0)
    sesion = services.iniciar_sesion(db, "admin", "admin12345", ahora=ahora)
    assert services.usuario_por_token(db, sesion.token, ahora) is not None
    vencida = ahora + timedelta(hours=13)
    assert services.usuario_por_token(db, sesion.token, vencida) is None


def test_cerrar_sesion(db, admin):
    sesion = services.iniciar_sesion(db, "admin", "admin12345")
    services.cerrar_sesion(db, sesion.token)
    assert services.usuario_por_token(db, sesion.token) is None


# ---------- altas ----------
def test_alumno_con_password_crea_usuario(db):
    services.crear_alumno(db, "40123456", "Ana", "Pérez", "clave12345")
    sesion = services.iniciar_sesion(db, "40123456", "clave12345")
    assert sesion.usuario.rol == "alumno"


def test_alumno_duplicado(db, escenario):
    with pytest.raises(HTTPException) as e:
        services.crear_alumno(db, "40123456", "Otra", "Persona")
    assert e.value.status_code == 409


def test_curso_con_docente_inexistente(db):
    with pytest.raises(HTTPException) as e:
        services.crear_curso(db, "X", 999, 3)
    assert e.value.status_code == 404


def test_inscripcion_duplicada(db, escenario):
    with pytest.raises(HTTPException) as e:
        services.inscribir(db, "40123456", escenario.curso.id)
    assert e.value.status_code == 409


# ---------- asistencia ----------
def test_presente_dentro_de_tolerancia(db, escenario):
    r = services.registrar_asistencia(
        db, "40123456", escenario.curso.id, None, ahora=LUNES_1910
    )
    assert r.estado == "presente"


def test_tardanza_fuera_de_tolerancia(db, escenario):
    r = services.registrar_asistencia(
        db, "40123456", escenario.curso.id, None, ahora=LUNES_1930
    )
    assert r.estado == "tardanza"


def test_sin_clase_hoy(db, escenario):
    with pytest.raises(HTTPException) as e:
        services.registrar_asistencia(
            db, "40123456", escenario.curso.id, None, ahora=MARTES
        )
    assert e.value.status_code == 409


def test_registro_duplicado(db, escenario):
    services.registrar_asistencia(
        db, "40123456", escenario.curso.id, "presente", ahora=LUNES_1910
    )
    with pytest.raises(HTTPException) as e:
        services.registrar_asistencia(
            db, "40123456", escenario.curso.id, "presente", ahora=LUNES_1910
        )
    assert e.value.status_code == 409


def test_alumno_no_inscripto(db, escenario):
    services.crear_alumno(db, "38111222", "Luis", "Gómez")
    with pytest.raises(HTTPException) as e:
        services.registrar_asistencia(
            db, "38111222", escenario.curso.id, "presente", ahora=LUNES_1910
        )
    assert e.value.status_code == 409


def test_ausente_se_corrige_si_llega(db, escenario):
    services.marcar_ausentes(db, escenario.curso.id, date(2026, 11, 23))
    r = services.registrar_asistencia(
        db, "40123456", escenario.curso.id, "tardanza", ahora=LUNES_1930
    )
    assert r.estado == "tardanza"
    assert r.hora is not None


def test_marcar_ausentes_solo_inscriptos_sin_registro(db, escenario):
    luis = services.crear_alumno(db, "38111222", "Luis", "Gómez")
    services.inscribir(db, luis.dni, escenario.curso.id)
    services.crear_alumno(db, "37000111", "Eva", "Ruiz")  # no inscripta
    services.registrar_asistencia(
        db, "40123456", escenario.curso.id, "presente", ahora=LUNES_1910
    )
    marcados = services.marcar_ausentes(db, escenario.curso.id, date(2026, 11, 23))
    assert marcados == 1


# ---------- permisos ----------
def test_docente_solo_ve_sus_cursos(db, escenario):
    otro = services.crear_docente(db, "30999888", "Luis", "Gómez", "lgomez", "clave12345")
    services.crear_curso(db, "Álgebra", otro.id, 3)
    from sqlalchemy import select
    from backend.models import Usuario

    usuario = db.scalar(select(Usuario).where(Usuario.username == "mdiaz"))
    cursos = services.listar_cursos(db, usuario)
    assert [c.nombre for c in cursos] == ["Programación III"]


def test_docente_ajeno_no_accede_al_curso(db, escenario):
    from backend.models import Usuario  # noqa: F401

    ajeno = services.crear_docente(db, "30999888", "Luis", "Gómez", "lgomez", "clave12345")
    usuario = services.usuario_por_token(
        db, services.iniciar_sesion(db, "lgomez", "clave12345").token
    )
    assert ajeno.usuario_id == usuario.id
    with pytest.raises(HTTPException) as e:
        services.verificar_acceso_curso(db, usuario, escenario.curso)
    assert e.value.status_code == 403