import asyncio

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
    _id_edicion = None
    _exp = [3, 5, 2]

    barra_loading = loading_bar()

    campo_nombre = ft.TextField(label="Nombre del punto", width=300, **_field_style())
    campo_descripcion = ft.TextField(label="Descripción (opcional)", width=400, **_field_style())

    txt_buscar = ft.TextField(
        label="Buscar punto",
        hint_text="Nombre o descripción",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        on_change=lambda e: _filtrar(),
        **_field_style(),
    )

    body = ft.Column(
        controls=[], scroll=ft.ScrollMode.ADAPTIVE, expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=4,
    )

    header_row = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("NOMBRE", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_exp[0], alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("DESCRIPCIÓN", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_exp[1], alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("ACCIONES", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_exp[2], alignment=ft.Alignment(-1, 0)),
        ]),
        bgcolor=BTN_BG,
        border_radius=ft.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0),
        padding=ft.Padding(16, 10, 16, 10),
    )

    tabla_container = ft.Container(
        content=ft.Column([header_row, body]),
        expand=True,
    )

    no_data_container = no_data(ft.Icons.LOCATION_ON, "No hay puntos de guardia. Cree uno desde el formulario.")
    cont_tabla = ft.Container(content=tabla_container, expand=True, visible=False)

    def _filtrar():
        q = (txt_buscar.value or "").strip().lower()
        filtrados = [p for p in _datos
                     if not q or q in p["nombre"].lower()
                     or q in p.get("descripcion", "").lower()]
        body.controls.clear()
        for p in filtrados:
            btn_editar = ft.IconButton(
                icon=ft.Icons.EDIT_OUTLINED, icon_color=TEXT_SECONDARY, icon_size=18,
                tooltip="Editar", data=p, on_click=seleccionar_para_editar,
            )
            btn_eliminar = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE, icon_color=TEXT_SECONDARY, icon_size=18,
                tooltip="Eliminar", data=p, on_click=eliminar_punto,
            )

            row = ft.Container(
                content=ft.Row([
                    ft.Container(ft.Text(p["nombre"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=_exp[0], alignment=ft.Alignment(-1, 0)),
                    ft.Container(ft.Text(p.get("descripcion", ""), size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=_exp[1], alignment=ft.Alignment(-1, 0)),
                    ft.Container(ft.Row([btn_editar, btn_eliminar], spacing=0), expand=_exp[2], alignment=ft.Alignment(-1, 0)),
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

    async def cargar_tabla():
        nonlocal _datos
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.get(f"{URL_BACKEND}/puntos", headers={"Authorization": f"Bearer {token}"})
                _datos = resp.json()
                _filtrar()
        except Exception:
            toast(page, "Error al cargar puntos.", "error")
            body.controls.clear()
            cont_tabla.visible = False
            no_data_container.visible = True
        finally:
            barra_loading.visible = False
            page.update()

    def limpiar_formulario():
        nonlocal _id_edicion
        campo_nombre.value = ""
        campo_descripcion.value = ""
        _id_edicion = None
        titulo_form.value = "Registrar punto"
        page.update()

    async def seleccionar_para_editar(e):
        nonlocal _id_edicion
        p = e.control.data
        _id_edicion = p["id"]
        campo_nombre.value = p["nombre"]
        campo_descripcion.value = p.get("descripcion", "")
        titulo_form.value = f"Editando: {p['nombre']}"
        page.update()

    async def crear_o_actualizar(e):
        nonlocal _id_edicion
        if not campo_nombre.value:
            toast(page, "El nombre es obligatorio.", "warning")
            return

        datos = {
            "nombre": campo_nombre.value,
            "descripcion": campo_descripcion.value or "",
        }

        es_edicion = _id_edicion is not None

        async def _guardar():
            try:
                async with httpx.AsyncClient() as cliente:
                    token = get_token(page)
                    if es_edicion:
                        resp = await cliente.put(
                            f"{URL_BACKEND}/puntos/editar/{_id_edicion}",
                            params=datos,
                            headers={"Authorization": f"Bearer {token}"},
                        )
                    else:
                        resp = await cliente.post(
                            f"{URL_BACKEND}/puntos/crear",
                            params=datos,
                            headers={"Authorization": f"Bearer {token}"},
                        )
                    resultado = resp.json()
                    if "error" in resultado:
                        toast(page, resultado["error"], "error")
                    else:
                        toast(page, resultado.get("mensaje", "Guardado correctamente"), "success")
                        limpiar_formulario()
                        await cargar_tabla()
            except Exception:
                toast(page, "Error inesperado. Intente de nuevo.", "error")

        if es_edicion:
            confirm_dialog(
                page,
                title="Editar punto",
                message=f"¿Guardar cambios en {campo_nombre.value}?",
                button_label="Guardar",
                on_confirm=_guardar,
            )
        else:
            await _guardar()

    async def eliminar_punto(e):
        p = e.control.data

        async def _confirmar():
            try:
                async with httpx.AsyncClient() as cliente:
                    token = get_token(page)
                    resp = await cliente.delete(
                        f"{URL_BACKEND}/puntos/eliminar/{p['id']}",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    resultado = resp.json()
                    if "error" in resultado:
                        toast(page, resultado["error"], "error")
                    else:
                        toast(page, resultado.get("mensaje", "Punto eliminado"), "success")
                        await cargar_tabla()
            except Exception:
                toast(page, "Error inesperado. Intente de nuevo.", "error")

        confirm_dialog(
            page,
            title="Eliminar punto",
            message=f"¿Eliminar el punto {p['nombre']}? No se puede deshacer.",
            button_label="Eliminar",
            on_confirm=_confirmar,
            destructive=True,
        )

    titulo_form = ft.Text("Registrar punto", size=15, color=TEXT, weight=ft.FontWeight.W_600)

    form_card = ft.Container(
        content=ft.Column([
            titulo_form,
            ft.Row([campo_nombre, campo_descripcion], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
            ft.Row([
                txt_buscar,
                ft.FilledButton(
                    "Guardar",
                    on_click=crear_o_actualizar,
                    icon=ft.Icons.SAVE,
                    style=ft.ButtonStyle(bgcolor=BTN_BG, color=BTN_TEXT),
                ),
                ft.OutlinedButton(
                    "Cancelar",
                    on_click=lambda e: limpiar_formulario(),
                    icon=ft.Icons.CANCEL,
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
            module_header("Puntos de Guardia", "Definición de ubicaciones y puntos de servicio"),
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
        "cargar_tabla": cargar_tabla,
    }
