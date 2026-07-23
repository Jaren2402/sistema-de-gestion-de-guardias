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
    _asignaciones_raw = []
    _novedades_map = {}

    barra_loading = loading_bar()

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
        options=[ft.dropdown.Option("Todos")],
        value="Todos",
        text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        border_color=DIVIDER, focused_border_color=PRIMARY,
    )
    txt_buscar_soldado = ft.TextField(
        label="Buscar soldado", hint_text="Nombre o cédula",
        width=220, on_change=lambda e: _filtrar_y_renderizar(),
        **_field_style(),
    )
    chk_solo_novedad = ft.Checkbox(
        label="Solo novedad", value=False,
        on_change=lambda e: _filtrar_y_renderizar(),
    )

    body = ft.Column(
        controls=[], scroll=ft.ScrollMode.ADAPTIVE, expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=22,
    )

    no_data_container = no_data(ft.Icons.CAMPAIGN, "No hay guardias para este mes")
    cont_grid = ft.Container(content=body, expand=True, visible=False)

    async def abrir_dialogo_novedad(id_asignacion, descripcion_actual):
        campo_novedad = ft.TextField(
            label="Descripción de la novedad",
            value="" if descripcion_actual == "Sin novedad" else descripcion_actual,
            multiline=True, min_lines=2, max_lines=5,
            border_color=DIVIDER, focused_border_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_TABLE, size=13),
            label_style=ft.TextStyle(color=TEXT_SECONDARY),
            cursor_color=PRIMARY,
        )

        async def guardar_novedad(e):
            nueva_desc = campo_novedad.value or "Sin novedad"
            page.pop_dialog()
            page.update()

            async def _confirmar():
                try:
                    async with httpx.AsyncClient() as cliente:
                        token = get_token(page)
                        resp = await cliente.post(
                            f"{URL_BACKEND}/novedades",
                            params={"id_asignacion": id_asignacion, "descripcion": nueva_desc},
                            headers={"Authorization": f"Bearer {token}"},
                        )
                        data = resp.json()
                        if "error" in data:
                            toast(page, data["error"], "error")
                        else:
                            toast(page, "Novedad guardada correctamente.", "success")
                            if nueva_desc and nueva_desc != "Sin novedad":
                                _novedades_map[id_asignacion] = {"id_asignacion": id_asignacion, "descripcion": nueva_desc}
                            else:
                                _novedades_map.pop(id_asignacion, None)
                            _filtrar_y_renderizar()
                except Exception:
                    toast(page, "Error inesperado. Intente de nuevo.", "error")

            confirm_dialog(
                page,
                title="Guardar novedad",
                message="¿Guardar novedad para esta guardia? La anterior se sobrescribirá.",
                button_label="Guardar",
                on_confirm=_confirmar,
            )

        dialogo = ft.AlertDialog(
            title=ft.Text("Registrar Novedad", size=20, weight=ft.FontWeight.BOLD, color=TEXT),
            content=ft.Column([campo_novedad], tight=True),
            bgcolor=SURFACE,
            shape=ft.RoundedRectangleBorder(radius=12),
            actions=[
                ft.OutlinedButton("Cancelar", on_click=lambda e: page.pop_dialog(),
                    style=ft.ButtonStyle(color=TEXT_SECONDARY, side=ft.BorderSide(1, DIVIDER))),
                ft.FilledButton("Guardar", on_click=guardar_novedad,
                    style=ft.ButtonStyle(bgcolor=BTN_BG, color=BTN_TEXT)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialogo)

    def _build_card(a):
        nov = _novedades_map.get(a["id_asignacion"])
        descripcion = nov["descripcion"] if nov else "Sin novedad"
        tiene_nov = nov is not None

        turno_color = SHIFT_DIURNO if a["turno"].lower() == "diurno" else SHIFT_NOCTURNO

        turno_badge = ft.Container(
            content=ft.Text(a["turno"].upper(), size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            bgcolor=turno_color,
            border_radius=4,
            padding=ft.Padding(8, 3, 8, 3),
        )

        nov_color = TEXT if tiene_nov else TEXT_SECONDARY
        nov_lines = ft.Text(descripcion, size=15, color=nov_color, italic=not tiene_nov, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS)

        card = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"DÍA {a['dia']}", size=15, weight=ft.FontWeight.BOLD, color=TEXT),
                            turno_badge,
                            ft.Container(expand=True),
                            ft.Text(a["punto"], size=14, color=TEXT_SECONDARY),
                        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Divider(height=1, color=DIVIDER),
                        ft.Text(f"{a['nombre']} {a['apellido']}", size=16, weight=ft.FontWeight.W_500, color=TEXT),
                        ft.Text(f"C.I. {a['cedula']}", size=14, color=TEXT_SECONDARY),
                        ft.Container(height=4),
                        nov_lines,
                        ft.Container(expand=True),
                        ft.Row([
                            ft.Container(expand=True),
                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED, icon_color=TEXT_SECONDARY, icon_size=16,
                                tooltip="Registrar novedad",
                                on_click=lambda e, id_a=a["id_asignacion"], desc=descripcion: page.run_task(abrir_dialogo_novedad, id_a, desc),
                            ),
                        ], spacing=0),
                    ], spacing=4, expand=True),
                    padding=ft.Padding(14, 10, 14, 8),
                    expand=True,
                ),
            ], spacing=0),
            bgcolor=SURFACE,
            border_radius=12,
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

    def _filtrar_y_renderizar():
        body.controls.clear()
        punto_filtro = selector_punto.value
        q = (txt_buscar_soldado.value or "").strip().lower()
        solo_nov = chk_solo_novedad.value

        filtradas = []
        for a in _asignaciones_raw:
            if punto_filtro != "Todos" and a["punto"] != punto_filtro:
                continue
            if q and q not in a["nombre"].lower() and q not in a["apellido"].lower() and q not in a["cedula"].lower():
                continue
            if solo_nov and not _novedades_map.get(a["id_asignacion"]):
                continue
            filtradas.append(a)

        filtradas.sort(key=lambda x: (x["dia"], 0 if x["turno"] == "diurno" else 1))

        for i in range(0, len(filtradas), 3):
            row_cards = []
            for j in range(3):
                idx = i + j
                if idx < len(filtradas):
                    row_cards.append(_build_card(filtradas[idx]))
                else:
                    row_cards.append(ft.Container(expand=True))
            body.controls.append(ft.Row(row_cards, spacing=22, expand=True))

        hay = len(filtradas) > 0
        cont_grid.visible = hay
        no_data_container.visible = not hay
        page.update()

    async def _cargar(e=None):
        mes = MESES.index(selector_mes.value) + 1
        ano = int(selector_ano.value)
        barra_loading.visible = True
        cont_grid.visible = False
        no_data_container.visible = False
        page.update()
        await asyncio.sleep(0.3)

        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                resp_cal = await cliente.get(f"{URL_BACKEND}/calendario-ver/{ano}/{mes}", headers={"Authorization": f"Bearer {token}"})
                nonlocal _asignaciones_raw
                _asignaciones_raw = resp_cal.json().get("asignaciones", [])

                resp_nov = await cliente.get(f"{URL_BACKEND}/novedades/{mes}/{ano}", headers={"Authorization": f"Bearer {token}"})
                nonlocal _novedades_map
                _novedades_map = {n["id_asignacion"]: n for n in resp_nov.json()}

                if not _asignaciones_raw:
                    no_data_container.visible = True
                    page.update()
                    return

                puntos = sorted(set(a["punto"] for a in _asignaciones_raw))
                selector_punto.options = [ft.dropdown.Option("Todos")] + [ft.dropdown.Option(p) for p in puntos]
                if selector_punto.value not in [o.key for o in selector_punto.options]:
                    selector_punto.value = "Todos"
                _filtrar_y_renderizar()

        except Exception:
            toast(page, "Error al cargar las guardias.", "error")
        finally:
            barra_loading.visible = False
            page.update()

    try:
        with httpx.Client() as cliente:
            token = get_token(page)
            resp = cliente.get(f"{URL_BACKEND}/puntos", headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                pts = [p["nombre"] for p in resp.json()]
                selector_punto.options = [ft.dropdown.Option("Todos")] + [ft.dropdown.Option(p) for p in pts]
                selector_punto.value = "Todos"
    except Exception:
        pass

    form_card = ft.Container(
        content=ft.Column([
            ft.Row([
                selector_mes, selector_ano, selector_punto, txt_buscar_soldado, chk_solo_novedad,
                ft.FilledButton("Cargar Guardias", on_click=_cargar, icon=ft.Icons.REFRESH,
                    style=ft.ButtonStyle(bgcolor=BTN_BG, color=BTN_TEXT)),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        ], spacing=12),
        padding=ft.Padding(16, 16, 16, 16),
    )

    panel = ft.Column(
        [
            barra_loading,
            module_header("Novedades", "Registro de eventos y observaciones por guardia"),
            ft.Divider(height=1, color=DIVIDER),
            form_card,
            ft.Container(height=8),
            cont_grid,
            no_data_container,
        ],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    return {"panel": panel}
