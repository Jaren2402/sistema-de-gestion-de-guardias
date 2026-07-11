import asyncio
import calendar as _cal
from datetime import date, datetime

import flet as ft
import httpx
from config import URL_BACKEND
from skeleton import hover_row, loading_bar, module_header, no_data, toast
from skeleton import table_row as sk_row
from theme import *


def build(page: ft.Page):
    """Construye la interfaz de gestión de restricciones: CRUD de períodos no disponibles por soldado."""
    _datos = []

    texto_estado = ft.Text()
    selector_soldado = ft.Dropdown(label="Soldado", options=[], width=300)
    campo_motivo = ft.TextField(label="Motivo", width=300)
    txt_fecha_inicio = ft.TextField(label="Fecha inicio", hint_text="YYYY-MM-DD", width=200)
    txt_fecha_fin = ft.TextField(label="Fecha fin", hint_text="YYYY-MM-DD", width=200)
    selector_mes = ft.Dropdown(label="Mes", options=[ft.dropdown.Option(str(m)) for m in range(1, 13)], width=100)
    selector_mes.on_change = lambda e: _filtrar()
    selector_año = ft.TextField(label="Año", hint_text="2026", width=100, on_change=lambda e: _filtrar())
    _exp = [2, 1, 1, 2, 1]

    def _parse_fecha(valor):
        try:
            return datetime.strptime(valor.strip(), "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            return None

    barra_loading = loading_bar()
    body = ft.Column(controls=[sk_row(_exp) for _ in range(5)], scroll=ft.ScrollMode.ADAPTIVE, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    header = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("SOLDADO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[0]),
            ft.Container(ft.Text("INICIO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[1]),
            ft.Container(ft.Text("FIN", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[2]),
            ft.Container(ft.Text("MOTIVO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[3]),
            ft.Container(ft.Text("ACCIONES", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[4]),
        ]),
        bgcolor=SURFACE_LIGHT,
        padding=ft.Padding(left=16, top=12, right=16, bottom=12),
    )

    tabla_container = ft.Container(
        content=ft.Column([header, body]),
        expand=True,
        bgcolor=TABLE_BG,
        border_radius=10,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    no_data_container = no_data(ft.Icons.BLOCK, "No hay restricciones registradas.")
    cont_tabla = ft.Row([
        ft.Container(expand=1),
        ft.Container(content=tabla_container, expand=6, padding=ft.Padding(left=20, right=20, top=10, bottom=10)),
        ft.Container(expand=1),
    ], expand=True, visible=False)
    txt_buscar = ft.TextField(
        label="Buscar restricci\u00f3n",
        hint_text="Nombre del soldado o motivo",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        on_change=lambda e: _filtrar(),
    )

    def _filtrar():
        q = txt_buscar.value.strip().lower()
        try:
            mes = int(selector_mes.value)
            año = int(selector_año.value.strip())
            inicio_mes = date(año, mes, 1)
            fin_mes = date(año, mes, _cal.monthrange(año, mes)[1])
        except (ValueError, AttributeError, TypeError):
            inicio_mes = fin_mes = None
        filtrados = []
        for r in _datos:
            if q and q not in r["nombre"].lower() and q not in r["motivo"].lower():
                continue
            r_start = _parse_fecha(r["fecha_inicio"])
            r_end = _parse_fecha(r["fecha_fin"])
            if inicio_mes and fin_mes and r_start and r_end:
                if r_end < inicio_mes or r_start > fin_mes:
                    continue
            filtrados.append(r)
        body.controls.clear()
        for r in filtrados:
            body.controls.append(hover_row(ft.Container(
                content=ft.Row([
                    ft.Container(ft.Text(r["nombre"], size=16, color=TEXT_TABLE), expand=_exp[0]),
                    ft.Container(ft.Text(r["fecha_inicio"], size=16, color=TEXT_TABLE), expand=_exp[1]),
                    ft.Container(ft.Text(r["fecha_fin"], size=16, color=TEXT_TABLE), expand=_exp[2]),
                    ft.Container(ft.Text(r["motivo"], size=16, color=TEXT_TABLE), expand=_exp[3]),
                    ft.Container(ft.IconButton(icon=ft.Icons.DELETE, icon_size=18,
                                                on_click=lambda e, rid=r["id"]: _pedir_confirmacion(rid),
                                                style=ft.ButtonStyle(
                                                    color={"default": TEXT_SECONDARY, "hovered": ft.Colors.WHITE},
                                                    bgcolor={"hovered": BTN_DANGER},
                                                )),
                                 expand=_exp[4]),
                ]),
                bgcolor=TABLE_ROW,
                height=40,
                padding=ft.Padding(left=16, top=0, right=16, bottom=0),
            )))
        hay = len(filtrados) > 0
        cont_tabla.visible = hay
        no_data_container.visible = not hay
        page.update()

    def _pedir_confirmacion(rid):
        dlg = ft.AlertDialog(
            title=ft.Text("Eliminar restricci\u00f3n"),
            content=ft.Text("\u00bfEst\u00e1 seguro de eliminar esta restricci\u00f3n?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: _cerrar_dlg(dlg)),
                ft.FilledButton("Eliminar", on_click=lambda e: page.run_task(_eliminar_con_confirmacion, dlg, rid)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)
        page.update()

    def _cerrar_dlg(dlg):
        dlg.open = False
        page.update()

    async def _eliminar_con_confirmacion(dlg, rid):
        dlg.open = False
        page.update()
        await eliminar(rid)

    async def cargar_dropdown(max_intentos=3):
        intentos = 0
        while intentos < max_intentos:
            try:
                async with httpx.AsyncClient() as cliente:
                    resp = await cliente.get(f"{URL_BACKEND}/soldados")
                    datos = resp.json()
                    if datos:
                        selector_soldado.options = [
                            ft.dropdown.Option(
                                key=str(s["id_soldado"]),
                                text=f"{s['nombre']} {s['apellido']} ({s['cedula']})"
                            )
                            for s in datos
                        ]
                        texto_estado.value = ""
                        page.update()
                        return
            except Exception:
                pass
            intentos += 1
            await asyncio.sleep(1)
        toast(page, "No se pudo cargar la lista de soldados.", "warning")

    async def cargar_tabla():
        nonlocal _datos
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.get(f"{URL_BACKEND}/restricciones")
                resp.raise_for_status()
                _datos = resp.json()
                if not isinstance(_datos, list):
                    raise TypeError(f"Respuesta inesperada: {type(_datos).__name__}")
                _filtrar()
        except Exception as ex:
            toast(page, f"Error al cargar restricciones: {ex}", "error")
            body.controls.clear()
            body.controls.append(
                ft.Container(ft.Text(f"Error: {ex}", italic=True, color=TEXT_SECONDARY, size=14),
                             alignment=ft.Alignment(0, 0), padding=20))
        finally:
            barra_loading.visible = False
            page.update()

    async def crear(e):
        if not selector_soldado.value:
            toast(page, "Seleccione un soldado.", "warning")
            return
        fi = _parse_fecha(txt_fecha_inicio.value)
        ff = _parse_fecha(txt_fecha_fin.value)
        if not fi or not ff:
            toast(page, "Ingrese fechas en formato YYYY-MM-DD.", "warning")
            return
        if fi > ff:
            toast(page, "La fecha fin debe ser posterior a la fecha inicio.", "warning")
            return
        if not campo_motivo.value.strip():
            toast(page, "Ingrese un motivo.", "warning")
            return
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.post(f"{URL_BACKEND}/restricciones", params={
                    "id_soldado": int(selector_soldado.value),
                    "fecha_inicio": fi.isoformat(),
                    "fecha_fin": ff.isoformat(),
                    "motivo": campo_motivo.value.strip(),
                })
                datos = resp.json()
                if "error" in datos:
                    toast(page, datos["error"], "error")
                else:
                    toast(page, "Restricci\u00f3n creada correctamente.", "success")
                    campo_motivo.value = ""
                    txt_fecha_inicio.value = ""
                    txt_fecha_fin.value = ""
                    await cargar_tabla()
        except Exception as ex:
            toast(page, f"Error: {ex}", "error")
        finally:
            page.update()

    async def eliminar(id_restriccion: int):
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.delete(f"{URL_BACKEND}/restricciones/{id_restriccion}")
                datos = resp.json()
                if "error" in datos:
                    toast(page, datos["error"], "error")
                else:
                    toast(page, "Restricci\u00f3n eliminada.", "success")
                    await cargar_tabla()
        except Exception as ex:
            toast(page, f"Error: {ex}", "error")
        finally:
            page.update()

    boton_crear = ft.FilledButton(
        "A\u00f1adir Restricci\u00f3n",
        on_click=crear,
        icon=ft.Icons.ADD,
    )
    boton_refrescar = ft.FilledButton(
        "Refrescar",
        on_click=lambda e: page.run_task(cargar_tabla),
        icon=ft.Icons.REFRESH,
    )

    panel = ft.Column([
        barra_loading,
        module_header("Restricciones", "Control de fechas no disponibles por soldado"),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row([selector_soldado, txt_fecha_inicio, txt_fecha_fin]),
        ft.Row([campo_motivo, boton_crear]),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row([boton_refrescar, txt_buscar, selector_mes, selector_año]),
        cont_tabla,
        no_data_container,
    ])

    page.run_task(cargar_dropdown)

    return {
        "panel": panel,
        "cargar_dropdown": cargar_dropdown,
        "cargar_tabla": cargar_tabla,
        "texto_estado": texto_estado,
    }
