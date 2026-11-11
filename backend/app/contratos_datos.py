"""Objetos de transferencia de datos (DTO) de BiblioNexo.

El módulo define dos familias de estructuras:

1. **Dataclasses** (``*Create``): entradas de los servicios de dominio en
   ``reglas_negocio/``. No dependen de FastAPI ni de Pydantic, lo que permite
   probar la lógica de negocio de forma aislada.
2. **Modelos Pydantic** (``*Request`` / ``*Response``): validan el JSON de
   entrada de la API y serializan las respuestas. Los ``*Response`` usan
   ``from_attributes=True`` para construirse directamente desde objetos ORM.
"""
from datetime import date, datetime
from dataclasses import dataclass
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

# Dataclasses originales para compatibilidad 100% con los servicios y test_sprint1.py
@dataclass
class UsuarioCreate:
    """Datos para registrar un usuario (entrada de usuarios_service.crear_usuario)."""
    nombre: str
    correo: str
    rol: str
    password: str

@dataclass
class LibroCreate:
    """Datos para registrar un libro y generar sus ejemplares (libros_service.agregar_libro)."""
    isbn: str
    titulo: str
    autor: str
    categoria: str
    cantidad_ejemplares: int = 1
    ubicacion: str = "Sala General"

@dataclass
class PrestamoCreate:
    """Datos para registrar un préstamo; ``fecha_prestamo`` None equivale a hoy."""
    usuario_id: int
    ejemplar_id: int
    fecha_limite: date
    fecha_prestamo: Optional[date] = None

@dataclass
class SancionCreate:
    """Datos para registrar una sanción, opcionalmente ligada a un préstamo."""
    usuario_id: int
    motivo: str
    fecha_fin: date
    prestamo_id: Optional[int] = None

# Esquemas Pydantic para peticiones y respuestas JSON de la API REST
class LoginRequest(BaseModel):
    """Cuerpo de ``POST /api/v1/login``."""
    correo: str
    password: str

class UsuarioCreateRequest(BaseModel):
    """Cuerpo de ``POST /api/v1/usuarios``; el rol por defecto es Lector."""
    nombre: str
    correo: str
    rol: str = "Lector"
    password: str

class UsuarioResponse(BaseModel):
    """Representación pública de un usuario (nunca incluye la contraseña ni su hash)."""
    id: int
    nombre: str
    correo: str
    rol: str
    creado_en: datetime
    model_config = ConfigDict(from_attributes=True)

class EjemplarResponse(BaseModel):
    """Representación de un ejemplar dentro de ``LibroResponse``."""
    id: int
    codigo_inventario: str
    libro_id: int
    ubicacion: str
    model_config = ConfigDict(from_attributes=True)

class LibroCreateRequest(BaseModel):
    """Cuerpo de ``POST /api/v1/libros``."""
    isbn: str
    titulo: str
    autor: str
    categoria: str
    cantidad_ejemplares: int = 1
    ubicacion: str = "Sala General"

class LibroResponse(BaseModel):
    """Representación de un libro con la lista de sus ejemplares."""
    id: int
    isbn: str
    titulo: str
    autor: str
    categoria: str
    ejemplares: List[EjemplarResponse] = []
    model_config = ConfigDict(from_attributes=True)

class PrestamoCreateRequest(BaseModel):
    """Cuerpo de ``POST /api/v1/prestamos``."""
    usuario_id: int
    ejemplar_id: int
    fecha_limite: date
    fecha_prestamo: Optional[date] = None

class DevolucionRequest(BaseModel):
    """Cuerpo de ``POST /api/v1/prestamos/devolver``; sin fecha se usa la de hoy."""
    prestamo_id: int
    fecha_devolucion: Optional[date] = None

class SancionCreateRequest(BaseModel):
    """Cuerpo de ``POST /api/v1/sanciones``."""
    usuario_id: int
    prestamo_id: Optional[int] = None
    motivo: str
    fecha_fin: date
