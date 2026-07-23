import asyncio
from datetime import datetime

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import confirm_dialog, loading_bar, module_header, no_data, toast
from theme import *


def _field_style():
    return dict(
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER,
        focused_border_color=PRIMARY,
        cursor_color=PRIMARY,
    )


def build(page: ft.Page):
    barra_loading = loading_bar()
    _asignaciones = []
    _motivo_actual = ""

    selector_mes = ft.Dropdown(
        label="Mes", expand=False, width=130,
        options=[ft.dropdown.Option(MESES[i]) for i in range(12)],
        value=MESES[datetime.now().month - 1],
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY,
    )
    selector_ano = ft.TextField(label="Año", value=str(datetime.now().year), width=100, **_field_style())

    selector_punto = ft.Dropdown(
        label="Punto", expand=False, width=160,
        options=[ft.dropdown.Option("")],
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY,
    )

    selector_asignacion = ft.Dropdown(
        label="Guardia a sustituir", expand=False, width=280,
        options=[],
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY,
    )

    zona_resultados = ft.Column(spacing=0, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    no_data_container = no_data(ft.Icons.SWAP_HORIZ, "Seleccione una guardia para ver opciones de sustitución")

    async def _llenar_dropdown(e=None):
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
                resp = await cliente.get(f"{URL_BACKEND}/calendario-ver/{ano}/{mes}", headers={"Authorization": f"Bearer {token}"})
                datos = resp.json()
                nonlocal _asignaciones
                _asignaciones = datos.get("asignaciones", [])
                _asignaciones.sort(key=lambda x: (x["dia"], 0 if x["turno"] == "diurno" else 1))
                puntos = sorted(set(str(a["punto"]) for a in _asignaciones))
                selector_punto.options = [ft.dropdown.Option(p) for p in puntos]
                selector_punto.value = None
                selector_asignacion.options = []
                selector_asignacion.value = None
                zona_resultados.controls.clear()
                no_data_container.visible = True
                if not _asignaciones:
                    toast(page, "No hay guardias para este mes", "warning")
        except Exception:
            toast(page, "Error al cargar las asignaciones.", "error")
        finally:
            barra_loading.visible = False
            page.update()

    async def _limpiar(e=None):
        nonlocal _motivo_actual
        _motivo_actual = ""
        await cargar_asignaciones()

    def _build_info_card(icono, titulo, lineas):
        items = []
        items.append(ft.Text(titulo, size=14, weight=ft.FontWeight.BOLD, color=TEXT))
        for linea in lineas:
            items.append(ft.Container(height=4))
            items.append(ft.Text(linea, size=13, color=TEXT_SECONDARY))
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(icono, size=18, color=PRIMARY),
                    ft.Text(titulo, size=14, weight=ft.FontWeight.BOLD, color=TEXT),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=1, color=DIVIDER),
            ] + items, spacing=0),
            bgcolor=SURFACE,
            border_radius=12,
            padding=ft.Padding(14, 12, 14, 12),
            expand=True,
        )

    def _build_candidate_card(soldado_nombre, soldado_apellido, cedula, rango, info_extra, tipo, on_click_callback):
        badge_color = SHIFT_DIURNO if tipo == "trueque" else BTN_BG
        badge_text = "TRUEQUE" if tipo == "trueque" else "SUSTITUCIÓN"
        fatiga = "fatiga" in info_extra.lower()

        card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"{soldado_nombre} {soldado_apellido}", size=16, weight=ft.FontWeight.W_500, color=TEXT),
                    ft.Container(
                        content=ft.Text(badge_text, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor=badge_color,
                        border_radius=4,
                        padding=ft.Padding(8, 3, 8, 3),
                    ),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=1, color=DIVIDER),
                ft.Text(f"{rango}  ·  C.I. {cedula}", size=14, color=TEXT_SECONDARY),
                ft.Container(height=4),
                ft.Text(info_extra, size=15, color=WARNING if fatiga else TEXT_SECONDARY, italic=fatiga),
                ft.Container(expand=True),
                ft.Row([
                    ft.Container(expand=True),
                    ft.FilledButton(
                        "Seleccionar",
                        on_click=on_click_callback,
                        style=ft.ButtonStyle(bgcolor=BTN_BG, color=BTN_TEXT),
                    ),
                ], spacing=0),
            ], spacing=6, expand=True),
            bgcolor=SURFACE,
            border_radius=12,
            padding=ft.Padding(16, 14, 16, 12),
            height=190,
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

    async def abrir_dialogo_confirmar(mensaje, callback_ejecutar):
        async def confirmar(e=None):
            page.pop_dialog()
            page.update()
            await callback_ejecutar()

        confirm_dialog(
            page,
            title="Confirmar operación",
            message=mensaje,
            button_label="Confirmar",
            on_confirm=confirmar,
        )

    async def buscar_candidatos(e=None):
        if not selector_asignacion.value:
            return

        id_asig = int(selector_asignacion.value)
        asig_original = next((a for a in _asignaciones if a["id_asignacion"] == id_asig), None)
        if not asig_original:
            toast(page, "Guardia no encontrada", "error")
            return

        barra_loading.visible = True
        zona_resultados.controls.clear()
        no_data_container.visible = False
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp = await cliente.post(
                    f"{URL_BACKEND}/sustituir-guardia",
                    params={"id_asignacion_original": id_asig},
                    headers={"Authorization": f"Bearer {token}"}
                )
                datos = resp.json()

                if "error" in datos:
                    toast(page, datos["error"], "error")
                    return

                intercambios = datos.get("intercambios", [])
                candidatos = datos.get("candidatos", [])

                async def _abrir_dialogo_motivo(e=None):
                    campo = ft.TextField(
                        label="Motivo",
                        value=_motivo_actual,
                        multiline=True, min_lines=3, max_lines=5,
                        border_color=DIVIDER, focused_border_color=PRIMARY,
                        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
                        label_style=ft.TextStyle(color=TEXT_SECONDARY),
                        cursor_color=PRIMARY,
                    )

                    async def guardar_motivo(e):
                        nonlocal _motivo_actual
                        _motivo_actual = campo.value.strip()
                        if _motivo_actual:
                            _motivo_text.value = _motivo_actual
                            _motivo_text.color = TEXT
                            _motivo_text.italic = False
                        else:
                            _motivo_text.value = "Clic para registrar motivo"
                            _motivo_text.color = TEXT_SECONDARY
                            _motivo_text.italic = True
                        page.pop_dialog()
                        page.update()

                    dialogo = ft.AlertDialog(
                        title=ft.Text("Motivo de la sustitución", size=20, weight=ft.FontWeight.BOLD, color=TEXT),
                        content=ft.Column([campo], tight=True),
                        bgcolor=SURFACE,
                        shape=ft.RoundedRectangleBorder(radius=12),
                        actions=[
                            ft.OutlinedButton("Cancelar", on_click=lambda e: page.pop_dialog(),
                                style=ft.ButtonStyle(color=TEXT_SECONDARY, side=ft.BorderSide(1, DIVIDER))),
                            ft.FilledButton("Guardar", on_click=guardar_motivo,
                                style=ft.ButtonStyle(bgcolor=BTN_BG, color=BTN_TEXT)),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END,
                    )
                    page.show_dialog(dialogo)

                _motivo_text = ft.Text(
                    "Clic para registrar motivo",
                    size=13, color=TEXT_SECONDARY, italic=True,
                )

                info_guardia_card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.CALENDAR_TODAY, size=18, color=PRIMARY),
                            ft.Text("Guardia a reemplazar", size=15, weight=ft.FontWeight.BOLD, color=TEXT),
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Divider(height=1, color=DIVIDER),
                        ft.Text(f"Día {asig_original['dia']} · {selector_mes.value}", size=15, color=TEXT),
                        ft.Container(height=6),
                        ft.Text(f"{asig_original['turno'].capitalize()} · {asig_original['punto']}", size=14, color=TEXT_SECONDARY),
                    ], spacing=8),
                    bgcolor=SURFACE,
                    border_radius=12,
                    padding=ft.Padding(16, 16, 16, 16),
                    expand=True,
                    height=140,
                )

                info_soldado_card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.PERSON, size=18, color=PRIMARY),
                            ft.Text("Soldado", size=15, weight=ft.FontWeight.BOLD, color=TEXT),
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Divider(height=1, color=DIVIDER),
                        ft.Text(f"{asig_original['nombre']} {asig_original['apellido']}", size=15, color=TEXT),
                        ft.Container(height=6),
                        ft.Text(f"{asig_original.get('rango', '').capitalize()} · C.I. {asig_original['cedula']}", size=14, color=TEXT_SECONDARY),
                    ], spacing=8),
                    bgcolor=SURFACE,
                    border_radius=12,
                    padding=ft.Padding(16, 16, 16, 16),
                    expand=True,
                    height=140,
                )

                motivo_card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.EDIT_NOTE, size=18, color=PRIMARY),
                            ft.Text("Motivo", size=15, weight=ft.FontWeight.BOLD, color=TEXT),
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Divider(height=1, color=DIVIDER),
                        _motivo_text,
                    ], spacing=8),
                    bgcolor=SURFACE,
                    border_radius=12,
                    padding=ft.Padding(16, 16, 16, 16),
                    expand=True,
                    height=140,
                    on_click=lambda e: page.run_task(_abrir_dialogo_motivo),
                )
                motivo_card.cursor = "pointer"

                def _motivo_hover(e):
                    if e.data:
                        motivo_card.bgcolor = HOVER_ROW_BG
                        motivo_card.shadow = [ft.BoxShadow(blur_radius=10, color="#000000", spread_radius=1, offset=ft.Offset(0, 3))]
                        motivo_card.scale = ft.Scale(1.01)
                    else:
                        motivo_card.bgcolor = SURFACE
                        motivo_card.shadow = []
                        motivo_card.scale = ft.Scale(1.0)
                    motivo_card.update()

                motivo_card.on_hover = _motivo_hover

                zona_resultados.controls.append(ft.Container(height=18))
                zona_resultados.controls.append(ft.Row([info_guardia_card, info_soldado_card, motivo_card], spacing=16, expand=True))
                zona_resultados.controls.append(ft.Container(height=18))

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
                    zona_resultados.controls.append(ft.Container(height=8))
                    zona_resultados.controls.append(
                        ft.Text("TRUEQUES DISPONIBLES", size=16, weight=ft.FontWeight.BOLD, color=TEXT)
                    )
                    zona_resultados.controls.append(ft.Container(height=12))
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
                                                "id_soldado_b": id_sb, "motivo": motivo},
                                        headers={"Authorization": f"Bearer {token}"}
                                    )
                                    data = resp.json()
                                    if "error" in data:
                                        toast(page, data["error"], "error")
                                    else:
                                        toast(page, "Trueque realizado correctamente", "success")
                                        await _limpiar()
                            except Exception:
                                toast(page, "Error inesperado. Intente de nuevo.", "error")
                            finally:
                                barra_loading.visible = False
                                page.update()

                        async def confirmar_trueque_click(e, _inter=inter, _ejecutar=ejecutar_trueque):
                            await abrir_dialogo_confirmar(
                                f"¿Confirmar el trueque con {_inter['nombre_B']}? "
                                f"Intercambiarán sus guardias del día {asig_original['dia']} y {_inter['dia_B']}.",
                                _ejecutar
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
                        zona_resultados.controls.append(ft.Row(row, spacing=16, expand=True))
                        zona_resultados.controls.append(ft.Container(height=16))

                if candidatos:
                    titulo = "SUSTITUCIONES SIMPLES" if "Ideal" in candidatos[0]["estado"] else "SUSTITUCIONES SIMPLES (CON FATIGA)"
                    zona_resultados.controls.append(ft.Divider(height=1, color=DIVIDER))
                    zona_resultados.controls.append(ft.Container(height=8))
                    zona_resultados.controls.append(
                        ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD, color=TEXT)
                    )
                    zona_resultados.controls.append(ft.Container(height=12))
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
                                                "id_nuevo_soldado": id_s, "motivo": motivo},
                                        headers={"Authorization": f"Bearer {token}"}
                                    )
                                    data = resp.json()
                                    if "error" in data:
                                        toast(page, data["error"], "error")
                                    else:
                                        toast(page, "Sustitución realizada correctamente", "success")
                                        await _limpiar()
                            except Exception:
                                toast(page, "Error inesperado. Intente de nuevo.", "error")
                            finally:
                                barra_loading.visible = False
                                page.update()

                        async def confirmar_simple_click(e, _c=c, _ejecutar=ejecutar_simple):
                            await abrir_dialogo_confirmar(
                                f"¿Confirmar sustitución? {_c['nombre']} "
                                f"tomará la guardia del día {asig_original['dia']} en {asig_original['punto']}.",
                                _ejecutar
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
                        zona_resultados.controls.append(ft.Row(row, spacing=16, expand=True))
                        zona_resultados.controls.append(ft.Container(height=16))

        except Exception as ex:
            toast(page, f"Error: {ex}", "error")
        finally:
            barra_loading.visible = False
            page.update()

    form_card = ft.Container(
        content=ft.Row([
            selector_mes,
            selector_ano,
            selector_punto,
            ft.FilledButton("Buscar", on_click=lambda e: page.run_task(_llenar_dropdown), icon=ft.Icons.SEARCH,
                style=ft.ButtonStyle(bgcolor=BTN_BG, color=BTN_TEXT)),
            selector_asignacion,
            ft.FilledButton("Cargar Guardias", on_click=lambda e: page.run_task(buscar_candidatos), icon=ft.Icons.REFRESH,
                style=ft.ButtonStyle(bgcolor=BTN_BG, color=BTN_TEXT)),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        padding=ft.Padding(16, 16, 16, 16),
    )

    panel = ft.Column(
        [
            barra_loading,
            module_header("Sustitución", "Reemplazo y trueque de guardias"),
            ft.Divider(height=1, color=DIVIDER),
            form_card,
            ft.Container(height=8),
            zona_resultados,
            no_data_container,
        ],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    page.run_task(cargar_asignaciones)

    return {"panel": panel, "cargar": cargar_asignaciones}
