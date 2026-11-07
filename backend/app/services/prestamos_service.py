from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from app.models import Libro, Ejemplar, Prestamo, Usuario, Sancion
from app.schemas import PrestamoCreate

def ejemplar_esta_disponible(db: Session, ejemplar_id: int) -> bool:
    activo = (
        db.query(Prestamo)
        .filter(Prestamo.ejemplar_id == ejemplar_id, Prestamo.fecha_devolucion.is_(None))
        .first()
    )
    return activo is None

def consultar_disponibilidad(db: Session, criterio: str) -> dict:
    texto = (criterio or "").strip()
    if not texto:
        raise ValueError("Debe ingresar un título o ISBN como criterio de búsqueda.")

    patron = f"%{texto}%"
    libros = (
        db.query(Libro)
        .filter(or_(Libro.titulo.ilike(patron), Libro.isbn.ilike(patron)))
        .order_by(Libro.id.asc())
        .all()
    )

    if not libros:
        return {"libros": [], "mensaje": "Sin resultados"}

    resultado = []
    for libro in libros:
        ejemplares_info = []
        disponibles = 0
        for ej in libro.ejemplares:
            disp = ejemplar_esta_disponible(db, ej.id)
            if disp:
                disponibles += 1
            ejemplares_info.append({
                "id": ej.id,
                "codigo_inventario": ej.codigo_inventario,
                "ubicacion": ej.ubicacion,
                "disponible": disp,
                "estado": "Disponible" if disp else "Prestado",
            })
        resultado.append({
            "libro": libro,
            "ejemplares": ejemplares_info,
            "total_ejemplares": len(ejemplares_info),
            "disponibles": disponibles,
            "sin_ejemplares": len(ejemplares_info) == 0,
        })

    return {"libros": resultado, "mensaje": None}

def agregar_prestamo(db: Session, datos: PrestamoCreate, fecha_hoy: Optional[date] = None) -> Prestamo:
    hoy = fecha_hoy or date.today()
    fecha_inicio = datos.fecha_prestamo or hoy

    usuario = db.query(Usuario).filter(Usuario.id == datos.usuario_id).first()
    if not usuario:
        raise ValueError("El usuario indicado no existe.")

    ejemplar = db.query(Ejemplar).filter(Ejemplar.id == datos.ejemplar_id).first()
    if not ejemplar:
        raise ValueError("El ejemplar indicado no existe.")

    if datos.fecha_limite < fecha_inicio:
        raise ValueError("La fecha límite no puede ser anterior a la fecha de préstamo.")

    sancion_activa = (
        db.query(Sancion)
        .filter(
            Sancion.usuario_id == usuario.id,
            Sancion.estado == "Activa",
            Sancion.fecha_fin >= hoy,
        )
        .first()
    )
    if sancion_activa:
        raise ValueError("El usuario posee una sanción administrativa activa y no puede solicitar préstamos.")

    if not ejemplar_esta_disponible(db, ejemplar.id):
        raise ValueError("El ejemplar ya se encuentra prestado.")

    prestamo = Prestamo(
        usuario_id=usuario.id,
        ejemplar_id=ejemplar.id,
        fecha_prestamo=fecha_inicio,
        fecha_limite=datos.fecha_limite,
        fecha_devolucion=None,
    )
    db.add(prestamo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("El ejemplar ya tiene un préstamo activo registrado.")
    db.refresh(prestamo)
    return prestamo

def registrar_devolucion(db: Session, prestamo_id: int, fecha_devolucion: Optional[date] = None) -> Prestamo:
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise ValueError("El préstamo indicado no existe.")
    if prestamo.fecha_devolucion is not None:
        raise ValueError("Este préstamo ya fue devuelto anteriormente.")

    prestamo.fecha_devolucion = fecha_devolucion or date.today()
    db.commit()
    db.refresh(prestamo)
    return prestamo

def consultar_prestamos(db: Session, solo_activos: bool = False) -> list[Prestamo]:
    query = db.query(Prestamo)
    if solo_activos:
        query = query.filter(Prestamo.fecha_devolucion.is_(None))
    return query.order_by(Prestamo.id.desc()).all()
