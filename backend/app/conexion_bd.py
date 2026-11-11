"""Capa de acceso a datos: motor, sesiones y clase base del ORM.

Expone:
    engine       -- motor SQLAlchemy conectado a ``DATABASE_URL``.
    SessionLocal -- fábrica de sesiones (sin autocommit ni autoflush).
    Base         -- clase base declarativa de la que heredan los modelos.
    get_db       -- dependencia FastAPI que entrega una sesión por petición.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

# SQLite restringe por defecto cada conexión al hilo que la creó; FastAPI
# atiende peticiones en varios hilos, por eso se desactiva esa verificación.
# Para otros motores no se pasan argumentos adicionales.

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Activa la integridad referencial en cada nueva conexión SQLite.

                SQLite ignora las claves foráneas salvo que se ejecute
                ``PRAGMA foreign_keys=ON`` por conexión. Sin esto, las reglas
                ``ondelete="RESTRICT"``/``"CASCADE"`` de entidades_bd.py no se aplicarían.

                Args:
                    dbapi_connection: conexión DB-API nativa recién abierta.
                    connection_record: registro del pool (no se usa).
                """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependencia FastAPI que provee una sesión de base de datos.

        Abre una sesión al inicio de la petición, la entrega al endpoint y la
        cierra siempre al finalizar, incluso si ocurre una excepción.

        Yields:
            Session: sesión SQLAlchemy válida durante la petición.
        """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
