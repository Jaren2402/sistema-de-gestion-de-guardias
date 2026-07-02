import flet as ft
from ui.soldados import build as build_soldados
from ui.calendario import build as build_calendario
from ui.restricciones import build as build_restricciones
from ui.ficha import build as build_ficha
from ui.gestion_soldados import build as build_gestion_soldados
from ui.puntos_guardia import build as build_puntos
from ui.novedades import build as build_novedades
from ui.sustitucion import build as build_sustitucion
from ui.dashboard import build as build_dashboard
from ui.historial import build as build_historial

async def main(page: ft.Page):
    page.title = "Sistema de Guardias Militares"
    # page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#12161A"
    page.theme_mode = ft.Theme(font_family="Tahoma")
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

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

    # Ensamblar las pestañas
    page.add(
        ft.Text("🪖 Gestión de Guardias", size=30, weight=ft.FontWeight.BOLD),
        ft.Tabs(
            selected_index=0,
            length=10,
            expand=True,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.TabBar(
                        tabs=[
                            ft.Tab(label=ft.Text("Soldados")),
                            ft.Tab(label=ft.Text("Calendario")),
                            ft.Tab(label=ft.Text("Restricciones")),
                            ft.Tab(label=ft.Text("Ficha")), 
                            ft.Tab(label=ft.Text("Gestión")),
                            ft.Tab(label=ft.Text("Puntos")),
                            ft.Tab(label=ft.Text("Novedades")),
                            ft.Tab(label=ft.Text("Sustitución")),
                            ft.Tab(label=ft.Text("Dashboard")),
                            ft.Tab(label=ft.Text("Historial")),
                        ]
                    ),
                    ft.TabBarView(
                        expand=True,
                        controls=[
                            mod_soldados["panel"],
                            mod_calendario["panel"],
                            mod_restricciones["panel"],
                            mod_ficha["panel"],  
                            mod_gestion["panel"],
                            mod_puntos["panel"],
                            mod_novedades["panel"],
                            mod_sustitucion["panel"],
                            mod_dashboard["panel"],
                            mod_historial["panel"],
                        ]
                    ),
                ]
            ),
        ),
        ft.Divider(),
        mod_soldados["barra_progreso"],
        mod_soldados["texto_estado"],
    )

    await mod_soldados["cargar"]()
    await mod_restricciones["cargar_tabla"]()

ft.run(main)