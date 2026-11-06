from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas, services
from .database import Base, engine, get_db

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # crea las tablas si no existen
    yield


app = FastAPI(title="Sistema de Control de Asistencia", version="3.0.0", lifespan=lifespan)


@app.post("/api/alumnos", response_model=schemas.AlumnoOut, status_code=201)
def crear_alumno(datos: schemas.AlumnoCreate, db: Session = Depends(get_db)):
    return services.crear_alumno(db, datos.dni, datos.nombre, datos.apellido)


@app.get("/api/alumnos", response_model=list[schemas.AlumnoOut])
def listar_alumnos(db: Session = Depends(get_db)):
    return db.scalars(select(models.Alumno).order_by(models.Alumno.apellido)).all()


@app.post("/api/asistencias", response_model=schemas.AsistenciaOut, status_code=201)
def registrar_asistencia(datos: schemas.AsistenciaCreate, db: Session = Depends(get_db)):
    registro = services.registrar_asistencia(db, datos.dni, datos.materia, datos.estado)
    return services.a_salida(registro)


@app.post("/api/asistencias/ausentes")
def marcar_ausentes(datos: schemas.AusentesCreate, db: Session = Depends(get_db)):
    cantidad = services.marcar_ausentes(db, datos.materia, datos.fecha or date.today())
    return {"marcados": cantidad}


@app.get("/api/asistencias", response_model=list[schemas.AsistenciaOut])
def listar_asistencias(
    fecha: date | None = None, materia: str | None = None, db: Session = Depends(get_db)
):
    return [services.a_salida(a) for a in services.listar_asistencias(db, fecha, materia)]


@app.get("/api/alumnos/{dni}/informe", response_model=schemas.InformeOut)
def informe_alumno(dni: str, materia: str | None = None, db: Session = Depends(get_db)):
    return services.informe_alumno(db, dni, materia)


# Siempre al final: sirve el frontend en "/"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")