import io
import traceback
from contextlib import asynccontextmanager
from datetime import date, datetime

import pandas as pd
from database import crear_tablas, get_session
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from models import Restriccion, Soldado
from services import (
    actualizar_soldado,
    buscar_candidatos_sustitucion,
    confirmar_sustitucion,
    confirmar_trueque,
    crear_novedad,
    crear_punto,
    crear_soldado,
    difundir_pdf,
    editar_punto,
    eliminar_punto,
    eliminar_soldado,
    generar_calendario,
    generar_pdf,
    listar_novedades,
    listar_puntos,
    obtener_calendario,
    obtener_estadisticas,
    obtener_ficha_soldado,
    obtener_historial_sustituciones,
)
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    crear_tablas()
    yield

app = FastAPI(
    title='Sistema de Guardias',
    lifespan=lifespan
)

@app.middleware("http")
async def log_errores_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as ex:
        print(f"[ERROR] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: {ex}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": "Error interno del servidor. Consulte los logs para más detalles."}
        )

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

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
                fecha_registro=datetime.now(),
            )
            session.add(soldado)
            session.flush()
            insertados += 1
        except IntegrityError as ex:
            session.rollback()
            print(f"[ERROR] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: [importar_soldados] Cédula duplicada: {ex}")
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
            "id_soldado": s.id_soldado,
            "cedula": s.cedula,
            "nombre": s.nombre,
            "apellido": s.apellido,
            "rango": s.rango,
            "unidad": s.unidad,
            "fecha_registro": s.fecha_registro.isoformat() if s.fecha_registro else None,
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

@app.post("/sustituir-guardia")
def sustituir_guardia(
    id_asignacion_original: int,
    session: Session = Depends(get_session)
):
    resultado = buscar_candidatos_sustitucion(id_asignacion_original, session)
    return resultado

@app.post("/confirmar-sustitucion")
def confirmar_sustitucion_endpoint(
    id_asignacion_original: int,
    id_nuevo_soldado: int,
    session: Session = Depends(get_session)
):
    resultado = confirmar_sustitucion(id_asignacion_original, id_nuevo_soldado, session)
    return resultado

@app.post("/confirmar-trueque")
def confirmar_trueque_endpoint(
    id_asignacion_a: int,
    id_asignacion_b: int,
    id_soldado_b: int,
    session: Session = Depends(get_session)
):
    resultado = confirmar_trueque(id_asignacion_a, id_asignacion_b, id_soldado_b, session)
    return resultado

@app.get("/ficha-soldado-ver/{id_soldado}/{mes}/{ano}")
def ficha_soldado(
    id_soldado: int,
    mes: int,
    ano: int,
    session: Session = Depends(get_session)
):
    return obtener_ficha_soldado(id_soldado, mes, ano, session)

@app.post("/soldados/crear")
def crear_soldado_endpoint(
    cedula: str,
    nombre: str,
    apellido: str,
    rango: str,
    unidad: str,
    session: Session = Depends(get_session)
):
    return crear_soldado(cedula, nombre, apellido, rango, unidad, session)

@app.put("/soldados/editar/{id_soldado}")
def editar_soldado_endpoint(
    id_soldado: int,
    cedula: str,
    nombre: str,
    apellido: str,
    rango: str,
    unidad: str,
    session: Session = Depends(get_session)
):
    return actualizar_soldado(id_soldado, cedula, nombre, apellido, rango, unidad, session)

@app.delete("/soldados/eliminar/{id_soldado}")
def eliminar_soldado_endpoint(
    id_soldado: int,
    session: Session = Depends(get_session)
):
    return eliminar_soldado(id_soldado, session)

@app.post("/puntos/crear")
def crear_punto_endpoint(
    nombre: str,
    descripcion: str = "",
    session: Session = Depends(get_session)
):
    return crear_punto(nombre, descripcion, session)

@app.put("/puntos/editar/{id_punto}")
def editar_punto_endpoint(
    id_punto: int,
    nombre: str,
    descripcion: str = "",
    session: Session = Depends(get_session)
):
    return editar_punto(id_punto, nombre, descripcion, session)

@app.delete("/puntos/eliminar/{id_punto}")
def eliminar_punto_endpoint(
    id_punto: int,
    session: Session = Depends(get_session)
):
    return eliminar_punto(id_punto, session)

@app.get("/puntos")
def listar_puntos_endpoint(session: Session = Depends(get_session)):
    return listar_puntos(session)

@app.get("/exportar-pdf/{mes}/{ano}")
def exportar_pdf(mes: int, ano: int, session: Session = Depends(get_session)):
    pdf_buffer = generar_pdf(mes, ano, session)
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Plan_de_Guardias_{mes}_{ano}.pdf"}
    )

@app.post("/novedades")
def crear_novedad_endpoint(
    id_asignacion: int,
    descripcion: str = "Sin novedad",
    session: Session = Depends(get_session)
):
    return crear_novedad(id_asignacion, descripcion, session)


@app.get("/novedades/{mes}/{ano}")
def listar_novedades_endpoint(
    mes: int,
    ano: int,
    session: Session = Depends(get_session)
):
    return listar_novedades(mes, ano, session)

@app.get("/estadisticas/{mes}/{ano}")
def estadisticas_endpoint(mes: int, ano: int, meses: int = 1, session: Session = Depends(get_session)):
    return obtener_estadisticas(mes, ano, session, meses)

@app.get("/historial-sustituciones/{mes}/{ano}")
def historial_sustituciones_endpoint(
    mes: int,
    ano: int,
    session: Session = Depends(get_session)
):
    return obtener_historial_sustituciones(mes, ano, session)

@app.post("/difundir/{mes}/{ano}")
async def difundir_endpoint(
    mes: int,
    ano: int,
    session: Session = Depends(get_session)
):
    return await difundir_pdf(mes, ano, session)
