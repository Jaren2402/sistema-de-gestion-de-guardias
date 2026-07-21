import asyncio

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import loading_bar, module_header
from theme import *


def _rank_color(i: int) -> str:
    return ["#FFD700", "#C0C0C0", "#CD7F32", "#555555", "#444444"][i]


def _build_rank_item(pos: int, nombre: str, valor: int):
    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Text(str(pos), size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
                width=24, height=24,
                bgcolor=_rank_color(pos - 1),
                border_radius=12,
                alignment=ft.Alignment(0, 0),
            ),
            ft.Text(nombre, size=13, color=TEXT, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(str(valor), size=13, weight=ft.FontWeight.BOLD, color=TEXT),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=34,
    )


def _build_rank_column(titulo: str, items: list, clave: str = "total_guardias"):
    rows = []
    for i, item in enumerate(items):
        rows.append(_build_rank_item(i + 1, item["nombre"], item.get(clave, 0)))
    return ft.Column([
        ft.Text(titulo, size=13, weight=ft.FontWeight.BOLD, color=TEXT_SECONDARY),
        ft.Divider(height=1, color=DIVIDER),
        *rows,
    ], spacing=2, expand=True)


def _mini_card(icon: str, titulo: str, items: list, clave: str):
    rows = []
    for i, item in enumerate(items[:5]):
        rows.append(_build_rank_item(i + 1, item["nombre"], item.get(clave, 0)))
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(icon, size=16, color=PRIMARY),
                ft.Text(titulo, size=13, weight=ft.FontWeight.BOLD, color=TEXT),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(height=1, color=DIVIDER),
            *rows,
        ], spacing=2),
        bgcolor=SURFACE, border_radius=20,
        border=ft.Border(bottom=ft.BorderSide(1, "#222222")),
        padding=ft.Padding(20, 20, 20, 14),
        expand=True,
    )


