import asyncio
from datetime import datetime
import os
import tempfile
import traceback as _tb

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import (
    calendar_grid,
    confirm_dialog,
    day_details_popup,
    loading_bar,
    module_header,
    toast,
)
from theme import *


def build(page: ft.Page):
    _asignaciones_raw = []

    def _log_error(context=""):
        try:
            with open("calendario_debug.log", "a", encoding="utf-8") as f:
                f.write(f"=== {context} ===\n")
                _tb.print_exc(file=f)
                f.write("\n")
        except Exception:
            pass

    barra_loading = loading_bar()
    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(MESES[i]) for i in range(12)],
        value=MESES[datetime.now().month - 1],
        width=120,
    )
    selector_año = ft.TextField(label="Año", value=str(datetime.now().year), width=100)
    contenedor_puntos = ft.Column(expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, scroll=ft.ScrollMode.AUTO)
    texto_estado = ft.Text()

    txt_buscar = ft.TextField(
        label="Buscar en calendario",
        hint_text="Nombre, cedula, rango o unidad",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        on_change=lambda e: _reconstruir(),
    )

    def _reconstruir():
        try:
            _reconstruir_inner()
        except Exception:
            _log_error("_reconstruir")
            toast(page, "Error al renderizar el calendario.", "error")

    def _reconstruir_inner():
        q = (txt_buscar.value or "").strip().lower()
        filtradas = [a for a in _asignaciones_raw
                     if not q
                     or q in a["nombre"].lower()
                     or q in a["apellido"].lower()
                     or q in a["cedula"].lower()
                     or q in a["rango"].lower()
                     or q in a["unidad"].lower()
                     or q in a["turno"].lower()]

        has_query = bool(q)

        contenedor_puntos.controls.clear()

        if not filtradas:
            contenedor_puntos.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.CALENDAR_MONTH, size=64, color=TEXT_SECONDARY),
                        ft.Text("No hay guardias para este período.", size=16, color=TEXT_SECONDARY, italic=True),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
                    alignment=ft.Alignment(0, 0),
                    padding=60,
                )
            )
            page.update()
            return

        asignaciones_por_punto = {}
        for a in filtradas:
            punto = a["punto"]
            asignaciones_por_punto.setdefault(punto, []).append(a)

        año_val = int(selector_año.value)
        mes_idx = MESES.index(selector_mes.value) + 1

        secciones = []
        for nombre_punto, lista in asignaciones_por_punto.items():
            matching_days = {a["dia"] for a in lista} if has_query else None
            assignments_by_day = {}
            for a in lista:
                dia = a["dia"]
                assignments_by_day.setdefault(dia, []).append(a)

            def make_day_click(punto, mes, año):
                def on_day_click(dia, dia_asignaciones):
                    day_details_popup(page, dia, mes, año, punto, dia_asignaciones)
                return on_day_click

            grid = calendar_grid(
                año_val,
                mes_idx,
                assignments_by_day,
                on_day_click=make_day_click(nombre_punto, selector_mes.value, año_val),
                matching_days=matching_days,
            )

            header_punto = ft.Container(
                content=ft.Text(
                    nombre_punto,
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                    text_align=ft.TextAlign.CENTER,
                ),
                bgcolor=BTN_BG,
                border_radius=ft.BorderRadius(top_left=8, top_right=8, bottom_left=0, bottom_right=0),
                padding=ft.Padding(left=12, top=8, right=12, bottom=8),
                alignment=ft.Alignment(0, 0),
                width=515,
            )

            seccion = ft.Column([header_punto, grid], spacing=0)

            secciones.append(seccion)

        contenedor_puntos.controls.clear()
        for i in range(0, len(secciones), 3):
            trio = secciones[i:i+3]
            contenedor_puntos.controls.append(
                ft.Row(trio, alignment=ft.MainAxisAlignment.START, spacing=12)
            )
            contenedor_puntos.controls.append(ft.Divider(height=16, color="transparent"))
        page.update()

    async def generar(e):
        mes_idx = MESES.index(selector_mes.value) + 1
        año_val = int(selector_año.value)

        async def _confirmar():
            barra_loading.visible = True
            page.update()
            await asyncio.sleep(0.3)
            try:
                async with httpx.AsyncClient() as cliente:
                    token = get_token(page)
                    resp = await cliente.post(
                        f"{URL_BACKEND}/generar-calendario",
                        params={"mes": mes_idx, "año": año_val},
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    datos = resp.json()
                    if "error" in datos:
                        toast(page, datos['error'], "error")
                    else:
                        toast(page, "Calendario generado correctamente", "success")
            except Exception:
                _log_error("generar_calendario")
                toast(page, "Error inesperado. Intente de nuevo.", "error")
            finally:
                barra_loading.visible = False
                page.update()

        confirm_dialog(
            page,
            title="Generar calendario",
            message=f"¿Generar el calendario de {selector_mes.value} {año_val}? Se sobrescribirá el existente.",
            button_label="Generar",
            on_confirm=_confirmar,
        )

    async def cargar(e=None):
        nonlocal _asignaciones_raw
        mes = MESES.index(selector_mes.value) + 1
        año = int(selector_año.value)
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.get(f"{URL_BACKEND}/calendario-ver/{año}/{mes}", headers={"Authorization": f"Bearer {token}"})
                datos = resp.json()
                _asignaciones_raw = datos.get("asignaciones", [])
                _reconstruir()
        except Exception:
            _log_error("cargar_calendario")
            toast(page, "Error al cargar el calendario.", "error")
        finally:
            barra_loading.visible = False
            page.update()

    async def descargar_pdf():
        mes = MESES.index(selector_mes.value) + 1
        año = int(selector_año.value)
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.get(f"{URL_BACKEND}/exportar-pdf/{mes}/{año}", headers={"Authorization": f"Bearer {token}"})
                if resp.status_code == 200:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    tmp.write(resp.content)
                    tmp.close()
                    os.startfile(tmp.name)
                else:
                    toast(page, "Error al generar el PDF. Verifique que existan guardias.", "error")
        except Exception:
            _log_error("descargar_pdf")
            toast(page, "Error inesperado. Intente de nuevo.", "error")
        finally:
            barra_loading.visible = False
            page.update()

    async def difundir():
        mes_idx = MESES.index(selector_mes.value) + 1
        año_val = int(selector_año.value)

        async def _confirmar():
            barra_loading.visible = True
            page.update()
            await asyncio.sleep(0.3)
            try:
                async with httpx.AsyncClient() as cliente:
                    token = get_token(page)
                    resp = await cliente.post(f"{URL_BACKEND}/difundir/{mes_idx}/{año_val}", headers={"Authorization": f"Bearer {token}"})
                    datos = resp.json()
                    if "error" in datos:
                        toast(page, datos['error'], "error")
                    else:
                        toast(page, "Calendario difundido correctamente", "success")
            except Exception:
                _log_error("difundir")
                toast(page, "Error inesperado. Intente de nuevo.", "error")
            finally:
                barra_loading.visible = False
                page.update()

        confirm_dialog(
            page,
            title="Difundir calendario",
            message=f"¿Difundir el calendario de {selector_mes.value} {año_val} por Telegram? Los soldados lo recibirán.",
            button_label="Difundir",
            on_confirm=_confirmar,
        )

    boton_generar = ft.FilledButton("Generar Calendario", on_click=generar, icon=ft.Icons.CALENDAR_MONTH)
    boton_ver = ft.FilledButton("Ver Calendario", on_click=cargar, icon=ft.Icons.CALENDAR_MONTH)
    boton_pdf = ft.FilledButton("Exportar PDF", on_click=lambda e: page.run_task(descargar_pdf), icon=ft.Icons.PICTURE_AS_PDF)
    boton_difundir = ft.FilledButton("Difundir", on_click=lambda e: page.run_task(difundir), icon=ft.Icons.SEND)

    panel = ft.Column([
        barra_loading,
        module_header("Calendario", "Planificación y asignación de guardias mensuales"),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row([selector_mes, selector_año, boton_generar, boton_ver, boton_pdf, boton_difundir]),
        ft.Divider(height=1, color=DIVIDER),
        txt_buscar,
        ft.Divider(height=1, color=DIVIDER),
        contenedor_puntos,
    ])

    return {
        "panel": panel,
        "generar_calendario": generar,
        "cargar_calendario": cargar,
        "contenedor_puntos": contenedor_puntos,
        "texto_estado": texto_estado,
    }
