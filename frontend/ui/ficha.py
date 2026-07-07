import asyncio

import flet as ft
import httpx
from config import URL_BACKEND


def build(page: ft.Page):
    """Construye la ficha individual de un soldado: historial mensual de guardias con ponderación."""
    _exp = [1, 1, 2, 2, 1]

    body = ft.Column(controls=[], scroll=ft.ScrollMode.ADAPTIVE, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    header = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("D\u00cdA", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[0]),
            ft.Container(ft.Text("TURNO", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[1]),
            ft.Container(ft.Text("PUNTO", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[2]),
            ft.Container(ft.Text("TITULAR/SUPLENTE", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[3]),
            ft.Container(ft.Text("FACTOR", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[4]),
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
    selector_soldado = ft.Dropdown(label="Soldado", options=[], width=300)
    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(str(m)) for m in range(1, 13)],
        value="5",
        width=120,
    )
    selector_año = ft.TextField(label="Año", value="2026", width=100)
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
                        page.update()
                        return
            except Exception:
                pass
            intentos += 1
            await asyncio.sleep(1)
        texto_estado.value = "No se pudo cargar la lista de soldados."
        texto_estado.color = ft.Colors.GREY_400
        page.update()

    async def cargar_ficha(e=None):
        if not selector_soldado.value:
            texto_estado.value = "Seleccione un soldado."
            texto_estado.color = ft.Colors.YELLOW
            page.update()
            return

        id_soldado = int(selector_soldado.value)
        mes = int(selector_mes.value)
        año = int(selector_año.value)

        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.get(f"{URL_BACKEND}/ficha-soldado-ver/{id_soldado}/{mes}/{año}")
                datos = resp.json()

                if "mensaje" in datos:
                    texto_estado.value = datos['mensaje']
                    texto_estado.color = ft.Colors.GREY_400
                    body.controls.clear()
                    resumen_texto.value = ""
                    page.update()
                    return

                body.controls.clear()
                for g in datos.get("guardias", []):
                    titular = "Titular" if g["es_titular"] else "Suplente"
                    body.controls.append(ft.Container(
                        content=ft.Row([
                            ft.Container(ft.Text(str(g["dia"]), size=16, color="#DEDEDE"), expand=_exp[0]),
                            ft.Container(ft.Text(g["turno"].capitalize(), size=16, color="#DEDEDE"), expand=_exp[1]),
                            ft.Container(ft.Text(g["punto"], size=16, color="#DEDEDE"), expand=_exp[2]),
                            ft.Container(ft.Text(titular, size=16, color="#DEDEDE"), expand=_exp[3]),
                            ft.Container(ft.Text(str(g["factor"]), size=16, color="#DEDEDE"), expand=_exp[4]),
                        ]),
                        bgcolor="#171C22",
                        height=40,
                        padding=ft.Padding(left=16, top=0, right=16, bottom=0),
                    ))

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
        ft.Row([
            ft.Container(expand=1),
            ft.Container(content=tabla_container, expand=6, padding=ft.Padding(left=20, right=20, top=10, bottom=10)),
            ft.Container(expand=1),
        ], expand=True),
        ft.Divider(),
        texto_estado,
    ])

    return {"panel": panel,
            "cargar_dropdown": cargar_dropdown,}
