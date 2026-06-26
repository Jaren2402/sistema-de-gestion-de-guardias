import flet as ft
import httpx
from config import URL_BACKEND


def build(page: ft.Page, on_sustitucion_completada=None):
    texto_estado = ft.Text()
    campo_id_asignacion = ft.TextField(label="ID de asignación a sustituir", width=250)
    boton_buscar = ft.Button("Buscar candidatos", on_click=lambda e: page.run_task(buscar_candidatos), icon=ft.Icons.SEARCH)
    zona_resultados = ft.Column()

    async def buscar_candidatos(e=None):
        id_asig = campo_id_asignacion.value.strip()
        if not id_asig:
            texto_estado.value = "⚠️ Debe ingresar un ID de asignación."
            texto_estado.color = ft.Colors.YELLOW
            page.update()
            return

        try:
            async with httpx.AsyncClient() as cliente:
                resp = await cliente.post(
                    f"{URL_BACKEND}/sustituir-guardia",
                    params={"id_asignacion_original": int(id_asig)}
                )
                datos = resp.json()
                zona_resultados.controls.clear()

                if "error" in datos:
                    texto_estado.value = f"❌ {datos['error']}"
                    texto_estado.color = ft.Colors.RED
                else:
                    intercambios = datos.get("intercambios", [])
                    candidatos = datos.get("candidatos", [])

                    if intercambios:
                        # Solo trueques
                        zona_resultados.controls.append(
                            ft.Text("🔄 Intercambios directos disponibles:", weight=ft.FontWeight.BOLD, size=16)
                        )
                        for inter in intercambios:
                            zona_resultados.controls.append(
                                ft.Card(
                                    content=ft.Container(
                                        content=ft.Column([
                                            ft.Text(f"{inter['rango_B']} {inter['nombre_B']} ({inter['cedula_B']})", weight=ft.FontWeight.BOLD),
                                            ft.Text(f"Intercambia su guardia del día {inter['dia_B']} ({inter['turno_B']})"),
                                            ft.ElevatedButton("Seleccionar", on_click=lambda e, id_s=inter['id_soldado_B'], id_a=inter['id_asignacion_B']: page.run_task(ejecutar_trueque, id_s, id_a)),
                                        ]),
                                        padding=10,
                                    ),
                                )
                            )
                    elif candidatos:
                        # Solo sustituciones simples (ya filtradas por el backend)
                        titulo = "📋 Candidatos disponibles:" if "Ideal" in candidatos[0]['estado'] else "⚠️ Solo disponibles estos candidatos (con fatiga):"
                        zona_resultados.controls.append(
                            ft.Text(titulo, weight=ft.FontWeight.BOLD, size=16)
                        )
                        for c in candidatos:
                            estado_icono = "✅" if "Ideal" in c['estado'] else "⚠️"
                            zona_resultados.controls.append(
                                ft.Card(
                                    content=ft.Container(
                                        content=ft.Column([
                                            ft.Text(f"{estado_icono} {c['rango']} {c['nombre']} ({c['cedula']})", weight=ft.FontWeight.BOLD),
                                            ft.ElevatedButton("Seleccionar", on_click=lambda e, id_s=c['id_soldado']: page.run_task(ejecutar_simple, id_s)),
                                        ]),
                                        padding=10,
                                    ),
                                )
                            )
                    else:
                        texto_estado.value = "ℹ️ No hay opciones disponibles para esta sustitución."
                        texto_estado.color = ft.Colors.GREY_400
                    texto_estado.value = ""
        except Exception as ex:
            texto_estado.value = f"Error: {ex}"
            texto_estado.color = ft.Colors.RED
        finally:
            page.update()

    async def ejecutar_trueque(id_soldado_B, id_asignacion_B):
        id_asig = int(campo_id_asignacion.value)
        async with httpx.AsyncClient() as cliente:
            resp = await cliente.post(
                f"{URL_BACKEND}/confirmar-trueque",
                params={
                    "id_asignacion_A": id_asig,
                    "id_asignacion_B": id_asignacion_B,
                    "id_soldado_B": id_soldado_B
                }
            )
            datos = resp.json()
            if "error" in datos:
                texto_estado.value = f"❌ {datos['error']}"
                texto_estado.color = ft.Colors.RED
            else:
                texto_estado.value = f"✅ {datos['mensaje']}. El calendario se refrescará automáticamente."
                texto_estado.color = ft.Colors.GREEN
                zona_resultados.controls.clear()
                campo_id_asignacion.value = ""
                # Llamar al callback de refresco si existe
                if on_sustitucion_completada:
                    on_sustitucion_completada()
            page.update()

    async def ejecutar_simple(id_soldado):
        id_asig = int(campo_id_asignacion.value)
        async with httpx.AsyncClient() as cliente:
            resp = await cliente.post(
                f"{URL_BACKEND}/confirmar-sustitucion",
                params={
                    "id_asignacion_original": id_asig,
                    "id_nuevo_soldado": id_soldado
                }
            )
            datos = resp.json()
            if "error" in datos:
                texto_estado.value = f"❌ {datos['error']}"
                texto_estado.color = ft.Colors.RED
            else:
                texto_estado.value = f"✅ {datos['mensaje']}. El calendario se refrescará automáticamente."
                texto_estado.color = ft.Colors.GREEN
                zona_resultados.controls.clear()
                campo_id_asignacion.value = ""
                # Llamar al callback de refresco si existe
                if on_sustitucion_completada:
                    on_sustitucion_completada()
            page.update()

    panel = ft.Column([
        ft.Text("Sustitución de Emergencia", weight=ft.FontWeight.BOLD, size=20),
        ft.Row([campo_id_asignacion, boton_buscar]),
        ft.Divider(),
        texto_estado,
        ft.Divider(),
        zona_resultados,
    ])

    return {"panel": panel}