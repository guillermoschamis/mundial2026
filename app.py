from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
import os, json
from datetime import datetime, timezone, timedelta

from datetime import timedelta
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mundial2026-secreto")
app.permanent_session_lifetime = timedelta(days=30)

# ─── DB ADAPTER (PostgreSQL en Render, SQLite local) ──────────────────────────

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

USE_PG = bool(DATABASE_URL)
PH = "%s" if USE_PG else "?"  # placeholder

if USE_PG:
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), "mundial.db")

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def get_db():
    if "db" not in g:
        if USE_PG:
            g.db = psycopg2.connect(DATABASE_URL)
        else:
            g.db = sqlite3.connect(SQLITE_PATH)
            g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db:
        try: db.close()
        except: pass

def query(sql, params=(), fetchone=False, fetchall=False, commit=False):
    db = get_db()
    if USE_PG:
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cur = db.cursor()
    cur.execute(sql, params)
    result = None
    if fetchone: result = cur.fetchone()
    elif fetchall: result = cur.fetchall()
    if commit: db.commit()
    return result

def executemany(sql, params_list):
    db = get_db()
    if USE_PG:
        cur = db.cursor()
    else:
        cur = db.cursor()
    cur.executemany(sql, params_list)
    db.commit()

def get_config():
    api_key = os.environ.get("FOOTBALL_API_KEY", "")
    if api_key: return {"api_key": api_key}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f: return json.load(f)
    return {"api_key": ""}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f: json.dump(cfg, f)

# ─── INIT DB ──────────────────────────────────────────────────────────────────

