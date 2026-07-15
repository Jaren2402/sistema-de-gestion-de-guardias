import asyncio

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import hover_row, loading_bar, module_header, no_data
from skeleton import table_row as sk_row
from theme import *


def build(page: ft.Page):
    """Construye la ficha individual de un soldado: historial mensual de guardias con ponderación."""
    _exp = [1, 1, 2, 2, 1]

    barra_loading = loading_bar()
    body = ft.Column(controls=[], scroll=ft.ScrollMode.ADAPTIVE, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    header = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("D\u00cdA", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[0]),
            ft.Container(ft.Text("TURNO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[1]),
            ft.Container(ft.Text("PUNTO", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[2]),
            ft.Container(ft.Text("TITULAR/SUPLENTE", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[3]),
            ft.Container(ft.Text("FACTOR", size=16, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[4]),
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
    selector_soldado = ft.Dropdown(label="Soldado", options=[], width=300)
    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(MESES[i]) for i in range(12)],
        value=MESES[4],
        width=120,
    )
    selector_año = ft.TextField(label="Año", value="2026", width=100)
    resumen_texto = ft.Text(size=16, weight=ft.FontWeight.BOLD)

    async def cargar_dropdown(max_intentos=3):
        intentos = 0
        while intentos < max_intentos:
            try:
                async with httpx.AsyncClient() as cliente:
                    token = get_token(page)
                    resp = await cliente.get(f"{URL_BACKEND}/soldados", params={"token": token})
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
        mes = MESES.index(selector_mes.value) + 1
        año = int(selector_año.value)

        body.controls = [sk_row(_exp) for _ in range(6)]
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.get(f"{URL_BACKEND}/ficha-soldado-ver/{id_soldado}/{mes}/{año}", params={"token": token})
                datos = resp.json()

                guardias = datos.get("guardias", [])
                body.controls.clear()
                if "mensaje" in datos or not guardias:
                    texto_estado.value = datos.get("mensaje", "No hay guardias para este soldado este mes.")
                    texto_estado.color = ft.Colors.GREY_400
                    resumen_texto.value = ""
                    cont_tabla.visible = False
                    no_data_container.visible = True
                    page.update()
                    return

                for g in guardias:
                    titular = "Titular" if g["es_titular"] else "Suplente"
                    body.controls.append(hover_row(ft.Container(
                        content=ft.Row([
                            ft.Container(ft.Text(str(g["dia"]), size=16, color=TEXT_TABLE), expand=_exp[0]),
                            ft.Container(ft.Text(g["turno"].capitalize(), size=16, color=TEXT_TABLE), expand=_exp[1]),
                            ft.Container(ft.Text(g["punto"], size=16, color=TEXT_TABLE), expand=_exp[2]),
                            ft.Container(ft.Text(titular, size=16, color=TEXT_TABLE), expand=_exp[3]),
                            ft.Container(ft.Text(str(g["factor"]), size=16, color=TEXT_TABLE), expand=_exp[4]),
                        ]),
                        bgcolor=TABLE_ROW,
                        height=40,
                        padding=ft.Padding(left=16, top=0, right=16, bottom=0),
                    )))

                resumen_texto.value = f"{datos['nombre']} - Total guardias: {datos['total_guardias']} | Puntos acumulados: {datos['total_puntos']}"
                texto_estado.value = ""
                cont_tabla.visible = True
                no_data_container.visible = False
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

    async def cargar_para_soldado(id_soldado, mes, año):
        selector_soldado.value = str(id_soldado)
        selector_mes.value = MESES[mes - 1]
        selector_año.value = str(año)
        await cargar_ficha()

    no_data_container = no_data(ft.Icons.PERSON_SEARCH, "Seleccione un soldado y presione 'Ver ficha'")
    cont_tabla = ft.Row([
        ft.Container(expand=1),
        ft.Container(content=tabla_container, expand=6, padding=ft.Padding(left=20, right=20, top=10, bottom=10)),
        ft.Container(expand=1),
    ], expand=True, visible=False)

    panel = ft.Column([
        barra_loading,
        module_header("Ficha Individual", "Historial mensual de guardias y puntaje ponderado"),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row([selector_soldado, selector_mes, selector_año,
                ft.FilledButton("Ver ficha", on_click=cargar_ficha, icon=ft.Icons.SEARCH)]),
        ft.Divider(height=1, color=DIVIDER),
        resumen_texto,
        ft.Divider(height=1, color=DIVIDER),
        cont_tabla,
        no_data_container,
        ft.Divider(height=1, color=DIVIDER),
        texto_estado,
    ])

    return {"panel": panel,
            "cargar_dropdown": cargar_dropdown,
            "cargar_para_soldado": cargar_para_soldado,}
