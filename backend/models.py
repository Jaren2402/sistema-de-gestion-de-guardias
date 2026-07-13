from datetime import date, datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


# Tabla soldado
class Soldado(SQLModel, table=True):
    __tablename__ = 'soldado'
    __table_args__ = (
        UniqueConstraint('cedula', 'id_usuario', name='uq_soldado_cedula_usuario'),
    )

    id_soldado:     Optional[int] = Field(default=None, primary_key=True)
    nombre:         str
    apellido:       str
    cedula:         str
    rango:          str
    unidad:         str
    fecha_registro: Optional[datetime] = Field(default=None)
    id_usuario:     Optional[int] = Field(default=None, foreign_key="usuario.id_usuario")

# Tabla punto_guardia
class PuntoGuardia(SQLModel, table=True):
    __tablename__ = "punto_guardia"
    __table_args__ = (
        UniqueConstraint('nombre', 'id_usuario', name='uq_punto_nombre_usuario'),
    )

    id_punto   : Optional[int] = Field(default=None, primary_key=True)
    nombre     : str
    descripcion: Optional[str] = Field(default=None)
    id_usuario : Optional[int] = Field(default=None, foreign_key="usuario.id_usuario")

# Tabla guardia
class Guardia(SQLModel, table=True):
    __tablename__ = 'guardia'

    # Atributos
    id_guardia:   Optional[int] = Field(default=None, primary_key=True)
    fecha_inicio: datetime
    fecha_fin:    datetime
    tipo:         str      # diurno o nocturno
    estado:       str = Field(default='pendiente') # pendiente o finalizada
    id_punto:     int = Field(foreign_key="punto_guardia.id_punto")

# Tabla asignación
class Asignacion(SQLModel, table=True):
    __tablename__ = 'asignacion'

    # Atributos
    id_asignacion:          Optional[int] = Field(default=None, primary_key=True)
    id_soldado:             int = Field(foreign_key="soldado.id_soldado")
    id_guardia:             int = Field(foreign_key="guardia.id_guardia")
    fecha_asignacion:       datetime = Field(default_factory=datetime.utcnow)
    es_titular:             bool = Field(default=True) # false si es reemplazo
    id_asignacion_original: Optional[int] = Field(default=None, foreign_key="asignacion.id_asignacion", nullable=True)
    es_anulada:             bool = Field(default=False)

# Tabla restricción
class Restriccion(SQLModel, table=True):
    __tablename__ = 'restriccion'

    # Atributos
    id_restriccion: Optional[int] = Field(default=None, primary_key=True)
    id_soldado:     int = Field(foreign_key="soldado.id_soldado")
    fecha_inicio:   date
    fecha_fin:      date
    motivo:         str       # "Permiso", "Viaje", etc.

class Novedad(SQLModel, table=True):
    __tablename__ = "novedad"
    id_novedad: Optional[int] = Field(default=None, primary_key=True)
    id_asignacion: int = Field(foreign_key="asignacion.id_asignacion")
    descripcion: str
    fecha_reporte: datetime = Field(default_factory=datetime.utcnow)


class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"
    id_usuario: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    password_hash: str
    rol: str = Field(default="admin")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Sesion(SQLModel, table=True):
    __tablename__ = "sesion"
    id_sesion: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    id_usuario: int = Field(foreign_key="usuario.id_usuario")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    activa: bool = Field(default=True)
