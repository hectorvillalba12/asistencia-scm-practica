"""Dependencias de FastAPI: autenticación y control de roles."""
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from . import services
from .database import get_db
from .models import Usuario


def usuario_actual(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Usuario:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta iniciar sesión")
    usuario = services.usuario_por_token(db, authorization[7:])
    if usuario is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o vencida")
    return usuario


def requiere_roles(*roles: str):
    """Crea una dependencia que exige que el usuario tenga alguno de los roles."""

    def dependencia(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=403, detail="No tenés permiso para esta acción"
            )
        return usuario

    return dependencia