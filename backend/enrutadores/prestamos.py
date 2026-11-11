"""Enrutador de la épica Circulación: disponibilidad, préstamos y devoluciones.

Endpoints (prefijo ``/api/v1``, solo rol Bibliotecario):
    GET  /disponibilidad      -- HU Consultar disponibilidad.
    GET  /prestamos           -- HU Consultar préstamos.
    POST /prestamos           -- HU Agregar préstamo.
    POST /prestamos/devolver  -- HU Registrar devolución.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.conexion_bd import get_db
from app.entidades_bd import Usuario
from app.contratos_datos import PrestamoCreate, PrestamoCreateRequest, DevolucionRequest
from app.seguridad_acceso import require_bibliotecario
from reglas_negocio.reglas_prestamos import (
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
    """Consulta la disponibilidad de ejemplares por título o ISBN.

    Args:
        criterio: texto parcial del título o del ISBN (obligatorio).
        db: sesión de base de datos.
        current_user: bibliotecario autenticado (control de acceso).

    Returns:
        dict: ``libros`` (lista con datos del libro, ``total_ejemplares``,
        ``disponibles``, ``sin_ejemplares`` y detalle de ``ejemplares``) y
        ``mensaje`` ("Sin resultados" si no hubo coincidencias, o None).

    Raises:
        HTTPException 400: si el criterio está vacío.
    """
    try:
        datos = consultar_disponibilidad(db, criterio)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Convierte el objeto ORM Libro de cada resultado en un dict serializable.
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
    """Lista los préstamos, del más reciente al más antiguo.

    Args:
        solo_activos: si es True, solo devuelve préstamos sin devolución.
        db: sesión de base de datos.
        current_user: bibliotecario autenticado (control de acceso).

    Returns:
        list[dict]: préstamos con datos del usuario, ejemplar y libro, fechas
        y ``estado`` calculado ("Activo" o "Devuelto").
    """
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
    """Registra un préstamo de un ejemplar a un usuario.

    Args:
        payload: ``usuario_id``, ``ejemplar_id``, ``fecha_limite`` y
            ``fecha_prestamo`` opcional (por defecto, hoy).
        db: sesión de base de datos.
        current_user: bibliotecario autenticado (control de acceso).

    Returns:
        dict: datos del préstamo creado y mensaje de confirmación (HTTP 201).

    Raises:
        HTTPException 400: si el usuario o ejemplar no existen, la fecha
            límite es anterior a la de préstamo, el usuario tiene una sanción
            activa o el ejemplar ya está prestado.
    """
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
    """Registra la devolución de un préstamo activo.

    Args:
        payload: ``prestamo_id`` y ``fecha_devolucion`` opcional (por defecto, hoy).
        db: sesión de base de datos.
        current_user: bibliotecario autenticado (control de acceso).

    Returns:
        dict: ``id``, ``fecha_devolucion`` y mensaje de confirmación.

    Raises:
        HTTPException 400: si el préstamo no existe o ya fue devuelto.
    """
    try:
        p = registrar_devolucion(db, prestamo_id=payload.prestamo_id, fecha_devolucion=payload.fecha_devolucion)
        return {
            "id": p.id,
            "fecha_devolucion": p.fecha_devolucion,
            "mensaje": f"Devolución registrada para el préstamo #{p.id}.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
