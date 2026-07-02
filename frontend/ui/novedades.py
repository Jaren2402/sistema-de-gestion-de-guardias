import flet as ft
import httpx
from config import URL_BACKEND


def build(page: ft.Page):
    texto_estado = ft.Text()
    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(str(m)) for m in range(1, 13)],
        value="5",
        width=120,
    )
    selector_año = ft.TextField(label="Año", value="2026", width=100)

    tabla_guardias = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("DÍA")),
            ft.DataColumn(ft.Text("TURNO")),
            ft.DataColumn(ft.Text("PUNTO")),
            ft.DataColumn(ft.Text("SOLDADO")),
            ft.DataColumn(ft.Text("NOVEDAD")),
            ft.DataColumn(ft.Text("ACCIÓN")),
        ],
        rows=[],
        border=ft.Border.all(1, ft.Colors.GREY_800),
        border_radius=10,
        bgcolor="#121416",
        heading_row_color="#25292E",
        heading_row_height=48,
        data_row_min_height=36,
        data_text_style=ft.TextStyle(size=16, color="#DEDEDE"),
        column_spacing=30,
    )

    async def cargar_guardias(e=None):
        mes = int(selector_mes.value)
        año = int(selector_año.value)
        tabla_guardias.rows.clear()
        texto_estado.value = "Cargando guardias..."
        page.update()

        try:
            async with httpx.AsyncClient() as cliente:
                # 1. Obtener asignaciones del mes
                resp_cal = await cliente.get(f"{URL_BACKEND}/calendario-ver/{año}/{mes}")
                asignaciones = resp_cal.json().get("asignaciones", [])

                # 2. Obtener novedades del mes
                resp_nov = await cliente.get(f"{URL_BACKEND}/novedades/{mes}/{año}")
                novedades = {n["id_asignacion"]: n for n in resp_nov.json()}

                for a in asignaciones:
                    id_asig = a["id_asignacion"]
                    nov = novedades.get(id_asig)
                    descripcion = nov["descripcion"] if nov else "Sin novedad"
                    tiene_nov = nov is not None

                    # Texto de la novedad
                    txt_novedad = ft.Text(descripcion, italic=not tiene_nov, color=ft.Colors.GREY_400 if not tiene_nov else None)

                    # Botón para agregar/editar
                    btn_accion = ft.IconButton(
                        icon=ft.Icons.EDIT if tiene_nov else ft.Icons.ADD,
                        tooltip="Editar novedad" if tiene_nov else "Agregar novedad",
                        data={"id_asignacion": id_asig, "descripcion_actual": descripcion, "tiene_nov": tiene_nov},
                        on_click=abrir_dialogo_novedad,
                    )

                    tabla_guardias.rows.append(ft.DataRow(
                        color="#171C22",
                        cells=[
                            ft.DataCell(ft.Text(str(a["dia"]))),
                            ft.DataCell(ft.Text(a["turno"].capitalize())),
                            ft.DataCell(ft.Text(a["punto"])),
                            ft.DataCell(ft.Text(f"{a['nombre']} {a['apellido']} ({a['cedula']})")),
                            ft.DataCell(txt_novedad),
                            ft.DataCell(btn_accion),
                        ]
                    ))
                texto_estado.value = f"Se encontraron {len(asignaciones)} guardias."
                texto_estado.color = ft.Colors.GREEN
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    async def abrir_dialogo_novedad(e):
        datos = e.control.data
        id_asig = datos["id_asignacion"]
        desc_actual = datos["descripcion_actual"]

        # Campo de texto del diálogo
        campo_novedad = ft.TextField(label="Descripción de la novedad", value="" if desc_actual == "Sin novedad" else desc_actual, multiline=True)

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
                        texto_estado.value = f"❌ {resultado['error']}"
                        texto_estado.color = ft.Colors.RED
                    else:
                        texto_estado.value = f"✅ {resultado['mensaje']}"
                        texto_estado.color = ft.Colors.GREEN
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

    # --- Construcción de la pestaña ---
    boton_cargar = ft.Button("Cargar Guardias", on_click=cargar_guardias, icon=ft.Icons.LIST)
    panel = ft.Column([
        ft.Row([selector_mes, selector_año, boton_cargar]),
        ft.Divider(),
        texto_estado,
        ft.Divider(),
        tabla_guardias,
    ])

    return {"panel": panel}