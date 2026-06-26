import flet as ft
import httpx
import tempfile
import os
from config import URL_BACKEND


def build(page: ft.Page):
    # --- Controles de la interfaz ---
    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(str(m)) for m in range(1, 13)],
        value="5",
        width=120,
    )
    selector_año = ft.TextField(label="Año", value="2026", width=100)
    contenedor_puntos = ft.Column()
    texto_estado = ft.Text()

    # --- Funciones asíncronas ---
    async def generar(e):
        mes = int(selector_mes.value)
        año = int(selector_año.value)
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.post(
                    f"{URL_BACKEND}/generar-calendario",
                    params={"mes": mes, "año": año}
                )
                datos = resp.json()
                if "error" in datos:
                    texto_estado.value = f"❌ {datos['error']}"
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = f"✅ {datos['mensaje']} ({datos['total_guardias']} guardias)"
                    texto_estado.color = ft.Colors.GREEN
        except Exception as ex:
            texto_estado.value = f"❌ Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    async def cargar(e=None):
        mes = int(selector_mes.value)
        año = int(selector_año.value)
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.get(f"{URL_BACKEND}/calendario-ver/{año}/{mes}")
                datos = resp.json()

                contenedor_puntos.controls.clear()
                asignaciones_por_punto = {}
                for a in datos.get("asignaciones", []):
                    punto = a["punto"]
                    asignaciones_por_punto.setdefault(punto, []).append(a)

                for nombre_punto, lista in asignaciones_por_punto.items():
                    tabla_punto = ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("ID")),
                            ft.DataColumn(ft.Text("Día")),
                            ft.DataColumn(ft.Text("Turno")),
                            ft.DataColumn(ft.Text("Cédula")),
                            ft.DataColumn(ft.Text("Nombre")),
                            ft.DataColumn(ft.Text("Apellido")),
                            ft.DataColumn(ft.Text("Rango")),
                            ft.DataColumn(ft.Text("Unidad")),
                        ],
                        rows=[],
                        border=ft.Border.all(1, ft.Colors.GREY_700),
                    )
                    for a in lista:
                        tabla_punto.rows.append(ft.DataRow(cells=[
                            ft.DataCell(ft.Text(str(a["id_asignacion"]))),
                            ft.DataCell(ft.Text(str(a["dia"]))),
                            ft.DataCell(ft.Text(a["turno"].capitalize())),
                            ft.DataCell(ft.Text(a["cedula"])),
                            ft.DataCell(ft.Text(a["nombre"])),
                            ft.DataCell(ft.Text(a["apellido"])),
                            ft.DataCell(ft.Text(a["rango"])),
                            ft.DataCell(ft.Text(a["unidad"])),
                        ]))
                    contenedor_puntos.controls.append(ft.Text(f"📌 {nombre_punto}", weight=ft.FontWeight.BOLD, size=16))
                    contenedor_puntos.controls.append(tabla_punto)
                    contenedor_puntos.controls.append(ft.Divider())

                texto_estado.value = f"Calendario {mes}/{año} cargado."
                texto_estado.color = ft.Colors.GREEN
        except Exception as ex:
            texto_estado.value = f"Error al cargar calendario: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    async def descargar_pdf():
        mes = int(selector_mes.value)
        año = int(selector_año.value)
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.get(f"{URL_BACKEND}/exportar-pdf/{mes}/{año}")
                if resp.status_code == 200:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    tmp.write(resp.content)
                    tmp.close()
                    os.startfile(tmp.name)
                    texto_estado.value = "✅ PDF generado y abierto automáticamente."
                    texto_estado.color = ft.Colors.GREEN
                else:
                    texto_estado.value = "❌ Error al generar el PDF. Verifique que existan guardias."
                    texto_estado.color = ft.Colors.RED
        except Exception as ex:
            texto_estado.value = f"❌ Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    # --- Botones ---
    boton_generar = ft.Button("⚙️ Generar Calendario", on_click=generar, icon=ft.Icons.CALENDAR_MONTH)
    boton_ver = ft.Button("📅 Ver Calendario", on_click=cargar, icon=ft.Icons.CALENDAR_MONTH)
    boton_pdf = ft.Button("📄 Exportar PDF", on_click=lambda e: page.run_task(descargar_pdf), icon=ft.Icons.PICTURE_AS_PDF)

    # --- Panel visual ---
    panel = ft.Column([
        ft.Row([selector_mes, selector_año, boton_generar, boton_ver, boton_pdf]),
        ft.Divider(),
        contenedor_puntos,
    ])

    return {
        "panel": panel,
        "generar_calendario": generar,
        "cargar_calendario": cargar,
        "contenedor_puntos": contenedor_puntos,
        "texto_estado": texto_estado,
    }