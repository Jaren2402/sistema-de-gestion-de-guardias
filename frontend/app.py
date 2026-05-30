import flet as ft
from ui.soldados import build as build_soldados
from ui.calendario import build as build_calendario
from ui.restricciones import build as build_restricciones

async def main(page: ft.Page):
    page.title = "Sistema de Guardias Militares"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    # Construir los módulos (cada uno devuelve un diccionario con su panel y funciones)
    # 1. Primero restricciones, para poder pasar su función de carga como callback
    mod_restricciones = build_restricciones(page)
    # 2. Luego soldados, conectando el evento de actualización
    mod_soldados = build_soldados(page, on_soldados_actualizados=mod_restricciones["cargar_dropdown"])
    # 3. Finalmente calendario
    mod_calendario = build_calendario(page)

    # Ensamblar las pestañas
    page.add(
        ft.Text("🪖 Gestión de Guardias", size=30, weight=ft.FontWeight.BOLD),
        ft.Tabs(
            selected_index=0,
            length=3,
            expand=True,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.TabBar(
                        tabs=[
                            ft.Tab(label=ft.Text("Soldados")),
                            ft.Tab(label=ft.Text("Calendario")),
                            ft.Tab(label=ft.Text("Restricciones")),
                        ]
                    ),
                    ft.TabBarView(
                        expand=True,
                        controls=[
                            mod_soldados["panel"],
                            mod_calendario["panel"],
                            mod_restricciones["panel"],
                        ]
                    ),
                ]
            ),
        ),
        ft.Divider(),
        mod_soldados["barra_progreso"],
        mod_soldados["texto_estado"],
    )

    # Inicializar datos al arrancar
    await mod_soldados["cargar"]()
    # Ya no llamamos a cargar_dropdown() aquí, se lanza solo desde restricciones.py
    await mod_restricciones["cargar_tabla"]()

ft.run(main)