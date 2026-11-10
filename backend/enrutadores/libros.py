from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario
from app.schemas import LibroCreate, LibroCreateRequest, LibroResponse
from app.security import require_bibliotecario
from reglas_negocio.libros_service import agregar_libro, consultar_libros

router = APIRouter(prefix="/api/v1/libros", tags=["Libros"])

@router.get("", response_model=List[LibroResponse])
def listar_libros(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    return consultar_libros(db, q=q)

@router.post("", response_model=LibroResponse, status_code=status.HTTP_201_CREATED)
def crear_libro_endpoint(
    payload: LibroCreateRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    try:
        return agregar_libro(
            db,
            LibroCreate(
                isbn=payload.isbn,
                titulo=payload.titulo,
                autor=payload.autor,
                categoria=payload.categoria,
                cantidad_ejemplares=payload.cantidad_ejemplares,
                ubicacion=payload.ubicacion,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
