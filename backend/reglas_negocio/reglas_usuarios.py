"""Servicio de dominio de la épica Gestión de Usuarios.

Implementa las reglas de las HU Agregar usuario y Consultar usuario. Las
validaciones se ejecutan en orden y la primera que falla lanza ValueError.
"""
import re
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.entidades_bd import Usuario
from app.contratos_datos import UsuarioCreate
from app.seguridad_acceso import hash_password

# Roles admitidos (comparación exacta, sensible a mayúsculas).
ROLES_VALIDOS = {"Bibliotecario", "Lector"}

# Reglas de la épica Gestión de Usuarios (HU Registrar Usuario)
# Formato mínimo de correo: <texto>@<texto>.<texto>, sin espacios ni '@' extra.
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LONGITUD_MAX_TEXTO = 120  # coincide con String(120) de nombre y correo en models.py
LONGITUD_MIN_PASSWORD = 8

def crear_usuario(db: Session, datos: UsuarioCreate) -> Usuario:
    """Registra un usuario nuevo con la contraseña cifrada.

    Normaliza el nombre (sin espacios externos) y el correo (sin espacios y
    en minúsculas) y valida, en este orden:
        1. Nombre, correo y contraseña no vacíos.
        2. Nombre y correo de hasta 120 caracteres.
        3. Correo con formato válido.
        4. Contraseña de al menos 8 caracteres.
        5. Rol "Bibliotecario" o "Lector".
        6. Correo no registrado previamente.

    Args:
        db: sesión de base de datos.
        datos: nombre, correo, rol y contraseña en texto plano.

    Returns:
        Usuario: usuario persistido (la contraseña se guarda como hash).

    Raises:
        ValueError: con un mensaje descriptivo si alguna regla falla.
    """
    nombre = (datos.nombre or "").strip()
    correo = (datos.correo or "").strip().lower()
    rol = (datos.rol or "").strip()
    password = datos.password or ""

    if not nombre or not correo or not password:
        raise ValueError("Nombre, correo y contraseña son obligatorios.")
    if len(nombre) > LONGITUD_MAX_TEXTO or len(correo) > LONGITUD_MAX_TEXTO:
        raise ValueError(f"El nombre y el correo no pueden superar {LONGITUD_MAX_TEXTO} caracteres.")
    if not PATRON_CORREO.match(correo):
        raise ValueError("El correo no tiene un formato válido (ej. nombre@dominio.com).")
    if len(password) < LONGITUD_MIN_PASSWORD:
        raise ValueError(f"La contraseña debe tener al menos {LONGITUD_MIN_PASSWORD} caracteres.")
    if rol not in ROLES_VALIDOS:
        raise ValueError("El rol debe ser 'Bibliotecario' o 'Lector'.")
    existente = db.query(Usuario).filter(Usuario.correo == correo).first()
    if existente:
        raise ValueError(f"Ya existe un usuario registrado con el correo '{correo}'.")

    nuevo = Usuario(
        nombre=nombre,
        correo=correo,
        rol=rol,
        password_hash=hash_password(password),
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

def consultar_usuarios(db: Session, q: str = "", rol: str = "") -> list[Usuario]:
    """Busca usuarios por texto y/o rol.

    Args:
        db: sesión de base de datos.
        q: texto parcial, sin distinguir mayúsculas, en nombre o correo.
        rol: rol exacto; vacío = todos los roles.

    Returns:
        list[Usuario]: usuarios coincidentes ordenados por id ascendente.
    """
    query = db.query(Usuario)
    if q and q.strip():
        patron = f"%{q.strip()}%"
        query = query.filter(or_(Usuario.nombre.ilike(patron), Usuario.correo.ilike(patron)))
    if rol and rol.strip():
        query = query.filter(Usuario.rol == rol.strip())
    return query.order_by(Usuario.id.asc()).all()
