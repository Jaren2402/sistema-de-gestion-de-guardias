import asyncio
import calendar as _cal
from datetime import date, datetime

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import confirm_dialog, loading_bar, module_header, no_data, toast
from theme import *


def _field_style():
    return dict(
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER,
        focused_border_color=PRIMARY,
        cursor_color=PRIMARY,
    )


def build(page: ft.Page):
    _datos = []
    _exp = [2, 1, 1, 2, 1]

    barra_loading = loading_bar()

    selector_soldado = ft.Dropdown(
        label="Soldado", options=[], expand=True,
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY,
    )
    txt_fecha_inicio = ft.TextField(label="Fecha inicio", hint_text="YYYY-MM-DD", expand=True, **_field_style())
    txt_fecha_fin = ft.TextField(label="Fecha fin", hint_text="YYYY-MM-DD", expand=True, **_field_style())
    campo_motivo = ft.TextField(label="Motivo", expand=True, **_field_style())

    txt_buscar = ft.TextField(
        label="Buscar restricción",
        hint_text="Nombre del soldado o motivo",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        on_change=lambda e: _filtrar(),
        **_field_style(),
    )

    selector_mes = ft.Dropdown(
        label="Mes", options=[ft.dropdown.Option(MESES[i]) for i in range(12)],
        width=130,
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY,
    )
    selector_mes.on_change = lambda e: _filtrar()
    selector_año = ft.TextField(
        label="Año", hint_text="2026", width=100,
        on_change=lambda e: _filtrar(),
        **_field_style(),
    )

    def _parse_fecha(valor):
        try:
            return datetime.strptime(valor.strip(), "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            return None

    body = ft.Column(
        controls=[], scroll=ft.ScrollMode.ADAPTIVE, expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=4,
    )

    header_row = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("SOLDADO", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_exp[0], alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("INICIO", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_exp[1], alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("FIN", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_exp[2], alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("MOTIVO", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_exp[3], alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("ACCIONES", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_exp[4], alignment=ft.Alignment(-1, 0)),
        ]),
        bgcolor=BTN_BG,
        border_radius=ft.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0),
        padding=ft.Padding(16, 10, 16, 10),
    )

    tabla_container = ft.Container(
        content=ft.Column([header_row, body]),
        expand=True,
    )

    no_data_container = no_data(ft.Icons.BLOCK, "No hay restricciones registradas.")
    cont_tabla = ft.Container(content=tabla_container, expand=True, visible=False)

    def _filtrar():
        q = (txt_buscar.value or "").strip().lower()
        try:
            mes = MESES.index(selector_mes.value) + 1
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
            btn_eliminar = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE, icon_color=TEXT_SECONDARY, icon_size=18,
                tooltip="Eliminar",
                on_click=lambda e, rid=r["id"]: _pedir_confirmacion(rid),
            )

            row = ft.Container(
                content=ft.Row([
                    ft.Container(ft.Text(r["nombre"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=_exp[0], alignment=ft.Alignment(-1, 0)),
                    ft.Container(ft.Text(r["fecha_inicio"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=_exp[1], alignment=ft.Alignment(-1, 0)),
                    ft.Container(ft.Text(r["fecha_fin"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=_exp[2], alignment=ft.Alignment(-1, 0)),
                    ft.Container(ft.Text(r["motivo"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=_exp[3], alignment=ft.Alignment(-1, 0)),
                    ft.Container(btn_eliminar, expand=_exp[4], alignment=ft.Alignment(-1, 0)),
                ]),
                bgcolor=SURFACE,
                height=56,
                padding=ft.Padding(16, 0, 16, 0),
                border_radius=10,
            )

            def _make_hover(c):
                def _on_hover(e):
                    if e.data:
                        c.bgcolor = HOVER_ROW_BG
                        c.shadow = [ft.BoxShadow(blur_radius=8, color="#000000", spread_radius=0, offset=ft.Offset(0, 2))]
                        c.scale = ft.Scale(1.005)
                    else:
                        c.bgcolor = SURFACE
                        c.shadow = []
                        c.scale = ft.Scale(1.0)
                    c.update()
                return _on_hover

            row.on_hover = _make_hover(row)
            body.controls.append(row)
        hay = len(filtrados) > 0
        cont_tabla.visible = hay
        no_data_container.visible = not hay
        page.update()

    def _pedir_confirmacion(rid):
        async def _confirmar():
            await eliminar(rid)
        confirm_dialog(
            page,
            title="Eliminar restricción",
            message="¿Está seguro de eliminar esta restricción?",
            button_label="Eliminar",
            on_confirm=_confirmar,
            destructive=True,
        )

    async def cargar_dropdown(max_intentos=3):
        intentos = 0
        while intentos < max_intentos:
            try:
                async with httpx.AsyncClient() as cliente:
                    token = get_token(page)
                    resp = await cliente.get(f"{URL_BACKEND}/soldados", headers={"Authorization": f"Bearer {token}"})
                    datos = resp.json()
                    if datos:
                        selector_soldado.options = [
                            ft.dropdown.Option(
                                key=str(s["id_soldado"]),
                                text=f"{s['nombre']} {s['apellido']} ({s['cedula']})"
                            )
                            for s in datos
                        ]
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
                token = get_token(page)
                resp = await cliente.get(f"{URL_BACKEND}/restricciones", headers={"Authorization": f"Bearer {token}"})
                resp.raise_for_status()
                _datos = resp.json()
                if not isinstance(_datos, list):
                    raise TypeError(f"Respuesta inesperada: {type(_datos).__name__}")
                _filtrar()
        except Exception:
            toast(page, "Error al cargar restricciones.", "error")
            body.controls.clear()
            cont_tabla.visible = False
            no_data_container.visible = True
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
                token = get_token(page)
                resp = await cliente.post(f"{URL_BACKEND}/restricciones", params={
                    "id_soldado": int(selector_soldado.value),
                    "fecha_inicio": fi.isoformat(),
                    "fecha_fin": ff.isoformat(),
                    "motivo": campo_motivo.value.strip(),
                }, headers={"Authorization": f"Bearer {token}"})
                datos = resp.json()
                if "error" in datos:
                    toast(page, datos["error"], "error")
                else:
                    toast(page, "Restricción creada correctamente.", "success")
                    campo_motivo.value = ""
                    txt_fecha_inicio.value = ""
                    txt_fecha_fin.value = ""
                    await cargar_tabla()
        except Exception:
            toast(page, "Error inesperado. Intente de nuevo.", "error")
        finally:
            page.update()

    async def eliminar(id_restriccion: int):
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.delete(f"{URL_BACKEND}/restricciones/{id_restriccion}", headers={"Authorization": f"Bearer {token}"})
                datos = resp.json()
                if "error" in datos:
                    toast(page, datos["error"], "error")
                else:
                    toast(page, "Restricción eliminada.", "success")
                    await cargar_tabla()
        except Exception:
            toast(page, "Error inesperado. Intente de nuevo.", "error")
        finally:
            page.update()

    form_card = ft.Container(
        content=ft.Column([
            ft.Text("Registrar restricción", size=15, color=TEXT, weight=ft.FontWeight.W_600),
            ft.Row([selector_soldado, txt_fecha_inicio, txt_fecha_fin, campo_motivo], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
            ft.Row([
                txt_buscar,
                selector_mes,
                selector_año,
                ft.Container(expand=True),
                ft.FilledButton(
                    "Añadir",
                    on_click=crear,
                    icon=ft.Icons.ADD,
                    style=ft.ButtonStyle(bgcolor=BTN_BG, color=BTN_TEXT),
                ),
                ft.OutlinedButton(
                    "Refrescar",
                    on_click=lambda e: page.run_task(cargar_tabla),
                    icon=ft.Icons.REFRESH,
                    style=ft.ButtonStyle(
                        color=TEXT_SECONDARY,
                        side=ft.BorderSide(1, DIVIDER),
                    ),
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        ], spacing=12),
        padding=ft.Padding(16, 16, 16, 16),
    )

    panel = ft.Column(
        [
            barra_loading,
            module_header("Restricciones", "Control de fechas no disponibles por soldado"),
            ft.Divider(height=1, color=DIVIDER),
            form_card,
            ft.Container(height=8),
            cont_tabla,
            no_data_container,
        ],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    return {
        "panel": panel,
        "cargar_dropdown": cargar_dropdown,
        "cargar_tabla": cargar_tabla,
    }
