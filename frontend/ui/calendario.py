import asyncio
import os
import tempfile

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import hover_row, loading_bar, module_header
from theme import *


def build(page: ft.Page):
    """Construye el calendario mensual de guardias con secciones colapsables por punto."""
    _asignaciones_raw = []

    barra_loading = loading_bar()
    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(MESES[i]) for i in range(12)],
        value=MESES[4],
        width=120,
    )
    selector_año = ft.TextField(label="Año", value="2026", width=100)
    contenedor_puntos = ft.Column(expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, scroll=ft.ScrollMode.AUTO)
    texto_estado = ft.Text()

    txt_buscar = ft.TextField(
        label="Buscar en calendario",
        hint_text="Nombre, cedula, rango o unidad",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        on_change=lambda e: _reconstruir(),
    )

    def _reconstruir():
        q = txt_buscar.value.strip().lower()
        filtradas = [a for a in _asignaciones_raw
                     if not q
                     or q in a["nombre"].lower()
                     or q in a["apellido"].lower()
                     or q in a["cedula"].lower()
                     or q in a["rango"].lower()
                     or q in a["unidad"].lower()
                     or q in a["turno"].lower()]
        contenedor_puntos.controls.clear()
        asignaciones_por_punto = {}
        for a in filtradas:
            punto = a["punto"]
            asignaciones_por_punto.setdefault(punto, []).append(a)

        _exp = [1, 1, 1, 1, 2, 2, 1, 1]
        for nombre_punto, lista in asignaciones_por_punto.items():
            body_punto = ft.Column(controls=[], scroll=ft.ScrollMode.ADAPTIVE, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
            table_header = ft.Container(
                content=ft.Row([
                    ft.Container(ft.Text("ID", size=14, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[0]),
                    ft.Container(ft.Text("DIA", size=14, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[1]),
                    ft.Container(ft.Text("TURNO", size=14, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[2]),
                    ft.Container(ft.Text("CEDULA", size=14, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[3]),
                    ft.Container(ft.Text("NOMBRE", size=14, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[4]),
                    ft.Container(ft.Text("APELLIDO", size=14, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[5]),
                    ft.Container(ft.Text("RANGO", size=14, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[6]),
                    ft.Container(ft.Text("UNIDAD", size=14, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_exp[7]),
                ]),
                bgcolor=SURFACE_LIGHT,
                padding=ft.Padding(left=16, top=10, right=16, bottom=10),
            )
            tabla_punto = ft.Container(
                content=ft.Column([table_header, body_punto]),
                height=400,
                bgcolor=TABLE_BG,
            )
            for a in lista:
                body_punto.controls.append(hover_row(ft.Container(
                    content=ft.Row([
                        ft.Container(ft.Text(str(a["id_asignacion"]), size=14, color=TEXT_TABLE), expand=_exp[0]),
                        ft.Container(ft.Text(str(a["dia"]), size=14, color=TEXT_TABLE), expand=_exp[1]),
                        ft.Container(ft.Text(a["turno"].capitalize(), size=14, color=TEXT_TABLE), expand=_exp[2]),
                        ft.Container(ft.Text(a["cedula"], size=14, color=TEXT_TABLE), expand=_exp[3]),
                        ft.Container(ft.Text(a["nombre"].capitalize(), size=14, color=TEXT_TABLE), expand=_exp[4]),
                        ft.Container(ft.Text(a["apellido"], size=14, color=TEXT_TABLE), expand=_exp[5]),
                        ft.Container(ft.Text(a["rango"].title(), size=14, color=TEXT_TABLE), expand=_exp[6]),
                        ft.Container(ft.Text(a["unidad"].capitalize(), size=14, color=TEXT_TABLE), expand=_exp[7]),
                    ]),
                    bgcolor=TABLE_ROW,
                    height=40,
                    padding=ft.Padding(left=16, top=0, right=16, bottom=0),
                )))

            chevron = ft.Icon(ft.Icons.EXPAND_LESS, size=22, color=TEXT)
            exp_state = [True]

            def hacer_toggle(t, c, es):
                def toggle(e):
                    es[0] = not es[0]
                    t.visible = es[0]
                    c.name = ft.Icons.EXPAND_LESS if es[0] else ft.Icons.EXPAND_MORE
                    page.update()
                return toggle

            header_colap = ft.Container(
                content=ft.Row([
                    chevron,
                    ft.Text(nombre_punto, size=16, weight=ft.FontWeight.BOLD, color=TEXT, expand=True),
                    ft.Text(f"{len(lista)} guardias", size=12, color=TEXT_SECONDARY),
                ]),
                bgcolor=HEADER_BG,
                padding=ft.Padding(left=16, top=16, right=16, bottom=16),
                on_click=hacer_toggle(tabla_punto, chevron, exp_state),
            )

            seccion = ft.Container(
                content=ft.Column([header_colap, tabla_punto]),
                border_radius=10,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                bgcolor=TABLE_BG,
            )

            contenedor_puntos.controls.append(
                ft.Row([
                    ft.Container(expand=1),
                    ft.Container(content=seccion, expand=6, padding=ft.Padding(left=20, right=20, top=5, bottom=5)),
                    ft.Container(expand=1),
                ], expand=True),
            )
            contenedor_puntos.controls.append(ft.Divider(height=16, color="transparent"))
        page.update()

    async def generar(e):
        mes = MESES.index(selector_mes.value) + 1
        año = int(selector_año.value)
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.post(
                    f"{URL_BACKEND}/generar-calendario",
                    params={"mes": mes, "año": año, "token": token}
                )
                datos = resp.json()
                if "error" in datos:
                    texto_estado.value = datos['error']
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = ""
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            barra_loading.visible = False
            page.update()

    async def cargar(e=None):
        nonlocal _asignaciones_raw
        mes = MESES.index(selector_mes.value) + 1
        año = int(selector_año.value)
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.get(f"{URL_BACKEND}/calendario-ver/{año}/{mes}", params={"token": token})
                datos = resp.json()
                _asignaciones_raw = datos.get("asignaciones", [])
                _reconstruir()
                texto_estado.value = ""
        except Exception as ex:
            texto_estado.value = f"Error al cargar calendario: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            barra_loading.visible = False
            page.update()

    async def descargar_pdf():
        mes = MESES.index(selector_mes.value) + 1
        año = int(selector_año.value)
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.get(f"{URL_BACKEND}/exportar-pdf/{mes}/{año}", params={"token": token})
                if resp.status_code == 200:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    tmp.write(resp.content)
                    tmp.close()
                    os.startfile(tmp.name)
                    texto_estado.value = ""
                else:
                    texto_estado.value = "Error al generar el PDF. Verifique que existan guardias."
                    texto_estado.color = ft.Colors.RED
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            barra_loading.visible = False
            page.update()

    async def difundir():
        mes = MESES.index(selector_mes.value) + 1
        año = int(selector_año.value)
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.post(f"{URL_BACKEND}/difundir/{mes}/{año}", params={"token": token})
                datos = resp.json()
                if "error" in datos:
                    texto_estado.value = datos['error']
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = ""
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            barra_loading.visible = False
            page.update()

    boton_generar = ft.FilledButton("Generar Calendario", on_click=generar, icon=ft.Icons.CALENDAR_MONTH)
    boton_ver = ft.FilledButton("Ver Calendario", on_click=cargar, icon=ft.Icons.CALENDAR_MONTH)
    boton_pdf = ft.FilledButton("Exportar PDF", on_click=lambda e: page.run_task(descargar_pdf), icon=ft.Icons.PICTURE_AS_PDF)
    boton_difundir = ft.FilledButton("Difundir", on_click=lambda e: page.run_task(difundir), icon=ft.Icons.SEND)

    panel = ft.Column([
        barra_loading,
        module_header("Calendario", "Planificación y asignación de guardias mensuales"),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row([selector_mes, selector_año, boton_generar, boton_ver, boton_pdf, boton_difundir]),
        ft.Divider(height=1, color=DIVIDER),
        txt_buscar,
        ft.Divider(height=1, color=DIVIDER),
        contenedor_puntos,
    ])

    return {
        "panel": panel,
        "generar_calendario": generar,
        "cargar_calendario": cargar,
        "contenedor_puntos": contenedor_puntos,
        "texto_estado": texto_estado,
    }
