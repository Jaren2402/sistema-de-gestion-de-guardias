import hashlib
import os

from models import Usuario
from sqlmodel import Session, SQLModel, create_engine, select

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, echo=False)
else:
    engine = create_engine(
        "sqlite:///guardias.db",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")


def migrar_bd():
    dialect = engine.dialect.name
    with engine.connect() as conn:
        if dialect == "postgresql":
            conn.exec_driver_sql("""
                DO $$
                BEGIN
                    ALTER TABLE soldado DROP CONSTRAINT IF EXISTS soldado_cedula_key;
                EXCEPTION WHEN undefined_object THEN NULL;
                END $$;
            """)
            conn.exec_driver_sql("""
                DO $$
                BEGIN
                    ALTER TABLE punto_guardia DROP CONSTRAINT IF EXISTS punto_guardia_nombre_key;
                EXCEPTION WHEN undefined_object THEN NULL;
                END $$;
            """)
            conn.exec_driver_sql("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'uq_soldado_cedula_usuario'
                    ) THEN
                        ALTER TABLE soldado ADD CONSTRAINT uq_soldado_cedula_usuario UNIQUE (cedula, id_usuario);
                    END IF;
                END $$;
            """)
            conn.exec_driver_sql("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'uq_punto_nombre_usuario'
                    ) THEN
                        ALTER TABLE punto_guardia ADD CONSTRAINT uq_punto_nombre_usuario UNIQUE (nombre, id_usuario);
                    END IF;
                END $$;
            """)
            conn.commit()


def crear_tablas():
    SQLModel.metadata.create_all(engine)
    migrar_bd()
    with Session(engine) as session:
        admin = session.exec(select(Usuario).where(Usuario.username == "admin")).first()
        if not admin:
            admin = Usuario(
                username="admin",
                password_hash=hashlib.sha256("admin123".encode()).hexdigest(),
                rol="admin",
            )
            session.add(admin)
            session.commit()


def get_session():
    with Session(engine) as session:
        yield session
