import re
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models import Usuario
from app.schemas import UsuarioCreate
from app.security import hash_password

ROLES_VALIDOS = {"Bibliotecario", "Lector"}

# Reglas de la épica Gestión de Usuarios (HU Registrar Usuario)
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LONGITUD_MAX_TEXTO = 120  # coincide con String(120) de nombre y correo en models.py
LONGITUD_MIN_PASSWORD = 8

def crear_usuario(db: Session, datos: UsuarioCreate) -> Usuario:
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
    query = db.query(Usuario)
    if q and q.strip():
        patron = f"%{q.strip()}%"
        query = query.filter(or_(Usuario.nombre.ilike(patron), Usuario.correo.ilike(patron)))
    if rol and rol.strip():
        query = query.filter(Usuario.rol == rol.strip())
    return query.order_by(Usuario.id.asc()).all()
