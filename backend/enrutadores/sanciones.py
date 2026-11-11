"""Enrutador de la épica Sanciones y Vencimientos.

Endpoints (prefijo ``/api/v1``, solo rol Bibliotecario):
    GET  /vencimientos  -- HU Consultar vencimiento.
    GET  /sanciones     -- HU Consultar sanciones.
    POST /sanciones     -- HU Agregar sanción.
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.conexion_bd import get_db
from app.entidades_bd import Usuario
from app.contratos_datos import SancionCreate, SancionCreateRequest
from app.seguridad_acceso import require_bibliotecario
from reglas_negocio.reglas_sanciones import (
    consultar_vencimientos,
    agregar_sancion,
    consultar_sanciones,
)

router = APIRouter(prefix="/api/v1", tags=["Sanciones y Vencimientos"])

@router.get("/vencimientos")
def listar_vencimientos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    """Lista los préstamos activos cuya fecha límite ya pasó.

    Args:
        db: sesión de base de datos.
        current_user: bibliotecario autenticado (control de acceso).

    Returns:
        dict: ``fecha_corte`` (hoy) y ``vencidos``, lista con datos del
        préstamo, usuario, ejemplar y libro y los ``dias_atraso``,
        ordenada por fecha límite ascendente (los más atrasados primero).
    """
    vencidos = consultar_vencimientos(db)
    return {
        "fecha_corte": date.today(),
        "vencidos": [
            {
                "prestamo_id": item["prestamo"].id,
                "usuario_id": item["usuario"].id,
                "usuario_nombre": item["usuario"].nombre,
                "ejemplar_id": item["ejemplar"].id,
                "codigo_inventario": item["ejemplar"].codigo_inventario,
                "libro_titulo": item["libro"].titulo,
                "fecha_prestamo": item["prestamo"].fecha_prestamo,
                "fecha_limite": item["prestamo"].fecha_limite,
                "dias_atraso": item["dias_atraso"],
            }
            for item in vencidos
        ],
    }

@router.get("/sanciones")
def listar_sanciones(
    estado: str = "",
    usuario_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    """Lista las sanciones, de la más reciente a la más antigua.

    Args:
        estado: estado exacto a filtrar ("Activa" o "Cumplida"); vacío = todos.
        usuario_id: si se indica, solo sanciones de ese usuario.
        db: sesión de base de datos.
        current_user: bibliotecario autenticado (control de acceso).

    Returns:
        list[dict]: sanciones con nombre del usuario, préstamo asociado,
        motivo, fechas y estado.
    """
    sanciones = consultar_sanciones(db, estado=estado, usuario_id=usuario_id)
    return [
        {
            "id": s.id,
            "usuario_id": s.usuario_id,
            "usuario_nombre": s.usuario.nombre if s.usuario else "",
            "prestamo_id": s.prestamo_id,
            "motivo": s.motivo,
            "fecha_inicio": s.fecha_inicio,
            "fecha_fin": s.fecha_fin,
            "estado": s.estado,
        }
        for s in sanciones
    ]

@router.post("/sanciones", status_code=status.HTTP_201_CREATED)
def crear_sancion_endpoint(
    payload: SancionCreateRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_bibliotecario),
):
    """Registra una sanción administrativa a un usuario.

    Args:
        payload: ``usuario_id``, ``prestamo_id`` opcional, ``motivo`` y
            ``fecha_fin``.
        db: sesión de base de datos.
        current_user: bibliotecario autenticado (control de acceso).

    Returns:
        dict: datos de la sanción creada (estado "Activa") y mensaje (HTTP 201).

    Raises:
        HTTPException 400: si el motivo está vacío, el usuario o préstamo no
            existen, el préstamo es de otro usuario, ya hay una sanción activa
            igual para ese préstamo o la fecha de fin es anterior a hoy.
    """
    try:
        s = agregar_sancion(
            db,
            SancionCreate(
                usuario_id=payload.usuario_id,
                prestamo_id=payload.prestamo_id,
                motivo=payload.motivo,
                fecha_fin=payload.fecha_fin,
            ),
        )
        return {
            "id": s.id,
            "usuario_id": s.usuario_id,
            "prestamo_id": s.prestamo_id,
            "motivo": s.motivo,
            "fecha_inicio": s.fecha_inicio,
            "fecha_fin": s.fecha_fin,
            "estado": s.estado,
            "mensaje": f"Sanción #{s.id} registrada exitosamente.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
