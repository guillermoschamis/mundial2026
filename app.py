from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
import sqlite3, os, json
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
app.secret_key = "mundial2026-secreto"
DATABASE = os.path.join(os.path.dirname(__file__), "mundial.db")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f: return json.load(f)
    return {"api_key": ""}

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
        CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE NOT NULL, password TEXT NOT NULL, es_admin INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS partidos (id INTEGER PRIMARY KEY AUTOINCREMENT, grupo TEXT NOT NULL, local TEXT NOT NULL, visitante TEXT NOT NULL, hora_inicio TEXT NOT NULL, resultado TEXT, api_id INTEGER);
        CREATE TABLE IF NOT EXISTS pronosticos (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL, partido_id INTEGER NOT NULL, pronostico TEXT NOT NULL, UNIQUE(usuario_id, partido_id), FOREIGN KEY(usuario_id) REFERENCES usuarios(id), FOREIGN KEY(partido_id) REFERENCES partidos(id));
    """)
    count = db.execute("SELECT COUNT(*) FROM partidos").fetchone()[0]
    if count == 0:
        partidos = [
            # Grupo A
            ("A","México","Sudáfrica",            "2026-06-11T19:00:00+00:00"),
            ("A","Corea del Sur","Rep. Checa",    "2026-06-12T02:00:00+00:00"),
            ("A","Rep. Checa","Sudáfrica",        "2026-06-18T16:00:00+00:00"),
            ("A","México","Corea del Sur",        "2026-06-19T01:00:00+00:00"),
            ("A","Sudáfrica","Corea del Sur",     "2026-06-25T01:00:00+00:00"),
            ("A","Rep. Checa","México",           "2026-06-25T01:00:00+00:00"),
            # Grupo B
            ("B","Canadá","Bosnia y Herz.",       "2026-06-12T19:00:00+00:00"),
            ("B","Qatar","Suiza",                 "2026-06-13T19:00:00+00:00"),
            ("B","Suiza","Bosnia y Herz.",        "2026-06-18T19:00:00+00:00"),
            ("B","Canadá","Qatar",                "2026-06-18T22:00:00+00:00"),
            ("B","Suiza","Canadá",                "2026-06-24T19:00:00+00:00"),
            ("B","Bosnia y Herz.","Qatar",        "2026-06-24T19:00:00+00:00"),
            # Grupo C
            ("C","Brasil","Marruecos",            "2026-06-13T22:00:00+00:00"),
            ("C","Haití","Escocia",               "2026-06-14T01:00:00+00:00"),
            ("C","Escocia","Marruecos",           "2026-06-19T22:00:00+00:00"),
            ("C","Brasil","Haití",                "2026-06-20T00:30:00+00:00"),
            ("C","Marruecos","Haití",             "2026-06-24T22:00:00+00:00"),
            ("C","Escocia","Brasil",              "2026-06-24T22:00:00+00:00"),
            # Grupo D
            ("D","EE.UU.","Paraguay",             "2026-06-13T01:00:00+00:00"),
            ("D","Australia","Turquía",           "2026-06-14T04:00:00+00:00"),
            ("D","EE.UU.","Australia",            "2026-06-19T19:00:00+00:00"),
            ("D","Turquía","Paraguay",            "2026-06-20T04:00:00+00:00"),
            ("D","Turquía","EE.UU.",              "2026-06-26T02:00:00+00:00"),
            ("D","Paraguay","Australia",          "2026-06-26T02:00:00+00:00"),
            # Grupo E
            ("E","Alemania","Curazao",            "2026-06-14T17:00:00+00:00"),
            ("E","Costa de Marfil","Ecuador",     "2026-06-14T23:00:00+00:00"),
            ("E","Alemania","Costa de Marfil",    "2026-06-20T20:00:00+00:00"),
            ("E","Ecuador","Curazao",             "2026-06-21T00:00:00+00:00"),
            ("E","Curazao","Costa de Marfil",     "2026-06-25T20:00:00+00:00"),
            ("E","Ecuador","Alemania",            "2026-06-25T20:00:00+00:00"),
            # Grupo F
            ("F","Países Bajos","Japón",          "2026-06-14T20:00:00+00:00"),
            ("F","Suecia","Túnez",                "2026-06-15T02:00:00+00:00"),
            ("F","Países Bajos","Suecia",         "2026-06-20T17:00:00+00:00"),
            ("F","Túnez","Japón",                 "2026-06-21T04:00:00+00:00"),
            ("F","Túnez","Países Bajos",          "2026-06-25T23:00:00+00:00"),
            ("F","Japón","Suecia",                "2026-06-25T23:00:00+00:00"),
            # Grupo G
            ("G","Bélgica","Egipto",              "2026-06-15T19:00:00+00:00"),
            ("G","Irán","Nueva Zelanda",          "2026-06-16T01:00:00+00:00"),
            ("G","Bélgica","Irán",                "2026-06-21T19:00:00+00:00"),
            ("G","Nueva Zelanda","Egipto",        "2026-06-22T01:00:00+00:00"),
            ("G","Nueva Zelanda","Bélgica",       "2026-06-27T03:00:00+00:00"),
            ("G","Egipto","Irán",                 "2026-06-27T03:00:00+00:00"),
            # Grupo H
            ("H","España","Cabo Verde",           "2026-06-15T16:00:00+00:00"),
            ("H","Arabia Saudita","Uruguay",      "2026-06-15T22:00:00+00:00"),
            ("H","España","Arabia Saudita",       "2026-06-21T16:00:00+00:00"),
            ("H","Uruguay","Cabo Verde",          "2026-06-21T22:00:00+00:00"),
            ("H","Cabo Verde","Arabia Saudita",   "2026-06-27T00:00:00+00:00"),
            ("H","Uruguay","España",              "2026-06-27T00:00:00+00:00"),
            # Grupo I
            ("I","Francia","Senegal",             "2026-06-16T19:00:00+00:00"),
            ("I","Irak","Noruega",                "2026-06-16T22:00:00+00:00"),
            ("I","Francia","Irak",                "2026-06-22T21:00:00+00:00"),
            ("I","Noruega","Senegal",             "2026-06-23T00:00:00+00:00"),
            ("I","Noruega","Francia",             "2026-06-26T19:00:00+00:00"),
            ("I","Senegal","Irak",                "2026-06-26T19:00:00+00:00"),
            # Grupo J
            ("J","Argentina","Argelia",           "2026-06-17T01:00:00+00:00"),
            ("J","Austria","Jordania",            "2026-06-17T04:00:00+00:00"),
            ("J","Argentina","Austria",           "2026-06-22T17:00:00+00:00"),
            ("J","Jordania","Argelia",            "2026-06-23T03:00:00+00:00"),
            ("J","Argelia","Austria",             "2026-06-28T02:00:00+00:00"),
            ("J","Jordania","Argentina",          "2026-06-28T02:00:00+00:00"),
            # Grupo K
            ("K","Portugal","DR Congo",           "2026-06-17T17:00:00+00:00"),
            ("K","Uzbekistán","Colombia",         "2026-06-18T02:00:00+00:00"),
            ("K","Portugal","Uzbekistán",         "2026-06-23T17:00:00+00:00"),
            ("K","Colombia","DR Congo",           "2026-06-24T02:00:00+00:00"),
            ("K","Colombia","Portugal",           "2026-06-27T23:30:00+00:00"),
            ("K","DR Congo","Uzbekistán",         "2026-06-27T23:30:00+00:00"),
            # Grupo L
            ("L","Inglaterra","Croacia",          "2026-06-17T20:00:00+00:00"),
            ("L","Ghana","Panamá",                "2026-06-17T23:00:00+00:00"),
            ("L","Inglaterra","Ghana",            "2026-06-23T20:00:00+00:00"),
            ("L","Panamá","Croacia",              "2026-06-23T23:00:00+00:00"),
            ("L","Panamá","Inglaterra",           "2026-06-27T21:00:00+00:00"),
            ("L","Croacia","Ghana",               "2026-06-27T21:00:00+00:00"),
        ]
        db.executemany("INSERT INTO partidos (grupo,local,visitante,hora_inicio) VALUES (?,?,?,?)", partidos)
    admin = db.execute("SELECT id FROM usuarios WHERE nombre='admin'").fetchone()
    if not admin:
        db.execute("INSERT INTO usuarios (nombre,password,es_admin) VALUES ('admin','admin123',1)")
    db.commit()
    db.close()

def partido_bloqueado(hora_inicio_str):
    try:
        dt = datetime.fromisoformat(hora_inicio_str)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= dt
    except: return False

app.jinja_env.globals["partido_bloqueado"] = partido_bloqueado

BANDERAS = {
    "México":"🇲🇽","Sudáfrica":"🇿🇦","Corea del Sur":"🇰🇷","Rep. Checa":"🇨🇿",
    "Canadá":"🇨🇦","Bosnia y Herz.":"🇧🇦","Qatar":"🇶🇦","Suiza":"🇨🇭",
    "Brasil":"🇧🇷","Marruecos":"🇲🇦","Haití":"🇭🇹","Escocia":"🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "EE.UU.":"🇺🇸","Paraguay":"🇵🇾","Australia":"🇦🇺","Turquía":"🇹🇷",
    "Alemania":"🇩🇪","Curazao":"🇨🇼","Costa de Marfil":"🇨🇮","Ecuador":"🇪🇨",
    "Países Bajos":"🇳🇱","Japón":"🇯🇵","Suecia":"🇸🇪","Túnez":"🇹🇳",
    "Bélgica":"🇧🇪","Egipto":"🇪🇬","Irán":"🇮🇷","Nueva Zelanda":"🇳🇿",
    "España":"🇪🇸","Cabo Verde":"🇨🇻","Arabia Saudita":"🇸🇦","Uruguay":"🇺🇾",
    "Francia":"🇫🇷","Senegal":"🇸🇳","Irak":"🇮🇶","Noruega":"🇳🇴",
    "Argentina":"🇦🇷","Argelia":"🇩🇿","Austria":"🇦🇹","Jordania":"🇯🇴",
    "Portugal":"🇵🇹","DR Congo":"🇨🇩","Uzbekistán":"🇺🇿","Colombia":"🇨🇴",
    "Inglaterra":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Croacia":"🇭🇷","Ghana":"🇬🇭","Panamá":"🇵🇦",
}
app.jinja_env.globals["BANDERAS"] = BANDERAS

@app.template_filter('enumerate')
def enumerate_filter(iterable): return enumerate(iterable)

@app.template_filter('hora_local')
def hora_local(s):
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        dt_arg = dt + timedelta(hours=-3)
        dias = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]
        meses = ["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return f"{dias[dt_arg.weekday()]} {dt_arg.day} {meses[dt_arg.month]} · {dt_arg.strftime('%H:%M')} hs"
    except: return s

@app.route("/")
def index():
    if "usuario_id" not in session: return redirect(url_for("login"))
    return redirect(url_for("pronosticos_view"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        pwd = request.form["password"]
        user = get_db().execute("SELECT * FROM usuarios WHERE nombre=? AND password=?", (nombre,pwd)).fetchone()
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
        try:
            get_db().execute("INSERT INTO usuarios (nombre,password) VALUES (?,?)", (nombre,pwd))
            get_db().commit()
            flash("¡Cuenta creada! Podés iniciar sesión.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Ese nombre de usuario ya existe.")
    return render_template("registro.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/pronosticos", methods=["GET","POST"])
def pronosticos_view():
    if "usuario_id" not in session: return redirect(url_for("login"))
    db = get_db()
    uid = session["usuario_id"]
    if request.method == "POST":
        guardados = 0
        for key, val in request.form.items():
            if key.startswith("partido_"):
                pid = int(key.split("_")[1])
                p = db.execute("SELECT hora_inicio FROM partidos WHERE id=?", (pid,)).fetchone()
                if p and not partido_bloqueado(p["hora_inicio"]) and val in ("1","E","2"):
                    db.execute("INSERT INTO pronosticos (usuario_id,partido_id,pronostico) VALUES (?,?,?) ON CONFLICT(usuario_id,partido_id) DO UPDATE SET pronostico=excluded.pronostico", (uid, pid, val))
                    guardados += 1
        db.commit()
        flash(f"¡{guardados} pronóstico(s) guardado(s)!")
        return redirect(url_for("pronosticos_view"))
    grupos = db.execute("SELECT DISTINCT grupo FROM partidos ORDER BY grupo").fetchall()
    partidos_por_grupo = {}
    mis_pronosticos = {r["partido_id"]: r["pronostico"] for r in db.execute("SELECT partido_id,pronostico FROM pronosticos WHERE usuario_id=?", (uid,))}
    for g in grupos:
        partidos_por_grupo[g["grupo"]] = db.execute("SELECT * FROM partidos WHERE grupo=? ORDER BY hora_inicio,id", (g["grupo"],)).fetchall()
    return render_template("pronosticos.html", partidos_por_grupo=partidos_por_grupo, mis_pronosticos=mis_pronosticos)

@app.route("/tabla")
def tabla():
    if "usuario_id" not in session: return redirect(url_for("login"))
    db = get_db()
    usuarios = db.execute("SELECT id,nombre FROM usuarios WHERE nombre != 'admin' ORDER BY nombre").fetchall()
    res_map = {r["id"]: r["resultado"] for r in db.execute("SELECT id,resultado FROM partidos WHERE resultado IS NOT NULL")}
    tabla = []
    for u in usuarios:
        pronos = db.execute("SELECT partido_id,pronostico FROM pronosticos WHERE usuario_id=?", (u["id"],)).fetchall()
        puntos = sum(1 for p in pronos if res_map.get(p["partido_id"]) == p["pronostico"])
        tabla.append({"nombre":u["nombre"],"puntos":puntos,"pronosticados":len(pronos)})
    tabla.sort(key=lambda x: (-x["puntos"], x["nombre"]))
    return render_template("tabla.html", tabla=tabla, partidos_jugados=len(res_map))

@app.route("/admin", methods=["GET","POST"])
def admin():
    if not session.get("es_admin"): return redirect(url_for("index"))
    db = get_db()
    if request.method == "POST":
        accion = request.form.get("accion","resultado")
        if accion == "resultado":
            pid = request.form.get("partido_id")
            res = request.form.get("resultado","")
            if pid:
                db.execute("UPDATE partidos SET resultado=? WHERE id=?", (res if res else None, pid))
                db.commit()
                flash("Resultado actualizado.")
        elif accion == "config":
            cfg = get_config(); cfg["api_key"] = request.form.get("api_key","").strip()
            with open(CONFIG_FILE,"w") as f: json.dump(cfg, f)
            flash("API key guardada.")
        return redirect(url_for("admin"))
    grupos = db.execute("SELECT DISTINCT grupo FROM partidos ORDER BY grupo").fetchall()
    partidos_por_grupo = {}
    for g in grupos:
        partidos_por_grupo[g["grupo"]] = db.execute("SELECT * FROM partidos WHERE grupo=? ORDER BY hora_inicio,id", (g["grupo"],)).fetchall()
    return render_template("admin.html", partidos_por_grupo=partidos_por_grupo, api_key=get_config().get("api_key",""))

@app.route("/api/sync-resultados", methods=["POST"])
def sync_resultados():
    if not session.get("es_admin"): return jsonify({"error":"No autorizado"}), 403
    api_key = get_config().get("api_key","").strip()
    if not api_key: return jsonify({"error":"API key no configurada"}), 400
    try:
        import urllib.request
        req = urllib.request.Request("https://api.football-data.org/v4/competitions/WC/matches?season=2026&stage=GROUP_STAGE", headers={"X-Auth-Token": api_key})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    db = get_db(); actualizados = 0
    for m in data.get("matches",[]):
        if m.get("status") not in ("FINISHED","IN_PLAY","PAUSED"): continue
        home = m.get("score",{}).get("fullTime",{}).get("home")
        away = m.get("score",{}).get("fullTime",{}).get("away")
        if home is None or away is None: continue
        resultado = "1" if home > away else ("2" if away > home else "E")
        api_id = m.get("id")
        p = db.execute("SELECT id FROM partidos WHERE api_id=?", (api_id,)).fetchone()
        if not p:
            hn = m.get("homeTeam",{}).get("shortName","")
            an = m.get("awayTeam",{}).get("shortName","")
            p = db.execute("SELECT id FROM partidos WHERE local LIKE ? AND visitante LIKE ?", (f"%{hn[:4]}%", f"%{an[:4]}%")).fetchone()
        if p:
            db.execute("UPDATE partidos SET resultado=?, api_id=? WHERE id=?", (resultado, api_id, p["id"]))
            actualizados += 1
    db.commit()
    return jsonify({"ok":True,"actualizados":actualizados})

@app.route("/manifest.json")
def manifest():
    return jsonify({"name":"Prode Mundial 2026","short_name":"Prode 2026","start_url":"/","display":"standalone","background_color":"#0a1628","theme_color":"#0d2137","icons":[{"src":"/static/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"/static/icon-512.png","sizes":"512x512","type":"image/png"}]})

@app.route("/sw.js")
def service_worker():
    from flask import Response
    return Response("const CACHE='prode-v1';const URLS=['/','/pronosticos','/tabla'];self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(URLS))));self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});", mimetype="application/javascript")


@app.route("/api/sync-horarios", methods=["POST"])
def sync_horarios():
    if not session.get("es_admin"): return jsonify({"error":"No autorizado"}), 403
    api_key = get_config().get("api_key","").strip()
    if not api_key: return jsonify({"error":"API key no configurada"}), 400
    try:
        import urllib.request
        req = urllib.request.Request("https://api.football-data.org/v4/competitions/WC/matches?season=2026&stage=GROUP_STAGE", headers={"X-Auth-Token": api_key})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    db = get_db(); actualizados = 0
    for m in data.get("matches",[]):
        utc_date = m.get("utcDate")
        if not utc_date: continue
        api_id = m.get("id")
        hn = m.get("homeTeam",{}).get("shortName","")
        an = m.get("awayTeam",{}).get("shortName","")
        p = db.execute("SELECT id FROM partidos WHERE api_id=?", (api_id,)).fetchone()
        if not p:
            p = db.execute("SELECT id FROM partidos WHERE local LIKE ? AND visitante LIKE ?", (f"%{hn[:4]}%", f"%{an[:4]}%")).fetchone()
        if p:
            db.execute("UPDATE partidos SET hora_inicio=?, api_id=? WHERE id=?", (utc_date, api_id, p["id"]))
            actualizados += 1
    db.commit()
    return jsonify({"ok":True,"actualizados":actualizados})


def calcular_posiciones_grupo(grupo, db):
    """Devuelve equipos del grupo ordenados por puntos, dif goles, goles favor."""
    partidos = db.execute(
        "SELECT * FROM partidos WHERE grupo=? AND resultado IS NOT NULL", (grupo,)
    ).fetchall()
    equipos = {}
    for p in partidos:
        for eq, rival, es_local in [(p["local"], p["visitante"], True), (p["visitante"], p["local"], False)]:
            if eq not in equipos:
                equipos[eq] = {"pts":0,"gj":0,"gf":0,"gc":0}
            equipos[eq]["gj"] += 1
            if (p["resultado"] == "1" and es_local) or (p["resultado"] == "2" and not es_local):
                equipos[eq]["pts"] += 3
            elif p["resultado"] == "E":
                equipos[eq]["pts"] += 1
    tabla = sorted(equipos.items(), key=lambda x: (-x[1]["pts"], x[0]))
    return tabla  # [(nombre, stats), ...]

def grupo_completo(grupo, db):
    """Verifica si todos los partidos del grupo tienen resultado."""
    total = db.execute("SELECT COUNT(*) FROM partidos WHERE grupo=?", (grupo,)).fetchone()[0]
    con_resultado = db.execute("SELECT COUNT(*) FROM partidos WHERE grupo=? AND resultado IS NOT NULL", (grupo,)).fetchone()[0]
    return total > 0 and total == con_resultado

@app.route("/api/generar-16avos", methods=["POST"])
def generar_16avos():
    if not session.get("es_admin"): return jsonify({"error":"No autorizado"}), 403
    db = get_db()

    # Verificar que todos los grupos estén completos
    grupos = [g["grupo"] for g in db.execute("SELECT DISTINCT grupo FROM partidos WHERE grupo NOT IN ('R32','R16','QF','SF','F') ORDER BY grupo").fetchall()]
    incompletos = [g for g in grupos if not grupo_completo(g, db)]
    if incompletos:
        return jsonify({"error": f"Grupos sin completar: {', '.join(incompletos)}"}), 400

    # Calcular 1° y 2° de cada grupo
    primeros = {}
    segundos = {}
    terceros = {}
    for g in grupos:
        tabla = calcular_posiciones_grupo(g, db)
        if len(tabla) >= 1: primeros[g] = tabla[0][0]
        if len(tabla) >= 2: segundos[g] = tabla[1][0]
        if len(tabla) >= 3: terceros[g] = (tabla[2][0], tabla[2][1])  # (nombre, stats)

    # Elegir los 8 mejores terceros
    todos_terceros = sorted(
        [(g, n, s) for g, (n, s) in terceros.items()],
        key=lambda x: (-x[2]["pts"], x[0])
    )
    mejores_terceros = [t[1] for t in todos_terceros[:8]]

    def t3(i):
        return mejores_terceros[i] if i < len(mejores_terceros) else "Mejor 3°"

    # Cruces oficiales R32 (basado en fixture FIFA 2026)
    cruces = [
        ("R32", segundos.get("A","2°A"), segundos.get("B","2°B"),    "2026-06-28T16:00:00+00:00"),
        ("R32", primeros.get("E","1°E"), t3(0),                       "2026-06-29T19:30:00+00:00"),
        ("R32", primeros.get("F","1°F"), segundos.get("C","2°C"),     "2026-06-29T23:00:00+00:00"),
        ("R32", primeros.get("C","1°C"), segundos.get("F","2°F"),     "2026-06-29T16:00:00+00:00"),
        ("R32", primeros.get("I","1°I"), t3(1),                       "2026-06-30T21:00:00+00:00"),
        ("R32", segundos.get("E","2°E"), segundos.get("I","2°I"),     "2026-06-30T16:00:00+00:00"),
        ("R32", primeros.get("A","1°A"), t3(2),                       "2026-06-30T23:00:00+00:00"),
        ("R32", primeros.get("L","1°L"), t3(3),                       "2026-07-01T16:00:00+00:00"),
        ("R32", primeros.get("D","1°D"), t3(4),                       "2026-07-01T21:00:00+00:00"),
        ("R32", primeros.get("G","1°G"), t3(5),                       "2026-07-01T17:00:00+00:00"),
        ("R32", segundos.get("K","2°K"), segundos.get("L","2°L"),     "2026-07-02T23:00:00+00:00"),
        ("R32", primeros.get("H","1°H"), segundos.get("J","2°J"),     "2026-07-02T16:00:00+00:00"),
        ("R32", primeros.get("B","1°B"), t3(6),                       "2026-07-02T20:00:00+00:00"),
        ("R32", primeros.get("J","1°J"), segundos.get("H","2°H"),     "2026-07-03T22:00:00+00:00"),
        ("R32", primeros.get("K","1°K"), t3(7),                       "2026-07-03T20:30:00+00:00"),
        ("R32", segundos.get("D","2°D"), segundos.get("G","2°G"),     "2026-07-03T17:00:00+00:00"),
    ]

    # Borrar R32 existentes y recrear
    db.execute("DELETE FROM partidos WHERE grupo='R32'")
    db.executemany("INSERT INTO partidos (grupo,local,visitante,hora_inicio) VALUES (?,?,?,?)", cruces)
    db.commit()
    return jsonify({"ok": True, "partidos": len(cruces)})


def auto_sync_horarios():
    """Sincroniza horarios desde la API al arrancar, si hay API key disponible."""
    api_key = os.environ.get("FOOTBALL_API_KEY") or get_config().get("api_key","")
    if not api_key:
        return
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.football-data.org/v4/competitions/WC/matches?season=2026&stage=GROUP_STAGE",
            headers={"X-Auth-Token": api_key.strip()}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        actualizados = 0
        for m in data.get("matches", []):
            utc_date = m.get("utcDate")
            if not utc_date:
                continue
            api_id = m.get("id")
            hn = m.get("homeTeam", {}).get("shortName", "")
            an = m.get("awayTeam", {}).get("shortName", "")
            p = db.execute("SELECT id FROM partidos WHERE api_id=?", (api_id,)).fetchone()
            if not p:
                p = db.execute(
                    "SELECT id FROM partidos WHERE local LIKE ? AND visitante LIKE ?",
                    (f"%{hn[:4]}%", f"%{an[:4]}%")
                ).fetchone()
            if p:
                db.execute("UPDATE partidos SET hora_inicio=?, api_id=? WHERE id=?",
                           (utc_date, api_id, p["id"]))
                actualizados += 1
            # también actualizar resultado si está disponible
            status = m.get("status","")
            if status == "FINISHED":
                home = m.get("score",{}).get("fullTime",{}).get("home")
                away = m.get("score",{}).get("fullTime",{}).get("away")
                if home is not None and away is not None and p:
                    resultado = "1" if home > away else ("2" if away > home else "E")
                    db.execute("UPDATE partidos SET resultado=? WHERE id=?", (resultado, p["id"]))
        db.commit()
        db.close()
        print(f"Auto-sync: {actualizados} partidos actualizados desde la API.")
    except Exception as e:
        print(f"Auto-sync: no se pudo conectar con la API ({e})")

try:
    conn = sqlite3.connect(DATABASE); conn.execute("SELECT 1"); conn.close()
except:
    if os.path.exists(DATABASE): os.remove(DATABASE)
init_db()
auto_sync_horarios()

if __name__ == "__main__":
    print("\n🏆 App del Mundial 2026 lista!\n   http://localhost:5000\n   Admin: usuario='admin' / contraseña='admin123'\n")
    app.run(debug=True, host="0.0.0.0", port=5000)

# ─── SYNC HORARIOS ────────────────────────────────────────────────────────────
