"""
Rifa Online - App Flask
------------------------
Permite:
- Ver una cuadrícula de números disponibles/reservados/pagados
- Elegir números y reservarlos temporalmente
- Registrar datos del comprador
- Mostrar un QR de pago (cuenta bancaria / alias) para transferir
- Subir el comprobante de pago
- Panel de administrador para confirmar o rechazar pagos

Cómo correrlo:
    pip install flask --break-system-packages   # (o en un venv)
    python app.py
Luego abrir: http://127.0.0.1:5000
"""

import os
import sqlite3
import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, g
)
from werkzeug.utils import secure_filename

# ----------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "rifa.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "pdf", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "cambia-esta-clave-por-una-segura")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --- Datos configurables de la rifa ---
RIFA_CONFIG = {
    "nombre": "Rifa Pro Fondos",
    "precio_numero": 20,           # Bs por número
    "cantidad_numeros": 100,       # del 00 al 99
    "fecha_sorteo": "2026-08-15",
    # Datos de pago (para el QR / transferencia manual)
    "banco": "Banco FIE",
    "titular": "LIDER SANCHEZ ESPINOZA",
    "cuenta": "40019569146",
    "alias_qr": "rifa.lidersanchez@bancofie",  # texto que se codifica en el QR
}

ADMIN_USER = "LIDER"
ADMIN_PASS = "LIDER1611"   # <-- CAMBIA ESTO antes de publicar

RESERVA_MINUTOS = 15  # minutos que se reserva un número mientras el usuario paga


