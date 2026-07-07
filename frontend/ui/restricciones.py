import asyncio

import flet as ft
import httpx
from config import URL_BACKEND


def build(page: ft.Page):
    """Construye la interfaz de gestión de restricciones: CRUD de períodos no disponibles por soldado."""
    _datos = []

    texto_estado = ft.Text(
        value="Para registrar una restriccion, primero importe soldados.",
        color=ft.Colors.GREY_400,
    )
    selector_soldado = ft.Dropdown(label="Soldado", options=[], width=300)
    campo_inicio = ft.TextField(label="Fecha inicio (YYYY-MM-DD)")
    campo_fin = ft.TextField(label="Fecha fin (YYYY-MM-DD)")
    campo_motivo = ft.TextField(label="Motivo")
    _exp = [2, 1, 1, 2, 1]

    body = ft.Column(controls=[], scroll=ft.ScrollMode.ADAPTIVE, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    header = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("SOLDADO", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[0]),
            ft.Container(ft.Text("INICIO", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[1]),
            ft.Container(ft.Text("FIN", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[2]),
            ft.Container(ft.Text("MOTIVO", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[3]),
            ft.Container(ft.Text("ACCIONES", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_exp[4]),
        ]),
        bgcolor="#25292E",
        padding=ft.Padding(left=16, top=12, right=16, bottom=12),
    )

    tabla_container = ft.Container(
        content=ft.Column([header, body]),
        expand=True,
        bgcolor="#121416",
        border_radius=10,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    cont_tabla = ft.Row([
        ft.Container(expand=1),
        ft.Container(content=tabla_container, expand=6, padding=ft.Padding(left=20, right=20, top=10, bottom=10)),
        ft.Container(expand=1),
    ], expand=True)
    txt_buscar = ft.TextField(
        label="Buscar restriccion",
        hint_text="Nombre del soldado o motivo",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        on_change=lambda e: _filtrar(),
    )

    def _filtrar():
        q = txt_buscar.value.strip().lower()
        filtrados = [r for r in _datos
                     if not q or q in r["nombre"].lower()
                     or q in r["motivo"].lower()]
        body.controls.clear()
        for r in filtrados:
            body.controls.append(ft.Container(
                content=ft.Row([
                    ft.Container(ft.Text(r["nombre"], size=16, color="#DEDEDE"), expand=_exp[0]),
                    ft.Container(ft.Text(r["fecha_inicio"], size=16, color="#DEDEDE"), expand=_exp[1]),
                    ft.Container(ft.Text(r["fecha_fin"], size=16, color="#DEDEDE"), expand=_exp[2]),
                    ft.Container(ft.Text(r["motivo"], size=16, color="#DEDEDE"), expand=_exp[3]),
                    ft.Container(ft.TextButton("Eliminar", icon=ft.Icons.DELETE, data=r["id"],
                                                on_click=lambda e, rid=r["id"]: page.run_task(eliminar, rid)),
                                 expand=_exp[4]),
                ]),
                bgcolor="#171C22",
                height=40,
                padding=ft.Padding(left=16, top=0, right=16, bottom=0),
            ))
        page.update()

    async def cargar_dropdown(max_intentos=3):
        intentos = 0
        while intentos < max_intentos:
            try:
                async with httpx.AsyncClient() as cliente:
                    resp = await cliente.get(f"{URL_BACKEND}/soldados")
                    datos = resp.json()
                    if datos:
                        selector_soldado.options = [
                            ft.dropdown.Option(
                                key=str(s["id_soldado"]),
                                text=f"{s['nombre']} {s['apellido']} ({s['cedula']})"
                            )
                            for s in datos
                        ]
                        texto_estado.value = "Lista de soldados cargada."
                        texto_estado.color = ft.Colors.GREEN
                        page.update()
                        return
            except Exception:
                pass
            intentos += 1
            await asyncio.sleep(1)
        texto_estado.value = "Para registrar una restriccion, primero importe soldados."
        texto_estado.color = ft.Colors.GREY_400
        page.update()

    async def cargar_tabla():
        nonlocal _datos
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.get(f"{URL_BACKEND}/restricciones")
                _datos = resp.json()
                _filtrar()
        except Exception as ex:
            texto_estado.value = f"Error al cargar restricciones: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    async def crear(e):
        if not selector_soldado.value:
            texto_estado.value = "Seleccione un soldado."
            texto_estado.color = ft.Colors.RED
            page.update()
            return
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.post(f"{URL_BACKEND}/restricciones", params={
                    "id_soldado": int(selector_soldado.value),
                    "fecha_inicio": campo_inicio.value,
                    "fecha_fin": campo_fin.value,
                    "motivo": campo_motivo.value,
                })
                datos = resp.json()
                if "error" in datos:
                    texto_estado.value = datos['error']
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = "Restriccion creada."
                    texto_estado.color = ft.Colors.GREEN
                    campo_motivo.value = ""
                    await cargar_tabla()
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    async def eliminar(id_restriccion: int):
        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.delete(f"{URL_BACKEND}/restricciones/{id_restriccion}")
                datos = resp.json()
                if "error" in datos:
                    texto_estado.value = datos['error']
                    texto_estado.color = ft.Colors.RED
                else:
                    texto_estado.value = "Restriccion eliminada."
                    texto_estado.color = ft.Colors.GREEN
                    await cargar_tabla()
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    boton_crear = ft.Button(
        "Anadir Restriccion",
        on_click=crear,
        icon=ft.Icons.ADD,
    )
    boton_refrescar = ft.Button(
        "Refrescar",
        on_click=lambda e: page.run_task(cargar_dropdown),
        icon=ft.Icons.REFRESH,
    )

    panel = ft.Column([
        ft.Text("Anadir restriccion:", weight=ft.FontWeight.BOLD),
        texto_estado,
        ft.Row([selector_soldado, campo_inicio, campo_fin]),
        ft.Row([campo_motivo, boton_crear]),
        ft.Divider(),
        ft.Row([boton_refrescar, txt_buscar]),
        cont_tabla,
    ])

    page.run_task(cargar_dropdown)

    return {
        "panel": panel,
        "cargar_dropdown": cargar_dropdown,
        "cargar_tabla": cargar_tabla,
        "texto_estado": texto_estado,
    }
