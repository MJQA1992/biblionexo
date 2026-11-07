from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario
from app.schemas import SancionCreate, SancionCreateRequest
from app.security import require_bibliotecario
from app.services.sanciones_service import (
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
