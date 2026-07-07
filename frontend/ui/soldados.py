import flet as ft
import httpx
from config import URL_BACKEND

_EXP = [1, 2, 2, 1, 1]

def build(page: ft.Page, on_soldados_actualizados=None):
    """Construye la tabla de listado de soldados con filtros, búsqueda y selección."""
    _datos = []

    body = ft.Column(controls=[], scroll=ft.ScrollMode.ADAPTIVE, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    header = ft.Container(
        content=ft.Row([
            ft.Container(ft.Text("C\u00c9DULA", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_EXP[0]),
            ft.Container(ft.Text("NOMBRE", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_EXP[1]),
            ft.Container(ft.Text("APELLIDO", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_EXP[2]),
            ft.Container(ft.Text("RANGO", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_EXP[3]),
            ft.Container(ft.Text("UNIDAD", size=16, color="#DEDEDE", weight=ft.FontWeight.BOLD), expand=_EXP[4]),
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

    barra_progreso = ft.ProgressBar(visible=False)
    texto_estado = ft.Text()
    selector_archivo = ft.FilePicker()

    txt_buscar = ft.TextField(
        label="Buscar soldado",
        hint_text="Nombre, c\u00e9dula o rango",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        on_change=lambda e: _filtrar(),
    )

    def _filtrar():
        q = txt_buscar.value.strip().lower()
        filtrados = [s for s in _datos
                     if (not q or q in s["cedula"].lower()
                         or q in s["nombre"].lower()
                         or q in s["apellido"].lower()
                         or q in s["rango"].lower())]
        body.controls.clear()
        for s in filtrados:
            body.controls.append(ft.Container(
                content=ft.Row([
                    ft.Container(ft.Text(s["cedula"], size=16, color="#DEDEDE"), expand=_EXP[0]),
                    ft.Container(ft.Text(s["nombre"], size=16, color="#DEDEDE"), expand=_EXP[1]),
                    ft.Container(ft.Text(s["apellido"], size=16, color="#DEDEDE"), expand=_EXP[2]),
                    ft.Container(ft.Text(s["rango"], size=16, color="#DEDEDE"), expand=_EXP[3]),
                    ft.Container(ft.Text(s["unidad"], size=16, color="#DEDEDE"), expand=_EXP[4]),
                ]),
                bgcolor="#171C22",
                height=40,
                padding=ft.Padding(left=16, top=0, right=16, bottom=0),
            ))
        page.update()

    async def cargar():
        nonlocal _datos
        try:
            async with httpx.AsyncClient() as cliente:
                respuesta = await cliente.get(f"{URL_BACKEND}/soldados")
                _datos = respuesta.json()
                _filtrar()
                texto_estado.value = ""
        except Exception as ex:
            texto_estado.value = f"Error al cargar: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            barra_progreso.visible = False
            page.update()

    async def importar(e):
        resultado = await selector_archivo.pick_files(allowed_extensions=["xlsx"])
        if not resultado:
            return
        archivo = resultado[0]
        texto_estado.value = f"Enviando {archivo.name}..."
        texto_estado.color = ft.Colors.YELLOW
        barra_progreso.visible = True
        page.update()
        try:
            with open(archivo.path, "rb") as f:
                contenido = f.read()
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.post(
                    f"{URL_BACKEND}/importar_soldados",
                    files={"archivo": (archivo.name, contenido)}
                )
                datos = resp.json()
                texto_estado.value = datos.get("mensaje", str(datos))
                texto_estado.color = ft.Colors.GREEN
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            barra_progreso.visible = False
            page.update()
            await cargar()
            if on_soldados_actualizados:
                await on_soldados_actualizados()

    boton_importar = ft.Button(
        "Importar soldados desde Excel",
        on_click=importar,
        icon=ft.Icons.UPLOAD_FILE,
    )
    boton_refrescar = ft.Button(
        "Actualizar lista",
        on_click=lambda e: page.run_task(cargar),
        icon=ft.Icons.REFRESH,
    )

    panel = ft.Column([
        ft.Row([boton_importar, boton_refrescar]),
        ft.Divider(),
        ft.Row([txt_buscar]),
        cont_tabla,
    ])

    return {
        "panel": panel,
        "cargar": cargar,
        "selector_archivo": selector_archivo,
        "texto_estado": texto_estado,
        "barra_progreso": barra_progreso,
    }
