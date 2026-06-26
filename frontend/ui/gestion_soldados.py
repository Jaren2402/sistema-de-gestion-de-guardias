import flet as ft
import httpx
from config import URL_BACKEND


def build(page: ft.Page):
    # --- Estado y controles ---
    texto_estado = ft.Text()
    campo_cedula = ft.TextField(label="Cédula", width=150)
    campo_nombre = ft.TextField(label="Nombre", width=200)
    campo_apellido = ft.TextField(label="Apellido", width=200)
    campo_rango = ft.Dropdown(
        label="Rango",
        options=[ft.dropdown.Option(r) for r in [
            "cabo segundo", "cabo primero", "sargento segundo",
            "sargento primero", "sargento mayor", "teniente",
            "primer teniente", "capitán"
        ]],
        width=180,
    )
    campo_unidad = ft.TextField(label="Unidad", width=200)
    id_edicion = ft.TextField(label="ID (solo lectura)", visible=False, disabled=True, width=100)

    tabla_soldados = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Cédula")),
            ft.DataColumn(ft.Text("Nombre")),
            ft.DataColumn(ft.Text("Apellido")),
            ft.DataColumn(ft.Text("Rango")),
            ft.DataColumn(ft.Text("Unidad")),
            ft.DataColumn(ft.Text("Acciones")),
        ],
        rows=[],
        border=ft.Border.all(1, ft.Colors.GREY_700),
    )

    # --- Funciones asíncronas ---
    async def cargar_tabla():
        """Carga la tabla con todos los soldados."""
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.get(f"{URL_BACKEND}/soldados")
                datos = resp.json()
                tabla_soldados.rows.clear()
                for s in datos:
                    tabla_soldados.rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(s["cedula"])),
                        ft.DataCell(ft.Text(s["nombre"])),
                        ft.DataCell(ft.Text(s["apellido"])),
                        ft.DataCell(ft.Text(s["rango"])),
                        ft.DataCell(ft.Text(s["unidad"])),
                        ft.DataCell(ft.Row([
                            ft.IconButton(icon=ft.Icons.EDIT, tooltip="Editar",
                                          data=s, on_click=seleccionar_para_editar),
                            ft.IconButton(icon=ft.Icons.DELETE, tooltip="Eliminar",
                                          data=s["id_soldado"], on_click=eliminar_soldado),
                        ])),
                    ]))
                texto_estado.value = ""
        except Exception as ex:
            texto_estado.value = f"Error al cargar: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
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
        """Llena el formulario con los datos del soldado seleccionado."""
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
        """Crea o actualiza un soldado según si hay un ID de edición."""
        if not campo_cedula.value or not campo_nombre.value or not campo_apellido.value or not campo_rango.value:
            texto_estado.value = "⚠️ Todos los campos son obligatorios."
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
                if id_edicion.value:
                    # Actualizar
                    resp = await cliente.put(
                        f"{URL_BACKEND}/soldados/editar/{id_edicion.value}",
                        params=datos,
                    )
                else:
                    # Crear
                    resp = await cliente.post(
                        f"{URL_BACKEND}/soldados/crear",
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

    async def eliminar_soldado(e):
        """Elimina un soldado por su ID."""
        id_soldado = e.control.data
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.delete(f"{URL_BACKEND}/soldados/eliminar/{id_soldado}")
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

    # --- Botones ---
    boton_guardar = ft.Button("Guardar", on_click=crear_o_actualizar, icon=ft.Icons.SAVE)
    boton_cancelar = ft.Button("Cancelar", on_click=lambda e: limpiar_formulario(), icon=ft.Icons.CANCEL)

    # --- Panel ---
    panel = ft.Column([
        ft.Text("Crear / Editar Soldado", weight=ft.FontWeight.BOLD, size=16),
        ft.Row([campo_cedula, campo_nombre, campo_apellido]),
        ft.Row([campo_rango, campo_unidad, id_edicion]),
        ft.Row([boton_guardar, boton_cancelar]),
        ft.Divider(),
        texto_estado,
        ft.Divider(),
        ft.Text("Soldados registrados", weight=ft.FontWeight.BOLD),
        tabla_soldados,
    ])

    # Cargar datos al iniciar el módulo
    page.run_task(cargar_tabla)

    return {"panel": panel,
            "cargar_tabla": cargar_tabla,}