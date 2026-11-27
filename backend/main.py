"""API del Sistema de Control de Asistencia (multiusuario)."""
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, Header
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import informes, models, schemas, services
from .database import Base, SessionLocal, engine, get_db
from .deps import requiere_roles, usuario_actual

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

solo_admin = requiere_roles("admin")
admin_o_docente = requiere_roles("admin", "docente")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        services.asegurar_admin(db)
    yield


app = FastAPI(
    title="Sistema de Control de Asistencia", version="4.0.0", lifespan=lifespan
)


# ---------- autenticación ----------
@app.post("/api/auth/login", response_model=schemas.TokenOut)
def login(datos: schemas.LoginIn, db: Session = Depends(get_db)):
    sesion = services.iniciar_sesion(db, datos.username, datos.password)
    return {
        "token": sesion.token,
        "username": sesion.usuario.username,
        "rol": sesion.usuario.rol,
    }


@app.post("/api/auth/logout", status_code=204)
def logout(
    authorization: str = Header(),
    _: models.Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    services.cerrar_sesion(db, authorization[7:])


@app.get("/api/auth/me", response_model=schemas.UsuarioOut)
def yo(usuario: models.Usuario = Depends(usuario_actual)):
    return usuario


@app.post("/api/usuarios", response_model=schemas.UsuarioOut, status_code=201)
def crear_usuario(
    datos: schemas.UsuarioCreate,
    _: models.Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    return services.crear_usuario(db, datos.username, datos.password, datos.rol)


# ---------- altas ----------
@app.post("/api/alumnos", response_model=schemas.AlumnoOut, status_code=201)
def crear_alumno(
    datos: schemas.AlumnoCreate,
    _: models.Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    return services.crear_alumno(
        db, datos.dni, datos.nombre, datos.apellido, datos.password
    )


@app.get("/api/alumnos", response_model=list[schemas.AlumnoOut])
def listar_alumnos(
    _: models.Usuario = Depends(admin_o_docente), db: Session = Depends(get_db)
):
    return db.scalars(select(models.Alumno).order_by(models.Alumno.apellido)).all()


@app.post("/api/docentes", response_model=schemas.DocenteOut, status_code=201)
def crear_docente(
    datos: schemas.DocenteCreate,
    _: models.Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    return services.crear_docente(
        db, datos.dni, datos.nombre, datos.apellido, datos.username, datos.password
    )


@app.get("/api/docentes", response_model=list[schemas.DocenteOut])
def listar_docentes(
    _: models.Usuario = Depends(solo_admin), db: Session = Depends(get_db)
):
    return db.scalars(select(models.Docente).order_by(models.Docente.apellido)).all()


@app.post("/api/cursos", response_model=schemas.CursoOut, status_code=201)
def crear_curso(
    datos: schemas.CursoCreate,
    _: models.Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    return services.crear_curso(db, datos.nombre, datos.docente_id, datos.limite_faltas)


@app.get("/api/cursos", response_model=list[schemas.CursoOut])
def listar_cursos(
    usuario: models.Usuario = Depends(admin_o_docente),
    db: Session = Depends(get_db),
):
    return services.listar_cursos(db, usuario)


@app.post("/api/horarios", response_model=schemas.HorarioOut, status_code=201)
def crear_horario(
    datos: schemas.HorarioCreate,
    _: models.Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    return services.crear_horario(
        db, datos.curso_id, datos.dia_semana, datos.hora_inicio, datos.hora_fin
    )


@app.get("/api/cursos/{curso_id}/horarios", response_model=list[schemas.HorarioOut])
def listar_horarios(
    curso_id: int,
    usuario: models.Usuario = Depends(admin_o_docente),
    db: Session = Depends(get_db),
):
    services.verificar_acceso_curso(db, usuario, services.obtener_curso(db, curso_id))
    return services.listar_horarios(db, curso_id)


@app.post("/api/inscripciones", response_model=schemas.InscripcionOut, status_code=201)
def inscribir(
    datos: schemas.InscripcionCreate,
    _: models.Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    inscripcion = services.inscribir(db, datos.dni, datos.curso_id)
    return {"dni": datos.dni, "curso_id": inscripcion.curso_id}


# ---------- asistencia ----------
@app.post("/api/asistencias", response_model=schemas.AsistenciaOut, status_code=201)
def registrar_asistencia(
    datos: schemas.AsistenciaCreate,
    usuario: models.Usuario = Depends(admin_o_docente),
    db: Session = Depends(get_db),
):
    curso = services.obtener_curso(db, datos.curso_id)
    services.verificar_acceso_curso(db, usuario, curso)
    registro = services.registrar_asistencia(
        db, datos.dni, datos.curso_id, datos.estado
    )
    return services.a_salida(registro)


@app.post("/api/asistencias/ausentes")
def marcar_ausentes(
    datos: schemas.AusentesCreate,
    usuario: models.Usuario = Depends(admin_o_docente),
    db: Session = Depends(get_db),
):
    curso = services.obtener_curso(db, datos.curso_id)
    services.verificar_acceso_curso(db, usuario, curso)
    cantidad = services.marcar_ausentes(db, curso.id, datos.fecha or date.today())
    return {"marcados": cantidad}


@app.get("/api/asistencias", response_model=list[schemas.AsistenciaOut])
def listar_asistencias(
    fecha: date | None = None,
    curso_id: int | None = None,
    usuario: models.Usuario = Depends(admin_o_docente),
    db: Session = Depends(get_db),
):
    registros = services.listar_asistencias(db, usuario, fecha, curso_id)
    return [services.a_salida(a) for a in registros]


# ---------- informes ----------
@app.get("/api/informes/total", response_model=schemas.InformeTotalOut)
def informe_total(
    curso_id: int | None = None,
    usuario: models.Usuario = Depends(admin_o_docente),
    db: Session = Depends(get_db),
):
    return informes.informe_total(db, usuario, curso_id)


@app.get("/api/informes/alumno/{dni}", response_model=schemas.InformeAlumnoOut)
def informe_alumno(
    dni: str,
    curso_id: int | None = None,
    usuario: models.Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    return informes.informe_alumno(db, usuario, dni, curso_id)


# Siempre al final: sirve el frontend en "/"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")