import calendar as cal_module
import flet as ft
from theme import (
    BTN_BG,
    BTN_DANGER,
    CAL_BG,
    CAL_BORDER,
    CAL_CELL,
    CAL_CELL_EMPTY,
    CAL_CELL_HEIGHT,
    CAL_CELL_HOVER,
    CAL_DAY_TEXT,
    CAL_DAY_TODAY,
    CAL_GRADIENT_END,
    CAL_GRADIENT_START,
    CAL_GLOW,
    CAL_HEADER_HEIGHT,
    CAL_HEADER_TEXT,
    CAL_PAST_BG,
    CAL_PAST_TEXT,
    ERROR,
    HOVER_ROW_BG,
    HOVER_ROW_TEXT,
    PRIMARY,
    SHIFT_DIURNO,
    SHIFT_NOCTURNO,
    SKELETON,
    SURFACE,
    SURFACE_LIGHT,
    TABLE_BG,
    TABLE_ROW,
    TEXT,
    TEXT_SECONDARY,
    WARNING,
)


def loading_bar():
    """Indeterminate progress bar for top-of-panel during data loading."""
    return ft.ProgressBar(value=None, color=PRIMARY, bgcolor=SURFACE_LIGHT, height=2, visible=False)


def block(height=20, width=None, expand=None, br=6):
    """A single gray skeleton block."""
    return ft.Container(height=height, width=width, expand=expand, bgcolor=SKELETON, border_radius=br)


def table_row(expands, height=40):
    """One skeleton table row."""
    return ft.Container(
        content=ft.Row([block(expand=e, height=16, br=4) for e in expands], spacing=10),
        bgcolor=TABLE_ROW,
        height=height,
        padding=ft.Padding(left=16, top=0, right=16, bottom=0),
    )


