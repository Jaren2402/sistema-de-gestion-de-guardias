from datetime import date

from pydantic import BaseModel, field_validator


class SoldadoCreate(BaseModel):
    cedula: str
    nombre: str
    apellido: str
    rango: str
    unidad: str


class SoldadoUpdate(BaseModel):
    cedula: str
    nombre: str
    apellido: str
    rango: str
    unidad: str


class PuntoCreate(BaseModel):
    nombre: str
    descripcion: str = ""


class PuntoUpdate(BaseModel):
    nombre: str
    descripcion: str = ""


class RestriccionCreate(BaseModel):
    id_soldado: int
    fecha_inicio: date
    fecha_fin: date
    motivo: str

    @field_validator("fecha_fin")
    @classmethod
    def validar_fecha_fin(cls, v, info):
        if "fecha_inicio" in info.data and v < info.data["fecha_inicio"]:
            raise ValueError("fecha_fin debe ser mayor o igual a fecha_inicio")
        return v


class NovedadCreate(BaseModel):
    id_asignacion: int
    descripcion: str = "Sin novedad"


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
