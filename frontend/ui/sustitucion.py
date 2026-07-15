import asyncio

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import loading_bar, module_header, toast
from theme import *

_TRUECOLOR = "#1E88E5"
_SIMPLECOLOR = "#0D47A1"


def build(page: ft.Page, on_sustitucion_completada=None):
    barra_loading = loading_bar()
    _asignaciones = []
    _motivo_actual = ""

    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(MESES[i]) for i in range(12)],
        value=MESES[4],
        width=120,
    )
    selector_mes.on_change = lambda e: page.run_task(cargar_asignaciones)
    selector_ano = ft.TextField(label="Año", value="2026", width=100)
    selector_ano.on_change = lambda e: page.run_task(cargar_asignaciones)

    selector_punto = ft.Dropdown(label="Punto", options=[ft.dropdown.Option("")], width=160)

    boton_refrescar_punto = ft.IconButton(
        icon=ft.Icons.REFRESH,
        tooltip="Cargar guardias del punto",
        icon_size=20,
        icon_color=PRIMARY,
        style=ft.ButtonStyle(bgcolor={"": "#1a1a2e", "hovered": "#2a2a4e"}),
        on_click=lambda e: _llenar_dropdown(),
    )

    selector_asignacion = ft.Dropdown(label="Guardia a sustituir", options=[], width=300)
    boton_buscar = ft.FilledButton("Buscar candidatos", on_click=lambda e: page.run_task(buscar_candidatos))

    zona_resultados = ft.Column(spacing=16, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    def _build_candidate_card(soldado_nombre, soldado_apellido, cedula, rango, info_extra, tipo, on_click_callback):
        color = _TRUECOLOR if tipo == "trueque" else _SIMPLECOLOR
        badge_text = "Trueque" if tipo == "trueque" else "Sustitución"

        def _hover(e):
            e.control.bgcolor = "#191919" if e.data else SURFACE
            e.control.update()

        return ft.Container(
            content=ft.Row([
                ft.Container(width=6, bgcolor=color, border_radius=2),
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(badge_text.upper(), size=11, color=TEXT_SECONDARY, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                        ], spacing=6),
                        ft.Container(
                            content=ft.Text(f"{soldado_nombre} {soldado_apellido}  ·  {rango}",
                                            size=14, weight=ft.FontWeight.BOLD, color=TEXT_SECONDARY),
                            margin=ft.Margin(0, 4, 0, 0),
                        ),
                        ft.Container(height=8),
                        ft.Text(info_extra, size=17, color=ft.Colors.GREY_400 if "fatiga" in info_extra.lower() else None),
                    ], spacing=0, expand=True),
                    padding=ft.Padding(left=12, top=12, right=12, bottom=12),
                    expand=True,
                ),
            ], spacing=0),
            bgcolor=SURFACE,
            border_radius=24,
            height=140,
            expand=True,
            padding=0,
            on_click=on_click_callback,
            on_hover=_hover,
        )

    async def abrir_dialogo_confirmar(mensaje, callback_ejecutar):
        texto_confirm = ft.Text(mensaje, size=15, color=TEXT_SECONDARY)

        async def confirmar(e):
            page.pop_dialog()
            await callback_ejecutar()

        dialogo = ft.AlertDialog(
            title=ft.Text("Confirmar operación", size=20, weight=ft.FontWeight.BOLD, color=TEXT),
            content=ft.Column([texto_confirm], tight=True),
            bgcolor=SURFACE,
            actions=[
                ft.OutlinedButton("Cancelar", on_click=lambda e: page.pop_dialog(),
                                  style=ft.ButtonStyle(color=TEXT_SECONDARY, overlay_color="#333333", side=ft.BorderSide(0))),
                ft.FilledButton("Confirmar", on_click=confirmar,
                                style=ft.ButtonStyle(bgcolor=PRIMARY, color=ft.Colors.WHITE)),
            ],
        )
        page.show_dialog(dialogo)

    def _llenar_dropdown():
        punto = selector_punto.value
        if not punto:
            selector_asignacion.options = []
            selector_asignacion.value = None
            page.update()
            return
        filtradas = [a for a in _asignaciones if str(a["punto"]) == punto]
        selector_asignacion.options = [
            ft.dropdown.Option(
                key=str(a["id_asignacion"]),
                text=f'{a["dia"]} {selector_mes.value} · {a["turno"].capitalize()} · {a["nombre"]} {a["apellido"]}'
            ) for a in filtradas
        ]
        selector_asignacion.value = None
        page.update()

    async def cargar_asignaciones(e=None):
        mes = MESES.index(selector_mes.value) + 1
        ano = int(selector_ano.value)
        barra_loading.visible = True
        page.update()
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.get(f"{URL_BACKEND}/calendario-ver/{ano}/{mes}", params={"token": token})
                datos = resp.json()
                nonlocal _asignaciones
                _asignaciones = datos.get("asignaciones", [])
                _asignaciones.sort(key=lambda x: (x["dia"], 0 if x["turno"] == "diurno" else 1))
                puntos = sorted(set(str(a["punto"]) for a in _asignaciones))
                selector_punto.options = [ft.dropdown.Option(p) for p in puntos]
                selector_punto.value = None
                if not _asignaciones:
                    toast(page, "No hay guardias para este mes", "warning")
        except Exception as ex:
            toast(page, f"Error: {ex}", "error")
        finally:
            barra_loading.visible = False
            page.update()
        _llenar_dropdown()

    async def buscar_candidatos(e=None):
        if not selector_asignacion.value:
            toast(page, "Seleccione una guardia primero", "warning")
            return

        id_asig = int(selector_asignacion.value)
        asig_original = next((a for a in _asignaciones if a["id_asignacion"] == id_asig), None)
        if not asig_original:
            toast(page, "Guardia no encontrada", "error")
            return

        barra_loading.visible = True
        zona_resultados.controls.clear()
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.post(
                    f"{URL_BACKEND}/sustituir-guardia",
                    params={"id_asignacion_original": id_asig, "token": token}
                )
                datos = resp.json()

                if "error" in datos:
                    toast(page, datos["error"], "error")
                    return

                intercambios = datos.get("intercambios", [])
                candidatos = datos.get("candidatos", [])

                _motivo_text = ft.Text(
                    "Registra el motivo para poder efectuar la sustitución",
                    size=14, color=TEXT_SECONDARY, italic=True,
                )

                async def _abrir_dialogo_motivo(e=None):
                    campo = ft.TextField(
                        label="Motivo",
                        value=_motivo_actual,
                        multiline=True,
                        min_lines=3,
                        max_lines=5,
                        bgcolor="#111111",
                        border_color="#333333",
                        focused_border_color="#555555",
                        border_radius=10,
                        color=TEXT,
                    )

                    async def guardar_motivo(e):
                        nonlocal _motivo_actual
                        _motivo_actual = campo.value.strip()
                        if _motivo_actual:
                            _motivo_text.value = _motivo_actual
                            _motivo_text.color = TEXT
                            _motivo_text.italic = False
                        else:
                            _motivo_text.value = "Registra el motivo para poder efectuar la sustitución"
                            _motivo_text.color = TEXT_SECONDARY
                            _motivo_text.italic = True
                        page.pop_dialog()
                        page.update()

                    dialogo = ft.AlertDialog(
                        title=ft.Text("Motivo de la sustitución", size=20, weight=ft.FontWeight.BOLD, color=TEXT),
                        content=ft.Column([campo], tight=True),
                        bgcolor=SURFACE,
                        actions=[
                            ft.OutlinedButton("Cancelar", on_click=lambda e: page.pop_dialog(),
                                              style=ft.ButtonStyle(color=TEXT_SECONDARY, overlay_color="#333333", side=ft.BorderSide(0))),
                            ft.FilledButton("Guardar", on_click=guardar_motivo,
                                            style=ft.ButtonStyle(bgcolor=PRIMARY, color=ft.Colors.WHITE)),
                        ],
                    )
                    page.show_dialog(dialogo)

                def _motivo_hover(e):
                    e.control.bgcolor = "#191919" if e.data else SURFACE
                    e.control.update()

                def _build_info_card():
                    return ft.Container(
                        content=ft.Row([
                            ft.Container(width=6, bgcolor="#444444", border_radius=2),
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("Guardia a reemplazar", size=17, color=TEXT, weight=ft.FontWeight.BOLD),
                                    ft.Container(height=10),
                                    ft.Text(f"{asig_original['dia']} {selector_mes.value}  ·  {asig_original['turno'].capitalize()}  ·  {asig_original['punto']}",
                                            size=14, color=TEXT_SECONDARY),
                                ], spacing=0),
                                padding=ft.Padding(left=12, top=12, right=12, bottom=12),
                                expand=True,
                            ),
                        ], spacing=0),
                        bgcolor=SURFACE,
                        border_radius=16,
                        height=125,
                        expand=True,
                        padding=0,
                    )

                def _build_soldado_card():
                    return ft.Container(
                        content=ft.Row([
                            ft.Container(width=6, bgcolor="#444444", border_radius=2),
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("Soldado", size=17, color=TEXT, weight=ft.FontWeight.BOLD),
                                    ft.Container(height=10),
                                    ft.Text(asig_original.get('rango', '').capitalize(),
                                            size=14, color=TEXT_SECONDARY),
                                    ft.Container(height=4),
                                    ft.Text(f"{asig_original['nombre']} {asig_original['apellido']}  ·  {asig_original['cedula']}  ·  {asig_original.get('unidad', '').capitalize()}",
                                            size=14, color=TEXT_SECONDARY),
                                ], spacing=0),
                                padding=ft.Padding(left=12, top=12, right=12, bottom=12),
                                expand=True,
                            ),
                        ], spacing=0),
                        bgcolor=SURFACE,
                        border_radius=16,
                        height=125,
                        expand=True,
                        padding=0,
                    )

                def _build_motivo_card():
                    return ft.Container(
                        content=ft.Row([
                            ft.Container(width=6, bgcolor="#444444", border_radius=2),
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("Motivo de la sustitución", size=17, color=TEXT, weight=ft.FontWeight.BOLD),
                                    ft.Container(height=10),
                                    _motivo_text,
                                ], spacing=0),
                                padding=ft.Padding(left=12, top=12, right=12, bottom=12),
                                expand=True,
                            ),
                        ], spacing=0),
                        bgcolor=SURFACE,
                        border_radius=16,
                        height=125,
                        expand=True,
                        padding=0,
                        on_click=lambda e: page.run_task(_abrir_dialogo_motivo),
                        on_hover=_motivo_hover,
                    )

                zona_resultados.controls.append(
                    ft.Row([
                        _build_info_card(),
                        _build_soldado_card(),
                        _build_motivo_card(),
                    ], spacing=20)
                )

                if not intercambios and not candidatos:
                    zona_resultados.controls.append(
                        ft.Container(
                            ft.Text("No hay opciones disponibles para esta sustitución", italic=True, color=TEXT_SECONDARY, size=15),
                            alignment=ft.Alignment(0, 0), padding=30,
                        )
                    )
                    page.update()
                    return

                if intercambios:
                    zona_resultados.controls.append(ft.Divider(height=1, color=DIVIDER))
                    zona_resultados.controls.append(
                        ft.Container(height=8)
                    )
                    zona_resultados.controls.append(
                        ft.Text("Trueques disponibles", size=24, color=TEXT, weight=ft.FontWeight.BOLD)
                    )
                    trueque_cards = []
                    for inter in intercambios:
                        info = f"Intercambia su guardia del día {inter['dia_B']} ({inter['turno_B']})"

                        async def ejecutar_trueque(id_sb=inter["id_soldado_B"], id_ab=inter["id_asignacion_B"]):
                            motivo = _motivo_actual.strip()
                            if not motivo:
                                toast(page, "Debe ingresar un motivo para la sustitución", "warning")
                                return
                            barra_loading.visible = True
                            page.update()
                            try:
                                async with httpx.AsyncClient() as cli:
                                    token = get_token(page)
                                    resp = await cli.post(
                                        f"{URL_BACKEND}/confirmar-trueque",
                                        params={"id_asignacion_a": id_asig, "id_asignacion_b": id_ab,
                                                "id_soldado_b": id_sb, "motivo": motivo, "token": token}
                                    )
                                    data = resp.json()
                                    if "error" in data:
                                        toast(page, data["error"], "error")
                                    else:
                                        toast(page, "Trueque realizado correctamente", "success")
                                        zona_resultados.controls.clear()
                                        selector_asignacion.value = None
                                        if on_sustitucion_completada:
                                            on_sustitucion_completada()
                                        page.update()
                            except Exception as ex:
                                toast(page, str(ex), "error")
                            finally:
                                barra_loading.visible = False
                                page.update()

                        async def confirmar_trueque_click(e):
                            await abrir_dialogo_confirmar(
                                f"¿Confirmar el trueque con {inter['nombre_B']} {inter.get('apellido_B', '')}? "
                                f"Intercambiarán sus guardias del día {asig_original['dia']} y {inter['dia_B']}.",
                                ejecutar_trueque
                            )

                        trueque_cards.append(
                            _build_candidate_card(
                                inter["nombre_B"], inter.get("apellido_B", ""),
                                inter["cedula_B"], inter.get("rango_B", ""),
                                info, "trueque", confirmar_trueque_click
                            )
                        )

                    for i in range(0, len(trueque_cards), 3):
                        row = []
                        for j in range(3):
                            idx = i + j
                            row.append(trueque_cards[idx] if idx < len(trueque_cards) else ft.Container(expand=True))
                        zona_resultados.controls.append(ft.Row(row, spacing=20))

                if candidatos:
                    zona_resultados.controls.append(ft.Divider(height=1, color=DIVIDER))
                    zona_resultados.controls.append(
                        ft.Container(height=8)
                    )
                    titulo = "Sustituciones simples" if "Ideal" in candidatos[0]["estado"] else "Sustituciones simples (con fatiga)"
                    zona_resultados.controls.append(
                        ft.Text(titulo, size=24, color=TEXT, weight=ft.FontWeight.BOLD)
                    )
                    simple_cards = []
                    for c in candidatos:
                        estado_tag = "✅ Ideal" if "Ideal" in c["estado"] else "⚠️ Con fatiga"

                        async def ejecutar_simple(id_s=c["id_soldado"]):
                            motivo = _motivo_actual.strip()
                            if not motivo:
                                toast(page, "Debe ingresar un motivo para la sustitución", "warning")
                                return
                            barra_loading.visible = True
                            page.update()
                            try:
                                async with httpx.AsyncClient() as cli:
                                    token = get_token(page)
                                    resp = await cli.post(
                                        f"{URL_BACKEND}/confirmar-sustitucion",
                                        params={"id_asignacion_original": id_asig,
                                                "id_nuevo_soldado": id_s, "motivo": motivo, "token": token}
                                    )
                                    data = resp.json()
                                    if "error" in data:
                                        toast(page, data["error"], "error")
                                    else:
                                        toast(page, "Sustitución realizada correctamente", "success")
                                        zona_resultados.controls.clear()
                                        selector_asignacion.value = None
                                        if on_sustitucion_completada:
                                            on_sustitucion_completada()
                                        page.update()
                            except Exception as ex:
                                toast(page, str(ex), "error")
                            finally:
                                barra_loading.visible = False
                                page.update()

                        async def confirmar_simple_click(e):
                            await abrir_dialogo_confirmar(
                                f"¿Confirmar sustitución? {c['nombre']} {c.get('apellido', '')} "
                                f"tomará la guardia del día {asig_original['dia']} en {asig_original['punto']}.",
                                ejecutar_simple
                            )

                        simple_cards.append(
                            _build_candidate_card(
                                c["nombre"], c.get("apellido", ""),
                                c["cedula"], c.get("rango", ""),
                                estado_tag, "simple", confirmar_simple_click
                            )
                        )

                    for i in range(0, len(simple_cards), 3):
                        row = []
                        for j in range(3):
                            idx = i + j
                            row.append(simple_cards[idx] if idx < len(simple_cards) else ft.Container(expand=True))
                        zona_resultados.controls.append(ft.Row(row, spacing=20))

        except Exception as ex:
            toast(page, f"Error: {ex}", "error")
        finally:
            barra_loading.visible = False
            page.update()

    panel = ft.Column([
        barra_loading,
        module_header("Sustitución", "Reemplazo y trueque de guardias"),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row([selector_mes, selector_ano, selector_punto, boton_refrescar_punto, selector_asignacion, boton_buscar], spacing=8),
        ft.Divider(height=1, color=DIVIDER),
        zona_resultados,
    ])

    page.run_task(cargar_asignaciones)
    return {"panel": panel}