def table(header_expands, rows=5):
    """Full table skeleton: header + N body rows."""
    hdr = ft.Container(
        content=ft.Row([block(expand=e, height=16, br=4) for e in header_expands], spacing=10),
        bgcolor=SURFACE_LIGHT,
        padding=ft.Padding(left=16, top=12, right=16, bottom=12),
    )
    body = ft.Column(
        [table_row(header_expands) for _ in range(rows)],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
    return ft.Container(
        content=ft.Column([hdr, body]),
        expand=True,
        bgcolor=TABLE_BG,
        border_radius=10,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def kpi():
    """Skeleton for a KPI card."""
    return ft.Container(
        content=ft.Column([
            ft.Row([block(width=22, height=22, br=4), block(expand=True, height=22, br=4)]),
            block(width=80, height=14, br=4),
        ], spacing=4),
        bgcolor=SURFACE,
        padding=ft.Padding(left=14, top=12, right=14, bottom=12),
        border_radius=10,
        expand=True,
    )


def ring():
    """Skeleton for the equity ring (square placeholder)."""
    return ft.Container(width=130, height=130, bgcolor=SKELETON, border_radius=65)


def bar(label_width=90):
    """Skeleton for a horizontal bar chart row."""
    return ft.Container(
        content=ft.Row([
            block(width=label_width, height=14, br=3),
            block(expand=True, height=14, br=3),
            block(width=26, height=14, br=3),
        ], spacing=6),
        padding=ft.Padding(top=2, bottom=2, left=0, right=0),
    )


def hover_row(container, hover_color=HOVER_ROW_BG, animate_ms=120, pointer=False, invert=False,
              text_hover_color=HOVER_ROW_TEXT):
    orig_bg = container.bgcolor
    container.animate = ft.Animation(animate_ms, ft.AnimationCurve.EASE_OUT)
    if pointer:
        container.cursor = "pointer"

    def _walk(ctrl, action, val=None):
        result = []
        if isinstance(ctrl, ft.Text):
            if action == "set":
                ctrl.color = val
            elif action == "save":
                result.append((ctrl, ctrl.color))
        for child in getattr(ctrl, "controls", []) or []:
            result.extend(_walk(child, action, val))
        child = getattr(ctrl, "content", None)
        if child is not None:
            result.extend(_walk(child, action, val))
        return result

    def _on_hover(e, ob=orig_bg, hc=hover_color):
        if e.data:
            container.bgcolor = hc
            if invert:
                saved = _walk(container.content, "save")
                container._hover_saved = saved
                _walk(container.content, "set", text_hover_color)
        else:
            container.bgcolor = ob
            if invert and hasattr(container, "_hover_saved"):
                for ctrl, orig_c in container._hover_saved:
                    ctrl.color = orig_c
                container._hover_saved = None
        container.update()

    container.on_hover = _on_hover
    return container


def rank_item():
    """Skeleton for a ranking list item."""
    return ft.Container(
        content=ft.Row([
            block(width=20, height=14, br=3),
            block(expand=True, height=14, br=3),
            block(width=30, height=14, br=3),
        ], spacing=4),
        bgcolor=SURFACE,
        padding=ft.Padding(left=6, top=3, right=6, bottom=3),
        border_radius=5,
    )


def module_header(title, subtitle):
    """Module page heading: bold large title + subtle subtitle."""
    return ft.Column([
        ft.Text(title, size=34, weight=ft.FontWeight.BOLD, color=TEXT),
        ft.Text(subtitle, size=18, color=TEXT_SECONDARY),
    ], spacing=2)


def placeholder(icon=ft.Icons.INFO_OUTLINE, text="Sin datos."):
    """Empty-state: centered icon + italic text."""
    return ft.Container(
        content=ft.Column([
            ft.Icon(icon, size=64, color=TEXT_SECONDARY),
            ft.Text(text, size=16, color=TEXT_SECONDARY, italic=True, text_align=ft.TextAlign.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        alignment=ft.Alignment(0, 0),
        expand=True,
        padding=60,
    )


def no_data(icon=ft.Icons.INFO_OUTLINE, text="Sin datos."):
    """Mounted placeholder: a Container wrapping the placeholder for toggling visibility."""
    return ft.Container(
        content=placeholder(icon, text),
        expand=True,
        visible=True,
        alignment=ft.Alignment(0, 0),
    )


def toast(page, mensaje, tipo="success"):
    iconos = {"success": ft.Icons.CHECK_CIRCLE, "error": ft.Icons.ERROR, "warning": ft.Icons.WARNING}
    colores = {"success": "#238636", "error": ERROR, "warning": WARNING}
    snack = ft.SnackBar(
        content=ft.Row([
            ft.Icon(iconos.get(tipo, ft.Icons.INFO), color=ft.Colors.WHITE, size=20),
            ft.Text(mensaje, color=ft.Colors.WHITE, size=14),
        ], spacing=10),
        bgcolor=colores.get(tipo, "#2EA043"),
        duration=3500,
        open=True,
        margin=ft.Margin(left=20, bottom=60, right=20, top=0),
        shape=ft.RoundedRectangleBorder(radius=8),
    )
    page.overlay.append(snack)
    page.update()


def confirm_dialog(page, title, message, button_label, on_confirm, destructive=False):
    """Diálogo de confirmación moderno y reutilizable.

    Args:
        page: Flet page.
        title: Título del diálogo.
        message: Mensaje de cuerpo.
        button_label: Texto del botón de acción principal.
        on_confirm: Coroutine a ejecutar al confirmar.
        destructive: Si True, el botón principal se muestra en rojo.
    """
    btn_color = BTN_DANGER if destructive else PRIMARY

    def _close(e):
        dlg.open = False
        page.update()

    async def _run(e):
        dlg.open = False
        page.update()
        await on_confirm()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=TEXT),
        content=ft.Text(message, size=15, color=TEXT_SECONDARY),
        bgcolor=SURFACE,
        shape=ft.RoundedRectangleBorder(radius=12),
        actions=[
            ft.OutlinedButton(
                "Cancelar",
                on_click=_close,
                style=ft.ButtonStyle(
                    color=TEXT_SECONDARY,
                    side=ft.BorderSide(1, "#333333"),
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
            ),
            ft.FilledButton(
                button_label,
                on_click=lambda e: page.run_task(_run, e),
                style=ft.ButtonStyle(
                    bgcolor=btn_color,
                    color=ft.Colors.WHITE,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.show_dialog(dlg)
    page.update()


def shift_badge(turno):
    colors = {"diurno": SHIFT_DIURNO, "nocturno": SHIFT_NOCTURNO}
    color = colors.get(turno.lower(), TEXT_SECONDARY)
    return ft.Container(
        content=ft.Text(turno[0].upper(), size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        bgcolor=color,
        border_radius=4,
        width=22,
        height=22,
        alignment=ft.Alignment(0, 0),
    )


def calendar_cell(dia, asignaciones, on_click=None, month=None, year=None, highlight=None):
    if dia == 0:
        return ft.Container(
            content=ft.Text(
                str(dia) if dia > 0 else "",
                size=14,
                color=CAL_CELL_EMPTY,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
            ),
            alignment=ft.Alignment(0, 0),
            bgcolor=CAL_BG,
            aspect_ratio=1,
            border_radius=8,
            padding=6,
            expand=True,
        )

    now = __import__("datetime").datetime.now()
    is_past = (
        month is not None and year is not None
        and (year < now.year or (year == now.year and month < now.month) or (year == now.year and month == now.month and dia < now.day))
    )
    is_today = dia == now.day and month == now.month and year == now.year

    day_color = CAL_DAY_TEXT

    cell_opacity = 1.0
    if highlight is False:
        cell_opacity = 0.10

    cell = ft.Container(
        content=ft.Text(
            str(dia),
            size=19,
            color=ft.Colors.WHITE if is_today else day_color,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        ),
        alignment=ft.Alignment(0, 0),
        bgcolor=BTN_BG if is_today else CAL_CELL,
        border_radius=8,
        padding=8,
        aspect_ratio=1,
        expand=True,
        opacity=cell_opacity,
        ink=True,
        ink_color=PRIMARY,
        scale=ft.Scale(1.0),
        animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        shadow=[ft.BoxShadow(blur_radius=6, color="#000000", spread_radius=0, offset=ft.Offset(0, 2))],
    )

    if on_click and asignaciones:
        cell.on_click = on_click
        cell.cursor = "pointer"

        default_bg = BTN_BG if is_today else CAL_CELL
        def _hover(e):
            if e.data:
                cell.bgcolor = CAL_CELL_HOVER
                cell.scale = ft.Scale(1.05)
                cell.shadow = [ft.BoxShadow(blur_radius=10, color="#000000", spread_radius=1, offset=ft.Offset(0, 3))]
            else:
                cell.bgcolor = default_bg
                cell.scale = ft.Scale(1.0)
                cell.shadow = [ft.BoxShadow(blur_radius=6, color="#000000", spread_radius=0, offset=ft.Offset(0, 2))]
            cell.update()
        cell.on_hover = _hover

    return cell


def calendar_grid(year, month, assignments_by_day, on_day_click=None, matching_days=None):
    weeks = cal_module.monthcalendar(year, month)
    day_names = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]

    header = ft.Container(
        content=ft.Row(
            [ft.Container(
                ft.Text(name, size=12, color=CAL_HEADER_TEXT, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                expand=True,
                alignment=ft.Alignment(0, 0),
            ) for name in day_names],
            spacing=12,
        ),
        height=CAL_HEADER_HEIGHT,
        bgcolor=CAL_CELL,
        border_radius=ft.BorderRadius(top_left=8, top_right=8, bottom_left=0, bottom_right=0),
        padding=ft.Padding(left=4, top=8, right=4, bottom=8),
    )

    rows = []
    for week in weeks:
        cells = []
        for day_num in week:
            day_assignments = assignments_by_day.get(day_num, [])

            def make_click(d, a):
                def _on_click(e):
                    if on_day_click:
                        on_day_click(d, a)
                return _on_click

            hl = None
            if matching_days is not None and day_num > 0:
                hl = day_num in matching_days

            cells.append(calendar_cell(
                day_num,
                day_assignments,
                on_click=make_click(day_num, day_assignments) if day_assignments else None,
                month=month,
                year=year,
                highlight=hl,
            ))
        rows.append(ft.Row(cells, spacing=12, expand=True))

    body = ft.Column(rows, spacing=12, expand=True)

    return ft.Container(
        content=ft.Column([header, body], spacing=0, expand=True),
        bgcolor=CAL_BG,
        border_radius=8,
        padding=8,
        width=515,
    )


def day_details_popup(page, dia, mes, año, punto, asignaciones):
    turno_groups = {}
    for a in asignaciones:
        t = a["turno"].capitalize()
        turno_groups.setdefault(t, []).append(a)

    turno_colors = {"Diurno": SHIFT_DIURNO, "Nocturno": SHIFT_NOCTURNO}

    items = []
    for turno, guardias in turno_groups.items():
        color = turno_colors.get(turno, TEXT_SECONDARY)
        items.append(ft.Chip(
            label=ft.Text(turno.upper(), size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            bgcolor=color,
            padding=ft.Padding(left=8, top=4, right=8, bottom=4),
        ))
        for g in guardias:
            items.append(ft.Container(
                content=ft.Row([
                    ft.Container(width=3, height=40, bgcolor=color, border_radius=2),
                    ft.Column([
                        ft.Text(f"{g['nombre'].capitalize()} {g['apellido'].capitalize()}", size=18, color=TEXT, weight=ft.FontWeight.W_500),
                        ft.Text(f"{g.get('rango', '')}  ·  Cédula {g['cedula']}", size=14, color=TEXT_SECONDARY),
                    ], spacing=1, expand=True),
                ], spacing=8),
                padding=ft.Padding(left=8, top=4, right=0, bottom=4),
            ))
        items.append(ft.Container(height=6))

    title = f"{dia} de {mes} — {punto}"

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=TEXT),
        content=ft.Container(
            content=ft.Column(items, spacing=4, scroll=ft.ScrollMode.AUTO),
            width=380,
            height=200,
        ),
        bgcolor=SURFACE,
        shape=ft.RoundedRectangleBorder(radius=12),
        actions=[
            ft.TextButton(
                "Cerrar",
                on_click=lambda e: _close(),
                style=ft.ButtonStyle(color=TEXT_SECONDARY),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def _close():
        dlg.open = False
        page.update()

    page.show_dialog(dlg)
    page.update()
