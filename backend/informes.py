"""Cálculo de informes de asistencia y control del límite de faltas."""
from collections import Counter, defaultdict
from collections.abc import Mapping

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import services
from .models import Alumno, Asistencia, Curso, Inscripcion, Usuario

# Se considera "en riesgo" al llegar al 80 % del límite de faltas.
PORCENTAJE_RIESGO = 80


def _porcentaje(asistidas: int, total: int) -> float:
    return round(asistidas / total * 100, 1) if total else 0.0


def calcular_resumen(conteo: Mapping[str, int], limite: int) -> dict:
    """Resumen puro (sin base de datos) de un alumno en un curso.

    - La tardanza cuenta como asistencia.
    - Solo las ausencias cuentan como falta.
    - 'libre' cuando las faltas superan el límite.
    """
    presentes = conteo.get("presente", 0)
    tardanzas = conteo.get("tardanza", 0)
    ausentes = conteo.get("ausente", 0)
    total = presentes + tardanzas + ausentes

    if ausentes > limite:
        regularidad = "libre"
    elif ausentes > 0 and ausentes * 100 >= limite * PORCENTAJE_RIESGO:
        regularidad = "en_riesgo"
    else:
        regularidad = "regular"

    return {
        "total_clases": total,
        "presentes": presentes,
        "tardanzas": tardanzas,
        "ausentes": ausentes,
        "porcentaje_asistencia": _porcentaje(presentes + tardanzas, total),
        "limite_faltas": limite,
        "faltas_restantes": max(limite - ausentes, 0),
        "regularidad": regularidad,
    }


def _conteos(
    db: Session,
    curso_ids: list[int] | None = None,
    alumno_id: int | None = None,
) -> dict[tuple[int, int], Counter]:
    """Cuenta estados por (alumno, curso) con una sola consulta."""
    stmt = select(
        Asistencia.alumno_id,
        Asistencia.curso_id,
        Asistencia.estado,
        func.count(),
    ).group_by(Asistencia.alumno_id, Asistencia.curso_id, Asistencia.estado)
    if curso_ids is not None:
        stmt = stmt.where(Asistencia.curso_id.in_(curso_ids))
    if alumno_id is not None:
        stmt = stmt.where(Asistencia.alumno_id == alumno_id)

    resultado: dict[tuple[int, int], Counter] = defaultdict(Counter)
    for alu_id, cur_id, estado, cantidad in db.execute(stmt):
        resultado[(alu_id, cur_id)][estado] = cantidad
    return resultado


def _fila(alumno: Alumno, curso: Curso, conteo: Mapping[str, int]) -> dict:
    return {
        "dni": alumno.dni,
        "nombre": alumno.nombre,
        "apellido": alumno.apellido,
        "curso_id": curso.id,
        "curso": curso.nombre,
        **calcular_resumen(conteo, curso.limite_faltas),
    }


def _cursos_visibles(
    db: Session, usuario: Usuario, curso_id: int | None = None
) -> list[Curso]:
    cursos = list(db.scalars(select(Curso).order_by(Curso.nombre)).all())
    if curso_id is not None:
        cursos = [c for c in cursos if c.id == curso_id]
    if usuario.rol == "docente":
        propios = {c.id for c in services.listar_cursos(db, usuario)}
        cursos = [c for c in cursos if c.id in propios]
    return cursos


def informe_alumno(
    db: Session, usuario: Usuario, dni: str, curso_id: int | None = None
) -> dict:
    alumno = services.obtener_alumno(db, dni)
    if usuario.rol == "alumno" and usuario.username != alumno.dni:
        raise HTTPException(
            status_code=403, detail="Solo podés ver tu propio informe"
        )

    inscriptos = set(
        db.scalars(
            select(Inscripcion.curso_id).where(Inscripcion.alumno_id == alumno.id)
        )
    )
    cursos = [
        c for c in _cursos_visibles(db, usuario, curso_id) if c.id in inscriptos
    ]
    conteos = _conteos(db, alumno_id=alumno.id)
    filas = [_fila(alumno, c, conteos[(alumno.id, c.id)]) for c in cursos]

    registros = db.scalars(
        select(Asistencia)
        .where(
            Asistencia.alumno_id == alumno.id,
            Asistencia.curso_id.in_([c.id for c in cursos]),
        )
        .order_by(Asistencia.fecha.desc())
    ).all()

    return {
        "dni": alumno.dni,
        "nombre": alumno.nombre,
        "apellido": alumno.apellido,
        "cursos": filas,
        "detalle": [services.a_salida(r) for r in registros],
    }


def informe_total(
    db: Session, usuario: Usuario, curso_id: int | None = None
) -> dict:
    cursos = _cursos_visibles(db, usuario, curso_id)
    por_id = {c.id: c for c in cursos}
    conteos = _conteos(db, curso_ids=list(por_id))

    pares = db.execute(
        select(Alumno, Inscripcion.curso_id)
        .join(Inscripcion, Inscripcion.alumno_id == Alumno.id)
        .where(Inscripcion.curso_id.in_(list(por_id)))
        .order_by(Alumno.apellido, Alumno.nombre)
    ).all()
    filas = [
        _fila(alumno, por_id[cid], conteos[(alumno.id, cid)])
        for alumno, cid in pares
    ]

    total: Counter = Counter()
    for conteo in conteos.values():
        total.update(conteo)
    asistidas = total["presente"] + total["tardanza"]
    registros = asistidas + total["ausente"]

    return {
        "total_registros": registros,
        "presentes": total["presente"],
        "tardanzas": total["tardanza"],
        "ausentes": total["ausente"],
        "porcentaje_asistencia": _porcentaje(asistidas, registros),
        "alumnos_libres": sum(1 for f in filas if f["regularidad"] == "libre"),
        "filas": filas,
    }