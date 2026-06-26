# 🪖 Sistema de Gestión de Guardias Militares

Automatiza la asignación de turnos de guardia con **equidad**, **control de fatiga** y **trazabilidad**, adaptable a cualquier unidad militar.

---

## 📊 1. Diagrama de Casos de Uso

```mermaid
graph LR
    Admin["🧑‍💼 Administrador"]

    Importar["📥 Importar personal"]
    Asignar["⚙️ Asignar guardias"]
    Reasignar["🆘 Reasignar guardia"]
    GenerarPDF["📄 Generar reporte PDF"]
    Difundir["📢 Difundir turnos"]
    Restricciones["🔧 Configurar restricciones"]

    Admin --- Importar
    Admin --- Asignar
    Admin --- Reasignar
    Admin --- GenerarPDF
    Admin --- Difundir
    Admin --- Restricciones

    Reasignar -.->|include| Asignar
    Difundir -.->|extend| GenerarPDF
```
---

## 🧱 2. Diagrama de Arquitectura

```mermaid
graph TD
    Admin["🧑‍💼 Administrador"]
    
    subgraph Cliente["Cliente (Flet)"]
        UI["Interfaz de escritorio"]
    end
    
    subgraph Servidor["Servidor (FastAPI)"]
        Logica["Lógica de negocio y algoritmo de equidad"]
        ManejoErrores["Manejo de errores y reintentos"]
    end
    
    subgraph Datos["Capa de datos"]
        SQLite["SQLite (modo WAL)"]
        Env["Archivo .env (tokens)"]
    end
    
    subgraph Externo["Servicios externos"]
        WhatsApp["WhatsApp API"]
        Telegram["Telegram API"]
    end

    Admin --> UI
    UI -->|"HTTP/REST"| Logica
    Logica --> SQLite
    Logica --> ManejoErrores
    ManejoErrores -->|"Reintentos / Logs"| WhatsApp
    ManejoErrores -->|"Reintentos / Logs"| Telegram
    Logica -.->|"Lectura de credenciales"| Env
```
---

## 🗃️ 3. Diagrama Entidad-Relación (ER)

```mermaid
erDiagram
    SOLDADO ||--o{ ASIGNACION : "tiene (1..*)"
    GUARDIA ||--o{ ASIGNACION : "incluye (1..*)"
    PUNTO_GUARDIA ||--o{ GUARDIA : "ubica (1..*)"
    SOLDADO ||--o{ RESTRICCION : "posee (1..*)"
    ASIGNACION ||--o{ ASIGNACION : "reemplaza (0..1)"

    SOLDADO {
        INTEGER id_soldado PK
        TEXT cedula UK
        TEXT nombre
        TEXT apellido
        TEXT rango
        TEXT unidad
    }

    PUNTO_GUARDIA {
        INTEGER id_punto PK
        TEXT nombre UK
        TEXT descripcion
    }

    GUARDIA {
        INTEGER id_guardia PK
        DATETIME fecha_inicio
        DATETIME fecha_fin
        TEXT tipo
        TEXT estado
        INTEGER id_punto FK
    }

    ASIGNACION {
        INTEGER id_asignacion PK
        INTEGER id_soldado FK
        INTEGER id_guardia FK
        DATETIME fecha_asignacion
        BOOLEAN es_titular
        INTEGER id_asignacion_original FK
    }

    RESTRICCION {
        INTEGER id_restriccion PK
        INTEGER id_soldado FK
        DATE fecha_inicio
        DATE fecha_fin
        TEXT motivo
    }
```
---

## 🔁 4. Diagrama de Flujo – Asignación Automática

```mermaid
graph TD
    Titulo1["Asignación automática de guardias"]
    Inicio[Iniciar asignación automática] --> Cargar[Cargar reglas de fatiga y restricciones]
    Cargar --> Verificar[Verificar soldados con restricciones activas]
    Verificar --> Historial[Cargar historial de guardias]
    Historial --> Algoritmo[Ejecutar algoritmo de equidad]
    Algoritmo --> Factible{¿Se encontró solución?}
    Factible -- Sí --> Calendario[Generar calendario de guardias]
    Calendario --> Revisar[Revisar calendario propuesto]
    Revisar --> Decision{¿Confirmar?}
    Decision -- Sí --> OK[Guardias asignadas]
    Decision -- No --> Cancelar[Cancelar o reintentar]
    Cancelar --> Inicio
    Factible -- No --> Error[Sin personal suficiente para cubrir turnos]
    Error --> RevisarRest[Revisar reglas o personal disponible]
    RevisarRest --> Inicio

    style Titulo1 fill:none,stroke:none,color:#000
```
---

## 🔁 5. Diagrama de Flujo – Reasignación de Emergencia

