from database import engine
from sqlmodel import Session
from services import confirmar_sustitucion, confirmar_trueque, obtener_historial_sustituciones
from models import Asignacion

with Session(engine) as session:
    print("=" * 50)
    print("1. Ejecutando SUSTITUCIÓN SIMPLE (ID 1 -> Soldado 3)")
    r_simple = confirmar_sustitucion(1, 3, session)
    print(r_simple)
    
    print("\n2. Ejecutando TRUEQUE (ID 3 <-> ID 5, Soldado 2)")
    r_trueque = confirmar_trueque(3, 5, 2, session)
    print(r_trueque)
    
    print("\n3. Consultando HISTORIAL de mayo 2026:")
    historial = obtener_historial_sustituciones(5, 2026, session)
    for h in historial:
        print(f"  - Fecha: {h['fecha']}, Turno: {h['turno']}, Punto: {h['punto']}")
        print(f"    Titular original: {h['titular_original']}")
        print(f"    Sustituto: {h['sustituto']}")
        print(f"    Tipo: {h['tipo']}")
        print()
    
    if not historial:
        print("  (No se encontraron sustituciones)")