def init_db():
    if USE_PG:
        serial = "SERIAL"
        text_pk = "TEXT"
    else:
        serial = "INTEGER"
        text_pk = "TEXT"

    stmts = [
        f"""CREATE TABLE IF NOT EXISTS usuarios (
            id {serial} PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            es_admin INTEGER DEFAULT 0
        )""",
        f"""CREATE TABLE IF NOT EXISTS partidos (
            id {serial} PRIMARY KEY,
            grupo TEXT NOT NULL,
            local TEXT NOT NULL,
            visitante TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            resultado TEXT,
            api_id INTEGER
        )""",
        f"""CREATE TABLE IF NOT EXISTS pronosticos (
            id {serial} PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            partido_id INTEGER NOT NULL,
            pronostico TEXT NOT NULL,
            UNIQUE(usuario_id, partido_id)
        )""",
    ]
    for stmt in stmts:
        query(stmt, commit=True)

    count = query("SELECT COUNT(*) as c FROM partidos", fetchone=True)
    cnt = count["c"] if USE_PG else count[0]
    if cnt == 0:
        partidos = [
            ("A","México","Sudáfrica","2026-06-11T19:00:00+00:00"),
            ("A","Corea del Sur","Rep. Checa","2026-06-12T02:00:00+00:00"),
            ("A","Rep. Checa","Sudáfrica","2026-06-18T16:00:00+00:00"),
            ("A","México","Corea del Sur","2026-06-19T01:00:00+00:00"),
            ("A","Sudáfrica","Corea del Sur","2026-06-25T01:00:00+00:00"),
            ("A","Rep. Checa","México","2026-06-25T01:00:00+00:00"),
            ("B","Canadá","Bosnia y Herz.","2026-06-12T19:00:00+00:00"),
            ("B","Qatar","Suiza","2026-06-13T19:00:00+00:00"),
            ("B","Suiza","Bosnia y Herz.","2026-06-18T19:00:00+00:00"),
            ("B","Canadá","Qatar","2026-06-18T22:00:00+00:00"),
            ("B","Suiza","Canadá","2026-06-24T19:00:00+00:00"),
            ("B","Bosnia y Herz.","Qatar","2026-06-24T19:00:00+00:00"),
            ("C","Brasil","Marruecos","2026-06-13T22:00:00+00:00"),
            ("C","Haití","Escocia","2026-06-14T01:00:00+00:00"),
            ("C","Escocia","Marruecos","2026-06-19T22:00:00+00:00"),
            ("C","Brasil","Haití","2026-06-20T00:30:00+00:00"),
            ("C","Marruecos","Haití","2026-06-24T22:00:00+00:00"),
            ("C","Escocia","Brasil","2026-06-24T22:00:00+00:00"),
            ("D","EE.UU.","Paraguay","2026-06-13T01:00:00+00:00"),
            ("D","Australia","Turquía","2026-06-14T04:00:00+00:00"),
            ("D","EE.UU.","Australia","2026-06-19T19:00:00+00:00"),
            ("D","Turquía","Paraguay","2026-06-20T04:00:00+00:00"),
            ("D","Turquía","EE.UU.","2026-06-26T02:00:00+00:00"),
            ("D","Paraguay","Australia","2026-06-26T02:00:00+00:00"),
            ("E","Alemania","Curazao","2026-06-14T17:00:00+00:00"),
            ("E","Costa de Marfil","Ecuador","2026-06-14T23:00:00+00:00"),
            ("E","Alemania","Costa de Marfil","2026-06-20T20:00:00+00:00"),
            ("E","Ecuador","Curazao","2026-06-21T00:00:00+00:00"),
            ("E","Curazao","Costa de Marfil","2026-06-25T20:00:00+00:00"),
            ("E","Ecuador","Alemania","2026-06-25T20:00:00+00:00"),
            ("F","Países Bajos","Japón","2026-06-14T20:00:00+00:00"),
            ("F","Suecia","Túnez","2026-06-15T02:00:00+00:00"),
            ("F","Países Bajos","Suecia","2026-06-20T17:00:00+00:00"),
            ("F","Túnez","Japón","2026-06-21T04:00:00+00:00"),
            ("F","Túnez","Países Bajos","2026-06-25T23:00:00+00:00"),
            ("F","Japón","Suecia","2026-06-25T23:00:00+00:00"),
            ("G","Bélgica","Egipto","2026-06-15T19:00:00+00:00"),
            ("G","Irán","Nueva Zelanda","2026-06-16T01:00:00+00:00"),
            ("G","Bélgica","Irán","2026-06-21T19:00:00+00:00"),
            ("G","Nueva Zelanda","Egipto","2026-06-22T01:00:00+00:00"),
            ("G","Nueva Zelanda","Bélgica","2026-06-27T03:00:00+00:00"),
            ("G","Egipto","Irán","2026-06-27T03:00:00+00:00"),
            ("H","España","Cabo Verde","2026-06-15T16:00:00+00:00"),
            ("H","Arabia Saudita","Uruguay","2026-06-15T22:00:00+00:00"),
            ("H","España","Arabia Saudita","2026-06-21T16:00:00+00:00"),
            ("H","Uruguay","Cabo Verde","2026-06-21T22:00:00+00:00"),
            ("H","Cabo Verde","Arabia Saudita","2026-06-27T00:00:00+00:00"),
            ("H","Uruguay","España","2026-06-27T00:00:00+00:00"),
            ("I","Francia","Senegal","2026-06-16T19:00:00+00:00"),
            ("I","Irak","Noruega","2026-06-16T22:00:00+00:00"),
            ("I","Francia","Irak","2026-06-22T21:00:00+00:00"),
            ("I","Noruega","Senegal","2026-06-23T00:00:00+00:00"),
            ("I","Noruega","Francia","2026-06-26T19:00:00+00:00"),
            ("I","Senegal","Irak","2026-06-26T19:00:00+00:00"),
            ("J","Argentina","Argelia","2026-06-17T01:00:00+00:00"),
            ("J","Austria","Jordania","2026-06-17T04:00:00+00:00"),
            ("J","Argentina","Austria","2026-06-22T17:00:00+00:00"),
            ("J","Jordania","Argelia","2026-06-23T03:00:00+00:00"),
            ("J","Argelia","Austria","2026-06-28T02:00:00+00:00"),
            ("J","Jordania","Argentina","2026-06-28T02:00:00+00:00"),
            ("K","Portugal","DR Congo","2026-06-17T17:00:00+00:00"),
            ("K","Uzbekistán","Colombia","2026-06-18T02:00:00+00:00"),
            ("K","Portugal","Uzbekistán","2026-06-23T17:00:00+00:00"),
            ("K","Colombia","DR Congo","2026-06-24T02:00:00+00:00"),
            ("K","Colombia","Portugal","2026-06-27T23:30:00+00:00"),
            ("K","DR Congo","Uzbekistán","2026-06-27T23:30:00+00:00"),
            ("L","Inglaterra","Croacia","2026-06-17T20:00:00+00:00"),
            ("L","Ghana","Panamá","2026-06-17T23:00:00+00:00"),
            ("L","Inglaterra","Ghana","2026-06-23T20:00:00+00:00"),
            ("L","Panamá","Croacia","2026-06-23T23:00:00+00:00"),
            ("L","Panamá","Inglaterra","2026-06-27T21:00:00+00:00"),
            ("L","Croacia","Ghana","2026-06-27T21:00:00+00:00"),
        ]
        ph = PH
        executemany(f"INSERT INTO partidos (grupo,local,visitante,hora_inicio) VALUES ({ph},{ph},{ph},{ph})", partidos)

    admin = query(f"SELECT id FROM usuarios WHERE nombre={PH}", ("admin",), fetchone=True)
    if not admin:
        query(f"INSERT INTO usuarios (nombre,password,es_admin) VALUES ({PH},{PH},1)", ("admin","admin123"), commit=True)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def partido_bloqueado(hora_inicio_str):
    try:
        dt = datetime.fromisoformat(str(hora_inicio_str))
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
        dt = datetime.fromisoformat(str(s))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        dt_arg = dt + timedelta(hours=-3)
        dias = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]
        meses = ["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        return f"{dias[dt_arg.weekday()]} {dt_arg.day} {meses[dt_arg.month]} · {dt_arg.strftime('%H:%M')} hs"
    except: return str(s)

# ─── AUTH ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "usuario_id" not in session: return redirect(url_for("login"))
    return redirect(url_for("pronosticos_view"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        pwd = request.form["password"]
        user = query(f"SELECT * FROM usuarios WHERE nombre={PH} AND password={PH}", (nombre,pwd), fetchone=True)
        if user:
            session.permanent = True
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
            query(f"INSERT INTO usuarios (nombre,password) VALUES ({PH},{PH})", (nombre,pwd), commit=True)
            flash("¡Cuenta creada! Podés iniciar sesión.")
            return redirect(url_for("login"))
        except Exception:
            flash("Ese nombre de usuario ya existe.")
    return render_template("registro.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── PRONÓSTICOS ──────────────────────────────────────────────────────────────

@app.route("/pronosticos", methods=["GET","POST"])
def pronosticos_view():
    if "usuario_id" not in session: return redirect(url_for("login"))
    uid = session["usuario_id"]

    if request.method == "POST":
        guardados = 0
        for key, val in request.form.items():
            if key.startswith("partido_"):
                pid = int(key.split("_")[1])
                p = query(f"SELECT hora_inicio FROM partidos WHERE id={PH}", (pid,), fetchone=True)
                if p and not partido_bloqueado(p["hora_inicio"]) and val in ("1","E","2"):
                    try:
                        if USE_PG:
                            query(f"INSERT INTO pronosticos (usuario_id,partido_id,pronostico) VALUES ({PH},{PH},{PH}) ON CONFLICT(usuario_id,partido_id) DO UPDATE SET pronostico=EXCLUDED.pronostico", (uid,pid,val), commit=True)
                        else:
                            query(f"INSERT INTO pronosticos (usuario_id,partido_id,pronostico) VALUES ({PH},{PH},{PH}) ON CONFLICT(usuario_id,partido_id) DO UPDATE SET pronostico=excluded.pronostico", (uid,pid,val), commit=True)
                        guardados += 1
                    except: pass
        flash(f"¡{guardados} pronóstico(s) guardado(s)!")
        return redirect(url_for("pronosticos_view"))

    modo = request.args.get("modo", "grupo")
    fases = query("SELECT DISTINCT grupo FROM partidos ORDER BY grupo", fetchall=True)
    fases = [f["grupo"] if USE_PG else f[0] for f in fases]

    partidos_por_grupo = {}
    for g in fases:
        partidos_por_grupo[g] = query(f"SELECT * FROM partidos WHERE grupo={PH} ORDER BY hora_inicio,id", (g,), fetchall=True)

    # Cronológico: todos los partidos ordenados por hora
    partidos_cronologicos = query("SELECT * FROM partidos ORDER BY hora_inicio,id", fetchall=True)

    pronos = query(f"SELECT partido_id,pronostico FROM pronosticos WHERE usuario_id={PH}", (uid,), fetchall=True)
    mis_pronosticos = {r["partido_id"]: r["pronostico"] for r in pronos}

    return render_template("pronosticos.html",
        partidos_por_grupo=partidos_por_grupo,
        partidos_cronologicos=partidos_cronologicos,
        mis_pronosticos=mis_pronosticos,
        modo=modo)

@app.route("/partido/<int:partido_id>/pronosticos")
def ver_pronosticos_partido(partido_id):
    if "usuario_id" not in session: return jsonify({"error":"No autorizado"}), 401
    p = query(f"SELECT * FROM partidos WHERE id={PH}", (partido_id,), fetchone=True)
    if not p: return jsonify({"error":"Partido no encontrado"}), 404
    if not partido_bloqueado(p["hora_inicio"]):
        return jsonify({"error":"Los pronosticos se ven una vez que el partido arranca."})
    rows = query(f"""SELECT u.nombre as nombre, pr.pronostico as pronostico
                      FROM pronosticos pr JOIN usuarios u ON u.id=pr.usuario_id
                      WHERE pr.partido_id={PH} ORDER BY u.nombre""", (partido_id,), fetchall=True)
    return jsonify([{"nombre":r["nombre"],"pronostico":r["pronostico"]} for r in rows])

# ─── TABLA ────────────────────────────────────────────────────────────────────

@app.route("/tabla")
def tabla():
    if "usuario_id" not in session: return redirect(url_for("login"))
    usuarios = query(f"SELECT id,nombre FROM usuarios WHERE nombre != {PH} ORDER BY nombre", ("admin",), fetchall=True)
    res_rows = query("SELECT id,resultado FROM partidos WHERE resultado IS NOT NULL", fetchall=True)
    res_map = {r["id"]: r["resultado"] for r in res_rows}
    tabla = []
    for u in usuarios:
        pronos = query(f"SELECT partido_id,pronostico FROM pronosticos WHERE usuario_id={PH}", (u["id"],), fetchall=True)
        puntos = sum(1 for p in pronos if res_map.get(p["partido_id"]) == p["pronostico"])
        tabla.append({"nombre":u["nombre"],"puntos":puntos,"pronosticados":len(pronos)})
    tabla.sort(key=lambda x: (-x["puntos"], x["nombre"]))
    partidos_jugados = len(res_map)
    return render_template("tabla.html", tabla=tabla, partidos_jugados=partidos_jugados)

# ─── ADMIN ────────────────────────────────────────────────────────────────────

@app.route("/admin", methods=["GET","POST"])
def admin():
    if not session.get("es_admin"): return redirect(url_for("index"))
    if request.method == "POST":
        accion = request.form.get("accion","resultado")
        if accion == "resultado":
            pid = request.form.get("partido_id")
            res = request.form.get("resultado","")
            if pid:
                query(f"UPDATE partidos SET resultado={PH} WHERE id={PH}", (res if res else None, pid), commit=True)
                flash("Resultado actualizado.")
        elif accion == "config":
            cfg = get_config(); cfg["api_key"] = request.form.get("api_key","").strip()
            save_config(cfg); flash("API key guardada.")
        return redirect(url_for("admin"))

    fases = query("SELECT DISTINCT grupo FROM partidos ORDER BY grupo", fetchall=True)
    fases = [f["grupo"] if USE_PG else f[0] for f in fases]
    partidos_por_grupo = {}
    for g in fases:
        partidos_por_grupo[g] = query(f"SELECT * FROM partidos WHERE grupo={PH} ORDER BY hora_inicio,id", (g,), fetchall=True)
    usuarios_raw = query(f"SELECT id,nombre FROM usuarios WHERE nombre!={PH} ORDER BY nombre", ("admin",), fetchall=True)
    usuarios = []
    for u in usuarios_raw:
        cnt = query(f"SELECT COUNT(*) as c FROM pronosticos WHERE usuario_id={PH}", (u["id"],), fetchone=True)
        usuarios.append({"id":u["id"],"nombre":u["nombre"],"total_pronos": cnt["c"] if USE_PG else cnt[0]})
    return render_template("admin.html", partidos_por_grupo=partidos_por_grupo, api_key=get_config().get("api_key",""), usuarios=usuarios)

# ─── API: SYNC RESULTADOS ─────────────────────────────────────────────────────

ESTADOS_CON_RESULTADO = {"1H","HT","2H","ET","BT","P","FT","AET","PEN","SUSP","INT"}

def _sync_resultados():
    api_key = get_config().get("api_key","").strip()
    if not api_key: return {"error":"API key no configurada"}
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://v3.football.api-sports.io/fixtures?league=1&season=2026",
            headers={"x-apisports-key": api_key})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}
    actualizados = 0
    for m in data.get("response", []):
        fixture = m.get("fixture", {})
        estado = fixture.get("status", {}).get("short")
        if estado not in ESTADOS_CON_RESULTADO: continue
        goles = m.get("goals", {})
        home, away = goles.get("home"), goles.get("away")
        if home is None or away is None: continue
        resultado = "1" if home > away else ("2" if away > home else "E")
        api_id = fixture.get("id")
        hn = m.get("teams", {}).get("home", {}).get("name", "")
        an = m.get("teams", {}).get("away", {}).get("name", "")
        p = query(f"SELECT id FROM partidos WHERE api_id={PH}", (api_id,), fetchone=True)
        if not p:
            p = query(f"SELECT id FROM partidos WHERE local LIKE {PH} AND visitante LIKE {PH}", (f"%{hn[:4]}%", f"%{an[:4]}%"), fetchone=True)
        if p:
            query(f"UPDATE partidos SET resultado={PH}, api_id={PH} WHERE id={PH}", (resultado, api_id, p["id"]), commit=True)
            actualizados += 1
    return {"ok":True,"actualizados":actualizados}

@app.route("/api/sync-resultados", methods=["POST"])
def sync_resultados():
    if not session.get("es_admin"): return jsonify({"error":"No autorizado"}), 403
    resultado = _sync_resultados()
    if "error" in resultado: return jsonify(resultado), 400
    return jsonify(resultado)

@app.route("/api/sync-horarios", methods=["POST"])
def sync_horarios():
    if not session.get("es_admin"): return jsonify({"error":"No autorizado"}), 403
    api_key = get_config().get("api_key","").strip()
    if not api_key: return jsonify({"error":"API key no configurada"}), 400
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://v3.football.api-sports.io/fixtures?league=1&season=2026",
            headers={"x-apisports-key": api_key})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    actualizados = 0
    for m in data.get("response", []):
        fixture = m.get("fixture", {})
        utc_date = fixture.get("date")
        if not utc_date: continue
        api_id = fixture.get("id")
        hn = m.get("teams", {}).get("home", {}).get("name", "")
        an = m.get("teams", {}).get("away", {}).get("name", "")
        p = query(f"SELECT id FROM partidos WHERE api_id={PH}", (api_id,), fetchone=True)
        if not p:
            p = query(f"SELECT id FROM partidos WHERE local LIKE {PH} AND visitante LIKE {PH}", (f"%{hn[:4]}%", f"%{an[:4]}%"), fetchone=True)
        if p:
            query(f"UPDATE partidos SET hora_inicio={PH}, api_id={PH} WHERE id={PH}", (utc_date, api_id, p["id"]), commit=True)
            actualizados += 1
    return jsonify({"ok":True,"actualizados":actualizados})

# ─── 16AVOS ───────────────────────────────────────────────────────────────────

def calcular_posiciones_grupo(grupo):
    partidos = query(f"SELECT * FROM partidos WHERE grupo={PH} AND resultado IS NOT NULL", (grupo,), fetchall=True)
    equipos = {}
    for p in partidos:
        for eq, es_local in [(p["local"], True), (p["visitante"], False)]:
            if eq not in equipos: equipos[eq] = {"pts":0,"gj":0}
            equipos[eq]["gj"] += 1
            if (p["resultado"]=="1" and es_local) or (p["resultado"]=="2" and not es_local):
                equipos[eq]["pts"] += 3
            elif p["resultado"]=="E":
                equipos[eq]["pts"] += 1
    return sorted(equipos.items(), key=lambda x: (-x[1]["pts"], x[0]))

def grupo_completo(grupo):
    total = query(f"SELECT COUNT(*) as c FROM partidos WHERE grupo={PH}", (grupo,), fetchone=True)
    con_res = query(f"SELECT COUNT(*) as c FROM partidos WHERE grupo={PH} AND resultado IS NOT NULL", (grupo,), fetchone=True)
    t = total["c"] if USE_PG else total[0]
    r = con_res["c"] if USE_PG else con_res[0]
    return t > 0 and t == r

@app.route("/api/generar-16avos", methods=["POST"])
def generar_16avos():
    if not session.get("es_admin"): return jsonify({"error":"No autorizado"}), 403
    grupos = ["A","B","C","D","E","F","G","H","I","J","K","L"]
    incompletos = [g for g in grupos if not grupo_completo(g)]
    if incompletos:
        return jsonify({"error": f"Grupos sin completar: {', '.join(incompletos)}"}), 400
    primeros, segundos, terceros = {}, {}, {}
    for g in grupos:
        tabla = calcular_posiciones_grupo(g)
        if len(tabla) >= 1: primeros[g] = tabla[0][0]
        if len(tabla) >= 2: segundos[g] = tabla[1][0]
        if len(tabla) >= 3: terceros[g] = (tabla[2][0], tabla[2][1])
    todos_terceros = sorted([(g,n,s) for g,(n,s) in terceros.items()], key=lambda x: (-x[2]["pts"], x[0]))
    mt = [t[1] for t in todos_terceros[:8]]
    def t3(i): return mt[i] if i < len(mt) else "Mejor 3°"
    cruces = [
        ("R32",segundos.get("A","2°A"),segundos.get("B","2°B"),"2026-06-28T16:00:00+00:00"),
        ("R32",primeros.get("E","1°E"),t3(0),"2026-06-29T19:30:00+00:00"),
        ("R32",primeros.get("F","1°F"),segundos.get("C","2°C"),"2026-06-29T23:00:00+00:00"),
        ("R32",primeros.get("C","1°C"),segundos.get("F","2°F"),"2026-06-29T16:00:00+00:00"),
        ("R32",primeros.get("I","1°I"),t3(1),"2026-06-30T21:00:00+00:00"),
        ("R32",segundos.get("E","2°E"),segundos.get("I","2°I"),"2026-06-30T16:00:00+00:00"),
        ("R32",primeros.get("A","1°A"),t3(2),"2026-06-30T23:00:00+00:00"),
        ("R32",primeros.get("L","1°L"),t3(3),"2026-07-01T16:00:00+00:00"),
        ("R32",primeros.get("D","1°D"),t3(4),"2026-07-01T21:00:00+00:00"),
        ("R32",primeros.get("G","1°G"),t3(5),"2026-07-01T17:00:00+00:00"),
        ("R32",segundos.get("K","2°K"),segundos.get("L","2°L"),"2026-07-02T23:00:00+00:00"),
        ("R32",primeros.get("H","1°H"),segundos.get("J","2°J"),"2026-07-02T16:00:00+00:00"),
        ("R32",primeros.get("B","1°B"),t3(6),"2026-07-02T20:00:00+00:00"),
        ("R32",primeros.get("J","1°J"),segundos.get("H","2°H"),"2026-07-03T22:00:00+00:00"),
        ("R32",primeros.get("K","1°K"),t3(7),"2026-07-03T20:30:00+00:00"),
        ("R32",segundos.get("D","2°D"),segundos.get("G","2°G"),"2026-07-03T17:00:00+00:00"),
    ]
    query(f"DELETE FROM partidos WHERE grupo={PH}", ("R32",), commit=True)
    ph = PH
    executemany(f"INSERT INTO partidos (grupo,local,visitante,hora_inicio) VALUES ({ph},{ph},{ph},{ph})", cruces)
    return jsonify({"ok":True,"partidos":len(cruces)})

# ─── PWA ──────────────────────────────────────────────────────────────────────

@app.route("/admin/eliminar-usuario", methods=["POST"])
def eliminar_usuario():
    if not session.get("es_admin"): return redirect(url_for("index"))
    uid = request.form.get("usuario_id")
    if uid:
        query(f"DELETE FROM pronosticos WHERE usuario_id={PH}", (uid,), commit=True)
        query(f"DELETE FROM usuarios WHERE id={PH} AND es_admin=0", (uid,), commit=True)
        flash("Usuario eliminado.")
    return redirect(url_for("admin"))


@app.route("/grupos")
def grupos_view():
    if "usuario_id" not in session: return redirect(url_for("login"))
    grupos = ["A","B","C","D","E","F","G","H","I","J","K","L"]
    datos = {}
    for g in grupos:
        partidos = query(f"SELECT * FROM partidos WHERE grupo={PH}", (g,), fetchall=True)
        equipos = {}
        for p in partidos:
            for eq, es_local in [(p["local"], True), (p["visitante"], False)]:
                if eq not in equipos:
                    equipos[eq] = {"pts":0,"gj":0,"gf":0,"gc":0,"pg":0,"pe":0,"pp":0}
                if p["resultado"] is not None:
                    equipos[eq]["gj"] += 1
                    if (p["resultado"]=="1" and es_local) or (p["resultado"]=="2" and not es_local):
                        equipos[eq]["pts"] += 3; equipos[eq]["pg"] += 1
                    elif p["resultado"]=="E":
                        equipos[eq]["pts"] += 1; equipos[eq]["pe"] += 1
                    else:
                        equipos[eq]["pp"] += 1
        tabla = sorted(equipos.items(), key=lambda x: (-x[1]["pts"], x[0]))
        datos[g] = tabla
    return render_template("grupos.html", datos=datos, BANDERAS=BANDERAS)


@app.route("/manifest.json")
def manifest():
    return jsonify({"name":"Prode Mundial 2026","short_name":"Prode 2026","start_url":"/","display":"standalone","background_color":"#0a1628","theme_color":"#0d2137","icons":[{"src":"/static/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"/static/icon-512.png","sizes":"512x512","type":"image/png"}]})

@app.route("/sw.js")
def service_worker():
    from flask import Response
    return Response("const CACHE='prode-v1';self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});", mimetype="application/javascript")

def auto_sync_horarios():
    api_key = os.environ.get("FOOTBALL_API_KEY") or get_config().get("api_key","")
    if not api_key: return
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://v3.football.api-sports.io/fixtures?league=1&season=2026",
            headers={"x-apisports-key": api_key.strip()})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        with app.app_context():
            actualizados = 0
            for m in data.get("response", []):
                fixture = m.get("fixture", {})
                utc_date = fixture.get("date")
                if not utc_date: continue
                api_id = fixture.get("id")
                hn = m.get("teams", {}).get("home", {}).get("name", "")
                an = m.get("teams", {}).get("away", {}).get("name", "")
                p = query(f"SELECT id FROM partidos WHERE api_id={PH}", (api_id,), fetchone=True)
                if not p:
                    p = query(f"SELECT id FROM partidos WHERE local LIKE {PH} AND visitante LIKE {PH}", (f"%{hn[:4]}%", f"%{an[:4]}%"), fetchone=True)
                if p:
                    query(f"UPDATE partidos SET hora_inicio={PH}, api_id={PH} WHERE id={PH}", (utc_date, api_id, p["id"]), commit=True)
                    actualizados += 1
            print(f"Auto-sync: {actualizados} horarios actualizados.")
    except Exception as e:
        print(f"Auto-sync error: {e}")

# ─── STARTUP ──────────────────────────────────────────────────────────────────

with app.app_context():
    init_db()
    auto_sync_horarios()

def _job_sync_resultados():
    with app.app_context():
        try:
            r = _sync_resultados()
            if r.get("actualizados"):
                print(f"Auto-sync resultados: {r['actualizados']} actualizados.")
        except Exception as e:
            print(f"Auto-sync resultados error: {e}")

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    if get_config().get("api_key","").strip():
        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.add_job(_job_sync_resultados, "interval", minutes=15, id="sync_resultados")
        _scheduler.start()
except Exception as e:
    print(f"No se pudo iniciar el sincronizador automático: {e}")

if __name__ == "__main__":
    print("\n🏆 App del Mundial 2026\n   http://localhost:5000\n   Admin: admin / admin123\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
