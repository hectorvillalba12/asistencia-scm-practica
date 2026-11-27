"""Lógica de negocio: usuarios, sesiones, altas y registro de asistencia."""
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .models import (
    Alumno,
    Asistencia,
    Curso,
    Docente,
    Horario,
    Inscripcion,
    Sesion,
    Usuario,
)
from .schemas import validar_dni
from .security import generar_token, hashear_password, verificar_password


# ---------- usuarios y sesiones ----------
def _agregar_usuario(
    db: Session, username: str, password: str, rol: str
) -> Usuario:
    """Agrega el usuario sin confirmar la transacción (hace flush)."""
    if rol not in config.ROLES:
        raise HTTPException(status_code=422, detail=f"Rol inválido: {rol}")
    if db.scalar(select(Usuario).where(Usuario.username == username)):
        raise HTTPException(
            status_code=409, detail=f"El usuario '{username}' ya existe"
        )
    usuario = Usuario(
        username=username, password_hash=hashear_password(password), rol=rol
    )
    db.add(usuario)
    db.flush()
    return usuario


def crear_usuario(db: Session, username: str, password: str, rol: str) -> Usuario:
    usuario = _agregar_usuario(db, username, password, rol)
    db.commit()
    db.refresh(usuario)
    return usuario


def asegurar_admin(db: Session) -> None:
    """Crea el administrador inicial si no existe ninguno."""
    if not db.scalar(select(Usuario).where(Usuario.rol == "admin")):
        crear_usuario(db, config.ADMIN_USER, config.ADMIN_PASSWORD, "admin")


