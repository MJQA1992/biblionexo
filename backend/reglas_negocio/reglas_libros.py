"""Servicio de dominio del catálogo: alta y consulta de libros.

Reglas de la HU Agregar libros:
    - ISBN, título, autor y categoría son obligatorios (se recortan espacios).
    - La cantidad de ejemplares debe estar entre 1 y 50.
    - El ISBN no puede repetirse.
    - Los ejemplares se generan automáticamente con código ``<ISBN>-EJ<nn>``.
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.entidades_bd import Libro, Ejemplar
from app.contratos_datos import LibroCreate

def agregar_libro(db: Session, datos: LibroCreate) -> Libro:
    """Registra un libro y crea sus ejemplares en una sola transacción.

    Args:
        db: sesión de base de datos.
        datos: datos del libro, cantidad de ejemplares y ubicación.

    Returns:
        Libro: libro persistido, refrescado con sus ejemplares.

    Raises:
        ValueError: si falta un campo obligatorio, la cantidad está fuera
            del rango 1-50 o el ISBN ya está registrado.
    """
    # Normalización: None se trata como cadena vacía y se recortan espacios.
    isbn = (datos.isbn or "").strip()
    titulo = (datos.titulo or "").strip()
    autor = (datos.autor or "").strip()
    categoria = (datos.categoria or "").strip()
    ubicacion = (datos.ubicacion or "Sala General").strip()

    if not isbn or not titulo or not autor or not categoria:
        raise ValueError("ISBN, título, autor y categoría son obligatorios.")
    if datos.cantidad_ejemplares < 1 or datos.cantidad_ejemplares > 50:
        raise ValueError("La cantidad de ejemplares debe estar entre 1 y 50.")

    existente = db.query(Libro).filter(Libro.isbn == isbn).first()
    if existente:
        raise ValueError(f"Ya existe un libro registrado con el ISBN '{isbn}'.")

    libro = Libro(isbn=isbn, titulo=titulo, autor=autor, categoria=categoria)
    db.add(libro)
    # flush() obtiene libro.id antes del commit para enlazar los ejemplares.
    db.flush()

    # Genera ejemplares numerados: <ISBN>-EJ01, <ISBN>-EJ02, ...
    for idx in range(1, datos.cantidad_ejemplares + 1):
        codigo = f"{isbn}-EJ{idx:02d}"
        ejemplar = Ejemplar(codigo_inventario=codigo, libro_id=libro.id, ubicacion=ubicacion)
        db.add(ejemplar)

    db.commit()
    db.refresh(libro)
    return libro

def consultar_libros(db: Session, q: str = "") -> list[Libro]:
    """Busca libros en el catálogo.

    Args:
        db: sesión de base de datos.
        q: texto parcial, sin distinguir mayúsculas, que se busca en título,
            autor, ISBN o categoría. Vacío devuelve todo el catalogo.

    Returns:
        list[Libro]: libros coincidentes ordenados por id ascendente.
    """
    query = db.query(Libro)
    if q and q.strip():
        patron = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Libro.titulo.ilike(patron),
                Libro.autor.ilike(patron),
                Libro.isbn.ilike(patron),
                Libro.categoria.ilike(patron),
            )
        )
    return query.order_by(Libro.id.asc()).all()
