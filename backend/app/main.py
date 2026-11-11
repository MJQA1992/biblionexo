"""Punto de entrada de la API REST de BiblioNexo (Sprint 1 MVP).

Crea la aplicación FastAPI, registra los middlewares (CORS y sesión) y monta
los enrutadores de cada épica. Se ejecuta con::

    uvicorn app.main:app --reload --port 8000

La documentación interactiva (Swagger UI) queda disponible en ``/docs``.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.config import SESSION_SECRET
from app.conexion_bd import Base, engine
from enrutadores import autenticacion, usuarios, libros, prestamos, sanciones

# Crea las tablas que aún no existan a partir de los modelos ORM.
# No altera tablas existentes (no es un sistema de migraciones).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BiblioNexo API REST — Sprint 1 (MVP)",
    description="Backend modular con las 11 historias de usuario del Release 1 y autenticación por rol.",
    version="2.0.0",
)
# CORS abierto: permite que el frontend desacoplado (servido en otro puerto u
# origen, p. ej. :8080) consuma la API desde el navegador.

# Sesión basada en cookie firmada con SESSION_SECRET. Es un mecanismo de
# autenticación alternativo al token Bearer (ver app.security.get_current_user).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)


# Registro de enrutadores por épica (todos bajo el prefijo /api/v1).
app.include_router(autenticacion.router)
app.include_router(usuarios.router)
app.include_router(libros.router)
app.include_router(prestamos.router)
app.include_router(sanciones.router)

@app.get("/")
def read_root():
    """Mensaje de bienvenida con la ruta de la documentación interactiva."""
    return {"message": "Bienvenido a la API REST de BiblioNexo (Sprint 1 MVP)", "docs": "/docs"}

@app.get("/health")
def health():
    """Verificación de salud (health check) para monitoreo o contenedores."""
    return {"status": "ok", "service": "BiblioNexo Backend Sprint 1"}
