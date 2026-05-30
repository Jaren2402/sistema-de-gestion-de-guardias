# Guía de Contribución

## Ramas
Usamos **Git Flow simplificado**:

- `main` – Código estable y listo para producción.
- `feature/<nombre>` – Nuevas funcionalidades (ej. `feature/importar-soldados`).
- `fix/<nombre>` – Corrección de errores (ej. `fix/bug-calendario`).

## Commits
Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` nueva funcionalidad
- `fix:` corrección de bug
- `chore:` tareas de mantenimiento (dependencias, configuraciones)
- `docs:` cambios en documentación
- `style:` formato, punto y coma, etc.

## Pull Requests
1. Crea una rama desde `main`.
2. Realiza tus cambios y súbelos.
3. Abre un PR hacia `main`.
4. El pipeline de CI debe pasar (verde).
5. Al menos un revisor debe aprobar.
6. Haz merge usando "Squash and merge".

## Estándares de código
- Python: sigue PEP 8.
- Usamos `ruff` como linter.
