from datetime import datetime, timedelta
from typing import Tuple
from sqlmodel import Session, select, delete
from models import Soldado, Guardia, Asignacion, Restriccion, PuntoGuardia, Novedad
from sqlalchemy.exc import IntegrityError
import random

# Imports para el PDF
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from collections import defaultdict

# Mapa de prioridad por rango (menor número = menor jerarquía, hará más guardias)
PRIORIDAD_RANGO = {
    "cabo segundo": 1,
    "cabo primero": 2,
    "sargento segundo": 3,
    "sargento primero": 4,
    "sargento mayor": 5,
    "teniente": 6,
    "primer teniente": 7,
    "capitán": 8,
} 

# Factores de ponderación para guardias
FACTOR_TURNO = {
    "diurno": 1.0,
    "nocturno": 2.0,
}
FACTOR_FIN_SEMANA = 1.5  # Multiplicador adicional para sábado y domingo

def generar_calendario(mes: int, año: int, session: Session) -> dict:
    """
    Genera el calendario de guardias para un mes completo.
    Limpia el mes anterior, crea turnos para cada punto de guardia,
    respetando 48 horas de descanso, restricciones y asignando con equidad.
    """
    soldados = session.exec(select(Soldado)).all()
    if not soldados:
        return {"error": "No hay soldados registrados."}

    # Obtener todos los puntos de guardia definidos por la unidad
    puntos = session.exec(select(PuntoGuardia)).all()
    if not puntos:
        return {"error": "No hay puntos de guardia definidos."}

    # Calcular el rango de fechas del mes
    inicio = datetime(año, mes, 1)
    if mes == 12:
        proximo_mes = datetime(año + 1, 1, 1)
    else:
        proximo_mes = datetime(año, mes + 1, 1)

    # --- LIMPIEZA PREVIA: eliminar el calendario anterior del mes ---
    ids_guardias = select(Guardia.id_guardia).where(
        Guardia.fecha_inicio >= inicio,
        Guardia.fecha_inicio < proximo_mes
    )
    session.exec(
        delete(Asignacion).where(Asignacion.id_guardia.in_(ids_guardias))
    )
    session.exec(
        delete(Guardia).where(
            Guardia.fecha_inicio >= inicio,
            Guardia.fecha_inicio < proximo_mes
        )
    )
    session.commit()
    # ---------------------------------------------------------------

    # --- ARRASTRE MULTI-MES: cargar fatiga del mes anterior ---
    # Determinar el inicio del mes anterior
    if mes == 1:
        mes_anterior = 12
        año_anterior = año - 1
    else:
        mes_anterior = mes - 1
        año_anterior = año

    inicio_mes_anterior = datetime(año_anterior, mes_anterior, 1)
    if mes_anterior == 12:
        fin_mes_anterior = datetime(año_anterior + 1, 1, 1) - timedelta(days=1)
    else:
        fin_mes_anterior = datetime(año_anterior, mes_anterior + 1, 1) - timedelta(days=1)

    # Consultar las últimas guardias del mes anterior (últimos 3 días)
    fecha_consulta = fin_mes_anterior - timedelta(days=3)
    asignaciones_anteriores = session.exec(
        select(Asignacion)
        .join(Guardia)
        .where(
            Asignacion.es_titular == True,
            Guardia.fecha_inicio >= fecha_consulta,
            Guardia.fecha_inicio <= fin_mes_anterior
        )
    ).all()

    # Diccionario con la última hora en que cada soldado terminó una guardia
    ultima_fecha_previa = {}
    for a in asignaciones_anteriores:
        g = session.get(Guardia, a.id_guardia)
        if g:
            if a.id_soldado not in ultima_fecha_previa or g.fecha_fin > ultima_fecha_previa[a.id_soldado]:
                ultima_fecha_previa[a.id_soldado] = g.fecha_fin
    # ---------------------------------------------------------------

    # Obtener todas las restricciones que se solapan con este mes
    restricciones = session.exec(
        select(Restriccion).where(
            Restriccion.fecha_inicio <= (proximo_mes - timedelta(days=1)).date(),
            Restriccion.fecha_fin >= inicio.date()
        )
    ).all()

    # Seguimiento de la carga y el último día trabajado por cada soldado
    historial = {s.id_soldado: 0.0 for s in soldados}  # float por ponderación

    # Inicializar la fatiga con los datos del mes anterior (arrastre)
    ultima_fecha = {}
    for s in soldados:
        ultima_fecha[s.id_soldado] = ultima_fecha_previa.get(s.id_soldado, None)

    asignaciones_creadas = []

    # Procesar días en orden cronológico
    dia_actual = inicio
    while dia_actual < proximo_mes:
        # Para cada día, procesamos los turnos en orden: primero nocturno (más pesado) luego diurno
        for turno in ["nocturno", "diurno"]:
            hora_inicio = 19 if turno == "nocturno" else 7
            fecha_inicio_turno = dia_actual.replace(hour=hora_inicio)
            fecha_fin_turno = fecha_inicio_turno + timedelta(hours=12)

            # Rotación de áreas: barajar puntos para evitar asignaciones fijas
            puntos_barajados = list(puntos)
            random.shuffle(puntos_barajados)

            for punto in puntos_barajados:
                nueva_guardia = Guardia(
                    fecha_inicio=fecha_inicio_turno,
                    fecha_fin=fecha_fin_turno,
                    tipo=turno,
                    id_punto=punto.id_punto
                )
                session.add(nueva_guardia)
                session.flush()

                # Filtrar candidatos
                candidatos = []
                for s in soldados:
                    # Fatiga: 48 horas de descanso
                    if ultima_fecha[s.id_soldado] is not None:
                        if ultima_fecha[s.id_soldado] + timedelta(hours=48) > fecha_inicio_turno:
                            continue

                    # Restricciones planificadas en este día
                    tiene_restriccion = False
                    for r in restricciones:
                        if r.id_soldado == s.id_soldado and r.fecha_inicio <= dia_actual.date() <= r.fecha_fin:
                            tiene_restriccion = True
                            break
                    if tiene_restriccion:
                        continue

                    candidatos.append(s)

                if not candidatos:
                    session.rollback()
                    return {
                        "error": f"No hay candidatos para el {dia_actual.date()} turno {turno}, punto {punto.nombre}."
                    }

                # Seleccionar al mejor candidato
                def clave_orden(s: Soldado) -> Tuple[int, int, str]:
                    prioridad = PRIORIDAD_RANGO.get(s.rango, 99)
                    return (historial[s.id_soldado], prioridad, s.cedula)

                elegido = min(candidatos, key=clave_orden)

                # Registrar asignación
                nueva_asignacion = Asignacion(
                    id_soldado=elegido.id_soldado,
                    id_guardia=nueva_guardia.id_guardia,
                    es_titular=True
                )
                session.add(nueva_asignacion)

                # Calcular factor ponderado y actualizar historial
                factor = FACTOR_TURNO.get(turno, 1.0)
                if dia_actual.weekday() in (5, 6):  # fin de semana
                    factor *= FACTOR_FIN_SEMANA
                historial[elegido.id_soldado] += factor
                ultima_fecha[elegido.id_soldado] = fecha_inicio_turno

                asignaciones_creadas.append({
                    "fecha": dia_actual.strftime("%Y-%m-%d"),
                    "turno": turno,
                    "punto": punto.nombre,
                    "cedula": elegido.cedula,
                    "nombre": f"{elegido.nombre} {elegido.apellido}"
                })

        dia_actual += timedelta(days=1)

    session.commit()
    return {
        "mensaje": "Calendario generado correctamente.",
        "total_guardias": len(asignaciones_creadas),
        "detalle": asignaciones_creadas
    }

