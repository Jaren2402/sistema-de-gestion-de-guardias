import flet as ft
import httpx
from config import URL_BACKEND


def build(page: ft.Page, on_soldados_actualizados=None):
    # --- Controles de la interfaz ---
    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Cédula")),
            ft.DataColumn(ft.Text("Nombre")),
            ft.DataColumn(ft.Text("Apellido")),
            ft.DataColumn(ft.Text("Rango")),
            ft.DataColumn(ft.Text("Unidad")),
        ],
        rows=[],
        border=ft.Border.all(1, ft.Colors.GREY_700),
    )
    barra_progreso = ft.ProgressBar(visible=False)
    texto_estado = ft.Text()
    selector_archivo = ft.FilePicker()

    # --- Funciones asíncronas ---
    async def cargar():
        """Obtiene la lista de soldados del backend y llena la tabla."""
        try:
            async with httpx.AsyncClient() as cliente:
                respuesta = await cliente.get(f"{URL_BACKEND}/soldados")
                datos = respuesta.json()
                tabla.rows.clear()
                for s in datos:
                    tabla.rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(s["cedula"])),
                        ft.DataCell(ft.Text(s["nombre"])),
                        ft.DataCell(ft.Text(s["apellido"])),
                        ft.DataCell(ft.Text(s["rango"])),
                        ft.DataCell(ft.Text(s["unidad"])),
                    ]))
                texto_estado.value = f"Mostrando {len(datos)} soldados."
                texto_estado.color = ft.Colors.GREEN
        except Exception as ex:
            texto_estado.value = f"Error al cargar: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            barra_progreso.visible = False
            page.update()

    async def importar(e):
        """Abre el selector de archivos y tras importar, refresca la tabla."""
        resultado = await selector_archivo.pick_files(allowed_extensions=["xlsx"])
        if not resultado:
            return
        archivo = resultado[0]
        texto_estado.value = f"Enviando {archivo.name}..."
        texto_estado.color = ft.Colors.YELLOW
        barra_progreso.visible = True
        page.update()
        try:
            with open(archivo.path, "rb") as f:
                contenido = f.read()
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.post(
                    f"{URL_BACKEND}/importar_soldados",
                    files={"archivo": (archivo.name, contenido)}
                )
                datos = resp.json()
                texto_estado.value = datos.get("mensaje", str(datos))
                texto_estado.color = ft.Colors.GREEN
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            barra_progreso.visible = False
            page.update()
            await cargar()
            # Notificar al módulo de restricciones que hay nuevos soldados
            if on_soldados_actualizados:
                await on_soldados_actualizados()

    # --- Botones ---
    boton_importar = ft.Button(
        "📂 Importar soldados desde Excel",
        on_click=importar,
        icon=ft.Icons.UPLOAD_FILE,
    )
    boton_refrescar = ft.Button(
        "🔄 Actualizar lista",
        on_click=lambda e: page.run_task(cargar),
        icon=ft.Icons.REFRESH,
    )

    # --- Panel visual que se insertará en la pestaña ---
    panel = ft.Column([
        ft.Row([boton_importar, boton_refrescar]),
        ft.Divider(),
        ft.Text("Soldados registrados:", weight=ft.FontWeight.BOLD),
        tabla,
    ])

    # --- Diccionario de retorno para el orquestador (app.py) ---
    return {
        "panel": panel,
        "cargar": cargar,
        "selector_archivo": selector_archivo,
        "texto_estado": texto_estado,
        "barra_progreso": barra_progreso,
    }