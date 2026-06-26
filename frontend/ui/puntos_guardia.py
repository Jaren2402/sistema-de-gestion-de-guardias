import flet as ft
import httpx
from config import URL_BACKEND


def build(page: ft.Page):
    texto_estado = ft.Text()
    campo_nombre = ft.TextField(label="Nombre del punto", width=300)
    campo_descripcion = ft.TextField(label="Descripción (opcional)", width=400)
    id_edicion = ft.TextField(label="ID", visible=False, disabled=True, width=100)

    tabla_puntos = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Nombre")),
            ft.DataColumn(ft.Text("Descripción")),
            ft.DataColumn(ft.Text("Acciones")),
        ],
        rows=[],
        border=ft.Border.all(1, ft.Colors.GREY_700),
    )

    async def cargar_tabla():
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.get(f"{URL_BACKEND}/puntos")
                datos = resp.json()
                tabla_puntos.rows.clear()
                for p in datos:
                    tabla_puntos.rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(p["nombre"])),
                        ft.DataCell(ft.Text(p.get("descripcion", ""))),
                        ft.DataCell(ft.Row([
                            ft.IconButton(icon=ft.Icons.EDIT, tooltip="Editar",
                                          data=p, on_click=seleccionar_para_editar),
                            ft.IconButton(icon=ft.Icons.DELETE, tooltip="Eliminar",
                                          data=p["id"], on_click=eliminar_punto),
                        ])),
                    ]))
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
            texto_estado.value = "⚠️ El nombre es obligatorio."
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
                    texto_estado.value = f"❌ {resultado['error']}"
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = f"✅ {resultado['mensaje']}"
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
                    texto_estado.value = f"❌ {resultado['error']}"
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = f"✅ {resultado['mensaje']}"
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
        ft.Text("Puntos de guardia registrados", weight=ft.FontWeight.BOLD),
        tabla_puntos,
    ])

    page.run_task(cargar_tabla)

    return {"panel": panel}