```mermaid
graph TD
    Titulo2["Reasignación de emergencia"]
    Inicio[Seleccionar guardia con baja] --> Marcar[Marcar soldado como no disponible]
    Marcar --> Reglas[Cargar reglas de fatiga y restricciones activas]
    Reglas --> Buscar[Buscar candidatos válidos]
    Buscar --> Candidatos{¿Hay candidatos?}
    Candidatos -- Sí --> Evaluar[Evaluar equidad de cada candidato]
    Evaluar --> Seleccionar[Seleccionar mejor sustituto]
    Seleccionar --> Revisar[Revisar sustituto propuesto]
    Revisar --> Decision{¿Confirmar?}
    Decision -- Sí --> Actualizar[Crear nueva asignación y enlazar a la original]
    Actualizar --> OK[Reasignación completada]
    Decision -- No --> Reintentar[Cancelar o elegir otro]
    Reintentar --> Buscar
    Candidatos -- No --> SinCand[Sin candidatos válidos]
    SinCand --> RevisarReg[Revisar restricciones]
    RevisarReg --> Inicio

    style Titulo2 fill:none,stroke:none,color:#000
```
---

## 🔄 6. Diagrama de Secuencia – Flujo Completo del Sistema

```mermaid
sequenceDiagram
    actor Admin
    participant UI as Interfaz (Flet)
    participant API as API REST (FastAPI)
    participant Logica as Lógica de negocio
    participant DB as SQLite
    participant Msg as APIs de mensajería

    Note over Admin, DB: 1. Importación de personal
    Admin->>UI: Subir archivo Excel
    UI->>API: Enviar archivo
    API->>Logica: Validar estructura y datos
    Logica->>DB: Insertar soldados válidos
    DB-->>Logica: Confirmación
    Logica-->>API: Resultado validación
    API-->>UI: Respuesta
    UI-->>Admin: Mostrar resumen

    Note over Admin, DB: 2. Configuración previa
    Admin->>UI: Configurar restricciones y reglas
    UI->>API: Enviar parámetros
    API->>Logica: Procesar reglas de fatiga y exenciones
    Logica->>DB: Guardar restricciones activas
    DB-->>Logica: Confirmación
    Logica-->>API: Parámetros actualizados
    API-->>UI: Confirmación visual
    UI-->>Admin: Mostrar estado de configuración

    Note over Admin, DB: 3. Asignación automática
    Admin->>UI: Iniciar asignación
    UI->>API: Solicitar asignación
    API->>Logica: Ejecutar algoritmo de equidad
    Logica->>DB: Cargar historial, reglas de fatiga y restricciones
    DB-->>Logica: Datos de entrada para el cálculo
    Logica->>Logica: Calcular asignación equitativa
    Logica-->>API: Calendario generado
    API-->>UI: Calendario
    UI-->>Admin: Mostrar calendario

    Note over Admin, DB: 4. Generación de PDF
    Admin->>UI: Solicitar PDF
    UI->>API: Solicitar PDF
    API->>Logica: Generar PDF (ReportLab)
    Logica->>DB: Obtener datos del calendario
    DB-->>Logica: Datos del calendario
    Logica-->>API: PDF generado
    API-->>UI: PDF
    UI-->>Admin: Descargar PDF

    Note over Admin, Msg: 5. Difusión de turnos
    Admin->>UI: Difundir turnos
    UI->>API: Solicitar difusión
    API->>Logica: Preparar envío
    Logica->>DB: Obtener contactos
    DB-->>Logica: Lista de contactos
    Logica-->>API: Datos listos para envío
    API->>Msg: Enviar mensajes

    alt Conexión exitosa
        Msg-->>API: Confirmación
        API-->>UI: Difusión completada
        UI-->>Admin: Mostrar éxito
    else Fallo de conexión o límite
        Msg-->>API: Error
        API->>Logica: Registrar fallo y reintentar
        Logica->>DB: Guardar log de error
        API-->>UI: Notificar fallo
        UI-->>Admin: Alerta: difusión fallida
    end
```
---

## 🛠️ Stack Tecnológico

| Herramienta | Rol |
|-------------|-----|
| Python | Lenguaje principal |
| Flet | Interfaz de escritorio (Material Design 3) |
| FastAPI | API REST |
| SQLModel | ORM para la base de datos |
| SQLite | Base de datos local |
| Pandas | Lectura y validación de Excel |
| ReportLab | Generación de PDF |
| PyInstaller | Empaquetado en .exe |

---

## ⚡ Instalación

```bash
git clone https://github.com/Jaren2402/sistema-de-gestion-de-guardias.git
cd sistema-de-gestion-de-guardias
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Configurar variables de entorno
cd backend && uvicorn main:app --reload
```
---

## 🚀 Estado del Proyecto

- [x] Importación de soldados desde Excel
- [x] Asignación automática equitativa con ponderación de turnos
- [x] Gestión de restricciones (permisos, cursos)
- [x] Visualización de calendario por áreas
- [ ] Sustitución de emergencia
- [ ] Generación y envío de PDF
- [ ] Dashboard de estadísticas
- [x] Protección de rama y flujo de Pull Request

---

## 📄 Licencia

Este proyecto es de uso académico.

---

## 📄 Documentación

Para generar la documentación técnica del módulo de servicios, ejecute:

```bash
cd backend
python -m pydoc -w services
```