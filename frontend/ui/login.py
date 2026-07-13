import asyncio

import flet as ft
import httpx
from config import URL_BACKEND
from theme import *


def LoginScreen(page: ft.Page, on_login_exitoso):
    outer_ref = ft.Ref[ft.Container]()
    es_registro = False

    CARD_BG = "#121212"
    CARD_BORDER = "#2A2A2A"

    txt_usuario = ft.TextField(
        label="Usuario",
        width=340,
        prefix_icon=ft.Icons.PERSON,
        border_color="#333333",
        focused_border_color="#555555",
        text_style=ft.TextStyle(color=TEXT),
        label_style=ft.TextStyle(color=TEXT_SECONDARY, weight=ft.FontWeight.W_500),
        bgcolor=BG,
        border_radius=10,
    )
    txt_password = ft.TextField(
        label="Contrase\u00f1a",
        width=340,
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK,
        border_color="#333333",
        focused_border_color="#555555",
        text_style=ft.TextStyle(color=TEXT),
        label_style=ft.TextStyle(color=TEXT_SECONDARY, weight=ft.FontWeight.W_500),
        bgcolor=BG,
        border_radius=10,
    )
    txt_confirmar = ft.TextField(
        label="Confirmar contrase\u00f1a",
        width=340,
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK,
        border_color="#333333",
        focused_border_color="#555555",
        text_style=ft.TextStyle(color=TEXT),
        label_style=ft.TextStyle(color=TEXT_SECONDARY, weight=ft.FontWeight.W_500),
        bgcolor=BG,
        border_radius=10,
        visible=False,
    )

    lbl_error = ft.Text("", color=ft.Colors.WHITE, size=14, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    error_card = ft.Container(
        content=lbl_error,
        bgcolor="#B71C1C",
        border=ft.Border(
            top=ft.BorderSide(1, "#E53935"),
            bottom=ft.BorderSide(1, "#E53935"),
            left=ft.BorderSide(1, "#E53935"),
            right=ft.BorderSide(1, "#E53935"),
        ),
        border_radius=8,
        padding=ft.Padding(left=16, top=14, right=16, bottom=14),
        visible=False,
        width=340,
    )

    txt_subtitulo = ft.Text("Inicia sesi\u00f3n para continuar", size=15, color=TEXT_SECONDARY)

    btn_login = ft.FilledButton(
        "Ingresar",
        width=340,
        height=48,
        icon=ft.Icons.LOGIN,
        style=ft.ButtonStyle(
            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD),
        ),
    )

    txt_toggle = ft.Text(
        "\u00bfNo tienes cuenta? Reg\u00edstrate",
        color=TEXT_SECONDARY,
        size=14,
        text_align=ft.TextAlign.CENTER,
    )

    def _hover_toggle(e):
        entered = e.data
        if isinstance(entered, str):
            entered = entered.lower() == "true"
        txt_toggle.color = "#4A9FF5" if entered else TEXT_SECONDARY
        page.update()

    btn_toggle = ft.Container(
        content=txt_toggle,
        on_click=lambda e: _toggle_modo(),
        on_hover=_hover_toggle,
        padding=ft.Padding(left=8, top=4, right=8, bottom=4),
    )

    async def _login(e):
        btn_login.disabled = True
        error_card.visible = False
        page.update()
        await asyncio.sleep(0.1)
        try:
            username = txt_usuario.value.strip()
            password = txt_password.value
            if not username or not password:
                raise ValueError("Completa todos los campos")

            if es_registro:
                if password != txt_confirmar.value:
                    raise ValueError("Las contrase\u00f1as no coinciden")
                if len(password) < 6:
                    raise ValueError("La contrase\u00f1a debe tener al menos 6 caracteres")

            async with httpx.AsyncClient() as cli:
                endpoint = f"{URL_BACKEND}/register" if es_registro else f"{URL_BACKEND}/login"
                resp = await cli.post(
                    endpoint,
                    params={"username": username, "password": password},
                )
                datos = resp.json()
                if "error" in datos:
                    lbl_error.value = datos["error"]
                    error_card.visible = True
                else:
                    if outer_ref.current:
                        outer_ref.current.opacity = 0
                        page.update()
                        await asyncio.sleep(0.25)
                    await on_login_exitoso(datos["token"], datos["usuario"])
                    return
        except ValueError as ex:
            lbl_error.value = str(ex)
            error_card.visible = True
        except Exception as ex:
            lbl_error.value = f"Error de conexi\u00f3n: {ex}"
            error_card.visible = True
        finally:
            btn_login.disabled = False
            page.update()

    def _toggle_modo():
        nonlocal es_registro
        es_registro = not es_registro
        if es_registro:
            txt_subtitulo.value = "Crea una cuenta para continuar"
            btn_login.text = "Registrarse"
            btn_login.icon = ft.Icons.PERSON_ADD
            txt_confirmar.visible = True
            txt_toggle.value = "\u00bfYa tienes cuenta? Inicia sesi\u00f3n"
        else:
            txt_subtitulo.value = "Inicia sesi\u00f3n para continuar"
            btn_login.text = "Ingresar"
            btn_login.icon = ft.Icons.LOGIN
            txt_confirmar.visible = False
            txt_confirmar.value = ""
            txt_toggle.value = "\u00bfNo tienes cuenta? Reg\u00edstrate"
        lbl_error.value = ""
        error_card.visible = False
        page.update()

    btn_login.on_click = lambda e: page.run_task(_login, e)

    def _on_keyboard(e: ft.KeyboardEvent):
        if e.key == "Enter":
            page.run_task(_login, None)

    page.on_keyboard_event = _on_keyboard

    card = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.SHIELD, color=PRIMARY, size=72),
            ft.Container(height=24),
            ft.Text("Sistema de Guardias", size=28, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Container(height=4),
            txt_subtitulo,
            ft.Container(height=36),
            txt_usuario,
            ft.Container(height=24),
            txt_password,
            ft.Container(height=8),
            txt_confirmar,
            ft.Container(height=8),
            error_card,
            ft.Container(height=12),
            btn_login,
            ft.Container(height=4),
            btn_toggle,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        width=412,
        bgcolor=CARD_BG,
        border=ft.Border(
            top=ft.BorderSide(1, CARD_BORDER),
            bottom=ft.BorderSide(1, CARD_BORDER),
            left=ft.BorderSide(1, CARD_BORDER),
            right=ft.BorderSide(1, CARD_BORDER),
        ),
        border_radius=20,
        padding=ft.Padding(left=36, top=48, right=36, bottom=48),
    )

    outer = ft.Container(
        ref=outer_ref,
        content=ft.Column([
            ft.Container(expand=1),
            card,
            ft.Container(expand=3),
        ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        ),
        bgcolor=BG,
        expand=True,
        opacity=1,
        animate_opacity=ft.Animation(250, ft.AnimationCurve.EASE_IN_OUT),
    )
    return outer
