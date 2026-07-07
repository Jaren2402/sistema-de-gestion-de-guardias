import flet as ft
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
    page.theme = ft.Theme(font_family="Tahoma")
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#12161A"
    page.padding = 0

    # Construir los módulos
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

    mod_soldados = build_soldados(page, on_soldados_actualizados=on_soldados_actualizados)

    # Definición de paneles
    paneles = [
        {"label": "Soldados",     "icon": ft.Icons.PEOPLE_OUTLINED,   "icon_sel": ft.Icons.PEOPLE,            "panel": mod_soldados["panel"]},
        {"label": "Calendario",   "icon": ft.Icons.CALENDAR_MONTH,    "icon_sel": ft.Icons.CALENDAR_MONTH,     "panel": mod_calendario["panel"]},
        {"label": "Restricciones","icon": ft.Icons.BLOCK,             "icon_sel": ft.Icons.BLOCK,              "panel": mod_restricciones["panel"]},
        {"label": "Ficha",        "icon": ft.Icons.BADGE,             "icon_sel": ft.Icons.BADGE,              "panel": mod_ficha["panel"]},
        {"label": "Gestión",      "icon": ft.Icons.MANAGE_ACCOUNTS,   "icon_sel": ft.Icons.MANAGE_ACCOUNTS,    "panel": mod_gestion["panel"]},
        {"label": "Puntos",       "icon": ft.Icons.LOCATION_ON,       "icon_sel": ft.Icons.LOCATION_ON,        "panel": mod_puntos["panel"]},
        {"label": "Novedades",    "icon": ft.Icons.CAMPAIGN,          "icon_sel": ft.Icons.CAMPAIGN,           "panel": mod_novedades["panel"]},
        {"label": "Sustitución",  "icon": ft.Icons.SWAP_HORIZ,        "icon_sel": ft.Icons.SWAP_HORIZ,         "panel": mod_sustitucion["panel"]},
        {"label": "Dashboard",    "icon": ft.Icons.DASHBOARD,         "icon_sel": ft.Icons.DASHBOARD,          "panel": mod_dashboard["panel"]},
        {"label": "Historial",    "icon": ft.Icons.HISTORY,           "icon_sel": ft.Icons.HISTORY,            "panel": mod_historial["panel"]},
    ]

    # Forzar que los paneles expandan y las tablas llenen el ancho disponible
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

    title_text = ft.Text("Soldados", size=20, weight=ft.FontWeight.BOLD, color="#E0E0E0")

    # Área de contenido
    contenedor_contenido = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=title_text,
                    padding=ft.Padding(left=0, top=4, right=0, bottom=4),
                ),
                ft.Divider(height=1, color="#2A2F35"),
                panel_scroll,
            ],
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        padding=ft.Padding(left=20, top=16, right=20, bottom=16),
        expand=True,
        bgcolor="#161A1E",
    )

    is_extendido = True
    idx_anterior = 0

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

    def _on_nav_change(e):
        nonlocal idx_anterior
        idx = e.control.selected_index
        if idx >= len(paneles):
            nav_rail.selected_index = idx_anterior
            _toggle_sidebar(e)
            return
        idx_anterior = idx
        title_text.value = paneles[idx]["label"]
        panel_scroll.controls.clear()
        panel_scroll.controls.append(paneles[idx]["panel"])
        page.update()

    def _toggle_sidebar(e):
        nonlocal is_extendido
        is_extendido = not is_extendido
        nav_rail.extended = is_extendido
        dest_colapsar.icon = ft.Icons.MENU_OPEN if is_extendido else ft.Icons.MENU
        pad = 12 if is_extendido else 8
        pad_texto = 12 if is_extendido else 0
        for d in dests_paneles:
            d.padding = ft.Padding(top=pad, bottom=pad, left=8, right=8)
            d.label.padding = ft.Padding(left=pad_texto, top=0, right=0, bottom=0)
        dest_colapsar.padding = ft.Padding(top=pad, bottom=pad, left=8, right=8)
        dest_colapsar.label.padding = ft.Padding(left=pad_texto, top=0, right=0, bottom=0)
        page.update()

    nav_rail = ft.NavigationRail(
        selected_index=0,
        extended=is_extendido,
        min_width=56,
        min_extended_width=200,
        bgcolor="#1A1E24",
        indicator_color="#4CAF50",
        label_type=ft.NavigationRailLabelType.ALL,
        use_indicator=True,
        indicator_shape=ft.RoundedRectangleBorder(radius=8),
        group_alignment=-0.2,
        expand=True,
        leading=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.SHIELD, color="#4CAF50", size=28),
                    ft.Text("GV", size=10, weight=ft.FontWeight.BOLD, color="#4CAF50"),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
            ),
            padding=ft.Padding(left=0, top=16, right=0, bottom=8),
        ),
        destinations=[*dests_paneles, dest_colapsar],
        on_change=_on_nav_change,
    )

    # Sidebar (solo el NavigationRail envuelto en un Container)
    sidebar = ft.Container(
        content=nav_rail,
        bgcolor="#1A1E24",
    )

    # Layout principal
    fila_principal = ft.Row(
        controls=[
            sidebar,
            ft.VerticalDivider(width=1, color="#3A3F45"),
            contenedor_contenido,
        ],
        expand=True,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    # Pie
    footer = ft.Container(
        content=ft.Column([
            mod_soldados["barra_progreso"],
            mod_soldados["texto_estado"],
        ]),
        padding=ft.Padding(left=20, top=5, right=20, bottom=10),
    )

    page.add(fila_principal, footer)

    await mod_soldados["cargar"]()
    await mod_restricciones["cargar_tabla"]()

ft.run(main)
