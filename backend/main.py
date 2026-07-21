import hashlib
import io
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime

import pandas as pd
from database import crear_tablas, get_session
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Path, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from logger import log_error, log_info, setup_logging
from models import PuntoGuardia, Restriccion, Sesion, Soldado, Usuario
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
    setup_logging()
    crear_tablas()
    yield

app = FastAPI(
    title='Sistema de Guardias',
    lifespan=lifespan
)

@app.middleware("http")
async def log_errores_middleware(request: Request, call_next):
    correlation_id = str(uuid.uuid4())[:8]
    request.state.correlation_id = correlation_id
    log_info(f"{request.method} {request.url.path}", correlation_id)
    try:
        response = await call_next(request)
        return response
    except Exception as ex:
        log_error("middleware", ex, correlation_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Ocurrió un error. Reporte el código: {correlation_id}"
            }
        )

@app.get("/health")
def health(session: Session = Depends(get_session)):
    db_ok = False
    try:
        session.exec(select(Sesion).limit(1))
        db_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if db_ok else "degradado",
        "database": "conectada" if db_ok else "fallo",
        "timestamp": datetime.now().isoformat()
    }


def get_usuario_id(authorization: str = Header(..., alias="Authorization"), session: Session = Depends(get_session)) -> int:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sesión inválida")
    token = authorization[len("Bearer "):]
    sesion = session.exec(select(Sesion).where(Sesion.token == token, Sesion.activa)).first()
    if not sesion:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    return sesion.id_usuario

@app.post('/importar_soldados')
async def importar_soldados(
    archivo: UploadFile = File(...),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    contenido = await archivo.read()
    if len(contenido) > 100 * 1024 * 1024:
        return {"error": "El archivo excede el tamaño máximo permitido (100 MB)."}
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
                id_usuario=usuario_id,
            )
            session.add(soldado)
            session.flush()
            insertados += 1
        except IntegrityError as ex:
            session.rollback()
            log_error("importar_soldados", ex)
            omitidos += 1

    session.commit()

    return {
        "mensaje": f"{insertados} soldados importados correctamente. {omitidos} omitidos (cédulas duplicadas o vacías)."
    }

