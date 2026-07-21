import asyncio

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import hover_row, loading_bar, module_header, placeholder
from theme import *


def build(page: ft.Page):
    """Construye el historial de sustituciones: registro de todos los cambios realizados."""
    barra_loading = loading_bar()
    texto_estado = ft.Text()
    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(MESES[i]) for i in range(12)],
        value=MESES[4],
        width=120,
    )
    selector_año = ft.TextField(label="Año", value="2026", width=100)
    lista_historial = ft.Column(controls=[placeholder(ft.Icons.HISTORY, "Seleccione un mes y presione 'Actualizar'")])

    # --- Función para crear tarjetas de auditoría ---
    def _tarjeta_historial(item):
        """Crea una tarjeta visual para una sustitución (simple o trueque)."""
        if item["tipo"] == "Trueque":
            borde_color = ft.Colors.ORANGE
            icono = ft.Icon(ft.Icons.SWAP_HORIZ, color=ft.Colors.ORANGE, size=28)
            titulo = f"Trueque — {item['fecha']} · {item['turno'].capitalize()} · {item['punto']}"
            cuerpo = ft.Column([
                ft.Text(item["texto_trueque"], weight=ft.FontWeight.BOLD, size=16),
                ft.Text("Trueque registrado.", size=12, color=ft.Colors.GREY_400),
            ])

        else:
            # Sustitución Simple
            borde_color = ft.Colors.RED
            icono = ft.Icon(ft.Icons.WARNING, color=ft.Colors.RED, size=28)
            titulo = f"Sustitución Simple — {item['fecha']} · {item['turno'].capitalize()} · {item['punto']}"
            cuerpo = ft.Column([
                ft.Text(f"Titular: {item['titular_original']}", weight=ft.FontWeight.BOLD),
                ft.Text(f"Sustituto: {item['sustituto']}"),
                ft.Text(f"Cédula sustituto: {item['cedula_sustituto']}", size=12, color=ft.Colors.GREY_400),
            ])

        return hover_row(ft.Container(
            content=ft.Row([
                ft.Container(width=5, bgcolor=borde_color),
                icono,
                ft.Column([
                    ft.Text(titulo, weight=ft.FontWeight.BOLD),
                    cuerpo,
                ]),
            ]),
            bgcolor=SURFACE, border_radius=10, padding=15, margin=8,
        ))

    # --- Función de carga ---
    async def cargar_historial(e=None):
        mes = MESES.index(selector_mes.value) + 1
        año = int(selector_año.value)
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.get(f"{URL_BACKEND}/historial-sustituciones/{mes}/{año}", headers={"Authorization": f"Bearer {token}"})
                datos = resp.json()
                lista_historial.controls.clear()

                if not datos:
                    lista_historial.controls.append(
                        ft.Text("No hay sustituciones registradas en este mes.", italic=True, color=ft.Colors.GREY_500)
                    )
                else:
                    for item in datos:
                        lista_historial.controls.append(_tarjeta_historial(item))

                texto_estado.value = ""
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            barra_loading.visible = False
            page.update()

    # --- Construcción del panel ---
    boton_actualizar = ft.FilledButton("Actualizar", on_click=cargar_historial, icon=ft.Icons.REFRESH)

    panel = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        controls=[
            barra_loading,
            module_header("Historial", "Sustituciones y cambios registrados en el sistema"),
            ft.Divider(height=1, color=DIVIDER),
            ft.Row([selector_mes, selector_año, boton_actualizar]),
            ft.Divider(height=1, color=DIVIDER),
            texto_estado,
            ft.Divider(height=1, color=DIVIDER),
            lista_historial,
        ]
    )

    return {"panel": panel}
