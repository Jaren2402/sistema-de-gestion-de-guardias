import asyncio

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import loading_bar, module_header, placeholder
from theme import *


def build(page: ft.Page, on_sustitucion_completada=None):
    """Construye la interfaz de sustitución de guardias: búsqueda de candidatos, trueques y confirmación."""
    barra_loading = loading_bar()
    texto_estado = ft.Text()
    campo_id_asignacion = ft.TextField(label="ID de asignación a sustituir", width=250)
    boton_buscar = ft.FilledButton("Buscar candidatos", on_click=lambda e: page.run_task(buscar_candidatos), icon=ft.Icons.SEARCH)
    zona_resultados = ft.Column(controls=[placeholder(ft.Icons.SWAP_HORIZ, "Ingrese un ID de asignaci\u00f3n y busque candidatos")])

    async def buscar_candidatos(e=None):
        id_asig = campo_id_asignacion.value.strip()
        if not id_asig:
            texto_estado.value = "⚠️ Debe ingresar un ID de asignación."
            texto_estado.color = ft.Colors.YELLOW
            page.update()
            return

        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.post(
                    f"{URL_BACKEND}/sustituir-guardia",
                    params={"id_asignacion_original": int(id_asig), "token": token}
                )
                datos = resp.json()
                zona_resultados.controls.clear()

                if "error" in datos:
                    texto_estado.value = f"❌ {datos['error']}"
                    texto_estado.color = ft.Colors.RED
                else:
                    intercambios = datos.get("intercambios", [])
                    candidatos = datos.get("candidatos", [])

                    if intercambios:
                        # Solo trueques
                        zona_resultados.controls.append(
                            ft.Text("🔄 Intercambios directos disponibles:", weight=ft.FontWeight.BOLD, size=16)
                        )
                        for inter in intercambios:
                            zona_resultados.controls.append(
                                ft.Card(
                                    content=ft.Container(
                                        content=ft.Column([
                                            ft.Text(f"{inter['rango_B']} {inter['nombre_B']} ({inter['cedula_B']})", weight=ft.FontWeight.BOLD),
                                            ft.Text(f"Intercambia su guardia del día {inter['dia_B']} ({inter['turno_B']})"),
                                            ft.FilledTonalButton("Seleccionar", on_click=lambda e, id_s=inter['id_soldado_B'], id_a=inter['id_asignacion_B']: page.run_task(ejecutar_trueque, id_s, id_a)),
                                        ]),
                                        padding=10,
                                    ),
                                )
                            )
                    elif candidatos:
                        # Solo sustituciones simples (ya filtradas por el backend)
                        titulo = "📋 Candidatos disponibles:" if "Ideal" in candidatos[0]['estado'] else "⚠️ Solo disponibles estos candidatos (con fatiga):"
                        zona_resultados.controls.append(
                            ft.Text(titulo, weight=ft.FontWeight.BOLD, size=16)
                        )
                        for c in candidatos:
                            estado_icono = "✅" if "Ideal" in c['estado'] else "⚠️"
                            zona_resultados.controls.append(
                                ft.Card(
                                    content=ft.Container(
                                        content=ft.Column([
                                            ft.Text(f"{estado_icono} {c['rango']} {c['nombre']} ({c['cedula']})", weight=ft.FontWeight.BOLD),
                                            ft.FilledTonalButton("Seleccionar", on_click=lambda e, id_s=c['id_soldado']: page.run_task(ejecutar_simple, id_s)),
                                        ]),
                                        padding=10,
                                    ),
                                )
                            )
                    else:
                        texto_estado.value = "ℹ️ No hay opciones disponibles para esta sustitución."
                        texto_estado.color = ft.Colors.GREY_400
                    texto_estado.value = ""
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            barra_loading.visible = False
            page.update()

    async def ejecutar_trueque(id_soldado_b, id_asignacion_b):
        id_asig = int(campo_id_asignacion.value)
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.post(
                    f"{URL_BACKEND}/confirmar-trueque",
                    params={
                        "id_asignacion_a": id_asig,
                        "id_asignacion_b": id_asignacion_b,
                        "id_soldado_b": id_soldado_b,
                        "token": token
                    }
                )
                datos = resp.json()
                if "error" in datos:
                    texto_estado.value = f"❌ {datos['error']}"
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = ""
                    zona_resultados.controls.clear()
                    campo_id_asignacion.value = ""
                    if on_sustitucion_completada:
                        on_sustitucion_completada()
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            barra_loading.visible = False
            page.update()

    async def ejecutar_simple(id_soldado):
        id_asig = int(campo_id_asignacion.value)
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.post(
                    f"{URL_BACKEND}/confirmar-sustitucion",
                    params={
                        "id_asignacion_original": id_asig,
                        "id_nuevo_soldado": id_soldado,
                        "token": token
                    }
                )
                datos = resp.json()
                if "error" in datos:
                    texto_estado.value = f"❌ {datos['error']}"
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = ""
                    zona_resultados.controls.clear()
                    campo_id_asignacion.value = ""
                    if on_sustitucion_completada:
                        on_sustitucion_completada()
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            barra_loading.visible = False
            page.update()

    panel = ft.Column([
        barra_loading,
        module_header("Sustitución", "Búsqueda y ejecución de reemplazos de guardia"),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row([campo_id_asignacion, boton_buscar]),
        ft.Divider(height=1, color=DIVIDER),
        texto_estado,
        ft.Divider(height=1, color=DIVIDER),
        zona_resultados,
    ])

    return {"panel": panel}