# ----------------------------------------------------------------------
# BASE DE DATOS
# ----------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    first_time = not os.path.exists(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS numeros (
            numero INTEGER PRIMARY KEY,
            estado TEXT NOT NULL DEFAULT 'disponible', -- disponible | reservado | pagado
            compra_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            celular TEXT NOT NULL,
            numeros TEXT NOT NULL,        -- ej "03,17,42"
            monto REAL NOT NULL,
            comprobante TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente', -- pendiente | confirmado | rechazado
            creado_en TEXT NOT NULL
        );
        """
    )
    if first_time:
        for n in range(RIFA_CONFIG["cantidad_numeros"]):
            db.execute("INSERT INTO numeros (numero, estado) VALUES (?, 'disponible')", (n,))
        db.commit()
    db.close()


def liberar_reservas_vencidas():
    """Vuelve a poner 'disponible' los números cuya compra pendiente ya expiró."""
    db = get_db()
    limite = datetime.datetime.now() - datetime.timedelta(minutes=RESERVA_MINUTOS)
    limite_str = limite.strftime("%Y-%m-%d %H:%M:%S")
    vencidas = db.execute(
        "SELECT id FROM compras WHERE estado='pendiente' AND creado_en < ? AND comprobante IS NULL",
        (limite_str,)
    ).fetchall()
    for row in vencidas:
        compra_id = row["id"]
        db.execute(
            "UPDATE numeros SET estado='disponible', compra_id=NULL WHERE compra_id=?",
            (compra_id,)
        )
        db.execute("UPDATE compras SET estado='expirado' WHERE id=?", (compra_id,))
    db.commit()


# ----------------------------------------------------------------------
# RUTAS PÚBLICAS
# ----------------------------------------------------------------------

@app.route("/")
def index():
    liberar_reservas_vencidas()
    db = get_db()
    numeros = db.execute("SELECT * FROM numeros ORDER BY numero").fetchall()
    return render_template(
        "index.html",
        numeros=numeros,
        config=RIFA_CONFIG,
    )


@app.route("/reservar", methods=["POST"])
def reservar():
    seleccionados = request.form.getlist("numeros")
    nombre = request.form.get("nombre", "").strip()
    celular = request.form.get("celular", "").strip()

    if not seleccionados:
        flash("Elige al menos un número.", "error")
        return redirect(url_for("index"))
    if not nombre or not celular:
        flash("Completa tu nombre y celular.", "error")
        return redirect(url_for("index"))

    db = get_db()
    liberar_reservas_vencidas()

    # Verificar que sigan disponibles
    for n in seleccionados:
        row = db.execute("SELECT estado FROM numeros WHERE numero=?", (n,)).fetchone()
        if row is None or row["estado"] != "disponible":
            flash(f"El número {n} ya no está disponible. Vuelve a elegir.", "error")
            return redirect(url_for("index"))

    monto = len(seleccionados) * RIFA_CONFIG["precio_numero"]
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur = db.execute(
        "INSERT INTO compras (nombre, celular, numeros, monto, estado, creado_en) VALUES (?, ?, ?, ?, 'pendiente', ?)",
        (nombre, celular, ",".join(seleccionados), monto, ahora),
    )
    compra_id = cur.lastrowid

    for n in seleccionados:
        db.execute(
            "UPDATE numeros SET estado='reservado', compra_id=? WHERE numero=?",
            (compra_id, n),
        )
    db.commit()

    return redirect(url_for("pagar", compra_id=compra_id))


@app.route("/pagar/<int:compra_id>", methods=["GET", "POST"])
def pagar(compra_id):
    db = get_db()
    compra = db.execute("SELECT * FROM compras WHERE id=?", (compra_id,)).fetchone()
    if compra is None:
        flash("Compra no encontrada.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        archivo = request.files.get("comprobante")
        if not archivo or archivo.filename == "":
            flash("Debes subir tu comprobante de pago.", "error")
            return redirect(url_for("pagar", compra_id=compra_id))

        ext = archivo.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXT:
            flash("Formato de archivo no permitido.", "error")
            return redirect(url_for("pagar", compra_id=compra_id))

        nombre_archivo = secure_filename(f"comprobante_{compra_id}.{ext}")
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        archivo.save(os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo))

        db.execute(
            "UPDATE compras SET comprobante=? WHERE id=?",
            (nombre_archivo, compra_id),
        )
        db.commit()
        flash("¡Comprobante recibido! Verificaremos tu pago pronto.", "ok")
        return redirect(url_for("gracias", compra_id=compra_id))

    return render_template("pagar.html", compra=compra, config=RIFA_CONFIG)


@app.route("/gracias/<int:compra_id>")
def gracias(compra_id):
    db = get_db()
    compra = db.execute("SELECT * FROM compras WHERE id=?", (compra_id,)).fetchone()
    return render_template("gracias.html", compra=compra)


# ----------------------------------------------------------------------
# ADMIN
# ----------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        u = request.form.get("usuario")
        p = request.form.get("password")
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["is_admin"] = True
            return redirect(url_for("admin_panel"))
        flash("Credenciales incorrectas.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("index"))


@app.route("/admin")
def admin_panel():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    db = get_db()
    liberar_reservas_vencidas()
    compras = db.execute("SELECT * FROM compras ORDER BY id DESC").fetchall()
    return render_template("admin.html", compras=compras)


@app.route("/admin/confirmar/<int:compra_id>")
def admin_confirmar(compra_id):
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    db = get_db()
    db.execute("UPDATE compras SET estado='confirmado' WHERE id=?", (compra_id,))
    db.execute("UPDATE numeros SET estado='pagado' WHERE compra_id=?", (compra_id,))
    db.commit()
    flash("Compra confirmada.", "ok")
    return redirect(url_for("admin_panel"))


@app.route("/admin/rechazar/<int:compra_id>")
def admin_rechazar(compra_id):
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    db = get_db()
    db.execute("UPDATE compras SET estado='rechazado' WHERE id=?", (compra_id,))
    db.execute("UPDATE numeros SET estado='disponible', compra_id=NULL WHERE compra_id=?", (compra_id,))
    db.commit()
    flash("Compra rechazada y números liberados.", "ok")
    return redirect(url_for("admin_panel"))


# ----------------------------------------------------------------------
# Se inicializa la base de datos apenas se importa el módulo, para que
# funcione tanto con "python app.py" como con un servidor de producción
# como gunicorn (que no ejecuta el bloque if __name__ == "__main__").
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
