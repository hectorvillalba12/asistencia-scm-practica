import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app


@pytest.fixture()
def client():
    # Base en memoria: no toca tu asistencia.db real
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Sesion = sessionmaker(bind=engine, autoflush=False)

    def override_db():
        db = Sesion()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def alta(client, dni="40123456", nombre="Ana", apellido="Pérez"):
    return client.post("/api/alumnos", json={"dni": dni, "nombre": nombre, "apellido": apellido})


def test_alta_alumno_y_dni_duplicado(client):
    assert alta(client).status_code == 201
    assert alta(client).status_code == 409


def test_dni_invalido(client):
    r = alta(client, dni="123")
    assert r.status_code == 422


def test_registrar_asistencia_y_duplicado(client):
    alta(client)
    r = client.post("/api/asistencias", json={"dni": "40123456", "estado": "presente"})
    assert r.status_code == 201
    assert r.json()["estado"] == "presente"
    r2 = client.post("/api/asistencias", json={"dni": "40123456", "estado": "presente"})
    assert r2.status_code == 409


def test_asistencia_dni_inexistente(client):
    r = client.post("/api/asistencias", json={"dni": "99999999"})
    assert r.status_code == 404


def test_marcar_ausentes_e_informe(client):
    alta(client, dni="40123456")
    alta(client, dni="38111222", nombre="Luis", apellido="Gómez")
    client.post("/api/asistencias", json={"dni": "40123456", "estado": "tardanza"})

    r = client.post("/api/asistencias/ausentes", json={})
    assert r.json()["marcados"] == 1

    informe = client.get("/api/alumnos/38111222/informe").json()
    assert informe["ausentes"] == 1
    assert informe["porcentaje_asistencia"] == 0.0

    informe = client.get("/api/alumnos/40123456/informe").json()
    assert informe["tardanzas"] == 1
    assert informe["porcentaje_asistencia"] == 100.0