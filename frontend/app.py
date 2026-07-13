import asyncio
import traceback

import flet as ft
import httpx
from config import URL_BACKEND
from theme import *
from ui.calendario import build as build_calendario
from ui.dashboard import build as build_dashboard
from ui.ficha import build as build_ficha
from ui.gestion_soldados import build as build_gestion_soldados
from ui.historial import build as build_historial
from ui.novedades import build as build_novedades
from ui.puntos_guardia import build as build_puntos
from ui.restricciones import build as build_restricciones
from ui.soldados import build as build_soldados
from ui.sustitucion import build as build_sustitucion


async def main(page: ft.Page):
    page.title = "Sistema de Guardias Militares"
    page.fonts = {
        "Inter": [
            "fonts/Inter-Regular.ttf",
            "fonts/Inter-Bold.ttf",
            "fonts/Inter-Medium.ttf",
            "fonts/Inter-SemiBold.ttf",
        ],
    }
    page.theme = ft.Theme(
        color_scheme_seed=PRIMARY,
        font_family=FONT_FAMILY,
        scrollbar_theme=ft.ScrollbarTheme(
            thickness=6,
            radius=3,
            thumb_color="#555555",
            track_color="#151515",
            interactive=True,
        ),
        filled_button_theme=ft.FilledButtonTheme(
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor={
                    "default": BTN_BG,
                    "hovered": BTN_HOVER,
                },
                text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
                padding=22,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
        ),
        text_button_theme=ft.TextButtonTheme(
            style=ft.ButtonStyle(
                color={
                    "default": TEXT_SECONDARY,
                    "hovered": BTN_TEXT,
                },
                bgcolor={"hovered": BTN_HOVER},
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        ),
        icon_button_theme=ft.IconButtonTheme(
            style=ft.ButtonStyle(
                color={
                    "default": TEXT_SECONDARY,
                    "hovered": BTN_TEXT,
                },
                bgcolor={"hovered": BTN_HOVER},
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        ),
    )
    page.theme.dropdown_theme = ft.DropdownTheme(text_style=ft.TextStyle(color=TEXT_SECONDARY))
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG
    page.padding = 0

    async def _construir_app():
        try:
            mod_restricciones = build_restricciones(page)
            mod_ficha = build_ficha(page)
            mod_gestion = build_gestion_soldados(page)
            mod_calendario = build_calendario(page)
            mod_puntos = build_puntos(page)
            mod_novedades = build_novedades(page)
            mod_sustitucion = build_sustitucion(page)
            mod_dashboard = build_dashboard(page)
            mod_historial = build_historial(page)

            async def on_soldados_actualizados():
                await mod_restricciones["cargar_dropdown"]()
                await mod_ficha["cargar_dropdown"]()
                await mod_gestion["cargar_tabla"]()

            is_extendido = True
            idx_anterior = 0

            async def _ir_a_panel(idx):
                nonlocal idx_anterior
                idx_anterior = idx
                nav_rail.selected_index = idx
                panel_wrapper.opacity = 0
                page.update()
                await asyncio.sleep(0.18)
                panel_scroll.controls.clear()
                panel_scroll.controls.append(paneles[idx]["panel"])
                panel_wrapper.opacity = 1
                page.update()
                if idx == 8:
                    await mod_dashboard["cargar"]()

            async def ver_ficha_por_id(id_soldado):
                import datetime as _dt
                now = _dt.datetime.now()
                await mod_ficha["cargar_para_soldado"](id_soldado, now.month, now.year)
                await _ir_a_panel(3)

            mod_soldados = build_soldados(page, on_soldados_actualizados=on_soldados_actualizados, on_ver_ficha=ver_ficha_por_id)

            paneles = [
                {"label": "Soldados", "icon": ft.Icons.PEOPLE_OUTLINED, "icon_sel": ft.Icons.PEOPLE, "panel": mod_soldados["panel"]},
                {"label": "Calendario", "icon": ft.Icons.CALENDAR_MONTH, "icon_sel": ft.Icons.CALENDAR_MONTH, "panel": mod_calendario["panel"]},
                {"label": "Restricciones", "icon": ft.Icons.BLOCK, "icon_sel": ft.Icons.BLOCK, "panel": mod_restricciones["panel"]},
                {"label": "Ficha", "icon": ft.Icons.BADGE, "icon_sel": ft.Icons.BADGE, "panel": mod_ficha["panel"]},
                {"label": "Gestión", "icon": ft.Icons.MANAGE_ACCOUNTS, "icon_sel": ft.Icons.MANAGE_ACCOUNTS, "panel": mod_gestion["panel"]},
                {"label": "Puntos", "icon": ft.Icons.LOCATION_ON, "icon_sel": ft.Icons.LOCATION_ON, "panel": mod_puntos["panel"]},
                {"label": "Novedades", "icon": ft.Icons.CAMPAIGN, "icon_sel": ft.Icons.CAMPAIGN, "panel": mod_novedades["panel"]},
                {"label": "Sustitución", "icon": ft.Icons.SWAP_HORIZ, "icon_sel": ft.Icons.SWAP_HORIZ, "panel": mod_sustitucion["panel"]},
                {"label": "Dashboard", "icon": ft.Icons.DASHBOARD, "icon_sel": ft.Icons.DASHBOARD, "panel": mod_dashboard["panel"]},
                {"label": "Historial", "icon": ft.Icons.HISTORY, "icon_sel": ft.Icons.HISTORY, "panel": mod_historial["panel"]},
            ]

            for p in paneles:
                panel = p["panel"]
                panel.expand = True
                panel.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
                stack = [panel]
                while stack:
                    ctrl = stack.pop()
                    if isinstance(ctrl, ft.DataTable):
                        for col in ctrl.columns:
                            col.expand = True
                    hijos = getattr(ctrl, 'controls', None)
                    if hijos:
                        stack.extend(hijos)
                    contenido = getattr(ctrl, 'content', None)
                    if contenido is not None:
                        stack.append(contenido)

            panel_scroll = ft.Column(
                controls=[paneles[0]["panel"]],
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
            panel_wrapper = ft.Container(
                content=panel_scroll,
                expand=True,
                opacity=1,
                animate_opacity=ft.Animation(180, ft.AnimationCurve.EASE_IN_OUT),
            )

            contenedor_contenido = ft.Container(
                content=panel_wrapper,
                padding=ft.Padding(left=20, top=16, right=20, bottom=16),
                expand=True,
                bgcolor=CONTENT_BG,
            )

            dests_paneles = [
                ft.NavigationRailDestination(
                    icon=p["icon"],
                    selected_icon=p["icon_sel"],
                    label=ft.Container(
                        content=ft.Text(p["label"], size=14),
                        padding=ft.Padding(left=12, top=0, right=0, bottom=0),
                    ),
                    padding=ft.Padding(top=12, bottom=12, left=8, right=8),
                ) for p in paneles
            ]

            dest_colapsar = ft.NavigationRailDestination(
                icon=ft.Icons.MENU_OPEN,
                label=ft.Container(
                    content=ft.Text("Colapsar", size=14),
                    padding=ft.Padding(left=12, top=0, right=0, bottom=0),
                ),
                padding=ft.Padding(top=12, bottom=12, left=8, right=8),
            )

            dest_cerrar = ft.NavigationRailDestination(
                icon=ft.Icons.LOGOUT,
                label=ft.Container(
                    content=ft.Text("Cerrar sesi\u00f3n", size=14),
                    padding=ft.Padding(left=12, top=0, right=0, bottom=0),
                ),
                padding=ft.Padding(top=12, bottom=12, left=8, right=8),
            )

            async def _on_nav_change(e):
                nonlocal idx_anterior
                idx = e.control.selected_index
                if idx >= len(paneles) + 1:
                    nav_rail.selected_index = idx_anterior
                    _toggle_sidebar(e)
                    return
                if idx == len(paneles):
                    nav_rail.selected_index = idx_anterior
                    await on_cerrar_sesion(e)
                    return
                idx_anterior = idx
                await _ir_a_panel(idx)

            def _toggle_sidebar(e):
                nonlocal is_extendido
                is_extendido = not is_extendido
                nav_rail.extended = is_extendido
                nav_rail.label_type = ft.NavigationRailLabelType.ALL if is_extendido else ft.NavigationRailLabelType.NONE
                dest_colapsar.icon = ft.Icons.MENU_OPEN if is_extendido else ft.Icons.MENU
                pad = 12
                pad_texto = 12 if is_extendido else 0
                for d in dests_paneles:
                    d.padding = ft.Padding(top=pad, bottom=pad, left=8, right=8)
                    d.label.padding = ft.Padding(left=pad_texto, top=0, right=0, bottom=0)
                dest_colapsar.padding = ft.Padding(top=pad, bottom=pad, left=8, right=8)
                dest_colapsar.label.padding = ft.Padding(left=pad_texto, top=0, right=0, bottom=0)
                dest_cerrar.padding = ft.Padding(top=pad, bottom=pad, left=8, right=8)
                dest_cerrar.label.padding = ft.Padding(left=pad_texto, top=0, right=0, bottom=0)
                page.update()

            nav_rail = ft.NavigationRail(
                selected_index=0,
                extended=is_extendido,
                min_width=56,
                min_extended_width=230,
                bgcolor="#121212",
                indicator_color=BTN_BG,
                label_type=ft.NavigationRailLabelType.ALL,
                use_indicator=True,
                indicator_shape=ft.RoundedRectangleBorder(radius=8),
                group_alignment=-0.2,
                expand=True,
                leading=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.SHIELD, color=PRIMARY, size=28),
                            ft.Text("GV", size=10, weight=ft.FontWeight.BOLD, color=PRIMARY),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                    ),
                    padding=ft.Padding(left=0, top=16, right=0, bottom=8),
                ),
                destinations=[*dests_paneles, dest_cerrar, dest_colapsar],
                on_change=_on_nav_change,
            )

            sidebar = ft.Container(
                content=nav_rail,
            )

            fila_principal = ft.Row(
                controls=[
                    sidebar,
                    contenedor_contenido,
                ],
                expand=True,
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            )

            app_body = ft.Container(
                content=fila_principal,
                expand=True,
                opacity=0,
                animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
            )
            page.add(app_body)
            page.update()
            await asyncio.sleep(0.05)
            app_body.opacity = 1
            page.update()

            page.run_task(mod_soldados["cargar"])
            page.run_task(mod_restricciones["cargar_tabla"])
            page.run_task(mod_restricciones["cargar_dropdown"])
            page.run_task(mod_ficha["cargar_dropdown"])
            page.run_task(mod_gestion["cargar_tabla"])
            page.run_task(mod_puntos["cargar_tabla"])
        except Exception as ex:
            page.add(ft.Container(
                ft.Text(f"Error: {ex}\n\n{traceback.format_exc()}",
                        color=ft.Colors.RED, size=14, selectable=True),
                padding=30, bgcolor="#111", expand=True))
            page.update()

    async def on_cerrar_sesion(e):
        token = page.session.store.get("session_token")
        if token:
            try:
                async with httpx.AsyncClient() as cli:
                    await cli.post(f"{URL_BACKEND}/logout", params={"token": token})
            except Exception:
                pass
        page.session.store.remove("session_token")
        page.controls.clear()
        from ui.login import login_screen
        page.add(login_screen(page, on_login_exitoso))
        page.update()

    async def on_login_exitoso(token, usuario):
        page.session.store.set("session_token", token)
        page.controls.clear()
        await _construir_app()
        page.update()

    token = page.session.store.get("session_token")
    sesion_valida = False
    if token:
        try:
            async with httpx.AsyncClient() as cli:
                resp = await cli.get(f"{URL_BACKEND}/verificar-sesion", params={"token": token})
                sesion_valida = resp.json().get("valido", False)
        except Exception:
            pass

    if not sesion_valida:
        from ui.login import login_screen
        page.add(login_screen(page, on_login_exitoso))
        page.update()
        return

    await _construir_app()

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=8501, host="0.0.0.0")
