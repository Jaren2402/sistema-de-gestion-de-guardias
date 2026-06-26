import flet as ft
import httpx
from config import URL_BACKEND


def build(page: ft.Page):
    texto_estado = ft.Text()
    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(str(m)) for m in range(1, 13)],
        value="5",
        width=120,
    )
    selector_año = ft.TextField(label="Año", value="2026", width=100)
    lista_historial = ft.Column()

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

        return ft.Container(
            content=ft.Row([
                ft.Container(width=5, bgcolor=borde_color),
                icono,
                ft.Column([
                    ft.Text(titulo, weight=ft.FontWeight.BOLD),
                    cuerpo,
                ]),
            ]),
            bgcolor=ft.Colors.GREY_900, border_radius=10, padding=15, margin=8,
        )

    # --- Función de carga ---
    async def cargar_historial(e=None):
        mes = int(selector_mes.value)
        año = int(selector_año.value)
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.get(f"{URL_BACKEND}/historial-sustituciones/{mes}/{año}")
                datos = resp.json()
                lista_historial.controls.clear()

                if not datos:
                    lista_historial.controls.append(
                        ft.Text("No hay sustituciones registradas en este mes.", italic=True, color=ft.Colors.GREY_500)
                    )
                else:
                    for item in datos:
                        lista_historial.controls.append(_tarjeta_historial(item))

                texto_estado.value = f"Se encontraron {len(datos)} sustituciones."
                texto_estado.color = ft.Colors.GREEN
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    # --- Construcción del panel ---
    boton_actualizar = ft.Button("Actualizar", on_click=cargar_historial, icon=ft.Icons.REFRESH)

    panel = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Historial de Sustituciones", weight=ft.FontWeight.BOLD, size=20),
            ft.Row([selector_mes, selector_año, boton_actualizar]),
            ft.Divider(),
            texto_estado,
            ft.Divider(),
            lista_historial,
        ]
    )

    return {"panel": panel}