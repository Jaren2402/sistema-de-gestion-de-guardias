import flet as ft
import httpx
import asyncio
from config import URL_BACKEND


def build(page: ft.Page):
    texto_estado = ft.Text()
    selector_soldado = ft.Dropdown(label="Soldado", options=[], width=300)
    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(str(m)) for m in range(1, 13)],
        value="5",
        width=120,
    )
    selector_año = ft.TextField(label="Año", value="2026", width=100)
    tabla_ficha = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Día")),
            ft.DataColumn(ft.Text("Turno")),
            ft.DataColumn(ft.Text("Punto")),
            ft.DataColumn(ft.Text("Titular/Suplente")),
            ft.DataColumn(ft.Text("Factor")),
        ],
        rows=[],
        border=ft.Border.all(1, ft.Colors.GREY_700),
    )
    resumen_texto = ft.Text(size=16, weight=ft.FontWeight.BOLD)

    async def cargar_dropdown(max_intentos=3):
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
                        print(f"✅ Dropdown Ficha cargado con {len(datos)} soldados.")
                        page.update()
                        return
            except Exception as ex:
                print(f"⏳ Intento {intentos+1} fallido en Ficha. Reintentando... ({ex})")
            intentos += 1
            await asyncio.sleep(1)
        texto_estado.value = "ℹ️ No se pudo cargar la lista de soldados."
        texto_estado.color = ft.Colors.GREY_400
        page.update()

    async def cargar_ficha(e=None):
        if not selector_soldado.value:
            texto_estado.value = "⚠️ Seleccione un soldado."
            texto_estado.color = ft.Colors.YELLOW
            page.update()
            return

        id_soldado = int(selector_soldado.value)
        mes = int(selector_mes.value)
        año = int(selector_año.value)

        try:
            async with httpx.AsyncClient() as cliente:
                # URL corregida (sin ñ)
                resp = await cliente.get(f"{URL_BACKEND}/ficha-soldado-ver/{id_soldado}/{mes}/{año}")
                datos = resp.json()

                if "mensaje" in datos:
                    texto_estado.value = f"ℹ️ {datos['mensaje']}"
                    texto_estado.color = ft.Colors.GREY_400
                    tabla_ficha.rows.clear()
                    resumen_texto.value = ""
                    page.update()
                    return

                tabla_ficha.rows.clear()
                for g in datos.get("guardias", []):
                    titular = "Titular" if g["es_titular"] else "Suplente"
                    tabla_ficha.rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(g["dia"]))),
                        ft.DataCell(ft.Text(g["turno"].capitalize())),
                        ft.DataCell(ft.Text(g["punto"])),
                        ft.DataCell(ft.Text(titular)),
                        ft.DataCell(ft.Text(str(g["factor"]))),
                    ]))

                resumen_texto.value = f"{datos['nombre']} - Total guardias: {datos['total_guardias']} | Puntos acumulados: {datos['total_puntos']}"
                texto_estado.value = ""
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    page.run_task(cargar_dropdown)

    panel = ft.Column([
        ft.Row([selector_soldado, selector_mes, selector_año,
                ft.Button("Ver ficha", on_click=cargar_ficha, icon=ft.Icons.SEARCH)]),
        ft.Divider(),
        resumen_texto,
        ft.Divider(),
        tabla_ficha,
        ft.Divider(),
        texto_estado,
    ])

    return {"panel": panel,
            "cargar_dropdown": cargar_dropdown,}