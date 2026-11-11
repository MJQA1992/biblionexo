"""Servicio de dominio de vencimientos y sanciones administrativas.

Reglas de la HU Agregar sanción:
    - El motivo es obligatorio y el usuario debe existir.
    - Si se asocia un préstamo, debe existir y pertenecer al mismo usuario,
      y no puede haber otra sanción activa con el mismo motivo para ese préstamo.
    - La fecha de fin no puede ser anterior a hoy.
    - Toda sanción nueva se crea con fecha de inicio hoy y estado "Activa".
"""
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from app.entidades_bd import Prestamo, Sancion, Usuario
from app.contratos_datos import SancionCreate

def consultar_vencimientos(db: Session, fecha_referencia: Optional[date] = None) -> list[dict]:
    """Obtiene los préstamos activos con la fecha límite vencida.

    Un préstamo está vencido si no se ha devuelto y su ``fecha_limite`` es
    estrictamente anterior a la fecha de referencia.

    Args:
        db: sesión de base de datos.
        fecha_referencia: fecha de corte; por defecto, hoy.

    Returns:
        list[dict]: un dict por préstamo vencido con ``prestamo``,
        ``usuario``, ``ejemplar``, ``libro`` (objetos ORM) y ``dias_atraso``
        (int), ordenados por fecha límite ascendente.
    """
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
    """Registra una sanción administrativa validando las reglas de negocio.

    Args:
        db: sesión de base de datos.
        datos: usuario, motivo, fecha de fin y préstamo asociado opcional.
        fecha_hoy: fecha de referencia; permite fijar "hoy" en pruebas.
            Por defecto, ``date.today()``.

    Returns:
        Sancion: sanción creada con estado "Activa".

    Raises:
        ValueError: si el motivo está vacío, el usuario o el préstamo no
            existen, el préstamo pertenece a otro usuario, ya existe una
            sanción activa duplicada o la fecha de fin es anterior a hoy.
    """
    hoy = fecha_hoy or date.today()
    motivo = (datos.motivo or "").strip()
    if not motivo:
        raise ValueError("El motivo de la sanción es obligatorio.")

    usuario = db.query(Usuario).filter(Usuario.id == datos.usuario_id).first()
    if not usuario:
        raise ValueError("El usuario indicado no existe.")

    # Validaciones adicionales solo cuando la sanción se liga a un préstamo.
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
    """Lista las sanciones con filtros opcionales.

    Args:
        db: sesión de base de datos.
        estado: estado exacto ("Activa" o "Cumplida"); vacío = sin filtro.
        usuario_id: id del usuario; None = todos los usuarios.

    Returns:
        list[Sancion]: sanciones ordenadas por id descendente.
    """
    query = db.query(Sancion)
    if estado and estado.strip():
        query = query.filter(Sancion.estado == estado.strip())
    if usuario_id is not None:
        query = query.filter(Sancion.usuario_id == usuario_id)
    return query.order_by(Sancion.id.desc()).all()
