import asyncio

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import confirm_dialog, loading_bar, module_header, no_data, toast
from theme import *

_CARD_SHADOW = [ft.BoxShadow(blur_radius=8, color="#000000", spread_radius=0, offset=ft.Offset(0, 3))]
_EXP = [1, 2, 2, 1, 1, 1]


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
    barra_loading = loading_bar()

    campo_cedula = ft.TextField(label="Cédula", expand=True, **_field_style())
    campo_nombre = ft.TextField(label="Nombre", expand=True, **_field_style())
    campo_apellido = ft.TextField(label="Apellido", expand=True, **_field_style())
    campo_rango = ft.Dropdown(
        label="Rango", expand=True,
        options=[ft.dropdown.Option(r) for r in [
            "cabo segundo", "cabo primero", "sargento segundo",
            "sargento primero", "sargento mayor", "teniente",
            "primer teniente", "capitán",
        ]],
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY,
    )
    campo_unidad = ft.TextField(label="Unidad", expand=True, **_field_style())

    txt_buscar = ft.TextField(
        label="Buscar soldado",
        hint_text="Nombre, cédula o rango",
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
            ft.Container(ft.Text("CÉDULA", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_EXP[0], alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("NOMBRE", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_EXP[1], alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("APELLIDO", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_EXP[2], alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("RANGO", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_EXP[3], alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("UNIDAD", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_EXP[4], alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("ACCIONES", size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_EXP[5], alignment=ft.Alignment(-1, 0)),
        ]),
        bgcolor=BTN_BG,
        border_radius=ft.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0),
        padding=ft.Padding(16, 10, 16, 10),
    )

    tabla_container = ft.Container(
        content=ft.Column([header_row, body]),
        expand=True,
    )

    no_data_container = no_data(ft.Icons.MANAGE_ACCOUNTS, "No hay soldados. Cree uno desde el formulario.")
    cont_tabla = ft.Container(content=tabla_container, expand=True, visible=False)

    def _filtrar():
        q = (txt_buscar.value or "").strip().lower()
        filtrados = [s for s in _datos
                     if not q or q in s["cedula"].lower()
                     or q in s["nombre"].lower()
                     or q in s["apellido"].lower()
                     or q in s["rango"].lower()]
        body.controls.clear()
        for s in filtrados:
            btn_editar = ft.IconButton(
                icon=ft.Icons.EDIT_OUTLINED, icon_color=TEXT_SECONDARY, icon_size=18,
                tooltip="Editar", data=s, on_click=seleccionar_para_editar,
            )
            btn_eliminar = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE, icon_color=TEXT_SECONDARY, icon_size=18,
                tooltip="Eliminar", data=s, on_click=eliminar_soldado,
            )

            row = ft.Container(
                content=ft.Row([
                    ft.Container(ft.Text(s["cedula"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=_EXP[0], alignment=ft.Alignment(-1, 0)),
                    ft.Container(ft.Text(s["nombre"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=_EXP[1], alignment=ft.Alignment(-1, 0)),
                    ft.Container(ft.Text(s["apellido"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=_EXP[2], alignment=ft.Alignment(-1, 0)),
                    ft.Container(ft.Text(s["rango"].capitalize(), size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=_EXP[3], alignment=ft.Alignment(-1, 0)),
                    ft.Container(ft.Text(s["unidad"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=_EXP[4], alignment=ft.Alignment(-1, 0)),
                    ft.Container(ft.Row([btn_editar, btn_eliminar], spacing=0), expand=_EXP[5], alignment=ft.Alignment(-1, 0)),
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
                resp = await cliente.get(
                    f"{URL_BACKEND}/soldados",
                    headers={"Authorization": f"Bearer {token}"},
                )
                _datos = resp.json()
                _filtrar()
        except Exception:
            toast(page, "Error al cargar soldados.", "error")
            body.controls.clear()
            cont_tabla.visible = False
            no_data_container.visible = True
        finally:
            barra_loading.visible = False
            page.update()

    def limpiar_formulario():
        nonlocal _id_edicion
        campo_cedula.value = ""
        campo_nombre.value = ""
        campo_apellido.value = ""
        campo_rango.value = None
        campo_unidad.value = ""
        _id_edicion = None
        titulo_form.value = "Registrar soldado"
        page.update()

    async def seleccionar_para_editar(e):
        nonlocal _id_edicion
        s = e.control.data
        _id_edicion = s["id_soldado"]
        campo_cedula.value = s["cedula"]
        campo_nombre.value = s["nombre"]
        campo_apellido.value = s["apellido"]
        campo_rango.value = s["rango"]
        campo_unidad.value = s["unidad"]
        titulo_form.value = f"Editando: {s['nombre']} {s['apellido']}"
        page.update()

    async def crear_o_actualizar(e):
        nonlocal _id_edicion
        if not campo_cedula.value or not campo_nombre.value or not campo_apellido.value or not campo_rango.value:
            toast(page, "Todos los campos son obligatorios.", "warning")
            return

        datos = {
            "cedula": campo_cedula.value,
            "nombre": campo_nombre.value,
            "apellido": campo_apellido.value,
            "rango": campo_rango.value,
            "unidad": campo_unidad.value or "",
        }

        es_edicion = _id_edicion is not None

        async def _guardar():
            try:
                async with httpx.AsyncClient() as cliente:
                    token = get_token(page)
                    if es_edicion:
                        resp = await cliente.put(
                            f"{URL_BACKEND}/soldados/editar/{_id_edicion}",
                            params=datos,
                            headers={"Authorization": f"Bearer {token}"},
                        )
                    else:
                        resp = await cliente.post(
                            f"{URL_BACKEND}/soldados/crear",
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
                title="Editar soldado",
                message=f"¿Guardar cambios en {campo_nombre.value} {campo_apellido.value}?",
                button_label="Guardar",
                on_confirm=_guardar,
            )
        else:
            await _guardar()

    async def eliminar_soldado(e):
        s = e.control.data

        async def _confirmar():
            try:
                async with httpx.AsyncClient() as cliente:
                    token = get_token(page)
                    resp = await cliente.delete(
                        f"{URL_BACKEND}/soldados/eliminar/{s['id_soldado']}",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    resultado = resp.json()
                    if "error" in resultado:
                        toast(page, resultado["error"], "error")
                    else:
                        toast(page, resultado.get("mensaje", "Soldado eliminado"), "success")
                        await cargar_tabla()
            except Exception:
                toast(page, "Error inesperado. Intente de nuevo.", "error")

        confirm_dialog(
            page,
            title="Eliminar soldado",
            message=f"¿Eliminar a {s['nombre']} {s['apellido']} ({s['cedula']})? No se puede deshacer.",
            button_label="Eliminar",
            on_confirm=_confirmar,
            destructive=True,
        )

    titulo_form = ft.Text("Registrar soldado", size=15, color=TEXT, weight=ft.FontWeight.W_600)

    form_card = ft.Container(
        content=ft.Column([
            titulo_form,
            ft.Row([campo_cedula, campo_nombre, campo_apellido, campo_rango, campo_unidad], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
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
            module_header("Gestión", "Alta, baja y edición de datos de soldados"),
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
