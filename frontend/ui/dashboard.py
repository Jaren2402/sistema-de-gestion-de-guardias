import asyncio

import flet as ft
import httpx
from config import URL_BACKEND
from skeleton import loading_bar, module_header
from theme import *


def build(page: ft.Page):
    """Construye el dashboard principal: estadísticas, gráficos y resumen mensual del cuartel."""
    sel_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(str(m)) for m in range(1, 13)],
        value="5", width=100,
    )
    sel_ano = ft.TextField(label="A\u00f1o", value="2026", width=90)
    sel_periodo = ft.Dropdown(
        label="Per\u00edodo",
        options=[
            ft.dropdown.Option("1", "1 mes"),
            ft.dropdown.Option("3", "3 meses"),
            ft.dropdown.Option("6", "6 meses"),
            ft.dropdown.Option("12", "12 meses"),
        ],
        value="1", width=130,
    )

    barra_loading = loading_bar()

    # ========================================================
    # KPIs
    # ========================================================
    def _kpi(titulo, icono):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(icono, size=22, color=PRIMARY),
                    ft.Text("—", size=22, weight=ft.FontWeight.BOLD, color=TEXT, expand=True,
                            text_align=ft.TextAlign.RIGHT),
                ]),
                ft.Text(titulo, size=11, color=TEXT_SECONDARY),
            ], spacing=2),
            bgcolor=SURFACE,
            padding=ft.Padding(left=14, top=12, right=14, bottom=12),
            border_radius=10,
            expand=True,
        )

    kpi_total = _kpi("Total Guardias", ft.Icons.ASSIGNMENT)
    kpi_sust = _kpi("Sustituciones", ft.Icons.SWAP_HORIZ)
    kpi_restr = _kpi("Restricciones", ft.Icons.BLOCK)

    # ========================================================
    # Equidad
    # ========================================================
    ring_eq = ft.ProgressRing(
        width=130, height=130, stroke_width=12, value=0.0,
        color=PRIMARY, bgcolor=SURFACE_LIGHT,
    )
    txt_pct = ft.Text("—", size=28, weight=ft.FontWeight.BOLD, color=TEXT)
    stack_eq = ft.Stack([
        ring_eq,
        ft.Container(content=txt_pct, alignment=ft.Alignment(0, -0.1), width=130, height=130),
    ])
    txt_eq_title = ft.Text("\u00cdndice de Equidad", size=14, weight=ft.FontWeight.BOLD, color=TEXT)
    txt_eq_max = ft.Text("", size=12, color=TEXT_SECONDARY)
    txt_eq_min = ft.Text("", size=12, color=TEXT_SECONDARY)
    txt_eq_dif = ft.Text("", size=12, color=PRIMARY_LIGHT)

    # ========================================================
    # Contenedores din\u00e1micos
    # ========================================================
    cont_carga = ft.Container(
        content=ft.Column(spacing=3, scroll=ft.ScrollMode.AUTO, height=260),
        bgcolor=SURFACE, border_radius=8, padding=ft.Padding(left=6, top=6, right=6, bottom=6),
        expand=True,
    )
    txt_avg = ft.Text("", size=11, color=TEXT_SECONDARY)

    cont_rango = ft.Container(
        content=ft.Column(spacing=3),
        bgcolor=SURFACE, border_radius=8, padding=ft.Padding(left=6, top=6, right=6, bottom=6),
        expand=True,
    )

    cont_suplentes = ft.Container(
        content=ft.Column(spacing=3),
        bgcolor=SURFACE, border_radius=8, padding=ft.Padding(left=6, top=6, right=6, bottom=6),
        expand=True,
    )

    # ========================================================
    # Rankings
    # ========================================================
    def _col_rank(titulo):
        return ft.Column([
            ft.Text(titulo, size=11, weight=ft.FontWeight.BOLD, color=PRIMARY),
            ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=170),
        ], expand=True, spacing=4)

    col_mg = _col_rank("M\u00e1s Guardias")
    col_mg2 = _col_rank("Menos Guardias")
    col_mp = _col_rank("M\u00e1s Puntos")
    col_mn = _col_rank("M\u00e1s Nocturnos")

    # ========================================================
    # Listas expandibles
    # ========================================================
    lista_sust = ft.Column(spacing=3)
    lista_restr = ft.Column(spacing=3)

    # ========================================================
    # Helpers
    # ========================================================
    def _barra(label, value, max_val, color=PRIMARY):
        ratio = value / max_val if max_val > 0 else 0
        r_int = int(ratio * 100)
        if r_int < 1 and ratio > 0:
            r_int = 1
        return ft.Container(
            content=ft.Row([
                ft.Container(ft.Text(label, size=11, color=TEXT, no_wrap=True), width=90),
                ft.Stack([
                    ft.Container(expand=True, height=14, bgcolor=SURFACE_LIGHT, border_radius=3),
                    ft.Row([
                        ft.Container(height=14, bgcolor=color, border_radius=3, expand=r_int),
                        ft.Container(height=14, expand=max(100 - r_int, 1)),
                    ], spacing=0),
                ], expand=True),
                ft.Container(
                    ft.Text(str(value), size=11, color=TEXT, text_align=ft.TextAlign.RIGHT),
                    width=26,
                ),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(top=2, bottom=2, left=0, right=0),
        )

    def _item_rank(s, idx):
        return ft.Container(
            content=ft.Row([
                ft.Text(f"{idx+1}\u00ba", size=9, weight=ft.FontWeight.BOLD,
                        color=TEXT_SECONDARY, width=20),
                ft.Text(s["nombre"], size=11, color=TEXT, expand=True),
                ft.Text(f"{s['rango']}", size=9, color=TEXT_SECONDARY),
            ], spacing=4),
            bgcolor=SURFACE,
            padding=ft.Padding(left=6, top=3, right=6, bottom=3),
            border_radius=5,
        )

    def _tarjeta(titulo, subtitulo):
        return ft.Container(
            content=ft.Row([
                ft.Container(width=3, bgcolor=PRIMARY, border_radius=2),
                ft.Column([
                    ft.Text(titulo, size=11, weight=ft.FontWeight.BOLD, color=TEXT),
                    ft.Text(subtitulo, size=9, color=TEXT_SECONDARY),
                ], spacing=0, expand=True),
            ], spacing=6),
            bgcolor=SURFACE,
            padding=ft.Padding(left=0, top=4, right=8, bottom=4),
            border_radius=6,
        )

    def _placeholder(mensaje="Sin datos para este mes."):
        return ft.Container(
            content=ft.Text(mensaje, italic=True, color=TEXT_SECONDARY, size=12),
            padding=ft.Padding(top=20, bottom=20, left=0, right=0),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    # ========================================================
    # Carga de datos
    # ========================================================
    async def cargar(e=None):
        m = int(sel_mes.value)
        a = int(sel_ano.value)
        n = int(sel_periodo.value)

        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cl:
                r = await cl.get(f"{URL_BACKEND}/estadisticas/{m}/{a}?meses={n}")
                d = r.json()

                kpi = d.get("kpi", {})
                total_g = kpi.get("total_guardias", 0)
                kpi_total.content.controls[0].controls[1].value = str(total_g)
                kpi_sust.content.controls[0].controls[1].value = str(kpi.get("total_sustituciones", 0))
                kpi_restr.content.controls[0].controls[1].value = str(kpi.get("total_restricciones", 0))

                eq = d.get("equidad", {})
                pct = eq.get("porcentaje", 0)
                ring_eq.value = pct / 100
                ring_eq.color = PRIMARY if pct >= 80 else PRIMARY_DARK if pct >= 60 else ERROR
                txt_pct.value = f"{pct:.0f}%" if total_g > 0 else "—"

                periodo = d.get("periodo", {})
                total_meses = periodo.get("total_meses_periodo", 1)
                if total_meses > 1:
                    txt_eq_title.value = f"\u00cdndice de Equidad ({total_meses} meses)"
                else:
                    txt_eq_title.value = "\u00cdndice de Equidad"

                tops = d.get("tops", {})
                tp = tops.get("mas_puntos", [])
                tm = tops.get("menos_puntos", [])
                if tp and total_g > 0:
                    txt_eq_max.value = f"M\u00e1x: {tp[0]['nombre']}  ({tp[0]['total_puntos']} pts)"
                else:
                    txt_eq_max.value = "M\u00e1x: —"
                if tm and total_g > 0:
                    txt_eq_min.value = f"M\u00edn: {tm[0]['nombre']}  ({tm[0]['total_puntos']} pts)"
                else:
                    txt_eq_min.value = "M\u00edn: —"
                dif = eq.get("diferencia_max_min", 0)
                txt_eq_dif.value = f"Diferencia: {dif} pts" if total_g > 0 else ""

                todos = d.get("todos_soldados", [])
                hay_datos = total_g > 0 and len(todos) > 0

                # --- Carga Individual ---
                col_c = cont_carga.content
                col_c.controls.clear()
                if not hay_datos:
                    col_c.controls.append(_placeholder("Genera el calendario para este mes."))
                else:
                    vals = [s["total_guardias"] for s in todos]
                    mx = max(vals)
                    prom = sum(vals) / len(vals)
                    txt_avg.value = f"Media: {prom:.1f}  \u2022  {len(todos)} soldados"
                    for s in sorted(todos, key=lambda x: x["total_guardias"], reverse=True):
                        color = PRIMARY_LIGHT if s["total_guardias"] <= prom else PRIMARY_DARK
                        col_c.controls.append(_barra(s["nombre"], s["total_guardias"], mx, color))

                # --- Guardias por Rango ---
                col_r = cont_rango.content
                col_r.controls.clear()
                if not hay_datos:
                    col_r.controls.append(_placeholder())
                else:
                    agrupados = {}
                    for s in todos:
                        rk = s["rango"].capitalize()
                        agrupados[rk] = agrupados.get(rk, 0) + s["total_guardias"]
                    orden = sorted(agrupados.items(), key=lambda x: x[1], reverse=True)
                    mx_r = orden[0][1]
                    for rk, rv in orden:
                        col_r.controls.append(_barra(rk, rv, mx_r, PRIMARY))

                # --- Top Suplentes ---
                col_sp = cont_suplentes.content
                col_sp.controls.clear()
                sustituciones = d.get("detalle_sustituciones", [])
                if not sustituciones:
                    col_sp.controls.append(_placeholder("No hay sustituciones este mes."))
                else:
                    from collections import Counter
                    conteo = Counter(s["soldado"] for s in sustituciones)
                    for nom, cnt in conteo.most_common(6):
                        col_sp.controls.append(_barra(nom, cnt, conteo.most_common(1)[0][1], PRIMARY_LIGHT))

                # --- Rankings ---
                def _llenar(col, lista):
                    col.controls[1].controls.clear()
                    if not lista:
                        col.controls[1].controls.append(
                            ft.Container(
                                ft.Text("—", color=TEXT_SECONDARY, size=10),
                                padding=5,
                            )
                        )
                    else:
                        for i, s in enumerate(lista):
                            col.controls[1].controls.append(_item_rank(s, i))

                _llenar(col_mg, tops.get("mas_guardias", []))
                _llenar(col_mg2, tops.get("menos_guardias", []))
                _llenar(col_mp, tops.get("mas_puntos", []))
                _llenar(col_mn, tops.get("mas_nocturnos", []))

                # --- Expandibles ---
                def _cargar(ctrl, datos, fmt):
                    ctrl.controls.clear()
                    if not datos:
                        ctrl.controls.append(ft.Text("Sin registros.", italic=True, color=TEXT_SECONDARY, size=11))
                    else:
                        for item in datos:
                            ctrl.controls.append(_tarjeta(item["soldado"], fmt(item)))

                _cargar(lista_sust, sustituciones,
                        lambda s: f"{s['fecha']}  \u2022  {s['turno'].capitalize()}")
                _cargar(lista_restr, d.get("detalle_restricciones", []),
                        lambda r: f"{r['fecha_inicio']} \u2192 {r['fecha_fin']}  \u2022  {r['motivo']}")

        except httpx.ConnectError:
            txt_pct.value = "—"
            for c in [cont_carga.content, cont_rango.content, cont_suplentes.content,
                      lista_sust, lista_restr]:
                c.controls.clear()
                c.controls.append(_placeholder("No se pudo conectar con el servidor."))
            for col in [col_mg, col_mg2, col_mp, col_mn]:
                col.controls[1].controls.clear()
                col.controls[1].controls.append(
                    ft.Container(ft.Text("—", color=TEXT_SECONDARY, size=10), padding=5))
        except Exception as ex:
            for c in [cont_carga.content, cont_rango.content, cont_suplentes.content,
                      lista_sust, lista_restr]:
                c.controls.clear()
                c.controls.append(_placeholder(f"Error: {ex}"))
        finally:
            barra_loading.visible = False
            page.update()

    btn = ft.FilledButton("Actualizar Dashboard", on_click=cargar, icon=ft.Icons.REFRESH)

    # ========================================================
    # Panel
    # ========================================================
    panel = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=14,
        controls=[
            barra_loading,
            module_header("Dashboard", "Resumen general de métricas y equidad del período"),
            ft.Divider(height=1, color=DIVIDER),
            ft.Row([sel_mes, sel_ano, sel_periodo, btn]),
            ft.Divider(height=1, color=DIVIDER),
            ft.Row([kpi_total, kpi_sust, kpi_restr], spacing=8),
            ft.Divider(height=1, color=DIVIDER),

            # Equidad
            ft.Row([
                stack_eq,
                ft.Container(width=24),
                ft.Column([
                    txt_eq_title,
                    txt_eq_max,
                    txt_eq_min,
                    txt_eq_dif,
                ], spacing=3, alignment=ft.MainAxisAlignment.CENTER, expand=True),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(height=1, color=DIVIDER),

            # Carga
            ft.Row([
                ft.Text("Carga Individual", size=14, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Container(expand=True),
                txt_avg,
            ]),
            cont_carga,
            ft.Divider(height=1, color=DIVIDER),

            # Rango
            ft.Text("Guardias por Rango", size=14, weight=ft.FontWeight.BOLD, color=TEXT),
            cont_rango,
            ft.Divider(height=1, color=DIVIDER),

            # Suplentes
            ft.Text("Top Suplentes", size=14, weight=ft.FontWeight.BOLD, color=TEXT),
            cont_suplentes,
            ft.Divider(height=1, color=DIVIDER),

            # Rankings
            ft.Text("Rankings", size=15, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Row([col_mg, col_mg2, col_mp, col_mn], spacing=10,
                   vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Divider(height=1, color=DIVIDER),

            ft.ExpansionTile(
                title=ft.Text("Sustituciones", size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                controls=[lista_sust],
            ),
            ft.ExpansionTile(
                title=ft.Text("Restricciones", size=13, weight=ft.FontWeight.BOLD, color=TEXT),
                controls=[lista_restr],
            ),
        ],
    )

    return {"panel": panel}
