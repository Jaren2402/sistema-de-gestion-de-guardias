import asyncio

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import hover_row, loading_bar, module_header, no_data
from skeleton import table_row as sk_row
from theme import *


def build(page: ft.Page):
    """Construye el formulario de creación y edición de soldados (CRUD completo)."""
    _datos = []
    texto_estado = ft.Text()
    campo_cedula = ft.TextField(label="C\u00e9dula", width=150)
    campo_nombre = ft.TextField(label="Nombre", width=200)
    campo_apellido = ft.TextField(label="Apellido", width=200)
    campo_rango = ft.Dropdown(
        label="Rango",
        options=[ft.dropdown.Option(r) for r in [
            "cabo segundo", "cabo primero", "sargento segundo",
            "sargento primero", "sargento mayor", "teniente",
            "primer teniente", "capit\u00e1n"
        ]],
        width=180,
    )
    campo_unidad = ft.TextField(label="Unidad", width=200)
    id_edicion = ft.TextField(label="ID (solo lectura)", visible=False, disabled=True, width=100)

    _exp = [1, 2, 2, 1, 1, 1]

    barra_loading = loading_bar()
    body = ft.Column(controls=[sk_row(_exp) for _ in range(6)], scroll=ft.ScrollMode.ADAPTIVE, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    header = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("C\u00c9DULA", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[0]),
            ft.Container(ft.Text("NOMBRE", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[1]),
            ft.Container(ft.Text("APELLIDO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[2]),
            ft.Container(ft.Text("RANGO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[3]),
            ft.Container(ft.Text("UNIDAD", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[4]),
            ft.Container(ft.Text("ACCIONES", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[5]),
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

    no_data_container = no_data(ft.Icons.MANAGE_ACCOUNTS, "No hay soldados. Cree uno desde el formulario.")
    cont_tabla = ft.Row([
        ft.Container(expand=1),
        ft.Container(content=tabla_container, expand=6, padding=ft.Padding(left=20, right=20, top=10, bottom=10)),
        ft.Container(expand=1),
    ], expand=True, visible=False)

    txt_buscar = ft.TextField(
        label="Buscar soldado",
        hint_text="Nombre, c\u00e9dula o rango",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        on_change=lambda e: _filtrar(),
    )

    def _filtrar():
        q = txt_buscar.value.strip().lower()
        filtrados = [s for s in _datos
                     if not q or q in s["cedula"].lower()
                     or q in s["nombre"].lower()
                     or q in s["apellido"].lower()
                     or q in s["rango"].lower()]
        body.controls.clear()
        for s in filtrados:
            body.controls.append(hover_row(ft.Container(
                content=ft.Row([
                    ft.Container(ft.Text(s["cedula"], size=16, color=TEXT_TABLE), expand=_exp[0]),
                    ft.Container(ft.Text(s["nombre"], size=16, color=TEXT_TABLE), expand=_exp[1]),
                    ft.Container(ft.Text(s["apellido"], size=16, color=TEXT_TABLE), expand=_exp[2]),
                    ft.Container(ft.Text(s["rango"], size=16, color=TEXT_TABLE), expand=_exp[3]),
                    ft.Container(ft.Text(s["unidad"], size=16, color=TEXT_TABLE), expand=_exp[4]),
                    ft.Container(ft.Row([
                        ft.IconButton(icon=ft.Icons.EDIT, tooltip="Editar", data=s, on_click=seleccionar_para_editar),
                        ft.IconButton(icon=ft.Icons.DELETE, tooltip="Eliminar", data=s["id_soldado"], on_click=eliminar_soldado),
                    ]), expand=_exp[5]),
                ]),
                bgcolor=TABLE_ROW,
                height=40,
                padding=ft.Padding(left=16, top=0, right=16, bottom=0),
            )))
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
                resp = await cliente.get(f"{URL_BACKEND}/soldados", params={"token": token})
                _datos = resp.json()
                _filtrar()
                texto_estado.value = ""
        except Exception as ex:
            texto_estado.value = f"Error al cargar: {ex}"
            texto_estado.color = ft.Colors.RED
            body.controls.clear()
            body.controls.append(
                ft.Container(ft.Text(f"Error: {ex}", italic=True, color=TEXT_SECONDARY, size=14),
                             alignment=ft.Alignment(0, 0), padding=20))
        finally:
            barra_loading.visible = False
            page.update()

    def limpiar_formulario():
        campo_cedula.value = ""
        campo_nombre.value = ""
        campo_apellido.value = ""
        campo_rango.value = None
        campo_unidad.value = ""
        id_edicion.value = ""
        id_edicion.visible = False
        page.update()

    async def seleccionar_para_editar(e):
        s = e.control.data
        campo_cedula.value = s["cedula"]
        campo_nombre.value = s["nombre"]
        campo_apellido.value = s["apellido"]
        campo_rango.value = s["rango"]
        campo_unidad.value = s["unidad"]
        id_edicion.value = str(s["id_soldado"])
        id_edicion.visible = True
        page.update()

    async def crear_o_actualizar(e):
        if not campo_cedula.value or not campo_nombre.value or not campo_apellido.value or not campo_rango.value:
            texto_estado.value = "Todos los campos son obligatorios."
            texto_estado.color = ft.Colors.YELLOW
            page.update()
            return

        datos = {
            "cedula": campo_cedula.value,
            "nombre": campo_nombre.value,
            "apellido": campo_apellido.value,
            "rango": campo_rango.value,
            "unidad": campo_unidad.value or "",
        }

        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                if id_edicion.value:
                    resp = await cliente.put(
                        f"{URL_BACKEND}/soldados/editar/{id_edicion.value}",
                        params={**datos, "token": token},
                    )
                else:
                    resp = await cliente.post(
                        f"{URL_BACKEND}/soldados/crear",
                        params={**datos, "token": token},
                    )
                resultado = resp.json()
                if "error" in resultado:
                    texto_estado.value = f"{resultado['error']}"
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = ""
                    limpiar_formulario()
                    await cargar_tabla()
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    async def eliminar_soldado(e):
        id_soldado = e.control.data
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.delete(f"{URL_BACKEND}/soldados/eliminar/{id_soldado}", params={"token": token})
                resultado = resp.json()
                if "error" in resultado:
                    texto_estado.value = f"{resultado['error']}"
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = ""
                    await cargar_tabla()
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    boton_guardar = ft.FilledButton("Guardar", on_click=crear_o_actualizar, icon=ft.Icons.SAVE)
    boton_cancelar = ft.FilledButton("Cancelar", on_click=lambda e: limpiar_formulario(), icon=ft.Icons.CANCEL)

    panel = ft.Column([
        barra_loading,
        module_header("Gestión", "Alta, baja y edición de datos de soldados"),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row([campo_cedula, campo_nombre, campo_apellido]),
        ft.Row([campo_rango, campo_unidad, id_edicion]),
        ft.Row([boton_guardar, boton_cancelar]),
        ft.Divider(height=1, color=DIVIDER),
        texto_estado,
        ft.Divider(height=1, color=DIVIDER),
        txt_buscar,
        cont_tabla,
        no_data_container,
    ])

    return {"panel": panel,
            "cargar_tabla": cargar_tabla,}