def obtener_calendario(mes: int, año: int, session: Session) -> dict:
    """
    Devuelve el calendario de guardias generado para un mes,
    organizado como lista plana con todos los detalles del soldado.
    """
    inicio = datetime(año, mes, 1)
    if mes == 12:
        proximo_mes = datetime(año + 1, 1, 1)
    else:
        proximo_mes = datetime(año, mes + 1, 1)

    query = (
        select(Guardia, Asignacion, Soldado, PuntoGuardia)
        .join(Asignacion, Guardia.id_guardia == Asignacion.id_guardia)
        .join(Soldado, Asignacion.id_soldado == Soldado.id_soldado)
        .join(PuntoGuardia, Guardia.id_punto == PuntoGuardia.id_punto)
        .where(
            Guardia.fecha_inicio >= inicio,
            Guardia.fecha_inicio < proximo_mes,
            Asignacion.es_titular
        )
        .order_by(Guardia.fecha_inicio, PuntoGuardia.nombre)
    )
    resultados = session.exec(query).all()

    asignaciones = []
    for guardia, asignacion, soldado, punto in resultados:
        asignaciones.append({
            "dia": guardia.fecha_inicio.day,
            "turno": guardia.tipo,
            "punto": punto.nombre,
            "cedula": soldado.cedula,
            "nombre": soldado.nombre,
            "apellido": soldado.apellido,
            "rango": soldado.rango,
            "unidad": soldado.unidad,
            "id_asignacion": asignacion.id_asignacion,
        })

    return {
        "mes": mes,
        "año": año,
        "asignaciones": asignaciones
    }
    
