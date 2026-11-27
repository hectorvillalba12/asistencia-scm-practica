"""Fixtures compartidas: base en memoria y datos de ejemplo."""
from datetime import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import services
from backend.database import Base, get_db
from backend.main import app


@pytest.fixture()
def sesion_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


@pytest.fixture()
def db(sesion_factory):
    with sesion_factory() as sesion:
        yield sesion


@pytest.fixture()
def client(sesion_factory):
    def override_db():
        with sesion_factory() as sesion:
            yield sesion

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def admin(db):
    return services.crear_usuario(db, "admin", "admin12345", "admin")


@pytest.fixture()
def escenario(db):
    """Docente + curso (límite 2, clase los lunes 19:00) + alumno inscripto."""
    docente = services.crear_docente(
        db, "30111222", "Marta", "Díaz", "mdiaz", "clave12345"
    )
    curso = services.crear_curso(db, "Programación III", docente.id, 2)
    services.crear_horario(db, curso.id, 0, time(19, 0), time(22, 0))
    alumno = services.crear_alumno(db, "40123456", "Ana", "Pérez")
    services.inscribir(db, alumno.dni, curso.id)
    return SimpleNamespace(docente=docente, curso=curso, alumno=alumno)