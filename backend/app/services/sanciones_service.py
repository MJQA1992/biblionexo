from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Prestamo, Sancion, Usuario
from app.schemas import SancionCreate

def consultar_vencimientos(db: Session, fecha_referencia: Optional[date] = None) -> list[dict]:
    ref = fecha_referencia or date.today()
    prestamos_activos = (
        db.query(Prestamo)
        .filter(Prestamo.fecha_devolucion.is_(None))
        .order_by(Prestamo.fecha_limite.asc())
        .all()
    )
    vencidos = []
    for p in prestamos_activos:
        es_vencido = p.fecha_devolucion is None and p.fecha_limite < ref
        if es_vencido:
            dias_atraso = (ref - p.fecha_limite).days
            vencidos.append({
                "prestamo": p,
                "usuario": p.usuario,
                "ejemplar": p.ejemplar,
                "libro": p.ejemplar.libro,
                "dias_atraso": dias_atraso,
            })
    return vencidos

def agregar_sancion(db: Session, datos: SancionCreate, fecha_hoy: Optional[date] = None) -> Sancion:
    hoy = fecha_hoy or date.today()
    motivo = (datos.motivo or "").strip()
    if not motivo:
        raise ValueError("El motivo de la sanción es obligatorio.")

    usuario = db.query(Usuario).filter(Usuario.id == datos.usuario_id).first()
    if not usuario:
        raise ValueError("El usuario indicado no existe.")

    if datos.prestamo_id is not None:
        prestamo = db.query(Prestamo).filter(Prestamo.id == datos.prestamo_id).first()
        if not prestamo:
            raise ValueError("El préstamo asociado no existe.")
        if prestamo.usuario_id != usuario.id:
            raise ValueError("El préstamo indicado no pertenece al usuario seleccionado.")
        duplicada = (
            db.query(Sancion)
            .filter(
                Sancion.prestamo_id == datos.prestamo_id,
                Sancion.motivo == motivo,
                Sancion.estado == "Activa",
            )
            .first()
        )
        if duplicada:
            raise ValueError("Ya existe una sanción activa para ese préstamo con el mismo motivo.")

    if datos.fecha_fin < hoy:
        raise ValueError("La fecha de fin de la sanción no puede ser anterior a hoy.")

    sancion = Sancion(
        usuario_id=usuario.id,
        prestamo_id=datos.prestamo_id,
        motivo=motivo,
        fecha_inicio=hoy,
        fecha_fin=datos.fecha_fin,
        estado="Activa",
    )
    db.add(sancion)
    db.commit()
    db.refresh(sancion)
    return sancion

def consultar_sanciones(db: Session, estado: str = "", usuario_id: Optional[int] = None) -> list[Sancion]:
    query = db.query(Sancion)
    if estado and estado.strip():
        query = query.filter(Sancion.estado == estado.strip())
    if usuario_id is not None:
        query = query.filter(Sancion.usuario_id == usuario_id)
    return query.order_by(Sancion.id.desc()).all()
