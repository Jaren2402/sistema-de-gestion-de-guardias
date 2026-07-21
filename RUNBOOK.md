# RUNBOOK — Sistema de Gestión de Guardias Militares

URL de producción: https://guardias-militares.up.railway.app

---

## Diagnóstico

### Verificar salud del sistema
```bash
curl https://guardias-militares.up.railway.app/health
```
Respuesta esperada:
```json
{"status": "ok", "database": "conectada", "timestamp": "2026-07-21T10:00:00"}
```
- `status: "ok"` → todo funciona
- `status: "degradado"` → la base de datos no responde
- Si no hay respuesta (404, 502, timeout) → el servidor no está corriendo o Railway lo durmió

### Revisar logs
Los logs se ven desde el dashboard de Railway:
1. Ir a https://railway.app/project
2. Seleccionar el proyecto
3. Ir a la pestaña **Deployments**
4. Hacer clic en el deployment activo
5. Ir a la pestaña **Logs**

Los logs están en formato JSON. Filtrar por nivel:
```
{"timestamp":"...","level":"ERROR","message":"...","correlation_id":"..."}
```

### Railway: conexión al proyecto
```bash
# Instalar Railway CLI (opcional)
npm i -g @railway/cli

# Vincular al proyecto
railway link

# Ver logs desde CLI
railway logs
```

---

## Protocolo ante caídas

### Nivel 1 — Reportar (cualquier usuario)
1. Si aparece un error con código (`"Reporte el código: X7F3"`), anotar el código
2. Reportar a la persona encargada con:
   - Código de error
   - Qué estaba haciendo cuando ocurrió
   - Captura de pantalla si es posible

### Nivel 2 — Diagnóstico y reinicio (encargado)
1. Ir al dashboard de Railway → Deployments → Logs
2. Buscar el código reportado: escribir `X7F3` en el campo de búsqueda de logs
3. Si el servidor no responde:
   ```bash
   # Hacer redeploy desde Railway Dashboard:
   # Ir a Deployments → clic en "Redeploy"
   
   # O desde Railway CLI:
   railway up
   ```
4. Si tras el redeploy el error persiste, pasar a Nivel 3

### Nivel 3 — Escalar (desarrollador)
1. Revisar el estado de las variables de entorno en Railway Dashboard → **Variables**
   - Verificar que `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, etc. estén configuradas
2. Verificar que el repositorio vinculado tiene el código correcto
3. Si la base de datos está corrupta:
   - Railway tiene discos efímeros (los datos se pierden al redeploy si no hay backup)
   - Si se configuró un volumen persistente, revisar Railway Dashboard → **Volumes**
4. Si no se encuentra la causa, probar en local para aislar el error

---

## Recuperación

> **⚠️ Importante:** Railway no persiste la base de datos por defecto. Al redeployar, los datos se pierden.  
> Si querés persistencia, se debe configurar un volumen o usar una BD externa.

### Regla 3-2-1
- **3** copias de los datos
- **2** soportes diferentes (ej. servidor + local)
- **1** copia fuera del sitio (ej. Google Drive, NAS)

### Archivos a respaldar
| Archivo | Ruta | Frecuencia sugerida |
|---------|------|---------------------|
| Base de datos | `data/guardias.db` | Diaria (descargar vía Railway) |
| Variables de entorno | `.env` / Railway Dashboard | Solo al cambiar |
| Código fuente | `backend/`, `frontend/` | Por cada release (git push) |

### Restaurar desde backup
```bash
# 1. Si hay backup local de la BD, subirla:
#    - Ir a Railway Dashboard → proyecto
#    - Agregar un comando de inicio que copie el backup
#    - O usar un volumen persistente

# 2. Hacer redeploy
# 3. Verificar health endpoint
curl https://guardias-militares.up.railway.app/health
```

### Recuperación desde cero (desastre total)
```bash
# 1. Clonar repositorio
git clone <repo-url>
cd sistema-de-gestion-de-guardias

# 2. (Opcional) Probar en local
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000

# 3. Hacer push a main (Railway auto-despliega)
git add .
git commit -m "fix: ..."
git push origin main

# 4. Verificar deploy en Railway Dashboard → Deployments
# 5. Probar health endpoint
curl https://guardias-militares.up.railway.app/health

# 6. Si no hay backup de BD, crear datos desde la app:
#    - Abrir https://guardias-militares.up.railway.app (frontend)
#    - Registrarse con usuario y contraseña
#    - Importar soldados desde Excel
#    - Configurar puntos de guardia
```
