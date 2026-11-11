"""Servicio de dominio de circulación: disponibilidad, préstamos y devoluciones.

Reglas principales de la HU Agregar préstamo:
    - El usuario y el ejemplar deben existir.
    - La fecha límite no puede ser anterior a la fecha de préstamo.
    - El usuario no puede tener una sanción activa vigente.
    - El ejemplar no puede tener otro préstamo activo (se valida en código y,
      además, mediante el índice único parcial definido en models.Prestamo).
"""
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from app.entidades_bd import Libro, Ejemplar, Prestamo, Usuario, Sancion
from app.contratos_datos import PrestamoCreate

def ejemplar_esta_disponible(db: Session, ejemplar_id: int) -> bool:
    """Indica si un ejemplar no tiene préstamos activos.

    Args:
        db: sesión de base de datos.
        ejemplar_id: id del ejemplar.

    Returns:
        bool: True si no existe un préstamo con ``fecha_devolucion`` nula.
    """
    activo = (
        db.query(Prestamo)
        .filter(Prestamo.ejemplar_id == ejemplar_id, Prestamo.fecha_devolucion.is_(None))
        .first()
    )
    return activo is None

def consultar_disponibilidad(db: Session, criterio: str) -> dict:
    """Busca libros por título o ISBN y calcula la disponibilidad de sus ejemplares.

    Args:
        db: sesión de base de datos.
        criterio: texto parcial del título o del ISBN.

    Returns:
        dict: ``{"libros": [...], "mensaje": None}`` donde cada elemento
        contiene ``libro`` (objeto ORM), ``ejemplares`` (lista de dicts con
        ``id``, ``codigo_inventario``, ``ubicacion``, ``disponible`` y
        ``estado``), ``total_ejemplares``, ``disponibles`` y
        ``sin_ejemplares``. Si no hay coincidencias devuelve
        ``{"libros": [], "mensaje": "Sin resultados"}``.

    Raises:
        ValueError: si el criterio está vacío o solo tiene espacios.
    """
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
        # Se consulta la disponibilidad de cada ejemplar individualmente.
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
    """Registra un préstamo validando todas las reglas de negocio.

    Args:
        db: sesión de base de datos.
        datos: usuario, ejemplar, fecha límite y fecha de préstamo opcional.
        fecha_hoy: fecha de referencia; permite fijar "hoy" en pruebas.
            Por defecto, ``date.today()``.

    Returns:
        Prestamo: préstamo creado y persistido.

    Raises:
        ValueError: si el usuario o el ejemplar no existen, la fecha límite
            es anterior a la de inicio, el usuario tiene una sanción activa
            vigente o el ejemplar ya está prestado (incluida la violación del
            índice único detectada al confirmar).
    """
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

    # Una sanción bloquea préstamos si está "Activa" y su fecha_fin no ha pasado.
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
        # Condición de carrera: otra petición prestó el mismo ejemplar entre
        # la validación y el commit; el índice único lo impide en la BD.
        db.rollback()
        raise ValueError("El ejemplar ya tiene un préstamo activo registrado.")
    db.refresh(prestamo)
    return prestamo

def registrar_devolucion(db: Session, prestamo_id: int, fecha_devolucion: Optional[date] = None) -> Prestamo:
    """Marca un préstamo como devuelto, liberando el ejemplar.

    Args:
        db: sesión de base de datos.
        prestamo_id: id del préstamo.
        fecha_devolucion: fecha de devolución; por defecto, hoy.

    Returns:
        Prestamo: préstamo actualizado.

    Raises:
        ValueError: si el préstamo no existe o ya había sido devuelto.
    """
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
    """Lista los préstamos registrados.

    Args:
        db: sesión de base de datos.
        solo_activos: si es True, excluye los préstamos ya devueltos.

    Returns:
        list[Prestamo]: préstamos ordenados por id descendente (recientes primero).
    """
    query = db.query(Prestamo)
    if solo_activos:
        query = query.filter(Prestamo.fecha_devolucion.is_(None))
    return query.order_by(Prestamo.id.desc()).all()