def buscar_candidatos_sustitucion(id_asignacion_original: int, session: Session) -> dict:
    """Busca los mejores candidatos para sustituir a un soldado, incluyendo intercambios directos."""
    asignacion_original = session.get(Asignacion, id_asignacion_original)
    if not asignacion_original:
        return {"error": "Asignación no encontrada."}
    
    guardia_original = session.get(Guardia, asignacion_original.id_guardia)
    if not guardia_original:
        return {"error": "Guardia no encontrada."}
    
    soldados = session.exec(select(Soldado)).all()
    fecha_guardia = guardia_original.fecha_inicio
    
    # Restricciones en esa fecha
    restricciones = session.exec(
        select(Restriccion).where(
            Restriccion.fecha_inicio <= fecha_guardia.date(),
            Restriccion.fecha_fin >= fecha_guardia.date()
        )
    ).all()

    # --- Calcular puntos acumulados de cada soldado en este mes ---
    inicio_mes = fecha_guardia.replace(day=1)
    if fecha_guardia.month == 12:
        fin_mes = inicio_mes.replace(year=fecha_guardia.year + 1, month=1) - timedelta(days=1)
    else:
        fin_mes = inicio_mes.replace(month=fecha_guardia.month + 1) - timedelta(days=1)

    puntos_soldados = {}
    for s in soldados:
        total = 0.0
        asignaciones_mes = session.exec(
            select(Asignacion)
            .join(Guardia)
            .where(
                Asignacion.id_soldado == s.id_soldado,
                Asignacion.es_titular == True,
                Asignacion.es_anulada == False,
                Guardia.fecha_inicio >= inicio_mes,
                Guardia.fecha_inicio <= fin_mes
            )
        ).all()
        for a in asignaciones_mes:
            g = session.get(Guardia, a.id_guardia)
            if g:
                factor = FACTOR_TURNO.get(g.tipo, 1.0)
                if g.fecha_inicio.weekday() in (5, 6):
                    factor *= FACTOR_FIN_SEMANA
                total += factor
        puntos_soldados[s.id_soldado] = total
    # ------------------------------------------------------------

    # 1. Buscar intercambios directos (A <-> B)
    intercambios = []
    candidatos_ideales = []
    candidatos_fatigados = []
    
    for s in soldados:
        if s.id_soldado == asignacion_original.id_soldado:
            continue
        
        # Verificar restricciones de s para la guardia original
        if any(r.id_soldado == s.id_soldado for r in restricciones):
            continue
        
        # Verificar si s puede cubrir la guardia original (fatiga)
        puede_cubrir = _puede_cubrir_guardia(s, fecha_guardia, session)
        
        # Buscar trueques para este s
        if puede_cubrir["disponible"]:
            guardia_de_s = session.exec(
                select(Guardia)
                .join(Asignacion)
                .where(
                    Asignacion.id_soldado == s.id_soldado,
                    Asignacion.es_titular == True,
                    Asignacion.es_anulada == False,
                    Guardia.fecha_inicio > fecha_guardia
                )
                .order_by(Guardia.fecha_inicio)
            ).first()
            
            if guardia_de_s:
                puede_cubrir_A = _puede_cubrir_guardia(
                    session.get(Soldado, asignacion_original.id_soldado),
                    guardia_de_s.fecha_inicio,
                    session
                )
                if puede_cubrir_A["disponible"]:
                    intercambios.append({
                        "id_soldado_B": s.id_soldado,
                        "cedula_B": s.cedula,
                        "nombre_B": f"{s.nombre} {s.apellido}",
                        "rango_B": s.rango,
                        "dia_B": guardia_de_s.fecha_inicio.day,
                        "turno_B": guardia_de_s.tipo,
                        "id_asignacion_B": session.exec(
                            select(Asignacion.id_asignacion).where(
                                Asignacion.id_soldado == s.id_soldado,
                                Asignacion.id_guardia == guardia_de_s.id_guardia
                            )
                        ).first()
                    })
        
        # Clasificar en ideales o fatigados
        if puede_cubrir["disponible"]:
            candidatos_ideales.append((s, puede_cubrir["horas_descanso"], "✅ Ideal"))
        else:
            candidatos_fatigados.append((s, puede_cubrir["horas_descanso"], f"⚠️ Solo {puede_cubrir['horas_descanso']:.0f}h descanso"))
    
    # --- Ordenar por puntos acumulados del mes ---
    def clave(item):
        s, _, _ = item
        puntos = puntos_soldados.get(s.id_soldado, 999)
        prioridad = PRIORIDAD_RANGO.get(s.rango, 99)
        return (puntos, prioridad, s.cedula)
    
    candidatos_ideales.sort(key=clave)
    candidatos_fatigados.sort(key=clave)
    # ------------------------------------------

    # Decidir qué candidatos mostrar
    if intercambios or candidatos_ideales:
        candidatos_finales = candidatos_ideales
    else:
        candidatos_finales = candidatos_fatigados
    
    # --- Limitar resultados ---
    return {
        "intercambios": intercambios[:5],
        "candidatos": [
            {
                "id_soldado": s.id_soldado,
                "cedula": s.cedula,
                "nombre": f"{s.nombre} {s.apellido}",
                "rango": s.rango,
                "estado": estado
            } for s, _, estado in candidatos_finales[:5]
        ]
    }
    # -------------------------


