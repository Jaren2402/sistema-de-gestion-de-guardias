import flet as ft
import httpx
import asyncio
from config import URL_BACKEND


def build(page: ft.Page):
    # --- Controles de la interfaz ---
    texto_estado = ft.Text(
        value="ℹ️ Para registrar una restricción, primero importe soldados.",
        color=ft.Colors.GREY_400,
    )
    selector_soldado = ft.Dropdown(label="Soldado", options=[], width=300)
    campo_inicio = ft.TextField(label="Fecha inicio (YYYY-MM-DD)")
    campo_fin = ft.TextField(label="Fecha fin (YYYY-MM-DD)")
    campo_motivo = ft.TextField(label="Motivo")
    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("SOLDADO")),
            ft.DataColumn(ft.Text("INICIO")),
            ft.DataColumn(ft.Text("FIN")),
            ft.DataColumn(ft.Text("MOTIVO")),
            ft.DataColumn(ft.Text("ACCIONES")),
        ],
        rows=[],
        border=ft.Border.all(1, ft.Colors.GREY_800),
        border_radius=10,
        bgcolor="#121416",
        heading_row_color="#25292E",
        heading_row_height=48,
        data_row_min_height=36,
        data_text_style=ft.TextStyle(size=16, color="#DEDEDE"),
        column_spacing=40,
    )

    # --- Funciones asíncronas ---
    async def cargar_dropdown(max_intentos=3):
        """Llena el dropdown de soldados con reintentos automáticos."""
        intentos = 0
        while intentos < max_intentos:
            try:
                async with httpx.AsyncClient() as cliente:
                    resp = await cliente.get(f"{URL_BACKEND}/soldados")
                    datos = resp.json()
                    if datos:
                        selector_soldado.options = [
                            ft.dropdown.Option(
                                key=str(s["id_soldado"]),
                                text=f"{s['nombre']} {s['apellido']} ({s['cedula']})"
                            )
                            for s in datos
                        ]
                        texto_estado.value = "✅ Lista de soldados cargada."
                        texto_estado.color = ft.Colors.GREEN
                        print(f"✅ Dropdown cargado con {len(datos)} soldados.")
                        page.update()
                        return
            except Exception as ex:
                print(f"⏳ Intento {intentos+1} fallido. Reintentando... ({ex})")
            intentos += 1
            await asyncio.sleep(1)
        
        # Si agotó los intentos, mostrar mensaje orientativo
        texto_estado.value = "ℹ️ Para registrar una restricción, primero importe soldados."
        texto_estado.color = ft.Colors.GREY_400
        page.update()

    async def cargar_tabla():
        """Carga la tabla de restricciones desde el backend."""
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.get(f"{URL_BACKEND}/restricciones")
                datos = resp.json()
                tabla.rows.clear()
                for r in datos:
                    tabla.rows.append(ft.DataRow(
                        color="#171C22",
                        cells=[
                            ft.DataCell(ft.Text(r["nombre"])),
                            ft.DataCell(ft.Text(r["fecha_inicio"])),
                            ft.DataCell(ft.Text(r["fecha_fin"])),
                            ft.DataCell(ft.Text(r["motivo"])),
                            ft.DataCell(ft.TextButton(
                                "Eliminar",
                                icon=ft.Icons.DELETE,
                                on_click=lambda e, rid=r["id"]: page.run_task(eliminar, rid)
                            )),
                        ]
                    ))
        except Exception as ex:
            texto_estado.value = f"Error al cargar restricciones: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    async def crear(e):
        """Crea una nueva restricción y refresca la tabla."""
        if not selector_soldado.value:
            texto_estado.value = "Seleccione un soldado."
            texto_estado.color = ft.Colors.RED
            page.update()
            return
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.post(f"{URL_BACKEND}/restricciones", params={
                    "id_soldado": int(selector_soldado.value),
                    "fecha_inicio": campo_inicio.value,
                    "fecha_fin": campo_fin.value,
                    "motivo": campo_motivo.value,
                })
                datos = resp.json()
                if "error" in datos:
                    texto_estado.value = f"❌ {datos['error']}"
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = "✅ Restricción creada."
                    texto_estado.color = ft.Colors.GREEN
                    campo_motivo.value = ""
                    await cargar_tabla()
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    async def eliminar(id_restriccion: int):
        """Elimina una restricción y refresca la tabla."""
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.delete(f"{URL_BACKEND}/restricciones/{id_restriccion}")
                datos = resp.json()
                if "error" in datos:
                    texto_estado.value = f"❌ {datos['error']}"
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = "✅ Restricción eliminada."
                    texto_estado.color = ft.Colors.GREEN
                    await cargar_tabla()
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    # --- Botones ---
    boton_crear = ft.Button(
        "➕ Añadir Restricción",
        on_click=crear,
        icon=ft.Icons.ADD,
    )
    boton_refrescar = ft.Button(
        "🔄 Refrescar",
        on_click=lambda e: page.run_task(cargar_dropdown),
        icon=ft.Icons.REFRESH,
    )

    # --- Panel visual ---
    panel = ft.Column([
        ft.Text("Añadir restricción:", weight=ft.FontWeight.BOLD),
        texto_estado,
        ft.Row([selector_soldado, campo_inicio, campo_fin]),
        ft.Row([campo_motivo, boton_crear]),
        ft.Divider(),
        ft.Row([boton_refrescar]),
        tabla,
    ])

    page.run_task(cargar_dropdown)
    
    # --- Retorno para app.py ---
    return {
        "panel": panel,
        "cargar_dropdown": cargar_dropdown,
        "cargar_tabla": cargar_tabla,
        "texto_estado": texto_estado,
    }