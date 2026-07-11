import flet as ft
from theme import (
    ERROR,
    HOVER_ROW_BG,
    HOVER_ROW_TEXT,
    PRIMARY,
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
