import asyncio
from datetime import datetime

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import loading_bar, module_header, no_data, toast
from theme import *

_CARD_SHADOW = [ft.BoxShadow(blur_radius=8, color="#000000", spread_radius=0, offset=ft.Offset(0, 3))]


def _kpi_card(icon, label, value_text, accent):
    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Row(
                        [ft.Icon(icon, size=16, color=ft.Colors.WHITE),
                         ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=accent,
                    border_radius=ft.BorderRadius(top_left=12, top_right=12, bottom_left=0, bottom_right=0),
                    padding=ft.Padding(12, 6, 12, 6),
                ),
                ft.Container(
                    content=ft.Text(value_text, size=24, weight=ft.FontWeight.BOLD, color=TEXT),
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding(0, 8, 0, 8),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        ),
        bgcolor=SURFACE,
        border_radius=12,
        shadow=_CARD_SHADOW,
        expand=True,
        height=85,
    )


def build(page: ft.Page):
    barra_loading = loading_bar()
    body = ft.Column(
        controls=[], scroll=ft.ScrollMode.ADAPTIVE, expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=4,
    )

    header_row = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("DÍA", size=13, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=1, alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("TURNO", size=13, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=1, alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("PUNTO", size=13, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=2, alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("ROL", size=13, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=1, alignment=ft.Alignment(-1, 0)),
            ft.Container(ft.Text("FACTOR", size=13, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=1, alignment=ft.Alignment(-1, 0)),
        ]),
        bgcolor=BTN_BG,
        border_radius=ft.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0),
        padding=ft.Padding(16, 10, 16, 10),
    )

    tabla_container = ft.Container(
        content=ft.Column([header_row, body]),
        expand=True,
    )

    texto_estado = ft.Text()
    selector_soldado = ft.Dropdown(
        label="Soldado", options=[], width=320,
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY,
    )
    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(MESES[i]) for i in range(12)],
        value=MESES[datetime.now().month - 1],
        width=130,
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY,
    )
    selector_año = ft.TextField(
        label="Año", value=str(datetime.now().year), width=100,
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY,
        cursor_color=PRIMARY,
    )

    kpi_total = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=TEXT)
    kpi_puntos = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=TEXT)
    kpi_diurnos = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=TEXT)
    kpi_nocturnos = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=TEXT)

    kpi_row = ft.Row(
        [
            _kpi_card(ft.Icons.SHIELD, "Guardias", "0", PRIMARY),
            _kpi_card(ft.Icons.STAR, "Puntos", "0", "#5C6BC0"),
            _kpi_card(ft.Icons.WB_SUNNY, "Diurnos", "0", SHIFT_DIURNO),
            _kpi_card(ft.Icons.NIGHTLIGHT, "Nocturnos", "0", SHIFT_NOCTURNO),
        ],
        spacing=12,
        expand=True,
    )

    resumen_card = ft.Container(
        bgcolor=SURFACE,
        border_radius=12,
        shadow=_CARD_SHADOW,
        visible=False,
        padding=ft.Padding(20, 14, 20, 14),
    )

    cont_tabla = ft.Container(content=tabla_container, expand=True, visible=False)
    no_data_container = no_data(ft.Icons.PERSON_SEARCH, "Seleccione un soldado y presione 'Ver ficha'")

    async def cargar_dropdown(max_intentos=3):
        intentos = 0
        while intentos < max_intentos:
            try:
                async with httpx.AsyncClient() as cliente:
                    token = get_token(page)
                    resp = await cliente.get(
                        f"{URL_BACKEND}/soldados",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    datos = resp.json()
                    if datos:
                        selector_soldado.options = [
                            ft.dropdown.Option(
                                key=str(s["id_soldado"]),
                                text=f"{s['nombre']} {s['apellido']} ({s['cedula']})",
                            )
                            for s in datos
                        ]
                        page.update()
                        return
            except Exception:
                pass
            intentos += 1
            await asyncio.sleep(1)
        toast(page, "No se pudo cargar la lista de soldados.", "error")

    def _actualizar_kpis(guardias):
        total = len(guardias)
        puntos = sum(g["factor"] for g in guardias)
        diurnos = sum(1 for g in guardias if g["turno"].lower() == "diurno")
        nocturnos = total - diurnos
        kpi_row.controls[0] = _kpi_card(ft.Icons.SHIELD, "Guardias", str(total), PRIMARY)
        kpi_row.controls[1] = _kpi_card(ft.Icons.STAR, "Puntos", f"{puntos:.1f}", "#5C6BC0")
        kpi_row.controls[2] = _kpi_card(ft.Icons.WB_SUNNY, "Diurnos", str(diurnos), SHIFT_DIURNO)
        kpi_row.controls[3] = _kpi_card(ft.Icons.NIGHTLIGHT, "Nocturnos", str(nocturnos), SHIFT_NOCTURNO)

    def _render_resumen(nombre, mes, anio, total_guardias, total_puntos):
        resumen_card.content = ft.Row([
            ft.Icon(ft.Icons.PERSON, size=20, color=PRIMARY),
            ft.Column([
                ft.Text(nombre, size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Text(
                    f"{MESES[mes - 1]} {anio}  ·  {total_guardias} guardias  ·  {total_puntos:.1f} puntos",
                    size=13, color=TEXT_SECONDARY,
                ),
            ], spacing=2),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)
        resumen_card.visible = True

    def _render_guardias(guardias):
        body.controls.clear()
        for g in guardias:
            turno = g["turno"].lower()
            es_titular = g["es_titular"]
            factor = g["factor"]

            turno_bg = "#2A2A2A"
            turno_badge = ft.Container(
                content=ft.Text(
                    turno.upper(),
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
                bgcolor=turno_bg,
                border_radius=4,
                padding=ft.Padding(8, 3, 8, 3),
            )

            rol_text = "TITULAR" if es_titular else "SUPLENTE"
            rol_chip = ft.Container(
                content=ft.Text(
                    rol_text,
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
                bgcolor="#2A2A2A",
                border_radius=4,
                padding=ft.Padding(8, 3, 8, 3),
            )

            row = ft.Container(
                content=ft.Row([
                    ft.Container(ft.Text(str(g["dia"]), size=15, color=TEXT_TABLE, weight=ft.FontWeight.W_600), expand=1, alignment=ft.Alignment(-1, 0)),
                    ft.Container(turno_badge, expand=1, alignment=ft.Alignment(-1, 0)),
                    ft.Container(ft.Text(g["punto"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=2, alignment=ft.Alignment(-1, 0)),
                    ft.Container(rol_chip, expand=1, alignment=ft.Alignment(-1, 0)),
                    ft.Container(ft.Text(f"{factor:.2f}", size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_600), expand=1, alignment=ft.Alignment(-1, 0)),
                ]),
                bgcolor=SURFACE,
                height=48,
                padding=ft.Padding(16, 0, 16, 0),
                border_radius=8,
            )

            def _make_hover(c):
                def _on_hover(e):
                    if e.data:
                        c.bgcolor = HOVER_ROW_BG
                        c.shadow = [ft.BoxShadow(blur_radius=8, color="#000000", spread_radius=0, offset=ft.Offset(0, 2))]
                        c.scale = ft.Scale(1.005)
                    else:
                        c.bgcolor = SURFACE
                        c.shadow = []
                        c.scale = ft.Scale(1.0)
                    c.update()
                return _on_hover

            row.on_hover = _make_hover(row)
            body.controls.append(row)

    async def cargar_ficha(e=None):
        if not selector_soldado.value:
            toast(page, "Seleccione un soldado.", "warning")
            return

        id_soldado = int(selector_soldado.value)
        mes = MESES.index(selector_mes.value) + 1
        anio = int(selector_año.value)

        body.controls.clear()
        resumen_card.visible = False
        cont_tabla.visible = False
        no_data_container.visible = False
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)

        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.get(
                    f"{URL_BACKEND}/ficha-soldado-ver/{id_soldado}/{mes}/{anio}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                datos = resp.json()

                guardias = datos.get("guardias", [])

                if "error" in datos:
                    toast(page, datos["error"], "error")
                    no_data_container.visible = True
                    return

                if not guardias:
                    toast(page, datos.get("mensaje", "No hay guardias para este soldado este mes."), "warning")
                    no_data_container.visible = True
                    return

                nombre = datos.get("nombre", "Desconocido")
                total_guardias = datos.get("total_guardias", 0)
                total_puntos = datos.get("total_puntos", 0)

                _actualizar_kpis(guardias)
                _render_resumen(nombre, mes, anio, total_guardias, total_puntos)
                _render_guardias(guardias)

                cont_tabla.visible = True

        except Exception:
            toast(page, "Error al cargar la ficha.", "error")
            no_data_container.visible = True
        finally:
            barra_loading.visible = False
            page.update()

    async def cargar_para_soldado(id_soldado, mes, anio):
        selector_soldado.value = str(id_soldado)
        selector_mes.value = MESES[mes - 1]
        selector_año.value = str(anio)
        await cargar_ficha()

    selectores_card = ft.Container(
        content=ft.Row([
            selector_soldado,
            selector_mes,
            selector_año,
            ft.FilledButton(
                "Ver ficha",
                on_click=cargar_ficha,
                icon=ft.Icons.SEARCH,
                style=ft.ButtonStyle(bgcolor=BTN_BG, color=BTN_TEXT),
            ),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        padding=ft.Padding(16, 12, 16, 12),
    )

    panel = ft.Column(
        [
            barra_loading,
            module_header("Ficha Individual", "Historial mensual de guardias y puntaje ponderado"),
            ft.Divider(height=1, color=DIVIDER),
            selectores_card,
            ft.Container(height=8),
            kpi_row,
            ft.Container(height=8),
            resumen_card,
            cont_tabla,
            no_data_container,
        ],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    return {
        "panel": panel,
        "cargar_dropdown": cargar_dropdown,
        "cargar_para_soldado": cargar_para_soldado,
    }
