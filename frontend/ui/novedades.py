import asyncio

import flet as ft
import httpx
from api import get_token
from config import URL_BACKEND
from skeleton import loading_bar, module_header, no_data
from theme import *

_DIURNO = "#1565C0"
_NOCTURNO = "#616161"


def build(page: ft.Page):
    _asignaciones_raw = []
    _novedades_map = {}

    barra_loading = loading_bar()
    texto_resumen = ft.Text(size=15, color=TEXT_SECONDARY)

    selector_mes = ft.Dropdown(
        label="Mes",
        options=[ft.dropdown.Option(MESES[i]) for i in range(12)],
        value=MESES[4],
        width=120,
    )
    selector_ano = ft.TextField(label="Año", value="2026", width=100)
    selector_punto = ft.Dropdown(
        label="Punto",
        options=[ft.dropdown.Option("Todos")],
        value="Todos",
        width=160,
    )
    txt_buscar_soldado = ft.TextField(
        label="Buscar soldado",
        hint_text="Nombre o cédula",
        width=220,
        on_change=lambda e: _filtrar_y_renderizar(),
    )
    chk_solo_novedad = ft.Checkbox(
        label="Solo con novedad",
        value=False,
        on_change=lambda e: _filtrar_y_renderizar(),
    )

    lista_container = ft.Container(
        content=ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=20),
        padding=ft.Padding(left=20, right=20, top=20, bottom=0),
        expand=True,
    )

    no_data_container = no_data(ft.Icons.CAMPAIGN, "No hay guardias para este mes")

    async def abrir_dialogo_novedad(id_asignacion, descripcion_actual):
        campo_novedad = ft.TextField(
            label="Descripción de la novedad",
            value="" if descripcion_actual == "Sin novedad" else descripcion_actual,
            multiline=True,
            min_lines=2,
            max_lines=5,
            bgcolor="#111111",
            border_color="#333333",
            focused_border_color="#555555",
            border_radius=10,
            color=TEXT,
        )

        async def guardar_novedad(e):
            nueva_desc = campo_novedad.value or "Sin novedad"
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
                        texto_resumen.value = data["error"]
                        texto_resumen.color = ft.Colors.RED
                    else:
                        texto_resumen.value = ""
                    page.pop_dialog()
                    await _cargar()
            except Exception as ex:
                texto_resumen.value = f"Error: {ex}"
                texto_resumen.color = ft.Colors.RED
            finally:
                page.update()

        dialogo = ft.AlertDialog(
            title=ft.Text("Registrar Novedad", size=20, weight=ft.FontWeight.BOLD, color=TEXT),
            content=ft.Column([campo_novedad], tight=True),
            bgcolor=SURFACE,
            actions=[
                ft.OutlinedButton("Cancelar", on_click=lambda e: page.pop_dialog(), style=ft.ButtonStyle(color=TEXT_SECONDARY, overlay_color="#333333", side=ft.BorderSide(0))),
                ft.FilledButton("Guardar", on_click=guardar_novedad, style=ft.ButtonStyle(bgcolor=PRIMARY, color=ft.Colors.WHITE)),
            ],
        )
        page.show_dialog(dialogo)

    def _build_card(a):
        nov = _novedades_map.get(a["id_asignacion"])
        descripcion = nov["descripcion"] if nov else "Sin novedad"
        tiene_nov = nov is not None
        color = _DIURNO

        def _hover(e):
            e.control.bgcolor = "#191919" if e.data else SURFACE
            e.control.update()

        return ft.Container(
            content=ft.Row([
                ft.Container(width=6, bgcolor=color, border_radius=2),
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{a['dia']} {selector_mes.value}  ·  {a['turno'].capitalize()}  ·  {a['punto']}",
                                    size=17, color=TEXT, weight=ft.FontWeight.BOLD, expand=True),
                        ], spacing=6),
                        ft.Container(
                            content=ft.Text(f"{a['nombre']} {a['apellido']}  ·  {a['cedula']}", size=14, weight=ft.FontWeight.BOLD, color=TEXT_SECONDARY),
                            margin=ft.Margin(0, 4, 0, 0),
                        ),
                        ft.Container(height=14),
                        ft.Container(height=1, bgcolor="#333333"),
                        ft.Container(height=16),
                        ft.Text(descripcion, size=17, italic=not tiene_nov, color=ft.Colors.GREY_400 if not tiene_nov else None),
                    ], spacing=0, expand=True),
                    padding=ft.Padding(left=12, top=12, right=12, bottom=12),
                    expand=True,
                ),
            ], spacing=0),
            bgcolor=SURFACE,
            border_radius=24,
            height=200,
            expand=True,
            padding=0,
            on_click=lambda e, id_asig=a["id_asignacion"], desc=descripcion: page.run_task(abrir_dialogo_novedad, id_asig, desc),
            on_hover=_hover,
        )

    def _filtrar_y_renderizar():
        lista_container.content.controls.clear()
        punto_filtro = selector_punto.value
        q = txt_buscar_soldado.value.strip().lower()
        solo_nov = chk_solo_novedad.value

        filtradas = []
        for a in _asignaciones_raw:
            if punto_filtro != "Todos" and a["punto"] != punto_filtro:
                continue
            if q and q not in a["nombre"].lower() and q not in a["apellido"].lower() and q not in a["cedula"].lower():
                continue
            if solo_nov:
                if not _novedades_map.get(a["id_asignacion"]):
                    continue
            filtradas.append(a)

        total = len(_asignaciones_raw)
        con_nov = sum(1 for a in _asignaciones_raw if a["id_asignacion"] in _novedades_map)
        texto_resumen.value = f"\U0001f4ca Novedades: {con_nov} de {total} guardias"

        if not filtradas:
            lista_container.content.controls.append(
                ft.Container(
                    ft.Text("No hay guardias que coincidan con los filtros", italic=True, color=TEXT_SECONDARY, size=15),
                    alignment=ft.Alignment(0, 0), padding=30,
                )
            )
            no_data_container.visible = False
            lista_container.visible = True
            page.update()
            return

        filtradas.sort(key=lambda x: (x["dia"], 0 if x["turno"] == "diurno" else 1))
        for i in range(0, len(filtradas), 4):
            row_cards = []
            for j in range(4):
                idx = i + j
                if idx < len(filtradas):
                    row_cards.append(_build_card(filtradas[idx]))
                else:
                    row_cards.append(ft.Container(expand=True))
            lista_container.content.controls.append(
                ft.Row(row_cards, spacing=20)
            )

        no_data_container.visible = False
        lista_container.visible = True
        page.update()

    async def _cargar(e=None):
        mes = MESES.index(selector_mes.value) + 1
        ano = int(selector_ano.value)
        barra_loading.visible = True
        lista_container.visible = False
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
                    texto_resumen.value = ""
                    page.update()
                    return

                puntos = sorted(set(a["punto"] for a in _asignaciones_raw))
                selector_punto.options = [ft.dropdown.Option("Todos")] + [ft.dropdown.Option(p) for p in puntos]
                if selector_punto.value not in [o.key for o in selector_punto.options]:
                    selector_punto.value = "Todos"
                _filtrar_y_renderizar()

        except Exception as ex:
            texto_resumen.value = f"Error: {ex}"
            texto_resumen.color = ft.Colors.RED
            page.update()
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

    panel = ft.Column([
        barra_loading,
        module_header("Novedades", "Registro de eventos y observaciones por guardia"),
        ft.Divider(height=1, color=DIVIDER),
        ft.Row(
            [selector_mes, selector_ano, selector_punto, txt_buscar_soldado, chk_solo_novedad,
             ft.Container(width=16),
             ft.FilledButton("Cargar Guardias", on_click=_cargar)],
            spacing=8,
        ),
        texto_resumen,
        ft.Divider(height=1, color=DIVIDER),
        lista_container,
        no_data_container,
    ])

    return {"panel": panel}