def _puede_cubrir_guardia(soldado: Soldado, fecha_guardia: datetime, session: Session) -> dict:
    """Verifica si un soldado puede cubrir una guardia en una fecha dada (fatiga)."""
    ultima_asignacion = session.exec(
        select(Asignacion)
        .join(Guardia)
        .where(
            Asignacion.id_soldado == soldado.id_soldado,
            Asignacion.es_titular == True,
            Asignacion.es_anulada == False,
            Guardia.fecha_fin < fecha_guardia
        )
        .order_by(Guardia.fecha_fin.desc())
    ).first()
    
    if ultima_asignacion is None:
        return {"disponible": True, "horas_descanso": 999}
    
    ultima_guardia = session.get(Guardia, ultima_asignacion.id_guardia)
    horas_descanso = (fecha_guardia - ultima_guardia.fecha_fin).total_seconds() / 3600
    
    return {
        "disponible": horas_descanso >= 48,
        "horas_descanso": horas_descanso
    }
    
def confirmar_sustitucion(id_asignacion_original: int, id_nuevo_soldado: int, session: Session) -> dict:
    """Realiza la sustitución simple: anula la original y crea una nueva asignación titular."""
    asignacion_original = session.get(Asignacion, id_asignacion_original)
    if not asignacion_original:
        return {"error": "Asignación original no encontrada."}
    
    # 1. Anular la asignación original del titular
    asignacion_original.es_anulada = True
    session.add(asignacion_original)
    
    # 2. Crear nueva asignación para el sustituto (como titular)
    nueva_asignacion = Asignacion(
        id_soldado=id_nuevo_soldado,
        id_guardia=asignacion_original.id_guardia,
        es_titular=True,  # <-- Ahora cuenta para sus estadísticas
        id_asignacion_original=asignacion_original.id_asignacion
    )
    session.add(nueva_asignacion)
    session.commit()
    session.refresh(nueva_asignacion)
    
    return {
        "mensaje": "Sustitución realizada correctamente.",
        "id_nueva_asignacion": nueva_asignacion.id_asignacion
    }
    
def confirmar_trueque(id_asignacion_A: int, id_asignacion_B: int, id_soldado_B: int, session: Session) -> dict:
    """Intercambia los soldados de dos guardias (trueque binario)."""
    asignacion_A = session.get(Asignacion, id_asignacion_A)
    asignacion_B = session.get(Asignacion, id_asignacion_B)
    
    if not asignacion_A or not asignacion_B:
        return {"error": "Alguna de las asignaciones no fue encontrada."}
    
    # Obtener las guardias para acceder a las fechas
    guardia_A = session.get(Guardia, asignacion_A.id_guardia)
    guardia_B = session.get(Guardia, asignacion_B.id_guardia)
    if not guardia_A or not guardia_B:
        return {"error": "Alguna de las guardias no fue encontrada."}
    
    # Guardar nombres originales ANTES del intercambio
    soldado_original_A = session.get(Soldado, asignacion_A.id_soldado)
    nombre_original_A = f"{soldado_original_A.nombre} {soldado_original_A.apellido}" if soldado_original_A else "Desconocido"
    soldado_original_B = session.get(Soldado, asignacion_B.id_soldado)
    nombre_original_B = f"{soldado_original_B.nombre} {soldado_original_B.apellido}" if soldado_original_B else "Desconocido"
    
    # Intercambiar soldados
    id_soldado_A = asignacion_A.id_soldado
    asignacion_A.id_soldado = id_soldado_B
    asignacion_B.id_soldado = id_soldado_A
    
    session.add(asignacion_A)
    session.add(asignacion_B)
    session.flush()
    
    # Crear novedad de auditoría para el historial (usando fechas de guardias)
    texto_trueque = f"{nombre_original_A} (Día {guardia_A.fecha_inicio.day}) ↔ {nombre_original_B} (Día {guardia_B.fecha_inicio.day})"
    novedad = Novedad(
        id_asignacion=asignacion_A.id_asignacion,
        descripcion=f"TRUEQUE:{texto_trueque}",
        fecha_reporte=guardia_A.fecha_inicio  # <-- Usar fecha de la guardia
    )
    session.add(novedad)
    session.commit()
    
    return {"mensaje": "Trueque realizado correctamente."}

def obtener_ficha_soldado(id_soldado: int, mes: int, año: int, session: Session) -> dict:
    """Devuelve el historial de guardias de un soldado en un mes."""
    inicio = datetime(año, mes, 1)
    if mes == 12:
        proximo_mes = datetime(año + 1, 1, 1)
    else:
        proximo_mes = datetime(año, mes + 1, 1)

    query = (
        select(Asignacion, Guardia, PuntoGuardia)
        .join(Guardia, Asignacion.id_guardia == Guardia.id_guardia)
        .join(PuntoGuardia, Guardia.id_punto == PuntoGuardia.id_punto)
        .where(
            Asignacion.id_soldado == id_soldado,
            Guardia.fecha_inicio >= inicio,
            Guardia.fecha_inicio < proximo_mes,
            Asignacion.es_anulada == False   
        )
        .order_by(Guardia.fecha_inicio)
    )
    resultados = session.exec(query).all()

    guardias = []
    total_puntos = 0.0
    for asignacion, guardia, punto in resultados:
        factor = FACTOR_TURNO.get(guardia.tipo, 1.0)
        if guardia.fecha_inicio.weekday() in (5, 6):
            factor *= FACTOR_FIN_SEMANA
        total_puntos += factor

        guardias.append({
            "dia": guardia.fecha_inicio.day,
            "turno": guardia.tipo,
            "punto": punto.nombre,
            "es_titular": asignacion.es_titular,
            "factor": factor,
        })

    soldado = session.get(Soldado, id_soldado)
    nombre_soldado = f"{soldado.nombre} {soldado.apellido}" if soldado else "Desconocido"

    return {
        "id_soldado": id_soldado,
        "nombre": nombre_soldado,
        "mes": mes,
        "año": año,
        "total_guardias": len(guardias),
        "total_puntos": total_puntos,
        "guardias": guardias
    }
    
