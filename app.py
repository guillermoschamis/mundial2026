from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
import sqlite3, os, json
from datetime import datetime, timezone

app = Flask(__name__)
app.secret_key = "mundial2026-secreto"
DATABASE = os.path.join(os.path.dirname(__file__), "mundial.db")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

# ─── CONFIG ───────────────────────────────────────────────────────────────────

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"api_key": ""}

# ─── DB ───────────────────────────────────────────────────────────────────────

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            es_admin INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupo TEXT NOT NULL,
            local TEXT NOT NULL,
            visitante TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            resultado TEXT,
            api_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS pronosticos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            partido_id INTEGER NOT NULL,
            pronostico TEXT NOT NULL,
            UNIQUE(usuario_id, partido_id),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(partido_id) REFERENCES partidos(id)
        );
    """)

    count = db.execute("SELECT COUNT(*) FROM partidos").fetchone()[0]
    if count == 0:
        # hora_inicio en UTC. Partidos del Mundial 2026 (horarios estimados)
        partidos = [
            # Grupo A
            ("A","México","Ecuador",         "2026-06-11T21:00:00+00:00"),
            ("A","Canadá","Marruecos",        "2026-06-12T18:00:00+00:00"),
            ("A","México","Canadá",           "2026-06-16T21:00:00+00:00"),
            ("A","Marruecos","Ecuador",       "2026-06-16T18:00:00+00:00"),
            ("A","Ecuador","Canadá",          "2026-06-20T21:00:00+00:00"),
            ("A","Marruecos","México",        "2026-06-20T21:00:00+00:00"),
            # Grupo B
            ("B","Uruguay","Kenia",           "2026-06-12T21:00:00+00:00"),
            ("B","Portugal","Zimbabwe",       "2026-06-12T18:00:00+00:00"),
            ("B","Uruguay","Portugal",        "2026-06-17T21:00:00+00:00"),
            ("B","Zimbabwe","Kenia",          "2026-06-17T18:00:00+00:00"),
            ("B","Kenia","Portugal",          "2026-06-21T21:00:00+00:00"),
            ("B","Zimbabwe","Uruguay",        "2026-06-21T21:00:00+00:00"),
            # Grupo C
            ("C","Alemania","Japón",          "2026-06-13T18:00:00+00:00"),
            ("C","Arabia Saudita","N. Zelanda","2026-06-13T21:00:00+00:00"),
            ("C","Alemania","Arabia Saudita", "2026-06-18T18:00:00+00:00"),
            ("C","N. Zelanda","Japón",        "2026-06-18T21:00:00+00:00"),
            ("C","Japón","Arabia Saudita",    "2026-06-22T21:00:00+00:00"),
            ("C","N. Zelanda","Alemania",     "2026-06-22T21:00:00+00:00"),
            # Grupo D
            ("D","España","Serbia",           "2026-06-13T21:00:00+00:00"),
            ("D","Brasil","Suiza",            "2026-06-14T18:00:00+00:00"),
            ("D","España","Brasil",           "2026-06-18T21:00:00+00:00"),
            ("D","Suiza","Serbia",            "2026-06-18T18:00:00+00:00"),
            ("D","Serbia","Brasil",           "2026-06-22T18:00:00+00:00"),
            ("D","Suiza","España",            "2026-06-22T18:00:00+00:00"),
            # Grupo E
            ("E","Francia","Colombia",        "2026-06-14T21:00:00+00:00"),
            ("E","Argentina","Croacia",       "2026-06-14T18:00:00+00:00"),
            ("E","Francia","Argentina",       "2026-06-19T21:00:00+00:00"),
            ("E","Croacia","Colombia",        "2026-06-19T18:00:00+00:00"),
            ("E","Colombia","Argentina",      "2026-06-23T21:00:00+00:00"),
            ("E","Croacia","Francia",         "2026-06-23T21:00:00+00:00"),
            # Grupo F
            ("F","Inglaterra","Senegal",      "2026-06-14T21:00:00+00:00"),
            ("F","Países Bajos","Irán",       "2026-06-15T18:00:00+00:00"),
            ("F","Inglaterra","Países Bajos", "2026-06-19T18:00:00+00:00"),
            ("F","Irán","Senegal",            "2026-06-19T21:00:00+00:00"),
            ("F","Senegal","Países Bajos",    "2026-06-23T18:00:00+00:00"),
            ("F","Irán","Inglaterra",         "2026-06-23T18:00:00+00:00"),
            # Grupo G
            ("G","Colombia","Eslovaquia",     "2026-06-15T18:00:00+00:00"),
            ("G","Ecuador","Qatar",           "2026-06-15T21:00:00+00:00"),
            ("G","Colombia","Ecuador",        "2026-06-20T18:00:00+00:00"),
            ("G","Qatar","Eslovaquia",        "2026-06-20T21:00:00+00:00"),
            ("G","Eslovaquia","Ecuador",      "2026-06-24T21:00:00+00:00"),
            ("G","Qatar","Colombia",          "2026-06-24T21:00:00+00:00"),
            # Grupo H
            ("H","Portugal","Polonia",        "2026-06-16T18:00:00+00:00"),
            ("H","Chile","Australia",         "2026-06-16T21:00:00+00:00"),
            ("H","Portugal","Chile",          "2026-06-20T18:00:00+00:00"),
            ("H","Australia","Polonia",       "2026-06-20T21:00:00+00:00"),
            ("H","Polonia","Chile",           "2026-06-24T18:00:00+00:00"),
            ("H","Australia","Portugal",      "2026-06-24T18:00:00+00:00"),
            # Grupo I
            ("I","Italia","Argelia",          "2026-06-15T21:00:00+00:00"),
            ("I","China","Trinidad y Tobago", "2026-06-15T18:00:00+00:00"),
            ("I","Italia","China",            "2026-06-19T21:00:00+00:00"),
            ("I","Trinidad y Tobago","Argelia","2026-06-19T18:00:00+00:00"),
            ("I","Argelia","China",           "2026-06-23T18:00:00+00:00"),
            ("I","Trinidad y Tobago","Italia","2026-06-23T18:00:00+00:00"),
            # Grupo J
            ("J","EE.UU.","Panamá",          "2026-06-13T21:00:00+00:00"),
            ("J","Bahréin","Guatemala",       "2026-06-13T18:00:00+00:00"),
            ("J","EE.UU.","Bahréin",         "2026-06-17T21:00:00+00:00"),
            ("J","Guatemala","Panamá",        "2026-06-17T18:00:00+00:00"),
            ("J","Panamá","Bahréin",          "2026-06-21T18:00:00+00:00"),
            ("J","Guatemala","EE.UU.",        "2026-06-21T18:00:00+00:00"),
            # Grupo K
            ("K","Bélgica","Costa de Marfil","2026-06-14T21:00:00+00:00"),
            ("K","Turquía","Indonesia",       "2026-06-14T18:00:00+00:00"),
            ("K","Bélgica","Turquía",         "2026-06-18T21:00:00+00:00"),
            ("K","Indonesia","Costa de Marfil","2026-06-18T18:00:00+00:00"),
            ("K","Costa de Marfil","Turquía", "2026-06-22T18:00:00+00:00"),
            ("K","Indonesia","Bélgica",       "2026-06-22T18:00:00+00:00"),
            # Grupo L
            ("L","Dinamarca","Bosnia",        "2026-06-13T18:00:00+00:00"),
            ("L","Filipinas","Guinea",        "2026-06-13T21:00:00+00:00"),
            ("L","Dinamarca","Filipinas",     "2026-06-17T18:00:00+00:00"),
            ("L","Guinea","Bosnia",           "2026-06-17T21:00:00+00:00"),
            ("L","Bosnia","Filipinas",        "2026-06-21T21:00:00+00:00"),
            ("L","Guinea","Dinamarca",        "2026-06-21T21:00:00+00:00"),
        ]
        db.executemany(
            "INSERT INTO partidos (grupo,local,visitante,hora_inicio) VALUES (?,?,?,?)",
            partidos
        )

    admin = db.execute("SELECT id FROM usuarios WHERE nombre='admin'").fetchone()
    if not admin:
        db.execute("INSERT INTO usuarios (nombre,password,es_admin) VALUES ('admin','admin123',1)")
    db.commit()
    db.close()


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def partido_bloqueado(hora_inicio_str):
    """Retorna True si el partido ya comenzó (hora_inicio <= ahora en UTC)."""
    try:
        from datetime import timezone
        dt = datetime.fromisoformat(hora_inicio_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= dt
    except Exception:
        return False

app.jinja_env.globals["partido_bloqueado"] = partido_bloqueado

@app.template_filter('enumerate')
def enumerate_filter(iterable):
    return enumerate(iterable)

@app.template_filter('hora_local')
def hora_local(s):
    """Formatea hora_inicio como 'Mié 11 Jun · 18:00 UTC'."""
    try:
        dt = datetime.fromisoformat(s)
        dias = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]
        meses = ["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return f"{dias[dt.weekday()]} {dt.day} {meses[dt.month]} · {dt.strftime('%H:%M')} UTC"
    except Exception:
        return s


# ─── AUTH ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("pronosticos_view"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        pwd = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM usuarios WHERE nombre=? AND password=?", (nombre,pwd)).fetchone()
        if user:
            session.update({"usuario_id":user["id"],"usuario_nombre":user["nombre"],"es_admin":user["es_admin"]})
            return redirect(url_for("pronosticos_view"))
        flash("Usuario o contraseña incorrectos.")
    return render_template("login.html")

@app.route("/registro", methods=["GET","POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        pwd = request.form["password"]
        if not nombre or not pwd:
            flash("Completá todos los campos.")
            return render_template("registro.html")
        db = get_db()
        try:
            db.execute("INSERT INTO usuarios (nombre,password) VALUES (?,?)", (nombre,pwd))
            db.commit()
            flash("¡Cuenta creada! Podés iniciar sesión.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Ese nombre de usuario ya existe.")
    return render_template("registro.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─── PRONÓSTICOS ──────────────────────────────────────────────────────────────

@app.route("/pronosticos", methods=["GET","POST"])
def pronosticos_view():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    uid = session["usuario_id"]

    if request.method == "POST":
        guardados = 0
        for key, val in request.form.items():
            if key.startswith("partido_"):
                partido_id = int(key.split("_")[1])
                p = db.execute("SELECT hora_inicio FROM partidos WHERE id=?", (partido_id,)).fetchone()
                if p and not partido_bloqueado(p["hora_inicio"]) and val in ("1","X","2"):
                    db.execute(
                        "INSERT INTO pronosticos (usuario_id,partido_id,pronostico) VALUES (?,?,?) "
                        "ON CONFLICT(usuario_id,partido_id) DO UPDATE SET pronostico=excluded.pronostico",
                        (uid, partido_id, val)
                    )
                    guardados += 1
        db.commit()
        flash(f"¡{guardados} pronóstico(s) guardado(s)!")
        return redirect(url_for("pronosticos_view"))

    grupos = db.execute("SELECT DISTINCT grupo FROM partidos ORDER BY grupo").fetchall()
    partidos_por_grupo = {}
    mis_pronosticos = {
        r["partido_id"]: r["pronostico"]
        for r in db.execute("SELECT partido_id,pronostico FROM pronosticos WHERE usuario_id=?", (uid,))
    }
    for g in grupos:
        partidos_por_grupo[g["grupo"]] = db.execute(
            "SELECT * FROM partidos WHERE grupo=? ORDER BY hora_inicio,id", (g["grupo"],)
        ).fetchall()

    return render_template("pronosticos.html", partidos_por_grupo=partidos_por_grupo, mis_pronosticos=mis_pronosticos)


# ─── TABLA ────────────────────────────────────────────────────────────────────

@app.route("/tabla")
def tabla():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    usuarios = db.execute("SELECT id,nombre FROM usuarios WHERE nombre != 'admin' ORDER BY nombre").fetchall()
    res_map = {r["id"]: r["resultado"] for r in
               db.execute("SELECT id,resultado FROM partidos WHERE resultado IS NOT NULL")}

    tabla = []
    for u in usuarios:
        pronos = db.execute("SELECT partido_id,pronostico FROM pronosticos WHERE usuario_id=?", (u["id"],)).fetchall()
        puntos = sum(1 for p in pronos if res_map.get(p["partido_id"]) == p["pronostico"])
        tabla.append({"nombre":u["nombre"],"puntos":puntos,"pronosticados":len(pronos)})

    tabla.sort(key=lambda x: (-x["puntos"], x["nombre"]))
    return render_template("tabla.html", tabla=tabla, partidos_jugados=len(res_map))


# ─── ADMIN ────────────────────────────────────────────────────────────────────

@app.route("/admin", methods=["GET","POST"])
def admin():
    if not session.get("es_admin"):
        return redirect(url_for("index"))
    db = get_db()

    if request.method == "POST":
        accion = request.form.get("accion","resultado")
        if accion == "resultado":
            pid = request.form.get("partido_id")
            res = request.form.get("resultado","")
            if pid:
                db.execute("UPDATE partidos SET resultado=? WHERE id=?",
                           (res if res else None, pid))
                db.commit()
                flash("Resultado actualizado.")
        elif accion == "config":
            api_key = request.form.get("api_key","").strip()
            cfg = get_config()
            cfg["api_key"] = api_key
            with open(CONFIG_FILE,"w") as f:
                json.dump(cfg, f)
            flash("API key guardada.")
        return redirect(url_for("admin"))

    grupos = db.execute("SELECT DISTINCT grupo FROM partidos ORDER BY grupo").fetchall()
    partidos_por_grupo = {}
    for g in grupos:
        partidos_por_grupo[g["grupo"]] = db.execute(
            "SELECT * FROM partidos WHERE grupo=? ORDER BY hora_inicio,id", (g["grupo"],)
        ).fetchall()

    cfg = get_config()
    return render_template("admin.html", partidos_por_grupo=partidos_por_grupo, api_key=cfg.get("api_key",""))


# ─── API: SYNC RESULTADOS ─────────────────────────────────────────────────────

@app.route("/api/sync-resultados", methods=["POST"])
def sync_resultados():
    if not session.get("es_admin"):
        return jsonify({"error": "No autorizado"}), 403

    cfg = get_config()
    api_key = cfg.get("api_key","").strip()
    if not api_key:
        return jsonify({"error": "API key no configurada"}), 400

    try:
        import urllib.request
        url = "https://api.football-data.org/v4/competitions/WC/matches?season=2026&stage=GROUP_STAGE"
        req = urllib.request.Request(url, headers={"X-Auth-Token": api_key})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return jsonify({"error": f"Error al consultar API: {str(e)}"}), 500

    db = get_db()
    actualizados = 0
    for m in data.get("matches", []):
        status = m.get("status","")
        score = m.get("score",{})
        if status not in ("FINISHED","IN_PLAY","PAUSED"):
            continue

        home = score.get("fullTime",{}).get("home")
        away = score.get("fullTime",{}).get("away")
        if home is None or away is None:
            continue

        resultado = "1" if home > away else ("2" if away > home else "X")

        # Buscar partido por equipos
        home_name = m.get("homeTeam",{}).get("shortName","")
        away_name = m.get("awayTeam",{}).get("shortName","")

        # Intentar por api_id primero
        api_id = m.get("id")
        partido = db.execute("SELECT id FROM partidos WHERE api_id=?", (api_id,)).fetchone()

        if not partido:
            # Buscar por nombre aproximado
            partido = db.execute(
                "SELECT id FROM partidos WHERE local LIKE ? AND visitante LIKE ?",
                (f"%{home_name[:4]}%", f"%{away_name[:4]}%")
            ).fetchone()

        if partido:
            db.execute("UPDATE partidos SET resultado=?, api_id=? WHERE id=?",
                       (resultado, api_id, partido["id"]))
            actualizados += 1

    db.commit()
    return jsonify({"ok": True, "actualizados": actualizados})


# ─── PWA ──────────────────────────────────────────────────────────────────────

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "Prode Mundial 2026",
        "short_name": "Prode 2026",
        "description": "Pronósticos del Mundial de Fútbol 2026",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a1628",
        "theme_color": "#0d2137",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    })

@app.route("/sw.js")
def service_worker():
    from flask import Response
    sw = """
const CACHE = 'prode-v1';
const URLS = ['/', '/pronosticos', '/tabla', '/static/style.css'];
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(URLS))));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
"""
    return Response(sw, mimetype="application/javascript")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        conn = sqlite3.connect(DATABASE)
        conn.execute("SELECT 1")
        conn.close()
    except Exception:
        if os.path.exists(DATABASE): os.remove(DATABASE)
    init_db()
    print("\n🏆 App del Mundial 2026 lista!")
    print("   Local:   http://localhost:5000")
    print("   Red:     http://[tu-IP]:5000  (para que entren tus amigos)")
    print("   Admin:   usuario='admin' / contraseña='admin123'\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
