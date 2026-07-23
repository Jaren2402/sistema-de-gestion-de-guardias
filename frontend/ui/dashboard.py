import asyncio
from datetime import datetime

import flet as ft
import flet_charts as fch
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import loading_bar, module_header
from theme import *


def _build_rank_row(pos: int, nombre: str, valor):
    item = ft.Container(
        content=ft.Row(
            [
                ft.Text(
                    nombre, size=14, color=TEXT,
                    expand=True, no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    str(valor), size=14,
                    weight=ft.FontWeight.BOLD, color=TEXT,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(12, 6, 12, 6),
        border_radius=6,
        expand=True,
    )

    def _hover(e):
        if e.data:
            item.bgcolor = HOVER_ROW_BG
        else:
            item.bgcolor = None
        item.update()

    item.on_hover = _hover
    return item


def _build_rank_card(titulo, icon, items, clave, accent):
    rows = []
    if items:
        for i, item in enumerate(items[:5]):
            rows.append(_build_rank_row(i + 1, item["nombre"], item.get(clave, 0)))
    else:
        rows.append(ft.Container(
            content=ft.Text("Sin datos", size=12, color=TEXT_SECONDARY, italic=True),
            alignment=ft.Alignment(0, 0), padding=20,
        ))

    card = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(icon, size=18, color=ft.Colors.WHITE),
                            ft.Text(titulo, size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=accent,
                    border_radius=ft.BorderRadius(
                        top_left=12, top_right=12, bottom_left=0, bottom_right=0,
                    ),
                    padding=ft.Padding(16, 10, 16, 10),
                ),
                ft.Column(rows, spacing=2, expand=True),
            ],
            spacing=0,
            expand=True,
        ),
        bgcolor=SURFACE,
        border_radius=12,
        shadow=[
            ft.BoxShadow(
                blur_radius=8, color="#000000",
                spread_radius=0, offset=ft.Offset(0, 3),
            )
        ],
        expand=True,
        animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        height=300,
    )

    def _hover(e):
        if e.data:
            card.shadow = [
                ft.BoxShadow(
                    blur_radius=12, color="#000000",
                    spread_radius=1, offset=ft.Offset(0, 4),
                )
            ]
            card.scale = ft.Scale(1.01)
        else:
            card.shadow = [
                ft.BoxShadow(
                    blur_radius=8, color="#000000",
                    spread_radius=0, offset=ft.Offset(0, 3),
                )
            ]
            card.scale = ft.Scale(1.0)
        card.update()

    card.on_hover = _hover
    return card


