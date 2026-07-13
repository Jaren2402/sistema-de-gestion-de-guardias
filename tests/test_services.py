import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlmodel import Session, SQLModel, create_engine, text

from backend.services import confirmar_sustitucion, generar_calendario


def test_generar_calendario_sin_soldados():
    """Si no hay soldados, debe devolver un error."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.exec(text("INSERT INTO usuario (username, password_hash, rol) VALUES ('test', 'x', 'admin')"))
        session.commit()
        resultado = generar_calendario(5, 2026, 1, session)

    assert "error" in resultado
    assert resultado["error"] == "No hay soldados registrados."


def test_generar_calendario_sin_puntos():
    """Si hay soldados pero no puntos de guardia, debe devolver un error."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.exec(text("INSERT INTO usuario (username, password_hash, rol) VALUES ('test', 'x', 'admin')"))
        # Insertar soldado con SQL textual (evita importar modelos)
        session.exec(
            text("INSERT INTO soldado (cedula, nombre, apellido, rango, unidad, id_usuario) VALUES ('V123', 'Prueba', 'Soldado', 'cabo segundo', 'Infantería', 1)")
        )
        session.commit()

        resultado = generar_calendario(5, 2026, 1, session)

    assert "error" in resultado
    assert resultado["error"] == "No hay puntos de guardia definidos."

def test_flujo_completo_sustitucion_simple():
    """Prueba integrada: anula la asignación original y crea la del sustituto."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.exec(text("INSERT INTO usuario (username, password_hash, rol) VALUES ('test', 'x', 'admin')"))
        # Insertar datos base con todos los campos NOT NULL
        session.exec(text(
            "INSERT INTO soldado (cedula, nombre, apellido, rango, unidad, id_usuario) "
            "VALUES ('V001', 'Titular', 'Prueba', 'cabo', 'Inf', 1)"
        ))
        session.exec(text(
            "INSERT INTO soldado (cedula, nombre, apellido, rango, unidad, id_usuario) "
            "VALUES ('V002', 'Sustituto', 'Prueba', 'cabo', 'Inf', 1)"
        ))
        session.exec(text("INSERT INTO punto_guardia (nombre, id_usuario) VALUES ('Entrada', 1)"))
        session.exec(text(
            "INSERT INTO guardia (fecha_inicio, fecha_fin, tipo, id_punto, estado) "
            "VALUES ('2026-05-01 07:00', '2026-05-01 19:00', 'diurno', 1, 'pendiente')"
        ))
        # Incluir es_anulada y fecha_asignacion
        session.exec(text(
            "INSERT INTO asignacion (id_soldado, id_guardia, es_titular, fecha_asignacion, es_anulada) "
            "VALUES (1, 1, 1, '2026-05-01 07:00', 0)"
        ))
        session.commit()

        # Ejecutar la sustitución
        resultado = confirmar_sustitucion(1, 2, session)

        # Verificar respuesta
        assert "mensaje" in resultado
        assert resultado["mensaje"] == "Sustitución realizada correctamente."

        # Verificar que la original fue anulada
        original = session.execute(text("SELECT es_anulada FROM asignacion WHERE id_asignacion=1")).fetchone()
        assert original[0] == 1  # 1 = True

        # Verificar que existe la nueva asignación del sustituto
        nueva = session.execute(text(
            "SELECT id_soldado, es_titular FROM asignacion WHERE id_asignacion_original=1 AND id_asignacion != 1"
        )).fetchone()
        assert nueva is not None
        assert nueva[0] == 2   # ID del sustituto
        assert nueva[1] == 1   # es_titular=True

def test_buscar_candidatos_sustitucion_ideal():
    """El candidato sin guardias previas aparece como ideal."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.exec(text("INSERT INTO usuario (username, password_hash, rol) VALUES ('test', 'x', 'admin')"))
        # Insertar 3 soldados
        session.exec(text("INSERT INTO soldado (cedula, nombre, apellido, rango, unidad, id_usuario) VALUES ('V001', 'A', 'Titular', 'cabo', 'Inf', 1)"))
        session.exec(text("INSERT INTO soldado (cedula, nombre, apellido, rango, unidad, id_usuario) VALUES ('V002', 'B', 'Ideal', 'cabo', 'Inf', 1)"))
        session.exec(text("INSERT INTO soldado (cedula, nombre, apellido, rango, unidad, id_usuario) VALUES ('V003', 'C', 'Fatigado', 'cabo', 'Inf', 1)"))
        session.exec(text("INSERT INTO punto_guardia (nombre, id_usuario) VALUES ('Entrada', 1)"))

        # Guardia que queremos sustituir (1 mayo diurno)
        session.exec(text("INSERT INTO guardia (fecha_inicio, fecha_fin, tipo, id_punto, estado) VALUES ('2026-05-01 07:00', '2026-05-01 19:00', 'diurno', 1, 'pendiente')"))
        # Guardia anterior para el fatigado (30 abril diurno)
        session.exec(text("INSERT INTO guardia (fecha_inicio, fecha_fin, tipo, id_punto, estado) VALUES ('2026-04-30 07:00', '2026-04-30 19:00', 'diurno', 1, 'pendiente')"))

        # Asignación original del titular en guardia 1
        session.exec(text("INSERT INTO asignacion (id_soldado, id_guardia, es_titular, fecha_asignacion, es_anulada) VALUES (1, 1, 1, '2026-05-01 07:00', 0)"))
        # Fatigado asignado a la guardia del 30 abril
        session.exec(text("INSERT INTO asignacion (id_soldado, id_guardia, es_titular, fecha_asignacion, es_anulada) VALUES (3, 2, 1, '2026-04-30 07:00', 0)"))
        session.commit()

        # Ejecutar búsqueda para la asignación 1
        from backend.services import buscar_candidatos_sustitucion
        resultado = buscar_candidatos_sustitucion(1, 1, session)

        # Verificar que hay candidatos
        assert "candidatos" in resultado
        candidatos = resultado["candidatos"]
        # Debe haber al menos 1 candidato (el soldado 2, ideal)
        assert len(candidatos) >= 1
        # El primer candidato debe ser el soldado 2 (sin fatiga)
        assert candidatos[0]["id_soldado"] == 2
        assert "Ideal" in candidatos[0]["estado"]

