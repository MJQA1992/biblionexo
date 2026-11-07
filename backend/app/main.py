from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.config import SESSION_SECRET
from app.database import Base, engine
from app.routers import auth, usuarios, libros, prestamos, sanciones

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BiblioNexo API REST — Sprint 1 (MVP)",
    description="Backend modular con las 11 historias de usuario del Release 1 y autenticación por rol.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(libros.router)
app.include_router(prestamos.router)
app.include_router(sanciones.router)

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API REST de BiblioNexo (Sprint 1 MVP)", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok", "service": "BiblioNexo Backend Sprint 1"}
