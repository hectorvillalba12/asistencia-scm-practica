"""Configuración central del sistema."""
import os

TOLERANCIA_MINUTOS = 15  # minutos después del inicio hasta ser "tardanza"
LIMITE_FALTAS_DEFECTO = 5
SESION_HORAS = 12

ROLES = ("admin", "docente", "alumno")

# Admin inicial: se crea solo si no existe ninguno. ¡Cambiá la clave!
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")