from fastapi import FastAPI, UploadFile, File, Depends
from contextlib import asynccontextmanager
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
import pandas as pd
import io
from services import generar_calendario, obtener_calendario

from datetime import date
from models import Soldado, Restriccion
from database import crear_tablas, get_session

@asynccontextmanager
async def lifespan(app: FastAPI):
    crear_tablas()
    yield

app = FastAPI(
    title='Sistema de Guardias',
    lifespan=lifespan
)

@app.post('/importar_soldados')
async def importar_soldados(
    archivo: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    contenido = await archivo.read()
    df = pd.read_excel(io.BytesIO(contenido))
    
    columnas_requeridas = {
        'cedula',
        'nombre',
        'apellido',
        'rango',
        'unidad'
    }
    if not columnas_requeridas.issubset(df.columns):
        return{'error': f'El Excel debe tener las columnas: {columnas_requeridas}'}

    insertados = 0
    omitidos = 0

    for _, fila in df.iterrows():
        if pd.isna(fila["cedula"]):
            omitidos += 1
            continue

        try:
            soldado = Soldado(
                cedula=str(fila["cedula"]),
                nombre=str(fila["nombre"]),
                apellido=str(fila["apellido"]),
                rango=str(fila["rango"]),
                unidad=str(fila["unidad"]),
            )
            session.add(soldado)
            session.flush()  
            insertados += 1
        except IntegrityError:
            session.rollback()
            omitidos += 1

    session.commit()

    return {
        "mensaje": f"{insertados} soldados importados correctamente. {omitidos} omitidos (cédulas duplicadas o vacías)."
    }
    
@app.get("/soldados")
def obtener_soldados(session: Session = Depends(get_session)):
    soldados = session.exec(select(Soldado)).all()
    resultado = []
    for s in soldados:
        resultado.append({
            "id_soldado": s.id_soldado,   # ← NUEVO
            "cedula": s.cedula,
            "nombre": s.nombre,
            "apellido": s.apellido,
            "rango": s.rango,
            "unidad": s.unidad,
        })
    return resultado

@app.post("/generar-calendario")
def generar_calendario_endpoint(mes: int, año: int, session: Session = Depends(get_session)):
    """
    Genera el calendario de guardias para un mes y año concretos.
    """
    resultado = generar_calendario(mes, año, session)
    return resultado 

# @app.get("/calendario/{año}/{mes}")
# def ver_calendario(año: int, mes: int, session: Session = Depends(get_session)):
#     """
#     Devuelve el calendario de guardias para un mes y año concretos.
#     """
#     return obtener_calendario(mes, año, session)
 
@app.get("/calendario-ver/{ano}/{mes}")
def ver_calendario(ano: int, mes: int, session: Session = Depends(get_session)):
    """
    Devuelve el calendario de guardias para un mes y año concretos.
    """
    return obtener_calendario(mes, ano, session)

@app.post("/restricciones")
def crear_restriccion(
    id_soldado: int,
    fecha_inicio: date,
    fecha_fin: date,
    motivo: str,
    session: Session = Depends(get_session)
):
    """
    Crea una nueva restricción para un soldado.
    """
    nueva = Restriccion(
        id_soldado=id_soldado,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        motivo=motivo
    )
    session.add(nueva)
    session.commit()
    session.refresh(nueva)
    return {"mensaje": "Restricción creada correctamente.", "id": nueva.id_restriccion}

@app.get("/restricciones")
def listar_restricciones(session: Session = Depends(get_session)):
    """
    Devuelve todas las restricciones con los datos del soldado.
    """
    query = (
        select(Restriccion, Soldado)
        .join(Soldado, Restriccion.id_soldado == Soldado.id_soldado)
        .order_by(Restriccion.fecha_inicio.desc())
    )
    resultados = session.exec(query).all()
    lista = []
    for restriccion, soldado in resultados:
        lista.append({
            "id": restriccion.id_restriccion,
            "fecha_inicio": restriccion.fecha_inicio.isoformat(),
            "fecha_fin": restriccion.fecha_fin.isoformat(),
            "motivo": restriccion.motivo,
            "cedula": soldado.cedula,
            "nombre": f"{soldado.nombre} {soldado.apellido}",
        })
    return lista

@app.delete("/restricciones/{id_restriccion}")
def eliminar_restriccion(id_restriccion: int, session: Session = Depends(get_session)):
    """
    Elimina una restricción por su ID.
    """
    restriccion = session.get(Restriccion, id_restriccion)
    if not restriccion:
        return {"error": "Restricción no encontrada."}
    session.delete(restriccion)
    session.commit()
    return {"mensaje": "Restricción eliminada."}