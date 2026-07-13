import asyncio
import datetime as dt

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import hover_row, loading_bar, module_header, no_data, toast
from skeleton import table_row as sk_row
from theme import *

_EXP = [1, 2, 2, 1, 1, 1]


def build(page: ft.Page, on_soldados_actualizados=None, on_ver_ficha=None):
    """Construye la tabla de listado de soldados con filtros, búsqueda y selección."""
    _datos = []

    barra_loading = loading_bar()
    body = ft.Column(controls=[sk_row(_EXP) for _ in range(6)], scroll=ft.ScrollMode.ADAPTIVE, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    header = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("CÉDULA", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_EXP[0]),
            ft.Container(ft.Text("NOMBRE", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_EXP[1]),
            ft.Container(ft.Text("APELLIDO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_EXP[2]),
            ft.Container(ft.Text("RANGO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_EXP[3]),
            ft.Container(ft.Text("UNIDAD", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_EXP[4]),
            ft.Container(ft.Text("REGISTRO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_EXP[5]),
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

    no_data_container = no_data(ft.Icons.PEOPLE_OUTLINED, "No hay soldados. Importe desde Excel.")
    cont_tabla = ft.Row([
        ft.Container(expand=1),
        ft.Container(content=tabla_container, expand=6, padding=ft.Padding(left=20, right=20, top=10, bottom=10)),
        ft.Container(expand=1),
    ], expand=True, visible=False)

    texto_estado = ft.Text()
    selector_archivo = ft.FilePicker()

    def _parse_fecha(valor):
        try:
            return dt.datetime.strptime(valor.strip(), "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            return None

    txt_fecha_desde = ft.TextField(label="Desde", hint_text="YYYY-MM-DD", width=200,
                                    on_change=lambda e: _filtrar())
    txt_fecha_hasta = ft.TextField(label="Hasta", hint_text="YYYY-MM-DD", width=200,
                                    on_change=lambda e: _filtrar())

    txt_buscar = ft.TextField(
        label="Buscar soldado",
        hint_text="Nombre, cédula o rango",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        on_change=lambda e: _filtrar(),
    )

    lbl_contador = ft.Text("", size=14, color=TEXT_SECONDARY)

    def _limpiar_fecha(e):
        txt_fecha_desde.value = ""
        txt_fecha_hasta.value = ""
        _filtrar()
        page.update()

    btn_limpiar = ft.FilledButton("Limpiar fechas", on_click=_limpiar_fecha, icon=ft.Icons.CLEAR)

    def _formatear_fecha(iso_str):
        if not iso_str:
            return "\u2014"
        try:
            d = dt.date.fromisoformat(iso_str[:10])
            return d.strftime("%d/%m/%Y")
        except ValueError:
            return "\u2014"

    def _filtrar():
        q = txt_buscar.value.strip().lower()
        fd = _parse_fecha(txt_fecha_desde.value)
        fh = _parse_fecha(txt_fecha_hasta.value)
        filtrados = [s for s in _datos
                     if (not q or q in s["cedula"].lower()
                         or q in s["nombre"].lower()
                         or q in s["apellido"].lower()
                         or q in s["rango"].lower())]
        if fd:
            filtrados = [s for s in filtrados if s.get("fecha_registro") and dt.date.fromisoformat(s["fecha_registro"][:10]) >= fd]
        if fh:
            filtrados = [s for s in filtrados if s.get("fecha_registro") and dt.date.fromisoformat(s["fecha_registro"][:10]) <= fh]

        body.controls.clear()
        for s in filtrados:
            row = hover_row(ft.Container(
                content=ft.Row([
                    ft.Container(ft.Text(s["cedula"], size=16, color=TEXT_TABLE), expand=_EXP[0]),
                    ft.Container(ft.Text(s["nombre"], size=16, color=TEXT_TABLE), expand=_EXP[1]),
                    ft.Container(ft.Text(s["apellido"], size=16, color=TEXT_TABLE), expand=_EXP[2]),
                    ft.Container(ft.Text(s["rango"], size=16, color=TEXT_TABLE), expand=_EXP[3]),
                    ft.Container(ft.Text(s["unidad"], size=16, color=TEXT_TABLE), expand=_EXP[4]),
                    ft.Container(ft.Text(_formatear_fecha(s.get("fecha_registro")), size=16, color=TEXT_TABLE), expand=_EXP[5]),
                ]),
                bgcolor=TABLE_ROW,
                height=40,
                padding=ft.Padding(left=16, top=0, right=16, bottom=0),
            ), pointer=True)
            sid = s["id_soldado"]
            row.on_click = lambda e, sid=sid: page.run_task(_abrir_ficha, sid)
            body.controls.append(row)
        hay = len(filtrados) > 0
        cont_tabla.visible = hay
        no_data_container.visible = not hay
        lbl_contador.value = f"Mostrando {len(filtrados)} de {len(_datos)} soldados"
        page.update()

    async def _abrir_ficha(id_soldado):
        if on_ver_ficha:
            await on_ver_ficha(id_soldado)

    async def cargar():
        nonlocal _datos
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                respuesta = await cliente.get(f"{URL_BACKEND}/soldados", params={"token": token})
                _datos = respuesta.json()
                _filtrar()
                texto_estado.value = ""
        except Exception as ex:
            toast(page, f"Error al cargar soldados: {ex}", "error")
            body.controls.clear()
            body.controls.append(
                ft.Container(ft.Text(f"Error: {ex}", italic=True, color=TEXT_SECONDARY, size=14),
                             alignment=ft.Alignment(0, 0), padding=20))
        finally:
            barra_loading.visible = False
            page.update()

    async def importar(e):
        resultado = await selector_archivo.pick_files(allowed_extensions=["xlsx"])
        if not resultado:
            return
        archivo = resultado[0]
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            if archivo.path is None:
                await selector_archivo.upload_all()
            with open(archivo.path, "rb") as f:
                contenido = f.read()
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.post(
                    f"{URL_BACKEND}/importar_soldados",
                    files={"archivo": (archivo.name, contenido)},
                    params={"token": token}
                )
                data = resp.json()
                if "error" in data:
                    toast(page, data["error"], "error")
                else:
                    toast(page, data.get("mensaje", "Importaci\u00f3n exitosa"), "success")
        except Exception as ex:
            toast(page, f"Error al importar: {ex}", "error")
        finally:
            barra_loading.visible = False
            page.update()
            await cargar()
            if on_soldados_actualizados:
                await on_soldados_actualizados()

    boton_importar = ft.FilledButton(
        "Importar soldados desde Excel",
        on_click=importar,
        icon=ft.Icons.UPLOAD_FILE,
    )
    boton_refrescar = ft.FilledButton(
        "Actualizar lista",
        on_click=lambda e: page.run_task(cargar),
        icon=ft.Icons.REFRESH,
    )

    panel = ft.Column([
        barra_loading,
        module_header("Soldados", "Gesti\u00f3n y sincronizaci\u00f3n del personal militar"),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row([boton_importar, boton_refrescar]),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row([txt_buscar, txt_fecha_desde, txt_fecha_hasta, lbl_contador]),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row([btn_limpiar]),
        cont_tabla,
        no_data_container,
    ])

    return {
        "panel": panel,
        "cargar": cargar,
        "selector_archivo": selector_archivo,
        "texto_estado": texto_estado,
    }
