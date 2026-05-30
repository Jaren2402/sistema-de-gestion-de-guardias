from datetime import datetime, timedelta, date
from typing import Tuple
from sqlmodel import Session, select, delete
from models import Soldado, Guardia, Asignacion, Restriccion, PuntoGuardia
import random

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

    # Obtener todas las restricciones que se solapan con este mes
    restricciones = session.exec(
        select(Restriccion).where(
            Restriccion.fecha_inicio <= (proximo_mes - timedelta(days=1)).date(),
            Restriccion.fecha_fin >= inicio.date()
        )
    ).all()

    # Seguimiento de la carga y el último día trabajado por cada soldado
    historial = {s.id_soldado: 0.0 for s in soldados}  # float por ponderación
    ultima_fecha = {s.id_soldado: None for s in soldados}
    asignaciones_creadas = []

    # Procesar días en orden cronológico
    dia_actual = inicio
    while dia_actual < proximo_mes:
        # Para cada día, procesamos los turnos en orden: primero nocturno (más pesado) luego diurno
        for turno in ["diurno", "nocturno"]:
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
            Asignacion.es_titular == True
        )
        .order_by(Guardia.fecha_inicio, PuntoGuardia.nombre)
    )
    resultados = session.exec(query).all()

    asignaciones = []
    for guardia, _, soldado, punto in resultados:
        asignaciones.append({
            "dia": guardia.fecha_inicio.day,
            "turno": guardia.tipo,
            "punto": punto.nombre,
            "cedula": soldado.cedula,
            "nombre": soldado.nombre,
            "apellido": soldado.apellido,
            "rango": soldado.rango,
            "unidad": soldado.unidad,
        })

    return {
        "mes": mes,
        "año": año,
        "asignaciones": asignaciones
    }