def _build_trend_card(evolucion):
    txt_title = ft.Text(
        "Tendencia de Equidad", size=14,
        weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE,
    )

    chart = fch.LineChart(
        min_y=0, max_y=100,
        expand=True,
        interactive=True,
        border=ft.Border(
            bottom=ft.BorderSide(1, DIVIDER),
            left=ft.BorderSide(1, DIVIDER),
        ),
        horizontal_grid_lines=fch.ChartGridLines(
            interval=25, color="#1E1E1E", width=1,
        ),
        vertical_grid_lines=fch.ChartGridLines(
            interval=1, color="#1E1E1E", width=1,
        ),
        tooltip=fch.LineChartTooltip(
            bgcolor=ft.Colors.with_opacity(0.85, "#1A1A1A"),
        ),
        left_axis=fch.ChartAxis(
            label_size=30,
            labels=[
                fch.ChartAxisLabel(value=v, label=ft.Text(f"{v}%", size=11, color=TEXT_SECONDARY))
                for v in [0, 25, 50, 75, 100]
            ],
        ),
        bottom_axis=fch.ChartAxis(
            label_size=36,
            labels=[],
        ),
    )

    header = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.SHOW_CHART, size=18, color=ft.Colors.WHITE),
                txt_title,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=BTN_BG,
        border_radius=ft.BorderRadius(top_left=12, top_right=12, bottom_left=0, bottom_right=0),
        padding=ft.Padding(16, 10, 16, 10),
    )

    body = ft.Stack(
        [
            ft.Container(bgcolor=SURFACE, expand=True),
            ft.Container(content=chart, expand=True, padding=ft.Padding(8, 8, 8, 4)),
        ],
        expand=True,
    )

    card = ft.Container(
        content=ft.Column(
            [header, ft.Stack([body], expand=True)],
            spacing=0,
            expand=True,
        ),
        bgcolor=SURFACE,
        border_radius=12,
        shadow=[
            ft.BoxShadow(
                blur_radius=8, color="#000000",
                spread_radius=0, offset=ft.Offset(0, 3),
            )
        ],
        expand=True,
        height=300,
    )

    def _hover(e):
        if e.data:
            card.shadow = [
                ft.BoxShadow(
                    blur_radius=12, color="#000000",
                    spread_radius=1, offset=ft.Offset(0, 4),
                )
            ]
        else:
            card.shadow = [
                ft.BoxShadow(
                    blur_radius=8, color="#000000",
                    spread_radius=0, offset=ft.Offset(0, 3),
                )
            ]
        card.update()

    card.on_hover = _hover

    def update_data(evolucion):
        chart.visible = True
        if not evolucion:
            chart.data_series = []
            chart.bottom_axis = fch.ChartAxis(label_size=36, labels=[])
        else:
            points = []
            labels = []
            for i, e in enumerate(evolucion):
                points.append(fch.LineChartDataPoint(
                    i, e.get("porcentaje", 0),
                    tooltip=fch.LineChartDataPointTooltip(
                        text_style=ft.TextStyle(
                            color=ft.Colors.WHITE, size=13,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ),
                ))
                labels.append(
                    fch.ChartAxisLabel(
                        value=i,
                        label=ft.Container(
                            content=ft.Text(
                                e.get("mes", ""), size=11,
                                color=TEXT_SECONDARY,
                                weight=ft.FontWeight.BOLD,
                            ),
                            margin=ft.Margin(top=6),
                        ),
                    )
                )
            chart.data_series = [
                fch.LineChartData(
                    color=BTN_BG,
                    curved=True,
                    rounded_stroke_cap=True,
                    stroke_width=4,
                    below_line_bgcolor=ft.Colors.with_opacity(0.15, BTN_BG),
                    points=points,
                )
            ]
            chart.bottom_axis = fch.ChartAxis(label_size=36, labels=labels)

    card.update_data = update_data
    return card


def build(page: ft.Page):
    barra_loading = loading_bar()

    sel_ano = ft.TextField(label="Año", value=str(datetime.now().year), width=100)
    _meses = [
        ("1", "Enero"), ("2", "Febrero"), ("3", "Marzo"),
        ("4", "Abril"), ("5", "Mayo"), ("6", "Junio"),
        ("7", "Julio"), ("8", "Agosto"), ("9", "Septiembre"),
        ("10", "Octubre"), ("11", "Noviembre"), ("12", "Diciembre"),
    ]
    sel_desde = ft.Dropdown(
        label="Desde", options=[ft.dropdown.Option(k, v) for k, v in _meses],
        value="1", width=120,
    )
    sel_hasta = ft.Dropdown(
        label="Hasta", options=[ft.dropdown.Option(k, v) for k, v in _meses],
        value="12", width=120,
    )

    rankings_row = ft.Row(
        [
            _build_rank_card("Más Guardias", ft.Icons.TRENDING_UP, [], "total_guardias", PRIMARY_DARK),
            ft.Container(width=12),
            _build_rank_card("Menos Guardias", ft.Icons.TRENDING_DOWN, [], "total_guardias", SHIFT_DIURNO),
            ft.Container(width=12),
            _build_rank_card("Más Puntos", ft.Icons.LOCAL_FIRE_DEPARTMENT, [], "total_puntos", PRIMARY_DARK),
            ft.Container(width=12),
            _build_rank_card("Menos Puntos", ft.Icons.OUTLINED_FLAG, [], "total_puntos", SHIFT_DIURNO),
        ],
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.START,
        expand=True,
    )

    trend_card = _build_trend_card([])

    new_cards_row = ft.Row(
        [
            _build_rank_card("Top Nocturnas", ft.Icons.NIGHTS_STAY, [], "nocturnas", SHIFT_DIURNO),
            ft.Container(width=12),
            _build_rank_card("Top Fines de Semana", ft.Icons.WEEKEND, [], "finde", PRIMARY_DARK),
        ],
        spacing=0,
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    bottom_row = ft.Row(
        [
            trend_card,
            ft.Container(width=12),
            ft.Container(content=new_cards_row, expand=True, height=300),
        ],
        spacing=0,
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    content = ft.Column(
        [
            rankings_row,
            ft.Container(height=12),
            bottom_row,
        ],
        spacing=0,
        expand=True,
    )
    cont_scroll = ft.Container(content=content, expand=True, padding=ft.Padding(0, 4, 0, 0))

    async def cargar(e=None):
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.15)
        try:
            txt = sel_ano.value.strip()
            if len(txt) != 4:
                raise ValueError
            a = int(txt)
            m = int(sel_hasta.value)
            desde = int(sel_desde.value)
            if desde > m:
                raise ValueError
            n = m - desde + 1
        except Exception:
            barra_loading.visible = False
            page.update()
            return

        try:
            async with httpx.AsyncClient(timeout=15) as cl:
                token = get_token(page)
                r = await cl.get(
                    f"{URL_BACKEND}/estadisticas/{m}/{a}",
                    params={"meses": n},
                    headers={"Authorization": f"Bearer {token}"},
                )
                d = r.json()
        except Exception:
            barra_loading.visible = False
            page.update()
            return

        tops = d.get("tops", {})
        evolucion = d.get("evolucion_equidad", [])

        rankings_row.controls = [
            _build_rank_card("Más Guardias", ft.Icons.TRENDING_UP,
                             tops.get("mas_guardias", []), "total_guardias", PRIMARY_DARK),
            ft.Container(width=12),
            _build_rank_card("Menos Guardias", ft.Icons.TRENDING_DOWN,
                             tops.get("menos_guardias", []), "total_guardias", SHIFT_DIURNO),
            ft.Container(width=12),
            _build_rank_card("Más Puntos", ft.Icons.LOCAL_FIRE_DEPARTMENT,
                             tops.get("mas_puntos", []), "total_puntos", PRIMARY_DARK),
            ft.Container(width=12),
            _build_rank_card("Menos Puntos", ft.Icons.OUTLINED_FLAG,
                             tops.get("menos_puntos", []), "total_puntos", SHIFT_DIURNO),
        ]

        new_cards_row.controls = [
            _build_rank_card("Top Nocturnas", ft.Icons.NIGHTS_STAY,
                             tops.get("mas_nocturnos", []), "nocturnas", SHIFT_DIURNO),
            ft.Container(width=12),
            _build_rank_card("Top Fines de Semana", ft.Icons.WEEKEND,
                             tops.get("mas_finde", []), "finde", PRIMARY_DARK),
        ]

        trend_card.update_data(evolucion)

        barra_loading.visible = False
        page.update()

    def _on_filtro_change(e):
        page.run_task(cargar)

    btn_refresh = ft.FilledButton("Refrescar", icon=ft.Icons.REFRESH, on_click=_on_filtro_change)
    for dd in [sel_ano, sel_desde, sel_hasta]:
        dd.on_change = _on_filtro_change

    panel = ft.Stack(
        [
            ft.Column(
                expand=True,
                controls=[
                    module_header("Dashboard", "Métricas del período"),
                    ft.Divider(height=1, color=DIVIDER),
                    ft.Container(content=ft.Row([sel_ano, sel_desde, sel_hasta, btn_refresh])),
                    ft.Divider(height=1, color=DIVIDER),
                    cont_scroll,
                ],
            ),
            ft.Container(content=barra_loading, left=0, top=0, right=0),
        ],
        expand=True,
    )

    return {"panel": panel, "cargar": cargar}
