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

    # ======================================================
    # 1. KPIs (Tarjetas de resumen)
    # ======================================================
    def _kpi(titulo, icono, color_icono):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icono, size=32, color=color_icono),
                ft.Column([
                    ft.Text(titulo.upper(), color=ft.Colors.GREY_400, size=12),
                    ft.Text("0", size=28, weight=ft.FontWeight.BOLD),
                ], alignment=ft.MainAxisAlignment.CENTER),
            ]),
            bgcolor=ft.Colors.GREY_900, padding=20, border_radius=15, width=200, height=90,
        )

    kpi_total = _kpi("Total Guardias", ft.Icons.ASSIGNMENT, ft.Colors.BLUE)
    kpi_sustituciones = _kpi("Sustituciones", ft.Icons.SWAP_HORIZ, ft.Colors.ORANGE)
    kpi_restricciones = _kpi("Restricciones", ft.Icons.BLOCK, ft.Colors.RED)

    # ======================================================
    # 2. Indicador de Equidad (Anillo con porcentaje dentro, label abajo)
    # ======================================================
    anillo_equidad = ft.ProgressRing(
        width=180, height=180, stroke_width=15, value=0.0,
        color=ft.Colors.GREEN, bgcolor=ft.Colors.GREY_800,
    )
    texto_pct_equidad = ft.Text("0%", size=40, weight=ft.FontWeight.BOLD)
    label_equidad = ft.Text("Índice de Equidad", weight=ft.FontWeight.BOLD, size=16)

    # Stack para poner el porcentaje DENTRO del anillo (ajustar alignment si hace falta)
    bloque_equidad = ft.Stack(
        controls=[
            anillo_equidad,
            ft.Container(
                content=texto_pct_equidad,
                alignment=ft.Alignment(0, -0.1),
                width=180,
                height=180,
            ),
        ],
        width=180,
        height=180,
    )

    # ======================================================
    # 3. Rankings (Tarjetas de podio)
    # ======================================================
    def _tarjeta_podio(soldado, color_icono, icono, metrica_label, metrica_valor):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icono, color=color_icono, size=30),
                ft.Column([
                    ft.Text(soldado["nombre"], weight=ft.FontWeight.BOLD, size=13),
                    ft.Text(f"{soldado['rango']} · {metrica_label}: {metrica_valor}", size=11),
                ]),
            ]),
            bgcolor=ft.Colors.GREY_900, padding=12, border_radius=10, margin=4,
        )

    seccion_top_guardias = ft.Column()
    seccion_top_puntos = ft.Column()
    seccion_top_nocturnos = ft.Column()
    seccion_top_finde = ft.Column()

    # ======================================================
    # 4. Detalle de sustituciones y restricciones (Tarjetas modernas)
    # ======================================================
    lista_sustituciones = ft.Column()
    lista_restricciones = ft.Column()

    # ======================================================
    # Función principal de carga
    # ======================================================
    async def cargar_estadisticas(e=None):
        mes = int(selector_mes.value)
        año = int(selector_año.value)
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.get(f"{URL_BACKEND}/estadisticas/{mes}/{año}")
                datos = resp.json()

                # --- KPIs ---
                kpi = datos.get("kpi", {})
                kpi_total.content.controls[1].controls[1].value = str(kpi.get("total_guardias", 0))
                kpi_sustituciones.content.controls[1].controls[1].value = str(kpi.get("total_sustituciones", 0))
                kpi_restricciones.content.controls[1].controls[1].value = str(kpi.get("total_restricciones", 0))

                # --- Anillo de Equidad ---
                eq = datos.get("equidad", {})
                pct = eq.get("porcentaje", 0)
                anillo_equidad.value = pct / 100
                anillo_equidad.color = ft.Colors.GREEN if pct >= 80 else ft.Colors.ORANGE if pct >= 60 else ft.Colors.RED
                texto_pct_equidad.value = f"{pct}%"

                # --- Rankings ---
                tops = datos.get("tops", {})

                def _llenar(seccion, lista, color_icono, icono, metrica_label, metrica_key):
                    seccion.controls.clear()
                    for s in lista:
                        seccion.controls.append(_tarjeta_podio(s, color_icono, icono, metrica_label, s[metrica_key]))

                _llenar(seccion_top_guardias, tops.get("mas_guardias", []), ft.Colors.RED, ft.Icons.ARROW_UPWARD, "Guardias", "total_guardias")
                _llenar(seccion_top_puntos, tops.get("mas_puntos", []), ft.Colors.ORANGE, ft.Icons.STAR, "Puntos", "total_puntos")
                _llenar(seccion_top_nocturnos, tops.get("mas_nocturnos", []), ft.Colors.INDIGO, ft.Icons.NIGHTLIGHT, "Nocturnas", "nocturnas")
                _llenar(seccion_top_finde, tops.get("mas_finde", []), ft.Colors.PURPLE, ft.Icons.CALENDAR_TODAY, "F. Semana", "finde")

                # --- Detalle de Sustituciones (Tarjetas) ---
                lista_sustituciones.controls.clear()
                sustituciones = datos.get("detalle_sustituciones", [])
                if not sustituciones:
                    lista_sustituciones.controls.append(
                        ft.Text("No hay sustituciones registradas en este mes.", italic=True, color=ft.Colors.GREY_500)
                    )
                else:
                    for s in sustituciones:
                        lista_sustituciones.controls.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Container(width=5, bgcolor=ft.Colors.ORANGE),
                                    ft.Icon(ft.Icons.SWAP_HORIZ, color=ft.Colors.ORANGE, size=24),
                                    ft.Column([
                                        ft.Text(s["soldado"], weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{s['fecha']} · {s['turno'].capitalize()} · Cédula: {s['cedula']}", size=12),
                                    ]),
                                ]),
                                bgcolor=ft.Colors.GREY_900, border_radius=10, padding=10, margin=5,
                            )
                        )

                # --- Detalle de Restricciones (Tarjetas) ---
                lista_restricciones.controls.clear()
                restricciones = datos.get("detalle_restricciones", [])
                if not restricciones:
                    lista_restricciones.controls.append(
                        ft.Text("No hay restricciones registradas en este mes.", italic=True, color=ft.Colors.GREY_500)
                    )
                else:
                    for r in restricciones:
                        lista_restricciones.controls.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Container(width=5, bgcolor=ft.Colors.RED),
                                    ft.Icon(ft.Icons.BLOCK, color=ft.Colors.RED, size=24),
                                    ft.Column([
                                        ft.Text(r["soldado"], weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{r['fecha_inicio']} → {r['fecha_fin']} · {r['motivo']}", size=12),
                                    ]),
                                ]),
                                bgcolor=ft.Colors.GREY_900, border_radius=10, padding=10, margin=5,
                            )
                        )

                texto_estado.value = ""
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    # ======================================================
    # Construcción del panel con desplegables modernos
    # ======================================================
    boton_actualizar = ft.Button("Actualizar", on_click=cargar_estadisticas, icon=ft.Icons.REFRESH)

    panel = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row([selector_mes, selector_año, boton_actualizar]),
            ft.Divider(),
            # KPIs siempre visibles
            ft.Row([kpi_total, kpi_sustituciones, kpi_restricciones], alignment=ft.MainAxisAlignment.SPACE_AROUND),
            ft.Divider(),
            # Anillo de Equidad (siempre visible) con el label debajo
            ft.Column([bloque_equidad, label_equidad], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(),
            # Secciones desplegables con ExpansionTile
            ft.ExpansionTile(
                title=ft.Text("🏆 Rankings (Top 5)", weight=ft.FontWeight.BOLD),
                controls=[
                    ft.Row([
                        ft.Column([ft.Text("Más Guardias", weight=ft.FontWeight.BOLD), seccion_top_guardias]),
                        ft.VerticalDivider(width=20, color=ft.Colors.TRANSPARENT),
                        ft.Column([ft.Text("Más Puntos", weight=ft.FontWeight.BOLD), seccion_top_puntos]),
                        ft.VerticalDivider(width=20, color=ft.Colors.TRANSPARENT),
                        ft.Column([ft.Text("Más Nocturnos", weight=ft.FontWeight.BOLD), seccion_top_nocturnos]),
                        ft.VerticalDivider(width=20, color=ft.Colors.TRANSPARENT),
                        ft.Column([ft.Text("Más F. Semana", weight=ft.FontWeight.BOLD), seccion_top_finde]),
                    ], scroll=ft.ScrollMode.AUTO, spacing=10),
                ],
            ),
            ft.ExpansionTile(
                title=ft.Text("🔄 Sustituciones", weight=ft.FontWeight.BOLD),
                controls=[lista_sustituciones],
            ),
            ft.ExpansionTile(
                title=ft.Text("🚫 Restricciones", weight=ft.FontWeight.BOLD),
                controls=[lista_restricciones],
            ),
            ft.Divider(),
            texto_estado,
        ]
    )

    return {"panel": panel}