def build(page: ft.Page):
    barra_loading = loading_bar()

    sel_ano = ft.TextField(label="Año", value="2026", width=100)
    _meses = [
        ("1", "Enero"), ("2", "Febrero"), ("3", "Marzo"),
        ("4", "Abril"), ("5", "Mayo"), ("6", "Junio"),
        ("7", "Julio"), ("8", "Agosto"), ("9", "Septiembre"),
        ("10", "Octubre"), ("11", "Noviembre"), ("12", "Diciembre"),
    ]
    sel_desde = ft.Dropdown(label="Desde", options=[ft.dropdown.Option(k, v) for k, v in _meses], value="1", width=120)
    sel_hasta = ft.Dropdown(label="Hasta", options=[ft.dropdown.Option(k, v) for k, v in _meses], value="12", width=120)

    # ======================= EQUITY RING =======================
    ring_size = 130
    txt_pct = ft.Text("—", size=34, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    ring = ft.ProgressRing(value=None, stroke_width=14, color=PRIMARY, bgcolor=SURFACE_LIGHT, width=ring_size, height=ring_size)

    ring_stack = ft.Stack([
        ring,
        ft.Container(content=txt_pct, alignment=ft.Alignment(0, 0), width=ring_size, height=ring_size),
    ], width=ring_size, height=ring_size)

    txt_label_equidad = ft.Text("Equidad del período", size=14, color=TEXT_SECONDARY)
    txt_diff = ft.Text("", size=12, color="#34A853")
    txt_sobrecargado = ft.Text("", size=12, color=TEXT_SECONDARY)
    txt_equidad_sub = ft.Text("", size=12, color=TEXT_SECONDARY)

    equity_card = ft.Container(
        content=ft.Column([
            ring_stack,
            txt_label_equidad,
            txt_equidad_sub,
            txt_diff,
            ft.Divider(height=1, color=DIVIDER),
            txt_sobrecargado,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
        bgcolor=SURFACE, border_radius=20,
        border=ft.Border(bottom=ft.BorderSide(1, "#222222")),
        padding=ft.Padding(20, 20, 20, 14),
        expand=True,
    )

    # ======================= RANKINGS =======================
    col_mas = _build_rank_column("Más guardias", [], "total_guardias")
    col_menos = _build_rank_column("Menos guardias", [], "total_guardias")

    def _card_rank(col: ft.Column) -> ft.Container:
        return ft.Container(
            content=col,
            bgcolor=SURFACE, border_radius=20,
            border=ft.Border(bottom=ft.BorderSide(1, "#222222")),
            padding=ft.Padding(20, 20, 20, 14),
            expand=True,
        )
    card_mas = _card_rank(col_mas)
    card_menos = _card_rank(col_menos)

    # ======================= MINI CARDS =======================
    mini_nocturnas = _mini_card(ft.Icons.DARK_MODE, "Más nocturnas", [], "nocturnas")
    mini_finde = _mini_card(ft.Icons.WEEKEND, "Más finde", [], "finde")
    mini_puntos = _mini_card(ft.Icons.LOCAL_FIRE_DEPARTMENT, "Más puntos fatiga", [], "total_puntos")

    # ======================= MAIN CONTENT =======================
    content = ft.Column([
        ft.Row([
            equity_card,
            ft.Container(width=10),
            card_mas,
            ft.Container(width=10),
            card_menos,
            ft.Container(width=10),
            mini_puntos,
        ], vertical_alignment=ft.CrossAxisAlignment.START),
        ft.Container(height=12),
        ft.Row([
            mini_nocturnas,
            ft.Container(width=12),
            mini_finde,
        ]),
    ], spacing=0)

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
                r = await cl.get(f"{URL_BACKEND}/estadisticas/{m}/{a}", params={"meses": n}, headers={"Authorization": f"Bearer {token}"})
                d = r.json()
        except Exception:
            txt_pct.value = "—"
            ring.value = None
            ring.color = PRIMARY
            txt_diff.value = ""
            txt_sobrecargado.value = "Error al cargar datos"
            txt_equidad_sub.value = ""
            barra_loading.visible = False
            page.update()
            return

        # --- Equity ring ---
        eq = d.get("equidad", {})
        pct = eq.get("porcentaje", 0)
        txt_pct.value = f"{pct:.0f}%"
        ring.value = pct / 100
        if pct >= 80:
            ring.color = PRIMARY
        elif pct >= 60:
            ring.color = PRIMARY_DARK
        else:
            ring.color = ERROR

        # --- vs previous month ---
        evol = d.get("evolucion_equidad", [])
        if len(evol) >= 2:
            diff = evol[-1]["porcentaje"] - evol[-2]["porcentaje"]
            if diff > 0:
                txt_diff.value = f"▲ +{diff:.1f}% vs mes anterior"
                txt_diff.color = "#34A853"
            elif diff < 0:
                txt_diff.value = f"▼ {diff:.1f}% vs mes anterior"
                txt_diff.color = ERROR
            else:
                txt_diff.value = "→ Sin cambio vs mes anterior"
                txt_diff.color = TEXT_SECONDARY
        else:
            txt_diff.value = ""

        # --- Equidad subtitle (max-min) ---
        dif = eq.get("diferencia_max_min", 0)
        max_p = eq.get("max_puntos", 0)
        txt_equidad_sub.value = f"Diferencia: {dif} pts  ·  Máx: {max_p} pts"
        txt_equidad_sub.color = TEXT_SECONDARY

        # --- Sobrecargado ---
        sc = d.get("sobrecargado", {})
        if sc and sc.get("nombre"):
            txt_sobrecargado.value = f"Sobrecargado: {sc['nombre']} ({sc['total_puntos']} pts)"
        else:
            txt_sobrecargado.value = ""

        # --- Rankings ---
        tops = d.get("tops", {})
        _update_rank_col(col_mas, tops.get("mas_guardias", []), "total_guardias")
        _update_rank_col(col_menos, tops.get("menos_guardias", []), "total_guardias")

        # --- Mini cards ---
        _update_mini_card(mini_nocturnas, tops.get("mas_nocturnos", []), "nocturnas")
        _update_mini_card(mini_finde, tops.get("mas_finde", []), "finde")
        _update_mini_card(mini_puntos, tops.get("mas_puntos", []), "total_puntos")
        barra_loading.visible = False
        page.update()

    def _on_filtro_change(e):
        page.run_task(cargar)

    btn_refresh = ft.FilledButton("Refrescar", icon=ft.Icons.REFRESH, on_click=_on_filtro_change)
    for dd in [sel_ano, sel_desde, sel_hasta]:
        dd.on_change = _on_filtro_change

    panel = ft.Stack([
        ft.Column(expand=True, controls=[
            module_header("Dashboard", "Métricas del período"),
            ft.Divider(height=1, color=DIVIDER),
            ft.Container(content=ft.Row([sel_ano, sel_desde, sel_hasta, btn_refresh])),
            ft.Divider(height=1, color=DIVIDER),
            cont_scroll,
        ]),
        ft.Container(content=barra_loading, left=0, top=0, right=0),
    ], expand=True)

    return {"panel": panel, "cargar": cargar}


def _update_rank_col(col: ft.Column, items: list, clave: str):
    controls = [
        ft.Text(col.controls[0].value, size=13, weight=ft.FontWeight.BOLD, color=TEXT_SECONDARY),
        ft.Divider(height=1, color=DIVIDER),
    ]
    for i, item in enumerate(items):
        controls.append(_build_rank_item(i + 1, item["nombre"], item.get(clave, 0)))
    col.controls = controls


def _update_mini_card(card: ft.Container, items: list, clave: str):
    body = card.content
    body.controls[2:] = []
    for i, item in enumerate(items[:5]):
        body.controls.append(_build_rank_item(i + 1, item["nombre"], item.get(clave, 0)))