def crear_soldado(cedula: str, nombre: str, apellido: str, rango: str, unidad: str, session: Session) -> dict:
    """Crea un nuevo soldado y lo guarda en la base de datos."""
    try:
        soldado = Soldado(cedula=cedula, nombre=nombre, apellido=apellido, rango=rango, unidad=unidad)
        session.add(soldado)
        session.commit()
        session.refresh(soldado)
        return {"mensaje": "Soldado creado correctamente.", "id_soldado": soldado.id_soldado}
    except IntegrityError:
        session.rollback()
        return {"error": "Ya existe un soldado con esa cédula."}

def actualizar_soldado(id_soldado: int, cedula: str, nombre: str, apellido: str, rango: str, unidad: str, session: Session) -> dict:
    """Actualiza los datos de un soldado existente."""
    soldado = session.get(Soldado, id_soldado)
    if not soldado:
        return {"error": "Soldado no encontrado."}
    soldado.cedula = cedula
    soldado.nombre = nombre
    soldado.apellido = apellido
    soldado.rango = rango
    soldado.unidad = unidad
    try:
        session.commit()
        return {"mensaje": "Soldado actualizado correctamente."}
    except IntegrityError:
        session.rollback()
        return {"error": "Ya existe otro soldado con esa cédula."}

def eliminar_soldado(id_soldado: int, session: Session) -> dict:
    """Elimina un soldado de la base de datos."""
    soldado = session.get(Soldado, id_soldado)
    if not soldado:
        return {"error": "Soldado no encontrado."}
    session.delete(soldado)
    session.commit()
    return {"mensaje": "Soldado eliminado correctamente."}

def crear_punto(nombre: str, descripcion: str, session: Session) -> dict:
    try:
        punto = PuntoGuardia(nombre=nombre, descripcion=descripcion)
        session.add(punto)
        session.commit()
        session.refresh(punto)
        return {"mensaje": "Punto de guardia creado.", "id": punto.id_punto}
    except IntegrityError:
        session.rollback()
        return {"error": "Ya existe un punto con ese nombre."}

def editar_punto(id_punto: int, nombre: str, descripcion: str, session: Session) -> dict:
    punto = session.get(PuntoGuardia, id_punto)
    if not punto:
        return {"error": "Punto no encontrado."}
    punto.nombre = nombre
    punto.descripcion = descripcion
    try:
        session.commit()
        return {"mensaje": "Punto actualizado correctamente."}
    except IntegrityError:
        session.rollback()
        return {"error": "Ya existe un punto con ese nombre."}

def eliminar_punto(id_punto: int, session: Session) -> dict:
    punto = session.get(PuntoGuardia, id_punto)
    if not punto:
        return {"error": "Punto no encontrado."}
    session.delete(punto)
    session.commit()
    return {"mensaje": "Punto eliminado correctamente."}

def listar_puntos(session: Session):
    puntos = session.exec(select(PuntoGuardia).order_by(PuntoGuardia.nombre)).all()
    return [
        {"id": p.id_punto, "nombre": p.nombre, "descripcion": p.descripcion or ""}
        for p in puntos
    ]
    
