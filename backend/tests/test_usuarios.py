"""Pruebas de la épica Gestión de Usuarios (HU Agregar usuario / Consultar usuario).

Cada prueba usa una base SQLite en memoria, así no se toca biblionexo.db.
Ejecutar desde backend/:  pytest -q
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Usuario
from app.schemas import UsuarioCreate
from app.security import hash_password, verify_password
from reglas_negocio.usuarios_service import crear_usuario, consultar_usuarios

PASSWORD = "Clave12345"


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    session.add_all([
        Usuario(nombre="Biblio Test", correo="biblio@test.local", rol="Bibliotecario",
                password_hash=hash_password(PASSWORD)),
        Usuario(nombre="Lector Test", correo="lector@test.local", rol="Lector",
                password_hash=hash_password(PASSWORD)),
    ])
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def auth_headers(client, correo):
    res = client.post("/api/v1/login", json={"correo": correo, "password": PASSWORD})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def datos(**cambios):
    base = {"nombre": "Ana Pérez", "correo": "ana@test.local", "rol": "Lector", "password": PASSWORD}
    base.update(cambios)
    return UsuarioCreate(**base)


# ---------- Reglas de negocio (reglas_negocio/usuarios_service.py) ----------

def test_registrar_usuario_valido_normaliza_y_encripta(db):
    u = crear_usuario(db, datos(nombre="  Ana Pérez ", correo="  ANA@Test.Local "))
    assert u.id is not None
    assert u.nombre == "Ana Pérez"
    assert u.correo == "ana@test.local"
    assert u.password_hash != PASSWORD
    assert verify_password(PASSWORD, u.password_hash)


def test_correo_duplicado_se_rechaza_sin_importar_mayusculas(db):
    with pytest.raises(ValueError, match="Ya existe"):
        crear_usuario(db, datos(correo="BIBLIO@test.local"))


@pytest.mark.parametrize("campo", ["nombre", "correo", "password"])
def test_campos_obligatorios(db, campo):
    with pytest.raises(ValueError, match="obligatorios"):
        crear_usuario(db, datos(**{campo: "   " if campo != "password" else ""}))


@pytest.mark.parametrize("correo", ["sin-arroba", "ana@dominio", "ana perez@test.com", "@test.com"])
def test_correo_con_formato_invalido(db, correo):
    with pytest.raises(ValueError, match="formato válido"):
        crear_usuario(db, datos(correo=correo))


def test_contrasena_menor_a_8_caracteres(db):
    with pytest.raises(ValueError, match="al menos 8"):
        crear_usuario(db, datos(password="1234567"))


@pytest.mark.parametrize("rol", ["Administrador", "lector", ""])
def test_rol_invalido(db, rol):
    with pytest.raises(ValueError, match="rol"):
        crear_usuario(db, datos(rol=rol))


def test_consultar_usuarios_por_texto_y_por_rol(db):
    assert [u.correo for u in consultar_usuarios(db, q="lector")] == ["lector@test.local"]
    assert [u.rol for u in consultar_usuarios(db, rol="Bibliotecario")] == ["Bibliotecario"]
    assert len(consultar_usuarios(db)) == 2


# ---------- API REST (enrutadores/usuarios.py) ----------

def test_bibliotecario_registra_usuario_201(client):
    res = client.post("/api/v1/usuarios", headers=auth_headers(client, "biblio@test.local"),
                      json={"nombre": "Ana Pérez", "correo": "ana@test.local", "rol": "Lector",
                            "password": PASSWORD})
    assert res.status_code == 201
    body = res.json()
    assert body["correo"] == "ana@test.local"
    assert "password" not in body and "password_hash" not in body


def test_lector_no_puede_registrar_usuarios_403(client):
    res = client.post("/api/v1/usuarios", headers=auth_headers(client, "lector@test.local"),
                      json={"nombre": "X", "correo": "x@test.local", "password": PASSWORD})
    assert res.status_code == 403


def test_sin_sesion_responde_401(client):
    assert client.get("/api/v1/usuarios").status_code == 401


def test_regla_violada_responde_400_con_mensaje(client):
    res = client.post("/api/v1/usuarios", headers=auth_headers(client, "biblio@test.local"),
                      json={"nombre": "Ana", "correo": "ana-sin-arroba", "password": PASSWORD})
    assert res.status_code == 400
    assert "formato válido" in res.json()["detail"]


def test_consultar_usuarios_filtrando_por_rol(client):
    res = client.get("/api/v1/usuarios?rol=Lector", headers=auth_headers(client, "biblio@test.local"))
    assert res.status_code == 200
    assert {u["rol"] for u in res.json()} == {"Lector"}
