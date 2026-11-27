"""Hash de contraseñas y tokens de sesión (solo biblioteca estándar)."""
import hashlib
import hmac
import secrets

ITERACIONES = 120_000


def _derivar(password: str, sal: str) -> str:
    clave = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(sal), ITERACIONES
    )
    return clave.hex()


def hashear_password(password: str) -> str:
    """Devuelve 'sal$hash' usando PBKDF2-SHA256."""
    sal = secrets.token_hex(16)
    return f"{sal}${_derivar(password, sal)}"


def verificar_password(password: str, almacenado: str) -> bool:
    try:
        sal, esperado = almacenado.split("$")
        return hmac.compare_digest(_derivar(password, sal), esperado)
    except ValueError:
        return False


def generar_token() -> str:
    return secrets.token_urlsafe(32)