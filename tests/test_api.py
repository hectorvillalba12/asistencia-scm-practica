import pytest

from backend import services


def login(client, username, password):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def alta(client, headers, dni="40123456", nombre="Ana", apellido="Pérez", **extra):
    return client.post(
        "/api/alumnos",
        headers=headers,
        json={"dni": dni, "nombre": nombre, "apellido": apellido, **extra},
    )


@pytest.fixture()
def headers_admin(client, sesion_factory):
    with sesion_factory() as db:
        services.crear_usuario(db, "admin", "admin12345", "admin")
    return login(client, "admin", "admin12345")


@pytest.fixture()
def curso(client, headers_admin):
    docente = client.post(
        "/api/docentes",
        headers=headers_admin,
        json={
            "dni": "30111222", "nombre": "Marta", "apellido": "Díaz",
            "username": "mdiaz", "password": "clave12345",
        },
    ).json()
    return client.post(
        "/api/cursos",
        headers=headers_admin,
        json={"nombre": "Programación III", "docente_id": docente["id"], "limite_faltas": 0},
    ).json()


# ---------- autenticación ----------
def test_sin_token_401(client):
    assert client.get("/api/alumnos").status_code == 401


def test_login_incorrecto(client, headers_admin):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "mala"})
    assert r.status_code == 401


def test_me_y_logout(client, headers_admin):
    assert client.get("/api/auth/me", headers=headers_admin).json()["rol"] == "admin"
    assert client.post("/api/auth/logout", headers=headers_admin).status_code == 204
    assert client.get("/api/auth/me", headers=headers_admin).status_code == 401


# ---------- altas ----------
def test_alta_alumno_y_duplicado(client, headers_admin):
    assert alta(client, headers_admin).status_code == 201
    assert alta(client, headers_admin).status_code == 409


def test_dni_invalido(client, headers_admin):
    assert alta(client, headers_admin, dni="123").status_code == 422


def test_horario_invalido(client, headers_admin, curso):
    r = client.post(
        "/api/horarios",
        headers=headers_admin,
        json={"curso_id": curso["id"], "dia_semana": 0,
              "hora_inicio": "20:00", "hora_fin": "19:00"},
    )
    assert r.status_code == 422


# ---------- permisos por rol ----------
def test_docente_no_puede_crear_alumnos(client, headers_admin, curso):
    headers = login(client, "mdiaz", "clave12345")
    assert alta(client, headers).status_code == 403


def test_alumno_solo_ve_su_informe(client, headers_admin):
    alta(client, headers_admin, password="clave12345")
    alta(client, headers_admin, dni="38111222", nombre="Luis", apellido="Gómez")
    headers = login(client, "40123456", "clave12345")
    assert client.get("/api/informes/alumno/40123456", headers=headers).status_code == 200
    assert client.get("/api/informes/alumno/38111222", headers=headers).status_code == 403
    assert client.get("/api/informes/total", headers=headers).status_code == 403


# ---------- flujo completo ----------
def test_flujo_asistencia_y_limite_de_faltas(client, headers_admin, curso):
    alta(client, headers_admin)
    alta(client, headers_admin, dni="38111222", nombre="Luis", apellido="Gómez")
    for dni in ("40123456", "38111222"):
        r = client.post(
            "/api/inscripciones",
            headers=headers_admin,
            json={"dni": dni, "curso_id": curso["id"]},
        )
        assert r.status_code == 201

    body = {"dni": "40123456", "curso_id": curso["id"], "estado": "presente"}
    assert client.post("/api/asistencias", headers=headers_admin, json=body).status_code == 201
    assert client.post("/api/asistencias", headers=headers_admin, json=body).status_code == 409

    r = client.post(
        "/api/asistencias/ausentes", headers=headers_admin, json={"curso_id": curso["id"]}
    )
    assert r.json()["marcados"] == 1

    total = client.get("/api/informes/total", headers=headers_admin).json()
    assert total["presentes"] == 1
    assert total["ausentes"] == 1
    assert total["alumnos_libres"] == 1  # límite 0: una falta ya es "libre"

    informe = client.get("/api/informes/alumno/38111222", headers=headers_admin).json()
    assert informe["cursos"][0]["regularidad"] == "libre"