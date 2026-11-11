"""Enrutador de la épica Gestión de Usuarios.

Endpoints (prefijo ``/api/v1/usuarios``, solo rol Bibliotecario):
    GET  ""  -- HU Consultar usuario: lista y filtra usuarios.
    POST ""  -- HU Agregar usuario: registra un usuario nuevo.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.conexion_bd import get_db
from app.entidades_bd import Usuario
from app.contratos_datos import UsuarioCreate, UsuarioCreateRequest, UsuarioResponse
from app.seguridad_acceso import require_bibliotecario
from reglas_negocio.reglas_usuarios import crear_usuario, consultar_usuarios

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios"])

@router.get("", response_model=List[UsuarioResponse])
def listar_usuarios(
    q: str = "",
    rol: str = "",
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    """Lista los usuarios, con filtros opcionales.

    Args:
        q: texto a buscar (parcial, sin distinguir mayúsculas) en nombre o correo.
        rol: rol exacto a filtrar ("Bibliotecario" o "Lector").
        db: sesión de base de datos.
        current_user: bibliotecario autenticado (control de acceso).

    Returns:
        list[UsuarioResponse]: usuarios ordenados por id ascendente.
    """
    return consultar_usuarios(db, q=q, rol=rol)

@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_usuario(
    payload: UsuarioCreateRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    """Registra un usuario nuevo.

    Args:
        payload: nombre, correo, rol y contraseña inicial.
        db: sesión de base de datos.
        current_user: bibliotecario autenticado (control de acceso).

    Returns:
        UsuarioResponse: usuario creado (HTTP 201), sin datos de contraseña.

    Raises:
        HTTPException 400: si se incumple alguna regla de negocio (campos
            vacíos, correo inválido o duplicado, contraseña corta, rol inválido).
    """
    try:
        return crear_usuario(
            db,
            UsuarioCreate(
                nombre=payload.nombre,
                correo=payload.correo,
                rol=payload.rol,
                password=payload.password,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
