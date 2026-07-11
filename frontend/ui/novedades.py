import asyncio

import flet as ft
import httpx
from config import URL_BACKEND
from skeleton import hover_row, loading_bar, module_header, no_data
from skeleton import table_row as sk_row
from theme import *


def build(page: ft.Page):
    """Construye la tabla de novedades: visualización de eventos y auditoría del sistema."""
    _exp = [1, 1, 1, 2, 2, 1]

    barra_loading = loading_bar()
    body = ft.Column(controls=[], scroll=ft.ScrollMode.ADAPTIVE, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    header = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("D\u00cdA", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[0]),
            ft.Container(ft.Text("TURNO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[1]),
            ft.Container(ft.Text("PUNTO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[2]),
            ft.Container(ft.Text("SOLDADO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[3]),
            ft.Container(ft.Text("NOVEDAD", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[4]),
            ft.Container(ft.Text("ACCI\u00d3N", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[5]),
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

    texto_estado = ft.Text()
    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(str(m)) for m in range(1, 13)],
        value="5",
        width=120,
    )
    selector_año = ft.TextField(label="Año", value="2026", width=100)

    async def cargar_guardias(e=None):
        mes = int(selector_mes.value)
        año = int(selector_año.value)
        body.controls = [sk_row(_exp) for _ in range(6)]
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)

        try:
            async with httpx.AsyncClient() as cliente:
                resp_cal = await cliente.get(f"{URL_BACKEND}/calendario-ver/{año}/{mes}")
                asignaciones = resp_cal.json().get("asignaciones", [])

                resp_nov = await cliente.get(f"{URL_BACKEND}/novedades/{mes}/{año}")
                novedades = {n["id_asignacion"]: n for n in resp_nov.json()}

                body.controls.clear()
                for a in asignaciones:
                    id_asig = a["id_asignacion"]
                    nov = novedades.get(id_asig)
                    descripcion = nov["descripcion"] if nov else "Sin novedad"
                    tiene_nov = nov is not None

                    txt_novedad = ft.Text(descripcion, italic=not tiene_nov, color=ft.Colors.GREY_400 if not tiene_nov else None, size=16)

                    btn_accion = ft.IconButton(
                        icon=ft.Icons.EDIT if tiene_nov else ft.Icons.ADD,
                        tooltip="Editar novedad" if tiene_nov else "Agregar novedad",
                        data={"id_asignacion": id_asig, "descripcion_actual": descripcion, "tiene_nov": tiene_nov},
                        on_click=abrir_dialogo_novedad,
                    )

                    body.controls.append(hover_row(ft.Container(
                        content=ft.Row([
                            ft.Container(ft.Text(str(a["dia"]), size=16, color=TEXT_TABLE), expand=_exp[0]),
                            ft.Container(ft.Text(a["turno"].capitalize(), size=16, color=TEXT_TABLE), expand=_exp[1]),
                            ft.Container(ft.Text(a["punto"], size=16, color=TEXT_TABLE), expand=_exp[2]),
                            ft.Container(ft.Text(f"{a['nombre']} {a['apellido']} ({a['cedula']})", size=16, color=TEXT_TABLE), expand=_exp[3]),
                            ft.Container(txt_novedad, expand=_exp[4]),
                            ft.Container(btn_accion, expand=_exp[5]),
                        ]),
                        bgcolor=TABLE_ROW,
                        height=40,
                        padding=ft.Padding(left=16, top=0, right=16, bottom=0),
                    )))

                texto_estado.value = ""
                hay = len(asignaciones) > 0
                cont_tabla.visible = hay
                no_data_container.visible = not hay
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
            body.controls.clear()
            body.controls.append(
                ft.Container(ft.Text(f"Error: {ex}", italic=True, color=TEXT_SECONDARY, size=14),
                             alignment=ft.Alignment(0, 0), padding=20))
            cont_tabla.visible = False
            no_data_container.visible = True
        finally:
            barra_loading.visible = False
            page.update()

    async def abrir_dialogo_novedad(e):
        datos = e.control.data
        id_asig = datos["id_asignacion"]
        desc_actual = datos["descripcion_actual"]

        campo_novedad = ft.TextField(label="Descripci\u00f3n de la novedad", value="" if desc_actual == "Sin novedad" else desc_actual, multiline=True)

        async def guardar_novedad(e):
            nueva_desc = campo_novedad.value or "Sin novedad"
            try:
                async with httpx.AsyncClient() as cliente:
                    resp = await cliente.post(
                        f"{URL_BACKEND}/novedades",
                        params={"id_asignacion": id_asig, "descripcion": nueva_desc}
                    )
                    resultado = resp.json()
                    if "error" in resultado:
                        texto_estado.value = resultado['error']
                        texto_estado.color = ft.Colors.RED
                    else:
                        texto_estado.value = ""
                    page.pop_dialog()
                    await cargar_guardias()
            except Exception as ex:
                texto_estado.value = f"Error: {ex}"
                texto_estado.color = ft.Colors.RED
            finally:
                page.update()

        dialogo = ft.AlertDialog(
            title=ft.Text("Registrar Novedad"),
            content=ft.Column([campo_novedad], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Guardar", on_click=guardar_novedad),
            ],
        )
        page.show_dialog(dialogo)

    no_data_container = no_data(ft.Icons.CAMPAIGN, "Seleccione un mes y presione 'Cargar Guardias'")
    cont_tabla = ft.Row([
        ft.Container(expand=1),
        ft.Container(content=tabla_container, expand=6, padding=ft.Padding(left=20, right=20, top=10, bottom=10)),
        ft.Container(expand=1),
    ], expand=True, visible=False)

    boton_cargar = ft.FilledButton("Cargar Guardias", on_click=cargar_guardias, icon=ft.Icons.LIST)
    panel = ft.Column([
        barra_loading,
        module_header("Novedades", "Registro de eventos y observaciones por guardia"),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row([selector_mes, selector_año, boton_cargar]),
        ft.Divider(height=1, color=DIVIDER),
        texto_estado,
        ft.Divider(height=1, color=DIVIDER),
        cont_tabla,
        no_data_container,
    ])

    return {"panel": panel}
