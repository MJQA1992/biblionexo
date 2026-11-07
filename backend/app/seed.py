from datetime import date, timedelta
from app.config import DEMO_PASSWORD
from app.database import SessionLocal, Base, engine
from app.models import Usuario, Libro, Ejemplar, Prestamo
from app.security import hash_password

def run_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Usuario).count() > 0:
            print("Base no vacía: no se modifica.")
            return

        biblio = Usuario(
            nombre="Bibliotecario Demo",
            correo="biblioteca@demo.local",
            rol="Bibliotecario",
            password_hash=hash_password(DEMO_PASSWORD),
        )
        lector = Usuario(
            nombre="Lector Demo",
            correo="lector@demo.local",
            rol="Lector",
            password_hash=hash_password(DEMO_PASSWORD),
        )
        db.add_all([biblio, lector])
        db.flush()

        categorias = ["Ingeniería de Software", "Algoritmos", "Bases de Datos", "Arquitectura", "Redes"]
        for i in range(1, 51):
            isbn = f"DEMO-{i:03d}"
            libro = Libro(
                isbn=isbn,
                titulo=f"Fundamentos Técnicos Volumen {i}",
                autor=f"Autor Académico {(i % 10) + 1}",
                categoria=categorias[i % len(categorias)],
            )
            db.add(libro)
            db.flush()
            for ej_num in (1, 2):
                db.add(
                    Ejemplar(
                        codigo_inventario=f"{isbn}-EJ{ej_num:02d}",
                        libro_id=libro.id,
                        ubicacion=f"Estante {(i % 5) + 1}",
                    )
                )

        db.flush()
        # Crear un préstamo vencido de ejemplo sobre DEMO-002-EJ01 para probar Consultar Vencimientos
        ej_vencido = db.query(Ejemplar).filter(Ejemplar.codigo_inventario == "DEMO-002-EJ01").first()
        if ej_vencido:
            db.add(
                Prestamo(
                    usuario_id=lector.id,
                    ejemplar_id=ej_vencido.id,
                    fecha_prestamo=date.today() - timedelta(days=15),
                    fecha_limite=date.today() - timedelta(days=5),
                    fecha_devolucion=None,
                )
            )

        db.commit()
        print("Datos de demostración creados: 2 usuarios, 50 títulos, 100 ejemplares y 1 préstamo vencido.")
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