@app.get("/soldados")
def obtener_soldados(usuario_id: int = Depends(get_usuario_id), session: Session = Depends(get_session)):
    soldados = session.exec(select(Soldado).where(Soldado.id_usuario == usuario_id)).all()
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
def generar_calendario_endpoint(
    mes: int = Query(..., ge=1, le=12),
    año: int = Query(..., ge=2020, le=2100),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    resultado = generar_calendario(mes, año, usuario_id, session)
    return resultado

@app.get("/calendario-ver/{ano}/{mes}")
def ver_calendario(
    ano: int = Path(..., ge=2020, le=2100),
    mes: int = Path(..., ge=1, le=12),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    return obtener_calendario(mes, ano, usuario_id, session)

@app.post("/restricciones")
def crear_restriccion(
    id_soldado: int,
    fecha_inicio: date,
    fecha_fin: date,
    motivo: str = Query(..., min_length=1, max_length=500),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    soldado = session.get(Soldado, id_soldado)
    if not soldado or soldado.id_usuario != usuario_id:
        return {"error": "Soldado no encontrado"}
    if fecha_fin < fecha_inicio:
        return {"error": "fecha_fin debe ser mayor o igual a fecha_inicio"}
    nueva = Restriccion(
        id_soldado=id_soldado,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        motivo=motivo
    )
    session.add(nueva)
    session.commit()
    session.refresh(nueva)
    return {"mensaje": "Restricci\u00f3n creada correctamente.", "id": nueva.id_restriccion}

@app.get("/restricciones")
def listar_restricciones(usuario_id: int = Depends(get_usuario_id), session: Session = Depends(get_session)):
    query = (
        select(Restriccion, Soldado)
        .join(Soldado, Restriccion.id_soldado == Soldado.id_soldado)
        .where(Soldado.id_usuario == usuario_id)
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
def eliminar_restriccion(id_restriccion: int, usuario_id: int = Depends(get_usuario_id), session: Session = Depends(get_session)):
    restriccion = session.get(Restriccion, id_restriccion)
    if not restriccion:
        return {"error": "Restricci\u00f3n no encontrada."}
    soldado = session.get(Soldado, restriccion.id_soldado)
    if not soldado or soldado.id_usuario != usuario_id:
        return {"error": "No autorizado"}
    session.delete(restriccion)
    session.commit()
    return {"mensaje": "Restricci\u00f3n eliminada."}

@app.post("/sustituir-guardia")
def sustituir_guardia(
    id_asignacion_original: int,
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    resultado = buscar_candidatos_sustitucion(id_asignacion_original, usuario_id, session)
    return resultado

@app.post("/confirmar-sustitucion")
def confirmar_sustitucion_endpoint(
    id_asignacion_original: int,
    id_nuevo_soldado: int,
    motivo: str = Query(default="", max_length=500),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    resultado = confirmar_sustitucion(id_asignacion_original, id_nuevo_soldado, motivo, usuario_id, session)
    return resultado

@app.post("/confirmar-trueque")
def confirmar_trueque_endpoint(
    id_asignacion_a: int,
    id_asignacion_b: int,
    id_soldado_b: int,
    motivo: str = Query(default="", max_length=500),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    resultado = confirmar_trueque(id_asignacion_a, id_asignacion_b, id_soldado_b, motivo, usuario_id, session)
    return resultado

@app.get("/ficha-soldado-ver/{id_soldado}/{mes}/{ano}")
def ficha_soldado(
    id_soldado: int = Path(..., ge=0),
    mes: int = Path(..., ge=1, le=12),
    ano: int = Path(..., ge=2020, le=2100),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    soldado = session.get(Soldado, id_soldado)
    if not soldado or soldado.id_usuario != usuario_id:
        return {"error": "Soldado no encontrado"}
    return obtener_ficha_soldado(id_soldado, mes, ano, session)

@app.post("/soldados/crear")
def crear_soldado_endpoint(
    cedula: str = Query(..., min_length=1, max_length=20),
    nombre: str = Query(..., min_length=1, max_length=100),
    apellido: str = Query(..., min_length=1, max_length=100),
    rango: str = Query(..., min_length=1, max_length=50),
    unidad: str = Query(..., min_length=1, max_length=100),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    return crear_soldado(cedula, nombre, apellido, rango, unidad, usuario_id, session)

@app.put("/soldados/editar/{id_soldado}")
def editar_soldado_endpoint(
    id_soldado: int,
    cedula: str = Query(..., min_length=1, max_length=20),
    nombre: str = Query(..., min_length=1, max_length=100),
    apellido: str = Query(..., min_length=1, max_length=100),
    rango: str = Query(..., min_length=1, max_length=50),
    unidad: str = Query(..., min_length=1, max_length=100),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    soldado = session.get(Soldado, id_soldado)
    if not soldado or soldado.id_usuario != usuario_id:
        return {"error": "Soldado no encontrado"}
    return actualizar_soldado(id_soldado, cedula, nombre, apellido, rango, unidad, session)

@app.delete("/soldados/eliminar/{id_soldado}")
def eliminar_soldado_endpoint(
    id_soldado: int,
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    soldado = session.get(Soldado, id_soldado)
    if not soldado or soldado.id_usuario != usuario_id:
        return {"error": "Soldado no encontrado"}
    return eliminar_soldado(id_soldado, session)

@app.post("/puntos/crear")
def crear_punto_endpoint(
    nombre: str = Query(..., min_length=1, max_length=100),
    descripcion: str = Query(default="", max_length=500),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    return crear_punto(nombre, descripcion, usuario_id, session)

@app.put("/puntos/editar/{id_punto}")
def editar_punto_endpoint(
    id_punto: int,
    nombre: str = Query(..., min_length=1, max_length=100),
    descripcion: str = Query(default="", max_length=500),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    punto = session.get(PuntoGuardia, id_punto)
    if not punto or punto.id_usuario != usuario_id:
        return {"error": "Punto no encontrado"}
    return editar_punto(id_punto, nombre, descripcion, session)

@app.delete("/puntos/eliminar/{id_punto}")
def eliminar_punto_endpoint(
    id_punto: int,
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    punto = session.get(PuntoGuardia, id_punto)
    if not punto or punto.id_usuario != usuario_id:
        return {"error": "Punto no encontrado"}
    return eliminar_punto(id_punto, session)

@app.get("/puntos")
def listar_puntos_endpoint(usuario_id: int = Depends(get_usuario_id), session: Session = Depends(get_session)):
    return listar_puntos(usuario_id, session)

@app.get("/exportar-pdf/{mes}/{ano}")
def exportar_pdf(
    mes: int = Path(..., ge=1, le=12),
    ano: int = Path(..., ge=2020, le=2100),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    pdf_buffer = generar_pdf(mes, ano, usuario_id, session)
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Plan_de_Guardias_{mes}_{ano}.pdf"}
    )

@app.post("/novedades")
def crear_novedad_endpoint(
    id_asignacion: int,
    descripcion: str = Query(default="Sin novedad", max_length=1000),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    return crear_novedad(id_asignacion, descripcion, usuario_id, session)


@app.get("/novedades/{mes}/{ano}")
def listar_novedades_endpoint(
    mes: int = Path(..., ge=1, le=12),
    ano: int = Path(..., ge=2020, le=2100),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    return listar_novedades(mes, ano, usuario_id, session)

@app.get("/estadisticas/{mes}/{ano}")
def estadisticas_endpoint(
    mes: int = Path(..., ge=1, le=12),
    ano: int = Path(..., ge=2020, le=2100),
    meses: int = Query(default=1, ge=1, le=12),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    return obtener_estadisticas(mes, ano, usuario_id, session, meses)

@app.get("/historial-sustituciones/{mes}/{ano}")
def historial_sustituciones_endpoint(
    mes: int = Path(..., ge=1, le=12),
    ano: int = Path(..., ge=2020, le=2100),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    return obtener_historial_sustituciones(mes, ano, usuario_id, session)

@app.post("/difundir/{mes}/{ano}")
async def difundir_endpoint(
    mes: int = Path(..., ge=1, le=12),
    ano: int = Path(..., ge=2020, le=2100),
    usuario_id: int = Depends(get_usuario_id),
    session: Session = Depends(get_session)
):
    return await difundir_pdf(mes, ano, usuario_id, session)


@app.post("/login")
def login(
    username: str = Query(..., min_length=5, max_length=50),
    password: str = Query(..., min_length=8, max_length=100),
    session: Session = Depends(get_session)
):
    if len(username) < 5 or len(password) < 8 or username == password:
        return {"error": "Credenciales inv\u00e1lidas"}
    usuario = session.exec(select(Usuario).where(Usuario.username == username)).first()
    if not usuario or usuario.password_hash != hashlib.sha256(password.encode()).hexdigest():
        return {"error": "Credenciales inv\u00e1lidas"}
    token = str(uuid.uuid4())
    sesion = Sesion(token=token, id_usuario=usuario.id_usuario)
    session.add(sesion)
    session.commit()
    return {"token": token, "usuario": usuario.username, "rol": usuario.rol}


@app.post("/register")
def register(
    username: str = Query(..., min_length=5, max_length=50),
    password: str = Query(..., min_length=8, max_length=100),
    session: Session = Depends(get_session)
):
    if len(username) < 5:
        return {"error": "El usuario debe tener al menos 5 caracteres"}
    if len(password) < 8:
        return {"error": "La contrase\u00f1a debe tener al menos 8 caracteres"}
    if username == password:
        return {"error": "El usuario y la contrase\u00f1a no pueden ser iguales"}
    existente = session.exec(select(Usuario).where(Usuario.username == username)).first()
    if existente:
        return {"error": "El usuario ya existe"}
    usuario = Usuario(
        username=username,
        password_hash=hashlib.sha256(password.encode()).hexdigest(),
        rol="admin",
    )
    session.add(usuario)
    session.commit()
    token = str(uuid.uuid4())
    sesion = Sesion(token=token, id_usuario=usuario.id_usuario)
    session.add(sesion)
    session.commit()
    return {"token": token, "usuario": usuario.username, "rol": usuario.rol}


@app.post("/logout")
def logout(authorization: str = Header(..., alias="Authorization"), session: Session = Depends(get_session)):
    if not authorization.startswith("Bearer "):
        return {"error": "Sesión inválida"}
    token = authorization[len("Bearer "):]
    sesion = session.exec(select(Sesion).where(Sesion.token == token, Sesion.activa)).first()
    if sesion:
        sesion.activa = False
        session.commit()
    return {"mensaje": "Sesi\u00f3n cerrada"}


@app.get("/verificar-sesion")
def verificar_sesion(authorization: str = Header(..., alias="Authorization"), session: Session = Depends(get_session)):
    if not authorization.startswith("Bearer "):
        return {"valido": False}
    token = authorization[len("Bearer "):]
    sesion = session.exec(select(Sesion).where(Sesion.token == token, Sesion.activa)).first()
    if not sesion:
        return {"valido": False}
    usuario = session.get(Usuario, sesion.id_usuario)
    return {"valido": True, "usuario": usuario.username, "rol": usuario.rol}