def generar_pdf(mes: int, año: int, session: Session) -> BytesIO:
    """
    Genera un PDF del calendario de guardias de un mes.
    Formato vertical (A4). Una tabla por página, centrada y compacta.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=35,
        bottomMargin=35,
        leftMargin=20,
        rightMargin=20,
    )
    elements = []
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("cell", fontSize=10.5, leading=10)
    header_style = ParagraphStyle("header", fontSize=11, leading=12, bold=True)
    title_style = styles["Title"]

    # Calcular fechas del mes
    inicio = datetime(año, mes, 1)
    if mes == 12:
        proximo_mes = datetime(año + 1, 1, 1)
    else:
        proximo_mes = datetime(año, mes + 1, 1)

    # Consultar asignaciones
    query = (
        select(
            PuntoGuardia.nombre,
            Guardia.fecha_inicio,
            Guardia.tipo,
            Soldado.cedula,
            Soldado.nombre,
            Soldado.apellido,
            Soldado.rango,
        )
        .join(Guardia, PuntoGuardia.id_punto == Guardia.id_punto)
        .join(Asignacion, Guardia.id_guardia == Asignacion.id_guardia)
        .join(Soldado, Asignacion.id_soldado == Soldado.id_soldado)
        .where(
            Guardia.fecha_inicio >= inicio,
            Guardia.fecha_inicio < proximo_mes,
            Asignacion.es_titular == True,
            Asignacion.es_anulada == False,
        )
        .order_by(PuntoGuardia.nombre, Guardia.fecha_inicio, Guardia.tipo)
    )
    resultados = session.exec(query).all()

    # Agrupar datos por área y turno
    datos_por_area = defaultdict(lambda: defaultdict(list))
    for nombre_punto, fecha, tipo, cedula, nombre, apellido, rango in resultados:
        dia = fecha.day
        turno_str = "Diurno" if tipo == "diurno" else "Nocturno"
        datos_por_area[nombre_punto][turno_str].append((str(dia), cedula, nombre, apellido, rango))

    # Ancho de la tabla que se usará en todas las páginas
    available_width = A4[0] - 130
    left_indent_sub = 39

    # Estilo para los subtítulos con el margen izquierdo calculado
    subtitle_style = ParagraphStyle(
        "subtitle",
        parent=styles["Normal"],
        fontSize=12,
        leading=14,
        bold=True,
        leftIndent=left_indent_sub,
    )

    # Estilo para la firma (se usará en cada página)
    firma_style = ParagraphStyle(
        "firma",
        parent=styles["Normal"],
        fontSize=12,
        leading=14,
        leftIndent=-14,
        alignment=1
    )

    primera_pagina = True
    for area, turnos in datos_por_area.items():
        for turno, filas in [("Diurno", turnos["Diurno"]), ("Nocturno", turnos["Nocturno"])]:
            if not primera_pagina:
                elements.append(PageBreak())
            primera_pagina = False

            # Título centrado
            elements.append(Paragraph("PLANIFICACIÓN DE GUARDIAS", title_style))
            elements.append(Spacer(1, 28))

            # Subtítulos alineados a la tabla
            elements.append(Paragraph(f"AÑO: {año}  -  MES: {mes}", subtitle_style))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(f"ÁREA: {area}  -  TURNO: {turno}", subtitle_style))
            elements.append(Spacer(1, 12))

            # Cabecera de la tabla
            header = [
                Paragraph("Día", header_style),
                Paragraph("Cédula", header_style),
                Paragraph("Nombre", header_style),
                Paragraph("Apellido", header_style),
                Paragraph("Rango", header_style),
            ]
            data = [header]

            for dia, cedula, nombre, apellido, rango in filas:
                data.append([
                    Paragraph(dia, cell_style),
                    Paragraph(cedula, cell_style),
                    Paragraph(nombre, cell_style),
                    Paragraph(apellido, cell_style),
                    Paragraph(rango, cell_style),
                ])

            col_widths = [
                available_width * 0.08,
                available_width * 0.22,
                available_width * 0.23,
                available_width * 0.23,
                available_width * 0.24,
            ]
            table = Table(data, colWidths=col_widths, hAlign="CENTER")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]))
            elements.append(table)

            # --- Firma del comandante (ahora dentro del bucle, aparece en cada página) ---
            elements.append(Spacer(1, 55))
            elements.append(Paragraph("___________________________", firma_style))
            elements.append(Spacer(1, 4))
            elements.append(Paragraph("Comandante de la Unidad", firma_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer

def crear_novedad(id_asignacion: int, descripcion: str, session: Session) -> dict:
    """Registra una novedad para una asignación de guardia."""
    asignacion = session.get(Asignacion, id_asignacion)
    if not asignacion:
        return {"error": "Asignación no encontrada."}
    novedad = Novedad(
        id_asignacion=id_asignacion,
        descripcion=descripcion,
    )
    session.add(novedad)
    session.commit()
    session.refresh(novedad)
    return {
        "mensaje": "Novedad registrada correctamente.",
        "id_novedad": novedad.id_novedad
    }


def listar_novedades(mes: int, año: int, session: Session) -> list:
    """Devuelve todas las novedades de un mes, con datos de la guardia y el soldado."""
    inicio = datetime(año, mes, 1)
    if mes == 12:
        proximo_mes = datetime(año + 1, 1, 1)
    else:
        proximo_mes = datetime(año, mes + 1, 1)

    query = (
        select(Novedad, Asignacion, Guardia, Soldado, PuntoGuardia)
        .join(Asignacion, Novedad.id_asignacion == Asignacion.id_asignacion)
        .join(Guardia, Asignacion.id_guardia == Guardia.id_guardia)
        .join(Soldado, Asignacion.id_soldado == Soldado.id_soldado)
        .join(PuntoGuardia, Guardia.id_punto == PuntoGuardia.id_punto)
        .where(
            Guardia.fecha_inicio >= inicio,
            Guardia.fecha_inicio < proximo_mes,
            Asignacion.es_anulada == False,
        )
        .order_by(Guardia.fecha_inicio.desc())
    )
    resultados = session.exec(query).all()

    novedades = []
    for novedad, asignacion, guardia, soldado, punto in resultados:
        novedades.append({
            "id_novedad": novedad.id_novedad,
            "id_asignacion": asignacion.id_asignacion,
            "fecha": guardia.fecha_inicio.strftime("%Y-%m-%d"),
            "turno": guardia.tipo,
            "punto": punto.nombre,
            "soldado": f"{soldado.nombre} {soldado.apellido}",
            "cedula": soldado.cedula,
            "descripcion": novedad.descripcion,
            "fecha_reporte": novedad.fecha_reporte.isoformat(),
        })
    return novedades

def obtener_estadisticas(mes: int, año: int, session: Session) -> dict:
    """Devuelve estadísticas completas del mes: KPIs, equidad, rankings y detalles de incidencias."""
    inicio = datetime(año, mes, 1)
    if mes == 12:
        proximo_mes = datetime(año + 1, 1, 1)
    else:
        proximo_mes = datetime(año, mes + 1, 1)

    # --- Guardias titulares del mes (para la mayoría de métricas) ---
    query_titulares = (
        select(Soldado, Asignacion, Guardia)
        .join(Asignacion, Soldado.id_soldado == Asignacion.id_soldado)
        .join(Guardia, Asignacion.id_guardia == Guardia.id_guardia)
        .where(
            Guardia.fecha_inicio >= inicio,
            Guardia.fecha_inicio < proximo_mes,
            Asignacion.es_titular == True,
            Asignacion.es_anulada == False
        )
    )
    titulares = session.exec(query_titulares).all()

    # --- Sustituciones del mes (es_titular=False) ---
    query_sustituciones = (
        select(Asignacion, Guardia, Soldado)
        .join(Guardia, Asignacion.id_guardia == Guardia.id_guardia)
        .join(Soldado, Asignacion.id_soldado == Soldado.id_soldado)
        .where(
            Guardia.fecha_inicio >= inicio,
            Guardia.fecha_inicio < proximo_mes,
            Asignacion.es_titular == False
        )
    )
    sustituciones_data = session.exec(query_sustituciones).all()

    # --- Restricciones que se solapan con el mes ---
    restricciones_data = session.exec(
        select(Restriccion, Soldado)
        .join(Soldado, Restriccion.id_soldado == Soldado.id_soldado)
        .where(
            Restriccion.fecha_inicio <= (proximo_mes - timedelta(days=1)).date(),
            Restriccion.fecha_fin >= inicio.date()
        )
    ).all()

    # --- Métricas por soldado ---
    datos_soldados = {}
    for soldado, asignacion, guardia in titulares:
        sid = soldado.id_soldado
        if sid not in datos_soldados:
            datos_soldados[sid] = {
                "soldado": soldado,
                "guardias": 0,
                "puntos": 0.0,
                "nocturnas": 0,
                "finde": 0,
            }
        d = datos_soldados[sid]
        d["guardias"] += 1
        factor = FACTOR_TURNO.get(guardia.tipo, 1.0)
        is_weekend = guardia.fecha_inicio.weekday() in (5, 6)
        if is_weekend:
            factor *= FACTOR_FIN_SEMANA
            d["finde"] += 1
        if guardia.tipo == "nocturno":
            d["nocturnas"] += 1
        d["puntos"] += factor

    # --- Lista de soldados ---
    lista_soldados = []
    for d in datos_soldados.values():
        lista_soldados.append({
            "id_soldado": d["soldado"].id_soldado,
            "nombre": f"{d['soldado'].nombre} {d['soldado'].apellido}",
            "rango": d["soldado"].rango,
            "total_guardias": d["guardias"],
            "total_puntos": round(d["puntos"], 1),
            "nocturnas": d["nocturnas"],
            "finde": d["finde"],
        })

    # --- Ordenamientos para rankings ---
    mas_guardias = sorted(lista_soldados, key=lambda x: x["total_guardias"], reverse=True)[:5]
    menos_guardias = sorted(lista_soldados, key=lambda x: x["total_guardias"])[:5]
    mas_puntos = sorted(lista_soldados, key=lambda x: x["total_puntos"], reverse=True)[:5]
    menos_puntos = sorted(lista_soldados, key=lambda x: x["total_puntos"])[:5]
    mas_nocturnos = sorted(lista_soldados, key=lambda x: x["nocturnas"], reverse=True)[:5]
    mas_finde = sorted(lista_soldados, key=lambda x: x["finde"], reverse=True)[:5]

    # --- KPIs ---
    total_guardias = sum(s["total_guardias"] for s in lista_soldados)
    total_sustituciones = len(sustituciones_data)
    total_restricciones = len(restricciones_data)

    # --- Porcentaje de equidad ---
    max_puntos = max(s["total_puntos"] for s in lista_soldados) if lista_soldados else 1
    min_puntos = min(s["total_puntos"] for s in lista_soldados) if lista_soldados else 1
    dif = max_puntos - min_puntos
    equidad_pct = max(0, 1 - (dif / max_puntos)) * 100 if max_puntos > 0 else 100

    # --- Detalle de sustituciones y restricciones (para mostrar en tablas) ---
    detalle_sustituciones = []
    for asig, guardia, soldado in sustituciones_data:
        detalle_sustituciones.append({
            "fecha": guardia.fecha_inicio.strftime("%Y-%m-%d"),
            "turno": guardia.tipo,
            "soldado": f"{soldado.nombre} {soldado.apellido}",
            "cedula": soldado.cedula,
            "id_asignacion_original": asig.id_asignacion_original,
        })

    detalle_restricciones = []
    for rest, soldado in restricciones_data:
        detalle_restricciones.append({
            "id": rest.id_restriccion,
            "soldado": f"{soldado.nombre} {soldado.apellido}",
            "cedula": soldado.cedula,
            "fecha_inicio": rest.fecha_inicio.isoformat(),
            "fecha_fin": rest.fecha_fin.isoformat(),
            "motivo": rest.motivo,
        })

    return {
        "kpi": {
            "total_guardias": total_guardias,
            "total_sustituciones": total_sustituciones,
            "total_restricciones": total_restricciones,
        },
        "equidad": {
            "porcentaje": round(equidad_pct, 1),
            "diferencia_max_min": round(dif, 1),
            "max_puntos": round(max_puntos, 1),
        },
        "tops": {
            "mas_guardias": mas_guardias,
            "menos_guardias": menos_guardias,
            "mas_puntos": mas_puntos,
            "menos_puntos": menos_puntos,
            "mas_nocturnos": mas_nocturnos,
            "mas_finde": mas_finde,
        },
        "detalle_sustituciones": detalle_sustituciones,
        "detalle_restricciones": detalle_restricciones,
    }
    
def obtener_historial_sustituciones(mes: int, año: int, session: Session) -> list:
    """Devuelve el historial de sustituciones de un mes, con trueques enriquecidos."""
    inicio = datetime(año, mes, 1)
    if mes == 12:
        proximo_mes = datetime(año + 1, 1, 1)
    else:
        proximo_mes = datetime(año, mes + 1, 1)

    # --- 1. Sustituciones simples ---
    query = (
        select(Asignacion, Guardia, Soldado, PuntoGuardia)
        .join(Guardia, Asignacion.id_guardia == Guardia.id_guardia)
        .join(Soldado, Asignacion.id_soldado == Soldado.id_soldado)
        .join(PuntoGuardia, Guardia.id_punto == PuntoGuardia.id_punto)
        .where(
            Guardia.fecha_inicio >= inicio,
            Guardia.fecha_inicio < proximo_mes,
            Asignacion.id_asignacion_original.isnot(None)
        )
        .order_by(Guardia.fecha_inicio.desc())
    )
    resultados = session.exec(query).all()

    historial = []
    for asignacion, guardia, soldado, punto in resultados:
        asignacion_original = session.get(Asignacion, asignacion.id_asignacion_original)
        if not asignacion_original:
            continue
        if asignacion_original.es_anulada:
            soldado_original = session.get(Soldado, asignacion_original.id_soldado)
            titular_original = f"{soldado_original.nombre} {soldado_original.apellido}" if soldado_original else ""
            historial.append({
                "fecha": guardia.fecha_inicio.strftime("%Y-%m-%d"),
                "turno": guardia.tipo,
                "punto": punto.nombre,
                "titular_original": titular_original,
                "sustituto": f"{soldado.nombre} {soldado.apellido}",
                "cedula_sustituto": soldado.cedula,
                "tipo": "Simple",
                "id_asignacion": asignacion.id_asignacion,
            })

    # --- 2. Trueques (novedades enriquecidas) ---
    novedades_trueque = session.exec(
        select(Novedad).where(
            Novedad.fecha_reporte >= inicio,
            Novedad.fecha_reporte < proximo_mes,
            Novedad.descripcion.startswith("TRUEQUE:")
        )
    ).all()

    for nov in novedades_trueque:
        texto = nov.descripcion[len("TRUEQUE:"):]
        # Obtener datos de la guardia asociada
        asignacion = session.get(Asignacion, nov.id_asignacion)
        if asignacion:
            guardia = session.get(Guardia, asignacion.id_guardia)
            punto = session.get(PuntoGuardia, guardia.id_punto) if guardia else None
            historial.append({
                "tipo": "Trueque",
                "texto_trueque": texto,
                "fecha": guardia.fecha_inicio.strftime("%Y-%m-%d") if guardia else "",
                "turno": guardia.tipo if guardia else "",
                "punto": punto.nombre if punto else "",
            })
        else:
            historial.append({
                "tipo": "Trueque",
                "texto_trueque": texto,
                "fecha": "",
                "turno": "",
                "punto": "",
            })

    return historial