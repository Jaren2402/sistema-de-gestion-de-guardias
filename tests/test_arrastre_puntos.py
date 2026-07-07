import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from services import _calcular_puntos_mes, generar_calendario, obtener_estadisticas
from sqlmodel import Session, SQLModel, create_engine, text


def test_arrastre_con_decaimiento():
    """Verifica que el arrastre con decaimiento 0.5 mejora la equidad acumulada."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        rangos = ['cabo segundo','cabo primero','sargento segundo','sargento primero']
        for i in range(20):
            rango = rangos[i % len(rangos)]
            s.exec(text(
                f"INSERT INTO soldado (cedula, nombre, apellido, rango, unidad) "
                f"VALUES ('V{i:03d}', 'Test', 'Soldado{i}', '{rango}', 'Inf')"
            ))
        for pto in ['Entrada', 'Porton']:
            s.exec(text(f"INSERT INTO punto_guardia (nombre) VALUES ('{pto}')"))
        s.commit()

        for mes in range(1, 5):
            r = generar_calendario(mes, 2026, s)
            assert "error" not in r, f"Mes {mes} fallo: {r.get('error')}"

        eq_1 = obtener_estadisticas(4, 2026, s, meses=1)["equidad"]["porcentaje"]
        eq_4 = obtener_estadisticas(4, 2026, s, meses=4)["equidad"]["porcentaje"]

        assert eq_4 >= eq_1, (
            f"Equidad acumulada ({eq_4:.1f}%) deberia ser >= individual ({eq_1:.1f}%)"
        )


def test_arrastre_nuevo_soldado_converge():
    """Soldado nuevo converge tras un par de meses."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        for i in range(16):
            s.exec(text(
                f"INSERT INTO soldado (cedula, nombre, apellido, rango, unidad) "
                f"VALUES ('V{i:03d}', 'Vet', 'Soldado{i}', 'cabo segundo', 'Inf')"
            ))
        for pto in ['Entrada', 'Porton']:
            s.exec(text(f"INSERT INTO punto_guardia (nombre) VALUES ('{pto}')"))
        s.commit()

        r1 = generar_calendario(1, 2026, s)
        assert "error" not in r1

        s.exec(text(
            "INSERT INTO soldado (cedula, nombre, apellido, rango, unidad) "
            "VALUES ('V099', 'Nuevo', 'Ingresa', 'cabo segundo', 'Inf')"
        ))
        s.commit()

        for mes in [2, 3]:
            r = generar_calendario(mes, 2026, s)
            assert "error" not in r, f"Mes {mes} fallo: {r.get('error')}"

        pts_m3 = _calcular_puntos_mes(3, 2026, s)
        nuevo_pts = pts_m3.get(17, 0)
        media_m3 = sum(pts_m3.values()) / len(pts_m3)

        assert nuevo_pts <= media_m3 * 1.5, (
            f"Nuevo en mes 3 ({nuevo_pts} pts) excede 1.5x media ({media_m3:.1f} pts)"
        )
