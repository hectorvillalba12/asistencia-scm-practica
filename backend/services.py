from collections import Counter
from datetime import date, datetime, time

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Alumno, Asistencia
from .schemas import validar_dni

# Pasada esta hora, la asistencia se registra como "tardanza".
# Cambiala según el horario de tu cursada.
HORA_LIMITE = time(19, 15)


def a_salida(a: Asistencia) -> dict:
    return {
        "id": a.id,
        "dni": a.alumno.dni,
        "nombre": a.alumno.nombre,
        "apellido": a.alumno.apellido,
        "materia": a.materia,
        "fecha": a.fecha,
        "hora": a.hora,
        "estado": a.estado,
    }


def obtener_alumno(db: Session, dni: str) -> Alumno:
    try:
        dni = validar_dni(dni)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    alumno = db.scalar(select(Alumno).where(Alumno.dni == dni))
    if not alumno:
        raise HTTPException(status_code=404, detail=f"No existe un alumno con DNI {dni}")
    return alumno


def crear_alumno(db: Session, dni: str, nombre: str, apellido: str) -> Alumno:
    if db.scalar(select(Alumno).where(Alumno.dni == dni)):
        raise HTTPException(status_code=409, detail=f"Ya existe un alumno con DNI {dni}")
    alumno = Alumno(dni=dni, nombre=nombre, apellido=apellido)
    db.add(alumno)
    db.commit()
    db.refresh(alumno)
    return alumno


def registrar_asistencia(db: Session, dni: str, materia: str, estado: str | None) -> Asistencia:
    alumno = obtener_alumno(db, dni)
    ahora = datetime.now()

    if estado is None:
        estado = "presente" if ahora.time() <= HORA_LIMITE else "tardanza"

    hora = None if estado == "ausente" else ahora.time().replace(microsecond=0)

    existente = db.scalar(
        select(Asistencia).where(
            Asistencia.alumno_id == alumno.id,
            Asistencia.materia == materia,
            Asistencia.fecha == ahora.date(),
        )
    )

    if existente:
        # Si estaba marcado ausente y después llegó, se corrige el registro.
        if existente.estado == "ausente" and estado != "ausente":
            existente.estado = estado
            existente.hora = hora
            db.commit()
            db.refresh(existente)
            return existente
        raise HTTPException(
            status_code=409,
            detail=f"{alumno.apellido} ya tiene registro hoy en {materia} ({existente.estado})",
        )

    registro = Asistencia(
        alumno_id=alumno.id, materia=materia, fecha=ahora.date(), hora=hora, estado=estado
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def marcar_ausentes(db: Session, materia: str, fecha: date) -> int:
    """Marca como ausentes a todos los alumnos sin registro en esa materia y fecha."""
    con_registro = select(Asistencia.alumno_id).where(
        Asistencia.materia == materia, Asistencia.fecha == fecha
    )
    pendientes = db.scalars(select(Alumno).where(Alumno.id.not_in(con_registro))).all()
    for alumno in pendientes:
        db.add(
            Asistencia(alumno_id=alumno.id, materia=materia, fecha=fecha, hora=None, estado="ausente")
        )
    db.commit()
    return len(pendientes)


def listar_asistencias(db: Session, fecha: date | None, materia: str | None) -> list[Asistencia]:
    stmt = select(Asistencia).order_by(Asistencia.fecha.desc(), Asistencia.hora.desc())
    if fecha:
        stmt = stmt.where(Asistencia.fecha == fecha)
    if materia:
        stmt = stmt.where(Asistencia.materia == materia)
    return list(db.scalars(stmt).all())


def informe_alumno(db: Session, dni: str, materia: str | None) -> dict:
    alumno = obtener_alumno(db, dni)
    stmt = (
        select(Asistencia)
        .where(Asistencia.alumno_id == alumno.id)
        .order_by(Asistencia.fecha.desc())
    )
    if materia:
        stmt = stmt.where(Asistencia.materia == materia)
    registros = list(db.scalars(stmt).all())

    conteo = Counter(r.estado for r in registros)
    total = len(registros)
    asistidas = conteo["presente"] + conteo["tardanza"]  # la tardanza cuenta como asistencia

    return {
        "dni": alumno.dni,
        "nombre": alumno.nombre,
        "apellido": alumno.apellido,
        "materia": materia,
        "total_clases": total,
        "presentes": conteo["presente"],
        "tardanzas": conteo["tardanza"],
        "ausentes": conteo["ausente"],
        "porcentaje_asistencia": round(asistidas / total * 100, 1) if total else 0.0,
        "detalle": [a_salida(r) for r in registros],
    }