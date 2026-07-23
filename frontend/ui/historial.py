import asyncio
from datetime import datetime

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import loading_bar, module_header, no_data, toast
from theme import *


def build(page: ft.Page):
    barra_loading = loading_bar()
    _todos_los_registros = []

    selector_mes = ft.Dropdown(
        label="Mes", expand=False, width=130,
        options=[ft.dropdown.Option(MESES[i]) for i in range(12)],
        value=MESES[datetime.now().month - 1],
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY,
    )
    selector_ano = ft.TextField(label="Año", value=str(datetime.now().year), width=100,
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY, cursor_color=PRIMARY,
    )

    search_field = ft.TextField(
        label="Buscar por nombre, cédula o motivo…",
        expand=True, height=42,
        prefix_icon=ft.Icons.SEARCH,
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY,
        cursor_color=PRIMARY,
        on_change=lambda e: _filtrar(),
    )

    no_data_container = no_data(ft.Icons.HISTORY, "No hay sustituciones registradas este mes")

    resultados_container = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    def _filtrar(e=None):
        texto_busqueda = (search_field.value or "").strip().lower()
        registros = _todos_los_registros
        if texto_busqueda:
            registros = [
                r for r in registros
                if texto_busqueda in str(r.get("texto_trueque", "")).lower()
                or texto_busqueda in str(r.get("titular_original", "")).lower()
                or texto_busqueda in str(r.get("sustituto", "")).lower()
                or texto_busqueda in str(r.get("cedula_sustituto", "")).lower()
                or texto_busqueda in str(r.get("motivo", "")).lower()
                or texto_busqueda in str(r.get("fecha", "")).lower()
                or texto_busqueda in str(r.get("punto", "")).lower()
            ]
        _renderizar(registros)

    def _renderizar(registros):
        resultados_container.controls.clear()
        no_data_container.visible = not registros
        if registros:
            total_trueques = sum(1 for r in registros if r.get("tipo") == "Trueque")
            total_simples = len(registros) - total_trueques
            badge_trueque = ft.Container(
                content=ft.Text(f"{total_trueques} trueques", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                bgcolor=SHIFT_DIURNO, border_radius=4, padding=ft.Padding(10, 4, 10, 4))
            badge_simple = ft.Container(
                content=ft.Text(f"{total_simples} sustituciones", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                bgcolor=BTN_BG, border_radius=4, padding=ft.Padding(10, 4, 10, 4))
            resultados_container.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.INSERT_CHART_OUTLINED, size=20, color=PRIMARY),
                        ft.Text("Resumen", size=14, weight=ft.FontWeight.BOLD, color=TEXT),
                        badge_trueque,
                        badge_simple,
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.Padding(14, 10, 14, 10),
                ))
            resultados_container.controls.append(ft.Divider(height=1, color=DIVIDER))
        cards = [_tarjeta_historial(item) for item in registros]
        for i in range(0, len(cards), 2):
            row_cards = cards[i:i+2]
            if len(row_cards) == 1:
                row_cards.append(ft.Container(expand=True))
            resultados_container.controls.append(ft.Row(row_cards, spacing=16, expand=True))
            resultados_container.controls.append(ft.Container(height=16))

    def _tarjeta_historial(item):
        if item["tipo"] == "Trueque":
            badge_bg = SHIFT_DIURNO
            badge_text = "TRUEQUE"
            icono = ft.Icons.SWAP_HORIZ
            icono_color = SHIFT_DIURNO
            titulo = f'{item["fecha"]}  ·  {item["turno"].capitalize()}  ·  {item["punto"]}'
            sub_lineas = [
                ft.Text(item.get("texto_trueque", ""), size=15, color=TEXT_TABLE),
            ]
            if item.get("motivo"):
                sub_lineas.append(ft.Container(height=2))
                sub_lineas.append(ft.Row([
                    ft.Icon(ft.Icons.DESCRIPTION, size=14, color=TEXT_SECONDARY),
                    ft.Text(item["motivo"], size=14, color=TEXT_SECONDARY, italic=True),
                ], spacing=6))
        else:
            badge_bg = BTN_BG
            badge_text = "SUSTITUCIÓN"
            icono = ft.Icons.REPLACE_TRAIL
            icono_color = BTN_BG
            titulo = f'{item["fecha"]}  ·  {item["turno"].capitalize()}  ·  {item["punto"]}'
            sub_lineas = [
                ft.Row([
                    ft.Text("Titular: ", size=14, color=TEXT_SECONDARY),
                    ft.Text(item["titular_original"], size=15, color=TEXT_TABLE),
                ], spacing=4),
                ft.Row([
                    ft.Text("Sustituto: ", size=14, color=TEXT_SECONDARY),
                    ft.Text(item["sustituto"], size=15, color=TEXT_TABLE),
                ], spacing=4),
            ]
            if item.get("cedula_sustituto"):
                sub_lineas.append(ft.Text(f"C.I. {item['cedula_sustituto']}", size=14, color=TEXT_SECONDARY))
            if item.get("motivo"):
                sub_lineas.append(ft.Container(height=2))
                sub_lineas.append(ft.Row([
                    ft.Icon(ft.Icons.DESCRIPTION, size=14, color=TEXT_SECONDARY),
                    ft.Text(item["motivo"], size=14, color=TEXT_SECONDARY, italic=True),
                ], spacing=6))

        card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(icono, size=20, color=icono_color),
                    ft.Text(titulo, size=15, weight=ft.FontWeight.BOLD, color=TEXT),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Text(badge_text, size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor=badge_bg, border_radius=4, padding=ft.Padding(10, 4, 10, 4),
                    ),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=1, color=DIVIDER),
                ft.Column(sub_lineas, spacing=6, expand=True),
            ], spacing=8, expand=True),
            bgcolor=SURFACE,
            border_radius=12,
            padding=ft.Padding(16, 14, 16, 14),
            height=120,
            expand=True,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        )

        def _on_hover(e):
            if e.data:
                card.bgcolor = HOVER_ROW_BG
                card.shadow = [ft.BoxShadow(blur_radius=10, color="#000000", spread_radius=1, offset=ft.Offset(0, 3))]
                card.scale = ft.Scale(1.01)
            else:
                card.bgcolor = SURFACE
                card.shadow = []
                card.scale = ft.Scale(1.0)
            card.update()

        card.on_hover = _on_hover
        return card

    async def cargar_historial(e=None):
        mes = MESES.index(selector_mes.value) + 1
        ano = int(selector_ano.value)
        barra_loading.visible = True
        resultados_container.controls.clear()
        no_data_container.visible = False
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.get(f"{URL_BACKEND}/historial-sustituciones/{mes}/{ano}", headers={"Authorization": f"Bearer {token}"})
                datos = resp.json()
                nonlocal _todos_los_registros
                _todos_los_registros = datos if datos else []
                _filtrar()
        except Exception:
            toast(page, "Error al cargar el historial.", "error")
        finally:
            barra_loading.visible = False
            page.update()

    form_card = ft.Container(
        content=ft.Row([
            selector_mes,
            selector_ano,
            search_field,
            ft.FilledButton(
                "Cargar", on_click=lambda e: page.run_task(cargar_historial),
                icon=ft.Icons.REFRESH, style=ft.ButtonStyle(bgcolor=BTN_BG, color=BTN_TEXT),
            ),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        padding=ft.Padding(16, 16, 16, 16),
    )

    panel = ft.Column(
        [
            barra_loading,
            module_header("Historial", "Registro de sustituciones y trueques"),
            ft.Divider(height=1, color=DIVIDER),
            form_card,
            ft.Container(height=8),
            resultados_container,
            no_data_container,
        ],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    page.run_task(cargar_historial)

    return {"panel": panel}
