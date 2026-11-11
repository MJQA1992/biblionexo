"""Enrutador de autenticación: inicio de sesión, cierre y perfil actual.

Endpoints (prefijo ``/api/v1``):
    POST /login   -- valida credenciales y emite un token Bearer.
    POST /logout  -- limpia la sesión por cookie.
    GET  /me      -- devuelve los datos del usuario autenticado.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.conexion_bd import get_db
from app.entidades_bd import Usuario
from app.contratos_datos import LoginRequest
from app.seguridad_acceso import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/v1", tags=["Autenticación"])

@router.post("/login")
def login(credentials: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Autentica a un usuario por correo y contraseña.

    El correo se normaliza (sin espacios y en minúsculas) antes de buscarlo.
    Si las credenciales son válidas, se emite un token de acceso y, además,
    se guarda ``user_id`` y ``user_rol`` en la sesión por cookie.

    Args:
        credentials: correo y contraseña enviados en el cuerpo JSON.
        request: petición actual (para acceder a la sesión).
        db: sesión de base de datos.

    Returns:
        dict: ``access_token``, ``token_type`` ("bearer") y los datos
        públicos del usuario (``id``, ``nombre``, ``correo``, ``rol``).

    Raises:
        HTTPException 401: si el correo no existe o la contraseña no coincide
            (mismo mensaje en ambos casos para no revelar qué falló).
    """
    correo = credentials.correo.strip().lower()
    user = db.query(Usuario).filter(Usuario.correo == correo).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas.")
    token = create_access_token(user)
    if "session" in request.scope:
        request.session["user_id"] = user.id
        request.session["user_rol"] = user.rol
    return {
        "access_token": token,
        "token_type": "bearer",
        "id": user.id,
        "nombre": user.nombre,
        "correo": user.correo,
        "rol": user.rol,
    }

@router.post("/logout")
def logout(request: Request):
    """Cierra la sesión por cookie del servidor.

    El token Bearer no se invalida en el servidor (no hay lista de
    revocación); el frontend lo descarta borrándolo de ``localStorage``.

    Returns:
        dict: mensaje de confirmación.
    """
    if "session" in request.scope:
        request.session.clear()
    return {"mensaje": "Sesión cerrada correctamente."}

@router.get("/me")
def me(current_user: Usuario = Depends(get_current_user)):
    """Devuelve el perfil del usuario autenticado (cualquier rol).

    Returns:
        dict: ``id``, ``nombre``, ``correo`` y ``rol``.

    Raises:
        HTTPException 401: si no hay una sesión o token válidos.
    """
    return {
        "id": current_user.id,
        "nombre": current_user.nombre,
        "correo": current_user.correo,
        "rol": current_user.rol,
    }