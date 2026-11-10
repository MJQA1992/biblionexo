from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario
from app.schemas import PrestamoCreate, PrestamoCreateRequest, DevolucionRequest
from app.security import require_bibliotecario
from reglas_negocio.prestamos_service import (
    consultar_disponibilidad,
    agregar_prestamo,
    registrar_devolucion,
    consultar_prestamos,
)

router = APIRouter(prefix="/api/v1", tags=["Préstamos y Disponibilidad"])

@router.get("/disponibilidad")
def endpoint_disponibilidad(
    criterio: str = "",
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    try:
        datos = consultar_disponibilidad(db, criterio)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    libros_out = []
    for item in datos["libros"]:
        libro = item["libro"]
        libros_out.append({
            "id": libro.id,
            "isbn": libro.isbn,
            "titulo": libro.titulo,
            "autor": libro.autor,
            "categoria": libro.categoria,
            "total_ejemplares": item["total_ejemplares"],
            "disponibles": item["disponibles"],
            "sin_ejemplares": item["sin_ejemplares"],
            "ejemplares": item["ejemplares"],
        })
    return {"libros": libros_out, "mensaje": datos["mensaje"]}

@router.get("/prestamos")
def listar_prestamos(
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    prestamos = consultar_prestamos(db, solo_activos=solo_activos)
    return [
        {
            "id": p.id,
            "usuario_id": p.usuario_id,
            "usuario_nombre": p.usuario.nombre if p.usuario else "",
            "ejemplar_id": p.ejemplar_id,
            "codigo_inventario": p.ejemplar.codigo_inventario if p.ejemplar else "",
            "libro_titulo": p.ejemplar.libro.titulo if (p.ejemplar and p.ejemplar.libro) else "",
            "fecha_prestamo": p.fecha_prestamo,
            "fecha_limite": p.fecha_limite,
            "fecha_devolucion": p.fecha_devolucion,
            "estado": "Activo" if p.fecha_devolucion is None else "Devuelto",
        }
        for p in prestamos
    ]

@router.post("/prestamos", status_code=status.HTTP_201_CREATED)
def crear_prestamo_endpoint(
    payload: PrestamoCreateRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    try:
        p = agregar_prestamo(
            db,
            PrestamoCreate(
                usuario_id=payload.usuario_id,
                ejemplar_id=payload.ejemplar_id,
                fecha_limite=payload.fecha_limite,
                fecha_prestamo=payload.fecha_prestamo,
            ),
        )
        return {
            "id": p.id,
            "usuario_id": p.usuario_id,
            "ejemplar_id": p.ejemplar_id,
            "fecha_prestamo": p.fecha_prestamo,
            "fecha_limite": p.fecha_limite,
            "fecha_devolucion": p.fecha_devolucion,
            "mensaje": f"Préstamo #{p.id} registrado exitosamente.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

@router.post("/prestamos/devolver")
def devolver_prestamo_endpoint(
    payload: DevolucionRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    try:
        p = registrar_devolucion(db, prestamo_id=payload.prestamo_id, fecha_devolucion=payload.fecha_devolucion)
        return {
            "id": p.id,
            "fecha_devolucion": p.fecha_devolucion,
            "mensaje": f"Devolución registrada para el préstamo #{p.id}.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
