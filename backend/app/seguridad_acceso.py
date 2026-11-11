"""Seguridad de BiblioNexo: contraseñas, tokens de acceso y autorización por rol.

Componentes:
    - Hash de contraseñas con PBKDF2-HMAC-SHA256 (120 000 iteraciones y sal
      aleatoria de 16 bytes), almacenado como ``pbkdf2_sha256$<sal>$<hash_hex>``.
    - Token de acceso propio con formato ``<payload_base64url>.<firma_hex>``,
      donde la firma es HMAC-SHA256 del payload con ``SESSION_SECRET``.
      El token no lleva fecha de expiración.
    - Dependencias FastAPI ``get_current_user`` y ``require_bibliotecario``
      para proteger los endpoints.
"""
import hashlib
import hmac
import secrets
import base64
import json
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import SESSION_SECRET
from app.conexion_bd import get_db
from app.entidades_bd import Usuario

# Esquema Bearer opcional: con auto_error=False no lanza 401 si falta la
# cabecera Authorization, para poder intentar luego la sesión por cookie.
bearer_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Genera el hash seguro de una contraseña en texto plano.

    Args:
        password: contraseña original.

    Returns:
        str: cadena ``pbkdf2_sha256$<sal_hex>$<derivada_hex>``. Cada llamada
        produce un resultado distinto porque la sal es aleatoria.
    """
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Comprueba si una contraseña coincide con un hash almacenado.

    Recalcula la derivada con la misma sal y la compara en tiempo constante
    (``hmac.compare_digest``) para evitar ataques de temporización.

    Args:
        password: contraseña introducida por el usuario.
        stored_hash: valor generado previamente por ``hash_password``.

    Returns:
        bool: True si coincide; False si no coincide, si el algoritmo no es
        ``pbkdf2_sha256`` o si el hash tiene un formato inválido.
    """
    try:
        algo, salt, hex_digest = stored_hash.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
        return hmac.compare_digest(dk.hex(), hex_digest)
    except Exception:
        return False

def create_access_token(user: Usuario) -> str:
    """Emite un token de acceso firmado para el usuario autenticado.

    Args:
        user: usuario que inició sesión.

    Returns:
        str: token ``<payload_b64url>.<firma_hex>``. El payload JSON contiene
        ``user_id``, ``rol`` y ``correo``; va codificado, no cifrado.
    """
    payload = {"user_id": user.id, "rol": user.rol, "correo": user.correo}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    b64 = base64.urlsafe_b64encode(raw).decode("utf-8")
    sig = hmac.new(SESSION_SECRET.encode("utf-8"), b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"

def decode_access_token(token: str) -> Optional[dict]:
    """Verifica la firma de un token y devuelve su payload.

    Args:
        token: token generado por ``create_access_token``.

    Returns:
        dict | None: payload decodificado si la firma es válida; None si la
        firma no coincide o el token está mal formado.
    """
    try:
        b64, sig = token.split(".", 1)
        expected = hmac.new(SESSION_SECRET.encode("utf-8"), b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return json.loads(base64.urlsafe_b64decode(b64.encode("utf-8")).decode("utf-8"))
    except Exception:
        return None

def get_current_user(
    request: Request,
     creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Dependencia FastAPI que identifica al usuario autenticado.

    Orden de resolución:
        1. Token Bearer en la cabecera ``Authorization`` (lo usa el frontend).
        2. ``user_id`` guardado en la sesión por cookie (SessionMiddleware).

    Args:
        request: petición HTTP actual.
        creds: credenciales Bearer, si se enviaron.
        db: sesión de base de datos.

    Returns:
        Usuario: usuario autenticado, consultado en la base de datos.

    Raises:
        HTTPException 401: si no hay credenciales válidas ("Debe iniciar
            sesión.") o si el usuario ya no existe ("Sesión inválida.").
    """
    user_id = None
    if creds and creds.credentials:
        data = decode_access_token(creds.credentials)
        if data:
            user_id = data.get("user_id")
    if not user_id and "session" in request.scope:
        user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Debe iniciar sesión.")
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida.")
    return user

def require_bibliotecario(user: Usuario = Depends(get_current_user)) -> Usuario:
    """Dependencia FastAPI que restringe un endpoint al rol Bibliotecario.

    Args:
        user: usuario autenticado (resuelto por ``get_current_user``).

    Returns:
        Usuario: el mismo usuario, si su rol es ``"Bibliotecario"``.

    Raises:
        HTTPException 401: propagada desde ``get_current_user``.
        HTTPException 403: si el usuario autenticado no es Bibliotecario.
    """
    if user.rol != "Bibliotecario":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: se requiere rol Bibliotecario.",
        )
    return user