def iniciar_sesion(
    db: Session, username: str, password: str, ahora: datetime | None = None
) -> Sesion:
    ahora = ahora or datetime.now()
    usuario = db.scalar(select(Usuario).where(Usuario.username == username))
    if (
        usuario is None
        or not usuario.activo
        or not verificar_password(password, usuario.password_hash)
    ):
        raise HTTPException(
            status_code=401, detail="Usuario o contraseña incorrectos"
        )
    sesion = Sesion(
        token=generar_token(),
        usuario_id=usuario.id,
        expira=ahora + timedelta(hours=config.SESION_HORAS),
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion


def usuario_por_token(
    db: Session, token: str, ahora: datetime | None = None
) -> Usuario | None:
    ahora = ahora or datetime.now()
    sesion = db.get(Sesion, token)
    if sesion is None:
        return None
    if sesion.expira < ahora:
        db.delete(sesion)
        db.commit()
        return None
    return sesion.usuario if sesion.usuario.activo else None


def cerrar_sesion(db: Session, token: str) -> None:
    sesion = db.get(Sesion, token)
    if sesion:
        db.delete(sesion)
        db.commit()


# ---------- permisos ----------
def docente_de(db: Session, usuario: Usuario) -> Docente | None:
    return db.scalar(select(Docente).where(Docente.usuario_id == usuario.id))


def listar_cursos(db: Session, usuario: Usuario) -> list[Curso]:
    """Admin ve todos; docente solo los suyos; alumno ninguno."""
    stmt = select(Curso).order_by(Curso.nombre)
    if usuario.rol == "docente":
        docente = docente_de(db, usuario)
        if docente is None:
            return []
        stmt = stmt.where(Curso.docente_id == docente.id)
    elif usuario.rol != "admin":
        return []
    return list(db.scalars(stmt).all())


def verificar_acceso_curso(db: Session, usuario: Usuario, curso: Curso) -> None:
    if usuario.rol == "admin":
        return
    docente = docente_de(db, usuario)
    if usuario.rol == "docente" and docente and curso.docente_id == docente.id:
        return
    raise HTTPException(status_code=403, detail="No tenés permiso sobre este curso")


# ---------- búsquedas ----------
def obtener_alumno(db: Session, dni: str) -> Alumno:
    try:
        dni = validar_dni(dni)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    alumno = db.scalar(select(Alumno).where(Alumno.dni == dni))
    if not alumno:
        raise HTTPException(
            status_code=404, detail=f"No existe un alumno con DNI {dni}"
        )
    return alumno


def obtener_curso(db: Session, curso_id: int) -> Curso:
    curso = db.get(Curso, curso_id)
    if curso is None:
        raise HTTPException(status_code=404, detail=f"No existe el curso {curso_id}")
    return curso


# ---------- altas ----------
def crear_alumno(
    db: Session, dni: str, nombre: str, apellido: str, password: str | None = None
) -> Alumno:
    if db.scalar(select(Alumno).where(Alumno.dni == dni)):
        raise HTTPException(
            status_code=409, detail=f"Ya existe un alumno con DNI {dni}"
        )
    if password:
        _agregar_usuario(db, dni, password, "alumno")
    alumno = Alumno(dni=dni, nombre=nombre, apellido=apellido)
    db.add(alumno)
    db.commit()
    db.refresh(alumno)
    return alumno


def crear_docente(
    db: Session,
    dni: str,
    nombre: str,
    apellido: str,
    username: str,
    password: str,
) -> Docente:
    if db.scalar(select(Docente).where(Docente.dni == dni)):
        raise HTTPException(
            status_code=409, detail=f"Ya existe un docente con DNI {dni}"
        )
    usuario = _agregar_usuario(db, username, password, "docente")
    docente = Docente(
        dni=dni, nombre=nombre, apellido=apellido, usuario_id=usuario.id
    )
    db.add(docente)
    db.commit()
    db.refresh(docente)
    return docente


def crear_curso(
    db: Session, nombre: str, docente_id: int, limite_faltas: int
) -> Curso:
    if db.get(Docente, docente_id) is None:
        raise HTTPException(
            status_code=404, detail=f"No existe el docente {docente_id}"
        )
    curso = Curso(nombre=nombre, docente_id=docente_id, limite_faltas=limite_faltas)
    db.add(curso)
    db.commit()
    db.refresh(curso)
    return curso


def crear_horario(
    db: Session, curso_id: int, dia_semana: int, hora_inicio, hora_fin
) -> Horario:
    curso = obtener_curso(db, curso_id)
    horario = Horario(
        curso_id=curso.id,
        dia_semana=dia_semana,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
    )
    db.add(horario)
    db.commit()
    db.refresh(horario)
    return horario


def listar_horarios(db: Session, curso_id: int) -> list[Horario]:
    stmt = (
        select(Horario)
        .where(Horario.curso_id == curso_id)
        .order_by(Horario.dia_semana, Horario.hora_inicio)
    )
    return list(db.scalars(stmt).all())


def inscribir(db: Session, dni: str, curso_id: int) -> Inscripcion:
    alumno = obtener_alumno(db, dni)
    curso = obtener_curso(db, curso_id)
    if _esta_inscripto(db, alumno.id, curso.id):
        raise HTTPException(
            status_code=409,
            detail=f"{alumno.apellido} ya está inscripto en {curso.nombre}",
        )
    inscripcion = Inscripcion(alumno_id=alumno.id, curso_id=curso.id)
    db.add(inscripcion)
    db.commit()
    db.refresh(inscripcion)
    return inscripcion


def _esta_inscripto(db: Session, alumno_id: int, curso_id: int) -> bool:
    stmt = select(Inscripcion.id).where(
        Inscripcion.alumno_id == alumno_id, Inscripcion.curso_id == curso_id
    )
    return db.scalar(stmt) is not None


# ---------- asistencia ----------
def a_salida(a: Asistencia) -> dict:
    return {
        "id": a.id,
        "dni": a.alumno.dni,
        "nombre": a.alumno.nombre,
        "apellido": a.alumno.apellido,
        "curso_id": a.curso_id,
        "curso": a.curso.nombre,
        "fecha": a.fecha,
        "hora": a.hora,
        "estado": a.estado,
    }


def calcular_estado(curso: Curso, ahora: datetime) -> str:
    """'presente' si llega dentro de la tolerancia del horario de hoy."""
    horario = next(
        (h for h in curso.horarios if h.dia_semana == ahora.weekday()), None
    )
    if horario is None:
        raise HTTPException(
            status_code=409, detail="El curso no tiene clase programada hoy"
        )
    limite = datetime.combine(ahora.date(), horario.hora_inicio) + timedelta(
        minutes=config.TOLERANCIA_MINUTOS
    )
    return "presente" if ahora <= limite else "tardanza"


def registrar_asistencia(
    db: Session,
    dni: str,
    curso_id: int,
    estado: str | None = None,
    ahora: datetime | None = None,
) -> Asistencia:
    ahora = ahora or datetime.now()
    alumno = obtener_alumno(db, dni)
    curso = obtener_curso(db, curso_id)
    if not _esta_inscripto(db, alumno.id, curso.id):
        raise HTTPException(
            status_code=409,
            detail=f"{alumno.apellido} no está inscripto en {curso.nombre}",
        )

    if estado is None:
        estado = calcular_estado(curso, ahora)
    hora = None if estado == "ausente" else ahora.time().replace(microsecond=0)

    existente = db.scalar(
        select(Asistencia).where(
            Asistencia.alumno_id == alumno.id,
            Asistencia.curso_id == curso.id,
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
            detail=(
                f"{alumno.apellido} ya tiene registro hoy en {curso.nombre} "
                f"({existente.estado})"
            ),
        )

    registro = Asistencia(
        alumno_id=alumno.id,
        curso_id=curso.id,
        fecha=ahora.date(),
        hora=hora,
        estado=estado,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def marcar_ausentes(db: Session, curso_id: int, fecha: date) -> int:
    """Marca ausentes a los inscriptos sin registro en ese curso y fecha."""
    curso = obtener_curso(db, curso_id)
    con_registro = select(Asistencia.alumno_id).where(
        Asistencia.curso_id == curso.id, Asistencia.fecha == fecha
    )
    pendientes = db.scalars(
        select(Alumno)
        .join(Inscripcion, Inscripcion.alumno_id == Alumno.id)
        .where(Inscripcion.curso_id == curso.id, Alumno.id.not_in(con_registro))
    ).all()
    for alumno in pendientes:
        db.add(
            Asistencia(
                alumno_id=alumno.id,
                curso_id=curso.id,
                fecha=fecha,
                hora=None,
                estado="ausente",
            )
        )
    db.commit()
    return len(pendientes)


def listar_asistencias(
    db: Session,
    usuario: Usuario,
    fecha: date | None = None,
    curso_id: int | None = None,
) -> list[Asistencia]:
    stmt = select(Asistencia).order_by(Asistencia.fecha.desc(), Asistencia.hora.desc())
    if fecha:
        stmt = stmt.where(Asistencia.fecha == fecha)
    if curso_id:
        stmt = stmt.where(Asistencia.curso_id == curso_id)
    if usuario.rol != "admin":
        propios = [c.id for c in listar_cursos(db, usuario)]
        stmt = stmt.where(Asistencia.curso_id.in_(propios))
    return list(db.scalars(stmt).all())