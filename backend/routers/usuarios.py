from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioCreateRequest, UsuarioResponse
from app.security import require_bibliotecario
from app.services.usuarios_service import crear_usuario, consultar_usuarios

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios"])

@router.get("", response_model=List[UsuarioResponse])
def listar_usuarios(
    q: str = "",
    rol: str = "",
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    return consultar_usuarios(db, q=q, rol=rol)

@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_usuario(
    payload: UsuarioCreateRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
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
