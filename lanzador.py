import os
import subprocess
import sys
import time


def iniciar_backend():
    """Inicia el servidor FastAPI en segundo plano."""
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=backend_dir
    )

def iniciar_frontend():
    """Inicia la aplicación Flet."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=frontend_dir
    )

if __name__ == "__main__":
    print("Iniciando servidor backend...")
    iniciar_backend()
    time.sleep(3)  # Esperar a que el backend esté listo
    print("Iniciando aplicación de escritorio...")
    iniciar_frontend()
    print("Sistema iniciado. Cierre la ventana de Flet para salir.")
