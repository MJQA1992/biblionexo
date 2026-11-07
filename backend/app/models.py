from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import relationship
from app.database import Base

class Usuario(Base):
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
    __tablename__ = "libros"
    id = Column(Integer, primary_key=True, index=True)
    isbn = Column(String(40), unique=True, nullable=False, index=True)
    titulo = Column(String(200), nullable=False, index=True)
    autor = Column(String(150), nullable=False)
    categoria = Column(String(100), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)

    ejemplares = relationship("Ejemplar", back_populates="libro", cascade="all, delete-orphan")

class Ejemplar(Base):
    __tablename__ = "ejemplares"
    id = Column(Integer, primary_key=True, index=True)
    codigo_inventario = Column(String(60), unique=True, nullable=False, index=True)
    libro_id = Column(Integer, ForeignKey("libros.id", ondelete="CASCADE"), nullable=False)
    ubicacion = Column(String(80), default="Sala General", nullable=False)

    libro = relationship("Libro", back_populates="ejemplares")
    prestamos = relationship("Prestamo", back_populates="ejemplar")

class Prestamo(Base):
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

    __table_args__ = (
        Index(
            "uq_prestamo_activo_por_ejemplar",
            "ejemplar_id",
            unique=True,
            sqlite_where=text("fecha_devolucion IS NULL"),
        ),
    )

class Sancion(Base):
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
