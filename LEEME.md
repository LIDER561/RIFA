# Rifa Online — Guía completa paso a paso

## Índice
1. Probarla en tu computadora
2. Configurar los datos de tu rifa
3. Subir el proyecto a GitHub
4. Publicarla en internet con Render
5. Notas importantes sobre la base de datos y los archivos subidos

---

## 1. Probarla en tu computadora

Necesitas Python instalado. Luego, en una terminal, dentro de la carpeta `rifa`:

```bash
pip install flask --break-system-packages
python app.py
```

Abre en el navegador: **http://127.0.0.1:5000**

Panel de administrador: **http://127.0.0.1:5000/admin/login**
(usuario `admin`, clave `admin123` — cámbialos antes de publicar, ver paso 2)

---

## 2. Configurar los datos de tu rifa

Abre `app.py` y edita el diccionario `RIFA_CONFIG` (cerca de la línea 30):

```python
RIFA_CONFIG = {
    "nombre": "Rifa Pro Fondos",
    "precio_numero": 20,
    "cantidad_numeros": 100,
    "fecha_sorteo": "2026-08-15",
    "banco": "Banco Ejemplo",
    "titular": "Nombre Apellido",
    "cuenta": "1234567890",
    "alias_qr": "rifa.ejemplo@banco",
}
```

Y cambia también, un poco más abajo:

```python
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"   # <-- pon una clave segura tuya
```

Guarda el archivo. Si ya habías generado `rifa.db` con la configuración anterior
(otra cantidad de números, por ejemplo), bórralo para que se regenere:
```bash
rm rifa.db
```

---

## 3. Subir el proyecto a GitHub

Si no tienes cuenta, crea una gratis en **github.com**.

**a) Crear el repositorio**
1. En GitHub, clic en el botón verde "New" (o el "+" arriba a la derecha → "New repository")
2. Nómbralo, por ejemplo `mi-rifa`
3. Déjalo público o privado, como prefieras
4. NO marques "Add a README" (ya tenemos archivos) → clic en "Create repository"

**b) Subir tu carpeta desde la terminal**

Dentro de la carpeta `rifa` (donde está `app.py`):

```bash
git init
git add .
git commit -m "Primera versión de mi rifa"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/mi-rifa.git
git push -u origin main
```

Reemplaza `TU-USUARIO` por tu usuario de GitHub. Te pedirá iniciar sesión
(o un token de acceso personal — GitHub te lo indicará en pantalla).

El archivo `.gitignore` ya está incluido para que NO subas la base de datos
(`rifa.db`) ni los comprobantes de pago (`static/uploads/`), que son datos
generados, no parte del código.

---

## 4. Publicarla en internet con Render

1. Crea una cuenta gratis en **render.com** (puedes entrar directo con tu cuenta de GitHub)
2. En el Dashboard: **"New +"** → **"Web Service"**
3. Conecta tu cuenta de GitHub si te lo pide, y selecciona el repositorio `mi-rifa`
4. Configura:
   - **Name:** el nombre que quieras (será parte de tu URL, ej. `mi-rifa.onrender.com`)
   - **Region:** la más cercana (Oregon suele ser la disponible en el plan gratis)
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Plan:** Free
5. En la sección **"Environment Variables"**, agrega una variable:
   - Key: `SECRET_KEY`
   - Value: cualquier texto largo y aleatorio (ej. genera uno en https://djecrety.ir)
6. Clic en **"Create Web Service"**

Render va a instalar dependencias y arrancar tu app. Al terminar (2-3 minutos),
te da una URL pública tipo `https://mi-rifa.onrender.com` — esa es la que
compartes con la gente para que compre sus números.

Cada vez que hagas `git push` con cambios, Render vuelve a desplegar
automáticamente.

---

## 5. Notas importantes

**Plan gratuito de Render "duerme" el servicio:**
Si nadie entra durante 15 minutos, el servicio se apaga y tarda unos 30-50
segundos en despertar la próxima vez que alguien entra. Es normal en el plan
gratis. Si esto te preocupa para el día del sorteo, puedes pasar a un plan
pago (~7 USD/mes) que no duerme.

**La base de datos se reinicia con cada despliegue nuevo:**
En el plan gratis, el disco no es permanente: si vuelves a hacer `git push`
(o Render reinicia el servicio), pierdes las compras y comprobantes guardados
hasta ese momento. Para una rifa real y sin sustos, te recomiendo:
- Revisar y confirmar los pagos seguido desde el panel admin (no dejar
  pendientes acumulados), o
- Cuando quieras algo más robusto, migrar a una base de datos externa
  (por ejemplo Render Postgres, que sí es persistente) — puedo ayudarte
  con eso si tu rifa crece.

**Seguridad básica antes de publicar:**
- Cambia `ADMIN_USER` / `ADMIN_PASS` por unos tuyos
- Usa una `SECRET_KEY` distinta (paso 4.5)
- No compartas el link de `/admin/login` públicamente
