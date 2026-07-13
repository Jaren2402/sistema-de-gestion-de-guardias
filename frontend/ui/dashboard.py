import asyncio

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import loading_bar, module_header
from theme import *


def build(page: ft.Page):
    barra_loading = loading_bar()

    sel_ano = ft.TextField(label="A\u00f1o", value="2026", width=100)
    _meses = [
        ("1", "Enero"), ("2", "Febrero"), ("3", "Marzo"),
        ("4", "Abril"), ("5", "Mayo"), ("6", "Junio"),
        ("7", "Julio"), ("8", "Agosto"), ("9", "Septiembre"),
        ("10", "Octubre"), ("11", "Noviembre"), ("12", "Diciembre"),
    ]
    sel_desde = ft.Dropdown(
        label="Desde",
        options=[ft.dropdown.Option(k, v) for k, v in _meses],
        value="1", width=120,
    )
    sel_hasta = ft.Dropdown(
        label="Hasta",
        options=[ft.dropdown.Option(k, v) for k, v in _meses],
        value="12", width=120,
    )

    # ============================================================
    # Circular progress controls
    # ============================================================
    txt_pct = ft.Text("—", size=34, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)

    w = 140
    circulo = ft.ProgressRing(
        value=None,
        stroke_width=14,
        color=PRIMARY,
        bgcolor=SURFACE_LIGHT,
        width=w,
        height=w,
    )

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
            async with httpx.AsyncClient() as cl:
                token = get_token(page)
                r = await cl.get(f"{URL_BACKEND}/estadisticas/{m}/{a}", params={"meses": n, "token": token})
                d = r.json()
            eq = d.get("equidad", {})
            pct = eq.get("porcentaje", 0)

            txt_pct.value = f"{pct:.0f}%"
            circulo.value = pct / 100

            if pct >= 80:
                circulo.color = PRIMARY
            elif pct >= 60:
                circulo.color = PRIMARY_DARK
            else:
                circulo.color = ERROR

        except Exception:
            txt_pct.value = "\u2014"
            circulo.value = None
            circulo.color = PRIMARY
        finally:
            barra_loading.visible = False
            page.update()

    def _on_filtro_change(e):
        page.run_task(cargar, e)

    btn_refresh = ft.FilledButton(
        "Refrescar",
        icon=ft.Icons.REFRESH,
        on_click=_on_filtro_change,
    )

    for dd in [sel_ano, sel_desde, sel_hasta]:
        dd.on_change = _on_filtro_change

    # ============================================================
    # Card
    # ============================================================
    card = ft.Container(
        content=ft.Stack([
            circulo,
            ft.Container(
                content=txt_pct,
                alignment=ft.Alignment(0, 0),
                width=w,
                height=w,
            ),
        ], width=w, height=w),
        width=200,
        height=200,
        alignment=ft.Alignment(0, 0),
        bgcolor=SURFACE,
        border=ft.Border(bottom=ft.BorderSide(1, "#222222")),
        border_radius=20,
    )

    # ============================================================
    # Layout
    # ============================================================
    panel = ft.Stack([
        ft.Column(expand=True, controls=[
            module_header("Dashboard", "M\u00e9tricas del per\u00edodo"),
            ft.Divider(height=1, color=DIVIDER),
            ft.Container(
                content=ft.Row([
                    sel_ano, sel_desde, sel_hasta, btn_refresh,
                ]),
            ),
            ft.Divider(height=1, color=DIVIDER),
            ft.Container(
                expand=1,
                content=ft.Row(
                    controls=[card],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ),
        ]),
        ft.Container(content=barra_loading, left=0, top=0, right=0),
    ], expand=True)

    return {"panel": panel, "cargar": cargar}
