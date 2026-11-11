"""Enrutador de la épica Catálogo de Libros.

Endpoints (prefijo ``/api/v1/libros``, solo rol Bibliotecario):
    GET  ""  -- HU Consultar libros: lista y busca en el catálogo.
    POST ""  -- HU Agregar libros: registra un título y sus ejemplares.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.conexion_bd import get_db
from app.entidades_bd import Usuario
from app.contratos_datos import LibroCreate, LibroCreateRequest, LibroResponse
from app.seguridad_acceso import require_bibliotecario
from reglas_negocio.reglas_libros import agregar_libro, consultar_libros

router = APIRouter(prefix="/api/v1/libros", tags=["Libros"])

@router.get("", response_model=List[LibroResponse])
def listar_libros(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    """Lista los libros del catálogo con sus ejemplares.

    Args:
        q: texto a buscar (parcial) en título, autor, ISBN o categoría.
        db: sesión de base de datos.
        current_user: bibliotecario autenticado (control de acceso).

    Returns:
        list[LibroResponse]: libros ordenados por id ascendente.
    """
    return consultar_libros(db, q=q)

@router.post("", response_model=LibroResponse, status_code=status.HTTP_201_CREATED)
def crear_libro_endpoint(
    payload: LibroCreateRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    """Registra un libro y genera automáticamente sus ejemplares.

    Args:
        payload: ISBN, título, autor, categoría, cantidad de ejemplares (1-50)
            y ubicación física.
        db: sesión de base de datos.
        current_user: bibliotecario autenticado (control de acceso).

    Returns:
        LibroResponse: libro creado con sus ejemplares (HTTP 201).

    Raises:
        HTTPException 400: si faltan campos, la cantidad está fuera de rango
            o el ISBN ya existe.
    """
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
