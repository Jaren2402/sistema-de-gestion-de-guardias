from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, date

# Tabla soldado
class Soldado(SQLModel, table=True):
    __tablename__ = 'soldado'
    
    # Atributos
    id_soldado: Optional[int] = Field(default=None, primary_key=True)
    nombre:   str
    apellido: str
    cedula:   str = Field(unique=True)
    rango:    str
    unidad:   str
    
# Tabla punto_guardia
class PuntoGuardia(SQLModel, table=True):
    __tablename__ = "punto_guardia"
    
    # Atributos
    id_punto   : Optional[int] = Field(default=None, primary_key=True)
    nombre     : str = Field(unique=True)  # Ej: "Entrada Principal"
    descripcion: Optional[str] = Field(default=None)
    
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
    
# Tabla restricción
class Restriccion(SQLModel, table=True):
    __tablename__ = 'restriccion'
    
    # Atributos
    id_restriccion: Optional[int] = Field(default=None, primary_key=True)
    id_soldado:     int = Field(foreign_key="soldado.id_soldado")
    fecha_inicio:   date  
    fecha_fin:      date       
    motivo:         str       # "Permiso", "Enfermedad", "Viaje", etc.
    