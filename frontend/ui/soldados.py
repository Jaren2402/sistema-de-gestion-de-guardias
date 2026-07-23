import asyncio
import datetime as dt
import os
from collections import Counter

import flet as ft
import httpx
from api import get_token
from config import UPLOAD_DIR, URL_BACKEND
from skeleton import loading_bar, module_header, no_data, toast
from theme import *

_EXP = [1, 2, 2, 1, 1, 1]
_CARD_SHADOW = [ft.BoxShadow(blur_radius=8, color="#000000", spread_radius=0, offset=ft.Offset(0, 3))]


def _build_kpi_card(icon, label, value_text, accent):
    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(icon, size=18, color=ft.Colors.WHITE),
                            ft.Text(label, size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=accent,
                    border_radius=ft.BorderRadius(top_left=12, top_right=12, bottom_left=0, bottom_right=0),
                    padding=ft.Padding(14, 8, 14, 8),
                ),
                ft.Container(
                    content=ft.Text(value_text, size=28, weight=ft.FontWeight.BOLD, color=TEXT),
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding(0, 10, 0, 10),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        ),
        bgcolor=SURFACE,
        border_radius=12,
        shadow=_CARD_SHADOW,
        expand=True,
        height=100,
    )


def build(page: ft.Page, on_soldados_actualizados=None, on_ver_ficha=None):
    _datos = []

    barra_loading = loading_bar()
    body = ft.Column(
        controls=[],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        spacing=6,
    )

    header = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("CÉDULA", size=14, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_EXP[0]),
            ft.Container(ft.Text("NOMBRE", size=14, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_EXP[1]),
            ft.Container(ft.Text("APELLIDO", size=14, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_EXP[2]),
            ft.Container(ft.Text("RANGO", size=14, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_EXP[3]),
            ft.Container(ft.Text("UNIDAD", size=14, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_EXP[4]),
            ft.Container(ft.Text("REGISTRO", size=14, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), expand=_EXP[5]),
        ]),
        bgcolor=BTN_BG,
        padding=ft.Padding(16, 10, 16, 10),
        border_radius=ft.BorderRadius(top_left=12, top_right=12, bottom_left=0, bottom_right=0),
    )

    tabla_container = ft.Container(
        content=ft.Column([header, body], spacing=4),
        expand=True,
        bgcolor=SURFACE,
        border_radius=12,
        shadow=_CARD_SHADOW,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    no_data_container = no_data(ft.Icons.PEOPLE_OUTLINED, "No hay soldados. Importe desde Excel.")
    cont_tabla = ft.Container(content=tabla_container, expand=True, visible=False)

    texto_estado = ft.Text()

    kpi_total = ft.Text("0", size=28, weight=ft.FontWeight.BOLD, color=TEXT)
    kpi_rangos = ft.Column(spacing=0, scroll=ft.ScrollMode.ADAPTIVE)

    kpi_row = ft.Row(
        [_build_kpi_card(ft.Icons.PEOPLE, "Total Soldados", "0", PRIMARY)],
        spacing=12,
        expand=True,
    )

    def _actualizar_kpis(datos):
        total = len(datos)
        ranks = Counter(s.get("rango", "—") for s in datos)
        top_ranks = ranks.most_common(4)

        cards = [_build_kpi_card(ft.Icons.PEOPLE, "Total Soldados", str(total), PRIMARY_DARK)]

        rank_accents = [SHIFT_DIURNO, PRIMARY_DARK, SHIFT_DIURNO, PRIMARY_DARK]
        rank_icons = [ft.Icons.SHIELD, ft.Icons.STAR, ft.Icons.MILITARY_TECH, ft.Icons.VERIFIED]
        for i, (rango, count) in enumerate(top_ranks):
            accent = rank_accents[i % len(rank_accents)]
            icon = rank_icons[i % len(rank_icons)]
            cards.append(_build_kpi_card(icon, rango.capitalize(), str(count), accent))

        kpi_row.controls = cards

    def _parse_fecha(valor):
        try:
            return dt.datetime.strptime(valor.strip(), "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            return None

    txt_fecha_desde = ft.TextField(label="Desde", hint_text="YYYY-MM-DD", width=180,
                                    on_change=lambda e: _filtrar())
    txt_fecha_hasta = ft.TextField(label="Hasta", hint_text="YYYY-MM-DD", width=180,
                                    on_change=lambda e: _filtrar())

    txt_buscar = ft.TextField(
        label="Buscar soldado",
        hint_text="Nombre, cédula o rango",
        prefix_icon=ft.Icons.SEARCH,
        width=280,
        on_change=lambda e: _filtrar(),
    )

    lbl_contador = ft.Text("", size=13, color=TEXT_SECONDARY)

    def _limpiar_fecha(e):
        txt_fecha_desde.value = ""
        txt_fecha_hasta.value = ""
        _filtrar()
        page.update()

    btn_limpiar = ft.TextButton("Limpiar fechas", on_click=_limpiar_fecha, icon=ft.Icons.CLEAR)

    def _formatear_fecha(iso_str):
        if not iso_str:
            return "\u2014"
        try:
            d = dt.date.fromisoformat(iso_str[:10])
            return d.strftime("%d/%m/%Y")
        except ValueError:
            return "\u2014"

    def _filtrar():
        q = txt_buscar.value.strip().lower()
        fd = _parse_fecha(txt_fecha_desde.value)
        fh = _parse_fecha(txt_fecha_hasta.value)
        filtrados = [s for s in _datos
                     if (not q or q in s["cedula"].lower()
                         or q in s["nombre"].lower()
                         or q in s["apellido"].lower()
                         or q in s["rango"].lower())]
        if fd:
            filtrados = [s for s in filtrados if s.get("fecha_registro") and dt.date.fromisoformat(s["fecha_registro"][:10]) >= fd]
        if fh:
            filtrados = [s for s in filtrados if s.get("fecha_registro") and dt.date.fromisoformat(s["fecha_registro"][:10]) <= fh]

        body.controls.clear()
        for s in filtrados:
            row = ft.Container(
                content=ft.Row([
                    ft.Container(ft.Text(s["cedula"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.W_500), expand=_EXP[0]),
                    ft.Container(ft.Text(s["nombre"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_EXP[1]),
                    ft.Container(ft.Text(s["apellido"], size=14, color=TEXT_TABLE, weight=ft.FontWeight.BOLD), expand=_EXP[2]),
                    ft.Container(ft.Text(s["rango"].capitalize(), size=13, color=TEXT_TABLE, weight=ft.FontWeight.W_600), expand=_EXP[3]),
                    ft.Container(ft.Text(s["unidad"], size=13, color=TEXT_TABLE), expand=_EXP[4]),
                    ft.Container(ft.Text(_formatear_fecha(s.get("fecha_registro")), size=13, color=TEXT_TABLE), expand=_EXP[5]),
                ]),
                bgcolor=SURFACE,
                height=56,
                padding=ft.Padding(16, 0, 16, 0),
                border_radius=10,
                animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            )

            def _make_hover(c):
                def _on_hover(e):
                    if e.data:
                        c.bgcolor = HOVER_ROW_BG
                        c.shadow = [ft.BoxShadow(blur_radius=8, color="#000000", spread_radius=0, offset=ft.Offset(0, 2))]
                        c.scale = ft.Scale(1.01)
                    else:
                        c.bgcolor = SURFACE
                        c.shadow = []
                        c.scale = ft.Scale(1.0)
                    c.update()
                return _on_hover

            row.on_hover = _make_hover(row)
            row.cursor = "pointer"
            sid = s["id_soldado"]
            row.on_click = lambda e, sid=sid: page.run_task(_abrir_ficha, sid)
            body.controls.append(row)

        hay = len(filtrados) > 0
        cont_tabla.visible = hay
        no_data_container.visible = not hay
        lbl_contador.value = f"Mostrando {len(filtrados)} de {len(_datos)} soldados"
        _actualizar_kpis(_datos)
        page.update()

    async def _abrir_ficha(id_soldado):
        if on_ver_ficha:
            await on_ver_ficha(id_soldado)

    async def cargar():
        nonlocal _datos
        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.3)
        try:
            async with httpx.AsyncClient() as cliente:
                token = get_token(page)
                respuesta = await cliente.get(f"{URL_BACKEND}/soldados", headers={"Authorization": f"Bearer {token}"})
                _datos = respuesta.json()
                _filtrar()
                texto_estado.value = ""
        except Exception:
            toast(page, "Error al cargar soldados.", "error")
            body.controls.clear()
            body.controls.append(
                ft.Container(ft.Text("Error al cargar datos.", italic=True, color=TEXT_SECONDARY, size=14),
                             alignment=ft.Alignment(0, 0), padding=20))
        finally:
            barra_loading.visible = False
            page.update()

    async def importar(e):
        selector = ft.FilePicker()
        resultado = await selector.pick_files(allowed_extensions=["xlsx"])
        if not resultado:
            return
        archivo = resultado[0]

        barra_loading.visible = True
        page.update()
        await asyncio.sleep(0.15)

        try:
            if archivo.path is None:
                upload_url = page.get_upload_url(archivo.name, 600)
                await selector.upload([
                    ft.FilePickerUploadFile(name=archivo.name, upload_url=upload_url, method="PUT")
                ])
                archivo.path = f"{UPLOAD_DIR}/{archivo.name}"
                for _ in range(50):
                    if os.path.exists(archivo.path):
                        break
                    await asyncio.sleep(0.2)

            with open(archivo.path, "rb") as f:
                contenido = f.read()

            async with httpx.AsyncClient(timeout=30) as cliente:
                token = get_token(page)
                resp = await cliente.post(
                    f"{URL_BACKEND}/preview-importar",
                    files={"archivo": (archivo.name, contenido)},
                    headers={"Authorization": f"Bearer {token}"},
                )
                data = resp.json()

            if "error" in data:
                toast(page, data["error"], "error")
                barra_loading.visible = False
                page.update()
                return

            filas = data.get("filas", [])
            resumen = data.get("resumen", {})
            if not filas:
                toast(page, "El archivo no contiene soldados.", "warning")
                barra_loading.visible = False
                page.update()
                return

            _abrir_preview_modal(filas, resumen)

        except Exception:
            toast(page, "Error al procesar el archivo.", "error")
        finally:
            barra_loading.visible = False
            page.update()

    def _abrir_preview_modal(filas, resumen):
        preview_data = list(filas)
        _row_widgets = {}
        solo_errores = ft.Checkbox(
            label="Solo con problemas",
            value=False,
            on_change=lambda e: _render_preview_rows(),
        )
        lbl_resumen = ft.Text("", size=13, color=TEXT_SECONDARY)
        rows_container = ft.Column(spacing=4, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        btn_importar_modal = ft.FilledButton(
            "Importar",
            icon=ft.Icons.UPLOAD,
            style=ft.ButtonStyle(bgcolor=BTN_BG, color=BTN_TEXT),
            disabled=False,
        )

        def _cerrar_modal(e=None):
            dlg.open = False
            page.update()

        def _actualizar_resumen():
            visibles = [f for f in preview_data if f.get("_visible", True)]
            total = len(visibles)
            ok = sum(1 for f in visibles if f["status"] == "ok")
            err = sum(1 for f in visibles if f["status"] == "error")
            dup = sum(1 for f in visibles if f["status"] == "duplicado")
            importables = ok + dup
            lbl_resumen.value = f"{total} filas  ·  {ok} válidas  ·  {err} con errores  ·  {dup} duplicadas"
            btn_importar_modal.disabled = importables == 0
            btn_importar_modal.text = f"Importar {importables}" if importables > 0 else "Sin válidas"

        def _validate_row(row_idx):
            f = preview_data[row_idx]
            errores = []
            if not f["cedula"].strip():
                errores.append("Cédula vacía")
            if not f["nombre"].strip():
                errores.append("Nombre vacío")
            if not f["apellido"].strip():
                errores.append("Apellido vacío")
            if not f["rango"].strip():
                errores.append("Rango vacío")
            if not f["unidad"].strip():
                errores.append("Unidad vacía")
            f["errores"] = errores
            f["status"] = "error" if errores else "ok"

        def _actualizar_fila(row_idx):
            w = _row_widgets.get(row_idx)
            if not w:
                return
            f = preview_data[row_idx]
            status_icon = ft.Icons.CHECK_CIRCLE if f["status"] == "ok" else (
                ft.Icons.INFO if f["status"] == "error" else ft.Icons.CONTENT_COPY
            )
            status_color = PRIMARY if f["status"] == "ok" else TEXT_SECONDARY
            error_text = " · ".join(f["errores"]) if f["errores"] else ""
            w["icon"].name = status_icon
            w["icon"].color = status_color
            if error_text:
                w["err_label"].value = error_text
                w["err_label"].visible = True
            else:
                w["err_label"].visible = False
            _actualizar_resumen()

        def _render_preview_rows():
            q = solo_errores.value
            rows_container.controls.clear()
            _row_widgets.clear()
            for i, f in enumerate(preview_data):
                if q and f["status"] == "ok":
                    f["_visible"] = False
                    continue
                f["_visible"] = True

                status_icon = ft.Icons.CHECK_CIRCLE if f["status"] == "ok" else (
                    ft.Icons.INFO if f["status"] == "error" else ft.Icons.CONTENT_COPY
                )
                status_color = PRIMARY if f["status"] == "ok" else TEXT_SECONDARY
                error_text = " · ".join(f["errores"]) if f["errores"] else ""

                idx = i

                def _make_field(value, key, row_idx, hint):
                    field = ft.TextField(
                        value=value, width=140, text_size=13, dense=True,
                        content_padding=ft.Padding(8, 4, 8, 4),
                        border_color=DIVIDER,
                        text_style=ft.TextStyle(color=TEXT_TABLE),
                        cursor_color=PRIMARY,
                        hint_text=hint,
                        hint_style=ft.TextStyle(color=TEXT_SECONDARY, size=12),
                    )
                    def _on_change(e):
                        preview_data[row_idx][key] = e.control.value
                        _validate_row(row_idx)
                        _actualizar_fila(row_idx)
                    field.on_change = _on_change
                    return field

                cedula_field = _make_field(f["cedula"], "cedula", idx, "Cédula")
                nombre_field = _make_field(f["nombre"], "nombre", idx, "Nombre")
                apellido_field = _make_field(f["apellido"], "apellido", idx, "Apellido")
                rango_field = _make_field(f["rango"], "rango", idx, "Rango")
                unidad_field = _make_field(f["unidad"], "unidad", idx, "Unidad")

                status_icon_ctrl = ft.Icon(status_icon, size=16, color=status_color)
                err_label = ft.Text(
                    error_text, size=11, color=TEXT_SECONDARY, italic=True,
                ) if error_text else ft.Container(visible=False)

                def _make_delete(row_idx):
                    def _delete(e):
                        preview_data.pop(row_idx)
                        _render_preview_rows()
                        _actualizar_resumen()
                    return _delete

                def _make_edit(row_idx, ced, nom, ape, run, uni):
                    def _edit(e):
                        fields = _row_widgets.get(row_idx, {})
                        for ctrl in [ced, nom, ape, run, uni]:
                            ctrl.focus()
                            break
                    return _edit

                row_card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            status_icon_ctrl,
                            cedula_field,
                            nombre_field,
                            apellido_field,
                            rango_field,
                            unidad_field,
                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                icon_color=TEXT_SECONDARY,
                                icon_size=18,
                                tooltip="Editar",
                                on_click=_make_edit(idx, cedula_field, nombre_field, apellido_field, rango_field, unidad_field),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color=TEXT_SECONDARY,
                                icon_size=18,
                                tooltip="Quitar",
                                on_click=_make_delete(idx),
                            ),
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                        err_label,
                    ], spacing=2),
                    bgcolor=SURFACE_LIGHT,
                    border_radius=8,
                    padding=ft.Padding(10, 6, 10, 6),
                )
                _row_widgets[idx] = {"icon": status_icon_ctrl, "err_label": err_label}
                rows_container.controls.append(row_card)

            _actualizar_resumen()
            page.update()

        _render_preview_rows()

        async def _cerrar_e_importar(e):
            _cerrar_modal()
            await _ejecutar_importacion()

        async def _ejecutar_importacion():
            a_importar = [
                {k: f[k] for k in ("cedula", "nombre", "apellido", "rango", "unidad")}
                for f in preview_data if f["status"] != "error"
            ]
            if not a_importar:
                toast(page, "No hay filas válidas para importar.", "warning")
                return

            barra_loading.visible = True
            page.update()
            try:
                async with httpx.AsyncClient(timeout=30) as cliente:
                    token = get_token(page)
                    resp = await cliente.post(
                        f"{URL_BACKEND}/importar_filas",
                        json={"filas": a_importar},
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    data = resp.json()
                    if "error" in data:
                        toast(page, data["error"], "error")
                    else:
                        toast(page, data.get("mensaje", "Importación exitosa"), "success")
            except Exception:
                toast(page, "Error inesperado al importar.", "error")
            finally:
                barra_loading.visible = False
                page.update()
                await cargar()
                if on_soldados_actualizados:
                    await on_soldados_actualizados()

        btn_importar_modal.on_click = lambda e: page.run_task(_cerrar_e_importar, e)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.PREVIEW, size=22, color=PRIMARY),
                ft.Text("Vista Previa de Importación", size=18, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.CLOSE, icon_color=TEXT_SECONDARY, icon_size=20,
                    on_click=_cerrar_modal,
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([solo_errores, ft.Container(expand=True), lbl_resumen]),
                    ft.Divider(height=1, color=DIVIDER),
                    rows_container,
                ], spacing=10, expand=True),
                width=850,
                height=500,
            ),
            bgcolor=SURFACE,
            shape=ft.RoundedRectangleBorder(radius=12),
            actions=[
                ft.OutlinedButton(
                    "Cancelar",
                    on_click=_cerrar_modal,
                    style=ft.ButtonStyle(
                        color=TEXT_SECONDARY,
                        side=ft.BorderSide(1, DIVIDER),
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                ),
                btn_importar_modal,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    btn_importar = ft.FilledButton(
        "Importar Excel",
        on_click=lambda e: page.run_task(importar, e),
        icon=ft.Icons.UPLOAD_FILE,
        style=ft.ButtonStyle(bgcolor=BTN_BG, color=BTN_TEXT),
    )
    btn_refrescar = ft.FilledButton(
        "Actualizar",
        on_click=lambda e: page.run_task(cargar),
        icon=ft.Icons.REFRESH,
        style=ft.ButtonStyle(bgcolor=SURFACE_LIGHT, color=TEXT),
    )

    filtros_card = ft.Container(
        content=ft.Column([
            ft.Row(
                [txt_buscar, txt_fecha_desde, txt_fecha_hasta, btn_limpiar],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                [btn_importar, btn_refrescar, ft.Container(expand=True), lbl_contador],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ], spacing=10),
        bgcolor=SURFACE,
        border_radius=12,
        shadow=_CARD_SHADOW,
        padding=ft.Padding(16, 12, 16, 12),
    )

    panel = ft.Column(
        [
            barra_loading,
            module_header("Soldados", "Gestión y sincronización del personal militar"),
            ft.Divider(height=1, color=DIVIDER),
            texto_estado,
            kpi_row,
            ft.Container(height=8),
            filtros_card,
            ft.Container(height=8),
            cont_tabla,
            no_data_container,
        ],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    return {
        "panel": panel,
        "cargar": cargar,
        "texto_estado": texto_estado,
    }
