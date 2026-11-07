from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models import Libro, Ejemplar
from app.schemas import LibroCreate

def agregar_libro(db: Session, datos: LibroCreate) -> Libro:
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
    db.flush()

    for idx in range(1, datos.cantidad_ejemplares + 1):
        codigo = f"{isbn}-EJ{idx:02d}"
        ejemplar = Ejemplar(codigo_inventario=codigo, libro_id=libro.id, ubicacion=ubicacion)
        db.add(ejemplar)

    db.commit()
    db.refresh(libro)
    return libro

def consultar_libros(db: Session, q: str = "") -> list[Libro]:
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