def test_confirmar_trueque():
    """El trueque debe intercambiar soldados entre dos asignaciones y crear novedad de auditoría."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.exec(text("INSERT INTO usuario (username, password_hash, rol) VALUES ('test', 'x', 'admin')"))
        # Insertar 2 soldados
        session.exec(text("INSERT INTO soldado (cedula, nombre, apellido, rango, unidad, id_usuario) VALUES ('V001', 'Pedro', 'González', 'cabo primero', 'Inf', 1)"))
        session.exec(text("INSERT INTO soldado (cedula, nombre, apellido, rango, unidad, id_usuario) VALUES ('V002', 'Andrés', 'Ramírez', 'sargento segundo', 'Inf', 1)"))
        # Insertar punto de guardia
        session.exec(text("INSERT INTO punto_guardia (nombre, id_usuario) VALUES ('Entrada', 1)"))
        # Insertar dos guardias (días distintos)
        session.exec(text("INSERT INTO guardia (fecha_inicio, fecha_fin, tipo, id_punto, estado) VALUES ('2026-05-10 07:00', '2026-05-10 19:00', 'diurno', 1, 'pendiente')"))
        session.exec(text("INSERT INTO guardia (fecha_inicio, fecha_fin, tipo, id_punto, estado) VALUES ('2026-05-15 07:00', '2026-05-15 19:00', 'diurno', 1, 'pendiente')"))
        # Insertar dos asignaciones originales
        session.exec(text("INSERT INTO asignacion (id_soldado, id_guardia, es_titular, fecha_asignacion, es_anulada) VALUES (1, 1, 1, '2026-05-10 07:00', 0)"))
        session.exec(text("INSERT INTO asignacion (id_soldado, id_guardia, es_titular, fecha_asignacion, es_anulada) VALUES (2, 2, 1, '2026-05-15 07:00', 0)"))
        session.commit()

        # Ejecutar trueque (intercambiar soldado 2 a la asignación 1)
        from backend.services import confirmar_trueque
        resultado = confirmar_trueque(1, 2, 2, session)

        # Verificar mensaje de éxito
        assert "mensaje" in resultado
        assert resultado["mensaje"] == "Trueque realizado correctamente."

        # Verificar que la asignación 1 ahora tiene al soldado 2
        a1 = session.execute(text("SELECT id_soldado FROM asignacion WHERE id_asignacion=1")).fetchone()
        assert a1[0] == 2

        # Verificar que la asignación 2 ahora tiene al soldado 1 (el original de la 1)
        a2 = session.execute(text("SELECT id_soldado FROM asignacion WHERE id_asignacion=2")).fetchone()
        assert a2[0] == 1

        # Verificar que se creó una novedad de auditoría
        novedad = session.execute(text("SELECT descripcion FROM novedad WHERE descripcion LIKE 'TRUEQUE:%'")).fetchone()
        assert novedad is not None
