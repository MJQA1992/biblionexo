"""Modelos ORM (SQLAlchemy) del dominio bibliotecario de BiblioNexo.

Relaciones principales::

    Usuario 1 ──< N Prestamo >── 1 Ejemplar >── 1 Libro
    Usuario 1 ──< N Sancion  >── 0..1 Prestamo

- Un ``Libro`` (título catalogado por ISBN) tiene uno o más ``Ejemplar``
  (copias físicas con código de inventario).
- Un ``Prestamo`` vincula un usuario con un ejemplar; se considera activo
  mientras ``fecha_devolucion`` sea ``NULL``.
- Una ``Sancion`` suspende a un usuario hasta ``fecha_fin`` y puede estar
  asociada opcionalmente al préstamo que la originó.
"""
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import relationship
from app.conexion_bd import Base

class Usuario(Base):
    """Persona registrada en el sistema (personal de biblioteca o lector).

    Attributes:
        id: identificador autoincremental.
        nombre: nombre completo (máx. 120 caracteres).
        correo: correo único, guardado en minúsculas; se usa como login.
        rol: ``"Bibliotecario"`` (acceso total a la API) o ``"Lector"``.
        password_hash: contraseña con PBKDF2-SHA256 (ver app.security).
        creado_en: fecha y hora UTC de registro.
        prestamos: préstamos realizados por el usuario.
        sanciones: sanciones aplicadas al usuario.
    """
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    correo = Column(String(120), unique=True, nullable=False, index=True)
    rol = Column(String(30), nullable=False)  # 'Bibliotecario' o 'Lector'
    password_hash = Column(String(255), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)

    prestamos = relationship("Prestamo", back_populates="usuario")
    sanciones = relationship("Sancion", back_populates="usuario")

class Libro(Base):
    """Título bibliográfico del catálogo, identificado por su ISBN.

    Attributes:
        id: identificador autoincremental.
        isbn: código ISBN único del título.
        titulo: título de la obra (indexado para búsquedas).
        autor: autor o autores.
        categoria: área temática.
        creado_en: fecha y hora UTC de registro.
        ejemplares: copias físicas; se eliminan junto con el libro
            (``cascade="all, delete-orphan"``).
    """
    __tablename__ = "libros"
    id = Column(Integer, primary_key=True, index=True)
    isbn = Column(String(40), unique=True, nullable=False, index=True)
    titulo = Column(String(200), nullable=False, index=True)
    autor = Column(String(150), nullable=False)
    categoria = Column(String(100), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)

    ejemplares = relationship("Ejemplar", back_populates="libro", cascade="all, delete-orphan")

class Ejemplar(Base):
    """Copia física de un libro que puede prestarse.

    Attributes:
        id: identificador autoincremental (el que se usa al prestar).
        codigo_inventario: código único con formato ``<ISBN>-EJ<nn>``.
        libro_id: libro al que pertenece (FK con borrado en cascada).
        ubicacion: ubicación física (sala o estante).
        libro: libro asociado.
        prestamos: historial de préstamos del ejemplar.
    """
    __tablename__ = "ejemplares"
    id = Column(Integer, primary_key=True, index=True)
    codigo_inventario = Column(String(60), unique=True, nullable=False, index=True)
    libro_id = Column(Integer, ForeignKey("libros.id", ondelete="CASCADE"), nullable=False)
    ubicacion = Column(String(80), default="Sala General", nullable=False)

    libro = relationship("Libro", back_populates="ejemplares")
    prestamos = relationship("Prestamo", back_populates="ejemplar")

class Prestamo(Base):
    """Préstamo de un ejemplar a un usuario.

    Un préstamo está **activo** mientras ``fecha_devolucion`` es ``NULL`` y
    **vencido** si además ``fecha_limite`` es anterior a la fecha de corte.

    Attributes:
        id: identificador autoincremental.
        usuario_id: usuario que recibe el ejemplar (FK RESTRICT).
        ejemplar_id: ejemplar prestado (FK RESTRICT).
        fecha_prestamo: fecha de entrega (por defecto, hoy).
        fecha_limite: fecha máxima de devolución.
        fecha_devolucion: fecha real de devolución; ``None`` si sigue activo.
        usuario, ejemplar: entidades relacionadas.
        sanciones: sanciones originadas por este préstamo.
    """
    __tablename__ = "prestamos"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    ejemplar_id = Column(Integer, ForeignKey("ejemplares.id", ondelete="RESTRICT"), nullable=False)
    fecha_prestamo = Column(Date, default=date.today, nullable=False)
    fecha_limite = Column(Date, nullable=False)
    fecha_devolucion = Column(Date, nullable=True)

    usuario = relationship("Usuario", back_populates="prestamos")
    ejemplar = relationship("Ejemplar", back_populates="prestamos")
    sanciones = relationship("Sancion", back_populates="prestamo")

    # Índice único parcial: garantiza a nivel de base de datos que un mismo
    # ejemplar no tenga dos préstamos activos (fecha_devolucion IS NULL) a la
    # vez. Complementa la validación de reglas_negocio.prestamos_service.
    # La cláusula sqlite_where solo la aplica el dialecto SQLite.
    __table_args__ = (
        Index(
            "uq_prestamo_activo_por_ejemplar",
            "ejemplar_id",
            unique=True,
            sqlite_where=text("fecha_devolucion IS NULL"),
        ),
    )

class Sancion(Base):
    """Sanción administrativa que impide al usuario solicitar préstamos.

    Attributes:
        id: identificador autoincremental.
        usuario_id: usuario sancionado (FK RESTRICT).
        prestamo_id: préstamo que originó la sanción (opcional).
        motivo: descripción del motivo (obligatorio).
        fecha_inicio: inicio de la sanción (por defecto, hoy).
        fecha_fin: último día de vigencia de la sanción.
        estado: ``"Activa"`` o ``"Cumplida"``.
        usuario, prestamo: entidades relacionadas.
    """
    __tablename__ = "sanciones"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id", ondelete="RESTRICT"), nullable=True)
    motivo = Column(String(255), nullable=False)
    fecha_inicio = Column(Date, default=date.today, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    estado = Column(String(30), default="Activa", nullable=False)  # Activa, Cumplida

    usuario = relationship("Usuario", back_populates="sanciones")
    prestamo = relationship("Prestamo", back_populates="sanciones")
