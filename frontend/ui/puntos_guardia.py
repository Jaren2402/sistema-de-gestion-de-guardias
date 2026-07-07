import flet as ft
import httpx
from config import URL_BACKEND


def build(page: ft.Page):
    """Construye la interfaz de gestión de puntos de guardia: CRUD de ubicaciones."""
    _exp = [3, 5, 2]

    body = ft.Column(controls=[], scroll=ft.ScrollMode.ADAPTIVE, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    header = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("NOMBRE", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[0]),
            ft.Container(ft.Text("DESCRIPCI\u00d3N", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[1]),
            ft.Container(ft.Text("ACCIONES", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[2]),
        ]),
        bgcolor="#25292E",
        padding=ft.Padding(left=16, top=12, right=16, bottom=12),
    )

    tabla_container = ft.Container(
        content=ft.Column([header, body]),
        expand=True,
        bgcolor="#121416",
        border_radius=10,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    texto_estado = ft.Text()
    campo_nombre = ft.TextField(label="Nombre del punto", width=300)
    campo_descripcion = ft.TextField(label="Descripci\u00f3n (opcional)", width=400)
    id_edicion = ft.TextField(label="ID", visible=False, disabled=True, width=100)

    async def cargar_tabla():
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.get(f"{URL_BACKEND}/puntos")
                datos = resp.json()
                body.controls.clear()
                for p in datos:
                    body.controls.append(ft.Container(
                        content=ft.Row([
                            ft.Container(ft.Text(p["nombre"], size=16, color="#DEDEDE"), expand=_exp[0]),
                            ft.Container(ft.Text(p.get("descripcion", ""), size=16, color="#DEDEDE"), expand=_exp[1]),
                            ft.Container(ft.Row([
                                ft.IconButton(icon=ft.Icons.EDIT, tooltip="Editar", data=p, on_click=seleccionar_para_editar),
                                ft.IconButton(icon=ft.Icons.DELETE, tooltip="Eliminar", data=p["id"], on_click=eliminar_punto),
                            ]), expand=_exp[2]),
                        ]),
                        bgcolor="#171C22",
                        height=40,
                        padding=ft.Padding(left=16, top=0, right=16, bottom=0),
                    ))
                texto_estado.value = ""
        except Exception as ex:
            texto_estado.value = f"Error al cargar: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    def limpiar_formulario():
        campo_nombre.value = ""
        campo_descripcion.value = ""
        id_edicion.value = ""
        id_edicion.visible = False
        page.update()

    async def seleccionar_para_editar(e):
        p = e.control.data
        campo_nombre.value = p["nombre"]
        campo_descripcion.value = p.get("descripcion", "")
        id_edicion.value = str(p["id"])
        id_edicion.visible = True
        page.update()

    async def crear_o_actualizar(e):
        if not campo_nombre.value:
            texto_estado.value = "El nombre es obligatorio."
            texto_estado.color = ft.Colors.YELLOW
            page.update()
            return

        datos = {
            "nombre": campo_nombre.value,
            "descripcion": campo_descripcion.value or "",
        }

        try:
            async with httpx.AsyncClient() as cliente:
                if id_edicion.value:
                    resp = await cliente.put(
                        f"{URL_BACKEND}/puntos/editar/{id_edicion.value}",
                        params=datos,
                    )
                else:
                    resp = await cliente.post(
                        f"{URL_BACKEND}/puntos/crear",
                        params=datos,
                    )
                resultado = resp.json()
                if "error" in resultado:
                    texto_estado.value = resultado['error']
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = resultado['mensaje']
                    texto_estado.color = ft.Colors.GREEN
                    limpiar_formulario()
                    await cargar_tabla()
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    async def eliminar_punto(e):
        id_punto = e.control.data
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.delete(f"{URL_BACKEND}/puntos/eliminar/{id_punto}")
                resultado = resp.json()
                if "error" in resultado:
                    texto_estado.value = resultado['error']
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = resultado['mensaje']
                    texto_estado.color = ft.Colors.GREEN
                    await cargar_tabla()
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    boton_guardar = ft.Button("Guardar", on_click=crear_o_actualizar, icon=ft.Icons.SAVE)
    boton_cancelar = ft.Button("Cancelar", on_click=lambda e: limpiar_formulario(), icon=ft.Icons.CANCEL)

    panel = ft.Column([
        ft.Text("Crear / Editar Punto de Guardia", weight=ft.FontWeight.BOLD, size=16),
        ft.Row([campo_nombre, campo_descripcion, id_edicion]),
        ft.Row([boton_guardar, boton_cancelar]),
        ft.Divider(),
        texto_estado,
        ft.Divider(),
        ft.Row([
            ft.Container(expand=1),
            ft.Container(content=tabla_container, expand=6, padding=ft.Padding(left=20, right=20, top=10, bottom=10)),
            ft.Container(expand=1),
        ], expand=True),
    ])

    page.run_task(cargar_tabla)

    return {"panel": panel}
