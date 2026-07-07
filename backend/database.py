from sqlmodel import Session, SQLModel, create_engine

# Ruta del archivo SQLite (si no existe, se crea automáticamente)
sqlite_url = 'sqlite:///guardias.db'

# Para crear el motor de BD (con modo WAL activado)
engine = create_engine(
    sqlite_url,
    echo=False,
    connect_args={'check_same_thread': False}
)

# Activar el modo WAL
with engine.connect() as conn:
    conn.exec_driver_sql('PRAGMA journal_mode=WAL')

# Para crear todas las tablas definidas en los modelos
def crear_tablas():
    SQLModel.metadata.create_all(engine)

# Esto es una dependencia de FastAPI (provee una sesión y la cierra al terminar)
def get_session():
    with Session(engine) as session:
        yield session



