from datetime import date, datetime
from dataclasses import dataclass
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

# Dataclasses originales para compatibilidad 100% con los servicios y test_sprint1.py
@dataclass
class UsuarioCreate:
    nombre: str
    correo: str
    rol: str
    password: str

@dataclass
class LibroCreate:
    isbn: str
    titulo: str
    autor: str
    categoria: str
    cantidad_ejemplares: int = 1
    ubicacion: str = "Sala General"

@dataclass
class PrestamoCreate:
    usuario_id: int
    ejemplar_id: int
    fecha_limite: date
    fecha_prestamo: Optional[date] = None

@dataclass
class SancionCreate:
    usuario_id: int
    motivo: str
    fecha_fin: date
    prestamo_id: Optional[int] = None

# Esquemas Pydantic para peticiones y respuestas JSON de la API REST
class LoginRequest(BaseModel):
    correo: str
    password: str

class UsuarioCreateRequest(BaseModel):
    nombre: str
    correo: str
    rol: str = "Lector"
    password: str

class UsuarioResponse(BaseModel):
    id: int
    nombre: str
    correo: str
    rol: str
    creado_en: datetime
    model_config = ConfigDict(from_attributes=True)

class EjemplarResponse(BaseModel):
    id: int
    codigo_inventario: str
    libro_id: int
    ubicacion: str
    model_config = ConfigDict(from_attributes=True)

class LibroCreateRequest(BaseModel):
    isbn: str
    titulo: str
    autor: str
    categoria: str
    cantidad_ejemplares: int = 1
    ubicacion: str = "Sala General"

class LibroResponse(BaseModel):
    id: int
    isbn: str
    titulo: str
    autor: str
    categoria: str
    ejemplares: List[EjemplarResponse] = []
    model_config = ConfigDict(from_attributes=True)

class PrestamoCreateRequest(BaseModel):
    usuario_id: int
    ejemplar_id: int
    fecha_limite: date
    fecha_prestamo: Optional[date] = None

class DevolucionRequest(BaseModel):
    prestamo_id: int
    fecha_devolucion: Optional[date] = None

class SancionCreateRequest(BaseModel):
    usuario_id: int
    prestamo_id: Optional[int] = None
    motivo: str
    fecha_fin: date
